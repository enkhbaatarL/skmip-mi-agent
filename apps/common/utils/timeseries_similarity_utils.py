# TODO: 소스 정리
from datetime import datetime, timedelta
import json
import time

from dateutil.relativedelta import relativedelta
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from apps.common.logging.logger_config import logger
from apps.connectors.llm.llm_client import invoke_llm_function_call


def get_default_period(months: int = 3) -> tuple[str, str]:
    """최근 n개월을 기본 기간으로 반환 (YYYY-MM-DD 문자열 형식)."""
    today = datetime.today()
    start = today - relativedelta(months=months)
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def get_historical_period(current_start: str, current_end: str) -> tuple[str, str]:
    """현재 구간과 겹치지 않도록, 최근 1년 범위 내 과거 구간을 설정."""
    curr_start = datetime.strptime(current_start, "%Y-%m-%d")
    past_end = curr_start - timedelta(days=1)
    past_start = past_end - relativedelta(years=1)
    return past_start.strftime("%Y-%m-%d"), past_end.strftime("%Y-%m-%d")


def np_cosine_similarity(a, b):
    """두 1차원 벡터 a, b의 코사인 유사도 반환."""
    a = np.array(a).flatten()
    b = np.array(b).flatten()
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0  # 0벡터 예외 처리
    return np.dot(a, b) / (norm_a * norm_b)


def detect_date_and_value_columns(data: list[dict]) -> pd.DataFrame:
    """RDB로부터 조회한 raw 시계열 데이터를 받아,
    날짜/값 컬럼을 자동 추출하여 date-value DataFrame으로 반환.

    - 컬럼명에 의존하지 않고 실제 값 패턴을 기반으로 날짜/값 추론
    """
    if not data:
        msg = "빈 데이터입니다."
        raise ValueError(msg)

    sample = data[0]
    keys = list(sample.keys())
    date_column = None
    value_column = None

    for key in keys:
        values = [row[key] for row in data if key in row][:10]
        parsed_dates = 0
        numeric_count = 0

        for v in values:
            if isinstance(v, str):
                try:
                    datetime.fromisoformat(v.replace("Z", ""))
                    parsed_dates += 1
                except:
                    try:
                        datetime.strptime(v, "%Y-%m-%d")
                        parsed_dates += 1
                    except:
                        pass
            try:
                float(v)
                numeric_count += 1
            except:
                pass

        if parsed_dates >= len(values) * 0.7:
            date_column = key
        elif numeric_count >= len(values) * 0.7:
            value_column = key

    if not date_column or not value_column:
        msg = f"날짜/수치 컬럼을 자동 추론할 수 없습니다. keys: {keys}"
        raise ValueError(msg)

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df[date_column], errors="coerce")
    df["value"] = pd.to_numeric(df[value_column], errors="coerce")

    df = df[["date", "value"]]
    return df.sort_values("date").reset_index(drop=True)


def detect_date_and_value_columns_safe(data: list[dict]) -> pd.DataFrame:
    """1. 우선적으로 표준 컬럼명 후보(price/value/date 등)가 있으면 그걸 사용
    2. 없으면 값 패턴 기반 자동 추론 (기존 detect 방식).
    """
    if not data:
        msg = "빈 데이터입니다."
        raise ValueError(msg)

    sample = data[0]
    keys = list(sample.keys())

    # 1. 우선순위 후보 컬럼 정의
    value_candidates = ["value", "price", "amount", "close", "score"]
    date_candidates = ["date", "trd_dt", "datetime", "dt"]

    # 날짜 후보 우선 탐색
    date_column = next(
        (k for k in keys if k.lower() in [d.lower() for d in date_candidates]),
        None,
    )
    value_column = next(
        (k for k in keys if k.lower() in [v.lower() for v in value_candidates]),
        None,
    )

    # 2. fallback: 기존 방식 사용
    if not date_column or not value_column:
        return detect_date_and_value_columns(data)  # 기존 자동 추론 방식

    # 3. 변환 및 정제
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df[date_column], errors="coerce")
    df["value"] = pd.to_numeric(df[value_column], errors="coerce")
    return df[["date", "value"]]  # 분석 일관성 보장


def preprocess_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    """시계열 데이터에 대해 다음 처리 수행:
    - 이상치 제거 (IQR 기반)
    - 결측치 보간 (시간 기반 보간)
    - 정렬 및 결측치 보완.

    전제:
    - df는 'date'와 'value' 컬럼을 반드시 포함하고 있어야 함
    """
    if df.empty or "value" not in df.columns or "date" not in df.columns:
        return df  # 유효하지 않은 입력은 그대로 반환

    # 이상치 제거 (IQR 기준)
    Q1 = df["value"].quantile(0.25)
    Q3 = df["value"].quantile(0.75)
    IQR = Q3 - Q1
    lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
    outlier_mask = (df["value"] < lower) | (df["value"] > upper)
    if outlier_mask.any():
        logger.info(f"이상치 {outlier_mask.sum()}개 → NaN 처리")

    df.loc[outlier_mask, "value"] = np.nan

    # 시간 정렬 및 보간
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")  # 반드시 정렬
    df = df.set_index("date")
    df["value"] = df["value"].interpolate(method="time")  # 시간 기반 보간
    df["value"] = df["value"].ffill().bfill()  # 양방향 결측 보완
    return df.reset_index()


def find_similar_patterns_combined(
    current_df: pd.DataFrame,
    historical_df: pd.DataFrame,
    window_size: int,
    top_n: int = 3,
    alpha: float = 0.5,
) -> pd.DataFrame:
    """최근 구간과 과거 구간의 유사도를 Cosine + Pearson 방식으로 평가
    (같은 날짜에서 NaN이 아닌 첫 번째 값 우선 선택).

    Args:
        current_df: 최근 구간 (DataFrame with 'date', 'value')
        historical_df: 과거 전체 구간 (DataFrame with 'date', 'value')
        window_size: 최근 구간 길이 (일 수)
        top_n: 반환할 유사 구간 개수
        alpha: 가중치 비율 (0~1), 1이면 Cosine 100%, 0이면 Pearson 100%

    Returns:
        유사 구간 리스트 (start_date, end_date, scores, etc.)

    """
    start_time = time.time()

    # 입력값 유효성 검증
    if (
        current_df.empty
        or historical_df.empty
        or "value" not in current_df.columns
        or "value" not in historical_df.columns
    ):
        logger.info(
            "[유사 구간 탐색 중단] 입력 데이터프레임이 비어있거나 'value' 컬럼이 없습니다.",
        )
        return pd.DataFrame()

    if window_size < 2:
        logger.info(
            f"[유사 구간 탐색 중단] window_size({window_size})가 너무 작습니다. 최소 2개 이상 필요합니다.",
        )
        return pd.DataFrame()

    if len(historical_df) < window_size:
        logger.info(
            f"[유사 구간 탐색 중단] window_size({window_size})가 유효하지 않거나 과거 데이터 길이보다 깁니다.",
        )
        return pd.DataFrame()

    logger.info(f"[유사 구간 추출 시작] current_df: {len(current_df)}개")
    logger.info(f"[유사 구간 추출 시작] historical_df: {len(historical_df)}개")

    current_values = current_df["value"].values.reshape(1, -1)
    hist_values = historical_df["value"].values
    hist_dates = historical_df["date"].values

    results = []

    # 모든 과거 구간을 순회하며 점수 계산
    for i in range(len(hist_values) - window_size + 1):
        window = hist_values[i : i + window_size]
        # 날짜 데이터 변환
        window_dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in hist_dates[i : i + window_size]]

        # 개선된 중복 제거 로직
        unique_dates = []
        unique_values = []

        # 같은 날짜별로 그룹화하여 처리
        date_groups = {}
        for d, v in zip(window_dates, window, strict=False):
            if d not in date_groups:
                date_groups[d] = []
            date_groups[d].append(v)

        # 각 날짜별로 최적의 값 선택
        for date, values in date_groups.items():
            # NaN이 아닌 첫 번째 값 찾기
            selected_value = None
            for v in values:
                if not pd.isna(v):  # NaN이 아닌 첫 번째 값
                    selected_value = v
                    break

            # NaN이 아닌 값이 없으면 첫 번째 값 사용 (NaN이어도)
            if selected_value is None:
                selected_value = values[0]

            unique_dates.append(date)
            unique_values.append(selected_value)

        if len(unique_values) == current_values.shape[1]:
            if len(unique_values) >= 2:
                # Cosine similarity
                try:
                    cosine_sim = np_cosine_similarity(
                        current_values.flatten(),
                        unique_values,
                    )
                except Exception as e:
                    logger.info(f"Cosine 유사도 계산 실패: {e}. 기본값 0 사용")
                    cosine_sim = 0.0

                # Pearson correlation
                try:
                    pearson_corr, _ = pearsonr(current_values.flatten(), unique_values)
                except ValueError as e:
                    logger.info(f"Pearson 상관계수 계산 실패: {e}. 기본값 0 사용")
                    pearson_corr = 0.0

                # 통합 점수 (가중 평균)
                combined_score = alpha * cosine_sim + (1 - alpha) * abs(pearson_corr)

                if not np.isnan(combined_score):
                    results.append(
                        {
                            "start_date": unique_dates[0],
                            "end_date": unique_dates[-1],
                            "cosine_similarity": cosine_sim,
                            "pearson_correlation": pearson_corr,
                            "combined_score": combined_score,
                            "dates": unique_dates,
                            "values": unique_values,
                            "start_index": i,
                            "window_size": len(window),
                            "unique_size": len(unique_dates),
                        },
                    )
            else:
                logger.info(
                    f"데이터 포인트가 부족합니다: {len(unique_values)}개 (최소 2개 필요)",
                )
    logger.info(f"유사 구간 탐색 결과: {len(results)}개")

    if not results:
        logger.info("[유사 구간 탐색 결과] 유효한 유사 구간을 찾지 못했습니다.")
        return pd.DataFrame()

    # 점수 기준으로 내림차순 정렬
    results = sorted(results, key=lambda x: x["combined_score"], reverse=True)

    # 겹치지 않는 상위 N개 패턴 선택
    distinct_patterns = []
    for pattern in results:
        if len(distinct_patterns) >= top_n:
            break

        is_overlapping = False
        for selected_pattern in distinct_patterns:
            # 시작 인덱스가 window_size보다 가까우면 겹치는 것으로 간주
            if abs(pattern["start_index"] - selected_pattern["start_index"]) < window_size:
                is_overlapping = True
                break

        if not is_overlapping:
            # 겹치지 않는 경우에만 추가
            distinct_patterns.append(pattern)

    # 최종 결과 로깅
    logger.info(
        f"[유사 구간 탐색 완료] 총 {len(distinct_patterns)}개의 겹치지 않는 패턴을 찾았습니다.",
    )

    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(
        f"[find_similar_patterns_combined] 유사 구간 탐색 시간: {elapsed_time:.3f}초",
    )

    # Pandas 데이터프레임으로 변환하여 반환
    if not distinct_patterns:
        return pd.DataFrame()

    return pd.DataFrame(distinct_patterns)


def analyze_similarity_patterns(
    current_data: list,
    historical_data: list,
    top_n: int = 3,
    alpha: float = 0.5,
) -> tuple:
    """데이터를 전처리하고, 이상치를 제거한 후 유사 패턴을 분석합니다.

    Returns:
        A tuple containing: (processed_current_df, processed_historical_df, similar_patterns_df)

    """
    if not current_data or not historical_data:
        logger.info("입력 데이터가 없어 유사도 분석을 건너뜁니다.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    current_df = detect_date_and_value_columns_safe(current_data)
    historical_df = detect_date_and_value_columns_safe(historical_data)

    # 이상치 제거 및 시간 정렬
    current_df = preprocess_timeseries(current_df)
    historical_df = preprocess_timeseries(historical_df)

    logger.info("current_df, historical_df 전처리 완료")

    # 유사 패턴 찾기
    window_size = len(current_df)
    logger.info(f"window_size: {window_size}")
    logger.info(
        f"current_df 길이: {len(current_df)}, historical_df 길이: {len(historical_df)}",
    )
    # logger.info(f"current_df date 샘플: {current_df['date'].tolist()}")

    similar_patterns_df = find_similar_patterns_combined(
        current_df=current_df,
        historical_df=historical_df,
        window_size=window_size,
        top_n=top_n,
        alpha=alpha,
    )

    return current_df, historical_df, similar_patterns_df


def extract_query_components(query: str) -> dict:
    """LLM을 이용해 자연어 질의에서 핵심 주제와 기간(start_date, end_date)을 추출."""
    today = datetime.today()

    prompt = f"""
    사용자의 질문을 분석하여 핵심 분석 대상과 기간을 추출하세요.
    오늘 날짜는 {today.strftime("%Y-%m-%d")}입니다. '최근 3개월'처럼 상대적인 기간은 이 날짜를 기준으로 계산해야 합니다.

    결과는 반드시 'metric_subject', 'start_date', 'end_date' 키를 가진 유효한 JSON 객체로만 반환해야 합니다.
    JSON 외에 다른 설명이나 문장을 절대로 추가하지 마세요.

    - "metric_subject": 분석의 핵심 주제 (예: "원유 가격", "금 시세"). 동사나 기간 관련 표현은 제외하세요.
    - "start_date", "end_date": 질문에 명시된 특정 기간. 기간 언급이 없으면 null 값을 가져야 합니다.
    - 날짜 형식은 "YYYY-MM-DD"여야 합니다.

    ### 예시 1 (기간이 언급된 경우: 지난 3개월)
    - 사용자 질문: "지난 3개월간 원유 가격 추세와 유사한 과거 패턴이 있었나요?"
    - 당신의 JSON 답변:
    {{
      "metric_subject": "원유 가격",
      "start_date": "{(today - relativedelta(months=3)).strftime("%Y-%m-%d")}",
      "end_date": "{today.strftime("%Y-%m-%d")}"
    }}

    ### 예시 2 (기간이 언급되지 않은 경우)
    - 사용자 질문: "삼성전자 주가와 비슷한 흐름을 보였던 적이 있나요?"
    - 당신의 JSON 답변:
    {{
      "metric_subject": "삼성전자 주가",
      "start_date": null,
      "end_date": null
    }}

    ### 사용자 질문
    "{query}"

    ### 당신의 JSON 답변:
    """

    try:
        start_time = time.time()
        response = invoke_llm_function_call(
            messages=[{"role": "user", "content": prompt}],
            model_name="gpt-4",
        )
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"[extract_query_components] LLM 응답시간: {elapsed_time:.3f}초")

        content = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        cleaned_response = content.strip().replace("```json", "").replace("```", "")
        result = json.loads(cleaned_response)

        if "metric_subject" in result:
            return result
        logger.warning(
            "[extract_query_components] LLM 응답에 'metric_subject' 키가 없습니다. Fallback 사용.",
        )
        return {"metric_subject": query, "start_date": None, "end_date": None}

    except Exception as e:
        logger.warning(
            f"[extract_query_components] LLM 응답 처리 실패: {e}. Fallback 사용.",
        )
        return {"metric_subject": query, "start_date": None, "end_date": None}

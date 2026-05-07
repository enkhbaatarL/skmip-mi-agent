"""
MI 수급모델 Param 도출 파이프라인
"""

import json
import re
import sys
from datetime import datetime, timezone

import pandas as pd


# ═════════════════════════════════════════════════════════════════════════════
# 1. 매핑 엑셀 파서
#    읽어야 하는 정보:
#      A. 00.시트별Params  → parameter별 model_file / axes / unit / enum
#      B. 0X.L1_*         → event_type(L1+L2) → Dim 목록 + 후보 파라미터
# ═════════════════════════════════════════════════════════════════════════════

# event_type level_1_code → 매핑 엑셀 시트명 대응표
# (매핑 엑셀에 L1 코드가 직접 없으므로 L1 label로 연결)
_L1_LABEL_TO_SHEET = {
    "지정학적 리스크": "01.L1_지정학적리스크",
    "기상/기후":       "02.L1_기상기후",
}
# event_type level_1_code(영문) → L1 label(한글) 변환
_L1_CODE_TO_LABEL = {
    "geopolitical_risk": "지정학적 리스크",
    "weather_climate":   "기상/기후",
}
# event_type level_2_code(영문) → L2 label(한글) 변환
_L2_CODE_TO_LABEL = {
    "summer_heat_wave":        "여름 고온",
    "winter_cold_wave":        "겨울 한파",
    "war_conflict":            "전쟁/군사분쟁",
    "geopolitical_tension":    "지정학적 긴장/불안정",
    "economic_sanctions":      "경제 제재/무역 제한",
    "regime_change":           "정권 교체/정치 전환",
}

# 간접 Dim 식별자 (시트명 컬럼이 "간접"인 경우)
_INDIRECT_MARKER = "간접"
# 미구현 파라미터 마커
_TBU_MARKER = "(TBU)"


def parse_param_master(xl: pd.ExcelFile) -> dict:
    """
    00.시트별Params 시트 파싱.

    반환값: {
      (model_sheet, parameter_name): {
        "model_file": str,
        "unit": str,
        "unit_note": str | None,
        "axes": [{"name": str, "level": str, "enum": str | None}, ...]
      }
    }
    """
    df = xl.parse("00.시트별Params", header=None)
    # 헤더: row 1 (col1=파일, col2=시트명, col3=Parameter Name, col4=단위,
    #             col6=축1이름, col7=축1단계, col8=축2이름, col9=축2단계,
    #             col10=축3이름, col11=축3단계, col16=Comment)
    master = {}
    for _, row in df.iterrows():
        mfile = str(row.iloc[1]).strip()
        msheet = str(row.iloc[2]).strip()
        pname = str(row.iloc[3]).strip()
        unit = str(row.iloc[4]).strip()

        if mfile == "nan" or msheet == "nan" or pname == "nan":
            continue

        # axes 파싱: 축1~4
        axes = []
        for name_col, level_col in [(6, 7), (8, 9), (10, 11), (12, 13)]:
            aname = str(row.iloc[name_col]).strip() if len(row) > name_col else "nan"
            alevel = str(row.iloc[level_col]).strip() if len(row) > level_col else "nan"
            if aname == "nan" or aname == "-":
                break
            # enum 추출: "enum (A, B, C)" 형태
            enum_vals = None
            if alevel.startswith("enum (") and alevel.endswith(")"):
                enum_vals = [v.strip() for v in alevel[6:-1].split(",")]
            axes.append({"name": aname, "level": alevel, "enum": enum_vals})

        comment = str(row.iloc[16]).strip() if len(row) > 16 else ""
        unit_note = comment if comment not in ("nan", "") else None
        # TBU 단위 처리
        if unit == _TBU_MARKER:
            unit_note = (unit_note + " " if unit_note else "") + \
                        "단위 미확정(TBU) — 실제 모델 단위 확인 필요"

        master[(msheet, pname)] = {
            "model_file": mfile,
            "unit":       unit if unit != _TBU_MARKER else "(TBU)",
            "unit_note":  unit_note,
            "axes":       axes,
        }
    return master


def parse_event_type_mapping(
    xl: pd.ExcelFile,
    l1_code: str,
    l2_code: str,
    param_master: dict,
) -> dict:
    """
    event_type(L1+L2)에 해당하는 매핑 시트 섹션을 파싱.

    반환값: {
      dim_id: {
        "position": int,          ← Dim 번호 (순서 결정용)
        "label_ko": str,
        "role": "direct" | "indirect",
        "indirect_note": str | None,
        "candidates": [
          {
            "parameter_name": str,
            "model_sheet": str,
            "model_file": str,
            "unit": str,
            "unit_note": str | None,
            "comment": str,
            "axes": [...],         ← param_master에서 조인
            "blocks": [],          ← 아래에서 후처리로 채움
          }, ...
        ]
      }
    }
    """
    l1_label = _L1_CODE_TO_LABEL.get(l1_code)
    l2_label = _L2_CODE_TO_LABEL.get(l2_code)
    sheet_name = _L1_LABEL_TO_SHEET.get(l1_label)

    if not sheet_name or not l2_label:
        raise ValueError(
            f"매핑 엑셀에서 event_type '{l1_code}::{l2_code}'에 "
            f"대응하는 시트/섹션을 찾을 수 없음"
        )

    df = xl.parse(sheet_name, header=None)

    # 해당 L2 섹션 시작 행 탐색
    section_start = None
    for i, row in df.iterrows():
        if str(row.iloc[2]).strip() == "L2" and str(row.iloc[3]).strip() == l2_label:
            section_start = i
            break

    if section_start is None:
        raise ValueError(f"매핑 시트 '{sheet_name}'에서 L2='{l2_label}' 섹션 없음")

    # 헤더 행: section_start + 3 (L2행, 버전행, 헤더행)
    # 실제 데이터: 헤더 다음 행부터 다음 빈 섹션 전까지
    header_row = section_start + 3
    dim_map = {}

    i = header_row + 1
    while i < len(df):
        row = df.iloc[i]
        dim_raw = str(row.iloc[2]).strip()   # "Dim1", "Dim2", ...
        label = str(row.iloc[3]).strip()
        msheet = str(row.iloc[4]).strip()
        pname = str(row.iloc[5]).strip()
        comment = str(row.iloc[6]).strip() if len(row) > 6 else ""

        # 섹션 종료 감지 (빈 행 또는 다음 Event Type 섹션)
        if dim_raw == "nan" and label == "nan":
            break
        if label == "nan":
            i += 1
            continue

        # Dim 번호 파싱: "Dim1" → 1
        dim_num_match = re.match(r"Dim(\d+)", dim_raw)
        if not dim_num_match:
            i += 1
            continue
        dim_num = int(dim_num_match.group(1))

        # dim_id는 실제 선택된 dimension_id와 매핑이 필요하므로
        # 여기서는 dim_num을 key로 임시 저장, 나중에 selected_dims와 매핑
        dim_key = f"dim_{dim_num}"

        is_indirect = (msheet == _INDIRECT_MARKER)
        is_tbu = (msheet == _TBU_MARKER)

        if dim_key not in dim_map:
            dim_map[dim_key] = {
                "position":      dim_num,
                "label_ko":      label,
                "role":          "indirect" if (is_indirect or is_tbu) else "direct",
                "indirect_note": comment if (is_indirect or is_tbu) else None,
                "candidates":    [],
                "blocks":        [],   # 후처리
            }

        if not is_indirect and not is_tbu and pname not in ("-", "nan", ""):
            # param_master에서 axes / unit 조인
            pm = param_master.get((msheet, pname), {})
            # Temperature 끝에 공백이 있을 수 있으므로 strip 재시도
            if not pm:
                pm = param_master.get((msheet, pname.strip()), {})

            dim_map[dim_key]["candidates"].append({
                "parameter_name": pname.strip(),
                "model_sheet":    msheet,
                "model_file":     pm.get("model_file", "Unknown"),
                "unit":           pm.get("unit", "(TBU)"),
                "unit_note":      pm.get("unit_note"),
                "comment":        comment if comment not in ("nan", "") else "",
                "axes":           pm.get("axes", []),
                "blocks":         [],   # 후처리
            })

        i += 1

    # ── 블로킹 관계 후처리
    # "B(기온강도)와 동시 선택 금지" 패턴 감지 → 동일 parameter_name을 갖는
    # 다른 Dim의 후보를 blocks에 등록
    _apply_blocks(dim_map)

    return dim_map


def _apply_blocks(dim_map: dict) -> None:
    """
    Comment에서 블로킹 규칙을 추출해 blocks 리스트를 채움.
    현재 패턴: "B(기온강도)와 동시 선택 금지" → 해당 parameter_name과
    같은 이름을 가진 다른 Dim의 후보들을 block 대상으로 등록.
    """
    BLOCK_PATTERN = re.compile(r"([A-Z])\(.*?\)와 동시 선택 금지")

    # Dim 레이블 첫 글자 → dim_key 매핑 구성
    label_initial_to_dim = {}
    for dk, dv in dim_map.items():
        label_ko = dv["label_ko"]
        # "A.", "B.", "C.", "E." 등 앞 글자
        m = re.match(r"([A-Z])\.", label_ko)
        if m:
            label_initial_to_dim[m.group(1)] = dk

    for dk, dv in dim_map.items():
        for cand in dv["candidates"]:
            m = BLOCK_PATTERN.search(cand["comment"])
            if not m:
                continue
            blocked_initial = m.group(1)   # 예: "B"
            blocker_dim_key = label_initial_to_dim.get(blocked_initial)
            if not blocker_dim_key:
                continue
            # blocker_dim의 동일 parameter_name 후보들을 block 대상으로 등록
            for blocker_cand in dim_map[blocker_dim_key]["candidates"]:
                block_entry = {
                    "dim_key":        dk,
                    "parameter_name": cand["parameter_name"],
                }
                if block_entry not in blocker_cand["blocks"]:
                    blocker_cand["blocks"].append(block_entry)


# ═════════════════════════════════════════════════════════════════════════════
# 2. Dim 순서 + primary 후보 결정
#    [전] DIM_PROCESS_ORDER     하드코딩
#    [후] dim_map["position"] 기반 정렬 + selected_dim_ids 교집합
#
#    [전] DIM_PRIMARY_CANDIDATE 하드코딩
#    [후] stage2.rationale 키워드 매칭 → fallback: 첫 번째 후보
# ═════════════════════════════════════════════════════════════════════════════

def build_dim_process_order(
    dim_map: dict,
    selected_dim_ids: list,
    dim_num_to_id: dict,
) -> list:
    """
    매핑 엑셀 Dim 번호(position) 오름차순으로 정렬.
    selected_dim_ids에 있는 것만 포함.

    dim_num_to_id: {dim_num(int): dimension_id(str)}
      ← stage2.selected_dimensions 순서와 매핑 엑셀 Dim 번호를 연결
    """
    matched = []
    for dim_key, dv in dim_map.items():
        dim_num = dv["position"]
        dim_id = dim_num_to_id.get(dim_num)
        if dim_id and dim_id in selected_dim_ids:
            matched.append((dv["position"], dim_key, dim_id))

    matched.sort(key=lambda x: x[0])
    return [(dk, did) for _, dk, did in matched]


def infer_primary_candidate(
    dim_id: str,
    candidates: list,
    rationale: str,
    event_context: str,
) -> str | None:
    """
    Logic §2.2 [1]: stage2.rationale + event context에서
    후보 parameter_name 키워드를 찾아 primary를 결정.

    1순위: rationale 또는 event_context에서 parameter_name 직접 언급
    2순위: comment 키워드 매칭 (기관 전망 언급 수 > 0)
    3순위: fallback — 첫 번째 후보 (매핑 엑셀 순서가 우선순위 의미)
    """
    search_text = (rationale + " " + event_context).lower()

    # 1순위: parameter_name 직접 언급
    for cand in candidates:
        if cand["parameter_name"].lower() in search_text:
            return cand["parameter_name"]

    # 2순위: comment 키워드 중 context에 등장하는 것
    # (예: "냉방도일", "cooling degree days" → CDD 선택)
    KEYWORD_MAP = {
        "CDD":         ["냉방도일", "cooling degree", "cdd"],
        "HDD":         ["난방도일", "heating degree", "hdd"],
        "Temperature": ["기온 편차", "temperature", "℃", "온도"],
        "PowerMix":    ["발전 mix", "power mix", "발전비중", "가스 비중"],
        "DemandModelOuptut": ["수요 직접", "overwrite", "demand output"],
        "LiqProdAdjustment":  ["생산량", "production", "직접 감소"],
        "LiqUtilAdjustment":  ["가동률", "utilisation", "utilization"],
    }
    best = None
    best_score = 0
    for cand in candidates:
        pname = cand["parameter_name"]
        keywords = KEYWORD_MAP.get(pname, [])
        score = sum(1 for kw in keywords if kw.lower() in search_text)
        if score > best_score:
            best_score = score
            best = pname

    if best:
        return best

    # 3순위: fallback — 매핑 엑셀 첫 번째 후보
    return candidates[0]["parameter_name"] if candidates else None


# ═════════════════════════════════════════════════════════════════════════════
# 3. 의존성 처리 (블로킹) — v3과 동일 로직, dim_map 기반으로 재작성
# ═════════════════════════════════════════════════════════════════════════════

def resolve_candidates(
    process_order: list,    # [(dim_key, dim_id), ...]
    dim_map: dict,
    selected_dim_ids: list,
    dim_num_to_id: dict,
    stage2_dims: dict,      # {dim_id: {"rationale": str}}
    event_context: str,
) -> dict:
    """
    Dim 순서대로 순회하며 후보 선택 + 블로킹 적용.

    반환값: {
      dim_id: {
        "role": str,
        "label_ko": str,
        "indirect_note": str | None,
        "candidates": [{"parameter_name", "selected", "blocked", "blocked_reason", ...}]
      }
    }
    """
    # dim_key → dim_id 역방향 맵
    dim_key_to_id = {dk: did for dk, did in process_order}
    # 블록 집합: {(dim_id, parameter_name)}
    blocked_set: set = set()

    result = {}

    for dim_key, dim_id in process_order:
        dv   = dim_map[dim_key]
        role = dv["role"]

        if role == "indirect":
            result[dim_id] = {
                "role":          "indirect",
                "label_ko":      dv["label_ko"],
                "indirect_note": dv.get("indirect_note"),
                "candidates":    [],
            }
            continue

        rationale     = stage2_dims.get(dim_id, {}).get("rationale", "")
        avail_cands   = [
            c for c in dv["candidates"]
            if (dim_id, c["parameter_name"]) not in blocked_set
        ]
        blocked_cands = [
            c for c in dv["candidates"]
            if (dim_id, c["parameter_name"]) in blocked_set
        ]

        # primary 결정 (input 파일 기반)
        primary_name = infer_primary_candidate(
            dim_id, avail_cands, rationale, event_context
        )

        resolved = []
        chosen = None

        for cand in dv["candidates"]:
            pname      = cand["parameter_name"]
            is_blocked = (dim_id, pname) in blocked_set

            if is_blocked:
                resolved.append({
                    **{k: v for k, v in cand.items() if k != "blocks"},
                    "selected":       False,
                    "blocked":        True,
                    "blocked_reason": (
                        "앞선 Dim 선택에 의해 차단. "
                        f"매핑 엑셀 comment: '{cand['comment']}'"
                    ),
                    "selection_basis": None,
                })
                continue

            is_selected = (chosen is None and pname == primary_name)
            if is_selected:
                chosen = pname
                # 이 후보의 blocks 대상을 blocked_set에 추가
                for blk in cand.get("blocks", []):
                    blk_dim_id = dim_key_to_id.get(blk["dim_key"])
                    if blk_dim_id:
                        blocked_set.add((blk_dim_id, blk["parameter_name"]))

            resolved.append({
                **{k: v for k, v in cand.items() if k != "blocks"},
                "selected":       is_selected,
                "blocked":        False,
                "blocked_reason": None,
                "selection_basis": (
                    f"rationale/context 키워드 매칭으로 선택: '{pname}'. "
                    f"rationale: \"{rationale[:60]}...\""
                ) if is_selected else None,
            })

        # primary가 선택 안 됐으면 첫 번째 비블록 후보 선택 (fallback)
        if chosen is None:
            for rc in resolved:
                if not rc["blocked"]:
                    rc["selected"]       = True
                    rc["selection_basis"] = (
                        "rationale 키워드 매칭 없음 — "
                        "매핑 엑셀 첫 번째 후보로 fallback"
                    )
                    chosen = rc["parameter_name"]
                    for blk in next(
                        c for c in dv["candidates"]
                        if c["parameter_name"] == chosen
                    ).get("blocks", []):
                        blk_dim_id = dim_key_to_id.get(blk["dim_key"])
                        if blk_dim_id:
                            blocked_set.add((blk_dim_id, blk["parameter_name"]))
                    break

        result[dim_id] = {
            "role":          "direct",
            "label_ko":      dv["label_ko"],
            "indirect_note": None,
            "candidates":    resolved,
        }

    return result


def get_selected_params(
    resolved: dict,
    stage2_dims: dict,
    event_context: str,
) -> list:
    """
    selected=True인 후보만 추출.
    build_param_entry에서 axis_values 추론에 필요한
    event_context / stage2_rationale을 함께 전달.
    """
    selected = []
    for dim_id, info in resolved.items():
        rationale = stage2_dims.get(dim_id, {}).get("rationale", "")
        for cand in info.get("candidates", []):
            if cand.get("selected"):
                selected.append({
                    "source_dim_id":     dim_id,
                    "parameter_name":    cand["parameter_name"],
                    "model_file":        cand["model_file"],
                    "model_sheet":       cand["model_sheet"],
                    "unit":              cand["unit"],
                    "unit_note":         cand.get("unit_note"),
                    "comment":           cand["comment"],
                    "axes":              cand.get("axes", []),
                    "selection_basis":   cand.get("selection_basis"),
                    # axis_values 추론용 — build_param_entry로 전달
                    "_event_context":    event_context,
                    "_stage2_rationale": rationale,
                })
    return selected


# ═════════════════════════════════════════════════════════════════════════════
# 4. axis_values 룰 (Dim1·Dim3 간접 처리)
#    이 부분은 현재 input 파일에 매핑 정보가 없으므로
#    향후 DB 연동 시 교체 예정 — 주석으로 명시
# ═════════════════════════════════════════════════════════════════════════════

# TODO: DB 연동 시 아래 두 딕셔너리를 DB 쿼리로 교체
DURATION_TO_MONTHS = {
    "shoulder_only": ["2026-04", "2026-09"],
    "short":         ["2026-06", "2026-07"],
    "mid_peak":      ["2026-06", "2026-07", "2026-08"],
    "extended":      ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09"],
    "prolonged":     ["2026-04", "2026-05", "2026-06", "2026-07",
                      "2026-08", "2026-09", "2026-10"],
}

SCOPE_TO_COUNTRIES = {
    "sea_india_only": ["India", "Thailand", "Vietnam"],
    "single_ne":      ["Japan", "South Korea"],
    "ne_asia_multi":  ["Japan", "South Korea", "China"],
    "multi_region":   ["Japan", "South Korea", "China", "Germany", "UK", "Kuwait"],
    "global":         ["Japan", "South Korea", "China", "India",
                       "Germany", "UK", "France", "Spain", "Kuwait", "UAE"],
}


# ═════════════════════════════════════════════════════════════════════════════
# 5. value_grid 계산
#    TODO: DB 연동 시 실측 기후 데이터 / 기관 전망값으로 교체
# ═════════════════════════════════════════════════════════════════════════════

TEMP_ANOMALY_DELTA_C = {
    "normal": 0.0, "mild": 1.5, "moderate": 2.5, "severe": 4.0, "extreme": 6.0,
}
MONTH_SEASONAL_FACTOR = {
    "2026-04": 0.30, "2026-05": 0.55, "2026-06": 0.88,
    "2026-07": 1.00, "2026-08": 0.95, "2026-09": 0.65, "2026-10": 0.35,
}
COOLING_TO_GAS_BASE_DELTA = {
    "s1_lt_1mt": 0.5, "s2_1_3mt": 1.5, "s3_3_6mt": 3.0,
    "s4_6_12mt": 5.5, "s5_12mt_plus": 9.0,
}
TEMP_POWERMIX_MULTIPLIER = {
    "normal": 0.5, "mild": 0.8, "moderate": 1.0, "severe": 1.2, "extreme": 1.5,
}


def calc_cdd_grid(countries, months, temp_enum):
    delta_c = TEMP_ANOMALY_DELTA_C[temp_enum]
    return [
        [round(delta_c * 30 * MONTH_SEASONAL_FACTOR.get(m, 0.8), 1) for m in months]
        for _ in countries
    ]


def calc_temp_grid(countries, months, temp_enum):
    delta_c = TEMP_ANOMALY_DELTA_C[temp_enum]
    return [
        [round(delta_c * MONTH_SEASONAL_FACTOR.get(m, 0.8), 2) for m in months]
        for _ in countries
    ]


def calc_powermix_grid(countries, energy_sources, temp_enum, cooling_enum):
    """
    shape = [n_country, n_energy, 1(year)].
    energy_sources: context에서 추론된 변동 에너지원 리스트 (예: ["Gas", "Hydro"])
    Gas는 +delta, 나머지(Hydro 등 감소 에너지원)는 -delta 절반으로 산출.
    """
    base_delta = round(
        COOLING_TO_GAS_BASE_DELTA[cooling_enum] * TEMP_POWERMIX_MULTIPLIER[temp_enum], 2
    )
    # 에너지원별 delta 방향 키워드 (감소 에너지원)
    DECREASE_ENERGY = {"Hydro", "Nuclear", "Solar", "Wind"}

    grid = []
    for _ in countries:
        energy_row = []
        for energy in energy_sources:
            if energy in DECREASE_ENERGY:
                # 가스 증가분의 일부를 흡수하는 감소 에너지원
                val = round(-base_delta * 0.5, 2)
            else:
                val = base_delta
            energy_row.append([val])   # [year] dimension = 1개
        grid.append(energy_row)
    return grid


def make_cell_annotations(months, temp_enum):
    peak_idx = months.index("2026-07") if "2026-07" in months else 0
    return [{
        "cell_index":   [0, peak_idx],
        "rationale_ko": (
            f"WMO 엘니뇨 예보: 피크월({months[peak_idx]}) 증분. "
            f"temp_anomaly={temp_enum} "
            f"(Δ+{TEMP_ANOMALY_DELTA_C[temp_enum]}°C 기준)"
        ),
        "confidence": "medium" if temp_enum in ["moderate", "severe"] else "low",
    }]


# ═════════════════════════════════════════════════════════════════════════════
# 6. Parameter 항목 조립
# ═════════════════════════════════════════════════════════════════════════════

def build_param_entry(
    selected_param: dict,
    dims: dict,
    event_summary: str,
    param_master: dict,
) -> dict:
    pname        = selected_param["parameter_name"]
    mfile        = selected_param["model_file"]
    msheet       = selected_param["model_sheet"]
    unit         = selected_param["unit"]
    unit_note    = selected_param.get("unit_note")
    src_dim      = selected_param["source_dim_id"]
    sel_basis    = selected_param.get("selection_basis", "")
    axes_meta    = selected_param.get("axes", [])

    scope    = dims.get("affected_region_scope", "ne_asia_multi")
    duration = dims.get("duration_months", "mid_peak")
    temp     = dims.get("temperature_anomaly", "moderate")
    cooling  = dims.get("cooling_power_demand_increase", "s3_3_6mt")

    countries = SCOPE_TO_COUNTRIES.get(scope, [])
    months    = DURATION_TO_MONTHS.get(duration, [])

    value_meta_base = {"mode": "delta", "unit": unit}
    if unit_note:
        value_meta_base["unit_note"] = unit_note

    # ── axis 구성: param_master의 axes_meta로부터 생성
    def infer_energy_axis_values(
        axis_enum_full: list,
        event_context: str,
        rationale: str,
    ) -> tuple[list, str]:
        """
        Logic §2.2 [2]: context에서 변동하는 에너지원을 추론해 axis_values 결정.

        추론 순서:
          1순위: axis_enum_full 각 항목이 event_context/rationale에 언급되는지 확인
          2순위: 언급된 에너지원이 없으면 "Gas" fallback
                 (PowerMix가 선택된 맥락 자체가 가스 수요 변동을 전제하므로)

        반환값: (axis_values, inference_note)
        """
        # 에너지원별 언급 키워드 (매핑 엑셀 enum 항목 → 관련 한글/영문 표현)
        # 단어 경계 매칭을 위해 한글은 앞뒤 비단어 문자, 영문은 word boundary 사용
        import re as _re
        ENERGY_KEYWORDS = {
            "Gas":        [r"가스", r"gas", r"lng", r"천연가스", r"가스발전"],
            "Coal":       [r"석탄", r"coal", r"석탄발전"],
            "Hydro":      [r"수력", r"hydro", r"수력발전"],
            "Solar":      [r"태양광", r"solar"],
            "Wind":       [r"풍력", r"wind"],
            "Nuclear":    [r"원자력", r"nuclear"],   # "핵" 단독은 제거 (부분매칭 방지)
            "Liquids":    [r"석유", r"oil", r"중유"],
            "Bioenergy":  [r"바이오매스", r"bio"],
            "Geothermal": [r"지열", r"geothermal"],
            "Other":      [],
        }

        search_text = (event_context + " " + rationale).lower()

        mentioned = []
        for energy in axis_enum_full:
            patterns = ENERGY_KEYWORDS.get(energy, [energy.lower()])
            if any(_re.search(p, search_text) for p in patterns):
                mentioned.append(energy)

        if mentioned:
            note = (
                f"context 키워드 매칭으로 결정: {mentioned}. "
                f"나머지 에너지원의 offset 처리는 모델 내부 동작 확인 필요."
            )
            return mentioned, note
        else:
            # fallback: PowerMix가 선택된 맥락 자체가 가스 수요 변동을 전제
            note = (
                "context에서 에너지원 직접 언급 없음 → 'Gas' fallback. "
                "(PowerMix 선택 맥락 = 가스 수요 변동이 전제). "
                "나머지 에너지원의 offset 처리는 모델 내부 동작 확인 필요."
            )
            return ["Gas"], note

    def build_slot_axes_from_meta(
        axes_meta, countries, months, event_context="", stage2_rationale=""
    ):
        """axes_meta(매핑 엑셀 파싱값)로 slot_axes 초안 생성."""
        slot_axes = []
        for ax in axes_meta:
            aname  = ax["name"]
            alevel = ax["level"]
            aenum  = ax.get("enum")

            if aname in ("지역", "Country", "시설"):
                entry = {"axis_name": alevel if alevel not in ("nan", "-") else aname,
                         "axis_values": countries}
                if aenum:
                    entry["axis_enum_full"] = aenum
                slot_axes.append(entry)

            elif "에너지원" in aname:
                # Logic §2.2 [2]: context 기반 추론 (하드코딩 제거)
                inferred_values, inference_note = infer_energy_axis_values(
                    aenum or [], event_context, stage2_rationale
                )
                entry = {
                    "axis_name":        aname,
                    "axis_values":      inferred_values,
                    "axis_enum_full":   aenum or [],
                    "axis_values_note": inference_note,
                }
                slot_axes.append(entry)

            elif aname in ("시간", "time"):
                time_axis_name = "year-month" if "월" in alevel else "year"
                time_values    = months if "월" in alevel else ["2026"]
                slot_axes.append({"axis_name": time_axis_name, "axis_values": time_values})

        return slot_axes

    # event_context: base_event의 전체 텍스트
    # stage2_rationale: 이 parameter를 구동한 dim의 rationale
    _event_context     = selected_param.get("_event_context", "")
    _stage2_rationale  = selected_param.get("_stage2_rationale", "")
    slot_axes = build_slot_axes_from_meta(
        axes_meta, countries, months, _event_context, _stage2_rationale
    )

    # ── parameter별 value_grid 계산
    if pname == "CDD":
        value_grid       = calc_cdd_grid(countries, months, temp)
        cell_annotations = make_cell_annotations(months, temp)
        src_refs         = ["temperature_anomaly", "affected_region_scope", "duration_months"]
        confidence       = "medium" if temp in ["moderate", "severe"] else "low"
        rationale        = (
            f"{event_summary}. scope={scope}({len(countries)}개국), "
            f"duration={duration}({months[0] if months else '?'}~{months[-1] if months else '?'}). "
            f"temp_anomaly={temp} → Δ+{TEMP_ANOMALY_DELTA_C[temp]}°C × 30일 × 계절성 보정."
        )

    elif pname.strip() == "Temperature":
        value_grid       = calc_temp_grid(countries, months, temp)
        cell_annotations = make_cell_annotations(months, temp)
        src_refs         = ["temperature_anomaly", "affected_region_scope", "duration_months"]
        confidence       = "medium" if temp in ["moderate", "severe"] else "low"
        rationale        = (
            f"{event_summary}. scope={scope}({len(countries)}개국). "
            f"temp_anomaly={temp} → Δ+{TEMP_ANOMALY_DELTA_C[temp]}°C 직접 입력 (계절성 보정)."
        )

    elif pname == "PowerMix":
        # axis_values는 이미 slot_axes에서 context 추론으로 결정됨
        # slot_axes의 에너지원 axis에서 axis_values를 가져와 value_grid shape 결정
        energy_axis     = next(
            (ax for ax in slot_axes if "에너지원" in ax["axis_name"]), None
        )
        energy_sources  = energy_axis["axis_values"] if energy_axis else ["Gas"]
        value_grid       = calc_powermix_grid(countries, energy_sources, temp, cooling)
        base_delta       = round(
            COOLING_TO_GAS_BASE_DELTA[cooling] * TEMP_POWERMIX_MULTIPLIER[temp], 2
        )
        energy_note      = energy_axis.get("axis_values_note", "") if energy_axis else ""
        cell_annotations = []
        src_refs         = ["cooling_power_demand_increase", "temperature_anomaly",
                            "affected_region_scope"]
        confidence       = "low"
        rationale        = (
            f"cooling_demand={cooling} × temp_anomaly={temp} → "
            f"변동 에너지원: {energy_sources} (base_delta={base_delta}%p). "
            f"추론 근거: {energy_note[:80]}. "
            f"scope={scope}({len(countries)}개국), 시간축=연(2026)."
        )

    elif pname == "DemandModelOuptut":
        n_month    = len(months)
        value_grid = [[[None] * n_month] for _ in countries]
        cell_annotations = []
        src_refs         = ["cooling_power_demand_increase", "affected_region_scope",
                            "duration_months"]
        confidence       = "low"
        rationale        = (
            f"Power/Commercial 섹터 수요 출력 직접 overwrite. "
            f"scope={scope}({len(countries)}개국). 값 null — 분석가 직접 입력(HIL-1)."
        )

    else:
        # 알 수 없는 parameter: value_grid = null (분석가 입력 필요)
        value_grid       = None
        cell_annotations = []
        src_refs         = [src_dim]
        confidence       = "low"
        rationale        = f"parameter '{pname}' — 값 산출 룰 미정의. 분석가 직접 입력 필요."

    return {
        "parameter_slot_id":  f"{mfile}.{msheet}.{pname}.{scope}.{duration}",
        "model_file":         mfile,
        "model_sheet":        msheet,
        "parameter_name":     pname,
        "source_dim_id":      src_dim,
        "slot_axes":          slot_axes,
        "value_meta":         value_meta_base,
        "value_grid":         value_grid,
        "cell_annotations":   cell_annotations,
        "selection_basis":    sel_basis or selected_param.get("comment", ""),
        "rationale_ko_overall":           rationale,
        "source_assumption_refs_overall": src_refs,
        "confidence_overall":             confidence,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 7. ModelInput 조립
# ═════════════════════════════════════════════════════════════════════════════

def build_model_input(
    scenario: dict,
    base_event: dict,
    stage2: dict,
    dim_map: dict,
    dim_num_to_id: dict,
    param_master: dict,
) -> dict:
    sid           = scenario["scenario_id"]
    dims          = scenario["dimension_values"]
    event_summary = base_event.get("one_line_summary", "")
    event_context = (
        base_event.get("detail_analysis", "") + " " +
        base_event.get("market_and_institution_view", "") + " " +
        " ".join(base_event.get("key_bullets", []))
    )
    event_type_id = (
        f"{base_event['event_type']['level_1_code']}::"
        f"{base_event['event_type']['level_2_code']}"
    )

    selected_dim_ids = list(dims.keys())
    stage2_dims = {
        d["dimension_id"]: {"rationale": d["rationale"]}
        for d in stage2["selected_dimensions"]
    }

    # Dim 처리 순서 결정 (매핑 엑셀 position 기반)
    process_order = build_dim_process_order(dim_map, selected_dim_ids, dim_num_to_id)

    # 후보 resolve + 블로킹
    resolved = resolve_candidates(
        process_order, dim_map, selected_dim_ids,
        dim_num_to_id, stage2_dims, event_context,
    )

    selected_params  = get_selected_params(resolved, stage2_dims, event_context)
    input_parameters = [
        build_param_entry(sp, dims, event_summary, param_master)
        for sp in selected_params
    ]

    now = datetime.now(timezone.utc).isoformat()

    return {
        "input_id":           f"mi_{sid}_{dims.get('affected_region_scope')}_{dims.get('duration_months')}",
        "source_scenario_id": sid,
        "state":              "Draft",
        "needs_re_propose":   False,
        "needs_re_execute":   False,
        "proposed_dims": [
            {
                "dim_id":        dim_id,
                "label_ko":      resolved[dim_id]["label_ko"],
                "role":          resolved[dim_id]["role"],
                "enum_value_id": dims.get(dim_id),
                "parameter_candidates_summary": [
                    {
                        "parameter_name": c["parameter_name"],
                        "model_file":     c["model_file"],
                        "model_sheet":    c["model_sheet"],
                        "selected":       c["selected"],
                        "blocked":        c["blocked"],
                        "blocked_reason": c.get("blocked_reason"),
                        "selection_basis": c.get("selection_basis"),
                    }
                    for c in resolved[dim_id]["candidates"]
                ] if resolved[dim_id]["role"] == "direct" else [],
            }
            for dim_id in resolved
        ],
        "source_assumptions": [
            {"dimension_id": k, "enum_value_id": v} for k, v in dims.items()
        ],
        "source_event_type_id": event_type_id,
        "parameter_candidates_full": {
            dim_id: info
            for dim_id, info in resolved.items()
            if info["role"] == "direct"
        },
        "input_parameters":    input_parameters,
        "input_param_changes": [],
        "active_result_id":    None,
        "created_at":          now,
        "last_updated_at":     now,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 8. Dim 번호 ↔ dimension_id 매핑
#    매핑 엑셀의 Dim 번호와 stage2의 dimension_id를 연결.
#    현재는 event_type별 고정 테이블 — 향후 DB에서 로드
# ═════════════════════════════════════════════════════════════════════════════

# TODO: DB 연동 시 아래 테이블을 DB 조회로 교체
DIM_NUM_TO_ID_BY_EVENT_TYPE = {
    "weather_climate::summer_heat_wave": {
        1: "duration_months",
        2: "temperature_anomaly",
        3: "affected_region_scope",
        4: "storage_injection_pace",     # 미선택 dim
        5: "cooling_power_demand_increase",
        6: "spot_price_spike",           # 미선택 dim
    },
    "weather_climate::winter_cold_wave": {
        1: "duration_months",
        2: "temperature_anomaly",
        3: "affected_region_scope",
        4: "storage_drawdown_impact",
        5: "heating_demand_increase",
        6: "spot_price_spike",
    },
    "geopolitical_risk::war_conflict": {
        1: "conflict_duration",
        2: "escalation_level",
        3: "strait_route_impact",
        4: "lng_facility_damage",
        5: "oil_production_disruption",
        6: "sanction_scope",
        7: "supply_response",
        8: "risk_premium",
    },
}


# ═════════════════════════════════════════════════════════════════════════════
# 9. 메인 실행
# ═════════════════════════════════════════════════════════════════════════════

def run(
    sample_event_path: str,
    stage_result_path: str,
    mapping_excel_path: str,
    output_path: str,
) -> None:
    with open(sample_event_path, encoding="utf-8") as f:
        base_event = json.load(f)
    with open(stage_result_path, encoding="utf-8") as f:
        stage_result = json.load(f)

    l1_code = base_event["event_type"]["level_1_code"]
    l2_code = base_event["event_type"]["level_2_code"]
    event_type_id = f"{l1_code}::{l2_code}"

    # 매핑 엑셀 로드
    xl = pd.ExcelFile(mapping_excel_path)

    # 00.시트별Params 파싱
    param_master = parse_param_master(xl)
    print(f"  param_master 로드: {len(param_master)}개 parameter")

    # event_type 매핑 파싱
    dim_map = parse_event_type_mapping(xl, l1_code, l2_code, param_master)
    print(f"  dim_map 로드: {len(dim_map)}개 Dim (event_type={event_type_id})")

    # Dim 번호 ↔ dimension_id 매핑
    dim_num_to_id = DIM_NUM_TO_ID_BY_EVENT_TYPE.get(event_type_id, {})
    if not dim_num_to_id:
        raise ValueError(f"DIM_NUM_TO_ID_BY_EVENT_TYPE에 '{event_type_id}' 없음. 추가 필요.")

    stage2    = stage_result["stage2_dimension_selection"]
    scenarios = stage_result["stage4_scenario_synthesis"]["scenarios"]

    model_inputs = []
    for scenario in scenarios:
        mi = build_model_input(
            scenario, base_event, stage2, dim_map, dim_num_to_id, param_master
        )
        model_inputs.append(mi)

        sid = scenario["scenario_id"]
        print(f"\n{'─'*60}")
        print(f"  {sid}  {scenario['title'][:40]}")
        for pd_entry in mi["proposed_dims"]:
            role_tag = "INDIRECT" if pd_entry["role"] == "indirect" else "DIRECT "
            print(f"    [{role_tag}] {pd_entry['dim_id']} = {pd_entry['enum_value_id']}")
            for c in pd_entry["parameter_candidates_summary"]:
                tag = ("✅ selected" if c["selected"]
                       else ("🚫 blocked " if c["blocked"] else "   skipped "))
                print(f"             {tag}  "
                      f"{c['model_file']}.{c['model_sheet']}.{c['parameter_name']}")
        params = mi["input_parameters"]
        print(f"    → input_parameters: {[p['parameter_name'] for p in params]}")

    output = {
        "pipeline_version": "vShare01c",
        "mapping_source":   mapping_excel_path,
        "base_event_id":    base_event["mi_event_id"],
        "event_type":       event_type_id,
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "model_inputs":     model_inputs,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n\n총 {len(model_inputs)}개 ModelInput → {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Usage: python param_pipeline_v4.py "
            "<sample_event.json> <stage_result.json> "
            "<mapping_excel.xlsx> <output.json>"
        )
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
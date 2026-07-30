import type { ApiCallRecord } from "./apiCall";

export function isMixedContentRequest(
  agentBaseUrl: string,
  pageProtocol: string
): boolean {
  if (pageProtocol !== "https:") return false;
  try {
    return new URL(agentBaseUrl).protocol === "http:";
  } catch {
    return false;
  }
}

export function connectionFailureGuidance(record: ApiCallRecord): string {
  switch (record.transportStatus) {
    case "success":
      return "Agent가 HTTP 200으로 응답했지만 API body가 실패를 나타냅니다. 응답 message와 Agent 로그를 확인하세요.";
    case "http-error":
      return `HTTP ${record.httpStatus ?? "오류"}: Agent가 응답했습니다. URL, 인증값, 서버 로그를 확인하세요.`;
    case "network-error":
      return "Network/CORS 오류: Agent URL 접근성과 CORS allowed origin 설정을 확인하세요.";
    case "timeout":
      return "연결 확인이 timeout되었습니다. Agent 상태와 timeout 설정을 확인하세요.";
    case "parse-error":
      return "Agent 응답을 JSON으로 해석하지 못했습니다. Base URL과 ingress 경로를 확인하세요.";
    case "abort":
      return "연결 확인이 취소되었습니다.";
    default:
      return record.error || "Agent 연결에 실패했습니다.";
  }
}

export const MIXED_CONTENT_GUIDANCE =
  "Mixed content 차단: HTTPS frontend에서는 HTTP Agent를 호출할 수 없습니다. Agent를 HTTPS로 제공하거나 동일한 보안 scheme을 사용하세요.";

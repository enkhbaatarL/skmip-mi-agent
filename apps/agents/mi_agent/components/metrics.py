class Metrics:
    @staticmethod
    def observe(
        step: str, tenant: str, ok: bool, dur_s: float, extra: dict | None = None
    ):
        # TODO: OpenTelemetry/로그 연결
        pass

from apps.agents.mi_agent.components.policies import SearchPolicySet


_SEARCH_POLICIES: SearchPolicySet | None = None


def get_search_policies() -> SearchPolicySet:
    if _SEARCH_POLICIES is None:
        msg = "SearchPolicySet 미초기화: ensure_ready에서 set_search_policies(...) 필요"
        raise RuntimeError(msg)
    return _SEARCH_POLICIES


def set_search_policies(policies: SearchPolicySet) -> None:
    global _SEARCH_POLICIES
    _SEARCH_POLICIES = policies


def reset_search_policies() -> None:
    global _SEARCH_POLICIES
    _SEARCH_POLICIES = None

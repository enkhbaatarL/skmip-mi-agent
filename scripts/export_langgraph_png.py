from __future__ import annotations

from pathlib import Path

from apps.agents.mi_agent.flows.mari_agent_graph import get_mi_agent
from apps.agents.mi_agent.subgraphs.rdb_search.subgraph_builder import _rdb_subgraph
from apps.agents.mi_agent.subgraphs.vdb_search.subgraph_builder import _vdb_subgraph
from apps.agents.mi_agent.subgraphs.web_search.subgraph_builder import _web_subgraph


def _draw_png(compiled: object, name: str, out_dir: Path) -> None:
    g = compiled.get_graph()

    png_bytes = None
    for method_name in ("draw_png", "draw_mermaid_png", "render_png"):
        if hasattr(g, method_name):
            png_bytes = getattr(g, method_name)()
            break

    if png_bytes is None:
        available = [m for m in dir(g) if "png" in m.lower() or "draw" in m.lower() or "render" in m.lower()]
        raise RuntimeError(
            f"[{name}] LangGraph PNG 렌더 메서드를 찾지 못했습니다.\n"
            f"시도한 메서드: draw_png / draw_mermaid_png / render_png\n"
            f"사용 가능한 유사 메서드: {available}"
        )

    out_path = out_dir / f"{name}.png"
    out_path.write_bytes(png_bytes)
    print(f"✅ saved: {out_path.resolve()}")


def main() -> None:
    out_dir = Path("docs")
    out_dir.mkdir(parents=True, exist_ok=True)

    graphs = [
        (get_mi_agent(), "mi_agent_flow"),
        (_rdb_subgraph, "rdb_search_flow"),
        (_vdb_subgraph, "vdb_search_flow"),
        (_web_subgraph, "web_search_flow"),
    ]

    for compiled, name in graphs:
        _draw_png(compiled, name, out_dir)


if __name__ == "__main__":
    main()

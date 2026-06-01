from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, END, StateGraph

from core.storage.file_checkpointer import FileCheckpointer
from modules.hitl_manager import apply_human_edit as apply_human_edit_payload
from modules.scenario_engine import generate_scenario_state_from_event, load_event
from modules.signpost_binder import attach_signposts


class PipelineState(TypedDict, total=False):
    thread_id: str
    event_input_path: str
    event_data: dict[str, Any]
    scenario_state: dict[str, Any]
    draft_state: dict[str, Any]
    human_edited_state: dict[str, Any]
    final_state: dict[str, Any]
    draft_path: str
    final_path: str
    delete_scenario_ids: list[str]
    add_scenario: bool
    phase: str


def _parse_branch_node(state: PipelineState) -> PipelineState:
    event_data = state.get("event_data")
    if event_data is not None:
        return {"event_data": event_data, "phase": "parse_branch"}
    path = state.get("event_input_path")
    if not path:
        raise ValueError("event_input_path is required when event_data is missing.")
    return {
        "event_data": load_event(Path(path)),
        "phase": "parse_branch",
    }


def _dimension_matrix_node(state: PipelineState) -> PipelineState:
    scenario_state = state.get("scenario_state")
    if scenario_state is None:
        event_data = state.get("event_data")
        if event_data is None:
            raise ValueError("event_data is required before dimension_matrix.")
        scenario_state = generate_scenario_state_from_event(event_data)
    return {"scenario_state": scenario_state, "phase": "dimension_matrix"}


def _save_draft_node(state: PipelineState, *, file_checkpointer: FileCheckpointer) -> PipelineState:
    scenario_state = state.get("scenario_state")
    if scenario_state is None:
        raise ValueError("scenario_state is required before save_draft.")

    thread_id = state.get("thread_id")
    if not thread_id:
        raise ValueError("thread_id is required.")

    draft_state = scenario_state
    draft_out = file_checkpointer.save_draft(thread_id, draft_state, state.get("draft_path"))
    file_checkpointer.save_graph_state(
        thread_id=thread_id,
        phase="interrupt_ready",
        state={**state, "draft_state": draft_state, "draft_path": str(draft_out)},
    )
    return {
        "draft_state": draft_state,
        "draft_path": str(draft_out),
        "phase": "save_draft",
    }


def _apply_human_edit_node(state: PipelineState) -> PipelineState:
    draft_state = state.get("draft_state")
    human_edited_state = state.get("human_edited_state")
    if draft_state is None:
        raise ValueError("draft_state is required before applying HITL edits.")
    if human_edited_state is None:
        raise ValueError("human_edited_state is required to resume from interrupt.")
    final_state = apply_human_edit_payload(
        draft_state,
        human_edited_state,
        delete_scenario_ids=set(state.get("delete_scenario_ids") or []),
        add_scenario=bool(state.get("add_scenario")),
    )
    return {"final_state": final_state, "phase": "apply_human_edit"}


def _signpost_attacher_node(state: PipelineState) -> PipelineState:
    final_state = state.get("final_state")
    if final_state is None:
        raise ValueError("final_state is required before signpost_attacher.")
    signpost_attached_state = attach_signposts(final_state)
    return {"final_state": signpost_attached_state, "phase": "signpost_attacher"}


def _save_final_node(state: PipelineState, *, file_checkpointer: FileCheckpointer) -> PipelineState:
    final_state = state.get("final_state")
    if final_state is None:
        raise ValueError("final_state is required before save_final.")
    thread_id = state.get("thread_id")
    if not thread_id:
        raise ValueError("thread_id is required.")
    final_out = file_checkpointer.save_final(thread_id, final_state, state.get("final_path"))
    file_checkpointer.save_graph_state(
        thread_id=thread_id,
        phase="completed",
        state={**state, "final_state": final_state, "final_path": str(final_out)},
    )
    return {"final_path": str(final_out), "phase": "save_final"}


def build_pipeline_app(file_checkpointer: FileCheckpointer):
    graph = StateGraph(PipelineState)
    graph.add_node("parse_branch", _parse_branch_node)
    graph.add_node("dimension_matrix", _dimension_matrix_node)
    graph.add_node(
        "save_draft",
        lambda state: _save_draft_node(state, file_checkpointer=file_checkpointer),
    )
    graph.add_node(
        "apply_human_edit",
        _apply_human_edit_node,
    )
    graph.add_node(
        "signpost_attacher",
        _signpost_attacher_node,
    )
    graph.add_node(
        "save_final",
        lambda state: _save_final_node(state, file_checkpointer=file_checkpointer),
    )

    graph.add_edge(START, "parse_branch")
    graph.add_edge("parse_branch", "dimension_matrix")
    graph.add_edge("dimension_matrix", "save_draft")
    graph.add_edge("save_draft", "apply_human_edit")
    graph.add_edge("apply_human_edit", "signpost_attacher")
    graph.add_edge("signpost_attacher", "save_final")
    graph.add_edge("save_final", END)

    return graph.compile(
        checkpointer=InMemorySaver(),
        interrupt_before=["apply_human_edit"],
    )

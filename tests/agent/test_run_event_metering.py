from datetime import datetime
from types import SimpleNamespace

from agent.agent_runtime_helpers import meter_run_event_payload


def _agent():
    return SimpleNamespace(
        model="deepseek/deepseek-v4-pro",
        session_input_tokens=12500,
        session_output_tokens=4200,
        session_reasoning_tokens=1800,
        session_actual_cost_usd=0.71,
        session_subagent_cost_records=[
            {"name": "etsy", "model": "deepseek/deepseek-v4-flash",
             "input_tokens": 8000, "output_tokens": 2000, "reasoning_tokens": 0,
             "cost_usd": 0.10},
            {"name": "pinterest", "model": "deepseek/deepseek-v4-flash",
             "input_tokens": 8000, "output_tokens": 2000, "reasoning_tokens": 0,
             "cost_usd": 0.17},
        ],
    )


def _valid_z_timestamp(ts: str) -> bool:
    assert ts.endswith("Z")
    datetime.fromisoformat(ts.replace("Z", "+00:00"))  # raises if malformed
    return True


def test_run_completed_event_gets_metered_cost_and_timestamp():
    args = {"event": {
        "timestamp": "2026-05-29T19:00:00Z",   # LLM-fabricated
        "event_type": "run_completed",
        "agent": "scout", "pipeline": "pod",
        "cost_usd": 0.018,                       # LLM-authored garbage
    }}
    meter_run_event_payload(_agent(), "emit_run_event", args)
    ev = args["event"]
    assert _valid_z_timestamp(ev["timestamp"])
    assert ev["timestamp"] != "2026-05-29T19:00:00Z"
    self_cost = ev["cost_breakdown"]["self"]["cost_usd"]
    subs = ev["cost_breakdown"]["sub_agents"]
    assert self_cost == 0.71
    assert [s["name"] for s in subs] == ["etsy", "pinterest"]
    # rollup consistency (the cipher-mcp consumer enforces this within 1e-6)
    assert abs(ev["cost_usd"] - (self_cost + sum(s["cost_usd"] for s in subs))) < 1e-6
    assert abs(ev["cost_usd"] - 0.98) < 1e-6
    assert ev["cost_breakdown"]["self"]["input_tokens"] == 12500


def test_non_cost_event_strips_cost_keeps_timestamp():
    args = {"event": {
        "timestamp": "2026-05-29T19:00:00Z",
        "event_type": "scan_summary",
        "agent": "scout", "pipeline": "pod",
        "cost_usd": 0.018, "cost_breakdown": {"self": {}, "sub_agents": []},
    }}
    meter_run_event_payload(_agent(), "emit_run_event", args)
    ev = args["event"]
    assert _valid_z_timestamp(ev["timestamp"])
    assert "cost_usd" not in ev
    assert "cost_breakdown" not in ev


def test_other_tools_are_untouched():
    args = {"event": {"event_type": "run_completed", "cost_usd": 0.018}}
    meter_run_event_payload(_agent(), "write_file", args)
    assert args["event"]["cost_usd"] == 0.018  # not emit_run_event -> no-op


def test_cost_event_type_is_also_metered():
    # cost_event is the other cost-bearing type in _COST_EVENT_TYPES — it must
    # get a populated cost_breakdown too, not just run_completed.
    args = {"event": {
        "timestamp": "2026-05-29T19:00:00Z",
        "event_type": "cost_event",
        "agent": "scout", "pipeline": "pod",
    }}
    meter_run_event_payload(_agent(), "emit_run_event", args)
    ev = args["event"]
    assert _valid_z_timestamp(ev["timestamp"])
    assert ev["cost_breakdown"]["self"]["cost_usd"] == 0.71
    assert [s["name"] for s in ev["cost_breakdown"]["sub_agents"]] == ["etsy", "pinterest"]
    assert abs(ev["cost_usd"] - 0.98) < 1e-6


def test_no_subagents_top_equals_self():
    # A single-agent run (no delegations) — top-level cost_usd must equal self,
    # sub_agents must be empty.
    agent = _agent()
    agent.session_subagent_cost_records = []
    args = {"event": {
        "timestamp": "2026-05-29T19:00:00Z",
        "event_type": "run_completed",
        "agent": "scout", "pipeline": "pod",
    }}
    meter_run_event_payload(agent, "emit_run_event", args)
    ev = args["event"]
    assert ev["cost_breakdown"]["sub_agents"] == []
    assert ev["cost_breakdown"]["self"]["cost_usd"] == 0.71
    assert ev["cost_usd"] == 0.71

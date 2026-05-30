"""The actual-cost metering fields must be reset by reset_session_state so a
/clear or /new session never carries stale cost into the next run."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.modules.setdefault("fire", types.SimpleNamespace(Fire=lambda *a, **k: None))
sys.modules.setdefault("firecrawl", types.SimpleNamespace(Firecrawl=object))
sys.modules.setdefault("fal_client", types.SimpleNamespace())

from run_agent import AIAgent


def _make_minimal_agent() -> AIAgent:
    agent = AIAgent.__new__(AIAgent)  # skip __init__
    # Attributes reset_session_state() writes today:
    agent.session_total_tokens = 0
    agent.session_input_tokens = 0
    agent.session_output_tokens = 0
    agent.session_prompt_tokens = 0
    agent.session_completion_tokens = 0
    agent.session_cache_read_tokens = 0
    agent.session_cache_write_tokens = 0
    agent.session_reasoning_tokens = 0
    agent.session_api_calls = 0
    agent.session_estimated_cost_usd = 0.0
    agent.session_cost_status = "unknown"
    agent.session_cost_source = "none"
    agent._user_turn_count = 0
    agent.context_compressor = None
    return agent


def test_actual_cost_fields_reset_to_empty():
    agent = _make_minimal_agent()
    # Simulate state accumulated in a previous session
    agent.session_actual_cost_usd = 1.27
    agent.session_actual_cost_calls = 9
    agent.session_subagent_cost_records = [{"name": "etsy", "cost_usd": 0.22}]

    agent.reset_session_state()

    assert agent.session_actual_cost_usd == 0.0
    assert agent.session_actual_cost_calls == 0
    assert agent.session_subagent_cost_records == []

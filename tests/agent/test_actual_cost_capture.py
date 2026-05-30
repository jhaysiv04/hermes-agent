from types import SimpleNamespace

from agent.usage_pricing import accumulate_actual_cost


def _agent():
    return SimpleNamespace(session_actual_cost_usd=0.0, session_actual_cost_calls=0)


def test_accumulates_actual_cost_when_present():
    agent = _agent()
    accumulate_actual_cost(agent, SimpleNamespace(cost=0.0123))
    accumulate_actual_cost(agent, SimpleNamespace(cost=0.0077))
    assert abs(agent.session_actual_cost_usd - 0.02) < 1e-9
    assert agent.session_actual_cost_calls == 2


def test_no_cost_field_is_a_noop():
    agent = _agent()
    accumulate_actual_cost(agent, SimpleNamespace(prompt_tokens=10))  # no .cost
    assert agent.session_actual_cost_usd == 0.0
    assert agent.session_actual_cost_calls == 0


def test_none_usage_is_a_noop():
    agent = _agent()
    accumulate_actual_cost(agent, None)
    assert agent.session_actual_cost_usd == 0.0
    assert agent.session_actual_cost_calls == 0


def test_non_numeric_cost_is_ignored():
    agent = _agent()
    accumulate_actual_cost(agent, SimpleNamespace(cost="oops"))
    assert agent.session_actual_cost_usd == 0.0
    assert agent.session_actual_cost_calls == 0


def test_zero_cost_is_counted_as_a_call():
    # A real reported cost of exactly 0.0 (free-tier / fully-cached call) is a
    # genuine provider report: it counts as a call and adds 0.0 to the total.
    agent = _agent()
    accumulate_actual_cost(agent, SimpleNamespace(cost=0.0))
    assert agent.session_actual_cost_usd == 0.0
    assert agent.session_actual_cost_calls == 1

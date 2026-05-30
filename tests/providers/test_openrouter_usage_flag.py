"""The OpenRouter profile must request usage accounting so responses carry
the ground-truth usage.cost field (used by the run-event metering adapter)."""
from providers import get_provider_profile


def test_openrouter_build_extra_body_requests_usage_accounting():
    profile = get_provider_profile("openrouter")
    assert profile is not None, "openrouter provider profile must be discoverable"
    body = profile.build_extra_body()
    assert body.get("usage") == {"include": True}, (
        f"expected usage accounting flag in extra_body; got {body!r}"
    )


def test_usage_flag_coexists_with_provider_preferences():
    profile = get_provider_profile("openrouter")
    body = profile.build_extra_body(provider_preferences={"order": ["anthropic"]})
    assert body.get("usage") == {"include": True}
    assert body.get("provider") == {"order": ["anthropic"]}

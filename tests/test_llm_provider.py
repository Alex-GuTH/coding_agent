from typing import runtime_checkable

from safe_test_repair_harness.llm import LLMProvider, MockLLMProvider, RealLLMProvider


def test_mock_provider_returns_scripted_actions_in_order():
    provider = MockLLMProvider(
        [
            '{"type":"read_file","path":"src/app.py"}',
            '{"type":"finish","reason":"done"}',
        ]
    )

    first = provider.generate({"iteration": 0})
    second = provider.generate({"iteration": 1})

    assert first.ok is True
    assert first.text == '{"type":"read_file","path":"src/app.py"}'
    assert first.error_code is None
    assert first.metadata["script_index"] == 0
    assert second.ok is True
    assert second.text == '{"type":"finish","reason":"done"}'
    assert second.metadata["script_index"] == 1


def test_mock_provider_exhaustion_is_deterministic():
    provider = MockLLMProvider(['{"type":"finish"}'])

    provider.generate({})
    exhausted = provider.generate({})
    exhausted_again = provider.generate({})

    assert exhausted.ok is False
    assert exhausted.text == ""
    assert exhausted.error_code == "mock_script_exhausted"
    assert exhausted.message == "MockLLMProvider script exhausted"
    assert exhausted.metadata["provider"] == "mock"
    assert exhausted_again.to_dict() == exhausted.to_dict()


def test_provider_metadata_marks_mock():
    provider = MockLLMProvider(['{"type":"finish"}'])

    assert isinstance(provider, LLMProvider)
    assert provider.metadata() == {"provider": "mock", "script_length": 1}
    result = provider.generate({})
    assert result.metadata["provider"] == "mock"


def test_real_provider_without_key_does_not_affect_mock_tests(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    real_provider = RealLLMProvider(provider_name="openai", model="example-model")
    real_result = real_provider.generate({"prompt": "hello"})
    mock_result = MockLLMProvider(['{"type":"finish"}']).generate({})

    assert real_result.ok is False
    assert real_result.error_code == "missing_api_key"
    assert real_result.metadata == {
        "provider": "openai",
        "model": "example-model",
        "network": "disabled",
    }
    assert mock_result.ok is True
    assert mock_result.metadata["provider"] == "mock"

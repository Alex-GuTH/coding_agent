import json

from safe_test_repair_harness.action_parser import ActionParser
from safe_test_repair_harness.models import Action, ToolObservation


def test_parse_valid_read_file_action():
    result = ActionParser().parse('{"type":"read_file","path":"src/app.py"}')

    assert result.status == "ok"
    assert isinstance(result.action, Action)
    assert result.action.type == "read_file"
    assert result.action.path == "src/app.py"
    assert result.observation is None
    assert not hasattr(result.action, "name")


def test_invalid_json_returns_parse_error():
    result = ActionParser().parse("{not json")

    assert result.status == "parse_error"
    assert result.action is None
    assert result.error_code == "invalid_json"
    assert result.observation.status == "parse_error"
    assert result.observation.error_code == "invalid_json"


def test_missing_action_type_returns_parse_error():
    result = ActionParser().parse('{"path":"src/app.py"}')

    assert result.status == "parse_error"
    assert result.action is None
    assert result.error_code == "missing_action_type"
    assert result.observation.error_code == "missing_action_type"


def test_parameter_type_error_returns_parse_error():
    result = ActionParser().parse('{"type":"read_file","path":["src/app.py"]}')

    assert result.status == "parse_error"
    assert result.action is None
    assert result.error_code == "parameter_type_error"
    assert result.observation.error_code == "parameter_type_error"


def test_unknown_action_returns_unsupported_action():
    result = ActionParser().parse('{"type":"delete_everything","path":"src/app.py"}')

    assert result.status == "unsupported_action"
    assert result.action is None
    assert result.error_code == "unsupported_action"
    assert result.observation.status == "unsupported_action"
    assert result.observation.data["action_type"] == "delete_everything"


def test_apply_patch_returns_unsupported_action_in_mvp():
    result = ActionParser().parse('{"type":"apply_patch","patch":"*** Begin Patch\\n*** End Patch"}')

    assert result.status == "unsupported_action"
    assert result.action is None
    assert result.error_code == "unsupported_action"
    assert result.observation.status == "unsupported_action"
    assert result.observation.data["action_type"] == "apply_patch"


def test_parse_error_and_unsupported_action_are_loggable_observations():
    parse_error = ActionParser().parse("{not json")
    unsupported = ActionParser().parse('{"type":"apply_patch","patch":"ignored"}')

    for result in [parse_error, unsupported]:
        assert isinstance(result.observation, ToolObservation)
        observation_json = result.observation.to_json()
        decoded = json.loads(observation_json)

        assert decoded["tool"] == "action_parser"
        assert decoded["status"] in {"parse_error", "unsupported_action"}
        assert decoded["error_code"] in {"invalid_json", "unsupported_action"}
        assert decoded["feedback"]["status"] == decoded["status"]
        assert "raw_response" in decoded["metadata"]

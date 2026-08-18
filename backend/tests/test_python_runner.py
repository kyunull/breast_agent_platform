import pytest

from app.runtime.python_runner import RestrictedCodeError, RestrictedPythonRunner, RunnerError


def test_runner_executes_structured_rule_with_inputs():
    result = RestrictedPythonRunner().run(
        """
result = {
    'high_risk': age >= 50,
    'name': name.strip(),
}
""",
        {"age": 52, "name": "  Alice  "},
    )
    assert result == {"high_risk": True, "name": "Alice"}


def test_runner_rejects_import_and_private_attribute():
    runner = RestrictedPythonRunner()
    with pytest.raises(RestrictedCodeError):
        runner.run("import os\nresult = {'x': 1}", {})
    with pytest.raises(RestrictedCodeError):
        runner.run("result = inputs.__class__", {})


def test_runner_times_out_infinite_loop():
    with pytest.raises(RunnerError, match="timed out"):
        RestrictedPythonRunner().run("while True:\n    pass", {}, timeout_seconds=0.1)


def test_runner_supports_chinese_output_box_and_rejects_non_json_result():
    result = RestrictedPythonRunner().run(
        "输出结果.result['出行方式'] = '步行'",
        {},
    )
    assert result == {"出行方式": "步行"}
    with pytest.raises(RunnerError, match="mapping"):
        RestrictedPythonRunner().run("result = 'not a mapping'", {})

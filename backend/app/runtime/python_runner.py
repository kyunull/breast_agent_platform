import ast
import json
import subprocess
import sys
from typing import Any


class RunnerError(RuntimeError):
    pass


class RestrictedCodeError(RunnerError):
    pass


_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "Exception": Exception,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "TypeError": TypeError,
    "ValueError": ValueError,
}


def _validate_ast(source: str) -> None:
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise RestrictedCodeError(f"invalid Python syntax: {exc}") from exc
    forbidden = (
        ast.AsyncFunctionDef,
        ast.AsyncWith,
        ast.AsyncFor,
        ast.ClassDef,
        ast.FunctionDef,
        ast.Import,
        ast.ImportFrom,
        ast.Lambda,
        ast.Try,
        ast.With,
        ast.Yield,
        ast.YieldFrom,
    )
    for node in ast.walk(tree):
        if isinstance(node, forbidden):
            raise RestrictedCodeError(f"forbidden Python construct: {type(node).__name__}")
        if isinstance(node, (ast.Name, ast.Attribute)):
            identifier = node.id if isinstance(node, ast.Name) else node.attr
            if identifier.startswith("__") or identifier in {
                "globals",
                "locals",
                "vars",
                "eval",
                "exec",
                "open",
            }:
                raise RestrictedCodeError(f"forbidden Python name: {identifier}")


class RestrictedPythonRunner:
    def __init__(self, *, max_output_chars: int = 100_000) -> None:
        self.max_output_chars = max_output_chars

    def run(
        self,
        source: str,
        inputs: dict[str, Any],
        timeout_seconds: float = 2.0,
    ) -> dict[str, Any]:
        _validate_ast(source)
        source_literal = json.dumps(source, ensure_ascii=False)
        inputs_literal = json.dumps(inputs, ensure_ascii=False, default=str)
        builtins_literal = "{" + ",".join(
            f"{name!r}: getattr(_builtins, {name!r})" for name in _SAFE_BUILTINS
        ) + "}"
        wrapper = f"""
import json
import builtins as _builtins
source = {source_literal}
inputs = json.loads({inputs_literal!r})
class OutputBox:
    def __init__(self):
        self.result = {{}}
namespace = {{"__builtins__": {builtins_literal}, "inputs": inputs, "输出结果": OutputBox()}}
for key, value in inputs.items():
    if isinstance(key, str) and key.isidentifier():
        namespace[key] = value
try:
    exec(compile(source, '<restricted-rule>', 'exec'), namespace, namespace)
    marker = object()
    value = namespace.get('result', marker)
    if value is marker:
        value = namespace.get('output', marker)
    if value is marker:
        value = namespace['输出结果'].result
    if not isinstance(value, dict):
        raise TypeError('rule result must be a mapping')
    print(json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str))
except Exception as exc:
    print(json.dumps({{"__runner_error__": str(exc)}}, ensure_ascii=False))
"""
        try:
            completed = subprocess.run(
                [sys.executable, "-c", wrapper],
                input="{}",
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=max(float(timeout_seconds), 0.01),
                check=False,
                env={"PYTHONIOENCODING": "utf-8"},
            )
        except subprocess.TimeoutExpired as exc:
            raise RunnerError("rule execution timed out") from exc
        output = completed.stdout.strip()
        if len(output) > self.max_output_chars:
            raise RunnerError("rule output exceeds configured limit")
        if not output:
            detail = completed.stderr.strip()[-500:]
            raise RunnerError(f"rule process returned no output{': ' + detail if detail else ''}")
        try:
            value = json.loads(output.splitlines()[-1])
        except json.JSONDecodeError as exc:
            raise RunnerError("rule process returned invalid JSON") from exc
        if isinstance(value, dict) and "__runner_error__" in value:
            raise RunnerError(str(value["__runner_error__"]))
        if not isinstance(value, dict):
            raise RunnerError("rule result must be a mapping")
        return value

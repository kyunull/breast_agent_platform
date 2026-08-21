from dataclasses import dataclass

import pytest

from app.extraction.schemas import ExtractionConfig
from app.graph.schemas import WorkflowGraph
from app.runtime.conditions import evaluate_condition
from app.runtime.context import ExecutionContext
from app.runtime.engine import WorkflowEngine
from app.runtime.executors import execute_node
from app.runtime.knowledge_gateway import EvidenceRecord
from app.runtime.model_gateway import ChatCompletionResult


def test_condition_uses_three_valued_logic_for_missing_values():
    context = ExecutionContext(raw_input={}, extracted={"facts": {"age": 52}}, run_id="run-1")
    assert evaluate_condition(
        {"operator": "gt", "left": "facts.age", "right": 50}, context
    ).status == "true"
    assert evaluate_condition(
        {"operator": "eq", "left": "facts.missing", "right": "x"}, context
    ).status == "unknown"
    assert evaluate_condition(
        {
            "operator": "and",
            "operands": [
                {"operator": "exists", "value": "facts.age"},
                {"operator": "eq", "left": "facts.age", "right": 52},
            ],
        },
        context,
    ).status == "true"


def test_condition_selects_configured_ports():
    context = ExecutionContext(raw_input={}, extracted={"facts": {"stage": "IV"}}, run_id="run-1")
    result = evaluate_condition(
        {
            "operator": "eq",
            "left": "facts.stage",
            "right": "IV",
            "true_port": "advanced",
            "false_port": "standard",
        },
        context,
    )
    assert result.selected_ports == ["advanced"]


def test_condition_supports_requested_comparison_operators():
    context = ExecutionContext(
        raw_input={},
        extracted={
            "facts": {
                "empty_text": "",
                "status": "HER2+",
                "age": 52,
                "tags": ["advanced", "reviewed"],
            }
        },
        run_id="run-operators",
    )
    cases = [
        ({"operator": "empty", "left": "facts.empty_text"}, "true"),
        ({"operator": "not_empty", "left": "facts.status"}, "true"),
        ({"operator": "eq", "left": "facts.age", "right": 52}, "true"),
        ({"operator": "neq", "left": "facts.age", "right": 51}, "true"),
        ({"operator": "gt", "left": "facts.age", "right": 50}, "true"),
        ({"operator": "lt", "left": "facts.age", "right": 60}, "true"),
        ({"operator": "gte", "left": "facts.age", "right": 52}, "true"),
        ({"operator": "lte", "left": "facts.age", "right": 52}, "true"),
        ({"operator": "contains", "left": "facts.tags", "right": "advanced"}, "true"),
    ]

    for config, expected in cases:
        assert evaluate_condition(config, context).status == expected


def test_condition_compares_numeric_field_with_editor_text_value():
    context = ExecutionContext(raw_input={}, extracted={"facts": {"age": 52}}, run_id="run-editor-value")

    assert evaluate_condition(
        {"operator": "gt", "left": "facts.age", "right": "50"}, context
    ).status == "true"


def test_condition_compares_boolean_field_with_editor_text_value():
    context = ExecutionContext(raw_input={}, extracted={"facts": {"eligible": True}}, run_id="run-editor-boolean")

    assert evaluate_condition(
        {"operator": "eq", "left": "facts.eligible", "right": "true"}, context
    ).status == "true"


def test_condition_group_short_circuits_to_one_of_two_ports():
    context = ExecutionContext(
        raw_input={},
        extracted={"facts": {"status": "HER2+", "age": 52}},
        run_id="run-group",
    )
    result = evaluate_condition(
        {
            "operator": "or",
            "operands": [
                {"operator": "empty", "left": "facts.status"},
                {"operator": "lt", "left": "facts.age", "right": 60},
            ],
            "true_port": "satisfied",
            "false_port": "unsatisfied",
        },
        context,
    )

    assert result.status == "true"
    assert result.selected_ports == ["satisfied"]


def test_condition_missing_strategy_routes_unknown_to_unsatisfied():
    context = ExecutionContext(raw_input={}, extracted={"facts": {}}, run_id="run-missing")
    result = evaluate_condition(
        {
            "operator": "not_empty",
            "left": "facts.missing",
            "missing_strategy": "false",
            "true_port": "satisfied",
            "false_port": "unsatisfied",
        },
        context,
    )

    assert result.status == "false"
    assert result.selected_ports == ["unsatisfied"]


def test_condition_missing_strategy_can_mark_review_or_stop():
    context = ExecutionContext(raw_input={}, extracted={"facts": {}}, run_id="run-missing")
    review = evaluate_condition(
        {
            "operator": "eq",
            "left": "facts.missing",
            "right": "x",
            "missing_strategy": "needs_review",
            "false_port": "unsatisfied",
        },
        context,
    )

    assert review.status == "needs_review"
    assert review.selected_ports == ["unsatisfied"]

    with pytest.raises(ValueError, match="condition value is unknown"):
        evaluate_condition(
            {
                "operator": "eq",
                "left": "facts.missing",
                "right": "x",
                "missing_strategy": "error",
            },
            context,
        )


def test_python_rule_uses_editor_field_contracts_for_inputs_and_outputs():
    context = ExecutionContext(
        raw_input={}, extracted={"facts": {"age": 52}}, run_id="run-field-contract"
    )

    result = execute_node(
        {
            "type": "python_rule",
            "config": {
                "code": "result = {'eligible': patient_age >= 50, 'ignored': 'value'}",
                "input_fields": [{"name": "patient_age", "path": "facts.age", "required": True}],
                "output_fields": [{"name": "is_eligible", "path": "eligible"}],
            },
        },
        context,
        {},
    )

    assert result.output == {"is_eligible": True}


def test_llm_uses_editor_input_aliases_and_projects_declared_outputs():
    model = FakeModel()
    context = ExecutionContext(
        raw_input={}, extracted={"facts": {"stage": "IV"}}, run_id="run-llm-contract"
    )

    result = execute_node(
        {
            "type": "llm",
            "config": {
                "prompt": "分期：{{stage}}",
                "input_fields": [{"name": "stage", "path": "facts.stage", "required": True}],
                "output_fields": [{"name": "recommendation", "path": "answer"}],
            },
        },
        context,
        {"model": model},
    )

    assert model.messages[0][-1]["content"] == "分期：IV"
    assert result.output == {"recommendation": "根据指南建议示例方案。"}


def test_input_and_output_nodes_apply_editor_field_contracts():
    context = ExecutionContext(
        raw_input={},
        extracted={"facts": {"age": 52, "stage": "IV"}},
        run_id="run-io-contract",
        node_outputs={"rule": {"eligible": True, "ignored": "value"}},
    )

    input_result = execute_node(
        {
            "type": "input",
            "config": {"output_fields": [{"name": "patient_age", "path": "facts.age"}]},
        },
        context,
        {},
    )
    output_result = execute_node(
        {
            "type": "output",
            "config": {"output_fields": [{"name": "is_eligible", "path": "rule.eligible"}]},
        },
        context,
        {},
    )

    assert input_result.output == {"patient_age": 52}
    assert output_result.output == {"is_eligible": True}


@dataclass
class FakeKnowledge:
    calls: list[str]

    def search(self, query, filters):
        self.calls.append(query)
        return [
            EvidenceRecord(
                evidence_id="ev-guideline-1",
                raw_chunk_id="chunk-1",
                text="HER2 阳性晚期乳腺癌首选方案是示例方案。",
                score=0.91,
                source_title="乳腺癌指南",
                guideline_id="caca",
                version_id="v1",
                locator="page 10",
                source_level="primary_guideline",
            )
        ]


class FakeModel:
    def __init__(self):
        self.messages = []

    def complete(self, profile, messages, response_format=None):
        self.messages.append(messages)
        return ChatCompletionResult(
            content='{"answer":"根据指南建议示例方案。"}',
            model="fake-model",
            usage={},
            finish_reason="stop",
            response_id="chat-1",
        )


def _runtime_graph():
    return WorkflowGraph.model_validate(
        {
            "nodes": [
                {
                    "id": "input",
                    "type": "input",
                    "name": "输入",
                    "output_ports": ["out"],
                },
                {
                    "id": "condition",
                    "type": "condition",
                    "name": "分期判断",
                    "input_ports": ["in"],
                    "output_ports": ["yes", "no", "unknown"],
                    "config": {
                        "operator": "gte",
                        "left": "facts.age",
                        "right": 50,
                        "true_port": "yes",
                        "false_port": "no",
                    },
                },
                {
                    "id": "rule",
                    "type": "python_rule",
                    "name": "规则",
                    "input_ports": ["in"],
                    "output_ports": ["out"],
                    "config": {"code": "result = {'eligible': True}"},
                },
                {
                    "id": "rag",
                    "type": "rag",
                    "name": "检索",
                    "input_ports": ["in"],
                    "output_ports": ["out"],
                    "config": {"query": "HER2 阳性晚期乳腺癌"},
                },
                {
                    "id": "llm",
                    "type": "llm",
                    "name": "模型",
                    "input_ports": ["in"],
                    "output_ports": ["out"],
                    "config": {
                        "prompt": "请根据检索证据给出结构化建议：{{rag.context_text}}",
                        "citation_required": True,
                        "output_schema": {"type": "object"},
                    },
                },
                {
                    "id": "output",
                    "type": "output",
                    "name": "输出",
                    "input_ports": ["in"],
                    "config": {"transfer_fields": ["llm.answer", "rag.evidence_refs"]},
                },
            ],
            "edges": [
                {"id": "e1", "source": "input", "target": "condition", "source_port": "out", "target_port": "in"},
                {"id": "e2", "source": "condition", "target": "rule", "source_port": "yes", "target_port": "in", "kind": "branch", "branch_label": "yes"},
                {"id": "e3", "source": "rule", "target": "rag", "source_port": "out", "target_port": "in"},
                {"id": "e4", "source": "rag", "target": "llm", "source_port": "out", "target_port": "in"},
                {"id": "e5", "source": "llm", "target": "output", "source_port": "out", "target_port": "in"},
            ],
        }
    )


def test_engine_runs_extraction_branch_rule_rag_llm_and_output():
    knowledge = FakeKnowledge([])
    model = FakeModel()
    traces = []
    result = WorkflowEngine(
        providers={"knowledge": knowledge, "model": model},
        trace_sink=traces.append,
    ).execute(
        _runtime_graph(),
        ExtractionConfig.model_validate(
            {
                "groups": [
                    {
                        "id": "facts",
                        "label": "事实",
                        "fields": [
                            {"alias": "age", "path": "$.patient.age", "type": "integer", "required": True}
                        ],
                    }
                ]
            }
        ),
        {"patient": {"age": 52}},
        run_id="run-1",
    )

    assert result.status == "succeeded"
    assert result.output == {"answer": "根据指南建议示例方案。", "evidence_refs": ["ev-guideline-1"]}
    assert knowledge.calls == ["HER2 阳性晚期乳腺癌"]
    assert model.messages
    assert "HER2 阳性" in model.messages[0][-1]["content"]
    assert any(trace["node_id"] == "rag" for trace in traces)
    assert result.evidence["ev-guideline-1"].source_title == "乳腺癌指南"


def test_engine_records_failed_node_and_stops_downstream():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                {"id": "input", "type": "input", "name": "输入", "output_ports": ["out"]},
                {"id": "rule", "type": "python_rule", "name": "失败规则", "input_ports": ["in"], "output_ports": ["out"], "config": {"code": "raise ValueError('bad')"}},
                {"id": "output", "type": "output", "name": "输出", "input_ports": ["in"]},
            ],
            "edges": [
                {"id": "e1", "source": "input", "target": "rule", "source_port": "out", "target_port": "in"},
                {"id": "e2", "source": "rule", "target": "output", "source_port": "out", "target_port": "in"},
            ],
        }
    )
    traces = []
    result = WorkflowEngine(trace_sink=traces.append).execute(
        graph,
        ExtractionConfig(groups=[]),
        {},
        run_id="run-2",
    )
    assert result.status == "failed"
    assert result.error["node_id"] == "rule"
    assert traces[-1]["status"] == "failed"


def test_engine_bounded_reassessment_does_not_run_forever():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                {"id": "input", "type": "input", "name": "输入", "output_ports": ["out"]},
                {"id": "rule", "type": "python_rule", "name": "规则", "input_ports": ["in"], "output_ports": ["out"], "config": {"code": "result = {'n': 1}"}},
                {"id": "output", "type": "output", "name": "输出", "input_ports": ["in"]},
            ],
            "edges": [
                {"id": "e1", "source": "input", "target": "rule", "source_port": "out", "target_port": "in"},
                {"id": "e2", "source": "rule", "target": "rule", "source_port": "out", "target_port": "in", "kind": "reassessment", "loop_policy": {"max_iterations": 2, "exit_condition": "never"}},
                {"id": "e3", "source": "rule", "target": "output", "source_port": "out", "target_port": "in"},
            ],
        }
    )
    result = WorkflowEngine().execute(graph, ExtractionConfig(groups=[]), {}, run_id="run-3")
    assert result.status == "succeeded"
    assert result.iterations["e2"] == 2


def test_engine_merges_after_skipping_an_unselected_branch():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                {"id": "input", "type": "input", "name": "输入", "output_ports": ["out"]},
                {
                    "id": "condition",
                    "type": "condition",
                    "name": "条件",
                    "input_ports": ["in"],
                    "output_ports": ["yes", "no"],
                    "config": {
                        "operator": "eq",
                        "left": "facts.stage",
                        "right": "IV",
                        "true_port": "yes",
                        "false_port": "no",
                    },
                },
                {
                    "id": "yes_rule",
                    "type": "python_rule",
                    "name": "命中分支",
                    "input_ports": ["in"],
                    "output_ports": ["out"],
                    "config": {"code": "result = {'branch': 'yes'}"},
                },
                {
                    "id": "no_rule",
                    "type": "python_rule",
                    "name": "未命中分支",
                    "input_ports": ["in"],
                    "output_ports": ["out"],
                    "config": {"code": "result = {'branch': 'no'}"},
                },
                {
                    "id": "output",
                    "type": "output",
                    "name": "汇合输出",
                    "input_ports": ["left", "right"],
                    "config": {"transfer_fields": ["yes_rule.branch"]},
                },
            ],
            "edges": [
                {"id": "e1", "source": "input", "target": "condition", "source_port": "out", "target_port": "in"},
                {"id": "e2", "source": "condition", "target": "yes_rule", "source_port": "yes", "target_port": "in", "kind": "branch", "branch_label": "yes"},
                {"id": "e3", "source": "condition", "target": "no_rule", "source_port": "no", "target_port": "in", "kind": "branch", "branch_label": "no"},
                {"id": "e4", "source": "yes_rule", "target": "output", "source_port": "out", "target_port": "left"},
                {"id": "e5", "source": "no_rule", "target": "output", "source_port": "out", "target_port": "right"},
            ],
        }
    )
    result = WorkflowEngine().execute(
        graph,
        ExtractionConfig.model_validate(
            {
                "groups": [
                    {
                        "id": "facts",
                        "label": "事实",
                        "fields": [{"alias": "stage", "path": "$.stage", "type": "string"}],
                    }
                ]
            }
        ),
        {"stage": "IV"},
    )
    assert result.output == {"branch": "yes"}
    assert "no_rule" not in result.node_outputs


def test_engine_runs_graphs_saved_with_frontend_input_output_ports():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                {"id": "input", "type": "input", "name": "输入", "output_ports": ["output"]},
                {"id": "output", "type": "output", "name": "输出", "input_ports": ["input"]},
            ],
            "edges": [
                {
                    "id": "edge",
                    "source": "input",
                    "target": "output",
                    "source_port": "output",
                    "target_port": "input",
                }
            ],
        }
    )

    result = WorkflowEngine().execute(
        graph,
        ExtractionConfig.model_validate(
            {
                "groups": [
                    {
                        "id": "facts",
                        "label": "事实",
                        "fields": [{"alias": "age", "path": "$.age", "type": "integer"}],
                    }
                ]
            }
        ),
        {"age": 52},
    )

    assert result.output == {"facts": {"age": 52}}

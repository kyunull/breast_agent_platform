import pytest

from app.graph.schemas import GraphValidationError, WorkflowGraph
from app.graph.validation import assert_valid_graph, validate_graph


def make_graph(edges):
    node_ids = {name for edge in edges for name in edge[:2]} | {"output"}
    node_types = {"input": "input", "output": "output", "condition": "condition", "task": "clinical_task"}
    nodes = [
        {
            "id": node_id,
            "type": node_types.get(node_id, "clinical_task"),
            "name": node_id,
            "input_ports": ["in"],
            "output_ports": ["out"],
        }
        for node_id in sorted(node_ids)
    ]
    edge_values = []
    for index, edge in enumerate(edges):
        options = edge[3] if len(edge) > 3 else {}
        edge_values.append(
            {
                "id": f"e-{index}",
                "source": edge[0],
                "target": edge[1],
                "kind": edge[2] if len(edge) > 2 else "normal",
                "branch_label": options.get("label"),
                "loop_policy": options if len(edge) > 2 and edge[2] == "reassessment" else None,
            }
        )
    return WorkflowGraph.model_validate({"nodes": nodes, "edges": edge_values})


def test_graph_rejects_normal_cycle():
    graph = make_graph([("input", "condition"), ("condition", "input")])
    issues = validate_graph(graph)
    assert any(issue.code == "normal_cycle" for issue in issues)


def test_graph_does_not_mark_cycle_downstream_as_cycle_member():
    graph = make_graph(
        [
            ("input", "condition"),
            ("condition", "task"),
            ("task", "condition"),
            ("condition", "output"),
        ]
    )
    issues = validate_graph(graph)
    cycle_nodes = {issue.node_id for issue in issues if issue.code == "normal_cycle"}
    assert cycle_nodes == {"condition", "task"}


def test_graph_allows_bounded_reassessment_cycle():
    graph = make_graph(
        [
            ("input", "condition"),
            ("condition", "task"),
            (
                "task",
                "condition",
                "reassessment",
                {"max_iterations": 2, "exit_condition": "资料足够"},
            ),
            ("condition", "output"),
        ]
    )
    assert validate_graph(graph) == []


def test_graph_preserves_multibranch_labels():
    graph = make_graph(
        [("input", "condition"), ("condition", "output", "branch", {"label": "证据不足"})]
    )
    assert graph.edges[1].branch_label == "证据不足"


def test_graph_reports_missing_endpoint_and_port():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                {"id": "input", "type": "input", "name": "输入", "output_ports": ["out"]},
                {"id": "output", "type": "output", "name": "输出", "input_ports": ["in"]},
            ],
            "edges": [
                {
                    "id": "bad-edge",
                    "source": "missing",
                    "target": "output",
                    "source_port": "wrong",
                    "target_port": "in",
                }
            ],
        }
    )
    issues = validate_graph(graph)
    assert {issue.code for issue in issues} >= {"missing_endpoint"}
    endpoint_issues = [issue for issue in issues if issue.code == "missing_endpoint"]
    assert endpoint_issues[0].edge_id == "bad-edge"


def test_graph_reports_missing_output_and_unreachable_node():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                {"id": "input", "type": "input", "name": "输入", "output_ports": ["out"]},
                {"id": "orphan", "type": "llm", "name": "孤立", "input_ports": ["in"], "output_ports": ["out"]},
            ],
            "edges": [],
        }
    )
    issues = validate_graph(graph)
    assert any(issue.code == "missing_output" for issue in issues)
    assert any(issue.code == "unreachable_node" and issue.node_id == "orphan" for issue in issues)


def test_graph_rejects_invalid_loop_policy():
    with pytest.raises(ValueError):
        WorkflowGraph.model_validate(
            {
                "nodes": [],
                "edges": [
                    {
                        "id": "loop",
                        "source": "a",
                        "target": "b",
                        "kind": "reassessment",
                        "loop_policy": {"max_iterations": 11, "exit_condition": ""},
                    }
                ],
            }
        )


def test_assert_valid_graph_raises_structured_error():
    graph = make_graph([("input", "output")])
    assert_valid_graph(graph)

    invalid = WorkflowGraph.model_validate(
        {
            "nodes": [{"id": "input", "type": "input", "name": "输入"}],
            "edges": [],
        }
    )
    with pytest.raises(GraphValidationError) as error:
        assert_valid_graph(invalid)
    assert error.value.issues

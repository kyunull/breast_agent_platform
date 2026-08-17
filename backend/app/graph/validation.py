from collections import defaultdict, deque

from app.graph.schemas import GraphIssue, GraphValidationError, WorkflowGraph


def _issue(code: str, message: str, *, node_id: str | None = None, edge_id: str | None = None) -> GraphIssue:
    return GraphIssue(code=code, message=message, node_id=node_id, edge_id=edge_id)


def _cycle_nodes(adjacency: dict[str, set[str]], node_ids: set[str]) -> set[str]:
    colors = {node_id: 0 for node_id in node_ids}
    stack: list[str] = []
    stack_positions: dict[str, int] = {}
    cycles: set[str] = set()

    def visit(node_id: str) -> None:
        colors[node_id] = 1
        stack_positions[node_id] = len(stack)
        stack.append(node_id)
        for target in adjacency.get(node_id, set()):
            if target not in colors:
                continue
            if colors[target] == 0:
                visit(target)
            elif colors[target] == 1:
                cycles.update(stack[stack_positions[target] :])
        stack.pop()
        stack_positions.pop(node_id, None)
        colors[node_id] = 2

    for node_id in sorted(node_ids):
        if colors[node_id] == 0:
            visit(node_id)
    return cycles


def validate_graph(graph: WorkflowGraph) -> list[GraphIssue]:
    issues: list[GraphIssue] = []
    node_by_id = {}
    duplicate_ids: set[str] = set()
    for node in graph.nodes:
        if node.id in node_by_id:
            duplicate_ids.add(node.id)
        node_by_id[node.id] = node
    for node_id in sorted(duplicate_ids):
        issues.append(_issue("duplicate_node_id", f"duplicate node id: {node_id}", node_id=node_id))

    input_ids = {node.id for node in graph.nodes if node.type == "input"}
    output_ids = {node.id for node in graph.nodes if node.type == "output"}
    if not input_ids:
        issues.append(_issue("missing_input", "workflow must contain an input node"))
    if not output_ids:
        issues.append(_issue("missing_output", "workflow must contain an output node"))

    normal_adjacency: dict[str, set[str]] = defaultdict(set)
    all_adjacency: dict[str, set[str]] = defaultdict(set)
    reverse_adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        source = node_by_id.get(edge.source)
        target = node_by_id.get(edge.target)
        if source is None or target is None:
            issues.append(
                _issue(
                    "missing_endpoint",
                    f"edge {edge.id} references a missing node",
                    edge_id=edge.id,
                )
            )
            continue
        if edge.source_port not in source.output_ports:
            issues.append(
                _issue(
                    "invalid_source_port",
                    f"edge {edge.id} source port is not declared by {edge.source}",
                    node_id=edge.source,
                    edge_id=edge.id,
                )
            )
        if edge.target_port not in target.input_ports:
            issues.append(
                _issue(
                    "invalid_target_port",
                    f"edge {edge.id} target port is not declared by {edge.target}",
                    node_id=edge.target,
                    edge_id=edge.id,
                )
            )
        if target.id in input_ids:
            issues.append(_issue("input_has_incoming", "input nodes cannot have incoming edges", node_id=target.id, edge_id=edge.id))
        if source.id in output_ids:
            issues.append(_issue("output_has_outgoing", "output nodes cannot have outgoing edges", node_id=source.id, edge_id=edge.id))
        all_adjacency[source.id].add(target.id)
        reverse_adjacency[target.id].add(source.id)
        if edge.kind != "reassessment":
            normal_adjacency[source.id].add(target.id)

    node_ids = set(node_by_id)
    for node_id in sorted(_cycle_nodes(normal_adjacency, node_ids)):
        issues.append(_issue("normal_cycle", "workflow contains a cycle outside a bounded reassessment edge", node_id=node_id))

    reachable: set[str] = set(input_ids)
    queue = deque(input_ids)
    while queue:
        source = queue.popleft()
        for target in all_adjacency.get(source, set()):
            if target not in reachable:
                reachable.add(target)
                queue.append(target)
    for node_id in sorted(node_ids - reachable):
        issues.append(_issue("unreachable_node", "node is not reachable from an input", node_id=node_id))

    can_reach_output: set[str] = set(output_ids)
    queue = deque(output_ids)
    while queue:
        target = queue.popleft()
        for source in reverse_adjacency.get(target, set()):
            if source not in can_reach_output:
                can_reach_output.add(source)
                queue.append(source)
    for node_id in sorted(node_ids - can_reach_output):
        issues.append(_issue("dead_end_node", "node cannot reach an output", node_id=node_id))

    return issues


def assert_valid_graph(graph: WorkflowGraph) -> None:
    issues = validate_graph(graph)
    if issues:
        raise GraphValidationError(issues)

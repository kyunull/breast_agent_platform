import time
from collections import defaultdict, deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.extraction.schemas import ExtractionConfig
from app.extraction.service import preview_extraction
from app.graph.schemas import EdgeSpec, WorkflowGraph
from app.graph.validation import assert_valid_graph
from app.runtime.conditions import MISSING, resolve_value
from app.runtime.context import ExecutionContext
from app.runtime.executors import execute_node
from app.runtime.knowledge_gateway import EvidenceRecord


@dataclass
class ExecutionResult:
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    node_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    evidence: dict[str, EvidenceRecord] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    iterations: dict[str, int] = field(default_factory=dict)


class WorkflowEngine:
    def __init__(
        self,
        *,
        providers: Mapping[str, Any] | None = None,
        trace_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.providers = providers or {}
        self.trace_sink = trace_sink

    @staticmethod
    def _selected(edge: EdgeSpec, selected_ports: list[str]) -> bool:
        return edge.source_port in selected_ports

    @staticmethod
    def _exit_condition(expression: str, context: ExecutionContext) -> bool:
        normalized = expression.strip().lower()
        if normalized in {"never", "false", "0", "no"}:
            return False
        if normalized in {"always", "true", "1", "yes"}:
            return True
        value = resolve_value(expression, context)
        return value is not MISSING and bool(value)

    def execute(
        self,
        graph: WorkflowGraph | dict[str, Any],
        extraction: ExtractionConfig | dict[str, Any],
        raw_input: dict[str, Any],
        *,
        run_id: str = "local-run",
    ) -> ExecutionResult:
        graph = graph if isinstance(graph, WorkflowGraph) else WorkflowGraph.model_validate(graph)
        extraction = (
            extraction
            if isinstance(extraction, ExtractionConfig)
            else ExtractionConfig.model_validate(extraction)
        )
        assert_valid_graph(graph)
        extracted = preview_extraction(raw_input, extraction).groups
        context = ExecutionContext(raw_input=raw_input, extracted=extracted, run_id=run_id)
        nodes = {node.id: node for node in graph.nodes}
        outgoing: dict[str, list[EdgeSpec]] = defaultdict(list)
        incoming: dict[str, list[EdgeSpec]] = defaultdict(list)
        for edge in graph.edges:
            outgoing[edge.source].append(edge)
            incoming[edge.target].append(edge)
        queue: deque[tuple[str, bool, str | None]] = deque(
            (node.id, False, None) for node in graph.nodes if node.type == "input"
        )
        processed: set[str] = set()
        enqueued: set[str] = {node.id for node in graph.nodes if node.type == "input"}
        active_edges: set[str] = set()
        iterations: dict[str, int] = defaultdict(int)
        final_output: dict[str, Any] = {}

        def emit(data: dict[str, Any]) -> None:
            if self.trace_sink is not None:
                self.trace_sink(data)

        while queue:
            node_id, repeat, parent_trace_id = queue.popleft()
            if node_id not in nodes or (node_id in processed and not repeat):
                continue
            node = nodes[node_id]
            started = time.perf_counter()
            try:
                result = execute_node(node, context, self.providers)
            except Exception as exc:  # noqa: BLE001 - persist every isolated node failure
                error = {"code": "node_execution_failed", "message": str(exc), "node_id": node_id}
                emit(
                    {
                        "node_id": node_id,
                        "parent_trace_id": parent_trace_id,
                        "status": "failed",
                        "error": error,
                        "duration_ms": int((time.perf_counter() - started) * 1000),
                    }
                )
                return ExecutionResult(
                    status="failed",
                    output=final_output,
                    node_outputs=context.node_outputs,
                    evidence=context.evidence,
                    error=error,
                    iterations=dict(iterations),
                )
            context.node_outputs[node_id] = result.output
            for evidence in result.evidence:
                context.evidence[evidence.evidence_id] = evidence
            emit(
                {
                    "node_id": node_id,
                    "parent_trace_id": parent_trace_id,
                    "status": result.status,
                    "output": result.output,
                    "evidence_refs": [item.evidence_id for item in result.evidence],
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                }
            )
            if node.type == "output":
                final_output = result.output
            if not repeat:
                processed.add(node_id)
            selected_ports = result.selected_ports or ["out"]
            for edge in outgoing.get(node_id, []):
                if edge.kind == "reassessment":
                    if not self._selected(edge, selected_ports):
                        continue
                    policy = edge.loop_policy
                    if policy is None or self._exit_condition(policy.exit_condition, context):
                        continue
                    if iterations[edge.id] >= policy.max_iterations:
                        continue
                    iterations[edge.id] += 1
                    queue.append((edge.target, True, node_id))
                    continue
                if self._selected(edge, selected_ports):
                    active_edges.add(edge.id)
                if edge.target in processed or edge.target in enqueued:
                    continue
                target_edges = [
                    candidate
                    for candidate in incoming.get(edge.target, [])
                    if candidate.kind != "reassessment"
                ]
                source_ids = {candidate.source for candidate in target_edges}
                if source_ids.issubset(processed) and any(
                    candidate.id in active_edges for candidate in target_edges
                ):
                    queue.append((edge.target, False, node_id))
                    enqueued.add(edge.target)

        output_nodes = [node.id for node in graph.nodes if node.type == "output"]
        if output_nodes and not final_output:
            for output_id in output_nodes:
                if output_id in context.node_outputs:
                    final_output = context.node_outputs[output_id]
                    break
        return ExecutionResult(
            status="succeeded",
            output=final_output,
            node_outputs=context.node_outputs,
            evidence=context.evidence,
            iterations=dict(iterations),
        )

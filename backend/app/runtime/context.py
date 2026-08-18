from dataclasses import dataclass, field
from typing import Any

from app.runtime.knowledge_gateway import EvidenceRecord


@dataclass
class ExecutionContext:
    raw_input: dict[str, Any]
    extracted: dict[str, Any]
    run_id: str
    node_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    evidence: dict[str, EvidenceRecord] = field(default_factory=dict)


@dataclass
class NodeResult:
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    selected_ports: list[str] = field(default_factory=lambda: ["out"])
    evidence: list[EvidenceRecord] = field(default_factory=list)


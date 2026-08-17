from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


NodeType = Literal[
    "input",
    "condition",
    "python_rule",
    "rag",
    "llm",
    "parallel_agent",
    "output",
    "clinical_task",
    "subworkflow",
    "annotation",
]


class NodeSpec(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    type: NodeType
    name: str = Field(min_length=1, max_length=255)
    position: dict[str, float] = Field(default_factory=dict)
    input_ports: list[str] = Field(default_factory=list)
    output_ports: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LoopPolicy(BaseModel):
    max_iterations: int = Field(ge=1, le=10)
    exit_condition: str = Field(min_length=1, max_length=2000)


class EdgeSpec(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=128)
    source_port: str = Field(default="out", min_length=1, max_length=128)
    target_port: str = Field(default="in", min_length=1, max_length=128)
    kind: Literal["normal", "branch", "reassessment"] = "normal"
    branch_label: str | None = None
    loop_policy: LoopPolicy | None = None

    @model_validator(mode="after")
    def validate_loop_policy(self) -> "EdgeSpec":
        if self.kind == "reassessment" and self.loop_policy is None:
            raise ValueError("reassessment edges require loop_policy")
        if self.kind != "reassessment" and self.loop_policy is not None:
            raise ValueError("loop_policy is only valid for reassessment edges")
        return self


class WorkflowGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[NodeSpec]
    edges: list[EdgeSpec]


class GraphIssue(BaseModel):
    code: str
    message: str
    node_id: str | None = None
    edge_id: str | None = None


class GraphValidationError(ValueError):
    def __init__(self, issues: list[GraphIssue]):
        self.issues = issues
        super().__init__("; ".join(issue.message for issue in issues))

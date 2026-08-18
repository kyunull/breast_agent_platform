# 运行时工作流执行阶段设计规格

日期：2026-08-18
版本：V1.0
状态：已获用户确认，进入实施

## 1. 目标

在现有 FastAPI 模块化单体基础上，实现可运行的决策工作流后端：执行已发布或草稿版本的图，调用 OpenAI Chat Completions 兼容模型和知识库，记录节点级追踪与可点击证据，并支持从运行结果生成提示词优化候选。

第一版执行模型为：`POST /api/v1/runs` 默认同步执行并返回最终结果；传入 `mode=async` 时创建 `queued` 运行并在进程内后台执行。Docker/Redis 队列不作为本阶段前置条件。

## 2. 现有系统边界

- 工作流图、提取配置、发布版本和两级角色已经存在，运行时只消费这些版本快照。
- `D:\coding\knowledgebase` 当前提供 `POST /search`，请求字段为 `query`、`guideline_ids`、`version_ids`、`language`、`top_k`、`use_bm25`。
- 知识库响应包含 `evidence[].text`、`raw_chunk_id`、`score`、`guideline_id`、`version_id`、`authority_level`、`citation` 和 `resolved_version_ids`；它不生成答案，也没有原文查看端点。
- 平台因此保存规范化证据和运行证据 ID，并提供自己的证据详情接口；若适配器收到外部原文 URL 则一并保存，否则展示完整检索原文。

## 3. 数据模型

新增 SQLAlchemy 实体：

- `WorkflowRun`：`id`、`workflow_id`、`workflow_version_id`、`mode`、`status`、`input_sha256`、`input_summary_json`、`output_json`、`error_json`、`started_at`、`finished_at`、`created_by`。
- `NodeTrace`：`id`、`run_id`、`node_id`、`parent_trace_id`、`status`、`attempt`、`input_summary_json`、`output_json`、`error_json`、`evidence_refs_json`、`duration_ms`、时间戳。患者输入只保存截断、脱敏摘要。
- `RunEvidence`：`id`、`run_id`、`trace_id`、`evidence_id`、`raw_chunk_id`、`text`、`score`、`source_title`、`guideline_id`、`version_id`、`locator`、`source_level`、`open_url`。
- `PromptOptimization`：`id`、`workflow_id`、`node_id`、`source_run_id`、`original_prompt`、`candidate_prompt`、`instruction`、`model_profile_id`、`test_input_sha256`、`result_diff_json`、`status`、`created_by`。

运行状态限定为 `queued`、`running`、`succeeded`、`failed`、`cancelled`。已发布工作流版本不可修改；提示词应用只能写入新的 draft。

## 4. 执行上下文和节点契约

每次运行创建只读上下文：

```python
ExecutionContext(
    raw_input: dict[str, object],
    extracted: dict[str, object],
    node_outputs: dict[str, dict[str, object]],
    evidence: dict[str, EvidenceRecord],
    run_id: str,
)
```

节点执行器统一返回：

```python
NodeResult(
    status="succeeded" | "branched" | "insufficient",
    output: dict[str, object],
    selected_ports: list[str],
    evidence: list[EvidenceRecord],
)
```

支持的节点行为：

- `input`：运行开始时调用现有提取服务，输出选定分组。
- `condition`：支持 `and`、`or`、`not`、`eq`、`neq`、`gt`、`lt`、`gte`、`lte`、`contains`、`exists`、`empty`；缺失值为 `unknown`，不能自动当作否定。
- `python_rule`：先做 AST 白名单校验，再在独立 Python 子进程执行；禁止导入、文件、网络、进程、反射和系统调用，限制超时、输出大小和结果 JSON 类型。
- `rag`：使用知识库 Profile 和查询模板调用适配器，输出 `context_text`、`evidence_refs`、`status`。
- `llm`：将提示词变量、上游结果和 RAG 证据转换为 Chat Completions `messages`，调用模型网关，校验结构化 JSON 输出并继承 `evidence_refs`。
- `parallel_agent`：并行执行列出的 Agent 节点，保存父子追踪并合并结果。
- `output`：按 `transfer_fields` 组织最终输出，校验输出 Schema。
- `clinical_task`、`subworkflow`、`annotation`：第一版输出结构化待办/引用/说明，不伪造临床结论。

调度器采用拓扑执行；普通环路在保存时已被拒绝，只有 `reassessment` 边按 `max_iterations` 执行并在 `exit_condition` 满足时退出。失败节点停止后继节点，所有已完成追踪仍可查询。

## 5. 模型网关

`OpenAICompatibleGateway` 接受 Model Profile 和渲染后的消息，向 `{base_url}/chat/completions` 发送：`model`、`messages`、`temperature`、`top_p`、`max_tokens`、`response_format`。API Key 只从 `*_REF` 环境变量解析，不写入请求日志或数据库。超时与网络错误只进行有限重试，响应异常统一转换为节点错误。

管理员可使用完整技术参数；普通用户只能选择已暴露 Profile 和语义化输出档位。工作流定义和 API 响应继续使用既有治理白名单。

## 6. 知识库适配器

`KnowledgeBaseAdapter` 使用 Profile 的 `base_url`、`search_path`、`api_key_ref` 和技术配置调用 HTTP JSON。`BreastKnowledgebaseAdapter` 兼容 `/search` 的现有字段和响应；`GenericHttpKnowledgeBaseAdapter` 允许配置同等字段映射。适配器把每条结果转换为稳定 `evidence_id`，并携带 `raw_chunk_id`、原文、指南/版本、citation 定位、分数和 `open_url`。

`POST /api/v1/knowledge/retrieve/preview` 只执行检索，不生成模型答案，返回同一证据结构。引用策略为 `required` 时，LLM/输出节点没有证据只能返回“待核实”状态，不能静默生成最终方案。

## 7. API

- `POST /api/v1/runs`：输入 `workflow_id`、`version_number`、`input`、`mode`、可选 `model_profile_id`；返回运行状态和结果/运行 ID。
- `GET /api/v1/runs/{run_id}`：返回状态、输出和错误摘要。
- `POST /api/v1/runs/{run_id}/cancel`：取消尚未完成的后台运行。
- `GET /api/v1/runs/{run_id}/traces`：按执行顺序返回节点追踪。
- `GET /api/v1/runs/{run_id}/evidence/{evidence_id}`：返回证据原文、来源和原文 URL。
- `POST /api/v1/knowledge/retrieve/preview`：在线测试 RAG 节点。
- `POST /api/v1/prompt-optimizations`：基于运行中的 LLM 节点生成候选提示词。
- `GET /api/v1/prompt-optimizations/{id}`：读取候选及测试差异。
- `POST /api/v1/prompt-optimizations/{id}/apply`：将候选写入工作流新 draft。

所有接口复用既有工作流访问控制；普通用户不能读取别人的运行详情，管理员可读取全部。错误返回 `code`、`message`、`run_id`、`node_id` 和 `details`。

## 8. 测试与安全

- 单元测试覆盖条件求值、AST 禁止项、Python 超时、模型请求/响应转换、RAG 响应转换、证据稳定 ID 和提示词变量渲染。
- 集成测试使用 Mock Chat Completions 和 Mock Knowledgebase，验证“RAG → LLM → output”的证据继承、普通用户治理、同步/异步运行和失败追踪。
- 运行 API 使用真实工作流图和测试 JSON；完整患者输入默认只计算 SHA-256，日志只保存脱敏摘要。
- 本阶段不宣称生产级沙箱或分布式队列；受限 Python 使用进程隔离和资源限制，Docker/Redis 可在后续部署增强。


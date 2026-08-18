# 乳腺癌决策智能体平台 Vue 前端设计规格

日期：2026-08-18  
版本：V1.0  
状态：待实施

## 1. 目标

基于已经完成的 FastAPI 后端，建设一个面向管理员/开发人员和医学用户的 Vue 3 前端。前端必须让医学用户能够独立完成数据字段选择、工作流节点配置、在线测试和提示词草稿优化，并让工作流最终输出中的知识库引用可以点击查看证据原文。

首版以决策方案和既有 spec 为准，不追求逐像素复现参考图，也不实现 `.pos` 文件导入。`.pos` 只作为节点、提示词、分支和医学字段设计参考。

## 2. 范围

### 2.1 首版必须实现

- 本地账号登录、当前用户和角色识别。
- 工作流列表、创建工作流、草稿信息、版本列表、发布状态。
- 工作流草稿编辑和保存，直接使用后端 `graph`、`extraction`、`metadata` 字段。
- 全量 JSON 数据准备：字段路径选择、业务分组、别名、类型、必填项、数组筛选、排序、时间范围、取值方式和缺失项策略。
- Vue Flow 工作流画布：输入、条件、Python 规则、RAG、LLM、并行 Agent、输出、临床任务、子工作流和说明节点。
- 节点连线、分支标签、节点属性面板、节点删除/复制、单节点 JSON 复制和粘贴校验。
- 普通医学用户可见的语义化配置；隐藏 `temperature`、`top_p`、`top_k`、BM25、分数阈值、去重、超时和重试等专业参数。
- 在线运行：选择草稿或已发布版本、输入测试 JSON、选择可用模型 Profile、查看运行结果。
- 原始输入、提取数据和最终输出的对照展示。
- 节点 trace 时间线和节点输入/输出摘要。
- `evidence_refs` 引用链接、证据详情抽屉、原文、来源标题、指南/版本、定位和 `open_url`。
- 提示词优化：选择运行和 LLM 节点，填写中文优化指令，读取候选，展示差异，仅应用到 draft。

### 2.2 首版不实现

- `.pos` 文件上传、解析、导入复核或正式工作流导入。
- 多租户、医院 SSO、正式审批链和生产级多进程队列。
- WebSocket 实时推送。运行状态使用短轮询。
- 像素级还原参考图；画布布局优先保证可读性和可操作性。

## 3. 技术方案

- Vue 3 + TypeScript + Vite。
- `@vue-flow/core` 和 `@vue-flow/background`/`@vue-flow/controls`（若依赖版本支持）负责 DAG 画布。
- Element Plus 负责表单、抽屉、表格、树和反馈组件。
- Pinia 保存当前用户、工作流编辑态和运行测试态。
- Axios 封装 API、Bearer Token、统一错误格式和 401 处理。
- `lucide-vue-next` 用于工具栏、状态和操作图标。
- Vitest + Vue Test Utils 覆盖核心 store、表单转换和证据渲染；Playwright 覆盖主要页面烟测和证据抽屉。

前端不引入第二套后端数据模型。API 类型应围绕后端响应定义，并使用小型适配器把后端 graph 节点转换为 Vue Flow 节点，把 Vue Flow 节点转换回后端 graph。

## 4. 视觉与交互方向

采用“临床控制台”视觉方向：

- 背景使用低饱和暖灰纸面，导航使用深墨蓝，主操作使用青绿色，风险/缺失使用琥珀色和红色。
- 采用高信息密度的分栏和表格，避免营销式大 Hero、嵌套卡片和大面积渐变。
- 标题使用稳重的中文显示字体回退链，正文使用 `Noto Sans SC`/`Microsoft YaHei` 等中文字体回退；不依赖必须联网的字体下载。
- 节点类型通过颜色、图标和短标签区分，颜色不作为唯一状态信号。
- 所有按钮有清晰的 icon + tooltip；复制、保存、发布、运行、打开证据等工具操作使用熟悉图标。
- 桌面端优先，窄屏时画布和 JSON 面板允许横向滚动，属性面板进入底部抽屉，不能遮挡运行结果。
- 文案以医学用户能理解的语义为主，不在普通用户界面暴露底层模型和检索参数名称。

## 5. 信息架构与路由

建议路由：

| 路由 | 页面 | 主要能力 |
| --- | --- | --- |
| `/login` | 登录 | 本地账号登录 |
| `/workflows` | 工作流列表 | 列表、创建、状态和版本入口 |
| `/workflows/:id/edit` | 工作流编辑 | 基本信息、数据准备、画布、保存/发布 |
| `/workflows/:id/test` | 在线测试 | 输入、运行、提取/输出对照、trace、证据 |
| `/workflows/:id/prompts` | 提示词优化 | 候选生成、差异、应用 draft |
| `/settings/profiles` | Profile 管理 | 仅管理员/开发人员，模型和知识库 Profile |

应用壳包含左侧导航、当前工作流上下文、角色标识、保存状态和退出登录。未登录路由重定向 `/login`；普通用户访问 Profile 管理时显示无权限页。

## 6. API 适配契约

默认 `VITE_API_BASE_URL=http://127.0.0.1:8000`，Axios 请求路径保留 `/api/v1`。

### 6.1 会话

- `POST /api/v1/auth/login`：`{ username, password }` -> `{ access_token, token_type, expires_at }`。
- `GET /api/v1/me`：读取 `{ id, username, display_name, role, is_active }`。
- `POST /api/v1/auth/logout`：清理本地 token。

### 6.2 工作流与提取

- `GET /api/v1/workflows` -> 工作流摘要列表。
- `POST /api/v1/workflows`：`{ name, description? }`。
- `GET /api/v1/workflows/{id}/draft` -> `{ id, workflow_id, version_number, status, name, description, graph, extraction, metadata, template_refs, definition_sha256? }`。
- `PATCH /api/v1/workflows/{id}/draft`：只提交发生变化的 `name`、`description`、`graph`、`extraction`、`metadata`、`template_refs`。
- `POST /api/v1/workflows/{id}/publish`：发布当前 draft；422 时展示 graph issues 定位到节点/边。
- `GET /api/v1/workflows/{id}/versions`：读取不可变已发布版本。
- `POST /api/v1/workflows/{id}/draft/extraction/preview`：`{ payload|sample_json, config }` -> `groups`、`missing`、`sufficiency`、`errors`。

### 6.3 Profile

- `GET /api/v1/model-profiles`。
- `GET /api/v1/knowledge-profiles`。
- 管理员可使用后端已有 POST/PATCH 创建和修改 Profile；普通用户只接收暴露的语义化字段。

### 6.4 运行、证据和优化

- `POST /api/v1/runs`：`{ workflow_id, version_number, input, mode: "sync"|"async", model_profile_id? }`。
- `GET /api/v1/runs/{run_id}`：读取 `status`、`output`、`error` 和时间。
- `POST /api/v1/runs/{run_id}/cancel`。
- `GET /api/v1/runs/{run_id}/traces`：按 `sequence` 展示节点日志。
- `GET /api/v1/runs/{run_id}/evidence/{evidence_id}`：读取证据详情。
- `POST /api/v1/knowledge/retrieve/preview`：用于 RAG 节点在线测试。
- `POST /api/v1/prompt-optimizations`、`GET /api/v1/prompt-optimizations/{id}`、`POST /api/v1/prompt-optimizations/{id}/apply`。

错误响应一般为 `{ detail: { code, message, issues?, node_id?, run_id? } }`。前端必须保留错误码和定位信息，不能只显示“请求失败”。

## 7. 页面设计

### 7.1 工作流列表

列表显示名称、说明、草稿版本、最近更新时间（如接口暂不返回时间则不显示假时间）、发布状态和操作入口。创建后自动进入编辑页。管理员可以看到全部工作流，医学用户只看到自己拥有的工作流。

### 7.2 数据准备

页面分为三栏：左侧原始 JSON 树，中间字段/分组配置，右侧提取预览。字段配置使用表单而不是要求用户书写 JSONPath；底层仍保存 `$` 路径。

字段行至少支持：别名、类型、必填、默认值、分组、数组筛选字段/值、排序字段、排序方向、取全部/首次/最新、时间起止。分组显示充分/不足状态和缺失字段。预览调用后端 extraction preview，错误定位到字段。

### 7.3 工作流画布

画布左侧为节点库，中央为 Vue Flow，右侧为属性面板。Node 数据结构映射：`id`、`type`、`label/name`、`position`、`input_ports`、`output_ports`、`config`、`metadata`。

节点表单要求：

- 输入：选择已定义提取分组。
- 条件：可视化条件树，支持 AND/OR/NOT、比较、存在/为空、包含和多出口标签；缺失值策略必须明确。
- Python 规则：可视化 RuleSpec、中文 AI 辅助入口、高级代码、输出字段和模拟样例；复制只包含结构和模拟数据，不包含真实患者数据。
- RAG：选择知识库 Profile、查询字段、无结果策略和在线预览；普通用户不显示技术参数。
- LLM：选择任务模板、字段变量、提示词、RAG 上游引用和输出 Schema；普通用户仅选择已批准模型和语义化详细程度。
- 并行 Agent：子任务列表、各自输入/提示词/RAG 引用和合并方式。
- 输出：字段映射、输出 Schema、方案/结束或转工作流终点。

复制节点按钮生成版本化 JSON 文本；粘贴时先执行 JSON 解析和最小结构校验，再显示预览，不直接覆盖当前节点。保存前前端提示未连接端点、空分支、无 output 节点和缺失提示词变量，但最终以后端校验为准。

### 7.4 在线测试

页面使用三栏对照：原始全量 JSON、提取结果、最终输出。顶部选择草稿（`version_number=0`）或已发布版本，以及当前用户可用的模型 Profile。同步运行直接展示结果；异步运行每 1.5 秒轮询直到 `succeeded`、`failed` 或 `cancelled`，提供取消按钮。

trace 使用时间线/表格展示节点名称、状态、耗时、输入摘要、输出摘要、错误和证据数量。最终输出和 trace 中的 `evidence_refs` 都渲染成可点击引用。点击引用调用证据接口并打开右侧抽屉，展示原文、来源标题、指南 ID、版本 ID、定位、来源等级和“打开原文”链接。

### 7.5 提示词优化

先选择一次运行，再从成功的 LLM trace 选择节点。提交中文优化指令后展示原提示词、候选提示词和 `result_diff`。应用操作必须明确标记“写入草稿”，成功后刷新 draft；不修改已发布版本。若后端返回冲突，保留候选文本并提示先刷新草稿。

## 8. 状态、权限与安全

- Pinia `auth` store 保存 token、用户和初始化状态；token 仅保存于 `sessionStorage`，退出时清除。
- Pinia `workflow` store 保存当前 draft、dirty 字段、保存状态和选中节点；切换页面前提示未保存修改。
- Pinia `run` store 保存 run、traces、evidence drawer 和轮询控制器。
- 普通用户不向界面展示或主动发送受治理的技术参数；后端返回的已脱敏对象作为唯一事实来源。
- 不把真实患者输入写入 localStorage、日志或复制内容；复制节点默认只复制字段结构和模拟样例。
- `open_url` 只作为外部链接显示，使用新标签页打开；原文详情以 API 返回文本为准。

## 9. 测试与验收

### 9.1 单元测试

- graph 节点双向转换保持 `id/type/config/metadata`。
- 普通用户节点表单隐藏技术参数，管理员表单可编辑。
- 提取配置序列化、字段筛选和预览错误展示。
- `evidence_refs` 能从最终输出和 trace 映射到证据抽屉。
- 异步运行轮询在终态停止，失败时显示后端错误码。
- 节点复制/粘贴不会包含 API Key 或真实输入。

### 9.2 Playwright 烟测

- 登录 -> 工作流列表 -> 创建/打开草稿。
- 编辑一个节点 -> 保存 draft -> 重新加载仍保留配置。
- 输入样例 JSON -> 运行 -> 查看输出和 trace。
- 点击 evidence 引用 -> 抽屉显示原文并可打开 `open_url`。
- 普通用户不显示 Profile 管理入口和技术参数。

### 9.3 验收标准

- `npm run build` 通过。
- Vitest 全部通过。
- 后端运行时可访问时 Playwright 主链路通过；后端不可用时显示明确的连接错误和重试入口。
- 桌面宽度 1440px 和窄屏宽度 390px 无主要文字/按钮重叠，画布可操作。

## 10. 本地运行

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

后端：

```powershell
powershell -ExecutionPolicy Bypass -File backend\scripts\run_backend.ps1
```

Vite 开发服务器默认 `http://127.0.0.1:5173`，后端默认 `http://127.0.0.1:8000`。需要在 `backend/.env` 中将 `CORS_ORIGINS` 加入 `http://127.0.0.1:5173`。

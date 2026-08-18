# 前端搭建交接说明

## 当前状态

- 仓库：`https://github.com/kyunull/breast_agent_platform.git`
- 当前后端基线提交：`486b6e1`
- 分支：`main`
- 后端目录：`backend/`
- 前端目录：尚未创建，本交接后应创建 `frontend/`
- 规格文档：
  - `docs/superpowers/specs/2026-08-17-breast-cancer-decision-agent-platform-design.md`
  - `docs/superpowers/specs/2026-08-18-runtime-execution-design.md`
  - `docs/superpowers/specs/2026-08-18-vue-frontend-design.md`
- 主工作树中原有 `outputs/`、`work/` 未跟踪内容要保留，不要清理。

后端已经完成并验证：`100 passed`，Ruff、compileall、Alembic 迁移和 Docker Compose 配置均通过。后端 Swagger 默认地址：`http://127.0.0.1:8000/docs`。

## 已确认的产品决策

1. 前端使用 Vue 3 + TypeScript + Vite，用户不维护 React。
2. `.pos` 决策树只用于参考节点、分支、提示词和字段需求，不做正式导入。
3. 非核心工作流搭建界面不要求像示意图逐像素复现，以决策方案和 spec 为准。
4. 医学用户必须能独立修改字段、条件、RAG 查询、提示词和输出；不懂 Python 时可通过可视化规则和 AI 辅助生成规则。
5. 管理员/开发人员与普通医学用户两种权限。普通用户隐藏 temperature、top_p、top_k、BM25、分数阈值、去重、超时、重试等技术参数。
6. 最重要的体验是最终结果中的知识库引用可点击查看原文、来源、指南版本、定位和外部链接。
7. 单个节点必须支持 JSON 一键复制/粘贴校验；复制内容不能含真实患者数据或密钥。
8. 本地部署优先，同时保留非 Docker 启动方式。

## 后端 API 速查

认证：

- `POST /api/v1/auth/login` body `{username,password}` -> token。
- `GET /api/v1/me` -> 当前用户和 `role`（`admin_developer` 或 `medical_user`）。
- `POST /api/v1/auth/logout`。

工作流：

- `GET /api/v1/workflows`
- `POST /api/v1/workflows` body `{name,description?}`
- `GET /api/v1/workflows/{workflow_id}/draft`
- `PATCH /api/v1/workflows/{workflow_id}/draft`，可提交 `name`、`description`、`graph`、`extraction`、`metadata`、`template_refs`
- `POST /api/v1/workflows/{workflow_id}/publish`
- `GET /api/v1/workflows/{workflow_id}/versions`
- `POST /api/v1/workflows/{workflow_id}/draft/extraction/preview` body `{payload|sample_json,config}`

Profile：

- `GET /api/v1/model-profiles`
- `GET /api/v1/knowledge-profiles`
- 管理员创建/修改 Profile 的 POST/PATCH 接口见 `backend/app/profiles/router.py`。

运行与证据：

- `POST /api/v1/runs` body `{workflow_id,version_number?,input,mode:"sync"|"async",model_profile_id?}`
- `GET /api/v1/runs/{run_id}`
- `POST /api/v1/runs/{run_id}/cancel`
- `GET /api/v1/runs/{run_id}/traces`
- `GET /api/v1/runs/{run_id}/evidence/{evidence_id}`
- `POST /api/v1/knowledge/retrieve/preview`

提示词优化：

- `POST /api/v1/prompt-optimizations` body `{run_id,node_id,instruction,model_profile_id?}`
- `GET /api/v1/prompt-optimizations/{id}`
- `POST /api/v1/prompt-optimizations/{id}/apply`，只写 draft，不改 published。

## 关键响应字段

`GET /workflows/{id}/draft`：

```json
{
  "id": "draft-id",
  "workflow_id": "workflow-id",
  "version_number": 0,
  "status": "draft",
  "name": "HER2 阳性晚期乳腺癌决策",
  "description": "...",
  "graph": {"nodes": [], "edges": []},
  "extraction": {"groups": []},
  "metadata": {},
  "template_refs": [],
  "definition_sha256": null
}
```

graph 节点字段：`id`、`type`、`name`、`position`、`input_ports`、`output_ports`、`config`、`metadata`。支持类型：

`input`、`condition`、`python_rule`、`rag`、`llm`、`parallel_agent`、`output`、`clinical_task`、`subworkflow`、`annotation`。

trace 字段：`id`、`node_id`、`status`、`sequence`、`input_summary`、`output`、`error`、`evidence_refs`、`duration_ms`。运行输出通常包含 `evidence_refs`。

证据字段：`evidence_id`、`text`、`score`、`source_title`、`guideline_id`、`version_id`、`locator`、`source_level`、`open_url`。

## 推荐实施顺序

1. 创建 `frontend/` Vite 工程和基础依赖。
2. 实现 API client、token 注入、错误拦截、Pinia auth store。
3. 实现应用壳、登录页、工作流列表和路由守卫。
4. 实现 workflow store、draft 加载/保存/发布和版本显示。
5. 实现工作流编辑页的基本信息和 Vue Flow 画布。
6. 实现节点库、节点属性面板、条件/RAG/LLM/Python/输出配置，以及单节点 JSON 复制/粘贴。
7. 实现数据准备页和 extraction preview。
8. 实现在线测试、同步/异步轮询、trace 时间线和 evidence drawer。
9. 实现提示词优化页和 draft 应用。
10. 补充管理员 Profile 页面、普通用户隐藏规则和响应式样式。
11. 用 Vitest 和 Playwright 验证，再启动 Vite 开发服务器。

## 推荐目录

```text
frontend/
  src/
    api/             # axios client 和各资源 API
    components/      # AppShell、EvidenceDrawer、NodePalette 等
    composables/     # usePolling、useNodeClipboard 等
    layouts/
    router/
    stores/          # auth、workflow、run
    types/           # API 和 graph 类型
    views/           # Login、Workflows、WorkflowEditor、WorkflowTest、PromptOptimization
    styles/
    App.vue
    main.ts
  tests/
```

## 本地启动与验证

后端：

```powershell
powershell -ExecutionPolicy Bypass -File backend\scripts\run_backend.ps1
```

前端（创建后）：

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
npm run build
npm run test:unit
npm run test:e2e
```

Vite 默认 `http://127.0.0.1:5173`。后端 `.env` 的 `CORS_ORIGINS` 需要包含 `http://127.0.0.1:5173`。

## 注意事项

- 不要把 API Key、secret 或真实患者 JSON 写入前端 localStorage、日志、节点复制内容或提交记录。
- 普通用户界面不应通过“高级设置”绕过治理隐藏参数；后端脱敏响应是最终边界。
- 发布版本不可编辑。任何优化或编辑都只保存到 draft，再由用户主动发布。
- 后端目前没有 workflow list 的更新时间字段，列表不要伪造更新时间。
- 同步运行会在 POST 请求中等待完成；异步运行用轮询，不能假设页面刷新后仍有本地患者输入。
- 证据引用必须优先展示 API 返回的 `text`，`open_url` 作为“打开原文”链接，不要只显示一个不可解释的 ID。

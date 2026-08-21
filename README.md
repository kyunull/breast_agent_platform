# 乳腺癌决策智能体平台

这是一个面向乳腺癌临床决策场景的可追溯工作流平台。平台将资料提取、条件分支、规则、知识库检索、LLM、并行智能体和输出节点组合成可验证的决策流程，并保留节点 Trace、证据原文和指南定位。

当前仓库包含：

- FastAPI 后端：双角色认证、模型/知识库 Profile 治理、工作流草稿与不可变发布版本、运行时执行、RAG 检索、受限 Python 规则、节点 Trace、证据查看和提示词优化。
- Vue 3 前端：工作流列表、Vue Flow 可视化编辑器、节点语义配置、字段提取预览、同步/异步在线测试、Trace 时间线、证据抽屉、提示词优化和管理员 Profile 管理。
- 两类用户：`admin_developer` 可管理技术配置；`medical_user` 只看到医学语义选项，不能绕过治理边界。

## 目录

```text
backend/                         FastAPI、SQLAlchemy、Alembic 和运行时
frontend/                        Vue 3 + TypeScript + Vite 临床工作区
docs/superpowers/specs/          平台、运行时和前端设计规格
docs/superpowers/plans/          前端实施计划
handoff.md                       后端基线、接口和前端搭建交接说明
```

## 本地启动

### Windows

需要 Python 3.12。

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
cd ..
powershell -ExecutionPolicy Bypass -File backend\scripts\run_backend.ps1
```

后端默认监听 `http://127.0.0.1:8000`，Swagger 地址为 `http://127.0.0.1:8000/docs`。

### macOS/Linux

```sh
cd backend
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
cd ..
bash backend/scripts/run_backend.sh
```

### 前端

另开终端执行：

```sh
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

前端默认地址为 `http://127.0.0.1:5173`。如后端不在默认地址，可设置 `VITE_API_BASE_URL`：

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev -- --host 127.0.0.1
```

后端 `.env` 的 `CORS_ORIGINS` 必须包含前端地址。

### Docker Compose

Compose 会启动 API 和 PostgreSQL，并自动执行数据库迁移：

```sh
cd backend
docker compose -f compose.yml up --build
```

API 绑定到 `127.0.0.1:8000`，PostgreSQL 只在 Compose 网络中可见。首次创建管理员：

```sh
docker compose -f compose.yml exec backend python scripts/create_admin.py
```

非 Docker 部署也可以在 `backend` 目录执行 `python scripts/create_admin.py` 创建管理员。

## 前端路由

| 路由 | 用途 | 权限 |
| --- | --- | --- |
| `/login` | 登录 | 公开 |
| `/workflows` | 工作流列表和创建 | 已登录 |
| `/workflows/:id/edit` | 草稿编辑、节点画布、配置和发布 | 已登录 |
| `/workflows/:id/test` | 在线运行、结果对比、Trace 和证据 | 已登录 |
| `/workflows/:id/prompts` | LLM 提示词候选和草稿应用 | 已登录 |
| `/settings/profiles` | 模型/知识库 Profile 管理 | 管理员/开发人员 |

## API 速查

所有接口前缀为 `/api/v1`。

认证：

- `POST /auth/login`：提交 `{username,password}` 获取令牌。
- `GET /me`：获取当前用户和角色。
- `POST /auth/logout`：注销当前会话。

工作流：

- `GET /workflows`、`POST /workflows`：列表和创建。
- `GET /workflows/{workflow_id}/draft`：读取草稿。
- `PATCH /workflows/{workflow_id}/draft`：保存 `graph`、`extraction`、`metadata` 等草稿内容。
- `POST /workflows/{workflow_id}/publish`：发布不可变版本。
- `GET /workflows/{workflow_id}/versions`：查看已发布版本。
- `POST /workflows/{workflow_id}/draft/extraction/preview`：预览字段提取。

Profile：

- `GET /model-profiles`、`GET /knowledge-profiles`：读取可用 Profile。
- 管理员创建和修改接口见 `backend/app/profiles/router.py`。

运行与证据：

- `POST /runs`：以 `sync` 或 `async` 模式运行工作流。
- `GET /runs/{run_id}`、`GET /runs/{run_id}/traces`：查询运行状态和节点结果。
- `POST /runs/{run_id}/cancel`：取消异步运行。
- `GET /runs/{run_id}/evidence/{evidence_id}`：查看证据原文、来源、指南版本、定位和外部链接。
- `POST /knowledge/retrieve/preview`：预览知识库检索结果。

提示词优化：

- `POST /prompt-optimizations`：从成功的 LLM Trace 生成候选提示词。
- `GET /prompt-optimizations/{id}`：读取候选和差异。
- `POST /prompt-optimizations/{id}/apply`：只写入当前 draft，不修改已发布版本。

## 配置与安全

复制 `backend/.env.example` 为 `backend/.env`。默认使用 `backend/data/platform.db`，生产环境可将 `DATABASE_URL` 改为 PostgreSQL 连接串。模型服务的 API Key 在管理员的“系统配置”页面直接输入，服务端使用 `backend/data/credential.key` 加密保存，接口不会返回明文或密文。知识库适配器仍可在配置中使用大写 `*_REF` 引用环境变量；任何 API Key 都不会写入工作流定义、节点 JSON、日志或 Git。

前端令牌只存于 `sessionStorage`；患者输入仅用于当前运行，不写入浏览器持久存储。节点 JSON 复制/粘贴会去除密钥和患者数据。普通用户界面不会展示温度、`top_k`、BM25、分数阈值、重试和超时等技术参数，后端脱敏和权限校验是最终边界。

异步运行是本地单进程开发模式的后台任务，进程重启后无法恢复；在部署持久化加密队列前，生产场景应优先使用同步运行。已发布版本不可编辑，所有修改和提示词应用都先进入 draft。

## 验证

后端：

```sh
cd backend
python -m pytest -q
python -m ruff check app tests
python -m compileall -q app tests alembic scripts
python -m alembic upgrade head
```

前端：

```sh
cd frontend
npm run test:unit -- --run
npm run build
npm run test:e2e
```

## 设计文档

- [平台总规格](docs/superpowers/specs/2026-08-17-breast-cancer-decision-agent-platform-design.md)
- [运行时执行规格](docs/superpowers/specs/2026-08-18-runtime-execution-design.md)
- [Vue 前端设计规格](docs/superpowers/specs/2026-08-18-vue-frontend-design.md)
- [前端实施计划](docs/superpowers/plans/2026-08-18-vue-frontend.md)
- [前端搭建交接说明](handoff.md)

# 工作流页签与模型服务配置 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为工作流增加数据、画板、测试三个路由页签，并让管理员通过中文表单安全维护及测试 OpenAI 兼容模型服务。

**Architecture:** 新的工作流上下文布局负责草稿加载、标题、保存/发布和局部页签，三个子页面只处理各自面板。模型服务继续使用 `ModelProfile.technical_config_json`，仅新增不持久化的管理员连接测试 API；前端通过纯函数将中文表单转换为既有 Profile API 负载。

**Tech Stack:** Vue 3、TypeScript、Vue Router、Pinia、Element Plus、Lucide、Vitest、Playwright、FastAPI、Pydantic、httpx、pytest。

## Global Constraints

- 保留 `/workflows/:id/edit` 与 `/workflows/:id/test`，新增 `/workflows/:id/data`，不使用查询参数切换页签。
- 真实 API Key 不得写入浏览器、数据库、草稿、日志、错误响应或审计详情；仅允许大写 `*_REF` 环境变量引用。
- 模型服务第一期仅支持 OpenAI Chat Completions 兼容接口，沿用 `base_url`、`model`、`api_key_ref` 和现有运行参数。
- 普通医学用户不显示系统配置或技术参数，后端接口继续通过 `admin_developer` 角色校验。
- 不修改或删除 `.idea/`、`backend/.venv/`、`outputs/`、`work/` 及用户已有未提交改动。
- 所有新增文案使用中文；桌面和窄屏不得有文字或按钮重叠。
- 每次提交前运行 `git diff --cached --check`，只暂存本任务明确涉及的文件和代码块。

## File Structure

| 文件 | 职责 |
| --- | --- |
| `backend/app/profiles/schemas.py` | 模型连接测试请求和安全响应。 |
| `backend/app/profiles/router.py` | 管理员限定的模型连接测试 API。 |
| `backend/tests/test_profiles.py` | API 权限、失败和密钥脱敏测试。 |
| `frontend/src/composables/useModelProfileForm.ts` | 表单状态与 Profile API 负载转换。 |
| `frontend/src/api/profiles.ts`、`frontend/src/types/api.ts` | 连接测试 API 和类型。 |
| `frontend/src/views/ProfileSettingsView.vue` | 系统配置中的模型服务表单及测试操作。 |
| `frontend/src/layouts/WorkflowWorkspaceLayout.vue` | 工作流草稿上下文、统一标题和操作区。 |
| `frontend/src/components/WorkflowWorkspaceTabs.vue` | 接入数据、工作流画板、在线测试页签。 |
| `frontend/src/views/WorkflowDataView.vue` | 独立数据接入页面，复用 `DataPreparation`。 |
| `frontend/src/stores/workflow.ts`、`frontend/src/router/index.ts` | 草稿缓存和嵌套路由。 |

### Task 1: 管理员模型连接测试 API

**Files:** Modify `backend/app/profiles/schemas.py`, `backend/app/profiles/router.py`, `backend/tests/test_profiles.py`.

**Interfaces:** Consumes `OpenAICompatibleGateway.complete(profile, messages)` 和 `require_role("admin_developer")`; produces `POST /api/v1/model-profiles/test`，请求 `{ "technical_config": { ... } }`，成功响应 `{ "ok": true, "model": "...", "latency_ms": 0 }`。

- [ ] **Step 1: 写失败 API 测试**

在 `backend/tests/test_profiles.py` 创建 `test_admin_can_test_openai_compatible_model_profile`。以 `monkeypatch.setattr(profiles_router, "OpenAICompatibleGateway", FakeGateway)` 替换网关，令 `FakeGateway.complete` 返回 `SimpleNamespace(model="mock-model")`，并断言调用消息为：

```python
[{"role": "user", "content": "请仅回复：连接成功。"}]
```

请求传 `provider="openai_compatible"`、`base_url`、`model`、`api_key_ref="MODEL_API_KEY_REF"`，断言 `200`、`ok is True`、模型名与非负耗时。增加医学用户返回 `403`、网关错误返回 `422` 两项测试；错误响应不得包含 `sk-test-secret`。

- [ ] **Step 2: 确认失败**

运行 `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_profiles.py -k "model_profile_connection" -q`。预期：FAIL，端点尚未定义时为 404。

- [ ] **Step 3: 添加请求和响应模型**

在 `schemas.py` 增加 `ModelProfileConnectionTest`，复用 `_validate_technical_config`，且仅接受 `provider == "openai_compatible"`、非空 `base_url`、`model` 或 `model_name`。增加响应模型：

```python
class ModelProfileConnectionTestRead(BaseModel):
    ok: bool = True
    model: str
    latency_ms: int = Field(ge=0)
```

- [ ] **Step 4: 实现不持久化端点**

在 `router.py` 增加管理员端点，用 `SimpleNamespace(technical_config_json=payload.technical_config)` 作为网关 Profile，调用固定消息并用 `time.perf_counter()` 计算毫秒。只把 `GatewayError` 转为 `HTTPException(422, detail={"code": "model_connection_failed", "message": str(exc)})`。不要返回供应商响应体、请求头或密钥，也不要创建数据库记录。

- [ ] **Step 5: 验证并提交**

运行 `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_profiles.py tests/test_runtime_adapters.py -q`，预期 PASS。然后运行 `git add backend/app/profiles/schemas.py backend/app/profiles/router.py backend/tests/test_profiles.py; git diff --cached --check; git commit -m "feat: add model profile connection test"`。

### Task 2: 模型表单 API 适配

**Files:** Create `frontend/src/composables/useModelProfileForm.ts`, `frontend/tests/unit/model-profile-form.spec.ts`; modify `frontend/src/api/profiles.ts`, `frontend/src/types/api.ts`.

**Interfaces:** Consumes `ProfileCreatePayload` 和 Task 1 API; produces `modelProfileToForm(profile?)`, `modelFormToPayload(form)`, `testModelProfile(payload)`。

- [ ] **Step 1: 写失败转换测试**

在 `model-profile-form.spec.ts` 输入名称、说明、启用/开放、地址、模型、`MODEL_API_KEY_REF`、温度、Top P、最大 Token、超时、重试和医学说明。断言序列化负载包含：

```ts
technical_config: {
  provider: 'openai_compatible', base_url: 'http://models.test/v1',
  model: 'gpt-test', api_key_ref: 'MODEL_API_KEY_REF',
}
```

同时断言没有 `api_key`。增加 `model_name` 回填兼容、空引用不写入负载、逗号分隔任务转换为字符串数组的用例。

- [ ] **Step 2: 确认失败**

运行 `cd frontend; npm run test:unit -- --run tests/unit/model-profile-form.spec.ts`。预期：FAIL，适配器尚未存在。

- [ ] **Step 3: 实现纯转换与 HTTP 调用**

在 `useModelProfileForm.ts` 定义 `ModelProfileForm`。`modelFormToPayload` 固定 provider，清理字符串，仅在引用非空时写 `api_key_ref`，将运行参数映射为 `temperature`、`top_p`、`max_tokens`、`timeout`、`retries`；医学说明映射为 `display_name`、`clinical_scope`、`supported_tasks`、`output_style`。为 `ProfileCreatePayload` 添加 `is_active?: boolean`，并声明：

```ts
export interface ModelProfileConnectionTestResponse {
  ok: boolean
  model: string
  latency_ms: number
}
```

在 `profiles.ts` 加入 `testModelProfile(payload)`，向 `/api/v1/model-profiles/test` POST 仅含 `technical_config` 的对象。

- [ ] **Step 4: 验证并提交**

运行 `cd frontend; npm run test:unit -- --run tests/unit/model-profile-form.spec.ts`，预期 PASS。然后运行 `git add frontend/src/composables/useModelProfileForm.ts frontend/src/api/profiles.ts frontend/src/types/api.ts frontend/tests/unit/model-profile-form.spec.ts; git diff --cached --check; git commit -m "feat: add model profile form adapter"`。

### Task 3: 管理员系统配置页面

**Files:** Modify `frontend/src/views/ProfileSettingsView.vue`, `frontend/src/layouts/AppShell.vue`, `frontend/src/router/index.ts`, `frontend/tests/unit/router.spec.ts`; create `frontend/tests/unit/profile-settings.spec.ts`.

**Interfaces:** Consumes Task 2 表单适配器、Profile CRUD 与 `testModelProfile`; produces 管理员“系统配置”导航、模型服务中文表单和连接测试，同时保留 `/settings/profiles`。

- [ ] **Step 1: 写失败页面与权限测试**

在 `router.spec.ts` 断言 `canAccessSystemSettings('admin_developer')` 为真、医学用户为假。挂载 `ProfileSettingsView` 并 mock Profile API，断言存在“模型服务”“新增模型服务”“服务地址”“密钥环境变量引用”“测试连接”，且不存在“API Key”原始密钥输入标签。

- [ ] **Step 2: 确认失败**

运行 `cd frontend; npm run test:unit -- --run tests/unit/router.spec.ts tests/unit/profile-settings.spec.ts`。预期：FAIL，模型服务表单和新权限函数尚未定义。

- [ ] **Step 3: 实现受控中文表单**

在 `ProfileSettingsView.vue` 保留“模型服务”“知识库服务”两项页内标签。模型服务表单包括基本信息、启用/开放开关、只读“OpenAI 兼容接口”、地址、模型、密钥环境变量引用、运行参数和医学说明。保存必须执行：

```ts
const payload = modelFormToPayload(modelForm)
const next = editing.value
  ? await patchModelProfile(editing.value.id, payload)
  : await createModelProfile(payload)
```

测试连接只发送 `modelFormToPayload(modelForm).technical_config`，成功展示模型名和耗时，失败显示 `getApiError(error).message`。知识库 Profile 保留既有 CRUD，不扩展新的知识库协议。导航和标题改为“系统配置”；router 导出 `canAccessSystemSettings` 并临时保留 `canAccessProfiles = canAccessSystemSettings` 兼容旧调用。

- [ ] **Step 4: 验证并提交**

运行 `cd frontend; npm run test:unit -- --run tests/unit/router.spec.ts tests/unit/profile-settings.spec.ts tests/unit/model-profile-form.spec.ts`，预期 PASS。然后运行 `git add frontend/src/views/ProfileSettingsView.vue frontend/src/layouts/AppShell.vue frontend/src/router/index.ts frontend/tests/unit/router.spec.ts frontend/tests/unit/profile-settings.spec.ts; git diff --cached --check; git commit -m "feat: add admin model service settings"`。

### Task 4: 工作流草稿上下文和页签路由

**Files:** Create `frontend/src/layouts/WorkflowWorkspaceLayout.vue`, `frontend/src/components/WorkflowWorkspaceTabs.vue`, `frontend/src/views/WorkflowDataView.vue`, `frontend/tests/unit/workflow-workspace-tabs.spec.ts`, `frontend/tests/unit/workflow-store.spec.ts`; modify `frontend/src/stores/workflow.ts`, `frontend/src/router/index.ts`.

**Interfaces:** Consumes `useWorkflowStore()`, `DataPreparation` 和路由参数 `id`; produces `/data`、`/edit`、`/test` 三个共享草稿页面。

- [ ] **Step 1: 写失败页签和 store 测试**

在 `workflow-workspace-tabs.spec.ts` 断言 `workflowId="workflow-1"` 生成 `/workflows/workflow-1/data`、`/workflows/workflow-1/edit`、`/workflows/workflow-1/test`，且仅当前路由名激活。`workflow-store.spec.ts` mock `getDraft` 和 `listVersions`，断言同一 ID 已加载且 `dirty=true` 时 `ensureDraft('workflow-1')` 不调用 API、不替换 draft；另一个 ID 时才加载。

- [ ] **Step 2: 确认失败**

运行 `cd frontend; npm run test:unit -- --run tests/unit/workflow-workspace-tabs.spec.ts tests/unit/workflow-store.spec.ts`。预期：FAIL，页签组件和 `ensureDraft` 尚未定义。

- [ ] **Step 3: 实现共享布局和数据页**

在 store 增加：

```ts
async function ensureDraft(workflowId: string) {
  if (draft.value?.workflow_id === workflowId) return draft.value
  await loadDraft(workflowId)
  return draft.value
}
```

`WorkflowWorkspaceLayout.vue` 挂载时调用 `ensureDraft`，草稿就绪后显示名称编辑、版本、保存、发布、`WorkflowWorkspaceTabs` 与 `<RouterView />`。离开当前 workflow ID 时若 `store.dirty`，显示中文确认提示；同一 ID 的页签切换不确认也不重新加载。`WorkflowDataView.vue` 只挂载 `DataPreparation`，将 `update` 转为 `store.patchLocal({ extraction: nextExtraction })`。router 使用 `:id` 共享布局，下挂 `data`、`edit`、`test` 具名子路由，保留既有 `:id/prompts`。

- [ ] **Step 4: 验证并提交**

运行 `cd frontend; npm run test:unit -- --run tests/unit/workflow-workspace-tabs.spec.ts tests/unit/workflow-store.spec.ts`，预期 PASS。然后运行 `git add frontend/src/layouts/WorkflowWorkspaceLayout.vue frontend/src/components/WorkflowWorkspaceTabs.vue frontend/src/views/WorkflowDataView.vue frontend/src/stores/workflow.ts frontend/src/router/index.ts frontend/tests/unit/workflow-workspace-tabs.spec.ts frontend/tests/unit/workflow-store.spec.ts; git diff --cached --check; git commit -m "feat: add workflow workspace tabs"`。

### Task 5: 迁移画板与测试页面

**Files:** Modify `frontend/src/views/WorkflowEditorView.vue`, `frontend/src/views/WorkflowTestView.vue`, `frontend/src/components/DataPreparation.vue`, `frontend/tests/unit/workflow-canvas.spec.ts`; create `frontend/tests/unit/workflow-editor.spec.ts`.

**Interfaces:** Consumes Task 4 布局已加载的共享 `useWorkflowStore().draft`; produces 数据配置仅存在于数据页，页签切换不覆盖画板或测试使用的草稿。

- [ ] **Step 1: 写失败迁移测试**

在 `workflow-editor.spec.ts` mock `DataPreparation`，挂载 `WorkflowEditorView` 后断言它不出现；挂载 `WorkflowDataView` 后断言它只出现一次且 `update` 调用 `store.patchLocal({ extraction })`。保留 `workflow-canvas.spec.ts` 的节点渲染、内部事件和位置同步断言。

- [ ] **Step 2: 确认失败**

运行 `cd frontend; npm run test:unit -- --run tests/unit/workflow-editor.spec.ts tests/unit/workflow-canvas.spec.ts`。预期：FAIL，画板页仍嵌入数据配置。

- [ ] **Step 3: 去除重复加载与重复头部**

在 `WorkflowEditorView.vue` 删除 `DataPreparation` 引入和实例，删除 `store.loadDraft(workflowId)`；保留 Profile 获取，使用 `watch(() => store.draft?.graph, ...)` 将共享草稿转为画布图，画布更新仍调用 `store.patchLocal({ graph })`。在 `WorkflowTestView.vue` 删除 `workflow.loadDraft(workflowId)`，只读取模型 Profile 和运行数据。将 `DataPreparation` 外层空间交给 `WorkflowDataView`，字段选择和预览逻辑不变。

- [ ] **Step 4: 验证并提交**

运行 `cd frontend; npm run test:unit -- --run tests/unit/workflow-editor.spec.ts tests/unit/workflow-canvas.spec.ts tests/unit/workflow-workspace-tabs.spec.ts`，预期 PASS。然后运行 `git add frontend/src/views/WorkflowEditorView.vue frontend/src/views/WorkflowTestView.vue frontend/src/components/DataPreparation.vue frontend/tests/unit/workflow-editor.spec.ts frontend/tests/unit/workflow-canvas.spec.ts; git diff --cached --check; git commit -m "refactor: separate workflow data workspace"`。

### Task 6: 浏览器回归、截图和最终验证

**Files:** Modify `frontend/tests/e2e/core.spec.ts`; create `frontend/tests/e2e/profile-settings.spec.ts`.

**Interfaces:** Consumes 完整路由、管理员和医学用户 mock、模型 Profile 及连接测试 API mock; produces 页签、草稿状态保持、模型设置权限和响应式端到端覆盖。

- [ ] **Step 1: 写失败端到端场景**

在 `core.spec.ts` 新增“workflow tabs”场景：管理员打开 `/workflows/workflow-1/edit`，点击“接入数据”“工作流画板”“在线测试”，断言 URL、激活态和草稿版本；在数据页变更字段后切至画板并保存，重新打开数据页仍显示该配置。创建 `profile-settings.spec.ts`：mock 模型、知识库及 `/model-profiles/test`，断言管理员看到“系统配置”，测试请求只含 `technical_config.api_key_ref`，成功结果显示模型和耗时；医学用户没有入口，访问 `/settings/profiles` 返回 `/workflows`。

- [ ] **Step 2: 运行新增端到端测试**

运行 `cd frontend; npm run test:e2e -- --grep "workflow tabs|model service settings" --reporter=line`。预期：实现前 FAIL，完成后 PASS。

- [ ] **Step 3: 执行完整验证和截图检查**

依次运行 `cd backend; .\.venv\Scripts\python.exe -m pytest -q`、`cd frontend; npm run test:unit -- --run`、`npm run test:e2e -- --reporter=line`、`npm run build`。预期四项退出码均为 0。随后在 `1440x1000` 和 `390x844` 浏览器视口检查 `/workflows/workflow-1/data`、`/workflows/workflow-1/edit`、`/settings/profiles`：页签可访问、模型表单可读、画板控件仍在左下、没有重叠。

- [ ] **Step 4: 提交验证覆盖并复核范围**

运行 `git add frontend/tests/e2e/core.spec.ts frontend/tests/e2e/profile-settings.spec.ts; git diff --cached --check; git commit -m "test: cover workflow tabs and model settings"; git status --short`。确认提交不包含 `.idea/`、`backend/.venv/`、`outputs/`、`work/` 或任何与本计划无关的用户改动。

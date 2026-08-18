# Vue Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the Vue 3 clinical-console frontend described by the committed frontend specification and handoff.

**Architecture:** Create a standalone `frontend/` Vite app. Keep backend-shaped API types in `src/types`, isolate Axios resource calls in `src/api`, use Pinia for session/workflow/run state, and adapt graph nodes at the Vue Flow boundary. Views remain thin and compose focused components for the shell, editor, test workspace, evidence drawer, and prompt optimization.

**Tech Stack:** Vue 3, TypeScript, Vite, Pinia, Vue Router, Element Plus, `@vue-flow/core`, `@vue-flow/background`, `@vue-flow/controls`, `lucide-vue-next`, Axios, Vitest + Vue Test Utils, Playwright.

## Global Constraints

- Use Vue 3 + TypeScript + Vite; do not introduce React.
- Preserve backend graph/extraction response shapes and only adapt at the Vue Flow boundary.
- Store tokens only in `sessionStorage`; never persist patient JSON, API keys, or secrets.
- Ordinary medical users must not see or submit governed technical model/retrieval parameters.
- Published versions are immutable; edits and prompt applications write only to draft.
- Evidence references must expose returned evidence text and metadata, with `open_url` as an external link when available.
- `npm run build`, `npm run test:unit`, and Playwright smoke coverage must be runnable from `frontend/`.

### Task 1: Scaffold the frontend app and test harness

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/tests/setup.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/playwright.config.ts`

**Interfaces:**
- Produces a runnable Vite app with `npm run dev`, `npm run build`, `npm run test:unit`, and `npm run test:e2e` scripts.

- [ ] Write a failing smoke test that mounts `App.vue` and expects the app shell slot text.
- [ ] Run `npm run test:unit -- --run` and confirm the missing app fails for the expected reason.
- [ ] Add the minimal Vue/Vite files, dependency scripts, and clinical-console CSS tokens.
- [ ] Run the focused smoke test and build; both must pass.
- [ ] Commit with `feat: scaffold vue frontend`.

### Task 2: Add typed API client, auth store, router, and shell

**Files:**
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/types/graph.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/api/workflows.ts`
- Create: `frontend/src/api/profiles.ts`
- Create: `frontend/src/api/runs.ts`
- Create: `frontend/src/api/prompts.ts`
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/stores/workflow.ts`
- Create: `frontend/src/stores/run.ts`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/layouts/AppShell.vue`
- Create: `frontend/src/views/LoginView.vue`
- Create: `frontend/src/views/WorkflowsView.vue`

**Interfaces:**
- `authStore.login(credentials): Promise<void>` stores token in `sessionStorage`, loads `/me`, and exposes `isAdmin`.
- `workflowStore.loadDraft(id)`, `saveDraft(patch)`, and `publish()` own draft state and dirty status.
- Router guards redirect unauthenticated users to `/login` and medical users away from `/settings/profiles`.

- [ ] Write unit tests for token injection/401 clearing and medical-user route blocking.
- [ ] Run the tests and confirm they fail before implementation.
- [ ] Implement Axios interceptors, resource APIs, Pinia stores, routes, login form, shell navigation, role badge, save state, and sign-out.
- [ ] Run unit tests and build.
- [ ] Commit with `feat: add auth shell and workflow navigation`.

### Task 3: Implement graph adapters, node palette, and editor canvas

**Files:**
- Create: `frontend/src/composables/useGraphAdapter.ts`
- Create: `frontend/src/composables/useNodeClipboard.ts`
- Create: `frontend/src/components/NodePalette.vue`
- Create: `frontend/src/components/WorkflowCanvas.vue`
- Create: `frontend/src/components/WorkflowNode.vue`
- Create: `frontend/src/components/NodeInspector.vue`
- Create: `frontend/src/views/WorkflowEditorView.vue`

**Interfaces:**
- `toFlowNode(node: GraphNode): Node` and `toGraphNode(node: Node): GraphNode` preserve `id`, `type`, `config`, `metadata`, ports, and position.
- `useNodeClipboard.copy(node)` returns versioned structure-only JSON; `parse(text)` returns validation issues without mutating the selected node.

- [ ] Write adapter and clipboard tests covering round-trip fields and secret/patient-data stripping.
- [ ] Run focused tests and confirm the expected failures.
- [ ] Implement the Vue Flow editor with node palette, connect/delete/duplicate interactions, branch labels, inspector drawer/panel, copy/paste preview, and unconnected-node warnings.
- [ ] Run focused tests and build.
- [ ] Commit with `feat: add workflow graph editor`.

### Task 4: Implement semantic node configuration forms and data preparation

**Files:**
- Create: `frontend/src/components/forms/ConditionForm.vue`
- Create: `frontend/src/components/forms/PythonRuleForm.vue`
- Create: `frontend/src/components/forms/RagForm.vue`
- Create: `frontend/src/components/forms/LlmForm.vue`
- Create: `frontend/src/components/forms/ParallelAgentForm.vue`
- Create: `frontend/src/components/forms/OutputForm.vue`
- Create: `frontend/src/components/forms/ClinicalTaskForm.vue`
- Create: `frontend/src/components/forms/SubworkflowForm.vue`
- Create: `frontend/src/components/forms/AnnotationForm.vue`
- Create: `frontend/src/components/DataPreparation.vue`

**Interfaces:**
- Forms emit normalized `GraphNode.config` patches and expose `governedFieldsVisible` only for admin/developer roles.
- `DataPreparation` serializes field rows to the backend extraction shape and emits preview requests/results.

- [ ] Write tests for extraction serialization, ordinary-user parameter hiding, and preview error path mapping.
- [ ] Run focused tests and verify RED.
- [ ] Implement semantic forms for all supported node types, JSON tree field selection, grouping/filter/sort/time controls, extraction preview, and admin-only advanced controls.
- [ ] Run focused tests and build.
- [ ] Commit with `feat: add semantic workflow configuration forms`.

### Task 5: Add online test workspace, polling, traces, and evidence drawer

**Files:**
- Create: `frontend/src/composables/usePolling.ts`
- Create: `frontend/src/components/JsonComparePane.vue`
- Create: `frontend/src/components/TraceTimeline.vue`
- Create: `frontend/src/components/EvidenceDrawer.vue`
- Create: `frontend/src/views/WorkflowTestView.vue`

**Interfaces:**
- `usePolling` stops on `succeeded`, `failed`, or `cancelled`, and exposes `cancel()`.
- `EvidenceDrawer.open(evidenceId)` loads `/runs/{runId}/evidence/{evidenceId}` and renders text plus source metadata.

- [ ] Write tests for terminal polling, backend error-code rendering, and evidence reference mapping from output/traces.
- [ ] Run focused tests and verify RED.
- [ ] Implement draft/published version selection, raw JSON input, sync/async run submission, 1.5-second polling, cancellation, three-way result comparison, trace timeline, clickable evidence refs, and source links.
- [ ] Run focused tests and build.
- [ ] Commit with `feat: add workflow testing and evidence inspection`.

### Task 6: Add prompt optimization, profile management, responsive polish, and smoke tests

**Files:**
- Create: `frontend/src/views/PromptOptimizationView.vue`
- Create: `frontend/src/views/ProfileSettingsView.vue`
- Create: `frontend/src/components/PromptDiff.vue`
- Create: `frontend/tests/unit/*.spec.ts`
- Create: `frontend/tests/e2e/core.spec.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/styles/tokens.css`

**Interfaces:**
- Prompt optimization submits Chinese instructions, displays original/candidate/diff, and applies only to draft.
- Profile settings is admin-only and renders semantic fields for medical users elsewhere.

- [ ] Write unit tests for draft-only prompt application and profile route visibility.
- [ ] Run tests and verify RED.
- [ ] Implement prompt flow, profile tables/forms, conflict handling, responsive breakpoints, focus/tooltip states, and accessible icon actions.
- [ ] Add Playwright smoke coverage for login -> workflow -> editor -> test -> evidence and ordinary-user restrictions.
- [ ] Run the full unit suite, production build, and Playwright smoke suite against the local backend/frontend.
- [ ] Commit with `feat: complete clinical console workflows`.

## Verification Checklist

- `npm run build` exits 0.
- `npm run test:unit -- --run` exits 0 with no warnings.
- Playwright smoke tests cover the principal route chain and evidence drawer.
- 1440px and 390px screenshots have no overlapping primary text or controls.
- `git status` shows only intended frontend/docs changes; `outputs/` and `work/` remain untouched.

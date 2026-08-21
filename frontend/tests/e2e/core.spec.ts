import { expect, test, type Page } from '@playwright/test'

async function expectNoHorizontalPageOverflow(page: Page) {
  const dimensions = await page.locator('html').evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth)
}

async function expectWithinViewport(page: Page, selector: string) {
  const box = await page.locator(selector).boundingBox()
  const viewport = page.viewportSize()
  expect(box).not.toBeNull()
  expect(viewport).not.toBeNull()
  expect(box!.x).toBeGreaterThanOrEqual(0)
  expect(box!.x + box!.width).toBeLessThanOrEqual(viewport!.width)
}

test('shows the local clinical workspace login', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: '登录工作区' })).toBeVisible()
  await expect(page.getByText('账号由本地管理员创建')).toBeVisible()
})

test('keeps login layout readable on a narrow viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: '登录工作区' })).toBeVisible()
  await expect(page.locator('.login-panel')).toBeVisible()
})

test('adds workflow nodes without a Vue render error', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  await page.addInitScript(() => sessionStorage.setItem('breast-agent-token', 'e2e-token'))
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/me') {
      await route.fulfill({ json: { id: 'user-1', username: 'tester', display_name: '测试用户', role: 'admin_developer', is_active: true } })
      return
    }
    if (path === '/api/v1/workflows/workflow-1/draft') {
      await route.fulfill({
        json: {
          id: 'draft-1', workflow_id: 'workflow-1', version_number: 1, status: 'draft', name: '节点创建验证', description: null,
          graph: { nodes: [], edges: [] }, extraction: { groups: [] }, metadata: {}, template_refs: [], definition_sha256: null,
        },
      })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/workflows/workflow-1/edit')
  await expect(page.getByRole('button', { name: '输入' })).toBeVisible()
  await page.getByRole('button', { name: '输入' }).click()
  await expect(page.locator('.vue-flow__node')).toHaveCount(1)
  await page.getByTitle('添加输出').click()
  await expect(page.locator('.vue-flow__node')).toHaveCount(2)

  expect(pageErrors).toEqual([])
})

test('navigates from a workflow to system settings for an admin', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  await page.addInitScript(() => sessionStorage.setItem('breast-agent-token', 'e2e-token'))
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/me') {
      await route.fulfill({ json: { id: 'admin-1', username: 'admin', display_name: '管理员', role: 'admin_developer', is_active: true } })
      return
    }
    if (path === '/api/v1/workflows/workflow-1/draft') {
      await route.fulfill({
        json: {
          id: 'draft-1', workflow_id: 'workflow-1', version_number: 1, status: 'draft', name: '路由验证', description: null,
          graph: { nodes: [], edges: [] }, extraction: { groups: [] }, metadata: {}, template_refs: [], definition_sha256: null,
        },
      })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/workflows/workflow-1/edit')
  await page.getByRole('link', { name: '系统配置' }).click()

  await expect(page).toHaveURL('/settings/profiles')
  await expect(page.getByRole('heading', { name: '系统配置', level: 2 })).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('supports canvas controls, clipping, and connecting workflow nodes', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  await page.addInitScript(() => sessionStorage.setItem('breast-agent-token', 'e2e-token'))
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/me') {
      await route.fulfill({ json: { id: 'admin-1', username: 'admin', display_name: '管理员', role: 'admin_developer', is_active: true } })
      return
    }
    if (path === '/api/v1/workflows/workflow-1/draft') {
      await route.fulfill({
        json: {
          id: 'draft-1', workflow_id: 'workflow-1', version_number: 1, status: 'draft', name: '画布交互验证', description: null,
          graph: {
            nodes: [
              { id: 'input-1', type: 'input', name: '输入资料', position: { x: 140, y: 190 }, input_ports: [{ id: 'input' }], output_ports: [{ id: 'output' }], config: {}, metadata: {} },
              { id: 'output-1', type: 'output', name: '方案输出', position: { x: 470, y: 190 }, input_ports: [{ id: 'input' }], output_ports: [{ id: 'output' }], config: {}, metadata: {} },
            ],
            edges: [],
          },
          extraction: { groups: [] }, metadata: {}, template_refs: [], definition_sha256: null,
        },
      })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/workflows/workflow-1/edit')
  await expect(page.locator('.vue-flow__node')).toHaveCount(2)

  const canvas = page.locator('.clinical-flow')
  const controls = page.locator('.vue-flow__controls')
  await expect(controls.locator('button')).toHaveCount(3)
  await expect(controls.locator('svg')).toHaveCount(3)
  expect(await canvas.evaluate((element) => getComputedStyle(element).overflow)).toBe('hidden')
  expect(await controls.evaluate((element) => getComputedStyle(element).position)).toBe('absolute')

  const canvasBox = await canvas.boundingBox()
  const controlsBox = await controls.boundingBox()
  expect(canvasBox).not.toBeNull()
  expect(controlsBox).not.toBeNull()
  expect(Math.abs(controlsBox!.x - canvasBox!.x)).toBeLessThanOrEqual(24)
  expect(Math.abs((controlsBox!.y + controlsBox!.height) - (canvasBox!.y + canvasBox!.height))).toBeLessThanOrEqual(24)

  const sourceHandle = page.locator('.vue-flow__node[data-id="input-1"] .vue-flow__handle.source')
  const targetHandle = page.locator('.vue-flow__node[data-id="output-1"] .vue-flow__handle.target')
  await expect(page.locator('.vue-flow__node[data-id="input-1"] .vue-flow__handle.target')).toHaveCount(0)
  await expect(page.locator('.vue-flow__node[data-id="output-1"] .vue-flow__handle.source')).toHaveCount(0)
  await expect(sourceHandle).toHaveCount(1)
  await expect(targetHandle).toHaveCount(1)
  const sourceBox = await sourceHandle.boundingBox()
  const targetBox = await targetHandle.boundingBox()
  expect(sourceBox?.width).toBeGreaterThanOrEqual(8)
  expect(targetBox?.width).toBeGreaterThanOrEqual(8)

  await page.mouse.move(sourceBox!.x + sourceBox!.width / 2, sourceBox!.y + sourceBox!.height / 2)
  await page.mouse.down()
  await page.mouse.move(targetBox!.x + targetBox!.width / 2, targetBox!.y + targetBox!.height / 2, { steps: 8 })
  await page.mouse.up()

  await expect(page.locator('.vue-flow__edge')).toHaveCount(1)
  await expect(page.getByText('2 个节点 · 1 条连线')).toBeVisible()

  await page.locator('.vue-flow__edge-path').click({ force: true })
  await page.keyboard.press('Delete')

  await expect(page.locator('.vue-flow__edge')).toHaveCount(0)
  await expect(page.getByText('2 个节点 · 0 条连线')).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('edits a two-branch condition node with field contracts', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  await page.addInitScript(() => sessionStorage.setItem('breast-agent-token', 'e2e-token'))
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/me') {
      await route.fulfill({ json: { id: 'admin-1', username: 'admin', display_name: '管理员', role: 'admin_developer', is_active: true } })
      return
    }
    if (path === '/api/v1/workflows/workflow-1/draft') {
      await route.fulfill({ json: {
        id: 'draft-1', workflow_id: 'workflow-1', version_number: 1, status: 'draft', name: '条件节点验证', description: null,
        graph: {
          nodes: [{
            id: 'condition-1', type: 'condition', name: 'HER2 判断', position: { x: 260, y: 220 },
            input_ports: ['input'], output_ports: ['satisfied', 'unsatisfied'],
            config: {
              operator: 'and', operands: [{ left: 'facts.her2', operator: 'not_empty', right: null }],
              true_port: 'satisfied', false_port: 'unsatisfied', true_label: '进入治疗', false_label: '补充资料', missing_strategy: 'false',
            }, metadata: {},
          }], edges: [],
        },
        extraction: { groups: [{ id: 'facts', label: '病理资料', fields: [{ alias: 'her2', path: '$.her2', type: 'string', required: true, default: null }], required: ['her2'] }] }, metadata: {}, template_refs: [], definition_sha256: null,
      } })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/workflows/workflow-1/edit')
  const condition = page.locator('.vue-flow__node[data-id="condition-1"]')
  await expect(condition).toHaveCount(1)
  await expect(condition.locator('.vue-flow__handle.source')).toHaveCount(2)
  await expect(condition.getByText('进入治疗')).toBeVisible()
  await expect(condition.getByText('补充资料')).toBeVisible()

  await condition.click()
  await expect(condition.locator('.workflow-node--selected')).toBeVisible()
  await expect(page.locator('.node-inspector__heading')).toContainText('条件 · HER2 判断')
  await expect(page.locator('.condition-rule')).toHaveCount(1)
  await page.getByRole('button', { name: '新增条件' }).click()
  await expect(page.locator('.condition-rule')).toHaveCount(2)
  await expect(page.locator('.structure-tools__body')).toHaveCount(0)
  await page.getByRole('button', { name: '结构工具' }).click()
  await expect(page.locator('.structure-tools__body')).toContainText('复制节点 JSON')
  expect(pageErrors).toEqual([])
})

test('workflow tabs keep the saved draft across data, editor, and test views', async ({ page }) => {
  const pageErrors: string[] = []
  let savedDraft = {
    id: 'draft-1', workflow_id: 'workflow-1', version_number: 7, status: 'draft', name: '多页签草稿', description: null,
    graph: { nodes: [], edges: [] }, extraction: { groups: [] }, metadata: {}, template_refs: [], definition_sha256: null,
  }
  let patchBody: unknown
  page.on('pageerror', (error) => pageErrors.push(error.message))
  await page.addInitScript(() => sessionStorage.setItem('breast-agent-token', 'e2e-token'))
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path === '/api/v1/me') {
      await route.fulfill({ json: { id: 'admin-1', username: 'admin', display_name: '管理员', role: 'admin_developer', is_active: true } })
      return
    }
    if (path === '/api/v1/workflows/workflow-1/draft' && request.method() === 'GET') {
      await route.fulfill({ json: savedDraft })
      return
    }
    if (path === '/api/v1/workflows/workflow-1/draft' && request.method() === 'PATCH') {
      patchBody = request.postDataJSON()
      savedDraft = { ...savedDraft, ...(patchBody as object) }
      await route.fulfill({ json: savedDraft })
      return
    }
    if (path === '/api/v1/workflows/workflow-1/versions' || path === '/api/v1/model-profiles' || path === '/api/v1/knowledge-profiles') {
      await route.fulfill({ json: [] })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/workflows/workflow-1/edit')
  await expect(page.getByText('草稿 v7')).toBeVisible()
  await expect(page.getByRole('link', { name: '流程编辑' })).toHaveClass(/is-active/)

  await page.getByRole('link', { name: '数据准备' }).click()
  await expect(page).toHaveURL('/workflows/workflow-1/data')
  await expect(page.getByRole('link', { name: '数据准备' })).toHaveClass(/is-active/)
  await expectWithinViewport(page, '.data-preparation')
  await expectNoHorizontalPageOverflow(page)
  const groupLabel = page.getByPlaceholder('业务分组名称').first()
  await groupLabel.fill('病理资料')
  await groupLabel.press('Tab')
  await expect(page.getByRole('button', { name: '未保存修改' })).toBeVisible()

  await page.getByRole('link', { name: '流程编辑' }).click()
  await expect(page).toHaveURL('/workflows/workflow-1/edit')
  await expect(page.getByRole('link', { name: '流程编辑' })).toHaveClass(/is-active/)
  await expect(page.locator('.clinical-flow')).toBeVisible()
  await expectWithinViewport(page, '.editor-workspace')
  await expectNoHorizontalPageOverflow(page)

  const saved = page.waitForRequest((request) => request.method() === 'PATCH' && new URL(request.url()).pathname === '/api/v1/workflows/workflow-1/draft')
  await page.locator('.workspace-actions').getByRole('button', { name: '未保存修改' }).click()
  await saved
  expect(patchBody).toEqual(expect.objectContaining({
    extraction: expect.objectContaining({ groups: expect.arrayContaining([expect.objectContaining({ label: '病理资料' })]) }),
  }))
  await expect(page.locator('.workspace-actions').getByRole('button', { name: '已保存' })).toBeVisible()

  await page.getByRole('link', { name: '在线测试' }).click()
  await expect(page).toHaveURL('/workflows/workflow-1/test')
  await expect(page.getByRole('link', { name: '在线测试' })).toHaveClass(/is-active/)

  const hydrated = page.waitForRequest((request) => request.method() === 'GET' && new URL(request.url()).pathname === '/api/v1/workflows/workflow-1/draft')
  await page.reload()
  await hydrated
  await page.getByRole('link', { name: '数据准备' }).click()
  await expect(page.getByPlaceholder('业务分组名称').first()).toHaveValue('病理资料')
  expect(savedDraft.extraction).toEqual(expect.objectContaining({ groups: expect.arrayContaining([expect.objectContaining({ label: '病理资料' })]) }))
  expect(pageErrors).toEqual([])
})

test('uploads a complete JSON document in data preparation and online testing', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  await page.addInitScript(() => sessionStorage.setItem('breast-agent-token', 'e2e-token'))
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/me') {
      await route.fulfill({ json: { id: 'admin-1', username: 'admin', display_name: '管理员', role: 'admin_developer', is_active: true } })
      return
    }
    if (path === '/api/v1/workflows/workflow-1/draft') {
      await route.fulfill({ json: {
        id: 'draft-1', workflow_id: 'workflow-1', version_number: 1, status: 'draft', name: 'JSON 上传验证', description: null,
        graph: { nodes: [], edges: [] }, extraction: { groups: [] }, metadata: {}, template_refs: [], definition_sha256: null,
      } })
      return
    }
    await route.fulfill({ json: [] })
  })
  const jsonFile = {
    name: 'BC-001.json',
    mimeType: 'application/json',
    buffer: Buffer.from('{"patient_data":{"age":42}}'),
  }

  await page.goto('/workflows/workflow-1/data')
  await page.locator('.sample-json summary').click()
  await expect(page.getByRole('button', { name: '上传完整 JSON' })).toBeVisible()
  await page.locator('.sample-json input[type="file"]').setInputFiles(jsonFile)
  await expect(page.locator('.sample-json')).toContainText('已载入：BC-001.json')
  await expect(page.locator('.sample-json textarea')).toHaveValue('{"patient_data":{"age":42}}')

  await page.getByRole('link', { name: '在线测试' }).click()
  await expect(page.getByRole('button', { name: '上传完整 JSON' })).toBeVisible()
  await page.locator('.input-panel input[type="file"]').setInputFiles(jsonFile)
  await expect(page.locator('.input-panel')).toContainText('已载入：BC-001.json')
  await expect(page.locator('.input-panel textarea')).toHaveValue('{"patient_data":{"age":42}}')
  expect(pageErrors).toEqual([])
})

test('keeps workflow data and editor layouts within a narrow viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.addInitScript(() => sessionStorage.setItem('breast-agent-token', 'e2e-token'))
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/me') {
      await route.fulfill({ json: { id: 'admin-1', username: 'admin', display_name: '管理员', role: 'admin_developer', is_active: true } })
      return
    }
    if (path === '/api/v1/workflows/workflow-1/draft') {
      await route.fulfill({ json: {
        id: 'draft-1', workflow_id: 'workflow-1', version_number: 1, status: 'draft', name: '窄屏布局验证', description: null,
        graph: { nodes: [], edges: [] }, extraction: { groups: [] }, metadata: {}, template_refs: [], definition_sha256: null,
      } })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/workflows/workflow-1/data')
  await expect(page.getByRole('link', { name: '数据准备' })).toHaveClass(/is-active/)
  await expectWithinViewport(page, '.data-preparation')
  await expectNoHorizontalPageOverflow(page)

  await page.getByRole('link', { name: '流程编辑' }).click()
  await expect(page).toHaveURL('/workflows/workflow-1/edit')
  await expect(page.getByRole('link', { name: '流程编辑' })).toHaveClass(/is-active/)
  await expectWithinViewport(page, '.editor-workspace')
  await expectNoHorizontalPageOverflow(page)

  const canvas = page.locator('.clinical-flow')
  await canvas.scrollIntoViewIfNeeded()
  await expect(canvas).toBeVisible()
  const canvasBox = await canvas.boundingBox()
  const workspaceBox = await page.locator('.editor-workspace').boundingBox()
  expect(canvasBox).not.toBeNull()
  expect(workspaceBox).not.toBeNull()
  expect(canvasBox!.x + canvasBox!.width).toBeGreaterThan(workspaceBox!.x)
  expect(canvasBox!.x).toBeLessThan(workspaceBox!.x + workspaceBox!.width)
})

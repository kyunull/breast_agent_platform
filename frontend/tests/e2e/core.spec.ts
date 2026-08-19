import { expect, test } from '@playwright/test'

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
  await page.getByRole('button', { name: '输出' }).click()
  await expect(page.locator('.vue-flow__node')).toHaveCount(2)

  expect(pageErrors).toEqual([])
})

test('navigates from a workflow to profile settings for an admin', async ({ page }) => {
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
  await page.getByRole('link', { name: '配置档案管理' }).click()

  await expect(page).toHaveURL('/settings/profiles')
  await expect(page.getByRole('heading', { name: '配置档案管理', level: 2 })).toBeVisible()
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

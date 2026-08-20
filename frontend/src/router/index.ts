import { createRouter, createWebHistory } from 'vue-router'

import AppShell from '@/layouts/AppShell.vue'
import { useAuthStore } from '@/stores/auth'
import type { UserRole } from '@/types/api'

export function canAccessSystemSettings(role: UserRole | undefined | null) {
  return role === 'admin_developer'
}

export const canAccessProfiles = canAccessSystemSettings

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/workflows' },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    {
      path: '/workflows',
      component: AppShell,
      children: [
        { path: '', name: 'workflows', component: () => import('@/views/WorkflowsView.vue') },
        { path: ':id/edit', name: 'workflow-edit', component: () => import('@/views/WorkflowEditorView.vue') },
        { path: ':id/test', name: 'workflow-test', component: () => import('@/views/WorkflowTestView.vue') },
        { path: ':id/prompts', name: 'workflow-prompts', component: () => import('@/views/PromptOptimizationView.vue') },
      ],
    },
    {
      path: '/settings',
      component: AppShell,
      children: [
        { path: 'profiles', name: 'profiles', component: () => import('@/views/ProfileSettingsView.vue'), meta: { adminOnly: true, title: '系统配置' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/workflows' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.initialized) await auth.initialize()
  if (to.meta.public) {
    if (to.name === 'login' && auth.isAuthenticated) return { name: 'workflows' }
    return true
  }
  if (!auth.isAuthenticated) return { name: 'login', query: { redirect: to.fullPath } }
  const requiresAdmin = to.matched.some((record) => record.meta.adminOnly === true)
  if (requiresAdmin && !canAccessSystemSettings(auth.user?.role)) return { name: 'workflows' }
  return true
})

export default router

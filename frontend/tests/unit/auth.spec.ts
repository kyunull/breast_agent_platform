import { setActivePinia, createPinia } from 'pinia'

import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/auth', () => ({
  login: vi.fn(async () => ({ access_token: 'token-123', token_type: 'bearer', expires_at: '2026-08-19T00:00:00Z' })),
  me: vi.fn(async () => ({
    id: 'user-1',
    username: 'doctor',
    display_name: 'Dr. Lin',
    role: 'medical_user',
    is_active: true,
  })),
  logout: vi.fn(async () => undefined),
}))

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    sessionStorage.clear()
  })

  it('stores only the bearer token in session storage and loads the current user', async () => {
    const store = useAuthStore()

    await store.login({ username: 'doctor', password: 'password' })

    expect(sessionStorage.getItem('breast-agent-token')).toBe('token-123')
    expect(store.user?.role).toBe('medical_user')
    expect(store.isAdmin).toBe(false)
  })

  it('clears session state on logout', async () => {
    const store = useAuthStore()
    await store.login({ username: 'doctor', password: 'password' })

    await store.logout()

    expect(sessionStorage.getItem('breast-agent-token')).toBeNull()
    expect(store.user).toBeNull()
  })
})

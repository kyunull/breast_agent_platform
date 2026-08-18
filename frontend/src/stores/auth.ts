import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import * as authApi from '@/api/auth'
import { TOKEN_KEY } from '@/api/client'
import type { LoginCredentials, User } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(sessionStorage.getItem(TOKEN_KEY))
  const user = ref<User | null>(null)
  const initialized = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const isAdmin = computed(() => user.value?.role === 'admin_developer')

  async function initialize() {
    if (!token.value) {
      initialized.value = true
      return
    }
    try {
      user.value = await authApi.me()
    } catch {
      token.value = null
      user.value = null
      sessionStorage.removeItem(TOKEN_KEY)
    } finally {
      initialized.value = true
    }
  }

  async function login(credentials: LoginCredentials) {
    error.value = null
    const response = await authApi.login(credentials)
    token.value = response.access_token
    sessionStorage.setItem(TOKEN_KEY, response.access_token)
    user.value = await authApi.me()
    initialized.value = true
  }

  async function logout() {
    try {
      if (token.value) await authApi.logout()
    } finally {
      token.value = null
      user.value = null
      initialized.value = true
      sessionStorage.removeItem(TOKEN_KEY)
    }
  }

  return { token, user, initialized, error, isAuthenticated, isAdmin, initialize, login, logout }
})

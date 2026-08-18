<template>
  <div class="shell">
    <aside class="shell__nav" aria-label="主导航">
      <div class="brand-lockup">
        <span class="brand-lockup__mark">乳</span>
        <div>
          <strong>决策智能体</strong>
          <span>临床工作区</span>
        </div>
      </div>

      <nav class="nav-list">
        <RouterLink class="nav-item" to="/workflows">
          <LayoutDashboard :size="18" aria-hidden="true" />
          <span>工作流</span>
        </RouterLink>
        <RouterLink v-if="auth.isAdmin" class="nav-item" to="/settings/profiles">
          <SlidersHorizontal :size="18" aria-hidden="true" />
          <span>Profile 管理</span>
        </RouterLink>
      </nav>

      <div class="shell__nav-footer">
        <span class="status-dot" aria-hidden="true"></span>
        <span>本地服务</span>
        <span class="shell__nav-version">v0.1</span>
      </div>
    </aside>

    <section class="shell__main">
      <header class="shell__header">
        <div>
          <p class="shell__section-label">Breast Cancer Decision Platform</p>
          <h1>{{ route.meta.title ?? '工作流工作区' }}</h1>
        </div>
        <div class="shell__header-actions">
          <span class="role-badge" :class="auth.isAdmin ? 'role-badge--admin' : 'role-badge--medical'">
            {{ auth.isAdmin ? '管理员 / 开发人员' : '医学用户' }}
          </span>
          <button class="icon-button" type="button" title="退出登录" @click="handleLogout">
            <LogOut :size="17" aria-hidden="true" />
            <span class="sr-only">退出登录</span>
          </button>
        </div>
      </header>
      <main class="shell__content"><RouterView /></main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { LayoutDashboard, LogOut, SlidersHorizontal } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

async function handleLogout() {
  await auth.logout()
  await router.push({ name: 'login' })
}
</script>

<style scoped>
.shell {
  display: grid;
  min-height: 100vh;
  grid-template-columns: 244px minmax(0, 1fr);
  background: var(--paper-200);
}

.shell__nav {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding: 24px 18px;
  color: #dfe8e5;
  background: var(--ink-950);
}

.brand-lockup {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 6px 8px 28px;
  border-bottom: 1px solid rgb(223 232 229 / 16%);
}

.brand-lockup__mark {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  color: var(--ink-950);
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 23px;
  font-weight: 700;
  background: #a9dbd3;
  border-radius: var(--radius-sm);
}

.brand-lockup strong,
.brand-lockup span {
  display: block;
}

.brand-lockup strong {
  font-size: 15px;
}

.brand-lockup div span {
  margin-top: 3px;
  color: #8fa7ac;
  font-size: 12px;
}

.nav-list {
  display: grid;
  gap: 5px;
  margin-top: 28px;
}

.nav-item {
  display: flex;
  gap: 10px;
  align-items: center;
  min-height: 42px;
  padding: 0 12px;
  color: #b9cbc9;
  font-size: 14px;
  text-decoration: none;
  border-radius: var(--radius-sm);
}

.nav-item:hover,
.nav-item.router-link-active {
  color: #eff8f5;
  background: rgb(169 219 211 / 14%);
}

.shell__nav-footer {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: auto;
  padding: 16px 10px 4px;
  color: #8fa7ac;
  font-size: 11px;
  border-top: 1px solid rgb(223 232 229 / 16%);
}

.status-dot {
  width: 7px;
  height: 7px;
  background: #59c49d;
  border-radius: 50%;
}

.shell__nav-version {
  margin-left: auto;
}

.shell__main {
  min-width: 0;
}

.shell__header {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  min-height: 86px;
  padding: 17px 34px;
  background: rgb(248 247 243 / 88%);
  border-bottom: 1px solid var(--line);
}

.shell__section-label {
  margin: 0 0 4px;
  color: var(--teal-700);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.shell__header h1 {
  margin: 0;
  color: var(--ink-950);
  font-size: 21px;
  font-weight: 700;
}

.shell__header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.role-badge {
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid;
  border-radius: 999px;
}

.role-badge--admin {
  color: #7f4b08;
  background: #fff4da;
  border-color: #e8c77e;
}

.role-badge--medical {
  color: var(--teal-700);
  background: #e4f2ee;
  border-color: #9bc8be;
}

.icon-button {
  display: grid;
  width: 34px;
  height: 34px;
  padding: 0;
  color: var(--ink-800);
  place-items: center;
  cursor: pointer;
  background: transparent;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}

.icon-button:hover {
  color: var(--red-700);
  border-color: #d48e92;
}

.shell__content {
  min-width: 0;
  padding: 30px 34px 42px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 760px) {
  .shell {
    display: block;
  }

  .shell__nav {
    min-height: auto;
    padding: 12px 14px;
  }

  .brand-lockup {
    padding-bottom: 12px;
  }

  .nav-list {
    grid-auto-flow: column;
    grid-auto-columns: max-content;
    margin-top: 12px;
    overflow-x: auto;
  }

  .shell__nav-footer {
    display: none;
  }

  .shell__header {
    min-height: 76px;
    padding: 14px 18px;
  }

  .shell__header h1 {
    font-size: 18px;
  }

  .shell__content {
    padding: 20px 16px 28px;
  }
}
</style>

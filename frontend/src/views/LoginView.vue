<template>
  <main class="login-page">
    <section class="login-intro">
      <p class="login-intro__eyebrow">Clinical Decision Workspace</p>
      <h1>把复杂的乳腺癌决策，放回可追溯的工作流。</h1>
      <p>从全量资料提取、规则判断到指南证据，每一步都保留可查看的输入、依据和输出。</p>
      <div class="login-intro__rule"><span></span><span></span><span></span></div>
    </section>
    <section class="login-panel" aria-labelledby="login-title">
      <div class="login-panel__heading">
        <span class="login-panel__mark">乳</span>
        <div>
          <p>本地部署</p>
          <h2 id="login-title">登录工作区</h2>
        </div>
      </div>
      <el-form :model="form" label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" placeholder="输入本地账号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" autocomplete="current-password" show-password placeholder="输入密码" type="password" />
        </el-form-item>
        <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
        <el-button :loading="loading" class="login-button" native-type="submit" type="primary">进入工作区</el-button>
      </el-form>
      <p class="login-panel__hint">账号由本地管理员创建，平台不会在浏览器保存患者资料。</p>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const loading = ref(false)
const errorMessage = ref('')
const form = reactive({ username: '', password: '' })

async function submit() {
  if (!form.username || !form.password) {
    errorMessage.value = '请输入用户名和密码。'
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    await auth.login(form)
    await router.push(typeof route.query.redirect === 'string' ? route.query.redirect : { name: 'workflows' })
  } catch (error) {
    errorMessage.value = getApiError(error).message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
  background: var(--paper-200);
}

.login-intro {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 100vh;
  padding: 56px clamp(30px, 8vw, 118px);
  color: #e5f1ee;
  background: var(--ink-950);
  background-image: linear-gradient(90deg, rgb(229 241 238 / 7%) 1px, transparent 1px), linear-gradient(rgb(229 241 238 / 7%) 1px, transparent 1px);
  background-size: 34px 34px;
}

.login-intro__eyebrow {
  margin: 0 0 22px;
  color: #93d1c7;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.login-intro h1 {
  max-width: 650px;
  margin: 0;
  font-family: "STKaiti", "KaiTi", serif;
  font-size: clamp(42px, 5.3vw, 76px);
  font-weight: 600;
  line-height: 1.08;
}

.login-intro > p:not(.login-intro__eyebrow) {
  max-width: 520px;
  margin: 25px 0 0;
  color: #abc2c0;
  font-size: 16px;
  line-height: 1.8;
}

.login-intro__rule {
  display: flex;
  gap: 8px;
  margin-top: 46px;
}

.login-intro__rule span {
  display: block;
  height: 4px;
  background: #88cabe;
}

.login-intro__rule span:nth-child(1) { width: 48px; }
.login-intro__rule span:nth-child(2) { width: 22px; background: #e5bd70; }
.login-intro__rule span:nth-child(3) { width: 8px; background: #cb757a; }

.login-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-width: 440px;
  width: 100%;
  margin: 0 auto;
  padding: 48px 42px;
}

.login-panel__heading {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 34px;
}

.login-panel__mark {
  display: grid;
  width: 46px;
  height: 46px;
  color: #e5f1ee;
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 27px;
  place-items: center;
  background: var(--teal-700);
  border-radius: var(--radius-sm);
}

.login-panel__heading p {
  margin: 0 0 2px;
  color: var(--teal-700);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.login-panel h2 {
  margin: 0;
  color: var(--ink-950);
  font-size: 26px;
}

.login-button {
  width: 100%;
  height: 44px;
  margin-top: 10px;
  font-weight: 700;
  background: var(--teal-700);
  border-color: var(--teal-700);
}

.login-button:hover {
  background: var(--teal-600);
  border-color: var(--teal-600);
}

.form-error {
  margin: 8px 0 0;
  color: var(--red-700);
  font-size: 13px;
}

.login-panel__hint {
  margin: 26px 0 0;
  color: var(--ink-650);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 860px) {
  .login-page {
    display: block;
  }

  .login-intro {
    min-height: auto;
    padding: 42px 26px 48px;
  }

  .login-intro h1 {
    font-size: 46px;
  }

  .login-panel {
    max-width: none;
    padding: 42px 26px 54px;
  }
}
</style>

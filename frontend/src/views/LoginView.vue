<template>
  <main class="login-page">
    <section class="login-intro" aria-labelledby="intro-title">
      <div class="login-intro__backdrop" aria-hidden="true">
        <div class="login-intro__contours login-intro__contours--one"></div>
        <div class="login-intro__contours login-intro__contours--two"></div>
        <div class="login-intro__contours login-intro__contours--three"></div>
        <div class="login-intro__pulse"><i></i><i></i><i></i><i></i><i></i></div>
      </div>
      <div class="login-intro__content">
        <p class="login-intro__eyebrow">乳腺癌临床决策平台</p>
        <h1 id="intro-title">把复杂的乳腺癌决策，放回可追溯的工作流。</h1>
        <p class="login-intro__description">从全量资料提取、规则判断到指南证据，每一步都保留可查看的输入、依据和输出。</p>
        <div class="login-intro__rule" aria-hidden="true"><span></span><span></span><span></span></div>
      </div>
    </section>
    <section class="login-panel" aria-labelledby="login-title">
      <div class="login-panel__inner">
        <div class="login-panel__heading">
          <div class="login-panel__mark" aria-hidden="true"><span>乳</span><i></i></div>
          <div>
            <p>本地部署</p>
            <h2 id="login-title">登录工作区</h2>
          </div>
        </div>

        <div class="login-panel__rule" aria-hidden="true"></div>

        <el-form :model="form" label-position="top" @submit.prevent="submit">
          <el-form-item label="用户名">
            <el-input v-model="form.username" autocomplete="username" placeholder="输入本地账号" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" autocomplete="current-password" show-password placeholder="输入密码" type="password" />
          </el-form-item>
          <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
          <el-button :loading="loading" class="login-button" native-type="submit" type="primary">
            <span>进入工作区</span>
            <span class="login-button__arrow" aria-hidden="true">↗</span>
          </el-button>
        </el-form>
        <p class="login-panel__hint">账号由本地管理员创建，平台不会在浏览器保存患者资料。</p>
        <div class="login-panel__meta" aria-hidden="true"><span>本地会话</span><span>仅限本机</span><span>版本 0.1</span></div>
      </div>
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
  --login-ink: #0a2029;
  --login-ink-soft: #78979a;
  --login-surface: #f5f7f3;
  --login-line: rgb(16 84 86 / 16%);
  position: relative;
  display: grid;
  min-height: 100dvh;
  grid-template-columns: minmax(560px, 1.13fr) minmax(420px, 0.87fr);
  overflow: hidden;
  background: var(--login-surface);
}

.login-intro {
  position: relative;
  isolation: isolate;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 100dvh;
  padding: 46px clamp(46px, 7vw, 112px);
  overflow: hidden;
  color: #e9f5f0;
  background: #082832;
}

.login-intro::before,
.login-intro::after {
  position: absolute;
  z-index: -1;
  content: '';
  pointer-events: none;
}

.login-intro::before {
  inset: 0;
  opacity: 0.7;
  background-image:
    linear-gradient(90deg, rgb(174 235 220 / 6%) 1px, transparent 1px),
    linear-gradient(rgb(174 235 220 / 6%) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(90deg, #000 0%, rgb(0 0 0 / 84%) 66%, transparent 100%);
}

.login-intro::after {
  inset: 12% -18% -20% 28%;
  opacity: 0.7;
  background: radial-gradient(ellipse at center, rgb(24 184 163 / 16%), transparent 63%);
  filter: blur(4px);
  animation: login-breathe 8s ease-in-out infinite;
}

.login-intro__backdrop {
  position: absolute;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  pointer-events: none;
}

.login-intro__contours {
  --contour-rotate: -18deg;
  --contour-scale-y: 1;
  position: absolute;
  right: -8%;
  top: 50%;
  width: min(66vw, 780px);
  aspect-ratio: 1.18;
  border: 1px solid rgb(122 226 204 / 30%);
  border-radius: 50%;
  transform: translateY(-50%) rotate(var(--contour-rotate)) scaleY(var(--contour-scale-y));
  box-shadow: inset 0 0 0 1px rgb(130 219 207 / 4%), 0 0 70px rgb(45 191 166 / 5%);
  animation: contour-breathe 11s ease-in-out infinite;
}

.login-intro__contours::before,
.login-intro__contours::after {
  position: absolute;
  inset: 8%;
  content: '';
  border: inherit;
  border-radius: inherit;
}

.login-intro__contours::after {
  inset: 18%;
  opacity: 0.75;
}

.login-intro__contours--two {
  --contour-rotate: 14deg;
  --contour-scale-y: 0.86;
  right: -17%;
  width: min(72vw, 860px);
  opacity: 0.68;
  animation-delay: -3.2s;
}

.login-intro__contours--three {
  --contour-rotate: -34deg;
  --contour-scale-y: 0.74;
  right: 4%;
  width: min(50vw, 600px);
  opacity: 0.42;
  animation-delay: -6.4s;
}

.login-intro__pulse {
  position: absolute;
  right: 18%;
  bottom: 20%;
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100px;
  height: 34px;
  opacity: 0.65;
}

.login-intro__pulse i {
  display: block;
  width: 2px;
  height: 8px;
  background: #8ce3d1;
  transform-origin: center;
  animation: pulse-line 2.8s ease-in-out infinite;
}

.login-intro__pulse i:nth-child(2) { height: 17px; animation-delay: -0.32s; }
.login-intro__pulse i:nth-child(3) { height: 30px; animation-delay: -0.58s; }
.login-intro__pulse i:nth-child(4) { height: 13px; animation-delay: -0.87s; }
.login-intro__pulse i:nth-child(5) { height: 6px; animation-delay: -1.1s; }

.login-intro__content {
  position: relative;
  z-index: 1;
  max-width: 640px;
}

.login-intro__eyebrow {
  margin: 0 0 18px;
  color: #93dcd0;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.login-intro h1 {
  max-width: 610px;
  margin: 0;
  color: #f0f8f4;
  font-size: 62px;
  font-weight: 750;
  letter-spacing: -0.045em;
  line-height: 1.13;
}

.login-intro__description {
  max-width: 500px;
  margin: 22px 0 0;
  color: #a4c4c3;
  font-size: 14px;
  line-height: 1.8;
}

.login-intro__rule {
  display: flex;
  gap: 6px;
  margin-top: 34px;
}

.login-intro__rule span {
  display: block;
  height: 3px;
  background: #8adfd0;
  box-shadow: 0 0 15px rgb(138 223 208 / 26%);
}

.login-intro__rule span:nth-child(1) { width: 58px; }
.login-intro__rule span:nth-child(2) { width: 24px; background: #d8bd7c; }
.login-intro__rule span:nth-child(3) { width: 8px; background: #d18c90; }

.login-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 100%;
  min-width: 0;
  padding: 54px clamp(40px, 6vw, 94px);
  background: var(--login-surface);
}

.login-panel__inner {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
}

.login-panel__heading {
  display: flex;
  gap: 15px;
  align-items: center;
  margin-bottom: 24px;
}

.login-panel__mark {
  display: grid;
  position: relative;
  width: 48px;
  height: 48px;
  color: #eaf8f2;
  place-items: center;
  background: #0b7c72;
  border-radius: 6px;
  box-shadow: 0 10px 20px rgb(11 124 114 / 20%);
}

.login-panel__mark span {
  position: relative;
  z-index: 1;
  font-size: 23px;
  font-weight: 750;
  letter-spacing: -0.08em;
}

.login-panel__mark i {
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 7px;
  height: 7px;
  border: 1px solid rgb(233 248 242 / 70%);
  border-radius: 50%;
}

.login-panel__heading p {
  margin: 0 0 5px;
  color: #0a8175;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.login-panel h2 {
  margin: 0;
  color: var(--login-ink);
  font-size: 27px;
  font-weight: 750;
  letter-spacing: -0.04em;
}

.login-panel__rule {
  width: 100%;
  height: 1px;
  margin-bottom: 30px;
  background: var(--login-line);
}

.login-button {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 50px;
  margin-top: 14px;
  font-weight: 700;
  letter-spacing: 0.03em;
  background: #0b7c72;
  border-color: #0b7c72;
  border-radius: 5px;
  box-shadow: 0 12px 24px rgb(11 124 114 / 16%);
}

.login-button:hover {
  background: #0d9184;
  border-color: #0d9184;
  box-shadow: 0 15px 28px rgb(11 124 114 / 22%);
}

.login-button__arrow {
  font-size: 18px;
  line-height: 1;
  transition: transform 160ms ease;
}

.login-button:hover .login-button__arrow {
  transform: translate(2px, -2px);
}

.form-error {
  margin: 8px 0 0;
  color: var(--red-700);
  font-size: 13px;
  line-height: 1.5;
}

.login-panel__hint {
  margin: 20px 0 0;
  color: #6e8585;
  font-size: 11px;
  line-height: 1.6;
}

.login-panel__meta {
  display: flex;
  justify-content: space-between;
  margin-top: 48px;
  padding-top: 14px;
  color: #9aabaa;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 9px;
  letter-spacing: 0.1em;
  border-top: 1px solid var(--login-line);
}

@keyframes login-breathe {
  0%, 100% { opacity: 0.44; transform: scale(0.96); }
  50% { opacity: 0.78; transform: scale(1.05); }
}

@keyframes contour-breathe {
  0%, 100% { opacity: 0.38; transform: translateY(-50%) rotate(var(--contour-rotate)) scale(0.96) scaleY(var(--contour-scale-y)); }
  50% { opacity: 0.7; transform: translateY(-50%) rotate(var(--contour-rotate)) scale(1.025) scaleY(var(--contour-scale-y)); }
}

@keyframes pulse-line {
  0%, 100% { opacity: 0.3; transform: scaleY(0.65); }
  50% { opacity: 0.92; transform: scaleY(1); }
}

@media (max-width: 1280px) and (min-width: 961px) {
  .login-intro h1 {
    font-size: 50px;
  }
}

@media (max-width: 960px) {
  .login-page {
    display: block;
    overflow: visible;
  }

  .login-intro {
    min-height: auto;
    padding: 28px 22px 30px;
  }

  .login-intro__backdrop {
    min-height: 340px;
  }

  .login-intro__contours {
    right: -30%;
    top: 55%;
    width: 540px;
  }

  .login-intro__contours--two {
    right: -42%;
    width: 620px;
  }

  .login-intro__contours--three {
    right: -8%;
    width: 420px;
  }

  .login-intro__pulse {
    right: 11%;
    bottom: 15%;
  }

  .login-intro h1 {
    max-width: 600px;
    font-size: 42px;
  }

  .login-intro__eyebrow {
    margin-bottom: 12px;
  }

  .login-intro__description {
    margin-top: 16px;
    font-size: 12px;
    line-height: 1.7;
  }

  .login-intro__rule {
    margin-top: 22px;
  }

  .login-panel {
    padding: 38px 22px 44px;
  }

  .login-panel__heading {
    margin-bottom: 24px;
  }

  .login-panel__inner {
    max-width: 520px;
  }

  .login-panel__meta {
    margin-top: 38px;
  }
}

@media (max-width: 420px) {
  .login-intro {
    padding: 24px 18px 26px;
  }

  .login-intro h1 {
    font-size: 35px;
    letter-spacing: -0.04em;
  }

  .login-intro__description {
    max-width: 320px;
  }

  .login-panel {
    padding: 30px 18px 36px;
  }

  .login-panel h2 {
    font-size: 24px;
  }

  .login-panel__meta {
    font-size: 8px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-intro::after,
  .login-intro__contours,
  .login-intro__pulse i {
    animation: none;
  }

  .login-button__arrow {
    transition: none;
  }
}
</style>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { loginModuleRecord } from '@/constants/app';
import { useAuthStore } from '@/store/modules/auth';
import { useRouterPush } from '@/hooks/common/router';
import { useFormRules, useNaiveForm } from '@/hooks/common/form';
import { $t } from '@/locales';

defineOptions({
  name: 'PwdLogin'
});

const authStore = useAuthStore();
const { toggleLoginModule } = useRouterPush();
const { formRef, validate } = useNaiveForm();

/** Cloudflare Turnstile 站点密钥（从环境变量获取） */
const turnstileSiteKey = import.meta.env.VITE_TURNSTILE_SITE_KEY || 'placeholder-site-key';
/** 人机验证 token，仅防恶意请求，非空即可 */
const turnstileToken = ref('');
const turnstileContainer = ref<HTMLDivElement | null>(null);
let turnstileWidgetId: string | undefined;

interface FormModel {
  user: string;
  password: string;
}

const model: FormModel = reactive({
  user: '',
  password: ''
});

const rules = computed<Record<keyof FormModel, App.Global.FormRule[]>>(() => {
  const { formRules } = useFormRules();
  return {
    user: formRules.userName,
    password: formRules.pwd
  };
});

function renderTurnstile() {
  nextTick(() => {
    const turnstile = (window as any).turnstile;
    if (turnstile && turnstileContainer.value) {
      turnstileToken.value = '';
      turnstileWidgetId = turnstile.render(turnstileContainer.value, {
        sitekey: turnstileSiteKey,
        callback: (token: string) => {
          turnstileToken.value = token;
        }
      });
    }
  });
}

onMounted(() => {
  const scriptSelector = 'script[src*="turnstile"]';
  if (document.querySelector(scriptSelector)) {
    renderTurnstile();
  } else {
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
    script.async = true;
    script.onload = () => renderTurnstile();
    document.head.appendChild(script);
  }
});

onBeforeUnmount(() => {
  const turnstile = (window as any).turnstile;
  if (turnstile && typeof turnstileWidgetId !== 'undefined') {
    try {
      turnstile.remove(turnstileWidgetId);
    } catch {
      // ignore
    }
  }
});

async function handleSubmit() {
  await validate();
  if (!turnstileToken.value) {
    window.$message?.error?.($t('page.login.turnstile.required' as App.I18n.I18nKey));
    return;
  }
  await authStore.login({
    user: model.user,
    password: model.password,
    turnstileToken: turnstileToken.value
  });
}
</script>

<template>
  <NForm ref="formRef" :model="model" :rules="rules" size="large" :show-label="false" @keyup.enter="handleSubmit">
    <NFormItem path="user">
      <NInput v-model:value="model.user" type="text" :placeholder="$t('page.login.common.userNamePlaceholder')" />
    </NFormItem>
    <NFormItem path="password">
      <NInput
        v-model:value="model.password"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.common.passwordPlaceholder')"
      />
    </NFormItem>
    <NFormItem>
      <div ref="turnstileContainer" class="turnstile-wrapper flex justify-center" />
    </NFormItem>
    <NSpace vertical :size="24">
      <div class="flex-y-center justify-between">
        <NCheckbox>{{ $t('page.login.pwdLogin.rememberMe') }}</NCheckbox>
        <NButton quaternary @click="toggleLoginModule('reset-pwd')">
          {{ $t('page.login.pwdLogin.forgetPassword') }}
        </NButton>
      </div>
      <NButton type="primary" size="large" round block :loading="authStore.loginLoading" @click="handleSubmit">
        {{ $t('common.confirm') }}
      </NButton>
      <div class="flex-y-center justify-between gap-12px">
        <NButton class="flex-1" block @click="toggleLoginModule('register')">
          {{ $t(loginModuleRecord.register) }}
        </NButton>
      </div>
    </NSpace>
  </NForm>
</template>

<style scoped>
.turnstile-wrapper {
  min-height: 60px;
}
</style>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { fetchRegister } from '@/service/api';
import { useAuthStore } from '@/store/modules/auth';
import { useRouterPush } from '@/hooks/common/router';
import { useFormRules, useNaiveForm } from '@/hooks/common/form';
import { useEmailCaptcha } from '@/hooks/business/email-captcha';
import { $t } from '@/locales';

defineOptions({
  name: 'Register'
});

const { toggleLoginModule, redirectFromLogin } = useRouterPush();
const { formRef, validate } = useNaiveForm();
const authStore = useAuthStore();
const { label, isCounting, loading: codeLoading, getCaptcha } = useEmailCaptcha();

/** Cloudflare Turnstile 站点密钥（从环境变量获取） */
const turnstileSiteKey = import.meta.env.VITE_TURNSTILE_SITE_KEY || 'placeholder-site-key';
/** 人机验证 token，仅防恶意请求，非空即可 */
const turnstileToken = ref('');
const turnstileContainer = ref<HTMLDivElement | null>(null);
let turnstileWidgetId: string | undefined;

interface FormModel {
  user: string;
  alias: string;
  email: string;
  code: string;
  password: string;
  confirmPassword: string;
}

const model: FormModel = reactive({
  user: '',
  alias: '',
  email: '',
  code: '',
  password: '',
  confirmPassword: ''
});

const emailPlaceholder = computed(() => $t('page.login.common.emailPlaceholder' as App.I18n.I18nKey));

const rules = computed<Record<keyof FormModel, App.Global.FormRule[]>>(() => {
  const { formRules, createConfirmPwdRule } = useFormRules();
  return {
    user: formRules.userName,
    alias: formRules.alias,
    email: formRules.email,
    code: formRules.code,
    password: formRules.pwd,
    confirmPassword: createConfirmPwdRule(model.password)
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
  const { error, data } = await fetchRegister({
    user: model.user,
    alias: model.alias,
    email: model.email,
    code: model.code,
    password: model.password,
    turnstile_token: turnstileToken.value
  });
  if (!error && data) {
    // 待审核注册：后端不返回 token，仅返回 registered + message，不可进入系统
    if ('registered' in data && data.registered === true) {
      window.$message?.warning(data.message || $t('page.login.common.accountPending'));
      setTimeout(() => {
        toggleLoginModule('pwd-login');
      }, 5000);
      return;
    }
    const pass = await authStore.loginByToken(data as Api.Auth.LoginToken);
    if (pass) {
      window.$message?.success?.($t('page.login.common.loginSuccess'));
      await redirectFromLogin(false);
    }
  }
}
</script>

<template>
  <NForm ref="formRef" :model="model" :rules="rules" size="large" :show-label="false" @keyup.enter="handleSubmit">
    <NFormItem path="user">
      <NInput v-model:value="model.user" type="text" :placeholder="$t('page.login.common.userNamePlaceholder')" />
    </NFormItem>
    <NFormItem path="alias">
      <NInput v-model:value="model.alias" type="text" :placeholder="$t('form.alias.placeholder')" />
    </NFormItem>
    <NFormItem path="email">
      <NInput v-model:value="model.email" type="text" :placeholder="emailPlaceholder" />
    </NFormItem>
    <NFormItem path="code">
      <div class="w-full flex-y-center gap-16px">
        <NInput v-model:value="model.code" :placeholder="$t('page.login.common.codePlaceholder')" />
        <NButton size="large" :disabled="isCounting" :loading="codeLoading" @click="getCaptcha(model.email)">
          {{ label }}
        </NButton>
      </div>
    </NFormItem>
    <NFormItem path="password">
      <NInput
        v-model:value="model.password"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.common.passwordPlaceholder')"
      />
    </NFormItem>
    <NFormItem path="confirmPassword">
      <NInput
        v-model:value="model.confirmPassword"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.common.confirmPasswordPlaceholder')"
      />
    </NFormItem>
    <NFormItem>
      <div ref="turnstileContainer" class="turnstile-wrapper flex justify-center" />
    </NFormItem>
    <NSpace vertical :size="18" class="w-full">
      <NButton type="primary" size="large" round block @click="handleSubmit">
        {{ $t('common.confirm') }}
      </NButton>
      <NButton size="large" round block @click="toggleLoginModule('pwd-login')">
        {{ $t('page.login.common.back') }}
      </NButton>
    </NSpace>
  </NForm>
</template>

<style scoped>
.turnstile-wrapper {
  min-height: 65px;
}
</style>

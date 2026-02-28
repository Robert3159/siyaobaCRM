import { computed } from 'vue';
import { useCountDown, useLoading } from '@sa/hooks';
import { REG_EMAIL } from '@/constants/reg';
import { fetchSendEmailCode } from '@/service/api';
import { $t } from '@/locales';

/** 邮箱验证码 hook：发送验证码到邮箱（用于注册等） */
export function useEmailCaptcha() {
  const { loading, startLoading, endLoading } = useLoading();
  const { count, start, isCounting } = useCountDown(60);

  const label = computed(() => {
    let text = $t('page.login.codeLogin.getCode');
    const countingLabel = $t('page.login.codeLogin.reGetCode', { time: count.value });
    if (loading.value) text = '';
    if (isCounting.value) text = countingLabel;
    return text;
  });

  function isEmailValid(email: string): boolean {
    if (!email.trim()) {
      window.$message?.error?.($t('form.email.required'));
      return false;
    }
    if (!REG_EMAIL.test(email)) {
      window.$message?.error?.($t('form.email.invalid'));
      return false;
    }
    return true;
  }

  async function getCaptcha(email: string): Promise<boolean> {
    if (!isEmailValid(email) || loading.value) return false;
    startLoading();
    const { error } = await fetchSendEmailCode(email);
    endLoading();
    if (!error) {
      window.$message?.success?.($t('page.login.codeLogin.sendCodeSuccess'));
      start();
      return true;
    }
    return false;
  }

  return {
    label,
    isCounting,
    loading,
    getCaptcha
  };
}

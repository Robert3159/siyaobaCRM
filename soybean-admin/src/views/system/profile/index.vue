<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { fetchResetPasswordByEmail } from '@/service/api/auth';
import { fetchMyProfile, updateMyProfile } from '@/service/api/user';
import { useEmailCaptcha } from '@/hooks/business/email-captcha';
import { useFormRules, useNaiveForm } from '@/hooks/common/form';

defineOptions({
  name: 'SystemProfile'
});

const ROLE_LABEL_MAP: Record<string, string> = {
  ADMIN: '超级管理员',
  SUB_ADMIN: '子管理员',
  QGS_DIRECTOR: '前端主管',
  QGS_LEADER: '前端组长',
  QGS_MEMBER: '前端成员',
  HGS_DIRECTOR: '后端主管',
  HGS_LEADER: '后端组长',
  HGS_MEMBER: '后端成员',
  PENDING_MEMBER: '待审核成员'
};

const loading = ref(false);
const profileSaving = ref(false);
const avatarSaving = ref(false);
const passwordSaving = ref(false);
const activePanel = ref<'profile' | 'password'>('profile');
const fileInputRef = ref<HTMLInputElement | null>(null);

const { formRef: profileFormRef, validate: validateProfileForm } = useNaiveForm();
const { formRef: passwordFormRef, validate: validatePasswordForm } = useNaiveForm();
const { formRules, createConfirmPwdRule } = useFormRules();
const { label, isCounting, loading: codeLoading, getCaptcha } = useEmailCaptcha();

const profileModel = reactive({
  user: '',
  alias: '',
  email: '',
  avatar: '' as string | null,
  role: '',
  registerAt: '',
  departmentName: '',
  teamName: ''
});

const profileSnapshot = reactive({
  user: '',
  alias: '',
  email: '',
  avatar: '' as string | null
});

const passwordModel = reactive({
  email: '',
  code: '',
  password: '',
  confirmPassword: ''
});

const profileRules = computed<Record<'user' | 'email', App.Global.FormRule[]>>(() => ({
  user: formRules.userName,
  email: formRules.email
}));

const passwordRules = computed<Record<'email' | 'code' | 'password' | 'confirmPassword', App.Global.FormRule[]>>(
  () => ({
    email: formRules.email,
    code: formRules.code,
    password: formRules.pwd,
    confirmPassword: createConfirmPwdRule(passwordModel.password)
  })
);

const displayName = computed(() => profileModel.alias || profileModel.user || '--');

const roleLabel = computed(() => ROLE_LABEL_MAP[profileModel.role] || profileModel.role || '--');

const formattedRegisterDate = computed(() => {
  if (!profileModel.registerAt) return '--';
  const date = new Date(profileModel.registerAt);
  if (Number.isNaN(date.getTime())) return '--';

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
});

function applyProfileData(data: Api.User.UserProfile) {
  profileModel.user = data.user;
  profileModel.alias = data.alias || '';
  profileModel.email = data.email;
  profileModel.avatar = data.avatar || null;
  profileModel.role = data.role;
  profileModel.registerAt = data.created_at || '';
  profileModel.departmentName = data.department_name || '未分配';
  profileModel.teamName = data.team_name || '未分配';

  profileSnapshot.user = data.user;
  profileSnapshot.alias = data.alias || '';
  profileSnapshot.email = data.email;
  profileSnapshot.avatar = data.avatar || null;

  passwordModel.email = data.email;
}

function resetProfileForm() {
  profileModel.user = profileSnapshot.user;
  profileModel.alias = profileSnapshot.alias;
  profileModel.email = profileSnapshot.email;
  profileModel.avatar = profileSnapshot.avatar;
}

async function loadProfile() {
  loading.value = true;
  try {
    const { data, error } = await fetchMyProfile();
    if (error || !data) return;
    applyProfileData(data);
  } finally {
    loading.value = false;
  }
}

async function saveProfile() {
  await validateProfileForm();
  profileSaving.value = true;
  try {
    const { error, data } = await updateMyProfile({
      user: profileModel.user.trim(),
      alias: profileModel.alias.trim() || null,
      email: profileModel.email.trim(),
      avatar: profileModel.avatar || null
    });
    if (error || !data) return;

    applyProfileData(data);
    window.$message?.success('个人资料已更新');
  } finally {
    profileSaving.value = false;
  }
}

function triggerUploadAvatar() {
  fileInputRef.value?.click();
}

function toDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('read-file-failed'));
    reader.readAsDataURL(file);
  });
}

async function saveAvatarAutomatically(avatar: string | null) {
  avatarSaving.value = true;
  try {
    const { error, data } = await updateMyProfile({
      user: profileSnapshot.user,
      alias: profileSnapshot.alias || null,
      email: profileSnapshot.email,
      avatar
    });
    if (error || !data) return false;

    profileModel.avatar = data.avatar || null;
    profileSnapshot.avatar = data.avatar || null;
    window.$message?.success('头像已更新');
    return true;
  } finally {
    avatarSaving.value = false;
  }
}

async function handleAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;

  if (!file.type.startsWith('image/')) {
    window.$message?.error('请上传图片文件');
    return;
  }

  if (file.size > 2 * 1024 * 1024) {
    window.$message?.error('头像大小不能超过 2MB');
    return;
  }

  const previousAvatar = profileModel.avatar;
  try {
    const dataUrl = await toDataUrl(file);
    profileModel.avatar = dataUrl;
    const ok = await saveAvatarAutomatically(dataUrl);
    if (!ok) profileModel.avatar = previousAvatar;
  } catch {
    profileModel.avatar = previousAvatar;
    window.$message?.error('头像上传失败，请重试');
  }
}

async function changePassword() {
  await validatePasswordForm();
  passwordSaving.value = true;
  try {
    const { error } = await fetchResetPasswordByEmail({
      email: passwordModel.email.trim(),
      code: passwordModel.code.trim(),
      password: passwordModel.password
    });
    if (error) return;

    passwordModel.code = '';
    passwordModel.password = '';
    passwordModel.confirmPassword = '';
    window.$message?.success('密码修改成功');
  } finally {
    passwordSaving.value = false;
  }
}

onMounted(() => {
  loadProfile();
});
</script>

<template>
  <NSpin :show="loading">
    <div class="profile-page">
      <NCard :bordered="false" class="profile-hero-card">
        <div class="hero-glow" />
        <div class="hero-content">
          <div class="hero-avatar">
            <div class="avatar-wrap">
              <img v-if="profileModel.avatar" :src="profileModel.avatar" class="avatar-img" />
              <SvgIcon v-else icon="mdi:account-circle" class="avatar-placeholder" />
            </div>
            <NButton size="small" secondary :loading="avatarSaving" @click="triggerUploadAvatar">上传头像</NButton>
          </div>

          <div class="hero-info">
            <h3 class="hero-name">{{ displayName }}</h3>
            <p class="hero-sub">@{{ profileModel.user || '--' }}</p>

            <div class="hero-grid">
              <div class="hero-item">
                <span class="item-label">用户名</span>
                <span class="item-value">{{ profileModel.user || '--' }}</span>
              </div>
              <div class="hero-item">
                <span class="item-label">角色</span>
                <span class="item-value">
                  <NTag round type="info" size="small">{{ roleLabel }}</NTag>
                </span>
              </div>
              <div class="hero-item">
                <span class="item-label">邮箱</span>
                <span class="item-value">{{ profileModel.email || '--' }}</span>
              </div>
              <div class="hero-item">
                <span class="item-label">注册时间</span>
                <span class="item-value">{{ formattedRegisterDate }}</span>
              </div>
              <div class="hero-item">
                <span class="item-label">部门</span>
                <span class="item-value">{{ profileModel.departmentName || '--' }}</span>
              </div>
              <div class="hero-item">
                <span class="item-label">团队</span>
                <span class="item-value">{{ profileModel.teamName || '--' }}</span>
              </div>
            </div>
          </div>
        </div>
      </NCard>

      <NCard :bordered="false" class="profile-editor-card">
        <div class="editor-tabs">
          <button
            type="button"
            class="tab-chip"
            :class="{ 'is-active': activePanel === 'profile' }"
            @click="activePanel = 'profile'"
          >
            基础信息
          </button>
          <button
            type="button"
            class="tab-chip"
            :class="{ 'is-active': activePanel === 'password' }"
            @click="activePanel = 'password'"
          >
            修改密码
          </button>
        </div>

        <template v-if="activePanel === 'profile'">
          <p class="section-desc">在这里更新你的基础资料，保存后会同步到系统顶栏展示。</p>
          <NForm
            ref="profileFormRef"
            :model="profileModel"
            :rules="profileRules"
            label-placement="top"
            class="profile-form"
          >
            <div class="profile-form-grid">
              <NFormItem label="花名" class="grid-span-2">
                <NInput v-model:value="profileModel.alias" placeholder="请输入花名（选填）" maxlength="64" />
              </NFormItem>
              <NFormItem label="用户名" path="user">
                <NInput v-model:value="profileModel.user" placeholder="请输入用户名" maxlength="32" />
              </NFormItem>
              <NFormItem label="邮箱" path="email">
                <NInput v-model:value="profileModel.email" placeholder="请输入邮箱" />
              </NFormItem>
              <NFormItem label="所在部门">
                <NInput :value="profileModel.departmentName || '--'" readonly />
              </NFormItem>
              <NFormItem label="所属团队">
                <NInput :value="profileModel.teamName || '--'" readonly />
              </NFormItem>
            </div>
          </NForm>
          <div class="main-actions">
            <NButton type="primary" :loading="profileSaving" @click="saveProfile">保存</NButton>
            <NButton @click="resetProfileForm">重置</NButton>
          </div>
        </template>

        <template v-else>
          <div class="safe-tip">
            <SvgIcon icon="mdi:shield-check" class="safe-tip-icon" />
            <span>通过邮箱验证码重置密码，确保账号安全。</span>
          </div>
          <NForm
            ref="passwordFormRef"
            :model="passwordModel"
            :rules="passwordRules"
            label-placement="top"
            class="password-form"
          >
            <NFormItem label="验证邮箱" path="email">
              <NInput v-model:value="passwordModel.email" readonly />
            </NFormItem>
            <NFormItem label="邮箱验证码" path="code">
              <div class="captcha-row">
                <NInput v-model:value="passwordModel.code" placeholder="请输入 6 位验证码" />
                <NButton
                  class="captcha-btn"
                  :disabled="isCounting"
                  :loading="codeLoading"
                  @click="getCaptcha(passwordModel.email)"
                >
                  {{ label }}
                </NButton>
              </div>
            </NFormItem>
            <NFormItem label="新密码" path="password">
              <NInput
                v-model:value="passwordModel.password"
                type="password"
                show-password-on="click"
                placeholder="请输入新密码（6-32 位）"
              />
            </NFormItem>
            <NFormItem label="确认新密码" path="confirmPassword">
              <NInput
                v-model:value="passwordModel.confirmPassword"
                type="password"
                show-password-on="click"
                placeholder="请再次输入新密码"
              />
            </NFormItem>
            <NButton type="primary" :loading="passwordSaving" @click="changePassword">确认提交</NButton>
          </NForm>
        </template>
      </NCard>

      <input ref="fileInputRef" type="file" accept="image/*" class="hidden" @change="handleAvatarChange" />
    </div>
  </NSpin>
</template>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.profile-hero-card {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
}

.hero-glow {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 14% 22%, rgb(22 119 255 / 24%), transparent 42%),
    radial-gradient(circle at 90% 12%, rgb(54 207 201 / 20%), transparent 30%),
    linear-gradient(145deg, #f5f9ff 0%, #fff 65%);
  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 26px;
  align-items: center;
}

.hero-avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.avatar-wrap {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, #edf2ff 0%, #eefaf6 100%);
  border: 4px solid #fff;
  box-shadow: 0 10px 24px rgb(27 41 76 / 16%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  font-size: 88px;
  color: #a8b3ca;
}

.hero-info {
  min-width: 0;
}

.hero-name {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1d2129;
}

.hero-sub {
  margin: 6px 0 16px;
  font-size: 13px;
  color: #86909c;
}

.hero-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 12px 28px;
}

.hero-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.item-label {
  flex-shrink: 0;
  min-width: 68px;
  color: #86909c;
  font-size: 13px;
}

.item-value {
  min-width: 0;
  color: #1d2129;
  font-size: 14px;
  font-weight: 500;
  word-break: break-all;
}

.profile-editor-card {
  border-radius: 16px;
}

.editor-tabs {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
  padding: 6px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f2f4f8 0%, #eef3ff 100%);
}

.tab-chip {
  padding: 8px 14px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #4e5969;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-chip:hover {
  color: #1d2129;
}

.tab-chip.is-active {
  background: #fff;
  color: #1677ff;
  box-shadow: 0 4px 14px rgb(22 119 255 / 16%);
}

.section-desc {
  margin: 0 0 16px;
  color: #86909c;
}

.profile-form {
  max-width: 560px;
  margin-top: 18px;
}

.profile-form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
}

.grid-span-2 {
  grid-column: span 1;
}

.profile-form :deep(.n-input),
.password-form :deep(.n-input) {
  width: 100%;
}

.main-actions {
  margin-top: 8px;
  display: flex;
  gap: 10px;
}

.safe-tip {
  border-radius: 12px;
  padding: 10px 12px;
  background: linear-gradient(135deg, #f2f8ff 0%, #ebf7f4 100%);
  color: #1f3d7a;
  display: flex;
  align-items: center;
  gap: 8px;
}

.safe-tip-icon {
  font-size: 20px;
}

.password-form {
  max-width: 560px;
  margin-top: 18px;
}

.captcha-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.captcha-btn {
  width: 128px;
  flex-shrink: 0;
}
@media (width <= 768px) {
  .hero-content {
    grid-template-columns: 1fr;
    gap: 18px;
  }

  .hero-avatar {
    align-items: flex-start;
  }

  .hero-grid {
    grid-template-columns: 1fr;
  }
}
</style>

<script setup lang="ts">
import { computed } from 'vue';
import { useNotificationStore } from '@/store/modules/notification';
import { formatUtc8DateTime } from '@/utils/datetime';
import { $t } from '@/locales';

defineOptions({
  name: 'NotificationButton'
});

const notificationStore = useNotificationStore();

const messageCount = computed(() => notificationStore.pendingCount);
const messages = computed(() => notificationStore.messages);
const canClaim = computed(() => notificationStore.canClaim);
const connected = computed(() => notificationStore.connected);
const connecting = computed(() => notificationStore.connecting);

type NotificationWsStatus = 'connected' | 'connecting' | 'disconnected';

const wsStatus = computed<NotificationWsStatus>(() => {
  if (connecting.value) return 'connecting';
  if (connected.value) return 'connected';
  return 'disconnected';
});

const statusText = computed(() => {
  switch (wsStatus.value) {
    case 'connected':
      return $t('theme.general.notification.broadcasting');
    case 'connecting':
      return $t('theme.general.notification.connecting');
    default:
      return $t('theme.general.notification.disconnected');
  }
});

const statusClass = computed(() => `is-${wsStatus.value}`);

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === '') return '-';
  if (Array.isArray(value)) {
    const normalized = value.map(item => String(item)).filter(item => item.trim());
    return normalized.length ? normalized.join(', ') : '-';
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return '-';
    }
  }
  const text = String(value).trim();
  return text || '-';
}
</script>

<template>
  <NPopover trigger="click" placement="bottom" to="body" :width="590" :show-arrow="false">
    <template #trigger>
      <span>
        <NBadge v-if="messageCount > 0" :value="messageCount" :max="99">
          <ButtonIcon icon="mdi:bell" :tooltip-content="$t('theme.general.notification.title')" />
        </NBadge>
        <ButtonIcon v-else icon="mdi:bell" :tooltip-content="$t('theme.general.notification.title')" />
      </span>
    </template>

    <div class="notification-panel">
      <div class="notification-panel__header">
        <div>
          <div class="notification-panel__title">{{ $t('theme.general.notification.title') }}</div>
          <div class="notification-panel__subtitle">当前{{ messageCount }}条注册未认领</div>
        </div>
        <div class="notification-panel__status" :class="statusClass">
          <span class="status-dot"></span>
          <span>{{ statusText }}</span>
        </div>
      </div>

      <NEmpty
        v-if="messages.length === 0"
        size="small"
        :description="$t('theme.general.notification.empty')"
        class="notification-panel__empty"
      />

      <NScrollbar v-else class="notification-panel__list">
        <article v-for="item in messages" :key="item.id" class="notification-card">
          <div class="notification-card__top">
            <div class="left">
              <div class="name">{{ formatValue(item.submitter) }}</div>
              <div class="meta-inline">
                <span>{{ formatValue(item.country) }}</span>
                <span>-</span>
                <span>{{ formatValue(item.age) }}岁</span>
                <span>-</span>
                <span>{{ formatValue(item.server) }}区</span>
              </div>
            </div>

            <div class="right">
              <span class="time">
                {{ formatUtc8DateTime(item.created_at) }}
              </span>

              <NButton
                v-if="canClaim"
                class="notification-card__claim-btn"
                size="small"
                type="primary"
                ghost
                :loading="notificationStore.isClaiming(item.id)"
                @click="notificationStore.claimMessage(item.id)"
              >
                {{ $t('theme.general.notification.claim') }}
              </NButton>
            </div>
          </div>

          <div class="token-line">
            <span class="token-label"></span>
            <span class="token-value">{{ formatValue(item.token) }}</span>
          </div>
        </article>
      </NScrollbar>
    </div>
  </NPopover>
</template>

<style scoped>
.notification-panel {
  width: min(560px, calc(100vw - 36px));
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.notification-panel__header {
  padding: 12px;
  border-radius: 12px;
  background: linear-gradient(118deg, rgb(15 23 42 / 3%), rgba(94, 38, 248, 0.08));
  border: 1px solid rgb(148 163 184 / 28%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.notification-panel__title {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.2;
}

.notification-panel__subtitle {
  margin-top: 4px;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.2px;
  color: var(--n-text-color-3);
}

.notification-panel__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--n-text-color-2);
  padding: 4px 10px;
  border-radius: 999px;
}

.notification-panel__status.is-connected {
  border: 1px solid rgb(16 185 129 / 30%);
  background: rgb(16 185 129 / 8%);
}

.notification-panel__status.is-connecting {
  border-color: rgb(245 158 11 / 30%);
  background: rgb(245 158 11 / 8%);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #10b981;
  box-shadow: 0 0 0 0 rgb(16 185 129 / 48%);
  animation: pulse 1.8s infinite;
}

.notification-panel__status.is-connecting .status-dot {
  background: #f59e0b;
  box-shadow: 0 0 0 0 rgb(245 158 11 / 45%);
}

.notification-panel__status.is-disconnected {
  border-color: rgb(239 68 68 / 30%);
  background: rgb(239 68 68 / 8%);
}

.notification-panel__status.is-disconnected .status-dot {
  background: #ef4444;
  box-shadow: none;
  animation: none;
}

.notification-panel__empty {
  min-height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px dashed var(--n-border-color);
  background: rgb(148 163 184 / 4%);
}

.notification-panel__list {
  max-height: 420px;
}

.notification-card {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--n-border-color);
  background: var(--n-color);
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: background 0.2s ease;
}

.notification-card + .notification-card {
  margin-top: 4px;
}

.notification-card:hover {
  background: var(--n-hover-color);
}

.notification-card__top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}

.left {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.name {
  font-size: 13px;
  font-weight: 600;
}

.meta-inline {
  font-size: 11px;
  color: var(--n-text-color-3);
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.time {
  font-size: 11px;
  color: var(--n-text-color-3);
  white-space: nowrap;
}

.notification-card__claim-btn {
  min-width: 64px;
}

.summary {
  font-size: 12px;
  color: var(--n-text-color-2);
  line-height: 1.4;

  display: -webkit-box;
  display: box;

  -webkit-line-clamp: 2;
  line-clamp: 2;

  -webkit-box-orient: vertical;
  overflow: hidden;
}

.token-line {
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--n-text-color-3);
}

.token-label {
  flex-shrink: 0;
  font-weight: 500;
}

.token-value {
  flex: 1;
  word-break: break-all;
  line-height: 1.4;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgb(16 185 129 / 45%);
  }

  70% {
    box-shadow: 0 0 0 6px rgb(16 185 129 / 0%);
  }

  100% {
    box-shadow: 0 0 0 0 rgb(16 185 129 / 0%);
  }
}

@media (max-width: 680px) {
  .notification-panel {
    width: min(520px, calc(100vw - 24px));
    padding: 10px;
    border-radius: 14px;
  }

  .notification-panel__header {
    padding: 10px;
  }

  .notification-panel__list {
    max-height: 360px;
  }

  .notification-card {
    padding: 10px;
  }

  .notification-card__meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>

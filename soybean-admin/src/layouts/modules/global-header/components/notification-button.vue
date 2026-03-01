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
const connecting = computed(() => notificationStore.connecting);

function formatValue(value?: string) {
  return value && value.trim() ? value : '-';
}
</script>

<template>
  <NPopover trigger="click" placement="bottom-end" to="body" :width="320">
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
        <div class="notification-panel__title">{{ $t('theme.general.notification.title') }}</div>
        <div v-if="connecting" class="notification-panel__status">
          {{ $t('theme.general.notification.connecting') }}
        </div>
      </div>

      <div v-if="messages.length === 0" class="notification-panel__empty">
        {{ $t('theme.general.notification.empty') }}
      </div>

      <div v-else class="notification-panel__list">
        <div v-for="item in messages" :key="item.id" class="notification-item">
          <div class="notification-item__fields">
            <div class="notification-item__field">
              <span class="label">{{ $t('theme.general.notification.submitter') }}</span>
              <span>{{ formatValue(item.submitter) }}</span>
            </div>
            <div class="notification-item__field">
              <span class="label">{{ $t('theme.general.notification.country') }}</span>
              <span>{{ formatValue(item.country) }}</span>
            </div>
            <div class="notification-item__field">
              <span class="label">{{ $t('theme.general.notification.age') }}</span>
              <span>{{ formatValue(item.age) }}</span>
            </div>
            <div class="notification-item__field">
              <span class="label">{{ $t('theme.general.notification.server') }}</span>
              <span>{{ formatValue(item.server) }}</span>
            </div>
            <div class="notification-item__field">
              <span class="label">{{ $t('theme.general.notification.token') }}</span>
              <span class="token">{{ formatValue(item.token) }}</span>
            </div>
          </div>
          <div class="notification-item__footer">
            <span class="notification-item__time">{{ formatUtc8DateTime(item.created_at) }}</span>
            <NButton v-if="canClaim" size="tiny" type="primary" @click="notificationStore.claimMessage(item.id)">
              {{ $t('theme.general.notification.claim') }}
            </NButton>
          </div>
        </div>
      </div>
    </div>
  </NPopover>
</template>

<style scoped>
.notification-panel {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notification-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.notification-panel__title {
  font-size: 14px;
  font-weight: 600;
}

.notification-panel__status {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.notification-panel__empty {
  font-size: 13px;
  color: var(--n-text-color-3);
}

.notification-panel__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 360px;
  overflow-y: auto;
}

.notification-item {
  border: 1px solid var(--n-border-color);
  border-radius: 10px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notification-item__summary {
  font-size: 12px;
  color: var(--n-text-color-2);
}

.notification-item__fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 10px;
  font-size: 12px;
}

.notification-item__field {
  display: flex;
  gap: 4px;
}

.notification-item__field .label {
  color: var(--n-text-color-3);
  white-space: nowrap;
}

.notification-item__field .token {
  word-break: break-all;
}

.notification-item__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--n-text-color-3);
}
</style>

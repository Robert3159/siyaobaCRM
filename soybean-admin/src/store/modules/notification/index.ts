import { computed, ref, watch } from 'vue';
import { defineStore } from 'pinia';
import { router } from '@/router';
import { SetupStoreId } from '@/enum';
import { $t } from '@/locales';
import { localStg } from '@/utils/storage';
import { useAuthStore } from '@/store/modules/auth';
import { useAppStore } from '@/store/modules/app';

type NotificationMessage = Api.Notification.Message;

type WsPayload =
  | { type: 'snapshot'; messages: NotificationMessage[] }
  | { type: 'new'; message: NotificationMessage }
  | { type: 'claimed'; id: string; claimer?: { id: number; role: string } }
  | { type: 'error'; message?: string };

const MAX_RECONNECT_DELAY = 10000;

export const useNotificationStore = defineStore(SetupStoreId.Notification, () => {
  const authStore = useAuthStore();
  const appStore = useAppStore();

  const messages = ref<NotificationMessage[]>([]);
  const connected = ref(false);
  const connecting = ref(false);

  let socket: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let reconnectAttempts = 0;
  let pendingClaimIds = new Set<string>();

  const pendingCount = computed(() => messages.value.length);

  const canClaim = computed(() => {
    const roles = authStore.userInfo.roles || [];
    return roles.some(role => role.startsWith('HGS') || role === 'ADMIN' || role === 'SUB_ADMIN');
  });

  function resolveWsUrl(token: string) {
    const explicit = import.meta.env.VITE_WS_URL;
    if (explicit) {
      return appendToken(explicit, token);
    }

    const base = import.meta.env.VITE_SERVICE_BASE_URL || '';
    if (!base) return '';

    let url: URL;
    try {
      url = new URL(base, window.location.origin);
    } catch {
      return '';
    }

    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    let pathname = url.pathname || '';
    pathname = pathname.replace(/\/api\/?$/, '');
    url.pathname = `${pathname}/ws/notifications`;
    return appendToken(url.toString(), token);
  }

  function appendToken(rawUrl: string, token: string) {
    if (!token) return rawUrl;
    try {
      const url = new URL(rawUrl, window.location.origin);
      url.searchParams.set('token', token);
      return url.toString();
    } catch {
      const sep = rawUrl.includes('?') ? '&' : '?';
      return `${rawUrl}${sep}token=${encodeURIComponent(token)}`;
    }
  }

  function resetReconnectState() {
    reconnectAttempts = 0;
    if (reconnectTimer) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer || !authStore.isLogin) return;
    const delay = Math.min(1000 * 2 ** reconnectAttempts, MAX_RECONNECT_DELAY);
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      reconnectAttempts += 1;
      connect();
    }, delay);
  }

  function connect() {
    const token = authStore.token || localStg.get('token');
    if (!token || connecting.value || connected.value) return;

    const url = resolveWsUrl(token);
    if (!url) return;

    connecting.value = true;
    try {
      socket = new WebSocket(url);
    } catch {
      connecting.value = false;
      scheduleReconnect();
      return;
    }

    socket.onopen = () => {
      connecting.value = false;
      connected.value = true;
      resetReconnectState();
    };

    socket.onmessage = event => {
      handleMessage(event.data);
    };

    socket.onerror = () => {
      connecting.value = false;
      connected.value = false;
    };

    socket.onclose = () => {
      connecting.value = false;
      connected.value = false;
      socket = null;
      scheduleReconnect();
    };
  }

  function disconnect() {
    resetReconnectState();
    pendingClaimIds = new Set();
    if (socket) {
      socket.close();
      socket = null;
    }
    connected.value = false;
    connecting.value = false;
    messages.value = [];
  }

  function claimMessage(id: string) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    pendingClaimIds.add(id);
    socket.send(JSON.stringify({ type: 'claim', id }));
  }

  function handleMessage(raw: string) {
    let payload: WsPayload | null = null;
    try {
      payload = JSON.parse(raw);
    } catch {
      return;
    }

    if (!payload || typeof payload !== 'object') return;

    if (payload.type === 'snapshot') {
      const list = Array.isArray(payload.messages) ? payload.messages : [];
      messages.value = list;
      return;
    }

    if (payload.type === 'new' && payload.message) {
      if (messages.value.some(item => item.id === payload.message.id)) return;
      messages.value = [payload.message, ...messages.value];
      return;
    }

    if (payload.type === 'claimed') {
      const id = payload.id;
      if (!id) return;
      messages.value = messages.value.filter(item => item.id !== id);
      pendingClaimIds.delete(id);
    }
  }

  function syncDocumentTitle() {
    if (typeof document === 'undefined') return;
    const { i18nKey, title } = router.currentRoute.value.meta;
    const baseTitle = i18nKey ? $t(i18nKey) : title;
    const prefix = pendingCount.value > 0 ? `(${pendingCount.value}) ` : '';
    document.title = `${prefix}${baseTitle || ''}`.trim() || document.title;
  }

  router.afterEach(() => {
    syncDocumentTitle();
  });

  watch(pendingCount, () => {
    syncDocumentTitle();
  });

  watch(
    () => appStore.locale,
    () => {
      syncDocumentTitle();
    }
  );

  watch(
    () => authStore.isLogin,
    isLogin => {
      if (isLogin) {
        connect();
      } else {
        disconnect();
      }
    },
    { immediate: true }
  );

  return {
    messages,
    pendingCount,
    connected,
    connecting,
    canClaim,
    connect,
    disconnect,
    claimMessage
  };
});

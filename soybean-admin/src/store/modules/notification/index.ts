import { computed, ref, watch } from 'vue';
import { defineStore } from 'pinia';
import { router } from '@/router';
import { useAuthStore } from '@/store/modules/auth';
import { useAppStore } from '@/store/modules/app';
import { localStg } from '@/utils/storage';
import { SetupStoreId } from '@/enum';
import { $t } from '@/locales';

type NotificationMessage = Api.Notification.Message;

type WsPayload =
  | { type: 'snapshot'; messages: NotificationMessage[] }
  | { type: 'new'; message: NotificationMessage }
  | { type: 'claimed'; id: string; player_id?: number; claimer?: { id: number; role: string; alias?: string } }
  | { type: 'error'; message?: string };

const MAX_RECONNECT_DELAY = 10000;

export const useNotificationStore = defineStore(SetupStoreId.Notification, () => {
  const authStore = useAuthStore();
  const appStore = useAppStore();

  const messages = ref<NotificationMessage[]>([]);
  const connected = ref(false);
  const connecting = ref(false);
  const lastClaimed = ref<{
    id: string;
    player_id?: number;
    claimer?: { id: number; role: string; alias?: string };
  } | null>(null);
  const pendingClaimIds = ref<Set<string>>(new Set());

  let socket: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let reconnectAttempts = 0;
  function setClaiming(id: string, active: boolean) {
    const next = new Set(pendingClaimIds.value);
    if (active) {
      next.add(id);
    } else {
      next.delete(id);
    }
    pendingClaimIds.value = next;
  }

  function clearClaiming() {
    pendingClaimIds.value = new Set();
  }

  function isClaiming(id: string) {
    return pendingClaimIds.value.has(id);
  }

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
    clearClaiming();
    if (socket) {
      socket.close();
      socket = null;
    }
    connected.value = false;
    connecting.value = false;
    messages.value = [];
  }

  function claimMessage(id: string) {
    const claimId = String(id || '').trim();
    if (!claimId) return;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      window.$message?.warning('通知连接尚未建立，请稍后重试');
      return;
    }
    if (pendingClaimIds.value.has(claimId)) return;
    setClaiming(claimId, true);
    socket.send(JSON.stringify({ type: 'claim', id: claimId }));
  }

  function handleSnapshot(payload: Extract<WsPayload, { type: 'snapshot' }>) {
    const list = Array.isArray(payload.messages) ? payload.messages : [];
    messages.value = list;
  }

  function handleNew(payload: Extract<WsPayload, { type: 'new' }>) {
    const message = payload.message;
    if (!message) return;
    if (messages.value.some(item => item.id === message.id)) return;
    messages.value = [message, ...messages.value];
  }

  function handleError() {
    if (pendingClaimIds.value.size === 0) return;
    clearClaiming();
    window.$message?.error('认领失败，请稍后重试');
  }

  function handleClaimed(payload: Extract<WsPayload, { type: 'claimed' }>) {
    const id = payload.id;
    if (!id) return;
    const wasPending = pendingClaimIds.value.has(id);
    if (wasPending) {
      setClaiming(id, false);
    }
    messages.value = messages.value.filter(item => item.id !== id);
    lastClaimed.value = {
      id,
      player_id: payload.player_id,
      claimer: payload.claimer
    };
    const currentUserId = authStore.userInfo.userId;
    const claimerId = payload.claimer?.id;
    if (currentUserId && claimerId !== undefined && String(claimerId) === String(currentUserId)) {
      window.$message?.success('认领成功');
    } else if (wasPending) {
      const alias = (payload.claimer?.alias || '').trim();
      window.$message?.warning(alias ? `已被 ${alias} 认领` : '已被其他人认领');
    }
  }

  function handlePayload(payload: WsPayload) {
    switch (payload.type) {
      case 'snapshot':
        handleSnapshot(payload);
        return;
      case 'new':
        handleNew(payload);
        return;
      case 'error':
        handleError();
        return;
      case 'claimed':
        handleClaimed(payload);
        break;
      default:
        break;
    }
  }

  function handleMessage(raw: string) {
    let payload: WsPayload | null = null;
    try {
      payload = JSON.parse(raw);
    } catch {
      return;
    }

    if (!payload || typeof payload !== 'object') return;
    handlePayload(payload);
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
    lastClaimed,
    canClaim,
    connect,
    disconnect,
    claimMessage,
    isClaiming
  };
});

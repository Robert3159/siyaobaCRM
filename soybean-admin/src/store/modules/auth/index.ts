import { computed, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import { defineStore } from 'pinia';
import { useLoading } from '@sa/hooks';
import { fetchGetUserInfo, fetchLogin, fetchMyProfile } from '@/service/api';
import { useRouterPush } from '@/hooks/common/router';
import { localStg } from '@/utils/storage';
import { SetupStoreId } from '@/enum';
import { $t } from '@/locales';
import { useRouteStore } from '../route';
import { useTabStore } from '../tab';
import { clearAuthStorage, getToken } from './shared';

export const useAuthStore = defineStore(SetupStoreId.Auth, () => {
  const route = useRoute();
  const authStore = useAuthStore();
  const routeStore = useRouteStore();
  const tabStore = useTabStore();
  const { toLogin, redirectFromLogin } = useRouterPush(false);
  const { loading: loginLoading, startLoading, endLoading } = useLoading();

  const token = ref(getToken());

  const userInfo: Api.Auth.UserInfo = reactive({
    userId: '',
    userName: '',
    roles: [],
    buttons: [],
    homeRoute: null,
    availableHomeRoutes: []
  });

  /** is super role in static route */
  const isStaticSuper = computed(() => {
    const { VITE_AUTH_ROUTE_MODE, VITE_STATIC_SUPER_ROLE } = import.meta.env;

    return VITE_AUTH_ROUTE_MODE === 'static' && userInfo.roles.includes(VITE_STATIC_SUPER_ROLE);
  });

  /** Is login */
  const isLogin = computed(() => Boolean(token.value));

  /** Reset auth store */
  async function resetStore() {
    recordUserId();

    clearAuthStorage();

    authStore.$reset();

    if (!route.meta.constant) {
      await toLogin();
    }

    tabStore.cacheTabs();
    routeStore.resetStore();
  }

  /** Record the user ID of the previous login session Used to compare with the current user ID on next login */
  function recordUserId() {
    if (!userInfo.userId) {
      return;
    }

    // Store current user ID locally for next login comparison
    localStg.set('lastLoginUserId', userInfo.userId);
  }

  /**
   * Check if current login user is different from previous login user If different, clear all tabs
   *
   * @returns {boolean} Whether to clear all tabs
   */
  function checkTabClear(): boolean {
    if (!userInfo.userId) {
      return false;
    }

    const lastLoginUserId = localStg.get('lastLoginUserId');

    // Clear all tabs if current user is different from previous user
    if (!lastLoginUserId || lastLoginUserId !== userInfo.userId) {
      localStg.remove('globalTabs');
      tabStore.clearTabs();

      localStg.remove('lastLoginUserId');
      return true;
    }

    localStg.remove('lastLoginUserId');
    return false;
  }

  /**
   * Login锛堢敤鎴峰悕 user + 瀵嗙爜 + Turnstile token锛?   *
   * @param payload.user 鐢ㄦ埛鍚?   * @param payload.password 瀵嗙爜
   * @param payload.turnstileToken Cloudflare Turnstile 浜烘満楠岃瘉 token
   * @param [payload.redirect=true] 鐧诲綍鎴愬姛鍚庢槸鍚﹁烦杞?   */
  async function login(payload: { user: string; password: string; turnstileToken: string; redirect?: boolean }) {
    const { user, password, turnstileToken } = payload;
    startLoading();

    const { data: loginToken, error } = await fetchLogin(user, password, turnstileToken);

    if (!error && loginToken) {
      const pass = await loginByToken(loginToken);

      if (pass) {
        // Keep the tab cleanup behavior when different users log in on this browser.
        checkTabClear();
        await routeStore.initAuthRoute();
        await redirectFromLogin(false);

        window.$notification?.success({
          title: $t('page.login.common.loginSuccess'),
          content: $t('page.login.common.welcomeBack', { userName: userInfo.userName }),
          duration: 4500
        });
      }
    } else {
      resetStore();
    }

    endLoading();
  }

  /** 浠呭厑璁歌繘鍏ョ郴缁熺殑瑙掕壊锛屼笌鍚庣 _ENTRY_ROLES 涓€鑷达紱PENDING_MEMBER 涓哄緟瀹℃牳涓嶅彲杩涚郴缁? */
  const ENTRY_ROLES = [
    'ADMIN',
    'SUB_ADMIN',
    'QGS_DIRECTOR',
    'QGS_LEADER',
    'QGS_MEMBER',
    'HGS_DIRECTOR',
    'HGS_LEADER',
    'HGS_MEMBER'
  ];

  async function syncDisplayNameFromProfile(fallbackName: string) {
    const { data, error } = await fetchMyProfile();
    if (error || !data) {
      userInfo.userName = fallbackName;
      return;
    }

    const alias = (data.alias || '').trim();
    const user = (data.user || '').trim();
    userInfo.userName = alias || user || fallbackName;
  }

  async function loginByToken(loginToken: Api.Auth.LoginToken) {
    const accessToken = loginToken.access_token ?? loginToken.token;
    if (!accessToken) return false;
    localStg.set('token', accessToken);
    if (loginToken.refreshToken) localStg.set('refreshToken', loginToken.refreshToken);

    // 浼樺厛浣跨敤鐧诲綍/娉ㄥ唽鍝嶅簲閲岀殑 user锛屽皯涓€娆?/auth/me 璇锋眰锛屽姞蹇烦杞?
    if (loginToken.user) {
      const u = loginToken.user;
      userInfo.userId = String(u.id);
      userInfo.userName = u.role;
      userInfo.roles = [u.role];
      userInfo.buttons = [];
      userInfo.homeRoute = u.home_route || null;
      userInfo.availableHomeRoutes = Array.isArray(u.available_home_routes) ? [...u.available_home_routes] : [];
      await syncDisplayNameFromProfile(u.role);
    } else {
      const pass = await getUserInfo();
      if (!pass) return false;
    }

    // 寰呭鏍告垨鏃犳寮忚鑹诧細涓嶅厑璁歌繘鍏ョ郴缁燂紝鎻愮ず鍚庢竻闄ょ櫥褰曟€?
    const hasEntryRole = userInfo.roles.some((r: string) => ENTRY_ROLES.includes(r));
    if (!hasEntryRole) {
      const msg = $t('page.login.common.accountPending');
      window.$message?.warning(msg);
      resetStore();
      return false;
    }

    token.value = accessToken;
    return true;
  }

  async function getUserInfo() {
    const { data: info, error } = await fetchGetUserInfo();

    if (!error && info) {
      userInfo.userId = String(info.id);
      userInfo.userName = info.role;
      userInfo.roles = [info.role];
      userInfo.buttons = [];
      userInfo.homeRoute = info.home_route || null;
      userInfo.availableHomeRoutes = Array.isArray(info.available_home_routes) ? [...info.available_home_routes] : [];
      await syncDisplayNameFromProfile(info.role);
      // 鑻ュ悗绔繑鍥炲緟瀹℃牳瑙掕壊锛屼笉鍏佽杩涘叆绯荤粺锛堣矾鐢卞畧鍗篃浼氬湪 initUserInfo 鍚庡仛鍚屾牱鍒ゆ柇锛?
      const hasEntryRole = userInfo.roles.some((r: string) => ENTRY_ROLES.includes(r));
      if (!hasEntryRole) {
        const msg = $t('page.login.common.accountPending');
        window.$message?.warning(msg);
        resetStore();
        return false;
      }
      return true;
    }

    return false;
  }

  async function initUserInfo() {
    const hasToken = getToken();

    if (hasToken) {
      const pass = await getUserInfo();

      if (!pass) {
        resetStore();
      }
    }
  }

  return {
    token,
    userInfo,
    isStaticSuper,
    isLogin,
    loginLoading,
    resetStore,
    login,
    loginByToken,
    initUserInfo
  };
});

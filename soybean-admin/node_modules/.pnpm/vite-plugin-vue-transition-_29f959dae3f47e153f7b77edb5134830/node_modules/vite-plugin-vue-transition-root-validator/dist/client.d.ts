import { App } from "vue";

//#region src/types.d.ts

type Lang = 'en' | 'zh';
//#endregion
//#region src/client.d.ts
/**
 * 客户端配置选项
 */
type SetupOptions = {
  /** 界面语言，默认 'en' */
  lang?: Lang;
  /** 是否在检测到错误后自动禁用检测（避免重复报错），默认 false */
  disableAfterFirstError?: boolean;
};
/**
 * 设置 Vue Root Validator
 *
 * 在 Vue 应用上注册 warnHandler 来捕获 Transition 多根节点警告
 *
 * @param app - Vue 应用实例
 * @param options - 配置选项
 *
 * @example
 * ```ts
 * import { createApp } from 'vue';
 * import { setupVueRootValidator } from 'virtual:vue-transition-root-validator';
 * import App from './App.vue';
 *
 * const app = createApp(App);
 *
 * // 在挂载前设置验证器
 * setupVueRootValidator(app, { lang: 'zh' });
 *
 * app.mount('#app');
 * ```
 */
declare function setupVueRootValidator(app: App, options?: SetupOptions): void;
//#endregion
export { setupVueRootValidator };
//# sourceMappingURL=client-DdpHavRX.d.ts.map
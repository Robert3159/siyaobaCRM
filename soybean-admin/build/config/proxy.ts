import type { ProxyOptions } from 'vite';
import { bgRed, bgYellow, green, lightBlue } from 'kolorist';
import { consola } from 'consola';
import { createServiceConfig } from '../../src/utils/service';

/**
 * Set http proxy
 *
 * @param env - The current env
 * @param enable - If enable http proxy
 */
const LOCAL_BACKEND = 'http://localhost:8026/api';

export function createViteProxy(env: Env.ImportMeta, enable: boolean) {
  const isEnableHttpProxy = enable && env.VITE_HTTP_PROXY === 'Y';

  if (!isEnableHttpProxy) return undefined;

  const isEnableProxyLog = env.VITE_PROXY_LOG === 'Y';

  const { baseURL, proxyPattern, other } = createServiceConfig(env);

  // 开发环境下若 baseURL 指向 mock/apifox，强制使用本地后端，避免 404
  const resolvedBaseURL =
    enable && (baseURL || '').includes('apifox')
      ? LOCAL_BACKEND
      : baseURL || LOCAL_BACKEND;

  const proxy: Record<string, ProxyOptions> = createProxyItem(
    { baseURL: resolvedBaseURL, proxyPattern },
    isEnableProxyLog
  );

  other.forEach(item => {
    Object.assign(proxy, createProxyItem(item, isEnableProxyLog));
  });

  return proxy;
}

function createProxyItem(item: App.Service.ServiceConfigItem, enableLog: boolean) {
  const proxy: Record<string, ProxyOptions> = {};

  // target 使用 origin（无 path），rewrite 时显式加上 baseURL 的 path，确保转发到 /api/xxx
  const targetUrl = new URL(item.baseURL);
  const targetOrigin = targetUrl.origin;
  const basePath = targetUrl.pathname.replace(/\/$/, '') || '';

  proxy[item.proxyPattern] = {
    target: targetOrigin,
    changeOrigin: true,
    configure: (_proxy, options) => {
      _proxy.on('proxyReq', (_proxyReq, req, _res) => {
        if (!enableLog) return;

        const requestUrl = `${lightBlue('[proxy url]')}: ${bgYellow(` ${req.method} `)} ${green(`${item.proxyPattern}${req.url}`)}`;

        const proxyUrl = `${lightBlue('[real request url]')}: ${green(`${options.target}${basePath}${req.url?.replace(new RegExp(`^${item.proxyPattern}`), '') || ''}`)}`;

        consola.log(`${requestUrl}\n${proxyUrl}`);
      });
      _proxy.on('error', (_err, req, _res) => {
        if (!enableLog) return;
        consola.log(bgRed(`Error: ${req.method} `), green(`${options.target}${req.url}`));
      });
    },
    rewrite: path => {
      const rest = path.replace(new RegExp(`^${item.proxyPattern}`), '');
      return basePath ? `${basePath}${rest}` : rest;
    }
  };

  return proxy;
}

import process from 'node:process';
import { URL, fileURLToPath } from 'node:url';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { defineConfig, loadEnv } from 'vite';
import { setupVitePlugins } from './build/plugins';
import { createViteProxy, getBuildTime } from './build/config';

/**
 * 读取后端端口（从 backend/.port 文件）
 */
function getBackendPort(): number | null {
  const portFilePath = path.resolve(__dirname, '../backend/.port');
  try {
    if (fs.existsSync(portFilePath)) {
      const port = Number.parseInt(fs.readFileSync(portFilePath, 'utf-8').trim(), 10);
      if (!Number.isNaN(port) && port > 0 && port < 65536) {
        // eslint-disable-next-line no-console
        console.log(`[Vite] 读取到后端端口: ${port}`);
        return port;
      }
    }
  } catch (e) {
    // eslint-disable-next-line no-console
    console.log(`[Vite] 无法读取后端端口文件: ${e}`);
  }
  return null;
}

export default defineConfig(configEnv => {
  const viteEnv = loadEnv(configEnv.mode, process.cwd()) as unknown as Env.ImportMeta;

  const buildTime = getBuildTime();

  const enableProxy = configEnv.command === 'serve' && !configEnv.isPreview;

  // 获取后端端口
  const backendPort = getBackendPort();

  return {
    base: viteEnv.VITE_BASE_URL,
    resolve: {
      alias: {
        '~': fileURLToPath(new URL('./', import.meta.url)),
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern-compiler',
          additionalData: `@use "@/styles/scss/global.scss" as *;`
        }
      }
    },
    plugins: setupVitePlugins(viteEnv, buildTime),
    define: {
      BUILD_TIME: JSON.stringify(buildTime)
    },
    server: {
      host: '0.0.0.0',
      port: 9527,
      open: true,
      proxy: createViteProxy(viteEnv, enableProxy, backendPort)
    },
    preview: {
      port: 9725
    },
    build: {
      reportCompressedSize: false,
      sourcemap: viteEnv.VITE_SOURCE_MAP === 'Y',
      commonjsOptions: {
        ignoreTryCatch: false
      }
    }
  };
});

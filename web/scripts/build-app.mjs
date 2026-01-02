import { mkdirSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = resolve(__dirname, '..');
const distDir = resolve(projectRoot, 'dist');
const appEntry = resolve(projectRoot, 'src', 'index.tsx');

if (!existsSync(appEntry)) {
  throw new Error(`Missing app entry file: ${appEntry}`);
}

mkdirSync(distDir, { recursive: true });

const isDev = process.env.NODE_ENV === 'development';

const buildOptions = {
  entryPoints: [appEntry],
  bundle: true,
  format: 'iife',
  outfile: resolve(distDir, 'app.js'),
  target: ['es2020'],
  sourcemap: false,
  minify: !isDev,
  jsx: 'automatic',
  logLevel: 'info',
  define: {
    'process.env.NODE_ENV': isDev ? '"development"' : '"production"',
    'process.env.API_BASE_URL': JSON.stringify(process.env.API_BASE_URL || 'http://localhost:8000')
  }
};

// Create HTML file for the app
const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NumbyAI - Finance Budgeting App</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f8fafc;
    }
    #root {
      min-height: 100vh;
    }
  </style>
</head>
<body>
  <div id="root"></div>
  <script src="/static/app.js"></script>
</body>
</html>`;

async function buildApp() {
  console.log('Building React app...');
  await build(buildOptions);
  writeFileSync(resolve(distDir, 'index.html'), htmlContent);
  console.log('✔ React app built successfully');
  console.log(`✔ HTML file created: ${resolve(distDir, 'index.html')}`);
}

buildApp().catch(err => {
  console.error('✗ Build failed:', err);
  process.exit(1);
});

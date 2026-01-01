import { mkdirSync, rmSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, resolve, relative, basename, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build, context } from 'esbuild';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = resolve(__dirname, '..');
const distDir = resolve(projectRoot, 'dist');
const widgetsConfigPath = resolve(projectRoot, 'widgets.config.json');
const isWatchMode = process.argv.includes('--watch');

if (!existsSync(widgetsConfigPath)) {
  throw new Error(`Missing widgets.config.json at ${widgetsConfigPath}`);
}

const widgetsConfig = JSON.parse(readFileSync(widgetsConfigPath, 'utf8'));
const entryPoints = widgetsConfig.map((widget) => {
  const entryPath = resolve(projectRoot, 'src', 'widgets', `${widget.entry}.tsx`);
  if (!existsSync(entryPath)) {
    throw new Error(`Missing widget entry file for ${widget.name}: ${entryPath}`);
  }
  return entryPath;
});

// Add dev mode entry point if DATA_SOURCE=mock
const dataSource = process.env.DATA_SOURCE;
if (dataSource === 'mock') {
  const devEntryPath = resolve(projectRoot, 'src', 'widgets', 'dashboard-dev.tsx');
  if (existsSync(devEntryPath)) {
    entryPoints.push(devEntryPath);
    console.log('📦 Building with MOCK data mode (dashboard-dev.tsx included)');
  }
}

if (entryPoints.length === 0) {
  throw new Error('No widget entry points found. Add files to src/widgets/*.tsx');
}

rmSync(distDir, { recursive: true, force: true });
mkdirSync(distDir, { recursive: true });

// Check if we're in dev mode (no minification for better errors)
const isDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev');

const buildOptions = {
  entryPoints,
  bundle: true,
  format: 'esm',
  outdir: distDir,
  entryNames: '[name]-[hash]',
  chunkNames: 'chunk-[hash]',
  assetNames: 'asset-[name]-[hash]',
  splitting: false,
  target: ['es2020'],
  sourcemap: false,      // Disable sourcemaps to avoid CSP eval issues
  minify: !isDev,        // Disable minification in dev mode
  metafile: true,
  jsx: 'automatic',
  logLevel: 'info',
  conditions: isDev ? ['development'] : ['production'],  // Use React development build
  define: {
    'process.env.NODE_ENV': isDev ? '"development"' : '"production"'
  }
};

async function writeManifest(metafile) {
  if (!metafile) {
    console.warn('No metafile produced by esbuild; skipping manifest generation.');
    return;
  }

  const manifest = {};
  for (const [outPath, output] of Object.entries(metafile.outputs)) {
    if (!output.entryPoint) continue;
    const entryName = basename(output.entryPoint, extname(output.entryPoint));
    const relativePath = relative(distDir, resolve(projectRoot, outPath)).replace(/\\/g, '/');
    manifest[entryName] = relativePath;
  }

  const manifestPath = resolve(distDir, 'widget-manifest.json');
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(`✔ Wrote widget manifest -> ${manifestPath}`);
}

async function runOnce() {
  const result = await build(buildOptions);
  await writeManifest(result.metafile);
  console.log('✔ Widgets bundled (per-widget artifacts)');
}

if (isWatchMode) {
  const ctx = await context(buildOptions);
  try {
    const initial = await ctx.rebuild();
    await writeManifest(initial.metafile);
    await ctx.watch({
      async onRebuild(error, result) {
        if (error) {
          console.error('✗ Rebuild failed:', error);
        } else if (result) {
          await writeManifest(result.metafile);
          console.log('✔ Rebuilt widgets');
        }
      },
    });
    console.log('👀 Watching widget sources for changes (Ctrl+C to exit)');
  } catch (err) {
    console.error('✗ Initial build failed:', err);
    await ctx.dispose();
    process.exit(1);
  }
} else {
  await runOnce();
}

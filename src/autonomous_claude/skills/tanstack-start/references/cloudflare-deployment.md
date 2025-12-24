# Cloudflare Workers Deployment

## Quick Reference

| Use Case | Solution |
|----------|----------|
| Server code in route loaders | `createServerFn()` |
| Server code from client event handlers | API routes (`server.handlers`) work best |
| Access Cloudflare bindings | `import { env } from 'cloudflare:workers'` |

## Setup

```bash
pnpm add -D @cloudflare/vite-plugin wrangler
```

## Configuration

**vite.config.ts** - add cloudflare plugin:
```typescript
import { cloudflare } from '@cloudflare/vite-plugin'

export default defineConfig({
  plugins: [
    tsConfigPaths(),
    cloudflare({ viteEnvironment: { name: 'ssr' } }),
    tanstackStart(),
    viteReact(),
  ],
})
```

**wrangler.jsonc**:
```jsonc
{
  "$schema": "./node_modules/wrangler/config-schema.json",
  "name": "my-app",
  "compatibility_date": "<CURRENT_DATE>",  // Use today's YYYY-MM-DD
  "compatibility_flags": ["nodejs_compat"],
  "main": "@tanstack/react-start/server-entry",
  "observability": {
    "enabled": true
  }
}
```

**package.json scripts**:
```json
{
  "scripts": {
    "preview": "pnpm build && vite preview",
    "deploy": "pnpm build && wrangler deploy",
    "cf-typegen": "wrangler types"
  }
}
```

## Deploy

```bash
pnpm dlx wrangler login
pnpm deploy
```

## Local Preview

Test your production build locally before deploying:
```bash
pnpm preview
```

## Static Prerendering

Generate static HTML at build time. Requires `@tanstack/react-start` v1.138.0+.

**vite.config.ts**:
```typescript
tanstackStart({
  prerender: {
    enabled: true,
  },
})
```

> **Important**: Prerendering runs during build and uses **local** environment variables, secrets, and bindings data. Use remote bindings for production data.

### CI/CD Prerendering

Create `.env` with variable references:
```bash
API_KEY=${API_KEY}
DATABASE_URL=${DATABASE_URL}
```

In CI, set `CLOUDFLARE_INCLUDE_PROCESS_ENV=true` and provide the actual values.

For local dev, create `.env.local` with actual values (gitignored).

## Bindings (KV, R2, D1)

**Access in server functions:**
```typescript
import { env } from 'cloudflare:workers'

const getData = createServerFn().handler(async () => {
  const value = await env.MY_KV.get('key')
  return { value, apiKey: env.API_KEY }
})
```

**wrangler.jsonc with bindings:**
```jsonc
{
  "kv_namespaces": [{ "binding": "MY_KV", "id": "kv-id" }],
  "r2_buckets": [{ "binding": "MY_BUCKET", "bucket_name": "bucket" }],
  "d1_databases": [{ "binding": "MY_DB", "database_id": "d1-id" }],
  "vars": { "API_KEY": "value" }
}
```

**Generate types:** `pnpm cf-typegen`

## Secrets

```bash
pnpm dlx wrangler secret put SECRET_NAME
```

## Custom Domains

```jsonc
{ "routes": [{ "pattern": "app.example.com", "custom_domain": true }] }
```

## GitHub Actions

See [github-actions-deploy.md](github-actions-deploy.md) for complete CI/CD setup including preview deployments and branch routing.

## Troubleshooting

- **"Cannot find module"**: Add `nodejs_compat` to compatibility_flags
- **Logs**: `pnpm dlx wrangler tail`
- **Auth issues**: `wrangler logout && wrangler login`

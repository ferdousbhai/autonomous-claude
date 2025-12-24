# Migration to TanStack Start

Convert existing React/Vite apps to TanStack Start.

## 1. Install Dependencies

```bash
pnpm add @tanstack/react-start @tanstack/react-router
pnpm add -D vite-tsconfig-paths
```

## 2. Update package.json

```json
{
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build"
  }
}
```

## 3. Update vite.config.ts

```typescript
import { defineConfig } from 'vite'
import tsConfigPaths from 'vite-tsconfig-paths'
import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import viteReact from '@vitejs/plugin-react'

export default defineConfig({
  server: { port: 3000 },
  plugins: [
    tsConfigPaths(),
    tanstackStart(),
    viteReact(),  // MUST come AFTER tanstackStart
  ],
})
```

## 4. Update tsconfig.json

```json
{
  "compilerOptions": {
    "jsx": "react-jsx",
    "moduleResolution": "Bundler",
    "module": "ESNext",
    "target": "ES2022",
    "skipLibCheck": true,
    "strictNullChecks": true
  }
}
```

**Warning:** Do NOT enable `verbatimModuleSyntax` - leaks server code to client.

## 5. Create Router

```typescript
// src/router.tsx
import { createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'

export function getRouter() {
  return createRouter({
    routeTree,
    scrollRestoration: true,
  })
}
```

## 6. Create Root Route

```tsx
// src/routes/__root.tsx
import type { ReactNode } from 'react'
import { Outlet, createRootRoute, HeadContent, Scripts } from '@tanstack/react-router'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title: 'My App' },
    ],
  }),
  component: RootComponent,
})

function RootComponent() {
  return (
    <html>
      <head><HeadContent /></head>
      <body>
        <Outlet />
        <Scripts />
      </body>
    </html>
  )
}
```

## 7. Create Index Route

```tsx
// src/routes/index.tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: () => <div>Hello TanStack Start</div>,
})
```

## 8. Delete Old Entry Points

Remove:
- `index.html`
- `src/main.tsx` or `src/index.tsx`
- Any `<App />` wrapper components

## 9. Run Dev Server

```bash
pnpm dev
```

TanStack Start auto-generates `src/routeTree.gen.ts` on first run.

## Migrating Components

Move existing components into route files or import them:

```tsx
// src/routes/dashboard.tsx
import { createFileRoute } from '@tanstack/react-router'
import { Dashboard } from '../components/Dashboard'  // existing component

export const Route = createFileRoute('/dashboard')({
  component: Dashboard,
})
```

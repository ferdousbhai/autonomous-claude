# Server Functions

Server-only code callable from anywhere (components, loaders, handlers).

## When to Use What

| Use Case | Solution |
|----------|----------|
| Server code in route loaders | `createServerFn()` |
| Server code from client event handlers | API routes (`server.handlers`) work best |
| Access Cloudflare bindings | `import { env } from 'cloudflare:workers'` |

> **Cloudflare Workers note:** For client-side event handlers, prefer API routes over calling `createServerFn()` directly. See [API Routes](#api-routes) below.

## createServerFn API

```typescript
import { createServerFn } from '@tanstack/react-start'

// GET (default)
export const getData = createServerFn().handler(async () => {
  return await db.find()
})

// POST with validation
export const saveData = createServerFn({ method: 'POST' })
  .inputValidator((d: { id: string }) => d)
  .handler(async ({ data }) => {
    return await db.save(data.id)
  })

// With Zod
import { z } from 'zod'
export const createUser = createServerFn({ method: 'POST' })
  .inputValidator(z.object({ name: z.string(), age: z.number() }))
  .handler(async ({ data }) => data.name)
```

## Calling from Components

Server functions can be called directly from anywhere:

```tsx
// Event handler - direct call
function DeleteButton({ id }: { id: string }) {
  const router = useRouter()

  return (
    <button onClick={async () => {
      await deletePost({ data: { id } })
      router.invalidate()
    }}>
      Delete
    </button>
  )
}
```

For initial page data, preload in loaders (see [query-integration.md](query-integration.md)).

## Request/Response Context

```typescript
import {
  getRequest,
  getRequestHeader,
  getRequestHeaders,
  setResponseHeader,
  setResponseStatus,
  getCookies,
} from '@tanstack/react-start/server'

export const handler = createServerFn().handler(async () => {
  const auth = getRequestHeader('authorization')
  const allHeaders = getRequestHeaders()
  const cookies = getCookies()

  setResponseHeader('X-Custom', 'value')
  setResponseStatus(201)

  return { success: true }
})
```

## Error Handling

```typescript
import { redirect, notFound } from '@tanstack/react-router'

export const protectedFn = createServerFn().handler(async () => {
  const user = await getUser()
  if (!user) throw redirect({ to: '/login' })

  const data = await getData()
  if (!data) throw notFound()

  return data
})
```

## Middleware

```typescript
import { createMiddleware, createServerFn } from '@tanstack/react-start'
import { zodValidator } from '@tanstack/zod-adapter'

const authMiddleware = createMiddleware({ type: 'function' })
  .server(async ({ next }) => {
    const user = await getUser()
    if (!user) throw new Error('Unauthorized')
    return next({ context: { user } })
  })

const validationMiddleware = createMiddleware({ type: 'function' })
  .inputValidator(zodValidator(z.object({ id: z.string() })))
  .server(async ({ next, data }) => next())

// Compose
export const protectedFn = createServerFn({ method: 'POST' })
  .middleware([authMiddleware, validationMiddleware])
  .handler(async ({ context }) => context.user)
```

## Global Middleware

```typescript
import { createStart, createMiddleware } from '@tanstack/react-start'

const globalMiddleware = createMiddleware({ type: 'function' })
  .server(async ({ next }) => {
    // Runs for all server functions
    return next()
  })

export const startInstance = createStart(() => ({
  functionMiddleware: [globalMiddleware],
}))
```

## Environment Variables

- **Server functions**: `process.env.VAR_NAME` (any variable)
- **Client code**: `import.meta.env.VITE_VAR_NAME` (VITE_ prefix only)

## API Routes

For client event handlers (onClick, onSubmit, etc.), use `server.handlers` instead of calling `createServerFn()` directly. This works better on Cloudflare Workers.

```tsx
// routes/api/users.ts - API route file
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/api/users')({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const users = await db.users.findMany()
        return Response.json(users)
      },
      POST: async ({ request }) => {
        const body = await request.json()
        const user = await db.users.create(body)
        return Response.json(user, { status: 201 })
      },
    },
  },
})
```

**Calling from components:**

```tsx
function UserList() {
  const [users, setUsers] = useState([])

  const loadUsers = async () => {
    const res = await fetch('/api/users')
    setUsers(await res.json())
  }

  const createUser = async (name: string) => {
    await fetch('/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    loadUsers()  // Refresh list
  }

  return (
    <button onClick={() => createUser('New User')}>Add User</button>
  )
}
```

**With route-level middleware:**

```tsx
export const Route = createFileRoute('/api/protected')({
  server: {
    middleware: [authMiddleware],  // Applies to all handlers
    handlers: {
      GET: async ({ request, context }) => {
        // context.user available from middleware
        return Response.json({ user: context.user })
      },
    },
  },
})
```

**Dynamic route parameters:**

```tsx
// routes/api/users.$id.ts
export const Route = createFileRoute('/api/users/$id')({
  server: {
    handlers: {
      GET: async ({ params }) => {
        const user = await db.users.findById(params.id)
        return Response.json(user)
      },
      DELETE: async ({ params }) => {
        await db.users.delete(params.id)
        return new Response(null, { status: 204 })
      },
    },
  },
})
```

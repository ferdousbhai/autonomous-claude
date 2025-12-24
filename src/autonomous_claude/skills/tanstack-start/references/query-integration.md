# TanStack Query Integration

## Setup

```bash
pnpm add @tanstack/react-query @tanstack/react-router-ssr-query
```

```tsx
// src/router.tsx
import { QueryClient } from '@tanstack/react-query'
import { createRouter } from '@tanstack/react-router'
import { setupRouterSsrQueryIntegration } from '@tanstack/react-router-ssr-query'
import { routeTree } from './routeTree.gen'

export function getRouter() {
  const queryClient = new QueryClient()
  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreload: 'intent',
  })

  setupRouterSsrQueryIntegration({ router, queryClient })
  return router
}
```

## Data Loading Pattern

Preload in loaders to avoid loading flashes, waterfalls, and SEO issues:

```tsx
import { queryOptions, useSuspenseQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'

const postsQueryOptions = queryOptions({
  queryKey: ['posts'],
  queryFn: () => fetch('/api/posts').then(r => r.json()),
})

export const Route = createFileRoute('/posts')({
  loader: ({ context }) => context.queryClient.ensureQueryData(postsQueryOptions),
  component: PostsPage,
})

function PostsPage() {
  const { data } = useSuspenseQuery(postsQueryOptions)
  return <div>{data.map((p: any) => p.title).join(', ')}</div>
}
```

## Non-Blocking Streaming

Start query without awaiting - streams to client:

```tsx
loader: ({ params, context }) => {
  context.queryClient.fetchQuery(userQuery(params.id))  // No await
}
```

## Error Handling

```tsx
import { useQueryErrorResetBoundary } from '@tanstack/react-query'

export const Route = createFileRoute('/')({
  loader: ({ context }) => context.queryClient.ensureQueryData(postsQueryOptions),
  errorComponent: ({ error }) => {
    const router = useRouter()
    const { reset } = useQueryErrorResetBoundary()

    useEffect(() => { reset() }, [reset])

    return (
      <div>
        {error.message}
        <button onClick={() => router.invalidate()}>Retry</button>
      </div>
    )
  },
})
```

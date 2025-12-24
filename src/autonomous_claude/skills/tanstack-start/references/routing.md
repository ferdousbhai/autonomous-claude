# TanStack Router

File-based routing in `src/routes/`.

## File Naming

| Pattern | Route | Notes |
|---------|-------|-------|
| `index.tsx` | `/` | Index |
| `about.tsx` | `/about` | Static |
| `posts.$postId.tsx` | `/posts/:postId` | Dynamic |
| `$.tsx` | `/*` | Catch-all |
| `_layout.tsx` | - | Layout wrapper |
| `__root.tsx` | - | Root (required) |

**Prefixes:** `$` = dynamic, `_` = pathless layout

## Route with Loader

```tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/posts/$postId')({
  loader: async ({ params }) => fetchPost(params.postId),
  component: () => {
    const post = Route.useLoaderData()
    const { postId } = Route.useParams()
    return <h1>{post.title}</h1>
  },
})
```

## Search Params

```tsx
import { z } from 'zod'

export const Route = createFileRoute('/search')({
  validateSearch: z.object({
    query: z.string().optional(),
    page: z.number().default(1),
  }),
  loaderDeps: ({ search }) => ({ search }),
  loader: async ({ deps: { search } }) => searchItems(search.query, search.page),
  component: () => {
    const { query } = Route.useSearch()
    return <div>Results for: {query}</div>
  },
})
```

## Navigation

```tsx
import { Link, useNavigate, useRouter } from '@tanstack/react-router'

<Link to="/posts/$postId" params={{ postId: '123' }}>Post</Link>
<Link to="/search" search={{ query: 'react' }}>Search</Link>

const navigate = useNavigate()
navigate({ to: '/posts/$postId', params: { postId: '123' } })

const router = useRouter()
router.invalidate()  // Refresh data
```

## Error/NotFound

```tsx
import { notFound } from '@tanstack/react-router'

export const Route = createFileRoute('/posts/$postId')({
  loader: async ({ params }) => {
    const post = await fetchPost(params.postId)
    if (!post) throw notFound()
    return post
  },
  notFoundComponent: () => <div>Not found</div>,
  errorComponent: ({ error, reset }) => <button onClick={reset}>{error.message}</button>,
})
```

## Route Context

```tsx
// router.tsx
export function getRouter() {
  return createRouter({ routeTree, context: { auth: undefined! } })
}

// __root.tsx
import { createRootRouteWithContext } from '@tanstack/react-router'
export const Route = createRootRouteWithContext<{ auth: AuthContext }>()({...})

// Protected route
export const Route = createFileRoute('/dashboard')({
  beforeLoad: async ({ context }) => {
    if (!context.auth.user) throw redirect({ to: '/login' })
  },
})
```

## Head/Meta

```tsx
export const Route = createFileRoute('/posts/$postId')({
  loader: ({ params }) => fetchPost(params.postId),
  head: ({ loaderData }) => ({
    meta: [
      { title: loaderData.title },
      { name: 'description', content: loaderData.excerpt },
    ],
  }),
})
```

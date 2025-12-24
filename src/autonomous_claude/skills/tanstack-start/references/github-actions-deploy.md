# GitHub Actions Deployment

Auto-deploy TanStack Start to Cloudflare Workers on git push.

## Setup

1. Create Cloudflare API token at https://dash.cloudflare.com/profile/api-tokens
   - Use "Edit Cloudflare Workers" template
   - Or custom with: Account > Workers Scripts: Edit, Zone > Workers Routes: Edit

2. Add secrets in GitHub repo Settings > Secrets and variables > Actions:
   - `CLOUDFLARE_API_TOKEN` - Your API token
   - `CLOUDFLARE_ACCOUNT_ID` - Found in Workers dashboard URL or sidebar

## Basic Workflow

`.github/workflows/deploy.yml`:
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm

      - run: pnpm install --frozen-lockfile

      - run: pnpm build

      - uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
```

## Preview Deployments

Deploy PRs to preview URLs:

```yaml
name: Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write  # For PR comments
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm

      - run: pnpm install --frozen-lockfile

      - run: pnpm build

      - name: Deploy to Cloudflare
        id: deploy
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: deploy --env ${{ github.event_name == 'pull_request' && 'preview' || 'production' }}

      - name: Comment PR with preview URL
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `🚀 Preview deployed: ${{ steps.deploy.outputs.deployment-url }}`
            })
```

**wrangler.jsonc** for preview environments:
```jsonc
{
  "name": "my-app",
  "env": {
    "preview": {
      "name": "my-app-preview"
    },
    "production": {
      "name": "my-app"
    }
  }
}
```

## With Secrets/Bindings

Pass secrets to the build:

```yaml
- run: pnpm build
  env:
    API_KEY: ${{ secrets.API_KEY }}

- uses: cloudflare/wrangler-action@v3
  with:
    apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
    secrets: |
      API_KEY
  env:
    API_KEY: ${{ secrets.API_KEY }}
```

## Caching for Faster Builds

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache
      .vinxi
    key: ${{ runner.os }}-build-${{ hashFiles('**/pnpm-lock.yaml') }}
    restore-keys: |
      ${{ runner.os }}-build-
```

## Branch-based Routing

Deploy different branches to different subdomains:

```yaml
- uses: cloudflare/wrangler-action@v3
  with:
    apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
    command: deploy --env ${{ github.ref_name }}
```

**wrangler.jsonc**:
```jsonc
{
  "env": {
    "main": {
      "name": "my-app",
      "routes": [{ "pattern": "app.example.com", "custom_domain": true }]
    },
    "staging": {
      "name": "my-app-staging",
      "routes": [{ "pattern": "staging.example.com", "custom_domain": true }]
    }
  }
}
```

## Debugging Failed Deploys

View logs after deployment:
```yaml
- name: Tail logs
  if: failure()
  run: npx wrangler tail --once
  env:
    CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
```

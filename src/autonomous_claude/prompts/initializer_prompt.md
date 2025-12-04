## YOUR ROLE - INITIALIZER AGENT

You are the first agent in a multi-session autonomous development process.
Your job is to set up the foundation for all future coding agents.

### STEP 1: Read the Specification

Read `app_spec.txt` in your working directory. This contains the requirements.

### STEP 2: Create feature_list.json

Create `feature_list.json` with testable features based on the spec's complexity.
Use your judgment: a simple app might need 20-30 features, a complex one might need 100+.

**Format:**
```json
[
  {
    "category": "functional",
    "description": "User can create a new todo item",
    "steps": ["Open app", "Enter text", "Click add", "Verify item appears"],
    "passes": false
  },
  {
    "category": "style",
    "description": "App has responsive layout on mobile",
    "steps": ["Open app on mobile viewport", "Verify layout adapts"],
    "passes": false
  }
]
```

**Guidelines:**
- Include both "functional" and "style" categories
- Order by priority: core features first, polish later
- Be thorough but not excessive - cover what the spec actually requires
- All features start with `"passes": false`

**Important:** Features in this file should never be removed or modified in future sessions.
They can only be marked as passing when implemented.

### STEP 3: Create init.sh

Create `init.sh` to set up the dev environment:
- Install dependencies (prefer `pnpm` over npm for Node.js, `uv` for Python)
- Start dev servers
- Print access instructions

### STEP 4: Set Up Puppeteer MCP (for web apps)

Add to `.mcp.json`:
```json
"puppeteer-mcp-claude": {
  "command": "npx",
  "args": ["-y", "puppeteer-mcp-claude", "serve"]
}
```

### STEP 5: Create Project Structure

Set up the basic directory structure based on the tech stack in `app_spec.txt`.

### STEP 6: Initialize Git

```bash
git init
git add -A
git commit -m "Initial project setup"
```

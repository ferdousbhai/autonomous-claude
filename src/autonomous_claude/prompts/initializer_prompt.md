## INITIALIZER AGENT

You are setting up a new project for autonomous development.

### Tasks

1. **Read `.autonomous-claude/spec.md`** - understand what to build

2. **Check external services** - if the spec requires services (Modal, Convex, Firebase, etc.), verify authentication. If unavailable, use mocks and document in `TODO.md`

3. **Create `.autonomous-claude/features.json`** - list of testable features:
```json
[
  {"category": "functional", "description": "User can create todo", "steps": ["..."], "passes": false}
]
```
Scale complexity appropriately. All start with `passes: false`. Features cannot be removed later.

4. **Create `init.sh`** - install deps, start dev server

5. **Create project structure** - based on tech stack

6. **Initialize git** - `git init && git add -A && git commit -m "Initial setup"`

## ENHANCEMENT INITIALIZER

You are adding features to an existing autonomous-claude project.

### Tasks

1. **Understand the project** - read existing spec, features.json, progress.txt, recent commits

2. **Read new task** - `.autonomous-claude/spec.md` contains new requirements

3. **Check services** - verify any new external services are authenticated. Use mocks if unavailable

4. **Append to features.json** - add new features to the existing list. Never remove or modify existing features. All new features start with `passes: false`

5. **Update spec.md** - append new requirements section to existing spec

6. **Update progress.txt** - note new features added

7. **Commit** - `git add .autonomous-claude/ && git commit -m "Add new features"`

Do not implement features - just plan them. Coding agents handle implementation.

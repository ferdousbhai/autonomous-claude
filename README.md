# autonomous-claude

Build apps autonomously with Claude Code CLI. Uses your existing Claude subscription - no API key required.

Based on [Anthropic's long-running agents guide](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

## Installation

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install autonomous-claude
uv tool install autonomous-claude
```

Or install from source:
```bash
git clone https://github.com/ferdousbhai/autonomous-claude.git
cd autonomous-claude
uv tool install .
```

### Prerequisites

Claude Code CLI must be installed and authenticated:

```bash
npm install -g @anthropic-ai/claude-code
claude login
```

## Usage

### Build a new app

```bash
# From a description
autonomous-claude build "An Apple Notes clone as a web app - uses local directory structure and .md files for storage, supports folders, rich text editing, and search"

# From a spec file
autonomous-claude build ./app-spec.md -o ./notes-app

# With options
autonomous-claude build "Markdown notes app with folder organization" -o ./notes -n 50
```

### Resume an existing project

Continue implementing existing features where you left off:

```bash
autonomous-claude resume ./notes-app
```

### Continue with new features

Add **new** features to any existing project - whether built with this tool or not.

> **Note:** If your project has incomplete features, you'll be asked to confirm. Use `resume` to continue without adding new features.

```bash
# Adopt an external project for maintenance
autonomous-claude continue ./my-nextjs-app "Add dark mode toggle and fix the sidebar collapse bug"

# Add new features to a project built with this tool
autonomous-claude continue ./notes-app "Add note sharing via public links and real-time collaboration"
```

### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--output` | `-o` | Output directory | prompted |
| `--model` | `-m` | Claude model | Claude Code default |
| `--max-sessions` | `-n` | Max sessions (Claude Code invocations) | 100 |
| `--timeout` | `-t` | Timeout per session (seconds) | 18000 (5 hours) |
| `--verbose` | `-V` | Stream Claude output in real-time | false |

### Configuration

Create `~/.config/autonomous-claude/config.toml` to customize defaults:

```toml
[session]
timeout = 18000        # Seconds per session (default: 5 hours)
max_turns = 2000       # Max turns per Claude session
max_sessions = 100     # Max Claude sessions before stopping
spec_timeout = 600     # Timeout for spec generation (10 minutes)

[tools]
allowed = ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]

[ui]
pending_display_limit = 10     # Max pending features to show
feature_name_max_length = 500  # Truncate long feature names
```

### Spec Confirmation

Before building, Claude generates a detailed spec from your description. You can review and request changes:

```
Accept? [y] n
What needs changing? Add offline support and keyboard shortcuts
Updating spec...
```

Type `y` (or press Enter) to accept, or describe what to change.

### Project Files

The tool creates these files in your project:

| File | Purpose |
|------|---------|
| `feature_list.json` | Tracks features and their completion status |
| `app_spec.txt` | The full application specification |
| `claude-progress.txt` | Session notes and progress updates |
| `.autonomous-claude/logs/` | Session logs (stdout, stderr, prompts) |

Use `--verbose` (`-V`) to stream Claude's output in real-time instead of showing a spinner.

## How It Works

### Building new projects (`build`)
1. **Session 1 (Initializer)**: Creates `feature_list.json` with testable features
2. **Sessions 2+ (Coding Agent)**: Implements features one by one, marking them as passing

### Adopting existing projects (`continue`)
1. **Session 1 (Adoption Initializer)**: Analyzes codebase, creates `feature_list.json` for requested tasks
2. **Sessions 2+ (Coding Agent)**: Implements the new features

### Adding features to existing projects (`continue` with `feature_list.json`)
1. **Session 1 (Enhancement Initializer)**: Appends new features to existing `feature_list.json`
2. **Sessions 2+ (Coding Agent)**: Implements the new features

Progress is persisted via `feature_list.json` and git commits. Press `Ctrl+C` to stop, then `resume` to continue.

## Example

```bash
$ autonomous-claude build "An Apple Notes clone - web app with local .md file storage, folder organization, rich text editing, and full-text search"
Project name: apple-notes-clone

╔═╗╦ ╦╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗╦ ╦╔═╗
╠═╣║ ║ ║ ║ ║║║║║ ║║║║║ ║║ ║╚═╗
╩ ╩╚═╝ ╩ ╚═╝╝╚╝╚═╝╩ ╩╚═╝╚═╝╚═╝
     Claude Code CLI

  Project     /home/user/apple-notes-clone
  Model       Claude Code default
  Sessions    100

Starting new project - initializer will run first
...
```

## Security Note

This tool uses `--dangerously-skip-permissions` for autonomous operation. Only run in trusted environments.

## License

MIT - Based on [Anthropic's claude-quickstarts](https://github.com/anthropics/claude-quickstarts)

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
autonomous-claude build "A todo app with React and SQLite"

# From a spec file
autonomous-claude build ./my-app-spec.txt -o ./my-app

# With options
autonomous-claude build "Blog with markdown" -o ./blog -n 5
```

### Resume an existing project

```bash
autonomous-claude resume ./my-app
```

### Continue with new features

Add new features to any existing project - whether built with this tool or not:

```bash
# Adopt an external project for maintenance
autonomous-claude continue ./existing-app "Add dark mode and fix login bug"

# Add new features to a project built with this tool
autonomous-claude continue ./my-app "Add user authentication"
```

### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--output` | `-o` | Output directory | auto-generated |
| `--model` | `-m` | Claude model | Claude Code default |
| `--max-iterations` | `-n` | Max iterations | unlimited |
| `--timeout` | `-t` | Timeout per session (seconds) | 1800 |

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
$ autonomous-claude build "A simple notes app with tags and search"

╔═╗╦ ╦╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗╦ ╦╔═╗
╠═╣║ ║ ║ ║ ║║║║║ ║║║║║ ║║ ║╚═╗
╩ ╩╚═╝ ╩ ╚═╝╝╚╝╚═╝╩ ╩╚═╝╚═╝╚═╝
     Claude Code CLI

  Project     /home/user/simple-notes-app
  Model       Claude Code default
  Iterations  unlimited

Starting new project - initializer will run first
...
```

## Security Note

This tool uses `--dangerously-skip-permissions` for autonomous operation. Only run in trusted environments.

## License

MIT - Based on [Anthropic's claude-quickstarts](https://github.com/anthropics/claude-quickstarts)

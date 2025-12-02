# Autonomous Coding Agent Demo

A minimal harness demonstrating long-running autonomous coding with Claude Code CLI. This demo implements a two-agent pattern (initializer + coding agent) that can build complete applications over multiple sessions.

**Uses your existing Claude Code subscription - no API key required!**

Based on [Anthropic's long-running agents guide](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

## Prerequisites

1. **Claude Code CLI** - Install and authenticate:

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Authenticate with your subscription
claude login
```

2. **uv** (Python package manager) - [Install uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Quick Start

```bash
# Clone and enter the directory
cd autonomous-claude-code

# Run the agent (uv handles dependencies automatically)
uv run autonomous_agent_demo.py --project-dir ./my_project
```

For testing with limited iterations:
```bash
uv run autonomous_agent_demo.py --project-dir ./my_project --max-iterations 3
```

## Important Timing Expectations

> **Warning: This demo takes a long time to run!**

- **First session (initialization):** The agent generates a `feature_list.json` with 200 test cases. This takes several minutes and may appear to hang - this is normal.

- **Subsequent sessions:** Each coding iteration can take **5-15 minutes** depending on complexity.

- **Full app:** Building all 200 features typically requires **many hours** of total runtime across multiple sessions.

**Tip:** Modify `prompts/initializer_prompt.md` to reduce the feature count (e.g., 20-50 features for a quicker demo).

## How It Works

### Two-Agent Pattern

1. **Initializer Agent (Session 1):** Reads `app_spec.txt`, creates `feature_list.json` with 200 test cases, sets up project structure, and initializes git.

2. **Coding Agent (Sessions 2+):** Picks up where the previous session left off, implements features one by one, and marks them as passing in `feature_list.json`.

### Session Management

- Each session runs with a fresh context window
- Progress is persisted via `feature_list.json` and git commits
- The agent auto-continues between sessions (3 second delay)
- Press `Ctrl+C` to pause; run the same command to resume

## Project Structure

```
autonomous-claude-code/
├── autonomous_agent_demo.py  # Main entry point
├── agent.py                  # Agent session logic
├── client.py                 # Claude CLI client wrapper
├── progress.py               # Progress tracking utilities
├── prompts.py                # Prompt loading utilities
├── pyproject.toml            # uv project configuration
├── prompts/
│   ├── app_spec.txt          # Application specification
│   ├── initializer_prompt.md # First session prompt
│   └── coding_prompt.md      # Continuation session prompt
```

## Generated Project Structure

After running, your project directory will contain:

```
my_project/
├── feature_list.json         # Test cases (source of truth)
├── app_spec.txt              # Copied specification
├── init.sh                   # Environment setup script
├── claude-progress.txt       # Session progress notes
└── [application files]       # Generated application code
```

## Running the Generated Application

After the agent completes (or pauses), you can run the generated application:

```bash
cd generations/my_project

# Run the setup script created by the agent
./init.sh

# Or manually (typical for Node.js apps):
npm install
npm run dev
```

The application will typically be available at `http://localhost:3000` or similar (check the agent's output or `init.sh` for the exact URL).

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--project-dir` | Directory for the project | `./autonomous_demo_project` |
| `--max-iterations` | Max agent iterations | Unlimited |
| `--model` | Claude model to use | `claude-sonnet-4-5-20250929` |

## Customization

### Changing the Application

Edit `prompts/app_spec.txt` to specify a different application to build.

### Adjusting Feature Count

Edit `prompts/initializer_prompt.md` and change the "200 features" requirement to a smaller number for faster demos.

## Security Note

This demo uses `--dangerously-skip-permissions` to allow autonomous operation. The agent has full access to the project directory. Only run in trusted environments.

## Troubleshooting

**"Claude Code CLI not found"**
Install the CLI with `npm install -g @anthropic-ai/claude-code` and authenticate with `claude login`.

**"Appears to hang on first run"**
This is normal. The initializer agent is generating 200 detailed test cases, which takes significant time.

**"Session timed out"**
The default timeout is 10 minutes per session. For complex tasks, increase the timeout in `client.py`.

## License

MIT - Based on [Anthropic's claude-quickstarts](https://github.com/anthropics/claude-quickstarts) (MIT License, Copyright 2023 Anthropic)

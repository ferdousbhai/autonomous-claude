# autonomous-claude sandbox image
# Provides isolated execution environment for Claude Code CLI

FROM node:22-bookworm-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    # Playwright browser dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install pnpm (latest)
RUN corepack enable && corepack prepare pnpm@latest --activate

# Use existing node user (uid 1000) and set up directories
# Create all directories Claude Code needs to write to
RUN mkdir -p /home/node/.claude/debug \
             /home/node/.claude/session-env \
             /home/node/.claude/todos \
             /home/node/.claude/file-history \
             /home/node/.claude/plans \
             /home/node/.claude/projects \
             /home/node/.claude/shell-snapshots \
             /home/node/.claude/statsig \
             /home/node/.claude/telemetry \
             /home/node/.claude/ide \
             /workspace && \
    chown -R node:node /home/node /workspace

# Copy uv to node user
RUN cp -r /root/.local /home/node/.local && \
    chown -R node:node /home/node/.local

# Switch to non-root user
USER node
WORKDIR /home/node

# Set up paths
ENV PNPM_HOME="/home/node/.local/share/pnpm"
ENV PATH="/home/node/.local/bin:$PNPM_HOME:$PATH"
RUN mkdir -p $PNPM_HOME

# Install Claude Code CLI (latest)
RUN pnpm add -g @anthropic-ai/claude-code@latest

# Install Playwright and Chromium browser (latest)
RUN npx playwright@latest install chromium

# Copy bundled skills
COPY --chown=node:node src/autonomous_claude/skills /home/node/.claude/skills/

# Install playwright-skill dependencies
WORKDIR /home/node/.claude/skills/playwright-skill
RUN if [ -f package.json ]; then pnpm install || true; fi

# Set up environment
WORKDIR /workspace
ENV HOME=/home/node
ENV USER=node

# Default entrypoint runs claude CLI
ENTRYPOINT ["claude"]
CMD ["--help"]

# Use the official Python lightweight image
FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory inside the container
WORKDIR /app

# Copy entire project into container
COPY . /app

# Allow Python logs to appear immediately
ENV PYTHONUNBUFFERED=1

# ENV variable to control runner ("mcp" or "workflow")
ENV RUN_MODE=mcp

# Install dependencies
RUN uv lock && uv sync --locked

# Expose port for Cloud Run
EXPOSE $PORT

# Entry point wrapper to choose runner
CMD ["/bin/sh", "-c", "\
    if [ \"$RUN_MODE\" = \"workflow\" ]; then \
        echo 'Running workflow only...'; \
        uv run main_workflow.py; \
    elif [ \"$RUN_MODE\" = \"both\" ]; then \
        echo 'Running workflow in background and MCP in foreground...'; \
        uv run main_workflow.py & \
        uv run src/mcp-server/mcp_server.py; \
    else \
        echo 'Running MCP server only...'; \
        uv run src/mcp-server/mcp_server.py; \
    fi \
"]


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

# Install dependencies
RUN uv lock && uv sync --locked

# Expose port for Cloud Run
EXPOSE $PORT

# Run the FastMCP server (mcp_server.py is inside src/mcp-server/)
CMD ["uv", "run", "src/mcp-server/mcp_server.py"]

# =============================================================================
# Frontend Dockerfile for Turret Web Interface
# =============================================================================
# Builds the React application using Bun
# Output goes to /app/out directory
# In production, this is built as part of the server Dockerfile
# In development, the output is mounted to the server via docker-compose
# =============================================================================

FROM oven/bun:1

WORKDIR /app

# Copy package files and install dependencies
COPY package.json bun.lock ./
RUN bun install --production=false

# Copy all source files
COPY . .

# Build the application
# Output goes to /app/out
RUN bun build.ts

# Keep container running (useful for CI/CD)
CMD ["tail", "-f", "/dev/null"]

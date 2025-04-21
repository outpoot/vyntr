# syntax = docker/dockerfile:1

ARG NODE_VERSION=22.12.0
FROM node:${NODE_VERSION}-slim AS base

WORKDIR /app

# Set production environment
ENV NODE_ENV="production"

# Build stage
FROM base AS build

RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
    build-essential \
    node-gyp \
    pkg-config \
    python-is-python3 && \
    rm -rf /var/lib/apt/lists/*

# Install node modules
COPY --chown=node:node package*.json ./
RUN npm ci --include=dev

# Copy entire project
COPY --chown=node:node . .

# Build application
RUN npm run build

# Remove development dependencies
RUN npm prune --omit=dev

# Final production stage
FROM base AS production

WORKDIR /app

# Copy only necessary files from build stage
COPY --from=build --chown=node:node /app/build ./build
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/package.json .
COPY --from=build --chown=node:node /app/.env .env

# Use node user
USER node

# Expose port
EXPOSE 3000

# Start the application
CMD ["node", "build/index.js"]
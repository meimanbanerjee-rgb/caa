# frontend/Dockerfile
# Builds and serves the React + Vite frontend for InsightForge AI.

FROM node:20-alpine

WORKDIR /app

# Copy dependency manifests
COPY package*.json ./

# Install packages
RUN npm ci --prefer-offline --no-audit

# Copy source code and assets
COPY . .

# Build production bundle
RUN npm run build

EXPOSE 5173

# Serve production assets on port 5173
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]


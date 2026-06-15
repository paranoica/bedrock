FROM node:20.11-bookworm-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
RUN useradd -r -u 10001 app
USER app                                 # non-root runtime
EXPOSE 3000
CMD ["node", "server.js"]
# API_KEY injected at runtime via the orchestrator's secret store, never baked in

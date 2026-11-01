FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/package*.json ./
RUN npm install --omit=dev
COPY backend/ ./
COPY frontend/ /app/frontend/
COPY python-engine/ /app/python-engine/
ENV NODE_ENV=production PYTHON_BIN=python3 PORT=3000
EXPOSE 3000
CMD ["npm", "start"]

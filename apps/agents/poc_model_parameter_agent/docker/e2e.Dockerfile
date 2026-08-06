FROM mcr.microsoft.com/playwright:v1.52.0-noble

WORKDIR /e2e

COPY e2e/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY e2e/ ./

CMD ["npm", "test"]

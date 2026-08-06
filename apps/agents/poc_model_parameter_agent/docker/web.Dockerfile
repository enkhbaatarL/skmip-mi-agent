FROM node:22-alpine AS dependencies

WORKDIR /app

COPY frontend/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

FROM dependencies AS build

ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY frontend/ ./
RUN npm run build

FROM build AS test
CMD ["npm", "test", "--", "--run"]

FROM nginx:1.27-alpine AS runtime

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1/web-health || exit 1

CMD ["nginx", "-g", "daemon off;"]

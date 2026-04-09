# === BUILD STAGE ===
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# In production, API calls go through nginx reverse proxy (not localhost)
ENV VITE_API_BASE_URL=""
RUN npm run build

# === PRODUCTION — nginx ===
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost/health-ui || exit 1

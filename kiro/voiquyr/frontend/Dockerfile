# ─────────────────────────────────────────────
# Stage 1: build React app
# ─────────────────────────────────────────────
FROM node:18-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build

# ─────────────────────────────────────────────
# Stage 2: serve with nginx
# ─────────────────────────────────────────────
FROM nginx:alpine AS runtime

COPY --from=builder /app/build /usr/share/nginx/html

# SPA routing — all paths fall back to index.html
RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

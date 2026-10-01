FROM node:24.14.1-bookworm-slim AS development
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

FROM development AS build
RUN npm run build

FROM nginx:1.28.0-alpine3.21 AS production
RUN mkdir -p /tmp/nginx/client_temp /tmp/nginx/proxy_temp \
    && chown -R nginx:nginx /tmp/nginx /var/cache/nginx
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
USER nginx
EXPOSE 8080
STOPSIGNAL SIGQUIT
CMD ["nginx", "-g", "daemon off;"]

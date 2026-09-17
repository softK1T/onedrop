FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
COPY package-lock.json ./
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
RUN addgroup -S onedrop && adduser -S onedrop -G onedrop \
 && chown -R onedrop:onedrop /usr/share/nginx/html /var/cache/nginx /var/run
USER onedrop
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
CMD ["nginx", "-g", "daemon off;"]

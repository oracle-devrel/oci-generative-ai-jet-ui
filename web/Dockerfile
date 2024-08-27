FROM --platform=linux/amd64 node:22-slim AS builder

ENV NODE_ENV=production
ENV NODE_MAX_MEM=2048

WORKDIR /usr/src/web

COPY package*.json ./

RUN npm ci --only=production --include=dev

COPY public/ ./public
COPY src/ ./src
COPY index.html .
COPY .eslintrc.cjs .
COPY vite.config.js .

RUN npm run build

FROM --platform=linux/amd64 nginx:1.23-alpine-slim

COPY --from=builder /usr/src/web/dist/ /usr/share/nginx/html/
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/default.conf /etc/nginx/conf.d

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
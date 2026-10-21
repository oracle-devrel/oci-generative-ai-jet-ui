FROM node:22-alpine AS build

WORKDIR /app
RUN corepack enable

COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml tsconfig.json ./
COPY apps ./apps
COPY packages ./packages
COPY samples ./samples
COPY services ./services
COPY scripts ./scripts

RUN pnpm install --frozen-lockfile=false
RUN pnpm build

FROM node:22-alpine AS runtime

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=8787
ENV WEB_DIST_DIR=/app/apps/web/dist

RUN corepack enable
COPY --from=build /app ./

EXPOSE 8787
CMD ["pnpm", "start"]

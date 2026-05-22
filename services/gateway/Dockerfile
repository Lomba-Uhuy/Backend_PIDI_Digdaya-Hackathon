# syntax=docker/dockerfile:1.7
# ---- builder ----
FROM node:22-alpine AS builder
WORKDIR /repo

RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

# Copy root manifests + workspace config
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml tsconfig.base.json ./
COPY libs/shared-types/package.json libs/shared-types/tsconfig.json libs/shared-types/
COPY libs/shared-types/src libs/shared-types/src
COPY services/gateway/package.json services/gateway/

RUN pnpm install --frozen-lockfile || pnpm install

COPY services/gateway/ services/gateway/

WORKDIR /repo/services/gateway
RUN pnpm build

# ---- runtime ----
FROM node:22-alpine AS runtime
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

COPY --from=builder /repo/package.json /repo/pnpm-lock.yaml* /repo/pnpm-workspace.yaml /repo/
COPY --from=builder /repo/libs /repo/libs
COPY --from=builder /repo/services/gateway/package.json /repo/services/gateway/
COPY --from=builder /repo/services/gateway/dist /repo/services/gateway/dist

WORKDIR /repo
RUN pnpm install --prod --frozen-lockfile || pnpm install --prod

WORKDIR /repo/services/gateway
EXPOSE 3000
CMD ["node", "dist/main.js"]
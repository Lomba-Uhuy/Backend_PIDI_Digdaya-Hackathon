# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS builder
WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml tsconfig.base.json ./
COPY libs/shared-types/package.json libs/shared-types/tsconfig.json libs/shared-types/
COPY libs/shared-types/src libs/shared-types/src
COPY services/user-service/package.json services/user-service/

RUN pnpm install --frozen-lockfile || pnpm install

# Build shared-types first
WORKDIR /repo/libs/shared-types
RUN pnpm build

# Then build user-service
COPY services/user-service/ /repo/services/user-service/
WORKDIR /repo/services/user-service
RUN pnpm build

FROM node:22-alpine AS runtime
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

COPY --from=builder /repo/package.json /repo/pnpm-lock.yaml* /repo/pnpm-workspace.yaml /repo/
COPY --from=builder /repo/libs/shared-types/dist /repo/libs/shared-types/dist
COPY --from=builder /repo/libs/shared-types/package.json /repo/libs/shared-types/
COPY --from=builder /repo/services/user-service/package.json /repo/services/user-service/
COPY --from=builder /repo/services/user-service/dist /repo/services/user-service/dist
# Copy Drizzle migration files so migrate() can run them at container startup
COPY --from=builder /repo/services/user-service/src/database/migrations /repo/services/user-service/migrations

WORKDIR /repo
RUN pnpm install --prod --frozen-lockfile || pnpm install --prod

WORKDIR /repo/services/user-service
EXPOSE 3001
CMD ["node", "dist/main.js"]
# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS builder
WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml tsconfig.base.json ./
COPY libs/shared-types/package.json libs/shared-types/tsconfig.json libs/shared-types/
COPY libs/shared-types/src libs/shared-types/src
COPY services/readiness-service/package.json services/readiness-service/

RUN pnpm install --frozen-lockfile || pnpm install

COPY services/readiness-service/ services/readiness-service/
WORKDIR /repo/services/readiness-service
RUN pnpm build

FROM node:22-alpine AS runtime
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

COPY --from=builder /repo/package.json /repo/pnpm-lock.yaml* /repo/pnpm-workspace.yaml /repo/
COPY --from=builder /repo/libs /repo/libs
COPY --from=builder /repo/services/readiness-service/package.json /repo/services/readiness-service/
COPY --from=builder /repo/services/readiness-service/dist /repo/services/readiness-service/dist

WORKDIR /repo
RUN pnpm install --prod --frozen-lockfile || pnpm install --prod

WORKDIR /repo/services/readiness-service
EXPOSE 3002
CMD ["node", "dist/main.js"]
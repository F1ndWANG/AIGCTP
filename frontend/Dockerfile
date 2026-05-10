# ── Build Stage ──
FROM node:20-alpine AS builder
WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY . .
RUN npm run build

# ── Production Runtime ──
FROM node:20-alpine AS runner
WORKDIR /app

RUN addgroup --system app && adduser --system --group app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /build/.next/standalone ./
COPY --from=builder /build/.next/static ./.next/static
COPY --from=builder /build/public ./public

USER app
EXPOSE 3000

ENV PORT=3000
CMD ["node", "server.js"]

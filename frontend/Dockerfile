# Build-time API URL: NEXT_PUBLIC_* vars are baked into the client bundle
# at build time, not read at container start. Pass the URL your users'
# BROWSERS can reach (not an internal Docker hostname).
ARG NEXT_PUBLIC_API_URL=http://localhost:8000

FROM node:20-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

ENV PORT=3000
EXPOSE 3000
CMD ["node", "server.js"]

FROM node:24-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:24-alpine AS builder

WORKDIR /app
ARG NEXT_PUBLIC_CUSTOMER_APP_URL=https://xantarapos.com
ENV NEXT_PUBLIC_CUSTOMER_APP_URL=$NEXT_PUBLIC_CUSTOMER_APP_URL
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24-alpine AS runner

ENV NODE_ENV=production \
    PORT=4020 \
    HOSTNAME=0.0.0.0

WORKDIR /app
COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=dependencies /app/node_modules ./node_modules

USER node

EXPOSE 4020

CMD ["npm", "run", "start", "--", "-p", "4020", "-H", "0.0.0.0"]

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json /app/package.json
RUN npm install

FROM deps AS builder
COPY . /app
RUN mkdir -p /app/public
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_BASE_PATH
ARG NEXT_PUBLIC_DESK_TOKEN
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL \
    NEXT_PUBLIC_BASE_PATH=$NEXT_PUBLIC_BASE_PATH \
    NEXT_PUBLIC_DESK_TOKEN=$NEXT_PUBLIC_DESK_TOKEN \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]

FROM deps AS dev
COPY . /app
EXPOSE 3000
CMD ["npm", "run", "dev"]

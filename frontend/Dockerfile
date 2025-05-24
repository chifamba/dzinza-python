# frontend/Dockerfile

# ---- Base Node image for subsequent stages ----
FROM node:20-alpine AS base
WORKDIR /app
RUN chown -R node:node /app # Ensure app directory is owned by node user

# ---- Dependencies Stage ----
FROM base AS deps
COPY package.json package-lock.json* ./
# If using yarn, copy yarn.lock instead of package-lock.json
# COPY package.json yarn.lock ./
RUN npm ci
# If using yarn:
# RUN yarn install --frozen-lockfile

# ---- Build Stage ----
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Make sure .env.local is NOT copied into the image for production builds.
# The .dockerignore file should handle this.
RUN npm run build

# ---- Production Stage ----
FROM base AS runner
ENV NODE_ENV production
# Set desired port, Next.js default is 3000
ENV PORT 3000
# Optionally, set NEXT_TELEMETRY_DISABLED to 1 to disable telemetry
ENV NEXT_TELEMETRY_DISABLED 1

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
# If you have a `public` folder, copy it as well.
# Check if public folder exists before attempting to copy
COPY --from=builder --chown=node:node /app/public ./public

USER node
EXPOSE 3000

CMD ["node", "server.js"]
# For older Next.js versions or if not using output standalone:
# CMD ["npm", "start"]

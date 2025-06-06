# Stage 1: Build the React application
FROM node:18-alpine AS builder

WORKDIR /app

# Define VITE_API_BASE_URL as a build argument with a default value
ARG VITE_API_BASE_URL=http://backend:8090/api
# Make the build argument available as an environment variable for the build process
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Copy package.json and package-lock.json (or yarn.lock)
COPY package.json package-lock.json* ./
# If you use yarn, it would be:
# COPY package.json yarn.lock ./

# Install dependencies
# Using --frozen-lockfile or --ci for reproducible builds
RUN npm ci
# If you use yarn, it would be:
# RUN yarn install --frozen-lockfile

# Copy the rest of the application source code
COPY . .

# Build the application
# npm run build will now have access to VITE_API_BASE_URL
RUN echo "Building UI with VITE_API_BASE_URL=${VITE_API_BASE_URL}" && npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:stable-alpine

# Remove default Nginx config and add our custom one for SPA
RUN rm /etc/nginx/conf.d/default.conf
COPY <<'EONginxConf' /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name localhost;

    # Root directory for static assets
    root /usr/share/nginx/html;
    index index.html index.htm;

    # Handle SPA routing: serve index.html for non-file requests
    # Any request that doesn't match a static file should serve index.html.
    location / {
        try_files $uri $uri/ /index.html;
    }

    # The /api proxy block has been removed as the UI will use an absolute URL
    # for API calls, defined by VITE_API_BASE_URL at build time.

    # Optional: You can add more specific configurations, e.g., for caching, gzip, etc.
    # gzip on;
    # gzip_vary on;
    # gzip_proxied any;
    # gzip_comp_level 6;
    # gzip_types text/plain text/css application/json application/javascript application/x-javascript text/xml application/xml application/xml+rss text/javascript;
}
EONginxConf

# Copy the build output from the builder stage to Nginx's web root
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx when the container launches
CMD ["nginx", "-g", "daemon off;"]

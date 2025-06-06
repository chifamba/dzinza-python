# Stage 1: Build the React application
FROM node:18-alpine AS builder

WORKDIR /app

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
# This command should match the build script in your package.json
# It's important that the VITE_API_BASE_URL (or similar) is correctly used by Vite
# during this build, so that the JS code makes requests to /api/...
RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:stable-alpine

# Remove default Nginx config and add our custom one
RUN rm /etc/nginx/conf.d/default.conf
COPY <<'EONginxConf' /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name localhost;

    # Root directory for static assets
    root /usr/share/nginx/html;
    index index.html index.htm;

    # Handle SPA routing: serve index.html for non-file requests
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to the backend service
    # The backend service is named 'backend' and listens on port 8090 in the Docker network
    location /api/ {
        # Remove /api prefix before forwarding, if backend expects paths like /users not /api/users
        # If backend's Flask routes are defined like @app.route("/api/users"), then do not rewrite.
        # Assuming backend routes are like /users, /login etc. and the /api is part of the gateway/proxy path only.
        # Based on existing backend `REACT_APP_API_URL=http://localhost:8090/api`
        # it seems the backend itself expects /api in the path.
        # So, no rewrite needed, just proxy directly.
        proxy_pass http://backend:8090; # Forward to backend service at port 8090

        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Optional: If dealing with WebSockets
        # proxy_http_version 1.1;
        # proxy_set_header Upgrade $http_upgrade;
        # proxy_set_header Connection "upgrade";
    }

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

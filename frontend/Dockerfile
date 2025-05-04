# frontend/Dockerfile

# --- Build Stage ---
# Use an official Node runtime as the build environment
FROM node:23-alpine AS build

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
COPY package*.json ./

# Install dependencies
# Use --legacy-peer-deps if you encounter peer dependency issues, otherwise remove it
RUN npm install # --legacy-peer-deps

# Copy the rest of the frontend application code
COPY . .

# Build the React application for production
# Ensure the build command succeeds
RUN npm run build

# --- Production Stage ---
# Use a lightweight Nginx image to serve the static files
FROM nginx:stable-alpine

# Copy the built assets from the build stage to Nginx's web root
COPY --from=build /app/dist /usr/share/nginx/html

# *** ADDED LINE: Copy custom Nginx configuration ***
# This replaces the default Nginx config with our SPA-friendly one
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 (default Nginx port)
EXPOSE 80

# Default command to start Nginx
CMD ["nginx", "-g", "daemon off;"]

# frontend/Dockerfile

# --- Build Stage ---
# Use an official Node runtime as the build environment
FROM node:18-alpine as build

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend application code
COPY . .

# Build the React application for production
RUN npm run build

# --- Production Stage ---
# Use a lightweight Nginx image to serve the static files
FROM nginx:stable-alpine

# Copy the built assets from the build stage to Nginx's web root
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration if needed (e.g., to handle routing)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 (default Nginx port)
EXPOSE 80

# Default command to start Nginx
CMD ["nginx", "-g", "daemon off;"]


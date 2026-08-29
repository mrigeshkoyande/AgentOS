# Stage 1: Build the React application
FROM node:18-alpine AS build-stage
WORKDIR /app

# Copy dependency specifications and install them
COPY package*.json ./
RUN npm ci

# Copy the rest of the application files and build
COPY . .
RUN npm run build

# Stage 2: Serve the compiled application with Nginx
FROM nginx:alpine
COPY --from=build-stage /app/dist/client /usr/share/nginx/html

# Copy proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

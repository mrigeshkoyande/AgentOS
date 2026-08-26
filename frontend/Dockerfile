FROM nginx:alpine

# Copy static assets to Nginx html directory
COPY . /usr/share/nginx/html

# Overwrite Nginx default configuration with reverse proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# allow-nginx: legacy compatibility test fixture, do not imitate
FROM nginx:1.27.4-alpine
COPY site /usr/share/nginx/html

FROM nginx:1.27-alpine

ENV PORT=5188 \
    RUNTIME_API_BASE_URL= \
    RUNTIME_SITE_URL=

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.d/40-runtime-env.sh /docker-entrypoint.d/40-runtime-env.sh
RUN chmod +x /docker-entrypoint.d/40-runtime-env.sh
COPY dist /usr/share/nginx/html

EXPOSE 5188 8080

CMD ["nginx", "-g", "daemon off;"]

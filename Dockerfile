FROM nginxinc/nginx-unprivileged:1.30.5-alpine@sha256:4714e0b1b2577eaa1a6131d07c958b67f0eb68e6d0521e90c6e5287db8cf0bc5

ADD --checksum=sha256:51b24db8170a5414875602c2f4e35017185b1c1dd7e9a6b1c0de69905a81e997 --chmod=0444 https://github.com/router-for-me/Cli-Proxy-API-Management-Center/releases/download/v1.24.2/management.html /www/index.html

USER root
RUN apk add --no-cache libexpat=2.8.5-r0 && chmod 0755 /www
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY UI-LICENSE /usr/share/licenses/cli-proxy-api-management-center/LICENSE

USER 65534:65534
EXPOSE 8080
ENV CLIPROXYAPI_UI_API_ENDPOINT=http://cliproxyapi:8317
ENV CLIPROXYAPI_UI_SERVER_PORT=8080
ENTRYPOINT ["/bin/sh", "-ec", "envsubst '$CLIPROXYAPI_UI_API_ENDPOINT $CLIPROXYAPI_UI_SERVER_PORT' < /etc/nginx/nginx.conf.template > /tmp/nginx.conf; exec nginx -c /tmp/nginx.conf -g 'daemon off;'"]

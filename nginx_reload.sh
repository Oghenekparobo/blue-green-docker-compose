#!/bin/sh
envsubst '${ACTIVE_POOL} ${APP_PORT} ${APP_HEALTH_URL}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
nginx -s reload
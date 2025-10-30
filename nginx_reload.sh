#!/bin/sh
set -e
# Wait for upstream services to be reachable via health check
echo "Waiting for upstream services..."
until wget --no-verbose --tries=1 --spider http://app_blue:3000/healthz && wget --no-verbose --tries=1 --spider http://app_green:3000/healthz; do
  echo "Upstreams not ready, waiting..."
  sleep 2
done
envsubst '${ACTIVE_POOL} ${BACKUP_POOL} ${APP_PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
nginx -s reload
echo "Reloaded NGINX config with ACTIVE_POOL=${ACTIVE_POOL}, BACKUP_POOL=${BACKUP_POOL}"
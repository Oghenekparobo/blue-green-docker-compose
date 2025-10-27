#!/bin/sh
set -e  # Exit on error
envsubst '${ACTIVE_POOL} ${BACKUP_POOL} ${APP_PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
nginx -s reload
echo "Reloaded NGINX config with ACTIVE_POOL=${ACTIVE_POOL}, BACKUP_POOL=${BACKUP_POOL}"
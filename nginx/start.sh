#!/bin/bash
envsubst '$BACKEND_SERVER_ADDR' < /tmp/default.conf > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'
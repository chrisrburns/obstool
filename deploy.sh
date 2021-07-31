#!/usr/bin/env bash

ROOT_PATH=`pwd`
NGINX_CONFIG_FILE=obstool_nginx.conf
#NGINX_SITES_CONFIG=/usr/local/etc/nginx/servers
NGINX_SITES_CONFIG=/opt/homebrew/etc/nginx/servers
UWSGI_CONFIG_FILE=obstool_uwsgi.ini

echo """
upstream obstool {
   server unix:///tmp/obstool.sock;
}

server {
   listen 8000;
   server_name localhost;
   charset utf-8;

   client_max_body_size 75M;

   location /media {
      alias $ROOT_PATH/media;
   }
   location /static {
      alias $ROOT_PATH/static;
   }

   location / {
      uwsgi_pass obstool;
      include $ROOT_PATH/uwsgi_params;
   }
}
""" > $NGINX_CONFIG_FILE

echo """
# obstool_uwsgi.ini file
[uwsgi]
# Django-related settings
# the base directory (full path) where settings.py locates
chdir           = $ROOT_PATH
# Django's wsgi file
wsgi-file       = obstool/wsgi.py
master          = true
# maximum number of worker processes
processes       = 2
# the socket (use the full path to be safe)
socket          = /tmp/obstool.sock
# ... with appropriate permissions - may be needed
chmod-socket    = 664
# clear environment on exit
vacuum          = true
# create a pidfile
pidfile = /tmp/obstool.pid
# background the process & log
daemonize = uwsgi.log
""" > $UWSGI_CONFIG_FILE

if [ ! -d "$NGINX_SITES_CONFIG" ] ; then
   mkdir -p "$NGINX_SITES_CONFIG"
fi
ln -sf $ROOT_PATH/$NGINX_CONFIG_FILE $NGINX_SITES_CONFIG

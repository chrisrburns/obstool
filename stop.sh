#!/usr/bin/env bash

#shut down uwsgi
uwsgi --stop /tmp/obstool.pid

# stop nginx
sudo nginx -s quit

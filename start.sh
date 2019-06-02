#!/usr/bin/env bash

# Start nginx
sudo nginx

# start uwsgi
uwsgi --ini obstool_uwsgi.ini

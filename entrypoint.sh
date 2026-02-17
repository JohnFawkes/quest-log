#!/bin/sh
set -e

# Fix ownership of bind-mounted volumes so the app user can write
chown -R questlog:questlog /data /app/static/uploads

# Drop privileges and run the CMD as the non-root app user
exec gosu questlog "$@"

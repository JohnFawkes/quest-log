#!/bin/sh
set -e

# Fix ownership of bind-mounted volumes so the app user can write
chown -R questlog:questlog /data /app/static/uploads

# Drop privileges using Python (guaranteed available, no extra deps)
# os.execvp replaces this process so the final command becomes PID 1
exec python3 -c "
import os, pwd, sys
pw = pwd.getpwnam('questlog')
os.setgroups([])
os.setgid(pw.pw_gid)
os.setuid(pw.pw_uid)
os.execvp(sys.argv[1], sys.argv[1:])
" "$@"

#!/bin/sh
# /etc/profile.d/motd.sh — Docker / container MOTD
#
# Add to your Dockerfile:
#   COPY integrate/docker.sh /etc/profile.d/motd.sh
#   RUN chmod +x /etc/profile.d/motd.sh
#
# /etc/profile.d/ scripts run for interactive login shells (docker exec -it, ssh, etc.)
# Silent on any failure — never breaks container startup.

set +e
bash /opt/motd/motd.sh 2>/dev/null || true

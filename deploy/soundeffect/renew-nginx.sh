#!/bin/sh
set -eu
if [ "${RENEWED_LINEAGE:-}" = /etc/letsencrypt/live/soundeffect.ruari.dev ]; then
    nginx -t
    systemctl reload nginx
fi

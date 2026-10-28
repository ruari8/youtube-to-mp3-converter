# Sound Cut deployment

The site at https://soundeffect.ruari.dev has an Editor tab and a shared Soundboard tab. The library starts with nine full MP4 videos and accepts YouTube imports. The soundboard starts with the ten original cuts. Saved cuts and imported videos are available to everyone with the site password.

The browser previews cuts and encodes direct MP3 downloads. Saving to the soundboard sends a video ID, name, and time range to the server, which creates a permanent MP3 with FFmpeg. Removing a pad hides it and offers Undo.

## Server layout

| Component | Location |
| --- | --- |
| VPS access | `deploy@100.97.46.6` through Tailscale |
| Public address | `46.224.210.96` behind Cloudflare |
| Active release | `/home/deploy/apps/soundeffect/current` |
| Initial release | `/home/deploy/apps/soundeffect/releases/20260919-video-v1` |
| Soundboard release | `/home/deploy/apps/soundeffect/releases/20260919-board-v2` |
| Static files | `current/public` |
| Shared data | `/home/deploy/apps/soundeffect/data` |
| Database | `data/library.sqlite3` |
| Imported videos and audio | `data/imports` |
| Saved MP3 clips | `data/clips` |
| Python environment | `/home/deploy/apps/soundeffect/venv` |
| Nginx configuration | `/etc/nginx/sites-available/soundeffect` |
| Authentication service | `soundeffect-auth.service`, listening on `127.0.0.1:8018` |
| Authentication secrets | `/etc/soundeffect/auth.json`, mode `0600` |
| TLS certificate | `/etc/letsencrypt/live/soundeffect.ruari.dev` |
| Certificate renewal hook | `/etc/letsencrypt/renewal-hooks/deploy/soundeffect-nginx` |

The authentication configuration contains a salted scrypt password hash and a random session-signing key. It stays outside the public directory and the repository. Cookies expire after seven days and carry `Secure`, `HttpOnly`, and `SameSite=Strict` attributes. Nginx checks authentication before serving pages, assets, or media and limits login requests. The API validates the same session itself and requires the site Origin for mutations.

## YouTube connection through the Mac

YouTube rejects this VPS's direct IPv4 and IPv6 downloads. The VPS runs yt-dlp through a SOCKS connection to Ruari's Mac. The phone sends a URL to the website and needs no SSH, Tailscale, or local software. The resulting files remain on the VPS.

`~/Library/LaunchAgents/dev.ruari.soundcut-youtube.plist` runs SSH at Mac login and reconnects after failures. It forwards a SOCKS listener bound to `127.0.0.1:18088` on the VPS. No public proxy port or inbound Mac port is opened. The backend selects it with `SOUNDCUT_PROXY=socks5://127.0.0.1:18088`. Logs are in `~/Library/Logs/soundcut-youtube.log`.

New imports require this Mac awake, logged in, online, and connected to Tailscale. When the tunnel is absent, imports stay queued. Existing videos, soundboard playback, editing, and MP3 downloads remain available. A connection lost during a download can fail that import; submitting the link again retries it.

## Shared API

| Route | Behavior |
| --- | --- |
| `GET /api/library` | Full video library |
| `GET /api/board` | Saved soundboard clips |
| `POST /api/board` | Save `{trackId, name, start, end}` as an MP3 |
| `DELETE /api/board/:id` | Hide a pad without deleting its file |
| `POST /api/board/:id/restore` | Restore a hidden pad |
| `POST /api/imports` | Queue `{url}` or return an existing video |
| `GET /api/imports` | Recent import status and errors |
| `GET /api/connection` | Mac connection availability |

SQLite owns shared metadata. One worker processes the persistent import queue. Canonical YouTube IDs prevent duplicate imports, including requests from different devices. Only YouTube video URLs are accepted. Imported videos are limited to ten minutes and 720p. The queue holds up to three pending requests. The library holds up to 100 videos and the board up to 250 visible clips. Cuts can be up to five minutes long.

The original implementation embedded the fixed library because the first deployment required only the nine supplied videos. Browser-only soundboard storage was rejected for this update because saved pads need to appear on the brother's devices. Release folders contain application files; shared data stays outside releases so updates preserve additions.

## Build and verification tools

`python3 scripts/build_soundeffect_site.py` creates `downloads/soundeffect-site/public` and `library.json` from the original videos in `downloads/stream-deck-sounds`. It requires FFmpeg and all nine originals. The backend seeds SQLite from `library.json` without replacing existing records. The hosted frontend fetches the current shared library through the API.

`python3 -m unittest discover -s tests -p 'test_soundeffect_*.py' -v` covers authentication, byte ranges, URL validation, duplicate imports, clip persistence, reversible removal, and actual FFmpeg output duration.

`scripts/verify_soundeffect_deployment.py` reads the password from the `SOUNDCUT_PASSWORD` environment variable. It checks the live HTTPS login, cookie attributes, and authenticated byte ranges for all 18 media files against the local build. It also checks that anonymous media requests are blocked. Its report is `downloads/soundeffect-deployment-verification.json`.

The HTTPS audit does not test browser interaction. The release was also checked in the browser for playback, video seeking, trim controls, and a downloaded eight-second MP3.

## Release contents

Each release contains `public/`, `library.json`, and the server files in this directory. The `current` symlink selects the release used by both Nginx and the authentication service. Static changes need no service restart. Backend changes need a restart of `soundeffect-auth.service`. Nginx configuration changes require a successful `nginx -t` before reload. The service needs write access to `data` and read access to the active release.

The existing `certbot.timer` renews the certificate. The deploy hook reloads Nginx only when this site's certificate changes.

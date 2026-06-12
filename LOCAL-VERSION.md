# Storytellers — Local Version Snapshot

This document is the **restore point** for the version that renders the final MP4
**server-side** (Flask + Pillow + ffmpeg) and runs perfectly on your laptop at
`http://localhost:8000/`.

> The public website (GitHub Pages) now uses a different, **in-browser** version
> so it can run for free without a server. This file is how you get the powerful
> local server version back whenever you want.

---

## 🔖 Snapshot markers

| Marker | Value |
| --- | --- |
| Git tag | `local-working-v1` |
| Git branch | `local-server` |
| Commit message | `Local working snapshot: server-side ffmpeg export, env-configurable host/port, deploy scripts` |

Both point at the exact, verified-working server-render code.

---

## ⏪ How to return to the local server version

Open a terminal in the project folder and run **one** of these:

```powershell
# Option A — check out the named branch (recommended, lets you keep working)
git checkout local-server

# Option B — check out the tagged snapshot (detached, read-only feel)
git checkout local-working-v1
```

To come back to the public web version afterwards:

```powershell
git checkout main
```

> Tip: commit or stash any local edits before switching branches so nothing is lost.

---

## ▶️ Running the local server version

Requirements: **Python 3** and **ffmpeg** installed and on PATH (or installed via
winget `Gyan.FFmpeg`, which the server auto-detects).

```powershell
# 1. (first time only) install Python deps
pip install -r requirements.txt

# 2. start the server
python server.py

# 3. open the app
#    http://localhost:8000/
```

Optional environment overrides:

```powershell
$env:HOST = "0.0.0.0"   # listen on all interfaces (LAN access)
$env:PORT = "9000"      # custom port
python server.py
```

---

## 🧩 What the local version does (architecture)

```
Browser (index.html)                 server.py (Flask + Pillow + ffmpeg)
─────────────────────                ──────────────────────────────────
• live spinning preview      POST     • Pillow builds a static, anti-aliased
• collects photo/audio/bg/fg  ───────►  circular-mask frame + a square art sprite
• sends settings + files               • ffmpeg rotates ONLY the art, overlays the
                             ◄───────    static mask (clean edge), tmix motion blur,
• receives finished .mp4      MP4        loops one revolution, muxes trimmed audio
                                         → libx264 / yuv420p / crf 18
```

Key qualities of this version:

- **Crisp circular edge** — the disc edge is a fixed anti-aliased mask, never
  re-sampled by rotation (no jagged/"sacadat" edge).
- **Smooth rotation** — `tmix` motion blur at 4× fps.
- **High resolution** — exports at 1.5× the preview (1080-class).
- **Fast** — periodic-loop trick renders one revolution then stream-copies the
  loop (e.g. ~4s for a 10s clip, ~11s for 60s).
- **Audio trim** — draggable clip window picks where the song starts.

---

## 📁 Files that belong to the local version

| File | Role |
| --- | --- |
| `server.py` | Flask backend + Pillow compositing + ffmpeg render |
| `requirements.txt` | `flask`, `pillow`, `gunicorn` |
| `deploy/setup.sh` | One-shot Ubuntu installer (nginx + systemd + gunicorn) |
| `deploy/update.sh` | `git pull` + reinstall + restart service |
| `index.html` *(on the `local-server` branch/tag)* | UI that POSTs to `/export` |

> On `main`, `index.html` is the **web** (in-browser) version. The server-render
> `index.html` lives in the `local-server` branch / `local-working-v1` tag.

---

## ✅ Verified working

This snapshot was confirmed working on the laptop:
- renders smooth 1080 MP4s with audio,
- crisp circular edge,
- draggable clip-start window,
- progress UI during render.

# Storytellers — Spinning Vinyl Video Maker

Turn a photo + a song into a smooth, professional **spinning-vinyl MP4** — the
same effect as [turn.audio](https://turn.audio/), rendered fast and in high
resolution.

Upload artwork, optionally drop in a track, pick a format, and export a polished
MP4 with a continuously rotating record, motion blur, drop shadow and a clean
circular edge.

---

## ✨ Features

- **Photo → spinning vinyl** — your image becomes the record label that rotates.
- **Optional audio** — attach an MP3/WAV/OGG/M4A or export a silent clip.
- **Full song or manual clip** — use the whole track, or pick a fixed-length
  window (15s / 30s / 1m) and **drag it across the waveform** to choose exactly
  where the clip starts.
- **Audio preview** — hear the selected portion before exporting.
- **Social formats** — Square (1:1), Portrait (4:5), Story (9:16), Wide (16:9).
- **Customisation** — background colour, optional background & foreground
  images, rotation speed (RPM) and disc size.
- **High-resolution export** — preview runs at a fast 720 base; the final MP4 is
  rendered at **1080 base (1.5×)** for crisp output.
- **Smooth, fluid motion** — server-side **motion blur** (sub-frame averaging)
  removes the choppiness of a stepping disc.
- **Crisp circular edge** — only the artwork rotates; a static anti-aliased
  circular mask is overlaid so the edge never re-samples (no jagged spinning
  edge).
- **Live progress** — real upload percentage, then an animated rendering bar
  with an elapsed-time counter.

---

## 🏗️ How it works

The browser is only the **editor and live preview**. The final MP4 is rendered
**server-side** with **ffmpeg / libx264** — exactly the approach turn.audio uses
(confirmed by their output metadata: `Lavc60 libx264`). In-browser WebCodecs
export was tried first but the GPU encoder warmed up slowly and oscillated
wildly (10↔234 fps), so a 1-minute clip took ~40s. ffmpeg renders the same clip
in a few seconds, reliably, on any machine.

```
┌────────────────────┐        multipart POST /export        ┌──────────────────────┐
│   index.html (UI)  │  ───────────────────────────────────▶ │  server.py (Flask)   │
│  • upload assets   │   image, audio, bg, fg + settings      │  • Pillow compositing│
│  • live preview    │                                        │  • ffmpeg / libx264  │
│  • waveform / trim  │  ◀─────────────────────────────────── │  • audio mux + loop  │
└────────────────────┘            MP4 download                └──────────────────────┘
```

### Render pipeline (`server.py`)

1. **Compositing (Pillow)**
   - `build_art()` builds the square artwork (cover-fit) that will rotate.
   - `build_frame()` builds a **static full-canvas overlay**: background colour /
     image, a soft drop shadow, an **anti-aliased transparent circular hole**
     (4× supersampled), the outer ring and the centre spindle hole.
2. **Rotation + motion blur (ffmpeg)**
   - Only the **artwork** is rotated (expanded to its diagonal so it always
     covers the circular hole), composited on black, then the **static frame**
     is overlaid → the circular edge stays a fixed, smooth circle.
   - The spin is rendered at **4× fps**, then `tmix` averages every 4 sub-frames
     into one → real motion blur → fluid rotation.
3. **Periodic-loop optimisation**
   - For integer RPM, only the frames for one whole set of revolutions are
     rendered, then `-stream_loop` repeats that segment to the full duration.
     This makes a 60s render take ~11s instead of ~60s.
4. **Audio**
   - Optional track is trimmed (`-ss <start> -t <duration>`), encoded to AAC and
     muxed; `-movflags +faststart` for instant web playback.

---

## 🚀 Running locally

> The export step **requires the Python server** (it runs ffmpeg). Opening
> `index.html` directly, or serving it with `python -m http.server`, will show
> the UI and preview but **export will fail** — there is no `/export` backend.

### Prerequisites

- **Python 3.10+**
- **ffmpeg** on `PATH` (the server also auto-detects a winget install of
  `Gyan.FFmpeg`)
- Python packages: `flask`, `pillow`

```powershell
# Install dependencies
pip install flask pillow

# (Windows) install ffmpeg if you don't have it
winget install Gyan.FFmpeg
```

### Start

```powershell
python server.py
```

Then open **http://localhost:8000/**.

---

## 🎛️ Export parameters

| Field        | Meaning                                                        |
|--------------|----------------------------------------------------------------|
| `image`      | Artwork (required) — becomes the spinning label                |
| `audio`      | Optional track                                                 |
| `bg` / `fg`  | Optional background / foreground overlay images                |
| `w`, `h`     | Output size (sent at 1.5× the preview, forced even)            |
| `rpm`        | Rotation speed (revolutions per minute)                        |
| `duration`   | Clip length in seconds                                         |
| `audioStart` | Start offset into the song (for the draggable manual window)   |
| `vinylPct`   | Disc diameter as a fraction of the canvas                      |
| `bgColor`    | Background colour (hex)                                         |
| `fps`        | Frame rate (30)                                                |

---

## 📁 Project structure

```
storytellers-app/
├── index.html      # Single-file UI + live preview + export client
├── server.py       # Flask backend: Pillow compositing + ffmpeg render
├── fonts/          # Brand fonts (Fractal, Futura Std Bold, Nexa Round Glow)
└── README.md
```

---

## ⚠️ Hosting note

Because export is **server-side**, this app cannot run export on a static host
such as **GitHub Pages**. To put it online with working export you need a host
that can run Python **and** ffmpeg, e.g.:

- A small VM / VPS (Render, Railway, Fly.io, a cloud VM) running `python server.py`
  behind a production WSGI server (gunicorn/waitress) + reverse proxy.
- A container image with `python`, `flask`, `pillow` and `ffmpeg` installed.

GitHub Pages can still host the **UI/preview**, but the export button will need
to point at a separately hosted backend.

---

## 🛠️ Tech stack

- **Frontend:** vanilla HTML/CSS/JS (single file), Canvas live preview,
  Web Audio API waveform, `XMLHttpRequest` upload with progress.
- **Backend:** Python, Flask, Pillow.
- **Rendering:** ffmpeg / libx264 (H.264 High, yuv420p), AAC audio.

# Storytellers — Spinning Vinyl Video Maker

### ▶️ Live app: **https://andreilucca.github.io/vinylaudio/**

Turn a photo + a song into a smooth, professional **spinning-vinyl MP4** —
rendered **100% in your browser**. No server, no upload, no watermark, no
account. Your files never leave your device.

Upload artwork, optionally drop in a track, pick a format, and export a polished
MP4 with a continuously rotating record, drop shadow and a clean circular edge.

---

## ✨ Features

- **Photo → spinning vinyl** — your image becomes the record label that rotates.
- **Optional audio** — attach an MP3/WAV/OGG/M4A or export a silent clip.
- **Full song or manual clip** — use the whole track (any length: 6, 10, 12 min…),
  or pick a fixed window (15s / 30s / 1m) and **drag it across the waveform** to
  choose exactly where the clip starts.
- **Audio preview** — hear the selected portion before exporting.
- **Social formats** — Square (1:1), Portrait (4:5), Story (9:16), Wide (16:9 — YouTube).
- **Customisation** — background colour, optional background & foreground
  images, rotation speed (RPM) and disc size.
- **High-resolution export** — preview runs at a fast 720 base; the final MP4 is
  rendered at **1080 base (1.5×)** for crisp output (Wide = 1920×1080).
- **Crisp circular edge** — only the artwork rotates; a static anti-aliased
  circular mask is overlaid, so the disc edge never re-samples (no jagged edge).
- **Fast & constant render time** — a 6-minute song exports in roughly the same
  time as a 1-minute clip (see *How it works*).
- **Live progress** — an animated bar while the rotation renders, then a real
  percentage while the audio is added.

---

## 🏗️ How it works

Everything runs in the browser using **[ffmpeg.wasm](https://ffmpegwasm.netlify.app/)**
(ffmpeg compiled to WebAssembly). Nothing is uploaded to a server.

```
┌─────────────────────────────────────────────┐
│            index.html (your browser)          │
│  • Canvas live preview + waveform / trim      │
│  • Canvas composites the art + circular frame │
│  • ffmpeg.wasm encodes H.264 + muxes audio    │
│                  ↓                            │
│            finished .mp4 (download)            │
└─────────────────────────────────────────────┘
```

### Render pipeline

1. **Compositing (Canvas)**
   - The square **artwork** (cover-fit) is drawn — this is what rotates.
   - A **static full-canvas overlay** is built: background colour / image, a soft
     drop shadow, a transparent circular hole, the outer edge ring and the centre
     spindle hole.
2. **Rotation (ffmpeg.wasm)**
   - Only the **artwork** is rotated (expanded to its diagonal so it always
     covers the circular hole), composited on black, then the **static frame** is
     overlaid → the circular edge stays a fixed, smooth circle.
   - Encoded with **libx264**, `yuv420p`, `crf 20`, `preset veryfast`.
3. **Periodic-loop optimisation (constant render time)**
   - Only **one full revolution** of the disc is rendered (a fixed, small number
     of frames). That segment is then repeated with `-stream_loop` (no
     re-encode) to the requested duration.
   - Because the heavy encoding work is always *one revolution*, a 12-minute clip
     takes about the same time as a 1-minute clip. The loop is made seamless by
     snapping the RPM to a whole number of frames per revolution (within ~1% of
     the slider — imperceptible).
4. **Audio**
   - The track is trimmed (`-ss <start>`), encoded to **AAC 192k** and muxed onto
     the looped video; `-movflags +faststart` for instant web playback.

> **Why in-browser?** An earlier version rendered server-side (Flask + ffmpeg).
> That powerful version is preserved as a restore point — see
> [LOCAL-VERSION.md](LOCAL-VERSION.md). The in-browser version was built so the
> app can be hosted for free on GitHub Pages with no backend.

---

## 🚀 Running locally

No backend required — it's a static site. Just serve the folder:

```powershell
python -m http.server 8123
```

Then open **http://localhost:8123/**.

> **First export downloads the render engine once** (~31 MB ffmpeg.wasm core),
> then it's cached by the browser. Keep the tab in the foreground while it works.

---

## 🎛️ Controls

| Control       | Meaning                                                        |
|---------------|----------------------------------------------------------------|
| Photo         | Artwork (required) — becomes the spinning label                |
| Audio         | Optional track (MP3 / WAV / OGG / M4A)                          |
| Format        | Square / Portrait / Story / Wide (16:9)                        |
| Duration      | Full song, or a 15s / 30s / 1m draggable window                |
| Background    | Background colour (hex)                                         |
| Bg / Fg image | Optional background / foreground overlay images                |
| Speed (RPM)   | Rotation speed (revolutions per minute)                        |
| Photo Size    | Disc diameter as a fraction of the canvas                      |

---

## 📁 Project structure

```
storytellers-app/
├── index.html        # Single-file app: UI + live preview + in-browser export
├── vendor/ffmpeg/    # Vendored ffmpeg.wasm (ffmpeg.js, util.js, core .js/.wasm)
├── fonts/            # Brand fonts (Fractal, Futura Std Bold, Nexa Round Glow)
├── README.md
├── LOCAL-VERSION.md  # Restore point for the old server-side render version
└── server.py         # Old Flask backend (kept for the local-server snapshot)
```

---

## 🛠️ Tech stack

- **Frontend:** vanilla HTML / CSS / JS (single file), Canvas live preview,
  Web Audio API waveform.
- **Rendering:** ffmpeg.wasm (libx264, H.264, yuv420p) + AAC audio — all
  client-side via WebAssembly.
- **Hosting:** static — GitHub Pages.

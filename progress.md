# Storytellers — Progress Log (local-server branch)

## Version registry (current state)

| Variant | Version | Date (UTC+3) | Branch / Tag | Engine | Status |
| ------- | ------- | ------------ | ------------ | ------ | ------ |
| **LOCAL** | **v2.0** | **2026-06-27 10:56** | `local-server` / `local-v2.0.1` | Native ffmpeg (libx264) | ✅ CURRENT — Full HD, 60fps, smooth-rotation, crf16/slow, audio 256k |
| LOCAL (old) | v1.0 | (snapshot) | tag `local-working-v1` | Native ffmpeg | superseded (720-class, 30fps, 1.5× scale, hitch) |
| **WEB (live)** | **v2.0** | **2026-06-29** | `main` / tag `web-v2.0` (GitHub Pages) | ffmpeg.wasm | ✅ LIVE — smooth-rotation + real 1080p + audio 256k (30fps) |

**LOCAL v2.0 — descriptive note:** Server-side render via native ffmpeg. Exports true
Full HD (1920×1080 class) at **60fps** with `crf 16` / `preset slow` (near-lossless),
adaptive `tmix` motion blur **with warm-up** so rotation is fluid and seam-free at every
RPM. Run with `python server.py` → http://localhost:8000/.

> Scope note: WEB (`main`) now has the smooth-rotation fix + real 1080p + 256k audio,
> pushed live to GitHub Pages (tag `web-v2.0`). progress.md is kept on BOTH branches.

---

This file documents every change made to the **local** version (the one rendered
server-side with native ffmpeg). It is the changelog for the work done turning the
local app into a **Full HD, smooth-rotation** exporter.

> Scope note: This log lives on BOTH branches. `local-server` is the native-ffmpeg
> app; `main` is the web (ffmpeg.wasm) build live on GitHub Pages. Both got v2.0.

---

## 1. What was changed (local version)

### 1.1 Full HD (1080p) format presets
**File:** `index.html` (format cards)

The format cards used to export at 720-class sizes. They were bumped to true
Full HD pixel dimensions so every preset outputs 1080p:

| Format   | Before     | After (Full HD) |
| -------- | ---------- | --------------- |
| SQUARE   | 720 × 720  | **1080 × 1080** |
| PORTRAIT | 720 × 900  | **1080 × 1350** |
| STORY    | 720 × 1280 | **1080 × 1920** |
| WIDE     | 1280 × 720 | **1920 × 1080** |

The initial state (`S.canvasW` / `S.canvasH`) was also set to `1080` so the
default selection matches the SQUARE card.

### 1.2 Removed the hidden 1.5× upscale (was producing 2880×1620)
**File:** `index.html`

```js
// before
const EXPORT_SCALE = 1.5;   // 1920×1080 × 1.5 = 2880×1620 (NOT what we want)
// after
const EXPORT_SCALE = 1.0;   // format cards already specify the final 1080p size
```

**Why it mattered:** with `EXPORT_SCALE = 1.5`, a "Full HD" WIDE export came out
as **2880×1620**, not 1920×1080. A multi-minute clip at that oversized resolution
is heavy to *play back*, which the media player showed as stutter/"braking" — even
though the file itself was timed perfectly. The on-screen preview stayed smooth
because the preview canvas is lightweight. Setting the scale to `1.0` makes the
export exactly the size shown on the card (real Full HD), which plays back fluidly.

### 1.3 Export frame rate 30 → 60 fps
**File:** `index.html`

```js
// before
const REC_FPS = 30;
// after
const REC_FPS = 60;
```

**Why:** the live preview spins at 60fps (driven by `requestAnimationFrame`), so a
30fps export looked comparatively choppy. Matching 60fps makes the exported motion
feel as fluid as the preview.

### 1.4 Motion-blur "warm-up" — fixes the once-per-revolution hitch
**File:** `server.py` (ffmpeg filter chain)

The disc render uses `tmix` (temporal mix) to average several sub-frames into one
output frame, which creates natural motion blur. But `tmix` averages the *last* N
sub-frames, so the **very first** output frame has no history and comes out
under-blurred (slightly sharper / "harder").

Because the renderer uses a periodic-loop optimization (it renders ONE full
revolution and then stream-copies/loops it to fill the whole duration), that single
weak first frame **reappears at every loop seam**, which reads as a tiny "hitch" or
"braking" once per revolution.

**The fix:** add a warm-up of `SUB` extra sub-frames *before* frame 0. Since the
rotation is periodic, those warm-up sub-frames are identical to the end of the
revolution, so they prime `tmix`. They are then dropped with `trim`, and the
rotation phase is shifted back by the warm-up so the kept frames still start at
angle 0. Result: every output frame — including the loop seam — carries a full,
identical motion blur.

```text
# before
[0:v]...rotate=2*PI*rpm*t/60...[art];
... ; [vN]tmix=frames=SUB:weights=1 1 1 1, fps=fps[vout]

# after  (warm = SUB / (fps*SUB) = 1/fps seconds)
[0:v]...rotate=2*PI*rpm*(t-warm)/60...[art];
... ; [vN]tmix=frames=SUB:weights=1 1 1 1,
        trim=start_frame=SUB, setpts=PTS-STARTPTS, fps=fps[vout]
```

**Verified** with ffprobe on test renders: the looped output has the exact expected
frame count and **zero** non-uniform PTS deltas at the seams (perfectly even
timing), confirming the loop is seamless.

### 1.5 Maximum-quality encode settings
**File:** `server.py`

| Setting    | Before   | After    |
| ---------- | -------- | -------- |
| `-preset`  | medium   | **slow** |
| `-crf`     | 18       | **16**   |
| audio `-b:a` | 192k   | **256k** |

`crf 16` + `preset slow` is visually near-lossless at 1080p (larger files, slightly
slower render — the normal trade-off for top quality).

### 1.6 Footer note text
**File:** `index.html` — updated to read
`Server render (ffmpeg) · Full HD 1080p · MP4 H.264 CFR 60fps · no watermark`.

---

## 2. How the LOCAL version works vs the GitHub WEB (live) version

Both versions share the **same UI and the same render logic** (same compositing,
same `tmix` motion blur, same periodic-loop trick). The ONLY difference is *where
ffmpeg runs*.

### Local version (`local-server` branch)
```
Browser (index.html)                 server.py  (Flask + Pillow + NATIVE ffmpeg)
─────────────────────                ───────────────────────────────────────────
• live spinning preview      POST    • Pillow builds the static frame + art sprite
• collects photo/audio/bg/fg ───────►• NATIVE ffmpeg (libx264) rotates the art,
• sends settings + files             •   overlays the static mask, tmix blur,
                            ◄───────     loops one revolution, muxes audio
• receives finished .mp4      MP4    → libx264 / yuv420p / crf16 / 60fps
```
- Runs with `python server.py` → open http://localhost:8000/
- Uses the computer's **native ffmpeg** (installed via winget `Gyan.FFmpeg`).
- **Faster, higher quality, no browser limits.** Rendering happens on your PC's CPU.
- Files stay local; nothing is uploaded to the cloud.

### Web version (`main` branch, GitHub Pages — LIVE)
```
Browser (index.html)  +  ffmpeg.wasm  (ffmpeg compiled to WebAssembly)
──────────────────────────────────────────────────────────────────────
• live spinning preview
• collects photo/audio/bg/fg
• ffmpeg.wasm (vendor/ffmpeg/*) runs the SAME filter chain ENTIRELY in the browser
• receives finished .mp4   → all in-browser, no server, no upload
```
- Hosted as **static files** on GitHub Pages (no backend, free).
- Rendering runs **100% in the browser** via `ffmpeg.wasm` — there is **no server**
  and **no file server**. Your photo/audio never leave your machine.
- The "I need a file server to save" idea is a misunderstanding: you only need the
  page to be **served** (GitHub Pages does this). It will NOT run by double-clicking
  `index.html` from `file://`, because browsers block the WebAssembly worker /
  same-origin loading of the ffmpeg core in that mode. The actual export still
  happens locally in your browser — it just needs the page delivered over http(s).
- **Slower and lower quality than local** (WebAssembly ffmpeg is slower than native,
  and currently set to 30fps + the old 1.5× scale), but it's free and serverless.

### Quick comparison

| Aspect            | Local (`local-server`)        | Web (`main`, GitHub Pages)     |
| ----------------- | ----------------------------- | ------------------------------ |
| ffmpeg            | Native (libx264)              | ffmpeg.wasm (WebAssembly)      |
| Where it runs     | Your PC via Flask server      | Your browser (no server)       |
| Hosting           | `python server.py` localhost  | Static files on GitHub Pages   |
| Speed             | Fast                          | Slower                         |
| Quality           | Max (crf16, slow, 60fps, 1080)| Lower (crf, 30fps, 1.5× scale) |
| Smooth-rotation fix | ✅ applied                   | ✅ applied (30fps)             |
| Upload to cloud   | No (local temp)               | No (in-browser)                |

---

## 3. Web version — smooth-rotation fix APPLIED (2026-06-29)

The same fix is portable to the web build (it runs the same chain via `ffmpeg.wasm`),
so it was tested on a `web-smooth-test` worktree and then merged into **`main`**:

1. **Warm-up / seam fix** — added `(t-warm)` phase shift +
   `trim=start_frame=SUB, setpts=PTS-STARTPTS` to the in-browser filter string.
2. **Real 1080p** — `EXPORT_SCALE = 1.0` and 1080p format cards (stops 2880×1620).
3. **fps kept at 30** — wasm is much slower than native, so 30fps balances quality
   vs in-browser render time. (Local stays 60fps because native ffmpeg is fast.)

Status: merged to `main` (commits `7175f1d` + `f7788e0`), audio bumped to 256k
(`6ffa0d2`), and **pushed live** (tag `web-v2.0`). Validated locally on :8001 first.

## 4. Audio quality
Both versions encode AAC **256k** (local: 2026-06-27; web: 2026-06-29). Video is
Full HD H.264 (local crf16/slow; web crf20/veryfast). No destructive compression.

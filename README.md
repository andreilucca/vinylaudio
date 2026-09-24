# Storytellers, Spinning Vinyl Video Maker

### Live app: **https://andreilucca.github.io/vinylaudio/**

**Current version: WEB v6.9 (2026-09-24)**

Turn a photo and a song into a smooth, professional spinning vinyl MP4 with an
animated effects engine. Everything renders 100% in your browser: no server,
no upload, no watermark, no account. Your files never leave your device.

## Features

- **Photo to spinning vinyl**: your image becomes the rotating record label,
  with drop shadow, anti-aliased circular edge and centre spindle hole. Three
  artwork modes: **Disc** (spinning record), **Card** (centred poster) and
  **Off** (background effect fills the whole frame).
- **Effects engine (WebGL)**: 28 animated background effects (Melt, Palette
  flow, Vortex, Ripple, Bloom, Nebula, Tunnel, Kaleido, Glitch, Spectrum,
  Droste, Warp, Liquid, Reactor, Echo, Datamosh, VHS, Burn, Halftone, Slices,
  Feedback, Dither, ASCII, Twinspin, Depth 3D, Cymatics, Topographic, CRT)
  with per-effect settings, palette editing, and forward and reverse
  direction. Effects marked **FULL** rotate or evolve continuously and need
  Export render: Full render on full songs (the app reminds you with a toast).
- **Finishing dials**: Aberration, Glow, Grain and Vignette apply on top of
  any effect; all default to 0 (image untouched) and reset together with the
  effect settings.
- **Optional audio**: MP3, WAV, OGG, M4A, or export a silent clip. Full song
  of any length, or a fixed window (30s or 1m) dragged across the waveform,
  with audio preview.
- **Social formats**: Square 1080x1080, Portrait 1080x1350, Story 1080x1920,
  Wide 1920x1080 (YouTube).
- **60 fps deterministic export**: every frame is computed at its exact
  timestamp with a perfectly constant rotation step per frame. Zero dropped or
  duplicated frames, by construction. The export matches the live preview.
- **Fast full-song exports (Fast loop)**: only one short seamless loop is
  rendered (whole disc revolutions plus a 1 second background crossfade baked
  at render time), then stream-copied to the full song length. A 6 minute song
  exports in roughly the same time as a 1 minute clip. **Full render** computes
  every frame of the song 1:1 and is required for FULL-tagged effects.
- **Full-song safe**: the export bitrate adapts to the song length so long
  tracks always fit in browser memory (up to 45 Mbps on short clips, around
  24 Mbps at 5 to 6 minutes, never below 8 Mbps on the GPU path), with a
  keyframe every 2 seconds for clean seeking.
- **Platform-friendly heavy effects (v6.9)**: Grain reseeds its noise pattern
  at 10 Hz instead of every frame, the CRT 37 Hz full-frame flicker was
  removed, and VHS snow was calmed (8 Hz reseed, halved amplitude). Motion,
  rotation and frame rate are untouched; the change only lowers the temporal
  entropy of the encoded pixels, so platform re-encoders (YouTube) keep the HD
  rungs cheap enough to serve on Auto quality.

## How the export works

The exporter picks the best available strategy at record time. The chosen
strategy is logged to the browser console as `[vinylaudio export] strategy:`.

**1. Deterministic GPU export (primary, WebCodecs).** Frames are rendered by
the WebGL engine one at a time at exact timestamps and handed straight to the
GPU hardware H.264 encoder in quality mode. No real-time capture and no
intermediate encode generation. Output is 60 fps for both fast loop and full
render. The loop crossfade is baked during rendering, so the H.264 stream is
encoded exactly once; ffmpeg.wasm only remuxes it and muxes the original
audio (AAC 320k, faststart).

**2. Real-time capture (fallback).** On browsers without WebCodecs H.264
support, the scene is captured live (MediaRecorder at up to 60 Mbps), then
ffmpeg.wasm bakes the loop crossfade (x264 superfast, crf 16, adaptive
maxrate, keyframe every 2 seconds) and muxes the audio.

**Classic exporter (effects off).** The disc rotation is perfectly periodic,
so a single revolution is rendered once with sub-frame motion blur, encoded,
then stream-copy-looped to the full duration with the original audio muxed in.

ffmpeg.wasm is vendored in `vendor/ffmpeg` (nothing fetched from a CDN) and is
preloaded in the background when the page opens, so recording starts
instantly. Browser memory is limited to roughly 2 GB, which is why the
bitrate adapts to duration; very long mixes (20+ minutes) export at more
modest bitrates.

## Project structure

```
index.html          the whole app (UI, WebGL engine, exporters)
vendor/ffmpeg/      vendored ffmpeg.wasm (works offline, no CDN)
fonts/              embedded fonts
```

## Usage

1. Open the live app (or serve this folder with any static web server).
2. Upload the artwork, optionally the song, pick a format.
3. Optionally enable an effect and tune it; the preview is what you get.
4. Record Video, then Download MP4.

## Uploading to YouTube

The exported MP4 is always complete 1080p/60. What YouTube serves on **Auto**
quality is decided per upload by its server-side adaptive bitrate (SABR),
and heavy content matters:

- Smooth effects (Bloom, Warp, Liquid...) are cheap to re-encode and usually
  get HD on Auto right away.
- Detail-dense effects (Depth 3D, CRT, VHS...) produce expensive 1080p
  renditions; a fresh upload can sit on Auto 360p even though 1080p60 is
  already processed and works when selected manually.
- **If a fresh upload stays on Auto 360p, delete the video and upload the same
  file again.** The serving decision is made per upload, not per file, and a
  re-upload of the identical MP4 typically lands directly on HD. Waiting has
  no guaranteed deadline; re-uploading takes 10 minutes.
- There is no uploader-side setting to force playback quality for viewers;
  the only upload-side levers are re-uploading and higher-resolution masters.

## Troubleshooting

- After an update, check the version tag in the footer (bottom right); hard
  refresh with Ctrl+F5 if it shows an older version. Current:
  `WEB v6.9 · 2026-09-24`.
- The console line `[vinylaudio export] strategy:` tells you which pipeline
  ran: `webcodecs avc1...` means the GPU encoder (the progress label also
  shows `GPU encode`), anything else means the real-time fallback.
- Playback stutter on YouTube while the app is exporting is expected: the GPU
  encode and the browser's 1080p60 decode compete for the same GPU. Check
  Stats for nerds ("dropped of" counter) and retest with the app tab closed.
- FULL-tagged effects on a full song need Export render: Full render;
  Fast loop would reset their continuous rotation at every loop.

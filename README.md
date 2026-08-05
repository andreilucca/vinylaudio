# Storytellers, Spinning Vinyl Video Maker

### Live app: **https://andreilucca.github.io/vinylaudio/**

Turn a photo and a song into a smooth, professional spinning vinyl MP4 with an
animated effects engine. Everything renders 100% in your browser: no server,
no upload, no watermark, no account. Your files never leave your device.

## Features

- **Photo to spinning vinyl**: your image becomes the rotating record label,
  with drop shadow, anti-aliased circular edge and centre spindle hole.
- **Effects engine (WebGL)**: 14 animated background effects (Melt, Vortex,
  Ripple, Tunnel, Kaleido, Glitch, Droste, Liquid, Palette flow, Bloom, Nebula,
  Spectrum, Warp, Reactor) with per-effect settings, palette editing, forward
  and reverse direction, and optional trails.
- **Beat sync**: effects react to the music (clips up to 1 minute). For export,
  the beat and spectrum are computed offline from the decoded audio with the
  same maths as the live analyser, so reactions land on exact frame times.
- **Optional audio**: MP3, WAV, OGG, M4A, or export a silent clip. Full song of
  any length, or a fixed window (30s or 1m) dragged across the waveform, with
  audio preview.
- **Social formats**: Square 1080x1080, Portrait 1080x1350, Story 1080x1920,
  Wide 1920x1080 (YouTube).
- **60 fps deterministic export**: every frame is computed at its exact
  timestamp with a perfectly constant rotation step per frame. Zero dropped or
  duplicated frames, by construction. The export matches the live preview.
- **Fast full-song exports**: with beat sync off, only one short seamless loop
  is rendered (whole disc revolutions plus a 1 second background crossfade
  baked at render time), then stream-copied to the full song length. A 6 minute
  song exports in roughly the same time as a 1 minute clip.
- **Full-song safe**: the export bitrate adapts to the song length so long
  tracks always fit in browser memory (up to 45 Mbps on short clips, around
  25 Mbps at 5 to 6 minutes, never below 6 Mbps), with a keyframe every
  2 seconds for clean seeking.

## How the export works

The exporter picks the best available strategy at record time. The chosen
strategy is logged to the browser console as `[vinylaudio export] strategy:`.

**1. Deterministic GPU export (primary, WebCodecs).** Frames are rendered by
the WebGL engine one at a time at exact timestamps and handed straight to the
GPU hardware H.264 encoder in quality mode. No real-time capture and no
intermediate encode generation. Output is 60 fps for both fast loop and beat
sync. The loop crossfade is baked during rendering, so the H.264 stream is
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

## Troubleshooting

- After an update, check the version tag in the footer (bottom right); hard
  refresh with Ctrl+F5 if it shows an older version.
- The console line `[vinylaudio export] strategy:` tells you which pipeline
  ran: `webcodecs avc1...` means the GPU encoder (the progress label also
  shows `GPU encode`), anything else means the real-time fallback.
- Beat sync is available for clips up to 1 minute; loading a full song
  disables it automatically.

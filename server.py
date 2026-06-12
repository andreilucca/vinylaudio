"""
Storytellers — server-side MP4 export (like turn.audio).

Browser WebCodecs export proved too slow/inconsistent, so rendering is done here
with ffmpeg + libx264. The page composes a static background, a circular disc
sprite and an optional foreground with Pillow, then ffmpeg rotates the disc over
time, overlays everything and muxes the (optionally trimmed) audio.

Run:  python server.py   then open  http://localhost:8000/
"""

import io
import os
import glob
import math
import shutil
import tempfile
import subprocess

from flask import Flask, request, send_file, send_from_directory, abort
from PIL import Image, ImageDraw, ImageFilter, ImageChops

ROOT = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=None)


# ── ffmpeg discovery ──────────────────────────────────────────────────────────
def _find_exe(name):
    """Locate an ffmpeg/ffprobe exe (PATH first, then the winget install dir)."""
    found = shutil.which(name)
    if found:
        return found
    pattern = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Microsoft", "WinGet", "Packages",
        "Gyan.FFmpeg*", "**", name + ".exe",
    )
    hits = glob.glob(pattern, recursive=True)
    return hits[0] if hits else name


FFMPEG = _find_exe("ffmpeg")


# ── image helpers ─────────────────────────────────────────────────────────────
def _cover(img, w, h):
    """Scale + center-crop `img` to exactly w×h (CSS object-fit: cover)."""
    img = img.convert("RGBA")
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _hex(c, default=(17, 17, 17)):
    c = (c or "").strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return default
    try:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


def build_art(R, art_img):
    """Square artwork (D×D, D=2R) that will be ROTATED each frame. No circular
    clip here — the clean circular edge is provided by the STATIC frame overlay,
    so rotation never touches (and never aliases) the disc's edge."""
    D = max(2, round(R * 2))
    if art_img is not None:
        return _cover(art_img, D, D)
    return Image.new("RGBA", (D, D), (26, 26, 26, 255))


def build_frame(w, h, bg_color, bg_img, R, has_bg_img):
    """Full-canvas STATIC overlay drawn ON TOP of the rotating artwork:
      - background (color + image + drop shadow) everywhere OUTSIDE the disc,
      - a transparent, anti-aliased circular hole (radius R) where the spinning
        art shows through — this fixed circle is what makes the edge perfectly
        smooth instead of the jagged, re-sampled edge a rotated disc produces,
      - the outer edge ring and the center spindle hole (also static)."""
    cx, cy = w / 2, h / 2
    base = Image.new("RGBA", (w, h), bg_color + (255,))
    if bg_img is not None:
        base.alpha_composite(_cover(bg_img, w, h))

    # Drop shadow: blurred black disc, offset downward (matches canvas shadow).
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        [cx - R, cy - R + 18, cx + R, cy + R + 18], fill=(0, 0, 0, 184))
    shadow = shadow.filter(ImageFilter.GaussianBlur(30))
    base.alpha_composite(shadow)

    ss = 4  # supersample factor for crisp, anti-aliased circular edges

    # Punch the transparent circular hole (subtract an AA disc from the alpha).
    hole = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(hole).ellipse(
        [(cx - R) * ss, (cy - R) * ss, (cx + R) * ss, (cy + R) * ss], fill=255)
    hole = hole.resize((w, h), Image.LANCZOS)
    r, g, b, a = base.split()
    a = ImageChops.subtract(a, hole)
    base = Image.merge("RGBA", (r, g, b, a))

    # Static marks (ring + spindle hole) on a supersampled layer for smooth AA.
    marks = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    md = ImageDraw.Draw(marks)
    md.ellipse([(cx - R + 1) * ss, (cy - R + 1) * ss,
                (cx + R - 1) * ss, (cy + R - 1) * ss],
               outline=(255, 255, 255, 36), width=2 * ss)
    spin = max(1.0, R * 0.022)
    hole_fill = (10, 10, 10, 255) if has_bg_img else bg_color + (255,)
    md.ellipse([(cx - spin) * ss, (cy - spin) * ss,
                (cx + spin) * ss, (cy + spin) * ss], fill=hole_fill)
    md.ellipse([(cx - spin) * ss, (cy - spin) * ss,
                (cx + spin) * ss, (cy + spin) * ss],
               outline=(255, 255, 255, 56), width=max(1, ss))
    marks = marks.resize((w, h), Image.LANCZOS)
    base.alpha_composite(marks)
    return base


def _open(file_storage):
    if file_storage is None or file_storage.filename == "":
        return None
    return Image.open(io.BytesIO(file_storage.read()))


# ── routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(ROOT, "index.html")


@app.route("/<path:path>")
def static_files(path):
    full = os.path.join(ROOT, path)
    if os.path.isfile(full):
        return send_from_directory(ROOT, path)
    abort(404)


@app.route("/export", methods=["POST"])
def export():
    try:
        w = int(float(request.form.get("w", 720)))
        h = int(float(request.form.get("h", 720)))
        rpm = float(request.form.get("rpm", 33))
        duration = max(0.1, float(request.form.get("duration", 30)))
        vinyl_pct = float(request.form.get("vinylPct", 0.86))
        bg_color = _hex(request.form.get("bgColor", "#111111"))
        audio_start = float(request.form.get("audioStart", 0))
        fps = int(float(request.form.get("fps", 30)))
    except (TypeError, ValueError):
        return {"error": "bad parameters"}, 400

    art_img = _open(request.files.get("image"))
    if art_img is None:
        return {"error": "missing image"}, 400
    bg_img = _open(request.files.get("bg"))
    fg_img = _open(request.files.get("fg"))
    audio = request.files.get("audio")
    has_audio = audio is not None and audio.filename != ""

    R = min(w, h) * vinyl_pct / 2

    work = tempfile.mkdtemp(prefix="story_")
    try:
        art_path = os.path.join(work, "art.png")
        frame_path = os.path.join(work, "frame.png")
        out_path = os.path.join(work, "out.mp4")

        art = build_art(R, art_img)
        art.save(art_path)
        build_frame(w, h, bg_color, bg_img, R, bg_img is not None).save(frame_path)
        art_d = art.size[0]                      # square side (= 2R)
        # rotate expands the canvas to the diagonal so the artwork ALWAYS fully
        # covers the circular hole at every angle (no transparent corners creep in).
        rot = math.ceil(art_d * 1.4143)

        fg_path = None
        if fg_img is not None:
            fg_path = os.path.join(work, "fg.png")
            _cover(fg_img, w, h).save(fg_path)

        audio_path = None
        if has_audio:
            audio_path = os.path.join(work, "audio_in")
            audio.save(audio_path)

        # A spinning disc is perfectly periodic: after one full revolution the
        # image repeats exactly. So instead of rendering every frame for the whole
        # clip (the rotate filter is the bottleneck), we render the shortest
        # segment that covers a WHOLE number of revolutions AND a whole number of
        # frames, then loop it (stream copy, no re-encode) to fill the duration
        # and mux the audio. For rpm=33/30fps this renders 600 frames instead of
        # 1800 — a 3x speedup — and the loop is seamless because frame N == frame 0.
        total_frames = max(1, round(fps * duration))
        rpm_int = round(rpm)
        seg_frames = total_frames
        if rpm_int > 0 and abs(rpm - rpm_int) < 1e-6:
            g = math.gcd(fps * 60, rpm_int)
            candidate = (fps * 60) // g          # frames for integer revolutions
            if 0 < candidate < total_frames:
                seg_frames = candidate

        seg_path = os.path.join(work, "seg.mp4")
        # input 0 = artwork (rotates), input 1 = static frame overlay (clean edge)
        seg_cmd = [FFMPEG, "-y", "-loop", "1", "-i", art_path,
                   "-loop", "1", "-i", frame_path]
        fg_idx = None
        if fg_path is not None:
            seg_cmd += ["-loop", "1", "-i", fg_path]
            fg_idx = 2

        # Motion blur for fluid rotation: render the spin at SUB× the target fps,
        # then average each group of SUB sub-frames (tmix) and resample down to
        # the target fps. A disc stepping ~6.6°/frame at 30fps looks slightly
        # choppy; blending sub-frames smears that step into smooth motion blur,
        # exactly how real cameras (and turn.audio) make rotation look fluid.
        SUB = 4
        hi = fps * SUB
        # Rotate ONLY the artwork (high-quality bilinear), composite onto black,
        # then lay the STATIC frame on top so the circular edge is a fixed,
        # anti-aliased circle that never gets re-sampled (no jagged spinning edge).
        chain = (
            f"color=c=black:s={w}x{h}:r={hi}[base];"
            f"[0:v]format=rgba,rotate=2*PI*{rpm}*t/60:ow={rot}:oh={rot}:c=none[art];"
            f"[base][art]overlay=(W-w)/2:(H-h)/2:format=auto[t1];"
            f"[t1][1:v]overlay=0:0[v1]"
        )
        last = "[v1]"
        if fg_idx is not None:
            chain += f";[v1][{fg_idx}:v]overlay=0:0[v2]"
            last = "[v2]"
        # Sub-frame averaging → motion blur, then down to target fps.
        chain += (
            f";{last}tmix=frames={SUB}:weights={' '.join(['1'] * SUB)},"
            f"fps={fps}[vout]"
        )
        last = "[vout]"

        seg_cmd += [
            "-filter_complex", chain, "-map", last,
            "-frames:v", str(seg_frames),
            "-r", str(fps),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-crf", "18",
            "-g", str(seg_frames),     # one closed GOP per segment → clean looping
            out_path if seg_frames >= total_frames and not has_audio else seg_path,
        ]

        proc = subprocess.run(seg_cmd, capture_output=True, text=True)
        seg_out = seg_cmd[-1]
        if proc.returncode != 0 or not os.path.isfile(seg_out):
            return {"error": "ffmpeg failed", "detail": proc.stderr[-2000:]}, 500

        # If the segment already is the whole clip and there's no audio, we're done.
        if seg_out == out_path:
            with open(out_path, "rb") as f:
                data = f.read()
            return send_file(io.BytesIO(data), mimetype="video/mp4",
                             as_attachment=True, download_name="storytellers.mp4")

        # Loop the segment (no re-encode) to the full duration and mux audio.
        loop_cmd = [FFMPEG, "-y", "-stream_loop", "-1", "-i", seg_path]
        if audio_path is not None:
            loop_cmd += ["-ss", str(audio_start), "-i", audio_path]
        loop_cmd += ["-map", "0:v", "-t", str(duration), "-c:v", "copy"]
        if audio_path is not None:
            loop_cmd += ["-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
        loop_cmd += ["-movflags", "+faststart", out_path]

        proc = subprocess.run(loop_cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.isfile(out_path):
            return {"error": "ffmpeg loop failed", "detail": proc.stderr[-2000:]}, 500

        with open(out_path, "rb") as f:
            data = f.read()
        return send_file(io.BytesIO(data), mimetype="video/mp4",
                         as_attachment=True, download_name="storytellers.mp4")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    print(f"ffmpeg: {FFMPEG}")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Storytellers server → http://{host}:{port}/")
    app.run(host=host, port=port, threaded=True)

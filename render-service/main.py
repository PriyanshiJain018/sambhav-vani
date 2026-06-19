"""
Sambhav Vani Reel Studio — Render Service
FastAPI + native FFmpeg (with libass + Noto Devanagari)

POST /render  →  video/mp4
"""

import os, uuid, shutil, subprocess, tempfile, json, math, re
from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SVRS Render Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your PWA origin in production
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

RENDER_TOKEN = os.environ.get("RENDER_TOKEN", "")        # set in env; empty = no auth
FONTSDIR     = os.environ.get("FONTSDIR", "/usr/share/fonts/truetype/noto")
FFMPEG       = os.environ.get("FFMPEG_BIN", "ffmpeg")


def check_auth(token: str):
    if RENDER_TOKEN and token != RENDER_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def sec_to_ass(s: float) -> str:
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    cs = int(round((sec - int(sec)) * 100))
    return f"{h}:{m:02d}:{int(sec):02d}.{cs:02d}"


def build_title_ass(title_text: str, clip_duration: float, p: dict) -> str:
    # Sanitise: replace curly braces and newlines
    safe = title_text.replace("{", "(").replace("}", ")").replace("\n", " ")
    end_ts = sec_to_ass(clip_duration)
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {p['res_w']}
PlayResY: {p['res_h']}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T,Noto Sans Devanagari,{p['title_fontsize']},&H004AD2FF,&H00202020,&H80000000,1,0,0,0,100,100,0,0,1,3,1,{p['title_alignment']},50,50,{p['title_margin_top']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,{end_ts},T,,0,0,0,,{safe}
"""


def _srt_ts_to_ass(ts: str) -> str:
    ts = ts.strip().replace(",", ".")
    h, m, s = ts.split(":")
    sec = float(s)
    cs = int(round((sec - int(sec)) * 100))
    return f"{int(h)}:{int(m):02d}:{int(sec):02d}.{cs:02d}"


def srt_to_ass(srt_text: str, p: dict) -> str:
    """Convert a (rebased) SRT into ASS at true res_w x res_h, so subtitle font
    size and margins are real pixels — consistent with the title layer."""
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    events = []
    for b in blocks:
        lines = [l for l in b.splitlines() if l.strip() != ""]
        if len(lines) < 2:
            continue
        ti = 0 if "-->" in lines[0] else (1 if len(lines) > 1 and "-->" in lines[1] else None)
        if ti is None:
            continue
        start_raw, end_raw = lines[ti].split("-->")
        text = "\\N".join(lines[ti + 1:]).replace("{", "(").replace("}", ")")
        if not text.strip():
            continue
        events.append((_srt_ts_to_ass(start_raw), _srt_ts_to_ass(end_raw), text))

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {p['res_w']}
PlayResY: {p['res_h']}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: S,Noto Sans Devanagari,{p['sub_fontsize']},&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,80,80,{p['sub_margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "".join(f"Dialogue: 0,{s},{e},S,,0,0,0,,{t}\n" for s, e, t in events)
    return header + body


def build_filter(sub_ass: str, title_ass: str, logo_path: str | None, clip_dur: float, p: dict) -> tuple[str, list]:
    """Returns (filter_complex_string, extra_input_args)"""

    # Escape paths for ffmpeg filter strings
    def esc(path):
        return path.replace("\\", "/").replace("'", "\\'").replace(":", "\\:")

    logo_x = f"W-w-{p['logo_margin']}" if p["logo_side"] == "right" else str(p["logo_margin"])
    fade   = p["fade"]
    dur    = clip_dur
    lm     = p["logo_margin"]
    lp     = p["logo_period"]

    base = (
        f"[0:v]crop='min(iw,ih*9/16)':ih,scale={p['res_w']}:{p['res_h']},setsar=1[v];"
        f"[v]ass='{esc(sub_ass)}':fontsdir='{esc(FONTSDIR)}'[vs];"
        f"[vs]ass='{esc(title_ass)}':fontsdir='{esc(FONTSDIR)}'[vt];"
    )

    extra_inputs = []

    if logo_path:
        logo_filter = (
            f"[1:v]scale={p['logo_w']}:-1,format=rgba,"
            f"colorchannelmixer=aa={p['logo_alpha']}[lg];"
            f"[vt][lg]overlay=x='{logo_x}':"
            f"y='{lm}+(H-h-{2*lm})*(0.5+0.5*sin(2*PI*t/{lp}))':eval=frame[ov];"
            f"[ov]fade=t=in:st=0:d={fade},fade=t=out:st={max(0,dur-fade)}:d={fade}[outv]"
        )
        extra_inputs = ["-i", logo_path]
    else:
        logo_filter = (
            f"[vt]fade=t=in:st=0:d={fade},fade=t=out:st={max(0,dur-fade)}:d={fade}[outv]"
        )

    return base + logo_filter, extra_inputs


@app.get("/health")
def health():
    return {"status": "ok", "ffmpeg": shutil.which(FFMPEG) or "not found"}


@app.post("/render")
async def render(
    source:     UploadFile = File(...),
    clip_srt:   UploadFile = File(...),
    title_text: str        = Form(...),
    clip_start: float      = Form(...),
    clip_end:   float      = Form(...),
    params:     str        = Form("{}"),
    logo:       UploadFile = File(None),
    x_render_token: str    = Header(default=""),
):
    check_auth(x_render_token)

    p = {**{
        "res_w": 1080, "res_h": 1920, "fade": 0.5,
        "sub_fontsize": 54, "sub_margin_v": 160,
        "title_fontsize": 60, "title_margin_top": 170, "title_alignment": 8,
        "logo_w": 130, "logo_alpha": 0.4, "logo_margin": 40,
        "logo_period": 26, "logo_side": "right",
    }, **json.loads(params)}

    clip_dur = clip_end - clip_start
    if clip_dur <= 0:
        raise HTTPException(400, detail="clip_end must be > clip_start")

    work = tempfile.mkdtemp(prefix="svrs_")
    try:
        # Write uploads to disk
        src_path  = os.path.join(work, "source" + Path(source.filename).suffix)
        srt_path  = os.path.join(work, "clip.srt")
        ass_path  = os.path.join(work, "title.ass")
        out_path  = os.path.join(work, "output.mp4")
        logo_path = None

        with open(src_path, "wb")  as f: f.write(await source.read())
        with open(srt_path, "wb")  as f: f.write(await clip_srt.read())

        if logo and logo.filename:
            logo_path = os.path.join(work, "logo" + Path(logo.filename).suffix)
            with open(logo_path, "wb") as f: f.write(await logo.read())

        # Build ASS title file
        ass_content = build_title_ass(title_text, clip_dur, p)
        with open(ass_path, "w", encoding="utf-8") as f: f.write(ass_content)

        # Convert incoming (rebased) SRT -> ASS at true resolution for correct subtitle sizing
        sub_ass_path = os.path.join(work, "subs.ass")
        srt_text = open(srt_path, encoding="utf-8", errors="replace").read()
        with open(sub_ass_path, "w", encoding="utf-8") as f: f.write(srt_to_ass(srt_text, p))

        # Build filter_complex
        filter_str, extra_inputs = build_filter(sub_ass_path, ass_path, logo_path, clip_dur, p)

        # Compose FFmpeg command
        cmd = [
            FFMPEG, "-y",
            "-ss", str(clip_start), "-t", str(clip_dur),
            "-i", src_path,
        ] + (extra_inputs) + [
            "-filter_complex", filter_str,
            "-map", "[outv]", "-map", "0:a?",
            "-af", f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:d=0.3,afade=t=out:st={max(0, clip_dur-0.3)}:d=0.3",
            "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", "-shortest",
            out_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            tail = (result.stderr or "")[-2000:]
            return JSONResponse(status_code=500, content={
                "error": "render_failed",
                "ffmpeg_stderr_tail": tail
            })

        return FileResponse(out_path, media_type="video/mp4", filename="reel.mp4")

    except subprocess.TimeoutExpired:
        return JSONResponse(status_code=500, content={"error": "render_timeout"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        shutil.rmtree(work, ignore_errors=True)

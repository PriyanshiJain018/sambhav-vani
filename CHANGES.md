# Fixes & Enhancements applied to this build

## Blocking bug fixed (this is why the original would have failed silently)
- **Sarvam response parsing (`public/index.html`, Stage 0).** The app read `data.transcript.transcript`
  and `data.transcript.timestamps` (wrong nesting). Sarvam returns `data.transcript` (string) and
  `data.timestamps` (object) at the top level — proven by your working transcriber. The old code
  produced an empty transcript and zero timestamps for every chunk while reporting success, which
  then fed nothing into clip-select, subtitles, and render. Now reads the correct top-level shape and
  mirrors the proven transcriber's behaviour (chunk-level fallback cue when no word timestamps; empty
  chunk treated as silent, not a false success).

## Alignment with the proven transcriber
- Added `mode: 'transcribe'` for `saaras*` models (keeps Hindi / मूल भाषा). The old app omitted it.

## Render correctness
- **Trim:** replaced `-to <clip_end>` with `-t <clip_dur>`. `-to` as an input option is version-dependent;
  `-t` (duration) is unambiguous across FFmpeg builds.
- **Subtitle sizing root-cause fix:** the SRT was rendered with the `subtitles` filter, whose default
  script height is 288px, so font size and margins were silently scaled ~6.7×. The service now converts
  the incoming (rebased) SRT to ASS at true `res_w×res_h` and renders it with the `ass` filter — same
  coordinate system as the title. Font sizes and margins are now **real pixels** and predictable.

## Reel-quality enhancements (all tunable in Config → Render params)
- `sub_fontsize` 18 → **54**, `sub_margin_v` 90 → **160**, `title_fontsize` 52 → **60** (now true px).
- **Bold subtitles** with black outline + drop shadow (CapCut-style, readable on any background;
  cleaner/more native than the old opaque box).
- **Loudness normalization** (`loudnorm` to ~-14 LUFS) — consistent, mobile-appropriate volume across
  pravachans recorded at different levels.
- **`-pix_fmt yuv420p`** — universal playback (iOS/Instagram/QuickTime reject some other pixel formats).
- **`-movflags +faststart`** — moov atom at front so the reel previews/streams before full download.
- **48 kHz / 192 kbps AAC** — standard, avoids loudnorm leaving a non-standard sample rate.

## Verified (render path tested end-to-end with real FFmpeg)
Synthetic landscape source → 1080×1920 H.264, yuv420p, AAC 48 kHz, faststart, exact clip duration,
Hindi title + subtitles shaping correctly via Noto Sans Devanagari, logo drifting on the side.

## Not testable here — verify on your side
- **Live PWA run** (IndexedDB, WebAudio decode/chunk, real Sarvam/Gemini/Groq calls with your keys).
  Code is consistent with your working transcriber and the LLM response shapes are correct, but a real
  browser run with keys is the final check. Start with a 5-min MP3.
- **Word-level subtitle sync depends on Sarvam returning word timestamps.** If `saaras:v3` returns only
  text for your audio, subtitles fall back to even-split timing per 29s chunk (same as your current
  transcriber — no worse). For tight word-sync, the `saarika` ASR model returns word timestamps but
  changes language/script behaviour; test before switching.
- First production render: confirm `fc-list | grep -i devanagari` is non-empty inside the deployed
  container (the Dockerfile installs `fonts-noto` and checks at build time).

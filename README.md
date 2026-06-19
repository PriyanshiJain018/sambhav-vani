# Sambhav Vani Reel Studio

**Raw pravachan → finished 1080×1920 reel — in one session.**

Transcribe → Clip Select → Subtitle Correction → Title → Render → Metadata → Review & Download.

---

## What's in this repo

```
sambhav-vani-studio/
├── public/                   ← PWA (static files — deploy to Netlify/Vercel)
│   ├── index.html            ← The entire app (single HTML file)
│   ├── manifest.json         ← PWA install manifest
│   ├── sw.js                 ← Service worker (offline shell + font cache)
│   └── icons/
│       ├── icon-192.png      ← App icon (auto-generated)
│       └── icon-512.png
├── render-service/           ← FFmpeg backend (deploy to Fly.io / Cloud Run)
│   ├── main.py               ← FastAPI app
│   ├── requirements.txt
│   ├── Dockerfile
│   └── fly.toml
├── src/
│   ├── sarvam-proxy.js       ← Cloudflare Worker (forward Sarvam STT calls)
│   └── generate_icons.py     ← One-time icon generator
├── netlify.toml              ← Netlify deploy config
└── vercel.json               ← Vercel deploy config (alternative)
```

---

## Part 1 — Accounts & API Keys you need

Get these before anything else. All free tiers are sufficient to start.

| Service | What it does | Get key at |
|---|---|---|
| **Sarvam AI** | Hindi STT (transcription) | [dashboard.sarvam.ai](https://dashboard.sarvam.ai) — ₹1,000 free credit (~33 hrs) |
| **Google AI Studio** | Gemini (clip select, title, metadata, correction) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — free tier |
| **Groq** | Llama checker model (subtitle correction) | [console.groq.com](https://console.groq.com) — free tier |
| **Cloudflare** | Sarvam proxy Worker | [dash.cloudflare.com](https://dash.cloudflare.com) — free |
| **Fly.io** | Render service hosting | [fly.io](https://fly.io) — free hobby tier |
| **Netlify** or **Vercel** | PWA hosting | [netlify.com](https://netlify.com) or [vercel.com](https://vercel.com) — free |

---

## Part 2 — Step-by-step deployment

### Step 1 — Deploy the Sarvam Proxy (Cloudflare Worker)

This worker is required because Sarvam blocks direct browser requests (CORS).

**You may already have this** from the old transcriber. If so, skip to Step 2.

```bash
# Install Wrangler (Cloudflare CLI)
npm install -g wrangler
wrangler login

# Edit sarvam-proxy.js first:
# → In ALLOWED_ORIGINS, add your future Netlify/Vercel URL
# → e.g. "https://sambhav-vani.netlify.app"

# Deploy
wrangler deploy src/sarvam-proxy.js --name sarvam-proxy
```

Your proxy URL will be: `https://sarvam-proxy.<your-subdomain>.workers.dev`

Save this URL — you'll paste it in the app's Keys menu.

---

### Step 2 — Deploy the Render Service (Fly.io)

This is the FFmpeg backend that builds the 1080×1920 reel.

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Navigate to render service
cd render-service

# First-time launch (creates the app on Fly)
fly launch --config fly.toml --no-deploy

# Set the shared secret token (pick any strong random string)
fly secrets set RENDER_TOKEN=your-strong-secret-here

# Deploy
fly deploy

# Test it's up
curl https://svrs-render.fly.dev/health
# → {"status":"ok","ffmpeg":"..."}
```

Your render service URL: `https://svrs-render.fly.dev`
Your render token: whatever you set above.

**Cost:** Fly.io auto-stops the machine when idle. A 60-second reel takes ~60–90 seconds to render on 1 shared CPU. With scale-to-zero, you pay only for active compute (~$0.003/minute).

**Alternative: Cloud Run (Google)**
```bash
cd render-service
gcloud run deploy svrs-render \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars RENDER_TOKEN=your-token
```

---

### Step 3 — Deploy the PWA (Netlify)

```bash
# Option A: Netlify CLI
npm install -g netlify-cli
netlify login
netlify deploy --dir public --prod

# Option B: Netlify Dashboard
# → New site → Deploy manually → Drag the /public folder
```

Your app URL: `https://your-site.netlify.app`

**Important after deploying:** Go back to `src/sarvam-proxy.js`, add your Netlify URL to `ALLOWED_ORIGINS`, and redeploy the Worker.

**Alternative: Vercel**
```bash
npm install -g vercel
vercel --prod
# Vercel auto-detects vercel.json and serves the /public folder
```

---

### Step 4 — Configure Keys in the App

Open your deployed PWA. Click **Keys** in the top nav.

Fill in and Save each field:

| Field | Value |
|---|---|
| Sarvam API Key | From dashboard.sarvam.ai |
| Sarvam Proxy URL | `https://sarvam-proxy.your-subdomain.workers.dev` |
| Gemini API Key | From aistudio.google.com |
| LLM Proxy URL | Leave blank (Gemini supports CORS directly) |
| Groq API Key | From console.groq.com |
| Render Service URL | `https://svrs-render.fly.dev` |
| Render Token | The secret you set in Step 2 |

Click **Test** on Gemini and Groq to verify. Sarvam is tested on first transcription.

---

## Part 3 — Using the App

### Assisted Mode (default — recommended for same-day content)

1. **Open the app** → Studio tab
2. **Upload** your pravachan file (mp3, m4a, mp4, etc.)
3. Click **📝 Transcribe करें** — watch progress, 3 chunks in parallel
4. Review/edit the transcript if needed
5. Click **अगला: Clip चुनें →**
6. **5 candidates** appear with Hindi titles and reasons
7. Click the one you want → adjust In/Out seconds if needed
8. Click **✅ इस Clip को चुनें**
9. Correction runs automatically (Maker → Checker). Diff is shown.
10. Title is generated — edit inline if you want
11. Render runs (~60–90s). Keep the tab open.
12. Metadata (title/description/hashtags) is written
13. **Review tab opens** — preview the video, then **Download**

Total operator time: ~5 minutes for a 60-minute pravachan.

---

### Auto Mode (batch / backlog)

Click the **Assisted** badge in the top-right to switch to **Auto**.

Upload → Transcribe → Click **अगला** → The app picks the best clip and runs the full pipeline. You only intervene at the final Review screen. Zero decisions mid-pipeline.

---

### Config Menu

All prompts and render params are editable live — no code changes needed.

**Key things to tune:**
- **Clip Min/Max seconds** — default 20–60s. Increase max for longer reels.
- **Subtitle Correction toggle** — turn off if you trust the transcription.
- **Models** — swap any Gemini model or the Groq checker model.
- **Prompts** — each has a sentinel token (`<<TRANSCRIPT>>`, `<<CLIP>>`, etc.). Keep the sentinel in your edited version or the stage will fail.
- **Render params** — font sizes, margins, logo position — all adjustable without redeploying.

Changes are saved to IndexedDB (persist across sessions).

---

## Part 4 — Installing as a PWA

### Android (Chrome)
1. Open the app in Chrome
2. Tap the **"App install करें"** banner at the bottom, or
3. Chrome menu → "Add to Home Screen"

### Desktop (Chrome/Edge)
- Address bar → install icon (⊕) on the right

### iOS (Safari)
- Share button → "Add to Home Screen"
- Note: iOS does not support the `beforeinstallprompt` event, so the banner won't appear. Use Share manually.

---

## Part 5 — The Render Service in detail

The render service accepts a `multipart/form-data` POST to `/render`:

| Field | Type | Description |
|---|---|---|
| `source` | file | Original audio/video file |
| `clip_srt` | file | Re-based SRT (clip starts at 00:00:00,000) |
| `title_text` | string | Hindi title for the reel |
| `clip_start` | number | Start second in original file |
| `clip_end` | number | End second in original file |
| `params` | JSON string | Render params from Config screen |
| `logo` | file (optional) | PNG logo for watermark |

The service:
1. Writes files to a temp directory
2. Builds an ASS title file (libass for correct Devanagari rendering)
3. Builds the `filter_complex` chain: crop→scale → subtitles → ASS title → logo overlay → fades
4. Runs FFmpeg, returns the MP4 binary
5. On failure, returns FFmpeg stderr tail in the JSON error

**Why libass instead of `drawtext`?** `drawtext` does not handle Devanagari script correctly — letters don't conjoin. libass does. This is non-negotiable for Hindi.

---

## Part 6 — Subtitle Correction Engine

The correction chain runs on the clip's subtitle lines only (timestamps are never touched):

1. **Learned dict** — any word corrected ≥2 times in past sessions is applied deterministically
2. **Maker (Gemini)** — proposes corrections for obvious transcription errors
3. **Checker (Groq/Llama)** — independently reviews changes; reverts any that changed meaning or altered likely proper nouns/spiritual terms
4. **Learn** — approved single-word changes increment the learned dict counter; at count ≥2 they're promoted to the dict

The learned dictionary grows in IndexedDB across sessions. Over time, repeat errors in Sarvam's output for the same channel's vocabulary will auto-correct without LLM calls.

Groq key is optional — without it, the checker step is skipped (only Maker + dict).

---

## Part 7 — Troubleshooting

### "Sarvam Proxy URL नहीं मिली"
→ You haven't saved the proxy URL in Keys menu. Make sure your Cloudflare Worker is deployed and the URL ends in `.workers.dev`.

### Transcription returns empty chunks
→ Check browser console (F12). Common causes: wrong sarvam model name (try `saaras:v2`), audio codec Sarvam can't decode (convert to mp3 first), or audio is silent.

### Render fails with FFmpeg error
→ The error shows the last 2000 chars of FFmpeg stderr in the app. Common issues:
- **Font not found**: SSH into Fly machine (`fly ssh console`) and run `fc-list | grep -i devanagari`. If empty, the fonts-noto package didn't install.
- **libass not compiled in**: Run `ffmpeg -filters | grep ass`. If not listed, your ffmpeg build lacks libass. The Dockerfile installs the Debian package which includes it.
- **Clip out of bounds**: `clip_end` > source duration. Use nudge controls to shorten the clip.

### Gemini returns wrong JSON shape
→ The app strips ` ```json ``` ` fences automatically. If parsing still fails, check the Config prompt — it must end with a JSON-only instruction and the sentinel must be present.

### PWA not installable
→ Requires HTTPS. `localhost` works for testing. Make sure `manifest.json` and `sw.js` are served at the root (`/manifest.json`, `/sw.js`). Check DevTools → Application → Manifest for errors.

---

## Part 8 — Local development (no build step needed)

The entire PWA is a single HTML file. No bundler required.

```bash
# Any static server works
npx serve public
# → http://localhost:3000

# Or Python
python3 -m http.server 3000 --directory public
# → http://localhost:3000
```

For the render service locally:
```bash
cd render-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
# → http://localhost:8080/health
```

Then in the app's Keys menu, set Render Service URL to `http://localhost:8080`.

---

## Part 9 — Security notes

- API keys are stored in IndexedDB (and localStorage as fallback) on the device. They are visible in DevTools. This is acceptable for a single trusted operator/device.
- The render service is protected by `X-Render-Token`. Do not expose it without this.
- The Sarvam proxy passes the key per-request and never stores it.
- Before giving access to anyone else: move keys and LLM calls server-side behind auth.

---

## Part 10 — What's out of scope (V1)

- YouTube auto-publishing
- Multi-channel / multi-user
- AI b-roll / image generation
- Fully offline render (ffmpeg.wasm)
- Aaharcharya pipeline

---

## Quick-start checklist

```
[ ] Sarvam API key saved
[ ] Sarvam Proxy Worker deployed + URL saved
[ ] Gemini API key saved
[ ] Groq API key saved
[ ] Render service deployed on Fly.io
[ ] Render token set (fly secrets set) + saved in app
[ ] PWA deployed on Netlify/Vercel
[ ] App opens at HTTPS URL
[ ] Test: upload a 5-min MP3, transcribe, check SRT downloads
[ ] Test: run a full Assisted pipeline on a short pravachan
[ ] (Optional) Install PWA on phone via Chrome
```

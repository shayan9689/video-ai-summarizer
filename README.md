# 🎬 NEURAFLUX — AI Video Summarizer & Highlight Generator

> Upload a raw video → get a **written summary** + an **auto-cut highlight reel**.  
> Multi-modal AI pipeline: speech, scenes, LLM reasoning, and FFmpeg rendering in one flow.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Vite_%2B_TS-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Deploy](https://img.shields.io/badge/Frontend-Vercel-000000?logo=vercel&logoColor=white)](https://vercel.com/)
[![Deploy](https://img.shields.io/badge/Backend-Render-46E3B7?logo=render&logoColor=black)](https://render.com/)

---

## ✨ What it does

| Step | Capability |
|------|------------|
| 🎧 **Audio** | Extracts clean 16 kHz mono WAV with FFmpeg |
| 🗣️ **Speech** | Transcribes with **faster-whisper** (timestamps) |
| 🧩 **Structure** | Chunks transcript + detects / windows scenes |
| 🧠 **Summary** | LLM overview, key points, notable quotes |
| ⭐ **Highlights** | Scores moments (motion · energy · salience) |
| 🎞️ **Reel** | Renders a downloadable highlight MP4 |

Built as a **portfolio Generative AI / multi-modal** project — not just chat over text, but real media processing + async jobs.

---

## 🏗️ Architecture

```
Upload (React / NEURAFLUX UI)
   │
   ▼
FastAPI job pipeline
   ├─ 1. Audio extraction (FFmpeg)
   ├─ 2. Transcription (faster-whisper)
   ├─ 3. Transcript segmentation
   ├─ 4. Scene analysis
   ├─ 5. LLM summarization (Anthropic / OpenAI)
   ├─ 6. Highlight scoring + selection
   └─ 7. Highlight reel render (FFmpeg)
   │
   ▼
Results: summary · scene timeline · downloadable reel
         (+ live progress via WebSocket / polling)
```

**Speed profile (demo-friendly):** `tiny` Whisper · light mode · clips ≤ ~2 min · target turnaround **~2–3 minutes** on a warm server.

---

## 🧰 Tech stack

| Layer | Tools |
|-------|--------|
| 🖥️ **Frontend** | React · Vite · TypeScript · Tailwind · Framer Motion · Lucide |
| ⚙️ **Backend** | Python · FastAPI · SQLAlchemy · Background pipeline |
| 🤖 **AI / ML** | faster-whisper · optional sentence-transformers · Anthropic / OpenAI |
| 🎥 **Media** | FFmpeg · OpenCV / PySceneDetect (full mode) |
| 🗄️ **Database** | Supabase Postgres (`DATABASE_URL`) · SQLite locally |
| ☁️ **Deploy** | **Vercel** (UI) · **Render** Docker (API + FFmpeg) |

---

## 📁 Repo structure

```
video-ai-summarizer/
├── backend/                 # FastAPI + processing services
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/          # Job status (SQLAlchemy)
│   │   ├── routers/         # REST + WebSocket
│   │   ├── services/        # Pipeline stages
│   │   └── utils/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # NEURAFLUX React app
├── docker-compose.yml
└── README.md
```

---

## 🚀 Local setup

### ✅ Prerequisites

- Python **3.11+**
- Node.js **20+**
- **FFmpeg** + **ffprobe** on PATH  
  - Windows: `winget install Gyan.FFmpeg`  
  - macOS: `brew install ffmpeg`  
  - Linux: `sudo apt-get install ffmpeg`

### 🔧 Backend

```bash
cd backend
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

- ❤️ Health: http://localhost:8000/health  
- 📚 Docs: http://localhost:8000/docs  

### 🎨 Frontend

```bash
cd frontend
npm install
npm run dev
```

- 🌐 App: http://localhost:5173  

### 🗄️ Database

| Environment | Setup |
|-------------|--------|
| 💻 Local | Leave `DATABASE_URL` empty → SQLite in `backend/storage/` |
| ☁️ Production | Supabase **Session pooler** URI → `DATABASE_URL` on Render |

---

## 🔐 Environment variables (important)

**Backend (`backend/.env` / Render)**

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` | Real LLM summaries (offline fallback if empty) |
| `DATABASE_URL` | Supabase pooler Postgres URI |
| `CORS_ORIGINS` | Your Vercel URL |
| `WHISPER_MODEL_SIZE` | `tiny` (recommended on Render free) |
| `LIGHT_MODE` | `true` for fast / low-RAM path |
| `MAX_VIDEO_DURATION_SECONDS` | Default `120` for demo UX |

**Frontend (Vercel)**

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE_URL` | Render API URL, e.g. `https://video-ai-summarizer.onrender.com` (no trailing slash) |

---

## ☁️ Deployment

### Backend → Render

1. New **Web Service** from this repo  
2. **Root Directory:** `backend`  
3. Runtime: **Docker** (FFmpeg included)  
4. Set env vars from the table above  
5. Health check: `https://YOUR-SERVICE.onrender.com/health` → `{"status":"ok","ffmpeg":true}`

> ⚠️ Free Render sleeps when idle — wake with `/health` before a live demo. Prefer the **Supabase pooler** URI (not direct `db.*` host).

### Frontend → Vercel

1. Import repo · **Root Directory:** `frontend`  
2. Build: `npm run build` · Output: `dist`  
3. Set `VITE_API_BASE_URL` · **Redeploy** after every env change  

---

## 🧪 Tests

```bash
cd backend
pytest -m "not slow" -q
```

---

## 🎯 Product notes for demos

- Use clips **under ~2 minutes** with clear speech  
- First job after a cold start may be slower (model warm-up)  
- UI brand: **NEURAFLUX** — synthesis dashboard with live progress  

---

## 📄 License

MIT — build on it, ship it, show it.

---

<p align="center">
  <b>Transcribe · Summarize · Highlight — end to end.</b><br/>
  Made for learning multi-modal AI systems in production shape.
</p>

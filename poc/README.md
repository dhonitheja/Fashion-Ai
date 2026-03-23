# Sahion POC — AI Fashion Stylist

Full loop: Text → Outfit Image → Virtual Try-On → Styling Tips

## Prerequisites

- Python 3.11+
- Node.js 18+
- API keys: OpenAI, Replicate, Clipdrop

## Setup

### 1. Get API Keys

| Service | URL | Cost |
|---------|-----|------|
| OpenAI | platform.openai.com | Pay per token |
| Replicate | replicate.com | ~$0.005/generation, ~$0.023/try-on |
| Clipdrop | clipdrop.co/apis | 100 free/day, then $0.002/call |

### 2. Backend

```bash
cd poc/backend
cp .env.example .env
# Edit .env and add your API keys

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
API docs at:     http://localhost:8000/docs

### 3. Frontend

```bash
cd poc/frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:3000

## How It Works

1. **Generate** — Enter a text description → AI generates outfit image via Stable Diffusion XL
2. **Try-On** — Upload your photo → background removed → outfit composited on your body via IDM-VTON
3. **Style** — Select skin tone + body type → GPT-4o gives personalized styling tips

## Cost per full user session

| Step | API | Cost |
|------|-----|------|
| Prompt enrichment | OpenAI GPT-4o-mini | ~$0.0001 |
| Outfit generation | Replicate SDXL | ~$0.005 |
| Background removal | Clipdrop | $0.002 |
| Virtual try-on | Replicate IDM-VTON | ~$0.023 |
| Styling suggestions | OpenAI GPT-4o | ~$0.012 |
| **Total** | | **~$0.042/session** |

## Project Structure

```
poc/
├── backend/
│   ├── main.py          ← FastAPI app (3 endpoints)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── App.css
    │   └── components/
    │       ├── GenerateStep.jsx   ← Step 1: text → image
    │       ├── TryOnStep.jsx      ← Step 2: photo + outfit → try-on
    │       └── StyleStep.jsx      ← Step 3: personalized styling
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## Next Steps (after POC validation)

- [ ] Migrate backend to Java Spring Boot microservices
- [ ] Add PostgreSQL for job history
- [ ] Add async job queue (SQS) — try-on takes 60-90s
- [ ] Add user auth (JWT)
- [ ] Add affiliate commerce layer
- [ ] Deploy to AWS (ECS Fargate + CloudFront)

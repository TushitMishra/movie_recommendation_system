# CineVerse Premium Frontend

Next.js + Tailwind + Framer Motion frontend designed for a premium OTT-like experience.

## 1) Start backend API

From project root:

```bash
uvicorn backend.api:app --reload --port 8000
```

## 2) Start frontend

```bash
cd frontend-next
npm install
npm run dev
```

Open `http://localhost:3000`.

## Optional env

Create `.env.local` in `frontend-next`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

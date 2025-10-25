# Mockly

Mockly is a full-stack coding-interview practice experience. The Vite/React frontend presents interview flows (landing → live editor → feedback), while the FastAPI backend powers code execution, problem distribution, structured feedback, and WebRTC signaling. This repo is a mono workspace that keeps both apps in sync.

## Architecture

- **Frontend (`mockly-frontend`)** – Vite + React + TypeScript UI with Tailwind and Zustand state. Calls `src/services/api.ts` for `/api/*` endpoints, manages the Monaco-like editor, and renders problems, execution results, and feedback.
- **Backend (`mockly-backend`)** – FastAPI service exposing:
  - `POST /api/execute` to compile/run snippets in a sandbox.
  - `POST /api/questions` to fetch prompts (with embedded examples) backed by `questions.yaml`.
  - `GET /api/feedback` for canned structured feedback.
  - `POST /api/webrtc/offer`, `POST /api/webrtc/candidate`, `DELETE /api/webrtc/session/:id` for lightweight WebRTC signaling.
- **Shared data** – `questions.yaml` stores multi-difficulty prompts consumed at startup by the backend.
- **Local proxying** – The Vite dev server proxies `/api` to `localhost:8000`, so browser calls reach FastAPI without manual CORS fiddling.

```
frontend (Vite dev server) --/api--> FastAPI -- sandbox runner/per diff YAML
```

## Repository layout

```
mockly/
├── mockly-frontend/       # React client
├── mockly-backend/        # FastAPI app + sandbox runner
├── questions.yaml         # Source of truth for prompts
├── environment.yml        # Optional Python env descriptor
└── README.md              # You are here
```

## Quick start

### Requirements
- Node 20+
- Python 3.11+
- (optional) Poetry for backend dependency management

### Backend
```bash
cd mockly-backend
poetry install         # or pip install -r <generated>
poetry run uvicorn app.main:app --reload
```
This exposes FastAPI on `http://localhost:8000`.

### Frontend
```bash
cd mockly-frontend
npm install            # or pnpm/yarn
npm run dev
```
The Vite dev server runs on `http://localhost:5173` and proxies `/api` to the backend.

## API surface (summary)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/execute` | POST | Compile/run code with language, source, stdin, timeout. |
| `/api/questions` | POST | Retrieve a random prompt for a given difficulty, including example IO. |
| `/api/feedback` | GET | Fetch static structured interview feedback. |
| `/api/webrtc/offer` | POST | Create a signaling session (placeholder echo implementation). |
| `/api/webrtc/candidate` | POST | Push ICE candidates into the session store. |
| `/api/webrtc/session/{id}` | DELETE | Close an in-memory signaling session. |

## Development workflow
1. Start the FastAPI server (`uvicorn app.main:app --reload`).
2. Start `npm run dev` in `mockly-frontend`.
3. The frontend issues relative `/api` requests which Vite forwards to FastAPI. Watch backend logs for request traces while verifying UI behavior.

See the per-app READMEs for deeper stack/command details.

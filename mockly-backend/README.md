# Mockly Backend

The backend is a FastAPI application that powers Mockly’s coding interview experience. It exposes endpoints for code execution, question retrieval, canned feedback, and lightweight WebRTC signaling.

## Stack
- **Framework**: FastAPI + Pydantic v1
- **Runtime**: Python 3.11
- **Process manager**: Uvicorn (see `app/main.py`)
- **Execution sandbox**: `app/sandbox.py` wraps `subprocess.run` (optionally behind Firejail) to compile/run user code safely.
- **Data**: `questions.yaml` (root-level) loaded once at startup.

## Project layout
```
mockly-backend/
├── app/
│   ├── main.py                 # FastAPI app + middleware + router registration
│   ├── models.py               # Pydantic schemas for requests/responses
│   ├── sandbox.py              # Helper to run code with limits
│   └── routes/
│       ├── routes_execute.py   # /api/execute logic
│       ├── routes_questions.py # /api/questions logic (loads YAML, injects examples)
│       ├── routes_feedback.py  # /api/feedback static payload
│       └── routes_webrtc.py    # /api/webrtc/* endpoints (in-memory signaling)
├── pyproject.toml / poetry.lock
└── questions.yaml              # Difficulty-tagged prompts
```

## Setup
```bash
cd mockly-backend
poetry install                   # installs FastAPI, uvicorn, pyyaml, aiortc
poetry run uvicorn app.main:app --reload
```
Environment variables:
- `HOST` / `PORT` – override default `0.0.0.0:8000` when using the `python app/main.py` entry point.
- `UVICORN_RELOAD=1` – enable reload when running via `python app/main.py` (uses the embedded `uvicorn.run`).
- `USE_FIREJAIL=1` – wrap sandboxed executions with Firejail if available on your system.

## API reference
### `POST /api/execute`
Run arbitrary snippets.
```json
{
  "language": "python",
  "source": "print('Hello')",
  "stdin": "optional stdin",
  "timeoutMs": 4000
}
```
Returns stdout/stderr/exitCode/timeMs. Supports `python`, `javascript`, `typescript`, `java`, and `cpp` with per-language compile/run steps handled in `routes_execute.py`.

### `POST /api/questions`
Body: `{ "difficulty": "easy" }`. Picks a random problem from `questions.yaml`, appends formatted example IO to the statement, and returns:
```json
{
  "id": "easy-abc12345",
  "difficulty": "easy",
  "prompt": "...statement...\n\nExamples:\n- ...",
  "starter_code": null,
  "language": null
}
```
(Hooks exist for `starter_code`/`language` if the YAML provides them.)

### `GET /api/feedback`
Returns static feedback metrics and narrative text used by the frontend’s post-interview screen.

### `/api/webrtc/*`
Placeholder signaling store backed by in-memory dicts (`routes_webrtc.py`). Replace this with a real media server/aiortc integration for production use.

## Development tips
- Run backend first (`uvicorn app.main:app --reload`) before starting the frontend. Vite proxies `/api` to `localhost:8000`.
- Questions are cached on import; restart the server if you edit `questions.yaml`.
- The sandbox respects `timeoutMs` provided by the client but caps compile steps to 8s to prevent runaways.

See the root README for the broader architecture picture and the frontend README for UI details.

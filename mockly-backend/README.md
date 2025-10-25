# Mockly Backend

The backend is a FastAPI application that powers Mockly’s coding interview experience. It now focuses on question retrieval, canned feedback, lightweight WebRTC signaling, and the multi-language code runner consumed by the frontend “Run” button.

## Stack
- **Framework**: FastAPI + Pydantic v1
- **Runtime**: Python 3.11
- **Process manager**: Uvicorn (see `app/main.py`)
- **Code runner deps**: Python 3.11 runtime plus Node 20 + `ts-node`, `g++`, and the JDK (see setup).
- **Data**: `questions.yaml` (root-level) loaded once at startup.

## Project layout
```
mockly-backend/
├── app/
│   ├── main.py                 # FastAPI app + middleware + router registration
│   ├── models.py               # Pydantic schemas for requests/responses
│   └── routes/
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

To enable `/api/execute` locally you also need:
- `node` + `npm`
- `npm install -g ts-node typescript`
- `g++` (build-essential on Debian/Ubuntu, Xcode CLT on macOS)
- `javac` (OpenJDK or similar)

**Easiest option:** run the backend inside the prebuilt image that already bundles these toolchains:
```bash
docker compose up --build backend
```

Environment variables:
- `HOST` / `PORT` – override default `0.0.0.0:8000` when using the `python app/main.py` entry point.
- `UVICORN_RELOAD=1` – enable reload when running via `python app/main.py` (uses the embedded `uvicorn.run`).

## API reference
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

### `POST /api/execute`
Body:
```json
{
  "language": "python",
  "source": "print('hi')",
  "stdin": "",
  "timeoutMs": 5000
}
```
Supported languages: `python`, `javascript`, `typescript`, `cpp`, `java`. Each request is written to a temp workspace under `/app/.runner`, executed with the appropriate runtime/compiler, and returns:
```json
{
  "stdout": "hi\n",
  "stderr": "",
  "exitCode": 0,
  "timeMs": 37
}
```
If the required toolchain is missing the handler returns an error message and `exitCode: 1`.

### `/api/webrtc/*`
Placeholder signaling store backed by in-memory dicts (`routes_webrtc.py`). Replace this with a real media server/aiortc integration for production use.

## Development tips
- Run backend first (`uvicorn app.main:app --reload`) before starting the frontend. Vite proxies `/api` to `localhost:8000`.
- Questions are cached on import; restart the server if you edit `questions.yaml`.

See the root README for the broader architecture picture and the frontend README for UI details.

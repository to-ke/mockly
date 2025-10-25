# Mockly Frontend

The Mockly frontend is a Vite + React + TypeScript single-page app that guides candidates through a mock interview: difficulty selection → live coding (Monaco-like editor) → feedback. It consumes `/api/*` endpoints exposed by the FastAPI backend and handles state via Zustand.

## Stack
- **Build tooling**: Vite, TypeScript, SWC React plugin
- **UI**: React 18, Tailwind (utility classes live under `src/styles`), custom components in `src/components`
- **State**: Zustand stores (`src/stores/app.ts`, `src/stores/session.ts`)
- **API client**: `src/services/api.ts` centralizes fetch logic for execute/questions/feedback/WebRTC

## Key flows
1. **Landing (`src/components/Landing.tsx`)** – lets the user pick a difficulty and fetches a prompt via `Api.fetchQuestion`.
2. **Editor pane (`src/components/EditorPane.tsx`)** – renders the language selector + code editor, backed by `useSession` for boilerplate per language.
3. **Execution** – `Api.execute` posts code to `/api/execute` and streams stdout/stderr back into the store.
4. **Feedback** – Once an interview is completed, the UI calls `Api.fetchFeedback` and shows the structured report.
5. **WebRTC signaling** – `Api.createWebRtcSession` / `sendWebRtcCandidate` wire up the remote IDE stream (placeholder backend currently echoes data).

## Development
```bash
npm install         # install deps
npm run dev         # start Vite on http://localhost:5173
```
The dev server proxies `/api` to `http://localhost:8000` (see `vite.config.ts`) so the browser talks to FastAPI without extra configuration.

### Scripts
- `npm run dev` – Vite dev server with HMR and proxying
- `npm run build` – production build (outputs to `dist/`)
- `npm run preview` – preview the production build locally
- `npm run lint` – run ESLint against the codebase

## Environment
Create `mockly-frontend/.env.local` to override defaults exposed via `import.meta.env`, such as `VITE_USE_MOCK`. When `VITE_USE_MOCK=true`, the app short-circuits API calls with local mock data to unblock UI work.

## Project structure (frontend)
```
mockly-frontend/
├── src/
│   ├── components/        # UI building blocks (Landing, EditorPane, Header, etc.)
│   ├── services/api.ts    # Fetch helpers (execute/questions/feedback/WebRTC)
│   ├── stores/            # Zustand stores for app+session state
│   ├── types/             # Shared TypeScript types (api.ts, etc.)
│   └── main.tsx           # App bootstrap
├── public/                # Static assets served by Vite
├── vite.config.ts         # Dev server + alias configuration
└── README.md              # This file
```

Pair this frontend with the backend described in `../mockly-backend/README.md`.

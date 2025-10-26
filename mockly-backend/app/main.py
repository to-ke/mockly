import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is importable before pulling in app.routes.* modules.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.routes.routes_questions import router as questions_router
from app.routes.routes_feedback import router as feedback_router
from app.routes.routes_webrtc import router as webrtc_router
from app.routes.routes_execute import router as execute_router
from app.routes.routes_audio import router as audio_router
from app.services.workflow import router as workflow_router

# Try to import the optional standalone workflow app. In some runtime
# environments (e.g., the Docker image) the top-level `workflow`
# package may not be present. We import inside a try/except and only
# mount the sub-app if the import succeeded.
try:
    import workflow.api as workflow_api
    workflow_import_error = None
except Exception as _e:  # pragma: no cover - runtime diagnostic
    workflow_api = None
    workflow_import_error = str(_e)


app = FastAPI(title="Mockly", version="0.1.0")


# Allow local dev frontends; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(questions_router)
app.include_router(feedback_router)
app.include_router(webrtc_router)
app.include_router(execute_router)
app.include_router(audio_router)
app.include_router(workflow_router)

# Mount the standalone workflow FastAPI app under /assistant so its
# endpoints (claude streaming, TTS helpers, etc.) are reachable from
# the running server. This mirrors the workflow module's previous
# standalone usage but exposes it under the main app.
if workflow_api is not None and getattr(workflow_api, "app", None) is not None:
    app.mount("/assistant", workflow_api.app)
else:
    # Provide a lightweight fallback endpoint under /assistant/debug/claude/stream
    # which uses the internal ChatbotAgent. This avoids relying on the
    # optional top-level `workflow` package being present in the image.
    from fastapi import Body, Response
    from app.services.chatbot.agent import ChatbotAgent
    from app.services.chatbot.prompts import load_question_by_difficulty

    agent = ChatbotAgent()

    @app.post("/assistant/debug/claude/stream")
    async def assistant_debug_claude_stream(payload: dict = Body(...)):
        text = (payload.get("text") or "").strip()
        if not text:
            return Response(content="", media_type="text/plain; charset=utf-8")

        # Prefer an explicit question payload from the client, otherwise allow
        # a difficulty hint to load a consistent question from questions.yaml.
        question = payload.get("question")
        if not question and payload.get("difficulty"):
            try:
                question = load_question_by_difficulty(str(payload.get("difficulty")))
            except Exception:
                question = None

        try:
            # Use the agent to get a full (non-streaming) reply for the frontend.
            reply = agent.get_text(text, question=question)
            return Response(content=reply, media_type="text/plain; charset=utf-8")
        except Exception as e:
            return Response(content=f"Error: {e}", media_type="text/plain; charset=utf-8", status_code=500)


@app.get("/assistant/_info")
def assistant_info():
    """Diagnostic endpoint to confirm the mounted workflow app and list its routes.

    This helps debug 404s by returning whether the workflow module was
    imported correctly and which paths it exposes.
    """
    try:
        subapp = getattr(workflow_api, "app", None)
        if subapp is None:
            return {"mounted": False, "reason": "workflow.api.app not found"}
        routes = []
        for r in getattr(subapp, "routes", []):
            try:
                routes.append({"path": getattr(r, "path", str(r)), "name": getattr(r, "name", None)})
            except Exception:
                routes.append({"repr": repr(r)})
        return {"mounted": True, "routes_count": len(routes), "routes": routes}
    except Exception as e:
        return {"mounted": False, "error": str(e)}


@app.get("/_assistant_info")
def assistant_info_root():
    """Root-level diagnostic that lists the mounted workflow app routes.

    This endpoint deliberately avoids the /assistant mount prefix so it
    is handled by the main app and not forwarded to the sub-application.
    """
    try:
        subapp = getattr(workflow_api, "app", None)
        if subapp is None:
            return {"mounted": False, "reason": "workflow.api.app not found"}
        routes = []
        for r in getattr(subapp, "routes", []):
            try:
                methods = []
                if hasattr(r, "methods") and r.methods:
                    methods = sorted(list(r.methods))
                routes.append({
                    "path": getattr(r, "path", None) or str(r),
                    "name": getattr(r, "name", None),
                    "methods": methods,
                })
            except Exception:
                routes.append({"repr": repr(r)})
        return {"mounted": True, "routes_count": len(routes), "routes": routes}
    except Exception as e:
        return {"mounted": False, "error": str(e)}


@app.get("/")
def root():
    return {"ok": True, "service": "Mockly"}


if __name__ == "__main__":
    import uvicorn

    # Allow overriding host/port/reload via env for local dev.
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("UVICORN_RELOAD", "0") == "1",
    )

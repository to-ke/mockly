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

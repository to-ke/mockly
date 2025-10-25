from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes_execute import router as execute_router
from .routes_questions import router as questions_router
from .routes_feedback import router as feedback_router
from .routes_webrtc import router as webrtc_router


app = FastAPI(title="Mockly", version="0.1.0")


# Allow local dev frontends; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(execute_router)
app.include_router(questions_router)
app.include_router(feedback_router)
app.include_router(webrtc_router)


@app.get("/")
def root():
    return {"ok": True, "service": "Mockly"}
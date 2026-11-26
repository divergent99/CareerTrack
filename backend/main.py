from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
import threading
from routers import chat, stats, company, applications, roadmap, resume, github
from services.mcp_client import get_schema_text

app = FastAPI()


@app.on_event("startup")
def warm_chat_schema():
    # Build the chat agent's schema context in the background so the first
    # real question after a deploy doesn't pay for introspection.
    def _warm():
        try:
            get_schema_text()
        except Exception:
            logging.getLogger(__name__).exception("Schema warm-up failed")
    threading.Thread(target=_warm, daemon=True).start()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(stats.router)
app.include_router(company.router)
app.include_router(applications.router)
app.include_router(roadmap.router)
app.include_router(resume.router)
app.include_router(github.router)



from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, stats, company, applications, roadmap, resume, github
app = FastAPI()

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



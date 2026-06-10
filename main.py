import os
from dotenv import load_dotenv
load_dotenv()
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database.db import init_db
from api.upload import router as upload_router
from api.analyze import router as analyze_router
from api.report import router as report_router
from api.agent import router as agent_router
from api.chat import router as chat_router
from api.risk import router as risk_router
from api.recommendations import router as recommendations_router
from api.planning import router as planning_router
from api.orchestration import router as orchestration_router

# Ensure directory paths exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE_DIR, "uploads"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "reports"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the sqlite database schemas on startup
    await init_db()
    yield
    # Cleanup logic (if any) can go here

app = FastAPI(
    title="InfraGuard - Infrastructure Inventory Reconciliation System",
    description="Deterministic rule-based asset and configuration reconciliation system (AI-free).",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(upload_router)
app.include_router(analyze_router)
app.include_router(report_router)
app.include_router(agent_router)
app.include_router(chat_router)
app.include_router(risk_router)
app.include_router(recommendations_router)
app.include_router(planning_router)
app.include_router(orchestration_router)

# Mount the static files directory to serve CSS and JS
# But we can also check if static files folder has items
static_dir = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_root():
    """
    Serves the dashboard single page application index.html.
    """
    index_path = os.path.join(BASE_DIR, "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "InfraGuard Backend API is online.",
        "frontend_status": "Index.html not found. Please verify the static directory setup."
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

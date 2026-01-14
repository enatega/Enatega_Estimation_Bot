from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api.endpoints import router
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API for generating time and cost estimates for client onboarding systems",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix=settings.API_V1_PREFIX)

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    # Serve static files (CSS, JS)
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    @app.get("/")
    async def serve_frontend():
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend not found. API is running at /docs"}
    
    # Serve individual frontend files
    @app.get("/styles.css")
    async def serve_css():
        file_path = os.path.join(frontend_path, "styles.css")
        if os.path.exists(file_path):
            from fastapi.responses import Response
            with open(file_path, 'r') as f:
                return Response(content=f.read(), media_type="text/css")
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    
    @app.get("/app.js")
    async def serve_js():
        file_path = os.path.join(frontend_path, "app.js")
        if os.path.exists(file_path):
            from fastapi.responses import Response
            with open(file_path, 'r') as f:
                return Response(content=f.read(), media_type="application/javascript")
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
else:
    @app.get("/")
    async def root():
        """Root endpoint - API only"""
        return {
            "message": "Estimation Bot API",
            "version": settings.VERSION,
            "docs": "/docs",
            "health": f"{settings.API_V1_PREFIX}/health"
        }

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup - load once, use everywhere"""
    logger.info("Starting Estimation Bot API...")
    logger.info(f"API Version: {settings.VERSION}")
    logger.info(f"OpenAI Model: {settings.OPENAI_MODEL}")
    
    # Pre-load knowledge base ONCE at startup (singleton)
    try:
        from app.services.knowledge_base import KnowledgeBase
        from app.services.openai_service import OpenAIService
        import app.api.endpoints as endpoints_module
        
        # Initialize global singletons in endpoints module
        endpoints_module._knowledge_base = KnowledgeBase(settings.DATA_DIR)
        logger.info("Knowledge base loaded successfully")
        
        # Initialize OpenAI service
        endpoints_module._openai_service = OpenAIService(endpoints_module._knowledge_base)
        logger.info("Services initialized and cached - ready for fast queries")
    except Exception as e:
        logger.error(f"Error loading knowledge base: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

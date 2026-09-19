from fastapi import FastAPI
from src.config.settings import settings
from src.router.main import router


def create_app() -> FastAPI:
    app =FastAPI(

        title=settings.title,
        description=settings.description,
        docs_url="/docs" if settings.debug else None ,
        redoc_url="/redoc" if settings.debug else None
    )

    app.include_router(router,prefix="/api/v1")

    @app.get("/health",tags=["Health check"])
    async def health_check():
        return {"status":"ok","version":settings.version}

        
       
    return app
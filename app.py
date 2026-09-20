import uvicorn

from src.config.settings import settings
from src.main import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

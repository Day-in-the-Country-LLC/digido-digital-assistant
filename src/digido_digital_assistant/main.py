from fastapi import FastAPI

from digido_digital_assistant.config import settings
from digido_digital_assistant.routes import router

app = FastAPI(title="Digido Digital Assistant", version="0.1.0")
app.include_router(router)


def run() -> None:
    import uvicorn

    uvicorn.run(
        "digido_digital_assistant.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.digido_env == "development",
    )


if __name__ == "__main__":
    run()

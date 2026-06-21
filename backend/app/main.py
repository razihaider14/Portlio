from fastapi import FastAPI

from app.config import settings

app = FastAPI(title = settings.APP_NAME)

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME
    }

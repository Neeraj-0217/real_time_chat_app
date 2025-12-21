from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import auth, chat
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# Mount Static Files
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

# Include Routers
app.include_router(auth.router)
app.include_router(chat.router)

@app.get("/")
async def root():
    return {"message": "Server is running. Go to /login"}
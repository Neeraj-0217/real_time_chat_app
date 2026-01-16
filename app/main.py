from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import auth, chat, users
from app.db.base import Base
from app.db.session import engine

# Base.metadata.drop_all(bind=engine)
# Base.metadata.create_all(bind=engine)

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
app.include_router(users.router)

@app.get("/")
async def root():
    return {"message": "Server is running. Go to /login"}

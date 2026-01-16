from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create SQLAlchemy engine using database URL from config
engine = create_engine(settings.DATABASE_URL)

# Session factory for database interactions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Dependency used in FastAPI routes
# Ensures session is properly closed after request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

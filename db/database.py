from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///test_flightlog.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Session = SessionLocal

Base = declarative_base()

def get_session():
    return SessionLocal()

# This must come *after* Base is defined
from db.models import Base  # Ensure this is not above Base or it will error

def init_db():
    Base.metadata.create_all(bind=engine)




"""
Database configuration and models
Task 2.4: Set up database (PostgreSQL)
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./voiquyr.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Task 2.2: Core data models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    region = Column(String, default="EU-Frankfurt")

class SIPTrunk(Base):
    __tablename__ = "sip_trunks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    uri = Column(String, nullable=False)
    username = Column(String)
    password = Column(String)
    region = Column(String, default="EU-Frankfurt")
    status = Column(String, default="active")
    created_at = Column(DateTime, default=func.now())

class Call(Base):
    __tablename__ = "calls"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    sip_trunk_id = Column(Integer)
    call_id = Column(String, unique=True, nullable=False)
    from_number = Column(String, nullable=False)
    to_number = Column(String, nullable=False)
    status = Column(String, default="initiated")
    duration = Column(Integer, default=0)  # seconds
    cost = Column(Float, default=0.0)
    started_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime)
    transcript = Column(Text)

async def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
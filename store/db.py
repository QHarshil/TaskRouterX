"""
Database connection and session management.

This module provides database initialization and session management using SQLite.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

from store.models import Base, WorkerPool, RegionType, ResourceType

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./taskrouterx.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize the database schema and seed initial data.
    
    Creates all tables and populates worker pools if they don't exist.
    """
    Base.metadata.create_all(bind=engine)
    
    # Seed worker pools if they don't exist
    db = SessionLocal()
    try:
        if db.query(WorkerPool).count() == 0:
            worker_pools = [
                WorkerPool(
                    name="us-east-cpu-pool",
                    region=RegionType.US_EAST,
                    resource_type=ResourceType.CPU,
                    cost_per_unit=0.5,
                    capacity=10,
                    current_load=0
                ),
                WorkerPool(
                    name="us-east-gpu-pool",
                    region=RegionType.US_EAST,
                    resource_type=ResourceType.GPU,
                    cost_per_unit=2.0,
                    capacity=5,
                    current_load=0
                ),
                WorkerPool(
                    name="us-west-cpu-pool",
                    region=RegionType.US_WEST,
                    resource_type=ResourceType.CPU,
                    cost_per_unit=0.6,
                    capacity=8,
                    current_load=0
                ),
                WorkerPool(
                    name="us-west-gpu-pool",
                    region=RegionType.US_WEST,
                    resource_type=ResourceType.GPU,
                    cost_per_unit=2.2,
                    capacity=4,
                    current_load=0
                ),
                WorkerPool(
                    name="eu-west-cpu-pool",
                    region=RegionType.EU_WEST,
                    resource_type=ResourceType.CPU,
                    cost_per_unit=0.55,
                    capacity=10,
                    current_load=0
                ),
                WorkerPool(
                    name="eu-west-gpu-pool",
                    region=RegionType.EU_WEST,
                    resource_type=ResourceType.GPU,
                    cost_per_unit=2.1,
                    capacity=5,
                    current_load=0
                ),
                WorkerPool(
                    name="ap-east-cpu-pool",
                    region=RegionType.AP_EAST,
                    resource_type=ResourceType.CPU,
                    cost_per_unit=0.65,
                    capacity=6,
                    current_load=0
                ),
                WorkerPool(
                    name="ap-east-gpu-pool",
                    region=RegionType.AP_EAST,
                    resource_type=ResourceType.GPU,
                    cost_per_unit=2.3,
                    capacity=3,
                    current_load=0
                ),
            ]
            db.add_all(worker_pools)
            db.commit()
    finally:
        db.close()


def get_db():
    """
    Dependency function to get database session.
    
    Yields:
        Session: SQLAlchemy database session
        
    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    
    Yields:
        Session: SQLAlchemy database session
        
    Usage:
        with get_db_context() as db:
            items = db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


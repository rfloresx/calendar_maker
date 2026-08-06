"""SQLAlchemy database models and session management."""

import json
import uuid
import datetime
from typing import Optional, List

from sqlalchemy import create_engine, Column, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

from lib.web.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """Create and return a new database session."""
    return SessionLocal()


def generate_id() -> str:
    """Generate a new UUID string for use as primary key."""
    return str(uuid.uuid4())


# --- Models ---

class Project(Base):
    __tablename__ = "projects"

    id = Column(Text, primary_key=True, default=generate_id)
    name = Column(Text, nullable=False)
    year = Column(Integer, nullable=False)
    project_type = Column(Text, nullable=False, default="wall")  # 'wall', 'desk', 'photos'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    wall_pages = relationship("WallPage", back_populates="project", cascade="all, delete-orphan")
    desk_pages = relationship("DeskPage", back_populates="project", cascade="all, delete-orphan")
    birthdays = relationship("Birthday", back_populates="project", cascade="all, delete-orphan")
    photo_labels = relationship("PhotoLabel", back_populates="project", cascade="all, delete-orphan")
    export_settings = relationship("ExportSettings", back_populates="project", uselist=False, cascade="all, delete-orphan")


class WallPage(Base):
    __tablename__ = "wall_pages"
    __table_args__ = (UniqueConstraint("project_id", "page_index"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    page_index = Column(Integer, nullable=False)
    image_path = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    place_data = Column(Text, nullable=True)  # JSON string

    project = relationship("Project", back_populates="wall_pages")

    @property
    def place_dict(self) -> dict:
        if self.place_data:
            try:
                return json.loads(self.place_data)
            except (json.JSONDecodeError, TypeError):
                pass
        return {}

    @place_dict.setter
    def place_dict(self, value: dict):
        self.place_data = json.dumps(value) if value else None


class DeskPage(Base):
    __tablename__ = "desk_pages"
    __table_args__ = (UniqueConstraint("project_id", "page_index"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    page_index = Column(Integer, nullable=False)
    image_path = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    place_data = Column(Text, nullable=True)

    project = relationship("Project", back_populates="desk_pages")

    @property
    def place_dict(self) -> dict:
        if self.place_data:
            try:
                return json.loads(self.place_data)
            except (json.JSONDecodeError, TypeError):
                pass
        return {}

    @place_dict.setter
    def place_dict(self, value: dict):
        self.place_data = json.dumps(value) if value else None


class Birthday(Base):
    __tablename__ = "birthdays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=True)
    date = Column(Text, nullable=True)  # DD/MM/YYYY
    image_path = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)

    project = relationship("Project", back_populates="birthdays")


class PhotoLabel(Base):
    __tablename__ = "photo_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(Text, nullable=True)
    template = Column(Text, nullable=True)
    place_data = Column(Text, nullable=True)  # JSON
    sort_order = Column(Integer, default=0)

    project = relationship("Project", back_populates="photo_labels")

    @property
    def place_dict(self) -> dict:
        if self.place_data:
            try:
                return json.loads(self.place_data)
            except (json.JSONDecodeError, TypeError):
                pass
        return {}

    @place_dict.setter
    def place_dict(self, value: dict):
        self.place_data = json.dumps(value) if value else None


class ExportSettings(Base):
    __tablename__ = "export_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    calendar_type = Column(Text, default="wall")
    format = Column(Text, default="png")
    exporter_name = Column(Text, default="default")
    options = Column(Text, default="{}")  # JSON

    project = relationship("Project", back_populates="export_settings")

    @property
    def options_dict(self) -> dict:
        if self.options:
            try:
                return json.loads(self.options)
            except (json.JSONDecodeError, TypeError):
                pass
        return {}

    @options_dict.setter
    def options_dict(self, value: dict):
        self.options = json.dumps(value) if value else "{}"


class AppConfig(Base):
    __tablename__ = "app_config"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False, default="")
    description = Column(Text, nullable=True)


# --- Database initialization ---

def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(engine)


# --- Helper functions ---

def get_or_create_export_settings(db: Session, project_id: str) -> ExportSettings:
    """Get or create export settings for a project."""
    settings = db.query(ExportSettings).filter_by(project_id=project_id).first()
    if not settings:
        settings = ExportSettings(project_id=project_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def get_config(db: Session, key: str, default: str = "") -> str:
    """Get a configuration value from the database."""
    import os
    # Environment variable takes priority
    env_val = os.environ.get(key, "")
    if env_val:
        return env_val
    config = db.query(AppConfig).filter_by(key=key).first()
    return config.value if config else default


def set_config(db: Session, key: str, value: str, description: str = ""):
    """Set a configuration value in the database."""
    config = db.query(AppConfig).filter_by(key=key).first()
    if config:
        config.value = value
        if description:
            config.description = description
    else:
        config = AppConfig(key=key, value=value, description=description)
        db.add(config)
    db.commit()

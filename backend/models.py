"""
MCServerPanel - Database Models
"""
import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    path = Column(String(500), nullable=False, unique=True)
    server_jar = Column(String(200), nullable=False)
    server_type = Column(String(50), default="vanilla")  # vanilla, forge, fabric, paper, spigot
    minecraft_version = Column(String(20), default="")
    loader_version = Column(String(50), default="")
    min_ram = Column(String(10), default="1G")
    max_ram = Column(String(10), default="4G")
    jvm_args = Column(Text, default="")
    port = Column(Integer, default=25565)
    auto_start = Column(Boolean, default=False)
    auto_restart = Column(Boolean, default=False)
    status = Column(String(20), default="stopped")  # stopped, starting, running, stopping
    pid = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    java_path = Column(String(500), default="java")
    icon = Column(String(100), default="default")

    backups = relationship("Backup", back_populates="server", cascade="all, delete-orphan")
    installed_mods = relationship("InstalledMod", back_populates="server", cascade="all, delete-orphan")
    modpack = relationship("InstalledModpack", back_populates="server", uselist=False, cascade="all, delete-orphan")


class Backup(Base):
    __tablename__ = "backups"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    name = Column(String(200), nullable=False)
    path = Column(String(500), nullable=False)
    size_mb = Column(Float, default=0.0)
    backup_type = Column(String(50), default="full")  # full, mods, config, world
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    server = relationship("Server", back_populates="backups")


class InstalledMod(Base):
    __tablename__ = "installed_mods"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    mod_name = Column(String(200), nullable=False)
    mod_slug = Column(String(200), default="")
    mod_id = Column(String(100), default="")  # Modrinth/CurseForge ID
    source = Column(String(50), default="modrinth")  # modrinth, curseforge, manual
    version_id = Column(String(100), default="")
    version_name = Column(String(100), default="")
    file_name = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)
    minecraft_version = Column(String(20), default="")
    loader = Column(String(50), default="")
    installed_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    server = relationship("Server", back_populates="installed_mods")


class InstalledModpack(Base):
    __tablename__ = "installed_modpacks"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False, unique=True)
    modpack_name = Column(String(200), nullable=False)
    modpack_slug = Column(String(200), default="")
    modpack_id = Column(String(100), default="")
    source = Column(String(50), default="modrinth")
    version_id = Column(String(100), default="")
    version_name = Column(String(100), default="")
    minecraft_version = Column(String(20), default="")
    loader = Column(String(50), default="")
    installed_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    server = relationship("Server", back_populates="modpack")


class JavaInstallation(Base):
    __tablename__ = "java_installations"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String(500), nullable=False, unique=True)
    version = Column(String(50), default="")
    vendor = Column(String(100), default="")
    is_64bit = Column(Boolean, default=True)
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)

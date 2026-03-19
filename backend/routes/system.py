"""
MCServerPanel - Backup & System API Routes
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.backup_manager import BackupManager
from backend.services.system_monitor import SystemMonitor

router = APIRouter(prefix="/api", tags=["system"])


class BackupCreate(BaseModel):
    backup_type: str = "full"
    name: str = ""


@router.get("/system/stats")
def get_system_stats():
    return SystemMonitor.get_system_stats()


@router.get("/system/network")
async def get_system_network():
    return await SystemMonitor.get_network_info()


@router.post("/backups/{server_id}")
def create_backup(server_id: int, data: BackupCreate, db: Session = Depends(get_db)):
    return BackupManager.create_backup(db, server_id, data.backup_type, data.name)


@router.get("/backups/{server_id}")
def list_backups(server_id: int, db: Session = Depends(get_db)):
    return BackupManager.list_backups(db, server_id)


@router.post("/backups/{server_id}/restore/{backup_id}")
def restore_backup(server_id: int, backup_id: int, db: Session = Depends(get_db)):
    return BackupManager.restore_backup(db, server_id, backup_id)


@router.delete("/backups/{backup_id}")
def delete_backup(backup_id: int, db: Session = Depends(get_db)):
    return BackupManager.delete_backup(db, backup_id)

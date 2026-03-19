"""
MCServerPanel - Backup Manager Service
Handles creating, restoring, and managing backups.
"""
import datetime
import shutil
import zipfile
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Server, Backup


class BackupManager:
    """Create and restore server backups."""

    @staticmethod
    def create_backup(
        db: Session,
        server_id: int,
        backup_type: str = "full",
        name: str = "",
    ) -> dict:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"success": False, "error": "Server not found"}

        server_path = Path(server.path)
        if not server_path.exists():
            return {"success": False, "error": "Server path does not exist"}

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if not name:
            name = f"{server.name}_{backup_type}_{timestamp}"

        backup_dir = settings.BACKUPS_DIR / str(server_id)
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / f"{name}.zip"

        # Determine what to back up
        if backup_type == "full":
            source_dir = server_path
        elif backup_type == "world":
            source_dir = server_path / "world"
            if not source_dir.exists():
                return {"success": False, "error": "No world folder found"}
        elif backup_type == "mods":
            source_dir = server_path / "mods"
            if not source_dir.exists():
                return {"success": False, "error": "No mods folder found"}
        elif backup_type == "config":
            source_dir = server_path / "config"
            if not source_dir.exists():
                return {"success": False, "error": "No config folder found"}
        else:
            source_dir = server_path

        # Create zip
        try:
            with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        arc_name = file_path.relative_to(source_dir.parent if backup_type != "full" else source_dir)
                        zf.write(file_path, arc_name)
        except Exception as e:
            return {"success": False, "error": f"Failed to create backup: {e}"}

        size_mb = backup_file.stat().st_size / (1024 * 1024)

        backup_record = Backup(
            server_id=server_id,
            name=name,
            path=str(backup_file),
            size_mb=round(size_mb, 2),
            backup_type=backup_type,
        )
        db.add(backup_record)
        db.commit()
        db.refresh(backup_record)

        return {
            "success": True,
            "backup_id": backup_record.id,
            "name": name,
            "size_mb": round(size_mb, 2),
            "path": str(backup_file),
        }

    @staticmethod
    def restore_backup(db: Session, server_id: int, backup_id: int) -> dict:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"success": False, "error": "Server not found"}

        backup = db.query(Backup).filter(Backup.id == backup_id, Backup.server_id == server_id).first()
        if not backup:
            return {"success": False, "error": "Backup not found"}

        backup_path = Path(backup.path)
        if not backup_path.exists():
            return {"success": False, "error": "Backup file not found on disk"}

        server_path = Path(server.path)

        try:
            # For full backups, clear server dir first (except backups reference)
            if backup.backup_type == "full":
                for item in server_path.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

            with zipfile.ZipFile(backup_path, "r") as zf:
                if backup.backup_type == "full":
                    zf.extractall(server_path)
                else:
                    zf.extractall(server_path)

            return {"success": True, "message": f"Restored backup: {backup.name}"}
        except Exception as e:
            return {"success": False, "error": f"Restore failed: {e}"}

    @staticmethod
    def list_backups(db: Session, server_id: int) -> list[dict]:
        backups = db.query(Backup).filter(Backup.server_id == server_id).order_by(Backup.created_at.desc()).all()
        return [
            {
                "id": b.id,
                "name": b.name,
                "size_mb": b.size_mb,
                "backup_type": b.backup_type,
                "created_at": b.created_at.isoformat() if b.created_at else "",
            }
            for b in backups
        ]

    @staticmethod
    def delete_backup(db: Session, backup_id: int) -> dict:
        backup = db.query(Backup).filter(Backup.id == backup_id).first()
        if not backup:
            return {"success": False, "error": "Backup not found"}
        backup_path = Path(backup.path)
        if backup_path.exists():
            backup_path.unlink()
        db.delete(backup)
        db.commit()
        return {"success": True}

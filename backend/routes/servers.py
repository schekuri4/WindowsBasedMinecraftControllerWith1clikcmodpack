"""
MCServerPanel - Server API Routes
"""
from pathlib import Path, PurePosixPath
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse as FastAPIFileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.server_manager import ServerManager
from backend.services.java_manager import JavaManager

router = APIRouter(prefix="/api/servers", tags=["servers"])


# --- Schemas ---
class ServerCreate(BaseModel):
    name: str
    server_type: str = "vanilla"
    minecraft_version: str = "1.20.4"
    min_ram: str = "1G"
    max_ram: str = "4G"
    port: int = 25565
    java_path: str = "java"


class ServerImport(BaseModel):
    name: str
    path: str


class ServerUpdate(BaseModel):
    name: str | None = None
    min_ram: str | None = None
    max_ram: str | None = None
    jvm_args: str | None = None
    port: int | None = None
    java_path: str | None = None
    auto_start: bool | None = None
    auto_restart: bool | None = None
    server_jar: str | None = None


class ServerCommand(BaseModel):
    command: str


# --- Endpoints ---
@router.get("")
def list_servers(db: Session = Depends(get_db)):
    servers = ServerManager.list_servers(db)
    return [
        {
            "id": s.id,
            "name": s.name,
            "path": s.path,
            "server_type": s.server_type,
            "minecraft_version": s.minecraft_version,
            "status": s.status,
            "port": s.port,
            "min_ram": s.min_ram,
            "max_ram": s.max_ram,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in servers
    ]


@router.get("/versions")
async def get_versions():
    return await ServerManager.get_available_versions()


@router.get("/java")
def get_java_installations():
    return JavaManager.find_java_installations()


@router.post("")
async def create_server(data: ServerCreate, db: Session = Depends(get_db)):
    server = ServerManager.create_server(
        db,
        name=data.name,
        server_type=data.server_type,
        minecraft_version=data.minecraft_version,
        min_ram=data.min_ram,
        max_ram=data.max_ram,
        port=data.port,
        java_path=data.java_path,
    )
    # Download server jar
    try:
        if data.server_type == "vanilla":
            await ServerManager.download_vanilla_jar(data.minecraft_version, server.path)
        elif data.server_type == "forge":
            jar = await ServerManager.download_forge_installer(data.minecraft_version, server.path)
            server.server_jar = jar
            db.commit()
        elif data.server_type == "neoforge":
            jar = await ServerManager.download_neoforge_installer(data.minecraft_version, server.path)
            server.server_jar = jar
            db.commit()
        elif data.server_type == "fabric":
            jar = await ServerManager.download_fabric_server(data.minecraft_version, server.path)
            server.server_jar = jar
            db.commit()
        elif data.server_type == "quilt":
            jar = await ServerManager.download_quilt_server(data.minecraft_version, server.path)
            server.server_jar = jar
            db.commit()
        elif data.server_type == "paper":
            await ServerManager.download_paper_jar(data.minecraft_version, server.path)
        elif data.server_type == "purpur":
            await ServerManager.download_purpur_jar(data.minecraft_version, server.path)
        elif data.server_type == "pufferfish":
            await ServerManager.download_pufferfish_jar(data.minecraft_version, server.path)
        elif data.server_type == "spigot":
            await ServerManager.download_spigot_buildtools(data.minecraft_version, server.path)
        elif data.server_type == "bukkit":
            await ServerManager.download_bukkit_buildtools(data.minecraft_version, server.path)
        elif data.server_type == "glowstone":
            await ServerManager.download_glowstone_jar(data.minecraft_version, server.path)
        elif data.server_type == "sponge":
            await ServerManager.download_sponge_jar(data.minecraft_version, server.path)
        elif data.server_type == "mohist":
            await ServerManager.download_mohist_jar(data.minecraft_version, server.path)
        elif data.server_type == "arclight":
            await ServerManager.download_arclight_jar(data.minecraft_version, server.path)
        elif data.server_type == "magma":
            await ServerManager.download_magma_jar(data.minecraft_version, server.path)
        elif data.server_type == "banner":
            await ServerManager.download_banner_jar(data.minecraft_version, server.path)
        elif data.server_type == "cardboard":
            await ServerManager.download_cardboard_jar(data.minecraft_version, server.path)
        elif data.server_type == "liteloader":
            await ServerManager.download_liteloader_jar(data.minecraft_version, server.path)
        elif data.server_type == "rift":
            await ServerManager.download_rift_jar(data.minecraft_version, server.path)
    except Exception as e:
        return {"server_id": server.id, "warning": f"Server created but jar download failed: {e}"}

    return {"server_id": server.id, "name": server.name, "path": server.path}


@router.post("/import")
def import_server(data: ServerImport, db: Session = Depends(get_db)):
    try:
        server = ServerManager.import_server(db, data.name, data.path)
        return {
            "server_id": server.id,
            "name": server.name,
            "server_type": server.server_type,
            "minecraft_version": server.minecraft_version,
            "server_jar": server.server_jar,
        }
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{server_id}")
def get_server(server_id: int, db: Session = Depends(get_db)):
    server = ServerManager.get_server(db, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return {
        "id": server.id,
        "name": server.name,
        "path": server.path,
        "server_jar": server.server_jar,
        "server_type": server.server_type,
        "minecraft_version": server.minecraft_version,
        "loader_version": server.loader_version,
        "min_ram": server.min_ram,
        "max_ram": server.max_ram,
        "jvm_args": server.jvm_args,
        "port": server.port,
        "auto_start": server.auto_start,
        "auto_restart": server.auto_restart,
        "status": server.status,
        "java_path": server.java_path,
        "created_at": server.created_at.isoformat() if server.created_at else "",
    }


@router.put("/{server_id}")
def update_server(server_id: int, data: ServerUpdate, db: Session = Depends(get_db)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    server = ServerManager.update_server(db, server_id, **updates)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"success": True}


@router.delete("/{server_id}")
def delete_server(server_id: int, delete_files: bool = False, db: Session = Depends(get_db)):
    result = ServerManager.delete_server(db, server_id, delete_files)
    if not result:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"success": True}


@router.post("/{server_id}/start")
def start_server(server_id: int, db: Session = Depends(get_db)):
    return ServerManager.start_server(db, server_id)


@router.post("/{server_id}/stop")
def stop_server(server_id: int, db: Session = Depends(get_db)):
    return ServerManager.stop_server(db, server_id)


@router.post("/{server_id}/command")
def send_command(server_id: int, data: ServerCommand, db: Session = Depends(get_db)):
    return ServerManager.send_command(server_id, data.command)


@router.get("/{server_id}/console")
def get_console(server_id: int, lines: int = 100):
    return {"lines": ServerManager.get_console(server_id, lines)}


@router.get("/{server_id}/status")
def get_server_status(server_id: int, db: Session = Depends(get_db)):
    return ServerManager.get_server_status(db, server_id)


# --- File Manager ---

def _resolve_server_path(db: Session, server_id: int, sub_path: str = "") -> tuple:
    """Resolve and validate a path inside the server directory. Returns (server, resolved_path)."""
    server = ServerManager.get_server(db, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    server_root = Path(server.path).resolve()
    # Normalise using PurePosixPath to handle forward-slash subpaths from the frontend
    clean = PurePosixPath(sub_path).as_posix() if sub_path else ""
    target = (server_root / clean).resolve()
    # Prevent path traversal
    if not str(target).startswith(str(server_root)):
        raise HTTPException(status_code=400, detail="Invalid path")
    return server, target


@router.get("/{server_id}/files")
def list_files(server_id: int, path: str = "", db: Session = Depends(get_db)):
    """List files and directories inside the server folder."""
    _, target = _resolve_server_path(db, server_id, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Not a directory")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            try:
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size if entry.is_file() else 0,
                    "modified": stat.st_mtime,
                })
            except (PermissionError, OSError):
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    return {"path": path or "", "items": items}


@router.get("/{server_id}/files/download")
def download_file(server_id: int, path: str, db: Session = Depends(get_db)):
    """Download a single file from the server directory."""
    _, target = _resolve_server_path(db, server_id, path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FastAPIFileResponse(str(target), filename=target.name)


@router.post("/{server_id}/files/upload")
async def upload_files(
    server_id: int,
    path: str = Form(""),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload one or more files. Paths in filenames (e.g. sub/dir/file.txt) create directories."""
    _, base = _resolve_server_path(db, server_id, path)
    base.mkdir(parents=True, exist_ok=True)

    results = []
    for f in files:
        # Support relative paths in filename for folder uploads
        clean_name = PurePosixPath(f.filename).as_posix() if f.filename else "unnamed"
        # Prevent traversal in uploaded filenames
        if ".." in clean_name.split("/"):
            results.append({"name": f.filename, "error": "Invalid path"})
            continue
        dest = (base / clean_name).resolve()
        if not str(dest).startswith(str(base.resolve())):
            results.append({"name": f.filename, "error": "Invalid path"})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = await f.read()
        dest.write_bytes(content)
        results.append({"name": clean_name, "size": len(content)})
    return {"success": True, "uploaded": results}


@router.post("/{server_id}/files/mkdir")
def create_directory(server_id: int, path: str = "", name: str = "", db: Session = Depends(get_db)):
    """Create a new directory inside the server folder."""
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    _, base = _resolve_server_path(db, server_id, path)
    new_dir = (base / name).resolve()
    if not str(new_dir).startswith(str(base.resolve().parent)):
        raise HTTPException(status_code=400, detail="Invalid path")
    new_dir.mkdir(parents=True, exist_ok=True)
    return {"success": True}


@router.delete("/{server_id}/files")
def delete_path(server_id: int, path: str, db: Session = Depends(get_db)):
    """Delete a file or directory from the server folder."""
    _, target = _resolve_server_path(db, server_id, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    server_root = Path(ServerManager.get_server(db, server_id).path).resolve()
    if target == server_root:
        raise HTTPException(status_code=400, detail="Cannot delete server root")
    import shutil
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"success": True}

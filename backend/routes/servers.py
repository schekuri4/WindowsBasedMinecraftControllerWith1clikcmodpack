"""
MCServerPanel - Server API Routes
"""
from fastapi import APIRouter, Depends, HTTPException
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

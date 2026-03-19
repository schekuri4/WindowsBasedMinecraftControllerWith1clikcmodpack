"""
MCServerPanel - Mod API Routes
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.mod_installer import ModInstaller

router = APIRouter(prefix="/api/mods", tags=["mods"])


class ModInstallRequest(BaseModel):
    source: str
    project_id: str
    version_id: str


class BatchModInstallRequest(BaseModel):
    mods: list[ModInstallRequest]


@router.get("/search/modrinth")
async def search_mods_modrinth(
    query: str = "",
    mc_version: str = "",
    loader: str = "",
    category: str = "",
    offset: int = 0,
    limit: int = 20,
):
    return await ModInstaller.search_mods_modrinth(query, mc_version, loader, category, offset, limit)


@router.get("/search/curseforge")
async def search_mods_curseforge(
    query: str = "",
    mc_version: str = "",
    category_id: int = 0,
    offset: int = 0,
    limit: int = 20,
):
    return await ModInstaller.search_mods_curseforge(query, mc_version, category_id, offset, limit)


@router.get("/detail/modrinth/{project_id}")
async def get_mod_detail(project_id: str):
    return await ModInstaller.get_mod_detail_modrinth(project_id)


@router.get("/versions/modrinth/{project_id}")
async def get_mod_versions(
    project_id: str,
    mc_version: str = "",
    loader: str = "",
):
    return await ModInstaller.get_mod_versions_modrinth(project_id, mc_version, loader)


@router.get("/categories/modrinth")
async def get_categories():
    return await ModInstaller.get_modrinth_categories()


@router.get("/installed/{server_id}")
def list_installed(server_id: int, db: Session = Depends(get_db)):
    return ModInstaller.list_installed_mods(db, server_id)


@router.get("/files/{server_id}")
def list_mod_files(server_id: int, db: Session = Depends(get_db)):
    """List actual mod jar files on disk for this server."""
    return ModInstaller.list_mod_files_on_disk(db, server_id)


@router.post("/install/{server_id}")
async def install_mod(
    server_id: int,
    data: ModInstallRequest,
    db: Session = Depends(get_db),
):
    return await ModInstaller.install_mod(db, server_id, data.source, data.project_id, data.version_id)


@router.post("/install-batch/{server_id}")
async def batch_install(
    server_id: int,
    data: BatchModInstallRequest,
    db: Session = Depends(get_db),
):
    mods = [m.model_dump() for m in data.mods]
    return await ModInstaller.batch_install_mods(db, server_id, mods)


@router.delete("/file/{server_id}/{file_name}")
def delete_mod_file(server_id: int, file_name: str, db: Session = Depends(get_db)):
    """Delete a mod file from disk by filename."""
    return ModInstaller.delete_mod_file_from_disk(db, server_id, file_name)


@router.delete("/uninstall/{server_id}/{mod_id}")
def uninstall_mod(server_id: int, mod_id: int, db: Session = Depends(get_db)):
    return ModInstaller.uninstall_mod(db, server_id, mod_id)


@router.get("/updates/{server_id}")
async def check_updates(server_id: int, db: Session = Depends(get_db)):
    return await ModInstaller.check_mod_updates(db, server_id)

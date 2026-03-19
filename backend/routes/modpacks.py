"""
MCServerPanel - Modpack API Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.modpack_installer import ModpackInstaller

router = APIRouter(prefix="/api/modpacks", tags=["modpacks"])


class ModpackInstallRequest(BaseModel):
    source: str  # modrinth or curseforge
    project_id: str
    version_id: str


class ExportRequest(BaseModel):
    name: str


class ImportRequest(BaseModel):
    path: str


@router.get("/search/modrinth")
async def search_modpacks_modrinth(
    query: str = "",
    mc_version: str = "",
    loader: str = "",
    offset: int = 0,
    limit: int = 20,
):
    return await ModpackInstaller.search_modpacks_modrinth(query, mc_version, loader, offset, limit)


@router.get("/search/curseforge")
async def search_modpacks_curseforge(
    query: str = "",
    mc_version: str = "",
    offset: int = 0,
    limit: int = 20,
):
    return await ModpackInstaller.search_modpacks_curseforge(query, mc_version, offset, limit)


@router.get("/detail/modrinth/{project_id}")
async def get_modpack_detail(project_id: str):
    return await ModpackInstaller.get_modpack_detail_modrinth(project_id)


@router.get("/versions/modrinth/{project_id}")
async def get_modpack_versions(
    project_id: str,
    mc_version: str = "",
    loader: str = "",
):
    return await ModpackInstaller.get_modpack_versions_modrinth(project_id, mc_version, loader)


@router.get("/versions/curseforge/{project_id}")
async def get_modpack_versions_curseforge(
    project_id: str,
    mc_version: str = "",
):
    return await ModpackInstaller.get_modpack_versions_curseforge(project_id, mc_version)


@router.post("/install/{server_id}")
async def install_modpack(
    server_id: int,
    data: ModpackInstallRequest,
    db: Session = Depends(get_db),
):
    return await ModpackInstaller.install_modpack(
        db, server_id, data.source, data.project_id, data.version_id
    )


@router.get("/update-check/{server_id}")
async def check_modpack_update(server_id: int, db: Session = Depends(get_db)):
    return await ModpackInstaller.check_modpack_update(db, server_id)


@router.post("/export/{server_id}")
async def export_setup(server_id: int, data: ExportRequest, db: Session = Depends(get_db)):
    return await ModpackInstaller.export_modpack_setup(db, server_id, data.name)


@router.post("/import/{server_id}")
async def import_setup(server_id: int, data: ImportRequest, db: Session = Depends(get_db)):
    return await ModpackInstaller.import_modpack_setup(db, server_id, data.path)

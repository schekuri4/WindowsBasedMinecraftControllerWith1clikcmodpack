"""
MCServerPanel - Plugin API Routes
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.plugin_installer import PluginInstaller

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


class PluginInstallRequest(BaseModel):
    source: str
    project_id: str
    version_id: str


@router.get("/search/modrinth")
async def search_plugins_modrinth(
    query: str = "",
    mc_version: str = "",
    loader: str = "",
    offset: int = 0,
    limit: int = 20,
):
    return await PluginInstaller.search_plugins_modrinth(query, mc_version, loader, offset, limit)


@router.get("/search/hangar")
async def search_plugins_hangar(
    query: str = "",
    mc_version: str = "",
    loader: str = "",
    offset: int = 0,
    limit: int = 20,
):
    return await PluginInstaller.search_plugins_hangar(query, mc_version, loader, offset, limit)


@router.get("/search/spiget")
async def search_plugins_spiget(
    query: str = "",
    mc_version: str = "",
    loader: str = "",
    offset: int = 0,
    limit: int = 20,
):
    return await PluginInstaller.search_plugins_spiget(query, mc_version, loader, offset, limit)


@router.get("/versions/modrinth/{project_id}")
async def get_plugin_versions(project_id: str, mc_version: str = "", loader: str = ""):
    return await PluginInstaller.get_plugin_versions_modrinth(project_id, mc_version, loader)


@router.get("/versions/hangar/{project_id}")
async def get_hangar_plugin_versions(project_id: str, mc_version: str = "", loader: str = ""):
    return await PluginInstaller.get_plugin_versions_hangar(project_id, mc_version, loader)


@router.get("/versions/spiget/{project_id}")
async def get_spiget_plugin_versions(project_id: str, mc_version: str = "", loader: str = ""):
    return await PluginInstaller.get_plugin_versions_spiget(project_id, mc_version, loader)


@router.post("/install/{server_id}")
async def install_plugin(server_id: int, data: PluginInstallRequest, db: Session = Depends(get_db)):
    return await PluginInstaller.install_plugin(db, server_id, data.source, data.project_id, data.version_id)

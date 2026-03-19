"""
MCServerPanel - Mod Installer Service
Handles browsing, downloading, and installing individual mods.
"""
import json
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Server, InstalledMod


class ModInstaller:
    """Browse and install individual mods from Modrinth/CurseForge."""

    # -------------------------------------------------------------------
    # Search Mods
    # -------------------------------------------------------------------
    @staticmethod
    async def search_mods_modrinth(
        query: str = "",
        mc_version: str = "",
        loader: str = "",
        category: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        """Search Modrinth for mods."""
        facets = [["project_type:mod"]]
        if mc_version:
            facets.append([f"versions:{mc_version}"])
        if loader:
            facets.append([f"categories:{loader}"])
        if category:
            facets.append([f"categories:{category}"])
        facets.append(["server_side:required", "server_side:optional"])

        params = {
            "query": query,
            "facets": json.dumps(facets),
            "limit": limit,
            "offset": offset,
            "index": "relevance",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{settings.MODRINTH_API_URL}/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            return {
                "total": data.get("total_hits", 0),
                "results": [
                    {
                        "id": p["project_id"],
                        "slug": p.get("slug", ""),
                        "name": p["title"],
                        "description": p.get("description", ""),
                        "author": p.get("author", ""),
                        "downloads": p.get("downloads", 0),
                        "icon_url": p.get("icon_url", ""),
                        "categories": p.get("categories", []),
                        "source": "modrinth",
                    }
                    for p in data.get("hits", [])
                ],
            }

    @staticmethod
    async def search_mods_curseforge(
        query: str = "",
        mc_version: str = "",
        category_id: int = 0,
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        """Search CurseForge for mods."""
        if not settings.CURSEFORGE_API_KEY:
            return {"total": 0, "results": [], "error": "CurseForge API key not configured"}

        params = {
            "gameId": settings.MINECRAFT_GAME_ID,
            "classId": 6,  # Mods
            "searchFilter": query,
            "pageSize": limit,
            "index": offset,
            "sortField": 2,
            "sortOrder": "desc",
        }
        if mc_version:
            params["gameVersion"] = mc_version
        if category_id:
            params["categoryId"] = category_id

        headers = {"x-api-key": settings.CURSEFORGE_API_KEY}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.CURSEFORGE_API_URL}/mods/search",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "total": data.get("pagination", {}).get("totalCount", 0),
                "results": [
                    {
                        "id": str(m["id"]),
                        "slug": m.get("slug", ""),
                        "name": m["name"],
                        "description": m.get("summary", ""),
                        "author": m.get("authors", [{}])[0].get("name", "") if m.get("authors") else "",
                        "downloads": m.get("downloadCount", 0),
                        "icon_url": m.get("logo", {}).get("thumbnailUrl", "") if m.get("logo") else "",
                        "categories": [c["name"] for c in m.get("categories", [])],
                        "source": "curseforge",
                    }
                    for m in data.get("data", [])
                ],
            }

    # -------------------------------------------------------------------
    # Get Mod Versions / Details
    # -------------------------------------------------------------------
    @staticmethod
    async def get_mod_versions_modrinth(project_id: str, mc_version: str = "", loader: str = "") -> list[dict]:
        params = {}
        if mc_version:
            params["game_versions"] = json.dumps([mc_version])
        if loader:
            params["loaders"] = json.dumps([loader])

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.MODRINTH_API_URL}/project/{project_id}/version",
                params=params,
            )
            resp.raise_for_status()
            return [
                {
                    "id": v["id"],
                    "name": v.get("name", v["version_number"]),
                    "version_number": v["version_number"],
                    "game_versions": v.get("game_versions", []),
                    "loaders": v.get("loaders", []),
                    "date_published": v.get("date_published", ""),
                    "dependencies": v.get("dependencies", []),
                    "files": [
                        {
                            "url": f["url"],
                            "filename": f["filename"],
                            "size": f.get("size", 0),
                            "primary": f.get("primary", False),
                        }
                        for f in v.get("files", [])
                    ],
                }
                for v in resp.json()
            ]

    @staticmethod
    async def get_mod_detail_modrinth(project_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{settings.MODRINTH_API_URL}/project/{project_id}")
            resp.raise_for_status()
            p = resp.json()
            return {
                "id": p["id"],
                "slug": p.get("slug", ""),
                "name": p["title"],
                "description": p.get("description", ""),
                "body": p.get("body", ""),
                "downloads": p.get("downloads", 0),
                "icon_url": p.get("icon_url", ""),
                "categories": p.get("categories", []),
                "game_versions": p.get("game_versions", []),
                "loaders": p.get("loaders", []),
                "license": p.get("license", {}).get("id", ""),
                "source": "modrinth",
            }

    # -------------------------------------------------------------------
    # Install Mod
    # -------------------------------------------------------------------
    @staticmethod
    async def install_mod(
        db: Session,
        server_id: int,
        source: str,
        project_id: str,
        version_id: str,
    ) -> dict:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"success": False, "error": "Server not found"}

        server_path = Path(server.path)
        mods_dir = server_path / "mods"
        mods_dir.mkdir(exist_ok=True)

        if source == "modrinth":
            return await ModInstaller._install_mod_modrinth(
                db, server, mods_dir, project_id, version_id
            )
        elif source == "curseforge":
            return await ModInstaller._install_mod_curseforge(
                db, server, mods_dir, project_id, version_id
            )
        return {"success": False, "error": f"Unknown source: {source}"}

    @staticmethod
    async def _install_mod_modrinth(
        db: Session,
        server: Server,
        mods_dir: Path,
        project_id: str,
        version_id: str,
    ) -> dict:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            # Get version info
            resp = await client.get(f"{settings.MODRINTH_API_URL}/version/{version_id}")
            resp.raise_for_status()
            version_data = resp.json()

            # Compatibility check
            game_versions = version_data.get("game_versions", [])
            loaders = version_data.get("loaders", [])
            if server.minecraft_version and game_versions and server.minecraft_version not in game_versions:
                return {
                    "success": False,
                    "error": f"Mod version incompatible with MC {server.minecraft_version}. "
                             f"Supports: {', '.join(game_versions[:5])}",
                }
            if server.server_type and loaders and server.server_type not in loaders:
                # Allow if "fabric" or "forge" is in loaders
                if not any(l in loaders for l in [server.server_type, "datapack"]):
                    return {
                        "success": False,
                        "error": f"Mod incompatible with {server.server_type}. Supports: {', '.join(loaders)}",
                    }

            # Find primary file
            primary_file = None
            for f in version_data.get("files", []):
                if f.get("primary", False):
                    primary_file = f
                    break
            if not primary_file and version_data.get("files"):
                primary_file = version_data["files"][0]
            if not primary_file:
                return {"success": False, "error": "No file available"}

            # Download
            file_path = mods_dir / primary_file["filename"]
            resp = await client.get(primary_file["url"])
            resp.raise_for_status()
            file_path.write_bytes(resp.content)

            # Install dependencies
            deps_installed = []
            for dep in version_data.get("dependencies", []):
                if dep.get("dependency_type") == "required":
                    dep_project_id = dep.get("project_id")
                    dep_version_id = dep.get("version_id")
                    if dep_project_id and not dep_version_id:
                        # Find compatible version
                        dep_versions = await ModInstaller.get_mod_versions_modrinth(
                            dep_project_id, server.minecraft_version, server.server_type
                        )
                        if dep_versions:
                            dep_version_id = dep_versions[0]["id"]
                    if dep_version_id:
                        dep_result = await ModInstaller._install_mod_modrinth(
                            db, server, mods_dir, dep_project_id, dep_version_id
                        )
                        if dep_result.get("success"):
                            deps_installed.append(dep_result.get("mod_name", ""))

            # Get project info for name
            proj_resp = await client.get(f"{settings.MODRINTH_API_URL}/project/{project_id}")
            proj_data = proj_resp.json() if proj_resp.status_code == 200 else {}
            mod_name = proj_data.get("title", primary_file["filename"])

            # Save to DB
            existing = (
                db.query(InstalledMod)
                .filter(InstalledMod.server_id == server.id, InstalledMod.mod_id == project_id)
                .first()
            )
            if existing:
                # Remove old file
                old_path = Path(existing.file_path)
                if old_path.exists():
                    old_path.unlink()
                existing.version_id = version_id
                existing.version_name = version_data.get("name", version_data.get("version_number", ""))
                existing.file_name = primary_file["filename"]
                existing.file_path = str(file_path)
                existing.minecraft_version = server.minecraft_version
                existing.loader = server.server_type
            else:
                db.add(InstalledMod(
                    server_id=server.id,
                    mod_name=mod_name,
                    mod_slug=proj_data.get("slug", ""),
                    mod_id=project_id,
                    source="modrinth",
                    version_id=version_id,
                    version_name=version_data.get("name", version_data.get("version_number", "")),
                    file_name=primary_file["filename"],
                    file_path=str(file_path),
                    minecraft_version=server.minecraft_version,
                    loader=server.server_type,
                ))
            db.commit()

            return {
                "success": True,
                "mod_name": mod_name,
                "file_name": primary_file["filename"],
                "dependencies_installed": deps_installed,
            }

    @staticmethod
    async def _install_mod_curseforge(
        db: Session,
        server: Server,
        mods_dir: Path,
        project_id: str,
        version_id: str,
    ) -> dict:
        if not settings.CURSEFORGE_API_KEY:
            return {"success": False, "error": "CurseForge API key not configured"}

        headers = {"x-api-key": settings.CURSEFORGE_API_KEY}
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            # Get file info
            resp = await client.get(
                f"{settings.CURSEFORGE_API_URL}/mods/{project_id}/files/{version_id}",
                headers=headers,
            )
            resp.raise_for_status()
            file_data = resp.json()["data"]

            download_url = file_data.get("downloadUrl")
            if not download_url:
                return {"success": False, "error": "Download URL not available"}

            # Download
            file_path = mods_dir / file_data["fileName"]
            resp = await client.get(download_url)
            resp.raise_for_status()
            file_path.write_bytes(resp.content)

            # Get mod info
            mod_resp = await client.get(
                f"{settings.CURSEFORGE_API_URL}/mods/{project_id}",
                headers=headers,
            )
            mod_data = mod_resp.json()["data"] if mod_resp.status_code == 200 else {}
            mod_name = mod_data.get("name", file_data["fileName"])

            # Download dependencies
            deps_installed = []
            for dep in file_data.get("dependencies", []):
                if dep.get("relationType") == 3:  # Required dependency
                    dep_id = str(dep["modId"])
                    # Get latest file for the dependency
                    dep_files_resp = await client.get(
                        f"{settings.CURSEFORGE_API_URL}/mods/{dep_id}/files",
                        headers=headers,
                        params={"gameVersion": server.minecraft_version} if server.minecraft_version else {},
                    )
                    if dep_files_resp.status_code == 200:
                        dep_files = dep_files_resp.json().get("data", [])
                        if dep_files:
                            dep_result = await ModInstaller._install_mod_curseforge(
                                db, server, mods_dir, dep_id, str(dep_files[0]["id"])
                            )
                            if dep_result.get("success"):
                                deps_installed.append(dep_result.get("mod_name", ""))

            # Save to DB
            existing = (
                db.query(InstalledMod)
                .filter(InstalledMod.server_id == server.id, InstalledMod.mod_id == project_id)
                .first()
            )
            if existing:
                old_path = Path(existing.file_path)
                if old_path.exists():
                    old_path.unlink()
                existing.version_id = version_id
                existing.file_name = file_data["fileName"]
                existing.file_path = str(file_path)
            else:
                db.add(InstalledMod(
                    server_id=server.id,
                    mod_name=mod_name,
                    mod_slug=mod_data.get("slug", ""),
                    mod_id=project_id,
                    source="curseforge",
                    version_id=version_id,
                    file_name=file_data["fileName"],
                    file_path=str(file_path),
                    minecraft_version=server.minecraft_version,
                    loader=server.server_type,
                ))
            db.commit()

            return {
                "success": True,
                "mod_name": mod_name,
                "file_name": file_data["fileName"],
                "dependencies_installed": deps_installed,
            }

    # -------------------------------------------------------------------
    # Batch install / uninstall / update
    # -------------------------------------------------------------------
    @staticmethod
    async def batch_install_mods(
        db: Session,
        server_id: int,
        mods: list[dict],
    ) -> list[dict]:
        """Install multiple mods at once. Each entry: {source, project_id, version_id}."""
        results = []
        for mod in mods:
            result = await ModInstaller.install_mod(
                db, server_id, mod["source"], mod["project_id"], mod["version_id"]
            )
            results.append(result)
        return results

    @staticmethod
    def uninstall_mod(db: Session, server_id: int, mod_db_id: int) -> dict:
        mod = db.query(InstalledMod).filter(
            InstalledMod.id == mod_db_id, InstalledMod.server_id == server_id
        ).first()
        if not mod:
            return {"success": False, "error": "Mod not found"}
        file_path = Path(mod.file_path)
        if file_path.exists():
            file_path.unlink()
        db.delete(mod)
        db.commit()
        return {"success": True, "mod_name": mod.mod_name}

    @staticmethod
    async def check_mod_updates(db: Session, server_id: int) -> list[dict]:
        """Check all installed mods for updates."""
        mods = db.query(InstalledMod).filter(InstalledMod.server_id == server_id).all()
        updates = []
        for mod in mods:
            if mod.source == "modrinth" and mod.mod_id:
                try:
                    versions = await ModInstaller.get_mod_versions_modrinth(
                        mod.mod_id, mod.minecraft_version, mod.loader
                    )
                    if versions and versions[0]["id"] != mod.version_id:
                        updates.append({
                            "mod_name": mod.mod_name,
                            "mod_db_id": mod.id,
                            "current_version": mod.version_name,
                            "latest_version": versions[0]["name"],
                            "latest_version_id": versions[0]["id"],
                            "source": mod.source,
                            "project_id": mod.mod_id,
                        })
                except Exception:
                    pass
        return updates

    @staticmethod
    def list_installed_mods(db: Session, server_id: int) -> list[dict]:
        mods = db.query(InstalledMod).filter(InstalledMod.server_id == server_id).all()
        return [
            {
                "id": m.id,
                "mod_name": m.mod_name,
                "mod_slug": m.mod_slug,
                "mod_id": m.mod_id,
                "source": m.source,
                "version_name": m.version_name,
                "file_name": m.file_name,
                "installed_at": m.installed_at.isoformat() if m.installed_at else "",
            }
            for m in mods
        ]

    @staticmethod
    def list_mod_files_on_disk(db: Session, server_id: int) -> list[dict]:
        """List jar/zip files in the server's mods/ folder."""
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return []
        mods_dir = Path(server.path) / "mods"
        if not mods_dir.exists():
            return []

        # Get DB-tracked file names for cross-reference
        tracked = {
            m.file_name
            for m in db.query(InstalledMod).filter(InstalledMod.server_id == server_id).all()
        }

        files = []
        for f in sorted(mods_dir.iterdir()):
            if f.suffix.lower() in (".jar", ".zip") and f.is_file():
                size_kb = f.stat().st_size / 1024
                files.append({
                    "file_name": f.name,
                    "size_kb": round(size_kb, 1),
                    "tracked": f.name in tracked,
                })
        return files

    @staticmethod
    def delete_mod_file_from_disk(db: Session, server_id: int, file_name: str) -> dict:
        """Delete a mod file from the server's mods/ folder."""
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"success": False, "error": "Server not found"}
        # Sanitize: prevent path traversal
        safe_name = Path(file_name).name
        if safe_name != file_name or ".." in file_name:
            return {"success": False, "error": "Invalid file name"}
        mod_path = Path(server.path) / "mods" / safe_name
        if not mod_path.exists():
            return {"success": False, "error": "File not found"}
        mod_path.unlink()
        return {"success": True, "message": f"Deleted {safe_name}"}

    @staticmethod
    async def get_modrinth_categories() -> list[dict]:
        """Get available mod categories from Modrinth."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{settings.MODRINTH_API_URL}/tag/category")
            resp.raise_for_status()
            return [
                {"name": c["name"], "icon": c.get("icon", ""), "project_type": c.get("project_type", "")}
                for c in resp.json()
                if c.get("project_type") == "mod"
            ]

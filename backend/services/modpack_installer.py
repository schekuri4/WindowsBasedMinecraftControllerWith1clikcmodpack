"""
MCServerPanel - Modpack Installer Service
Handles browsing, downloading, and installing modpacks from Modrinth and CurseForge.
"""
import asyncio
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Server, InstalledModpack
from backend.services.server_manager import ServerManager


class ModpackInstaller:
    """Browse and install modpacks from Modrinth/CurseForge."""

    # -------------------------------------------------------------------
    # Modrinth API
    # -------------------------------------------------------------------
    @staticmethod
    async def search_modpacks_modrinth(
        query: str = "",
        mc_version: str = "",
        loader: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        """Search Modrinth for modpacks."""
        params = {
            "query": query,
            "facets": ModpackInstaller._build_modrinth_facets("modpack", mc_version, loader),
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
                        "versions": p.get("versions", []),
                        "source": "modrinth",
                    }
                    for p in data.get("hits", [])
                ],
            }

    @staticmethod
    async def get_modpack_versions_modrinth(project_id: str, mc_version: str = "", loader: str = "") -> list[dict]:
        """Get available versions for a Modrinth modpack."""
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
            versions = resp.json()
            return [
                {
                    "id": v["id"],
                    "name": v.get("name", v["version_number"]),
                    "version_number": v["version_number"],
                    "game_versions": v.get("game_versions", []),
                    "loaders": v.get("loaders", []),
                    "date_published": v.get("date_published", ""),
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
                for v in versions
            ]

    @staticmethod
    async def get_modpack_detail_modrinth(project_id: str) -> dict:
        """Get detailed info about a Modrinth modpack."""
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
                "author": p.get("team", ""),
                "downloads": p.get("downloads", 0),
                "icon_url": p.get("icon_url", ""),
                "categories": p.get("categories", []),
                "game_versions": p.get("game_versions", []),
                "loaders": p.get("loaders", []),
                "source": "modrinth",
            }

    # -------------------------------------------------------------------
    # CurseForge API
    # -------------------------------------------------------------------
    @staticmethod
    async def search_modpacks_curseforge(
        query: str = "",
        mc_version: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        """Search CurseForge for modpacks."""
        if not settings.CURSEFORGE_API_KEY:
            return {"total": 0, "results": [], "error": "CurseForge API key not configured"}

        params = {
            "gameId": settings.MINECRAFT_GAME_ID,
            "classId": 4471,  # Modpacks
            "searchFilter": query,
            "pageSize": limit,
            "index": offset,
            "sortField": 2,  # Popularity
            "sortOrder": "desc",
        }
        if mc_version:
            params["gameVersion"] = mc_version

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

    @staticmethod
    async def get_modpack_versions_curseforge(project_id: str, mc_version: str = "") -> list[dict]:
        """Get available files/versions for a CurseForge modpack."""
        if not settings.CURSEFORGE_API_KEY:
            return []

        params = {
            "pageSize": 50,
            "index": 0,
            "sortField": 1,  # File date
            "sortOrder": "desc",
        }
        if mc_version:
            params["gameVersion"] = mc_version

        headers = {"x-api-key": settings.CURSEFORGE_API_KEY}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.CURSEFORGE_API_URL}/mods/{project_id}/files",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

            versions = []
            for f in data.get("data", []):
                file_versions = f.get("sortableGameVersions", [])
                game_versions = [
                    v.get("gameVersionName", "")
                    for v in file_versions
                    if v.get("gameVersionName")
                ]
                game_versions = list(dict.fromkeys(game_versions))

                loaders = []
                for v in file_versions:
                    name = (v.get("gameVersionName") or "").lower()
                    if "forge" in name:
                        loaders.append("forge")
                    if "fabric" in name:
                        loaders.append("fabric")
                    if "quilt" in name:
                        loaders.append("quilt")
                    if "neoforge" in name:
                        loaders.append("neoforge")
                loaders = list(dict.fromkeys(loaders))

                versions.append(
                    {
                        "id": str(f["id"]),
                        "name": f.get("displayName", f.get("fileName", str(f["id"]))),
                        "version_number": f.get("fileName", ""),
                        "game_versions": game_versions,
                        "loaders": loaders,
                        "date_published": f.get("fileDate", ""),
                        "files": [
                            {
                                "url": f.get("downloadUrl", ""),
                                "filename": f.get("fileName", ""),
                                "size": f.get("fileLength", 0),
                                "primary": True,
                            }
                        ],
                    }
                )

            return versions

    # -------------------------------------------------------------------
    # Install Modpack
    # -------------------------------------------------------------------
    @staticmethod
    async def install_modpack(
        db: Session,
        server_id: int,
        source: str,
        project_id: str,
        version_id: str,
    ) -> dict:
        """Download and install a modpack onto a server."""
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"success": False, "error": "Server not found"}

        server_path = Path(server.path)
        temp_dir = settings.TEMP_DIR / f"modpack_{server_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            if source == "modrinth":
                result = await ModpackInstaller._install_modrinth_modpack(
                    db, server, server_path, temp_dir, project_id, version_id
                )
            elif source == "curseforge":
                result = await ModpackInstaller._install_curseforge_modpack(
                    db, server, server_path, temp_dir, project_id, version_id
                )
            else:
                return {"success": False, "error": f"Unknown source: {source}"}

            return result
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    async def _install_modrinth_modpack(
        db: Session,
        server: Server,
        server_path: Path,
        temp_dir: Path,
        project_id: str,
        version_id: str,
    ) -> dict:
        """Install a Modrinth modpack (mrpack format)."""
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            # Get version info
            resp = await client.get(f"{settings.MODRINTH_API_URL}/version/{version_id}")
            resp.raise_for_status()
            version_data = resp.json()

            # Find primary file
            primary_file = None
            for f in version_data.get("files", []):
                if f.get("primary", False):
                    primary_file = f
                    break
            if not primary_file and version_data.get("files"):
                primary_file = version_data["files"][0]
            if not primary_file:
                return {"success": False, "error": "No downloadable file found"}

            # Download mrpack
            pack_path = temp_dir / primary_file["filename"]
            resp = await client.get(primary_file["url"])
            resp.raise_for_status()
            pack_path.write_bytes(resp.content)

            # Extract mrpack (it's a zip)
            extract_dir = temp_dir / "extracted"
            with zipfile.ZipFile(pack_path, "r") as zf:
                zf.extractall(extract_dir)

            # Parse modrinth.index.json
            index_path = extract_dir / "modrinth.index.json"
            if not index_path.exists():
                return {"success": False, "error": "Invalid mrpack: missing modrinth.index.json"}

            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)

            mc_version = ""
            loader = ""
            loader_version = ""
            deps = index.get("dependencies", {})
            mc_version = deps.get("minecraft", "")
            if "forge" in deps:
                loader = "forge"
                loader_version = deps["forge"]
            elif "fabric-loader" in deps:
                loader = "fabric"
                loader_version = deps["fabric-loader"]
            elif "quilt-loader" in deps:
                loader = "quilt"
                loader_version = deps["quilt-loader"]

            # Download all mod files listed in the index
            mods_dir = server_path / "mods"
            mods_dir.mkdir(exist_ok=True)

            files_to_download = index.get("files", [])
            for file_entry in files_to_download:
                file_dest = server_path / file_entry["path"]
                file_dest.parent.mkdir(parents=True, exist_ok=True)
                downloads = file_entry.get("downloads", [])
                if downloads:
                    file_resp = await client.get(downloads[0])
                    file_resp.raise_for_status()
                    file_dest.write_bytes(file_resp.content)

            # Copy overrides
            overrides_dir = extract_dir / "overrides"
            if overrides_dir.exists():
                for item in overrides_dir.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(overrides_dir)
                        dest = server_path / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)

            server_overrides = extract_dir / "server-overrides"
            if server_overrides.exists():
                for item in server_overrides.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(server_overrides)
                        dest = server_path / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)

            # Install the server loader if needed
            if loader == "forge" and mc_version:
                try:
                    jar = await ServerManager.download_forge_installer(mc_version, str(server_path))
                    server.server_jar = jar
                except Exception as e:
                    return {"success": False, "error": f"Failed to install Forge: {e}"}
            elif loader == "fabric" and mc_version:
                try:
                    jar = await ServerManager.download_fabric_server(mc_version, str(server_path))
                    server.server_jar = jar
                except Exception as e:
                    return {"success": False, "error": f"Failed to install Fabric: {e}"}
            else:
                try:
                    await ServerManager.download_vanilla_jar(mc_version, str(server_path))
                except Exception:
                    pass

            # Update server record
            server.server_type = loader or "vanilla"
            server.minecraft_version = mc_version
            server.loader_version = loader_version
            db.commit()

            # Save modpack record
            project_resp = await client.get(f"{settings.MODRINTH_API_URL}/project/{project_id}")
            project_data = project_resp.json() if project_resp.status_code == 200 else {}

            existing = db.query(InstalledModpack).filter(InstalledModpack.server_id == server.id).first()
            if existing:
                existing.modpack_name = index.get("name", project_data.get("title", ""))
                existing.modpack_slug = project_data.get("slug", "")
                existing.modpack_id = project_id
                existing.source = "modrinth"
                existing.version_id = version_id
                existing.version_name = version_data.get("name", version_data.get("version_number", ""))
                existing.minecraft_version = mc_version
                existing.loader = loader
            else:
                modpack_record = InstalledModpack(
                    server_id=server.id,
                    modpack_name=index.get("name", project_data.get("title", "")),
                    modpack_slug=project_data.get("slug", ""),
                    modpack_id=project_id,
                    source="modrinth",
                    version_id=version_id,
                    version_name=version_data.get("name", version_data.get("version_number", "")),
                    minecraft_version=mc_version,
                    loader=loader,
                )
                db.add(modpack_record)
            db.commit()

            return {
                "success": True,
                "modpack_name": index.get("name", ""),
                "minecraft_version": mc_version,
                "loader": loader,
                "files_installed": len(files_to_download),
            }

    @staticmethod
    async def _install_curseforge_modpack(
        db: Session,
        server: Server,
        server_path: Path,
        temp_dir: Path,
        project_id: str,
        version_id: str,
    ) -> dict:
        """Install a CurseForge modpack (manifest.json based)."""
        if not settings.CURSEFORGE_API_KEY:
            return {"success": False, "error": "CurseForge API key not configured"}

        headers = {"x-api-key": settings.CURSEFORGE_API_KEY}
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            # Get file info
            resp = await client.get(
                f"{settings.CURSEFORGE_API_URL}/mods/{project_id}/files/{version_id}",
                headers=headers,
            )
            resp.raise_for_status()
            file_data = resp.json()["data"]

            download_url = file_data.get("downloadUrl")
            if not download_url:
                return {"success": False, "error": "Download URL not available for this modpack"}

            # Download the modpack zip
            pack_path = temp_dir / file_data["fileName"]
            resp = await client.get(download_url)
            resp.raise_for_status()
            pack_path.write_bytes(resp.content)

            # Extract
            extract_dir = temp_dir / "extracted"
            with zipfile.ZipFile(pack_path, "r") as zf:
                zf.extractall(extract_dir)

            # Parse manifest.json
            manifest_path = extract_dir / "manifest.json"
            if not manifest_path.exists():
                return {"success": False, "error": "Invalid modpack: missing manifest.json"}

            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            mc_version = ""
            loader = ""
            loader_version = ""
            mc_info = manifest.get("minecraft", {})
            mc_version = mc_info.get("version", "")
            for mod_loader in mc_info.get("modLoaders", []):
                lid = mod_loader.get("id", "")
                if lid.startswith("forge-"):
                    loader = "forge"
                    loader_version = lid.replace("forge-", "")
                elif lid.startswith("fabric-"):
                    loader = "fabric"
                    loader_version = lid.replace("fabric-", "")

            # Download each mod file
            mods_dir = server_path / "mods"
            mods_dir.mkdir(exist_ok=True)

            installed_count = 0
            for mod_file in manifest.get("files", []):
                cf_project_id = mod_file["projectID"]
                cf_file_id = mod_file["fileID"]
                try:
                    file_resp = await client.get(
                        f"{settings.CURSEFORGE_API_URL}/mods/{cf_project_id}/files/{cf_file_id}",
                        headers=headers,
                    )
                    file_resp.raise_for_status()
                    fdata = file_resp.json()["data"]
                    dl_url = fdata.get("downloadUrl")
                    if dl_url:
                        mod_resp = await client.get(dl_url)
                        mod_resp.raise_for_status()
                        mod_path = mods_dir / fdata["fileName"]
                        mod_path.write_bytes(mod_resp.content)
                        installed_count += 1
                except Exception:
                    continue

            # Copy overrides
            overrides_name = manifest.get("overrides", "overrides")
            overrides_dir = extract_dir / overrides_name
            if overrides_dir.exists():
                for item in overrides_dir.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(overrides_dir)
                        dest = server_path / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)

            # Install loader
            if loader == "forge" and mc_version:
                try:
                    jar = await ServerManager.download_forge_installer(mc_version, str(server_path))
                    server.server_jar = jar
                except Exception as e:
                    return {"success": False, "error": f"Forge install failed: {e}"}
            elif loader == "fabric" and mc_version:
                try:
                    jar = await ServerManager.download_fabric_server(mc_version, str(server_path))
                    server.server_jar = jar
                except Exception as e:
                    return {"success": False, "error": f"Fabric install failed: {e}"}

            server.server_type = loader or "vanilla"
            server.minecraft_version = mc_version
            server.loader_version = loader_version
            db.commit()

            # Save record
            existing = db.query(InstalledModpack).filter(InstalledModpack.server_id == server.id).first()
            pack_name = manifest.get("name", "")
            if existing:
                existing.modpack_name = pack_name
                existing.modpack_id = project_id
                existing.source = "curseforge"
                existing.version_id = version_id
                existing.minecraft_version = mc_version
                existing.loader = loader
            else:
                db.add(InstalledModpack(
                    server_id=server.id,
                    modpack_name=pack_name,
                    modpack_id=project_id,
                    source="curseforge",
                    version_id=version_id,
                    minecraft_version=mc_version,
                    loader=loader,
                ))
            db.commit()

            return {
                "success": True,
                "modpack_name": pack_name,
                "minecraft_version": mc_version,
                "loader": loader,
                "files_installed": installed_count,
            }

    # -------------------------------------------------------------------
    # Check for updates
    # -------------------------------------------------------------------
    @staticmethod
    async def check_modpack_update(db: Session, server_id: int) -> dict:
        """Check if a newer version of the installed modpack is available."""
        modpack = db.query(InstalledModpack).filter(InstalledModpack.server_id == server_id).first()
        if not modpack:
            return {"has_update": False, "error": "No modpack installed"}

        if modpack.source == "modrinth":
            versions = await ModpackInstaller.get_modpack_versions_modrinth(
                modpack.modpack_id, modpack.minecraft_version, modpack.loader
            )
            if versions and versions[0]["id"] != modpack.version_id:
                return {
                    "has_update": True,
                    "current_version": modpack.version_name,
                    "latest_version": versions[0]["name"],
                    "latest_version_id": versions[0]["id"],
                }

        return {"has_update": False, "current_version": modpack.version_name}

    # -------------------------------------------------------------------
    # Export / Import custom modpack setups
    # -------------------------------------------------------------------
    @staticmethod
    async def export_modpack_setup(db: Session, server_id: int, export_name: str) -> dict:
        """Export current server mod setup as a portable config."""
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"success": False, "error": "Server not found"}

        server_path = Path(server.path)
        export_dir = settings.BACKUPS_DIR / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_file = export_dir / f"{export_name}.json"

        modpack = db.query(InstalledModpack).filter(InstalledModpack.server_id == server_id).first()
        from backend.models import InstalledMod
        mods = db.query(InstalledMod).filter(InstalledMod.server_id == server_id).all()

        export_data = {
            "name": export_name,
            "server_name": server.name,
            "server_type": server.server_type,
            "minecraft_version": server.minecraft_version,
            "loader_version": server.loader_version,
            "min_ram": server.min_ram,
            "max_ram": server.max_ram,
            "jvm_args": server.jvm_args,
            "modpack": {
                "name": modpack.modpack_name,
                "id": modpack.modpack_id,
                "source": modpack.source,
                "version_id": modpack.version_id,
            } if modpack else None,
            "mods": [
                {
                    "name": m.mod_name,
                    "id": m.mod_id,
                    "source": m.source,
                    "version_id": m.version_id,
                    "file_name": m.file_name,
                }
                for m in mods
            ],
        }

        export_file.write_text(json.dumps(export_data, indent=2), encoding="utf-8")
        return {"success": True, "path": str(export_file)}

    @staticmethod
    async def import_modpack_setup(db: Session, server_id: int, import_path: str) -> dict:
        """Import a previously exported modpack setup."""
        import_file = Path(import_path)
        if not import_file.exists():
            return {"success": False, "error": "Import file not found"}

        with open(import_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"success": False, "error": "Server not found"}

        results = []

        # Install modpack if present
        if data.get("modpack"):
            mp = data["modpack"]
            result = await ModpackInstaller.install_modpack(
                db, server_id, mp["source"], mp["id"], mp["version_id"]
            )
            results.append({"type": "modpack", "result": result})

        # Install individual mods
        from backend.services.mod_installer import ModInstaller
        for mod in data.get("mods", []):
            result = await ModInstaller.install_mod(
                db, server_id, mod["source"], mod["id"], mod["version_id"]
            )
            results.append({"type": "mod", "name": mod["name"], "result": result})

        # Apply server settings
        server.min_ram = data.get("min_ram", server.min_ram)
        server.max_ram = data.get("max_ram", server.max_ram)
        server.jvm_args = data.get("jvm_args", server.jvm_args)
        db.commit()

        return {"success": True, "results": results}

    # -------------------------------------------------------------------
    # Utils
    # -------------------------------------------------------------------
    @staticmethod
    def _build_modrinth_facets(project_type: str, mc_version: str = "", loader: str = "") -> str:
        facets = [[f'project_type:{project_type}']]
        if mc_version:
            facets.append([f"versions:{mc_version}"])
        if loader:
            facets.append([f"categories:{loader}"])
        facets.append(["server_side:required", "server_side:optional"])
        return json.dumps(facets)

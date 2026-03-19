"""
MCServerPanel - Plugin Installer Service
Handles browsing and installing server plugins from Modrinth, Hangar, and Spiget.
"""
import json
from pathlib import Path
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Server


class PluginInstaller:
    @staticmethod
    def _preferred_platform(loader: str, server_type: str) -> str:
        preferred = (loader or server_type or "paper").strip().lower()
        mapping = {
            "paper": "PAPER",
            "spigot": "PAPER",
            "bukkit": "PAPER",
            "purpur": "PAPER",
            "velocity": "VELOCITY",
            "waterfall": "WATERFALL",
            "bungeecord": "WATERFALL",
        }
        return mapping.get(preferred, "PAPER")

    @staticmethod
    def _split_hangar_project_id(project_id: str) -> tuple[str, str]:
        owner, slug = project_id.split(":", 1)
        return owner, slug

    @staticmethod
    async def search_plugins_modrinth(
        query: str = "",
        mc_version: str = "",
        loader: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        facets = [["project_type:plugin"]]
        if mc_version:
            facets.append([f"versions:{mc_version}"])
        if loader:
            facets.append([f"categories:{loader}"])

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
                        "name": p.get("title", ""),
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
    async def search_plugins_hangar(
        query: str = "",
        mc_version: str = "",
        loader: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        params = {
            "limit": limit,
            "offset": offset,
        }
        if query:
            params["query"] = query

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get("https://hangar.papermc.io/api/v1/projects", params=params)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for project in data.get("result", []):
                namespace = project.get("namespace", {})
                results.append({
                    "id": f"{namespace.get('owner', '')}:{namespace.get('slug', project.get('name', ''))}",
                    "slug": namespace.get("slug", ""),
                    "name": project.get("name", ""),
                    "description": project.get("description", ""),
                    "author": namespace.get("owner", ""),
                    "downloads": project.get("stats", {}).get("downloads", 0),
                    "icon_url": project.get("avatarUrl", ""),
                    "categories": [project.get("category", "")],
                    "source": "hangar",
                })
            return {
                "total": data.get("pagination", {}).get("count", len(results)),
                "results": results,
            }

    @staticmethod
    async def search_plugins_spiget(
        query: str = "",
        mc_version: str = "",
        loader: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        page = offset // max(limit, 1)
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            if query:
                resp = await client.get(
                    f"https://api.spiget.org/v2/search/resources/{quote(query)}",
                    params={"size": limit, "page": page},
                )
            else:
                resp = await client.get(
                    "https://api.spiget.org/v2/resources/free",
                    params={"size": limit, "page": page, "sort": "-downloads"},
                )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for resource in data:
                tested_versions = resource.get("testedVersions", [])
                if mc_version and tested_versions and mc_version not in tested_versions:
                    continue
                results.append({
                    "id": str(resource.get("id", "")),
                    "slug": "",
                    "name": resource.get("name", ""),
                    "description": resource.get("tag", ""),
                    "author": f"Author #{resource.get('author', {}).get('id', '')}",
                    "downloads": resource.get("downloads", 0),
                    "icon_url": resource.get("icon", {}).get("url", ""),
                    "categories": [str(resource.get("category", {}).get("id", ""))],
                    "source": "spiget",
                })
            return {
                "total": len(results),
                "results": results,
            }

    @staticmethod
    async def get_plugin_versions_modrinth(project_id: str, mc_version: str = "", loader: str = "") -> list[dict]:
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
                    "name": v.get("name", v.get("version_number", "")),
                    "game_versions": v.get("game_versions", []),
                    "loaders": v.get("loaders", []),
                    "files": v.get("files", []),
                }
                for v in resp.json()
            ]

    @staticmethod
    async def get_plugin_versions_hangar(project_id: str, mc_version: str = "", loader: str = "") -> list[dict]:
        owner, slug = PluginInstaller._split_hangar_project_id(project_id)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"https://hangar.papermc.io/api/v1/projects/{owner}/{slug}/versions")
            resp.raise_for_status()
            versions = []
            preferred_platform = PluginInstaller._preferred_platform(loader, loader)
            for version in resp.json().get("result", []):
                platforms = list(version.get("stats", {}).get("platformDownloads", {}).keys())
                if preferred_platform and platforms and preferred_platform not in platforms:
                    if not (preferred_platform == "PAPER" and "PAPER" in platforms):
                        continue
                detail_resp = await client.get(
                    f"https://hangar.papermc.io/api/v1/projects/{owner}/{slug}/versions/{quote(version.get('name', ''))}"
                )
                detail_resp.raise_for_status()
                detail = detail_resp.json()
                selected_platform = preferred_platform if preferred_platform in detail.get("downloads", {}) else next(iter(detail.get("downloads", {}).keys()), "")
                game_versions = detail.get("platformDependencies", {}).get(selected_platform, []) if selected_platform else []
                if mc_version and game_versions and mc_version not in game_versions:
                    continue
                versions.append({
                    "id": version.get("name", ""),
                    "name": version.get("name", ""),
                    "game_versions": game_versions,
                    "loaders": [selected_platform.lower()] if selected_platform else [],
                    "platform": selected_platform,
                    "files": [detail.get("downloads", {}).get(selected_platform, {})] if selected_platform else [],
                })
            return versions

    @staticmethod
    async def get_plugin_versions_spiget(project_id: str, mc_version: str = "", loader: str = "") -> list[dict]:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(f"https://api.spiget.org/v2/resources/{project_id}/versions")
            resp.raise_for_status()
            return [
                {
                    "id": str(v.get("id", "")),
                    "name": v.get("name", f"Version {v.get('id', '')}"),
                    "game_versions": [],
                    "loaders": [],
                    "files": [{"url": f"https://api.spiget.org/v2/resources/{project_id}/versions/{v.get('id', '')}/download/proxy"}],
                }
                for v in resp.json()
            ]

    @staticmethod
    async def install_plugin(
        db: Session,
        server_id: int,
        source: str,
        project_id: str,
        version_id: str,
    ) -> dict:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"success": False, "error": "Server not found"}

        plugins_dir = Path(server.path) / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)

        if source == "modrinth":
            return await PluginInstaller._install_modrinth_plugin(plugins_dir, project_id, version_id)
        if source == "hangar":
            return await PluginInstaller._install_hangar_plugin(plugins_dir, project_id, version_id, server.server_type)
        if source == "spiget":
            return await PluginInstaller._install_spiget_plugin(plugins_dir, project_id, version_id)

        return {"success": False, "error": f"Unsupported source: {source}"}

    @staticmethod
    async def _install_modrinth_plugin(plugins_dir: Path, project_id: str, version_id: str) -> dict:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            version_resp = await client.get(f"{settings.MODRINTH_API_URL}/version/{version_id}")
            version_resp.raise_for_status()
            version_data = version_resp.json()

            files = version_data.get("files", [])
            primary = next((f for f in files if f.get("primary")), files[0] if files else None)
            if not primary:
                return {"success": False, "error": "No downloadable plugin file found"}

            filename = primary.get("filename", "plugin.jar")
            file_path = plugins_dir / filename

            file_resp = await client.get(primary.get("url", ""))
            file_resp.raise_for_status()
            file_path.write_bytes(file_resp.content)

            project_resp = await client.get(f"{settings.MODRINTH_API_URL}/project/{project_id}")
            project_data = project_resp.json() if project_resp.status_code == 200 else {}

            return {
                "success": True,
                "plugin_name": project_data.get("title", filename),
                "file_name": filename,
                "path": str(file_path),
            }

    @staticmethod
    async def _install_hangar_plugin(plugins_dir: Path, project_id: str, version_id: str, server_type: str) -> dict:
        owner, slug = PluginInstaller._split_hangar_project_id(project_id)
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            detail_resp = await client.get(
                f"https://hangar.papermc.io/api/v1/projects/{owner}/{slug}/versions/{quote(version_id)}"
            )
            detail_resp.raise_for_status()
            detail = detail_resp.json()

            preferred_platform = PluginInstaller._preferred_platform("", server_type)
            selected_platform = preferred_platform if preferred_platform in detail.get("downloads", {}) else next(iter(detail.get("downloads", {}).keys()), "")
            download = detail.get("downloads", {}).get(selected_platform, {}) if selected_platform else {}
            download_url = download.get("downloadUrl", "")
            if not download_url:
                return {"success": False, "error": "No downloadable plugin file found"}

            filename = download.get("fileInfo", {}).get("name", f"{slug}-{version_id}.jar")
            file_path = plugins_dir / filename

            file_resp = await client.get(download_url)
            file_resp.raise_for_status()
            file_path.write_bytes(file_resp.content)

            return {
                "success": True,
                "plugin_name": slug,
                "file_name": filename,
                "path": str(file_path),
            }

    @staticmethod
    async def _install_spiget_plugin(plugins_dir: Path, project_id: str, version_id: str) -> dict:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            meta_resp = await client.get(f"https://api.spiget.org/v2/resources/{project_id}")
            meta_resp.raise_for_status()
            metadata = meta_resp.json()

            filename = f"{metadata.get('name', 'plugin').replace('/', '-')}-{version_id}.jar"
            file_path = plugins_dir / filename
            download_url = f"https://api.spiget.org/v2/resources/{project_id}/versions/{version_id}/download/proxy"

            file_resp = await client.get(download_url)
            file_resp.raise_for_status()
            file_path.write_bytes(file_resp.content)

            return {
                "success": True,
                "plugin_name": metadata.get("name", filename),
                "file_name": filename,
                "path": str(file_path),
            }

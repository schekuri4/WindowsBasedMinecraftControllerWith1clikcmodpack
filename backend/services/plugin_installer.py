"""
MCServerPanel - Plugin Installer Service
Handles browsing and installing server plugins from Modrinth.
"""
import json
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Server


class PluginInstaller:
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
    async def install_plugin(
        db: Session,
        server_id: int,
        source: str,
        project_id: str,
        version_id: str,
    ) -> dict:
        if source != "modrinth":
            return {"success": False, "error": f"Unsupported source: {source}"}

        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"success": False, "error": "Server not found"}

        plugins_dir = Path(server.path) / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)

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

"""
MCServerPanel - Server Manager Service
Handles starting, stopping, creating, detecting, and managing Minecraft servers.
"""
import asyncio
import datetime
import json
import os
import re
import shutil
import subprocess
import signal
from pathlib import Path
from typing import Optional

import httpx
import psutil
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Server
from backend.services.java_manager import JavaManager


class ServerManager:
    """Manages Minecraft server instances."""

    # Track running processes: server_id -> subprocess.Popen
    _processes: dict[int, subprocess.Popen] = {}
    # Console output buffers: server_id -> list[str]
    _console_buffers: dict[int, list[str]] = {}
    _MAX_CONSOLE_LINES = 500

    # -------------------------------------------------------------------
    # Server CRUD
    # -------------------------------------------------------------------
    @staticmethod
    def create_server(
        db: Session,
        name: str,
        server_type: str = "vanilla",
        minecraft_version: str = "1.20.4",
        min_ram: str = "1G",
        max_ram: str = "4G",
        port: int = 25565,
        java_path: str = "java",
    ) -> Server:
        """Create a new server entry and prepare its directory."""
        safe_name = re.sub(r'[^\w\-]', '_', name)
        server_path = settings.SERVERS_DIR / safe_name
        server_path.mkdir(parents=True, exist_ok=True)

        resolved_java_path = java_path
        if not resolved_java_path or resolved_java_path == "java":
            resolved_java_path = JavaManager.get_best_java_path(minecraft_version)

        server = Server(
            name=name,
            path=str(server_path),
            server_jar="server.jar",
            server_type=server_type,
            minecraft_version=minecraft_version,
            min_ram=min_ram,
            max_ram=max_ram,
            jvm_args=settings.DEFAULT_JVM_ARGS,
            port=port,
            java_path=resolved_java_path,
        )
        db.add(server)
        db.commit()
        db.refresh(server)

        # Accept EULA
        eula_path = server_path / "eula.txt"
        eula_path.write_text("eula=true\n", encoding="utf-8")

        # Write server.properties with port
        props_path = server_path / "server.properties"
        if not props_path.exists():
            props_path.write_text(
                f"server-port={port}\nonline-mode=true\nmax-players=20\ndifficulty=normal\n",
                encoding="utf-8",
            )

        return server

    @staticmethod
    def import_server(
        db: Session,
        name: str,
        path: str,
    ) -> Server:
        """Import an existing server folder by detecting its jar and type."""
        server_path = Path(path)
        if not server_path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        jar_name, server_type, mc_version, loader_version = ServerManager.detect_server(path)
        if not jar_name:
            raise ValueError("Could not find a server jar in the specified path")

        server = Server(
            name=name,
            path=str(server_path),
            server_jar=jar_name,
            server_type=server_type,
            minecraft_version=mc_version,
            loader_version=loader_version,
            min_ram=settings.DEFAULT_MIN_RAM,
            max_ram=settings.DEFAULT_MAX_RAM,
            jvm_args=settings.DEFAULT_JVM_ARGS,
            port=ServerManager._read_port_from_properties(server_path),
            java_path="java",
        )
        db.add(server)
        db.commit()
        db.refresh(server)
        return server

    @staticmethod
    def detect_server(path: str) -> tuple[str, str, str, str]:
        """Detect the server jar and type in a directory.
        Returns (jar_name, server_type, minecraft_version, loader_version).
        """
        server_path = Path(path)
        jar_name = ""
        server_type = "vanilla"
        mc_version = ""
        loader_version = ""

        # Priority patterns for detection (order matters - more specific first)
        jar_patterns = {
            "neoforge": re.compile(r"neoforge.*?\.jar", re.I),
            "arclight": re.compile(r"arclight.*?\.jar", re.I),
            "mohist": re.compile(r"mohist.*?\.jar", re.I),
            "magma": re.compile(r"magma.*?\.jar", re.I),
            "banner": re.compile(r"banner.*?\.jar", re.I),
            "cardboard": re.compile(r"cardboard.*?\.jar", re.I),
            "forge": re.compile(r"forge.*?(\d+\.\d+\.\d+).*?-(\d+[\.\d]*).*?\.jar", re.I),
            "purpur": re.compile(r"purpur.*?\.jar", re.I),
            "pufferfish": re.compile(r"pufferfish.*?\.jar", re.I),
            "paper": re.compile(r"paper.*?\.jar", re.I),
            "spigot": re.compile(r"spigot.*?\.jar", re.I),
            "craftbukkit": re.compile(r"craftbukkit.*?\.jar", re.I),
            "sponge": re.compile(r"sponge(vanilla|forge)?.*?\.jar", re.I),
            "glowstone": re.compile(r"glowstone.*?\.jar", re.I),
            "fabric": re.compile(r"fabric-server.*?\.jar", re.I),
            "quilt": re.compile(r"quilt-server.*?\.jar", re.I),
            "liteloader": re.compile(r"liteloader.*?\.jar", re.I),
            "rift": re.compile(r"rift.*?\.jar", re.I),
            "vanilla": re.compile(r"(server|minecraft_server).*?\.jar", re.I),
        }

        jars = list(server_path.glob("*.jar"))
        for stype, pattern in jar_patterns.items():
            for jar in jars:
                m = pattern.match(jar.name)
                if m:
                    jar_name = jar.name
                    server_type = stype
                    if stype == "forge" and m.lastindex and m.lastindex >= 1:
                        mc_version = m.group(1)
                        if m.lastindex >= 2:
                            loader_version = m.group(2)
                    break
            if jar_name:
                break

        # Fallback: pick first jar
        if not jar_name and jars:
            jar_name = jars[0].name

        # Try to read version from version.json
        version_json = server_path / "version.json"
        if version_json.exists() and not mc_version:
            try:
                with open(version_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    mc_version = data.get("id", "") or data.get("name", "")
            except Exception:
                pass

        # Check for fabric/quilt indicators
        if not server_type or server_type == "vanilla":
            if (server_path / ".fabric").exists() or (server_path / "fabric-server-launcher.properties").exists():
                server_type = "fabric"
            elif (server_path / ".quilt").exists():
                server_type = "quilt"

        return jar_name, server_type, mc_version, loader_version

    @staticmethod
    def _read_port_from_properties(server_path: Path) -> int:
        props = server_path / "server.properties"
        if props.exists():
            try:
                text = props.read_text(encoding="utf-8")
                m = re.search(r"server-port\s*=\s*(\d+)", text)
                if m:
                    return int(m.group(1))
            except Exception:
                pass
        return settings.DEFAULT_PORT

    @staticmethod
    def get_server(db: Session, server_id: int) -> Optional[Server]:
        return db.query(Server).filter(Server.id == server_id).first()

    @staticmethod
    def list_servers(db: Session) -> list[Server]:
        return db.query(Server).all()

    @staticmethod
    def update_server(db: Session, server_id: int, **kwargs) -> Optional[Server]:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return None
        new_port = kwargs.get("port")
        for key, value in kwargs.items():
            if hasattr(server, key):
                setattr(server, key, value)
        db.commit()
        db.refresh(server)

        if new_port is not None:
            server_path = Path(server.path)
            props_path = server_path / "server.properties"
            try:
                if props_path.exists():
                    text = props_path.read_text(encoding="utf-8")
                    if re.search(r"^server-port=.*$", text, flags=re.MULTILINE):
                        text = re.sub(r"^server-port=.*$", f"server-port={server.port}", text, flags=re.MULTILINE)
                    else:
                        text += f"\nserver-port={server.port}\n"
                else:
                    text = f"server-port={server.port}\nonline-mode=true\nmax-players=20\ndifficulty=normal\n"
                props_path.write_text(text, encoding="utf-8")
            except Exception:
                pass
        return server

    @staticmethod
    def delete_server(db: Session, server_id: int, delete_files: bool = False) -> bool:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return False
        if server.id in ServerManager._processes:
            ServerManager.stop_server(db, server_id)
        if delete_files:
            server_path = Path(server.path)
            if server_path.exists() and str(settings.SERVERS_DIR) in str(server_path):
                shutil.rmtree(server_path, ignore_errors=True)
        db.delete(server)
        db.commit()
        return True

    # -------------------------------------------------------------------
    # Start / Stop / Console
    # -------------------------------------------------------------------
    @staticmethod
    def start_server(db: Session, server_id: int) -> dict:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"success": False, "error": "Server not found"}
        if server_id in ServerManager._processes:
            proc = ServerManager._processes[server_id]
            if proc.poll() is None:
                return {"success": False, "error": "Server is already running"}

        server_path = Path(server.path)
        jar_path = server_path / server.server_jar
        if not jar_path.exists():
            return {"success": False, "error": f"Server jar not found: {server.server_jar}"}

        # Remove session.lock to prevent "another process has locked" errors
        for lock_file in server_path.rglob("session.lock"):
            try:
                lock_file.unlink()
            except Exception:
                pass

        java_executable = server.java_path or "java"
        if java_executable == "java" or not Path(java_executable).exists():
            detected_java = JavaManager.get_best_java_path(server.minecraft_version)
            if detected_java != "java":
                java_executable = detected_java
                server.java_path = detected_java
                db.commit()

        if java_executable == "java" and not shutil.which("java"):
            return {"success": False, "error": "Java not found. Please install Java 17+ or select a Java path in server settings."}

        cmd = [
            java_executable,
            f"-Xms{server.min_ram}",
            f"-Xmx{server.max_ram}",
        ]
        if server.jvm_args:
            cmd.extend(server.jvm_args.split())
        cmd.extend(["-jar", server.server_jar, "nogui"])

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(server_path),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            ServerManager._processes[server_id] = proc
            ServerManager._console_buffers[server_id] = []
            server.status = "running"
            server.pid = proc.pid
            db.commit()

            # Start background reader
            import threading
            t = threading.Thread(
                target=ServerManager._read_output,
                args=(server_id, proc),
                daemon=True,
            )
            t.start()

            return {"success": True, "pid": proc.pid}
        except FileNotFoundError:
            return {"success": False, "error": "Java not found. Please configure Java path."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def stop_server(db: Session, server_id: int) -> dict:
        if server_id not in ServerManager._processes:
            server = db.query(Server).filter(Server.id == server_id).first()
            if server:
                server.status = "stopped"
                server.pid = None
                db.commit()
            return {"success": True, "message": "Server was not running"}

        proc = ServerManager._processes[server_id]
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.write("stop\n")
                proc.stdin.flush()
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

        del ServerManager._processes[server_id]
        ServerManager._console_buffers.pop(server_id, None)

        server = db.query(Server).filter(Server.id == server_id).first()
        if server:
            server.status = "stopped"
            server.pid = None
            db.commit()

        return {"success": True}

    @staticmethod
    def send_command(server_id: int, command: str) -> dict:
        if server_id not in ServerManager._processes:
            return {"success": False, "error": "Server is not running"}
        proc = ServerManager._processes[server_id]
        if proc.poll() is not None:
            return {"success": False, "error": "Server process has ended"}
        try:
            proc.stdin.write(command + "\n")
            proc.stdin.flush()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_console(server_id: int, lines: int = 100) -> list[str]:
        buf = ServerManager._console_buffers.get(server_id, [])
        return buf[-lines:]

    @staticmethod
    def _read_output(server_id: int, proc: subprocess.Popen):
        """Background thread to read server stdout."""
        try:
            for line in proc.stdout:
                buf = ServerManager._console_buffers.setdefault(server_id, [])
                buf.append(line.rstrip("\n"))
                if len(buf) > ServerManager._MAX_CONSOLE_LINES:
                    del buf[0]
        except Exception:
            pass

    @staticmethod
    def get_server_status(db: Session, server_id: int) -> dict:
        """Get real-time status of a server."""
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"error": "Server not found"}

        is_running = False
        cpu = 0.0
        memory_mb = 0.0

        if server_id in ServerManager._processes:
            proc = ServerManager._processes[server_id]
            if proc.poll() is None:
                is_running = True
                try:
                    ps_proc = psutil.Process(proc.pid)
                    cpu = ps_proc.cpu_percent(interval=0.5)
                    memory_mb = ps_proc.memory_info().rss / (1024 * 1024)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            else:
                server.status = "stopped"
                server.pid = None
                db.commit()
                del ServerManager._processes[server_id]

        # Directory size
        server_path = Path(server.path)
        dir_size_mb = 0.0
        if server_path.exists():
            try:
                total = sum(f.stat().st_size for f in server_path.rglob("*") if f.is_file())
                dir_size_mb = total / (1024 * 1024)
            except Exception:
                pass

        return {
            "id": server.id,
            "name": server.name,
            "status": "running" if is_running else "stopped",
            "server_type": server.server_type,
            "minecraft_version": server.minecraft_version,
            "port": server.port,
            "pid": proc.pid if is_running else None,
            "cpu_percent": round(cpu, 1),
            "memory_mb": round(memory_mb, 1),
            "disk_mb": round(dir_size_mb, 1),
        }

    # -------------------------------------------------------------------
    # Download server jars
    # -------------------------------------------------------------------
    @staticmethod
    async def download_vanilla_jar(version: str, dest_dir: str) -> str:
        """Download vanilla Minecraft server jar."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"

        async with httpx.AsyncClient(timeout=120) as client:
            # Fetch version manifest
            manifest_resp = await client.get(
                "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
            )
            manifest_resp.raise_for_status()
            manifest = manifest_resp.json()

            version_url = None
            for v in manifest["versions"]:
                if v["id"] == version:
                    version_url = v["url"]
                    break
            if not version_url:
                raise ValueError(f"Minecraft version {version} not found")

            # Fetch version data
            ver_resp = await client.get(version_url)
            ver_resp.raise_for_status()
            ver_data = ver_resp.json()

            download_url = ver_data["downloads"]["server"]["url"]

            # Download jar
            jar_resp = await client.get(download_url)
            jar_resp.raise_for_status()
            jar_path.write_bytes(jar_resp.content)

        return str(jar_path)

    @staticmethod
    async def download_forge_installer(mc_version: str, dest_dir: str) -> str:
        """Download Forge installer and run it."""
        dest_path = Path(dest_dir)
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            # Get Forge promotions to find recommended version
            promos_url = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
            resp = await client.get(promos_url)
            resp.raise_for_status()
            promos = resp.json()["promos"]

            forge_version = promos.get(f"{mc_version}-recommended") or promos.get(f"{mc_version}-latest")
            if not forge_version:
                raise ValueError(f"No Forge version found for MC {mc_version}")

            full_version = f"{mc_version}-{forge_version}"
            installer_url = (
                f"https://maven.minecraftforge.net/net/minecraftforge/forge/"
                f"{full_version}/forge-{full_version}-installer.jar"
            )

            installer_path = dest_path / f"forge-{full_version}-installer.jar"
            resp = await client.get(installer_url)
            resp.raise_for_status()
            installer_path.write_bytes(resp.content)

        # Run the installer
        subprocess.run(
            ["java", "-jar", str(installer_path), "--installServer"],
            cwd=str(dest_path),
            timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        installer_path.unlink(missing_ok=True)

        # Find the resulting jar/script
        for f in dest_path.iterdir():
            if f.name.startswith("forge") and f.suffix == ".jar" and "installer" not in f.name.lower():
                return f.name

        # Newer Forge versions use run.bat
        run_bat = dest_path / "run.bat"
        if run_bat.exists():
            return "run.bat"

        return "server.jar"

    @staticmethod
    async def download_fabric_server(mc_version: str, dest_dir: str) -> str:
        """Download and install Fabric server."""
        dest_path = Path(dest_dir)
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            # Get latest loader + installer version
            loader_resp = await client.get("https://meta.fabricmc.net/v2/versions/loader")
            loader_resp.raise_for_status()
            loader_version = loader_resp.json()[0]["version"]

            installer_resp = await client.get("https://meta.fabricmc.net/v2/versions/installer")
            installer_resp.raise_for_status()
            installer_version = installer_resp.json()[0]["version"]

            jar_url = (
                f"https://meta.fabricmc.net/v2/versions/loader/"
                f"{mc_version}/{loader_version}/{installer_version}/server/jar"
            )

            jar_path = dest_path / "fabric-server-launch.jar"
            resp = await client.get(jar_url)
            resp.raise_for_status()
            jar_path.write_bytes(resp.content)

        return "fabric-server-launch.jar"

    @staticmethod
    async def download_neoforge_installer(mc_version: str, dest_dir: str) -> str:
        """Download NeoForge installer and run it."""
        dest_path = Path(dest_dir)
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            # List available NeoForge versions from Maven
            resp = await client.get(
                "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge"
            )
            resp.raise_for_status()
            all_versions = resp.json().get("versions", [])

            # NeoForge versions are like "20.4.237" for MC 1.20.4, "21.1.1" for MC 1.21.1
            # MC 1.20.x -> NeoForge 20.x, MC 1.21.x -> NeoForge 21.x
            parts = mc_version.split(".")
            if len(parts) >= 2:
                major_minor = f"{parts[1]}"  # e.g. "20" from "1.20.4"
                if len(parts) >= 3:
                    patch = parts[2]
                    prefix = f"{major_minor}.{patch}."
                else:
                    prefix = f"{major_minor}."
            else:
                prefix = ""

            matching = [v for v in all_versions if v.startswith(prefix)]
            if not matching:
                # Fallback: try just major
                matching = [v for v in all_versions if v.startswith(f"{parts[1]}.")]
            if not matching:
                raise ValueError(f"No NeoForge version found for MC {mc_version}")

            nf_version = matching[-1]  # Latest matching version
            installer_url = (
                f"https://maven.neoforged.net/releases/net/neoforged/neoforge/"
                f"{nf_version}/neoforge-{nf_version}-installer.jar"
            )

            installer_path = dest_path / f"neoforge-{nf_version}-installer.jar"
            resp = await client.get(installer_url)
            resp.raise_for_status()
            installer_path.write_bytes(resp.content)

        java_path = JavaManager.get_best_java_path(mc_version)
        subprocess.run(
            [java_path, "-jar", str(installer_path), "--installServer"],
            cwd=str(dest_path),
            timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        installer_path.unlink(missing_ok=True)

        # Find resulting jar or run script
        for f in dest_path.iterdir():
            if "neoforge" in f.name.lower() and f.suffix == ".jar" and "installer" not in f.name.lower():
                return f.name

        run_bat = dest_path / "run.bat"
        if run_bat.exists():
            return "run.bat"

        return "server.jar"

    @staticmethod
    async def download_quilt_server(mc_version: str, dest_dir: str) -> str:
        """Download Quilt server launcher jar."""
        dest_path = Path(dest_dir)
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            loader_resp = await client.get("https://meta.quiltmc.org/v3/versions/loader")
            loader_resp.raise_for_status()
            loader_version = loader_resp.json()[0]["version"]

            installer_resp = await client.get("https://meta.quiltmc.org/v3/versions/installer")
            installer_resp.raise_for_status()
            installer_version = installer_resp.json()[0]["version"]

            jar_url = (
                f"https://meta.quiltmc.org/v3/versions/loader/"
                f"{mc_version}/{loader_version}/{installer_version}/server/jar"
            )

            jar_path = dest_path / "quilt-server-launch.jar"
            resp = await client.get(jar_url)
            resp.raise_for_status()
            jar_path.write_bytes(resp.content)

        return "quilt-server-launch.jar"

    @staticmethod
    async def download_paper_jar(mc_version: str, dest_dir: str) -> str:
        """Download Paper server jar via PaperMC API."""
        return await ServerManager._download_papermc_project("paper", mc_version, dest_dir)

    @staticmethod
    async def download_purpur_jar(mc_version: str, dest_dir: str) -> str:
        """Download Purpur server jar."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(
                f"https://api.purpurmc.org/v2/purpur/{mc_version}/latest/download"
            )
            resp.raise_for_status()
            jar_path.write_bytes(resp.content)
        return "server.jar"

    @staticmethod
    async def download_pufferfish_jar(mc_version: str, dest_dir: str) -> str:
        """Download Pufferfish server jar from GitHub releases."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(
                "https://api.github.com/repos/pufferfish-gg/Pufferfish/releases",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            releases = resp.json()

            for release in releases:
                tag = release.get("tag_name", "")
                if mc_version in tag:
                    for asset in release.get("assets", []):
                        if asset["name"].endswith(".jar") and "pufferfish" in asset["name"].lower():
                            dl_resp = await client.get(asset["browser_download_url"])
                            dl_resp.raise_for_status()
                            jar_path.write_bytes(dl_resp.content)
                            return "server.jar"

            # Fallback: latest release
            if releases and releases[0].get("assets"):
                for asset in releases[0]["assets"]:
                    if asset["name"].endswith(".jar"):
                        dl_resp = await client.get(asset["browser_download_url"])
                        dl_resp.raise_for_status()
                        jar_path.write_bytes(dl_resp.content)
                        return "server.jar"

            raise ValueError(f"No Pufferfish jar found for MC {mc_version}")

    @staticmethod
    async def download_spigot_buildtools(mc_version: str, dest_dir: str) -> str:
        """Download and run SpigotMC BuildTools to build Spigot server jar."""
        dest_path = Path(dest_dir)
        bt_dir = settings.TEMP_DIR / "buildtools"
        bt_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(
                "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar"
            )
            resp.raise_for_status()
            bt_jar = bt_dir / "BuildTools.jar"
            bt_jar.write_bytes(resp.content)

        java_path = JavaManager.get_best_java_path(mc_version)
        subprocess.run(
            [java_path, "-jar", "BuildTools.jar", "--rev", mc_version],
            cwd=str(bt_dir),
            timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        # Find built jar
        built_jar = bt_dir / f"spigot-{mc_version}.jar"
        target_jar = dest_path / "server.jar"
        if built_jar.exists():
            shutil.copy2(str(built_jar), str(target_jar))
        else:
            # Try any spigot jar
            for f in bt_dir.iterdir():
                if f.name.startswith("spigot") and f.suffix == ".jar":
                    shutil.copy2(str(f), str(target_jar))
                    break

        return "server.jar"

    @staticmethod
    async def download_bukkit_buildtools(mc_version: str, dest_dir: str) -> str:
        """Download and run BuildTools to build CraftBukkit server jar."""
        dest_path = Path(dest_dir)
        bt_dir = settings.TEMP_DIR / "buildtools"
        bt_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(
                "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar"
            )
            resp.raise_for_status()
            bt_jar = bt_dir / "BuildTools.jar"
            bt_jar.write_bytes(resp.content)

        java_path = JavaManager.get_best_java_path(mc_version)
        subprocess.run(
            [java_path, "-jar", "BuildTools.jar", "--rev", mc_version, "--compile", "craftbukkit"],
            cwd=str(bt_dir),
            timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        built_jar = bt_dir / f"craftbukkit-{mc_version}.jar"
        target_jar = dest_path / "server.jar"
        if built_jar.exists():
            shutil.copy2(str(built_jar), str(target_jar))
        else:
            for f in bt_dir.iterdir():
                if f.name.startswith("craftbukkit") and f.suffix == ".jar":
                    shutil.copy2(str(f), str(target_jar))
                    break

        return "server.jar"

    @staticmethod
    async def download_glowstone_jar(mc_version: str, dest_dir: str) -> str:
        """Download Glowstone server jar from GitHub releases."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(
                "https://api.github.com/repos/GlowstoneMC/Glowstone/releases",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            releases = resp.json()
            for release in releases:
                for asset in release.get("assets", []):
                    if asset["name"].endswith(".jar"):
                        dl_resp = await client.get(asset["browser_download_url"])
                        dl_resp.raise_for_status()
                        jar_path.write_bytes(dl_resp.content)
                        return "server.jar"
            raise ValueError("No Glowstone jar found")

    @staticmethod
    async def download_sponge_jar(mc_version: str, dest_dir: str) -> str:
        """Download SpongeVanilla server jar."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            # Use Sponge downloads API
            resp = await client.get(
                f"https://dl-api-new.spongepowered.org/api/v2/groups/org.spongepowered/artifacts/spongevanilla/versions?tags=minecraft:{mc_version}&limit=1"
            )
            if resp.status_code == 200:
                data = resp.json()
                artifacts = data.get("artifacts", {})
                for ver_key, ver_data in artifacts.items():
                    assets = ver_data.get("assets", [])
                    for asset in assets:
                        if asset.get("classifier") == "universal" or asset.get("extension") == "jar":
                            dl_url = asset.get("downloadUrl") or asset.get("url")
                            if dl_url:
                                dl_resp = await client.get(dl_url)
                                dl_resp.raise_for_status()
                                jar_path.write_bytes(dl_resp.content)
                                return "server.jar"
            # Fallback: try GitHub releases
            resp = await client.get(
                "https://api.github.com/repos/SpongePowered/SpongeVanilla/releases",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            for release in resp.json():
                for asset in release.get("assets", []):
                    if asset["name"].endswith(".jar"):
                        dl_resp = await client.get(asset["browser_download_url"])
                        dl_resp.raise_for_status()
                        jar_path.write_bytes(dl_resp.content)
                        return "server.jar"
            raise ValueError(f"No SpongeVanilla jar found for MC {mc_version}")

    # -------------------------------------------------------------------
    # Hybrid server downloads (Mods + Plugins)
    # -------------------------------------------------------------------
    @staticmethod
    async def download_mohist_jar(mc_version: str, dest_dir: str) -> str:
        """Download Mohist server jar via Mohistmc API."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(
                f"https://mohistmc.com/api/v2/projects/mohist/{mc_version}/builds/latest"
            )
            resp.raise_for_status()
            data = resp.json()
            dl_url = data.get("url")
            if not dl_url:
                raise ValueError(f"No Mohist build found for MC {mc_version}")
            dl_resp = await client.get(dl_url)
            dl_resp.raise_for_status()
            jar_path.write_bytes(dl_resp.content)
        return "server.jar"

    @staticmethod
    async def download_arclight_jar(mc_version: str, dest_dir: str) -> str:
        """Download Arclight server jar from GitHub releases."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(
                "https://api.github.com/repos/IzzelAliz/Arclight/releases",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            releases = resp.json()
            for release in releases:
                tag = release.get("tag_name", "")
                body = release.get("body", "")
                if mc_version in tag or mc_version in body:
                    for asset in release.get("assets", []):
                        name = asset["name"].lower()
                        if name.endswith(".jar") and "arclight" in name:
                            dl_resp = await client.get(asset["browser_download_url"])
                            dl_resp.raise_for_status()
                            jar_path.write_bytes(dl_resp.content)
                            return "server.jar"
            # Fallback: latest release
            if releases:
                for asset in releases[0].get("assets", []):
                    name = asset["name"].lower()
                    if name.endswith(".jar") and "arclight" in name:
                        dl_resp = await client.get(asset["browser_download_url"])
                        dl_resp.raise_for_status()
                        jar_path.write_bytes(dl_resp.content)
                        return "server.jar"
            raise ValueError(f"No Arclight jar found for MC {mc_version}")

    @staticmethod
    async def download_magma_jar(mc_version: str, dest_dir: str) -> str:
        """Download Magma server jar."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            # Try Magma API
            resp = await client.get(
                f"https://api.magmafoundation.org/api/v2/{mc_version}/latest"
            )
            if resp.status_code == 200:
                data = resp.json()
                dl_url = data.get("url") or data.get("link")
                if dl_url:
                    dl_resp = await client.get(dl_url)
                    dl_resp.raise_for_status()
                    jar_path.write_bytes(dl_resp.content)
                    return "server.jar"
            # Fallback: GitHub
            resp = await client.get(
                "https://api.github.com/repos/magmafoundation/Magma/releases",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            for release in resp.json():
                tag = release.get("tag_name", "")
                if mc_version in tag:
                    for asset in release.get("assets", []):
                        if asset["name"].endswith(".jar"):
                            dl_resp = await client.get(asset["browser_download_url"])
                            dl_resp.raise_for_status()
                            jar_path.write_bytes(dl_resp.content)
                            return "server.jar"
            raise ValueError(f"No Magma jar found for MC {mc_version}")

    @staticmethod
    async def download_banner_jar(mc_version: str, dest_dir: str) -> str:
        """Download Banner server jar via Mohistmc API."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(
                f"https://mohistmc.com/api/v2/projects/banner/{mc_version}/builds/latest"
            )
            resp.raise_for_status()
            data = resp.json()
            dl_url = data.get("url")
            if not dl_url:
                raise ValueError(f"No Banner build found for MC {mc_version}")
            dl_resp = await client.get(dl_url)
            dl_resp.raise_for_status()
            jar_path.write_bytes(dl_resp.content)
        return "server.jar"

    @staticmethod
    async def download_cardboard_jar(mc_version: str, dest_dir: str) -> str:
        """Download Cardboard (Bukkit on Fabric) jar from GitHub."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(
                "https://api.github.com/repos/CardboardPowered/cardboard/releases",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            releases = resp.json()
            for release in releases:
                tag = release.get("tag_name", "")
                if mc_version in tag:
                    for asset in release.get("assets", []):
                        if asset["name"].endswith(".jar"):
                            dl_resp = await client.get(asset["browser_download_url"])
                            dl_resp.raise_for_status()
                            jar_path.write_bytes(dl_resp.content)
                            return "server.jar"
            if releases:
                for asset in releases[0].get("assets", []):
                    if asset["name"].endswith(".jar"):
                        dl_resp = await client.get(asset["browser_download_url"])
                        dl_resp.raise_for_status()
                        jar_path.write_bytes(dl_resp.content)
                        return "server.jar"
            raise ValueError(f"No Cardboard jar found for MC {mc_version}")

    # -------------------------------------------------------------------
    # Legacy mod loaders
    # -------------------------------------------------------------------
    @staticmethod
    async def download_liteloader_jar(mc_version: str, dest_dir: str) -> str:
        """Download LiteLoader server jar (legacy, limited version support)."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        # LiteLoader is legacy; provide direct download attempt
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            # Try known snapshot repo
            url = f"http://dl.liteloader.com/versions/com/mumfrey/liteloader/{mc_version}/liteloader-{mc_version}.jar"
            resp = await client.get(url)
            if resp.status_code == 200:
                jar_path.write_bytes(resp.content)
                return "server.jar"
            raise ValueError(
                f"LiteLoader is a legacy mod loader with limited version support. "
                f"No jar found for MC {mc_version}. Consider using Fabric or Forge instead."
            )

    @staticmethod
    async def download_rift_jar(mc_version: str, dest_dir: str) -> str:
        """Download Rift mod loader (legacy, for 1.13.x only)."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        if not mc_version.startswith("1.13"):
            raise ValueError("Rift only supports Minecraft 1.13.x. Consider NeoForge or Fabric for newer versions.")
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(
                "https://api.github.com/repos/DimensionalDevelopment/Rift/releases",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            for release in resp.json():
                for asset in release.get("assets", []):
                    if asset["name"].endswith(".jar"):
                        dl_resp = await client.get(asset["browser_download_url"])
                        dl_resp.raise_for_status()
                        jar_path.write_bytes(dl_resp.content)
                        return "server.jar"
            raise ValueError("No Rift jar found. Rift is a legacy loader for MC 1.13 only.")

    # -------------------------------------------------------------------
    # Helper: PaperMC API (shared by Paper and Folia)
    # -------------------------------------------------------------------
    @staticmethod
    async def _download_papermc_project(project: str, mc_version: str, dest_dir: str) -> str:
        """Download a jar from PaperMC API (paper, folia, velocity, waterfall)."""
        dest_path = Path(dest_dir)
        jar_path = dest_path / "server.jar"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(
                f"https://api.papermc.io/v2/projects/{project}/versions/{mc_version}/builds"
            )
            resp.raise_for_status()
            builds = resp.json()["builds"]
            if not builds:
                raise ValueError(f"No {project} builds found for MC {mc_version}")
            latest = builds[-1]
            build_num = latest["build"]
            download_name = latest["downloads"]["application"]["name"]
            dl_url = (
                f"https://api.papermc.io/v2/projects/{project}/versions/"
                f"{mc_version}/builds/{build_num}/downloads/{download_name}"
            )
            dl_resp = await client.get(dl_url)
            dl_resp.raise_for_status()
            jar_path.write_bytes(dl_resp.content)
        return "server.jar"

    @staticmethod
    async def get_available_versions() -> list[dict]:
        """Fetch list of available Minecraft versions."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {"id": v["id"], "type": v["type"], "releaseTime": v["releaseTime"]}
                for v in data["versions"]
            ]

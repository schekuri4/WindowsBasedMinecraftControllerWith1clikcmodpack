"""
MCServerPanel - Java Detection & Management
"""
import os
import re
import subprocess
import shutil
from pathlib import Path
from backend.config import settings


class JavaManager:
    """Detects and manages Java installations on Windows."""

    @staticmethod
    def find_java_installations() -> list[dict]:
        """Scan system for Java installations."""
        installations = []
        seen_paths = set()

        # Check PATH first
        java_on_path = shutil.which("java")
        if java_on_path:
            java_path = Path(java_on_path).resolve()
            info = JavaManager._get_java_info(str(java_path))
            if info and str(java_path) not in seen_paths:
                seen_paths.add(str(java_path))
                installations.append(info)

        # Check JAVA_HOME
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            java_exe = Path(java_home) / "bin" / "java.exe"
            if java_exe.exists():
                info = JavaManager._get_java_info(str(java_exe))
                if info and str(java_exe) not in seen_paths:
                    seen_paths.add(str(java_exe))
                    installations.append(info)

        # Scan known directories
        for search_path in settings.JAVA_SEARCH_PATHS:
            p = Path(search_path)
            if not p.exists():
                continue
            for child in p.iterdir():
                if child.is_dir():
                    java_exe = child / "bin" / "java.exe"
                    if java_exe.exists() and str(java_exe) not in seen_paths:
                        info = JavaManager._get_java_info(str(java_exe))
                        if info:
                            seen_paths.add(str(java_exe))
                            installations.append(info)

        return installations

    @staticmethod
    def _get_java_info(java_path: str) -> dict | None:
        """Get version info for a Java executable."""
        try:
            result = subprocess.run(
                [java_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            output = result.stderr + result.stdout
            version_match = re.search(r'"(\d+[\.\d_]*)"', output)
            version = version_match.group(1) if version_match else "unknown"

            # Determine major version
            major = version.split(".")[0]
            if major == "1":
                major = version.split(".")[1] if len(version.split(".")) > 1 else major

            vendor = "Unknown"
            output_lower = output.lower()
            if "openjdk" in output_lower:
                vendor = "OpenJDK"
            elif "hotspot" in output_lower:
                vendor = "Oracle HotSpot"
            elif "adoptium" in output_lower or "temurin" in output_lower:
                vendor = "Eclipse Adoptium"
            elif "zulu" in output_lower:
                vendor = "Azul Zulu"

            is_64bit = "64-bit" in output or "amd64" in output_lower

            return {
                "path": java_path,
                "version": version,
                "major_version": int(major) if major.isdigit() else 0,
                "vendor": vendor,
                "is_64bit": is_64bit,
            }
        except Exception:
            return None

    @staticmethod
    def get_recommended_java(minecraft_version: str) -> int:
        """Return recommended Java major version for a Minecraft version."""
        try:
            parts = minecraft_version.split(".")
            if len(parts) >= 2:
                minor = int(parts[1])
                if minor >= 21:
                    return 21
                if minor >= 17:
                    return 17
                return 8
        except (ValueError, IndexError):
            pass
        return 17

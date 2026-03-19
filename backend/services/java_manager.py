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
        major, minor, patch = JavaManager._parse_mc_version(minecraft_version)

        # 1.20.5+ generally requires Java 21+
        if major > 1 or (major == 1 and (minor > 20 or (minor == 20 and patch >= 5))):
            return 21

        # 1.18 - 1.20.4 generally run best on Java 17
        if major == 1 and 18 <= minor <= 20:
            return 17

        # 1.17 targets Java 16
        if major == 1 and minor == 17:
            return 16

        # Older versions typically target Java 8
        return 8

    @staticmethod
    def _parse_mc_version(minecraft_version: str) -> tuple[int, int, int]:
        """Parse a Minecraft version string into (major, minor, patch)."""
        try:
            core = minecraft_version.split('-')[0].strip()
            parts = core.split('.')
            major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 1
            minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
            return major, minor, patch
        except Exception:
            return 1, 20, 0

    @staticmethod
    def _compatible_java_majors(minecraft_version: str) -> list[int]:
        """Return compatible Java majors for a Minecraft version, in priority order."""
        recommended = JavaManager.get_recommended_java(minecraft_version)
        if recommended == 21:
            return [21, 22, 23]
        if recommended == 17:
            return [17]
        if recommended == 16:
            return [16]
        return [8]

    @staticmethod
    def get_best_java_path(minecraft_version: str) -> str:
        """Return the best available Java executable path for a Minecraft version."""
        installations = JavaManager.find_java_installations()
        if not installations:
            return "java"

        for major in JavaManager._compatible_java_majors(minecraft_version):
            matches = [item for item in installations if item.get("major_version", 0) == major]
            if matches:
                matches.sort(key=lambda item: item.get("is_64bit", False), reverse=True)
                return matches[0].get("path", "java")

        return "java"

    @staticmethod
    def is_java_compatible(java_path: str, minecraft_version: str) -> bool:
        """Check whether a Java executable is compatible with a Minecraft version."""
        info = JavaManager._get_java_info(java_path)
        if not info:
            return False
        return info.get("major_version", 0) in JavaManager._compatible_java_majors(minecraft_version)

"""
MCServerPanel - System Monitor Service
Provides CPU, RAM, disk, and network usage information.
"""
import socket

import httpx
import psutil
from backend.config import settings


class SystemMonitor:
    """Monitor system resource usage."""

    @staticmethod
    def get_system_stats() -> dict:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(str(settings.DATA_DIR))

        net = psutil.net_io_counters()

        return {
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count(logical=True),
            },
            "memory": {
                "total_mb": round(mem.total / (1024 * 1024)),
                "used_mb": round(mem.used / (1024 * 1024)),
                "available_mb": round(mem.available / (1024 * 1024)),
                "percent": mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "free_gb": round(disk.free / (1024**3), 1),
                "percent": round(disk.percent, 1),
            },
            "network": {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
            },
        }

    @staticmethod
    def get_process_stats(pid: int) -> dict:
        try:
            proc = psutil.Process(pid)
            return {
                "pid": pid,
                "cpu_percent": proc.cpu_percent(interval=0.5),
                "memory_mb": round(proc.memory_info().rss / (1024 * 1024), 1),
                "status": proc.status(),
                "threads": proc.num_threads(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"pid": pid, "error": "Process not found or access denied"}

    @staticmethod
    async def get_network_info() -> dict:
        local_ips = []
        try:
            for addresses in psutil.net_if_addrs().values():
                for address in addresses:
                    if address.family == socket.AF_INET and address.address and not address.address.startswith("127."):
                        local_ips.append(address.address)
        except Exception:
            pass

        local_ips = sorted(set(local_ips))
        public_ip = ""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("https://api.ipify.org?format=json")
                resp.raise_for_status()
                public_ip = resp.json().get("ip", "")
        except Exception:
            public_ip = ""

        panel_port = settings.PORT
        panel_urls = []
        if public_ip:
            panel_urls.append(f"http://{public_ip}:{panel_port}")
        panel_urls.extend([f"http://{ip}:{panel_port}" for ip in local_ips])

        return {
            "public_ip": public_ip,
            "local_ips": local_ips,
            "panel_port": panel_port,
            "panel_urls": panel_urls,
            "default_minecraft_port": settings.DEFAULT_PORT,
        }

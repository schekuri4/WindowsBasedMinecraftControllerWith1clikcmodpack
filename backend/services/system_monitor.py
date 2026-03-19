"""
MCServerPanel - System Monitor Service
Provides CPU, RAM, disk, and network usage information.
"""
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

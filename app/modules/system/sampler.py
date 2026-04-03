import ctypes
import platform
import socket
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import psutil

from app.core.logger import logger


class SystemSampler:
    """
    Background service that periodically samples system metrics (CPU, Memory, Disk, Network).
    Uses multiple threads to avoid blocking the main API thread.
    """

    def __init__(self):
        self._cpu_usage: List[float] = [0.0] * psutil.cpu_count()
        self._cpu_metadata: Dict[str, str] = {"brand": "Unknown", "vendor_id": "Unknown"}
        self._net_cache: Dict[str, Dict[str, int]] = {}
        self._prev_net_stats: Dict[str, Any] = {}
        self._latency: Optional[float] = None
        self._sample_error: Optional[str] = None
        self._top_processes: List[Dict[str, Any]] = []
        self._disk_cache: Dict[str, Any] = {"disks": [], "io": {"read": 0, "written": 0}}

        self._running = True
        self._lock = threading.Lock()

        # Initialize and start sampling threads
        self._cpu_thread = threading.Thread(target=self._cpu_worker, daemon=True)
        self._net_thread = threading.Thread(target=self._net_worker, daemon=True)
        self._latency_thread = threading.Thread(target=self._latency_worker, daemon=True)
        self._process_thread = threading.Thread(target=self._process_worker, daemon=True)
        self._disk_thread = threading.Thread(target=self._disk_worker, daemon=True)

        self._cpu_thread.start()
        self._net_thread.start()
        self._latency_thread.start()
        self._process_thread.start()
        self._disk_thread.start()

    def _get_cpu_info_once(self) -> None:
        """Retrieves CPU brand and vendor information once at startup."""
        if self._cpu_metadata["brand"] != "Unknown":
            return

        brand = "Unknown"
        vendor_id = "Unknown"
        try:
            import cpuinfo

            info = cpuinfo.get_cpu_info()
            brand = info.get("brand_raw", platform.processor())
            vendor_id = info.get("vendor_id_raw", "Unknown")
        except ImportError, Exception:
            brand = platform.processor() or "Unknown"

        with self._lock:
            self._cpu_metadata["brand"] = brand
            self._cpu_metadata["vendor_id"] = vendor_id

    def _cpu_worker(self) -> None:
        """Thread worker to sample CPU usage per core."""
        self._get_cpu_info_once()

        try:
            self._cpu_usage = psutil.cpu_percent(interval=None, percpu=True)
        except Exception:
            pass

        while self._running:
            try:
                usage = psutil.cpu_percent(interval=1, percpu=True)
                with self._lock:
                    self._cpu_usage = usage
            except Exception as e:
                logger.error(f"Error in CPU sampler: {e}")
                time.sleep(1)

    def _net_worker(self) -> None:
        """Thread worker to sample network I/O stats per interface."""
        while self._running:
            try:
                current = psutil.net_io_counters(pernic=True)

                if not current:
                    time.sleep(1)
                    continue

                cache = {}
                with self._lock:
                    for name, s2 in current.items():
                        s1 = self._prev_net_stats.get(name, s2)
                        cache[name] = {
                            "received": s2.bytes_recv - s1.bytes_recv,
                            "transmitted": s2.bytes_sent - s1.bytes_sent,
                            "packets_received": s2.packets_recv - s1.packets_recv,
                            "packets_transmitted": s2.packets_sent - s1.packets_sent,
                            "errors_on_received": s2.errin - s1.errin,
                            "errors_on_transmitted": s2.errout - s1.errout,
                            "total_received": s2.bytes_recv,
                            "total_transmitted": s2.bytes_sent,
                            "total_packets_received": s2.packets_recv,
                            "total_packets_transmitted": s2.packets_sent,
                            "total_errors_on_received": s2.errin,
                            "total_errors_on_transmitted": s2.errout,
                        }
                    self._prev_net_stats = current
                    self._net_cache = cache
                    self._sample_error = None
            except Exception as e:
                with self._lock:
                    self._sample_error = str(e)
                time.sleep(1)
            time.sleep(1)

    def _latency_worker(self) -> None:
        """Thread worker to sample network latency to a public DNS."""
        while self._running:
            try:
                start = time.time()
                socket.setdefaulttimeout(2)
                # Google DNS as a reliable ping target
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
                latency = round((time.time() - start) * 1000, 2)
                with self._lock:
                    self._latency = latency
            except Exception:
                with self._lock:
                    self._latency = None
            time.sleep(5)

    def _process_worker(self) -> None:
        """Thread worker to sample top 10 processes by memory usage."""
        while self._running:
            try:
                temp_procs = []
                for proc in psutil.process_iter(["pid", "name", "memory_info", "memory_percent"]):
                    try:
                        info = proc.info
                        if info["memory_info"] is None:
                            continue
                        temp_procs.append(
                            {
                                "pid": info["pid"],
                                "name": info["name"] or "Unknown",
                                "memory": info["memory_info"].rss,
                                "virtual_memory": info["memory_info"].vms,
                                "memory_percent": info["memory_percent"] or 0.0,
                            }
                        )
                    except psutil.NoSuchProcess, psutil.AccessDenied:
                        continue

                temp_procs.sort(key=lambda x: x["memory"], reverse=True)
                with self._lock:
                    self._top_processes = temp_procs[:10]
            except Exception as e:
                logger.error(f"Error in Process sampler: {e}")
            time.sleep(5)

    def _get_volume_label(self, mountpoint: str) -> str:
        """Retrieves the volume label for a mountpoint (Windows-only support)."""
        if platform.system() != "Windows":
            return mountpoint.rstrip("/\\") or "/"

        try:
            label = ctypes.create_unicode_buffer(261)
            ctypes.windll.kernel32.GetVolumeInformationW(mountpoint, label, 261, None, None, None, None, 0)
            return label.value or mountpoint.rstrip("\\")
        except AttributeError, Exception:
            return mountpoint.rstrip("\\")

    def _disk_worker(self) -> None:
        """Thread worker to sample disk status and I/O."""
        while self._running:
            try:
                disks = []
                partitions = psutil.disk_partitions(all=False)
                for part in partitions:
                    # Skip virtual or temporary file systems
                    if any(
                        x in part.device.lower() or x in part.mountpoint.lower()
                        for x in ["overlay", "tmpfs", "shm", "vfs", "docker", "loop"]
                    ):
                        continue

                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        disks.append(
                            {
                                "name": self._get_volume_label(part.mountpoint),
                                "mount_point": part.mountpoint,
                                "file_system": part.fstype,
                                "kind": "Unknown",
                                "is_removable": "removable" in part.opts,
                                "total_space": usage.total,
                                "available_space": usage.free,
                                "used_space": usage.used,
                                "usage_percent": usage.percent,
                            }
                        )
                    except PermissionError, FileNotFoundError:
                        continue

                io = psutil.disk_io_counters(perdisk=False)
                with self._lock:
                    self._disk_cache = {
                        "disks": disks,
                        "io": {
                            "read_bytes": io.read_bytes if io else 0,
                            "write_bytes": io.write_bytes if io else 0,
                        },
                    }
            except Exception as e:
                logger.error(f"Error in Disk sampler: {e}")
            time.sleep(10)

    def get_cpu_usage(self) -> List[float]:
        """Returns the last sampled CPU usage per core."""
        with self._lock:
            return self._cpu_usage

    def get_cpu_metadata(self) -> Dict[str, str]:
        """Returns CPU metadata (brand, vendor)."""
        with self._lock:
            return self._cpu_metadata

    def get_net_cache(self) -> Tuple[Dict[str, Dict[str, int]], Optional[str]]:
        """Returns sampled network throughput metrics and any sampling errors."""
        with self._lock:
            return self._net_cache, self._sample_error

    def get_latency(self) -> Optional[float]:
        """Returns the last measured network latency."""
        with self._lock:
            return self._latency

    def get_top_processes(self) -> List[Dict[str, Any]]:
        """Returns the top 10 processes by memory consumption."""
        with self._lock:
            return self._top_processes

    def get_disks(self) -> Dict[str, Any]:
        """Returns sampled disk usage and I/O statistics."""
        with self._lock:
            return self._disk_cache


sampler = SystemSampler()

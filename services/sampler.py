import ctypes
import os
import platform
import socket
import threading
import time

import psutil

from services.logger import logger


class SystemSampler:
    def __init__(self):
        # Initialize with zeros to avoid "usage unavailable" errors on immediate requests
        self._cpu_usage = [0.0] * psutil.cpu_count()

        self._cpu_metadata = {"brand": "Unknown", "vendor_id": "Unknown"}
        self._net_cache = {}
        self._prev_net_stats = {}
        self._latency = None
        self._sample_error = None

        self._top_processes = []
        self._disk_cache = {"disks": [], "io": {"read": 0, "written": 0}}
        self._prev_disk_io = None

        self._running = True
        self._lock = threading.Lock()

        # Start background workers
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

    def _get_cpu_info_once(self):
        """Fetches CPU brand and vendor ID once."""
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

    def _cpu_worker(self):
        """Samples CPU usage every second and metadata once."""
        self._get_cpu_info_once()
        # Initial non-blocking sample
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
                print(f"Error in CPU sampler: {e}")
                time.sleep(1)

    def _parse_host_net_dev(self):
        """
        Manually parse /host/proc/net/dev to get host-level network statistics.
        Returns a dictionary compatible with psutil.net_io_counters(pernic=True).
        """
        path = "/proc/net/dev"
        if not os.path.exists(path):
            return None

        from collections import namedtuple

        snetio = namedtuple(
            "snetio",
            [
                "bytes_sent",
                "bytes_recv",
                "packets_sent",
                "packets_recv",
                "errin",
                "errout",
                "dropin",
                "dropout",
            ],
        )

        stats = {}
        try:
            with open(path, "r") as f:
                lines = f.readlines()
                for line in lines[2:]:
                    parts = line.split(":")
                    if len(parts) < 2:
                        continue
                    iface = parts[0].strip()
                    data = parts[1].split()

                    # Receive: bytes(0), packets(1), errs(2), drop(3)...
                    # Transmit: bytes(8), packets(9), errs(10), drop(11)...
                    stats[iface] = snetio(
                        bytes_recv=int(data[0]),
                        packets_recv=int(data[1]),
                        errin=int(data[2]),
                        dropin=int(data[3]),
                        bytes_sent=int(data[8]),
                        packets_sent=int(data[9]),
                        errout=int(data[10]),
                        dropout=int(data[11]),
                    )
            return stats
        except Exception as e:
            logger.error(f"Error parsing host net dev: {e}")
            return None

    def _net_worker(self):
        """Samples network byte rates every second."""
        while self._running:
            try:
                # Try to get host-level stats if available, fall back to psutil
                current = self._parse_host_net_dev()
                if not current:
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

    def _latency_worker(self):
        """Samples network latency every 5 seconds."""
        while self._running:
            try:
                start = time.time()
                socket.setdefaulttimeout(2)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
                latency = round((time.time() - start) * 1000, 2)
                with self._lock:
                    self._latency = latency
            except Exception:
                with self._lock:
                    self._latency = None
            time.sleep(5)

    def _process_worker(self):
        """Samples top 10 processes every 5 seconds."""
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
                print(f"Error in Process sampler: {e}")
            time.sleep(5)

    def _get_volume_label(self, mountpoint):
        """Helper to get volume label on Windows."""
        try:
            label = ctypes.create_unicode_buffer(261)
            ctypes.windll.kernel32.GetVolumeInformationW(mountpoint, label, 261, None, None, None, None, 0)
            return label.value or mountpoint.rstrip("\\")
        except AttributeError:
            return mountpoint.rstrip("\\")
        except Exception:
            return mountpoint.rstrip("\\")

    def _disk_worker(self):
        """Samples disk partitions and usage every 10 seconds."""
        use_host_prefix = os.path.exists("/host") and platform.system() == "Linux"
        while self._running:
            try:
                disks = []
                partitions = psutil.disk_partitions(all=False)
                logger.info(f"Host Discovery: Found {len(partitions)} potential partitions")
                for part in partitions:
                    # Skip noise and container-specific mounts
                    if any(
                        x in part.device or x in part.mountpoint
                        for x in ["overlay", "tmpfs", "shm", "vfs", "docker", "loop"]
                    ):
                        continue

                    try:
                        # Inside container, host root is at /host
                        check_path = f"/host{part.mountpoint}" if use_host_prefix else part.mountpoint

                        # Validate the path exists before usage to avoid exceptions
                        if not os.path.exists(check_path):
                            continue

                        usage = psutil.disk_usage(check_path)
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
                                "health": "Unknown",
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
                print(f"Error in Disk sampler: {e}")
            time.sleep(10)

    def get_cpu_usage(self):
        with self._lock:
            return self._cpu_usage

    def get_cpu_metadata(self):
        with self._lock:
            return self._cpu_metadata

    def get_net_cache(self):
        with self._lock:
            return self._net_cache, self._sample_error

    def get_latency(self):
        with self._lock:
            return self._latency

    def get_top_processes(self):
        with self._lock:
            return self._top_processes

    def get_disks(self):
        with self._lock:
            return self._disk_cache


# Global instance
sampler = SystemSampler()

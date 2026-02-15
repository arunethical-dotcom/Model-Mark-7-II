"""
JARVIIS Resource Monitor
Lightweight observability via OS-level probes.

Architecture Choice: OS-Level Probes (psutil-style)
--------------------------------------------------
Evaluated:
- Inline measurement → Invasive, affects behavior
- Background monitoring → Adds threads, complexity
- OS-level probes → ✅ CHOSEN

Why OS-Level Probes?
- Synchronous snapshots on demand
- No background threads
- Cross-platform (Windows/Linux/Mac)
- Minimal overhead
- No state to maintain

Design Principle:
- Monitoring must never affect system behavior
- Cheap to call, safe to skip
- Returns snapshots, doesn't store history
"""

import os
import time
import sys
from typing import Dict, Any, Optional
from datetime import datetime


class ResourceMonitor:
    """
    Lightweight resource monitoring.
    
    Responsibilities:
    - Measure RAM usage
    - Measure CPU usage
    - Track response latency
    - Return snapshots on demand
    
    Does NOT:
    - Run in background (no threads)
    - Store history (stateless snapshots)
    - Perform heavy profiling
    - Affect system behavior
    
    Philosophy: Observe, don't interfere.
    """
    
    def __init__(self):
        """Initialize resource monitor."""
        self._start_time = time.time()
        self._snapshot_count = 0
        
        # Try to import psutil if available (optional dependency)
        self._psutil_available = False
        try:
            import psutil
            self._psutil = psutil
            self._psutil_available = True
            self._process = psutil.Process(os.getpid())
        except ImportError:
            self._psutil = None
            self._process = None
            print("[MONITOR] psutil not available - using fallback monitoring")
    
    def get_snapshot(self) -> Dict[str, Any]:
        """
        Get current resource snapshot.
        
        Returns:
            Dictionary with current resource metrics
        """
        self._snapshot_count += 1
        
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'snapshot_count': self._snapshot_count,
            'uptime_seconds': time.time() - self._start_time,
        }
        
        # Add resource metrics
        if self._psutil_available:
            snapshot.update(self._get_psutil_metrics())
        else:
            snapshot.update(self._get_fallback_metrics())
        
        return snapshot
    
    def measure_latency(self, start_time: float) -> float:
        """
        Measure latency from start time.
        
        Args:
            start_time: Time from time.time()
            
        Returns:
            Latency in milliseconds
        """
        latency_ms = (time.time() - start_time) * 1000
        return round(latency_ms, 2)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            'snapshot_count': self._snapshot_count,
            'uptime_seconds': round(time.time() - self._start_time, 2),
            'psutil_available': self._psutil_available,
            'monitoring_mode': 'psutil' if self._psutil_available else 'fallback'
        }
    
    # ========================================================================
    # psutil-based Metrics (Accurate)
    # ========================================================================
    
    def _get_psutil_metrics(self) -> Dict[str, Any]:
        """Get resource metrics using psutil."""
        try:
            # Memory info
            mem_info = self._process.memory_info()
            ram_mb = mem_info.rss / (1024 * 1024)  # Convert bytes to MB
            
            # CPU usage (requires interval or non-blocking)
            cpu_percent = self._process.cpu_percent(interval=None)
            
            # System-wide metrics
            system_mem = self._psutil.virtual_memory()
            
            return {
                'ram_usage_mb': round(ram_mb, 2),
                'cpu_percent': round(cpu_percent, 2),
                'system_ram_available_mb': round(system_mem.available / (1024 * 1024), 2),
                'system_ram_percent': system_mem.percent,
                'thread_count': self._process.num_threads(),
            }
            
        except Exception as e:
            print(f"[MONITOR] psutil error: {e}")
            return self._get_fallback_metrics()
    
    # ========================================================================
    # Fallback Metrics (Basic)
    # ========================================================================
    
    def _get_fallback_metrics(self) -> Dict[str, Any]:
        """Get basic metrics without psutil."""
        # Very basic fallback - platform-dependent
        try:
            # Python memory tracking (approximate)
            import gc
            gc.collect()
            
            # Get sys info
            ram_info = {
                'python_version': sys.version.split()[0],
                'platform': sys.platform,
            }
            
            # Try to get process info from /proc (Linux only)
            if sys.platform == 'linux':
                try:
                    with open(f'/proc/{os.getpid()}/status', 'r') as f:
                        for line in f:
                            if line.startswith('VmRSS:'):
                                kb = int(line.split()[1])
                                ram_info['ram_usage_mb'] = round(kb / 1024, 2)
                                break
                except:
                    pass
            
            return ram_info
            
        except Exception as e:
            print(f"[MONITOR] Fallback metrics error: {e}")
            return {'error': 'Metrics unavailable'}
    
    def check_resource_limits(
        self,
        max_ram_mb: int = 512,
        max_cpu_percent: float = 80.0
    ) -> Dict[str, Any]:
        """
        Check if resources are within acceptable limits.
        
        Args:
            max_ram_mb: Maximum RAM in MB
            max_cpu_percent: Maximum CPU percentage
            
        Returns:
            Dictionary with check results
        """
        snapshot = self.get_snapshot()
        
        ram_usage = snapshot.get('ram_usage_mb', 0)
        cpu_usage = snapshot.get('cpu_percent', 0)
        
        return {
            'timestamp': snapshot['timestamp'],
            'ram_ok': ram_usage <= max_ram_mb if ram_usage else True,
            'cpu_ok': cpu_usage <= max_cpu_percent if cpu_usage else True,
            'ram_usage_mb': ram_usage,
            'cpu_percent': cpu_usage,
            'ram_limit_mb': max_ram_mb,
            'cpu_limit_percent': max_cpu_percent,
        }


# ============================================================================
# Optional: Install psutil for better monitoring
# ============================================================================
# pip install psutil --break-system-packages
#
# Without psutil, monitoring still works but with reduced metrics.
# This is acceptable for Phase 2.

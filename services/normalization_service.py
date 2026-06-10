import re
from typing import Optional
from services.ingestion_service import RawAsset

class NormalizedAsset:
    def __init__(
        self,
        external_id: Optional[str],
        hostname: Optional[str],
        ip_address: Optional[str],
        cpu: Optional[int],
        ram_gb: Optional[int],
        os: Optional[str],
        status: Optional[str]
    ):
        self.external_id = external_id
        self.hostname = hostname
        self.ip_address = ip_address
        self.cpu = cpu
        self.ram_gb = ram_gb
        self.os = os
        self.status = status

    def to_dict(self) -> dict:
        return {
            "external_id": self.external_id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "cpu": self.cpu,
            "ram_gb": self.ram_gb,
            "os": self.os,
            "status": self.status
        }

class NormalizationService:
    @staticmethod
    def normalize_hostname(hostname: Optional[str]) -> Optional[str]:
        if not hostname:
            return None
        return hostname.strip().lower()

    @staticmethod
    def normalize_ip(ip: Optional[str]) -> Optional[str]:
        if not ip:
            return None
        return ip.strip()

    @staticmethod
    def normalize_ram(ram: Optional[float]) -> Optional[int]:
        """
        Normalizes RAM to integer GB.
        If ram > 256, assumes MB and divides by 1024.
        Otherwise, rounds to closest integer.
        """
        if ram is None:
            return None
        if ram > 256:
            # Assume it's in MB (e.g. 8192, 16384)
            return int(round(ram / 1024.0))
        return int(round(ram))

    @staticmethod
    def normalize_cpu(cpu: Optional[int]) -> Optional[int]:
        if cpu is None:
            return None
        return int(cpu)

    @staticmethod
    def normalize_os(os_name: Optional[str]) -> Optional[str]:
        """
        Normalizes OS strings into standardized names.
        Examples:
          - "Ubuntu 22.04.3 LTS" -> "Ubuntu 22.04"
          - "CentOS Linux 7 (Core)" -> "CentOS 7"
          - "Windows Server 2019 Datacenter" -> "Windows Server 2019"
        """
        if not os_name:
            return "Unknown OS"
            
        os_clean = os_name.strip()
        os_lower = os_clean.lower()
        
        # Windows Server checks
        if "windows" in os_lower and "server" in os_lower:
            match = re.search(r"server\s+(\d{4})", os_lower)
            if match:
                return f"Windows Server {match.group(1)}"
            return "Windows Server"
            
        # Ubuntu checks
        if "ubuntu" in os_lower:
            match = re.search(r"(\d{2}\.\d{2})", os_lower)
            if match:
                return f"Ubuntu {match.group(1)}"
            return "Ubuntu"
            
        # CentOS checks
        if "centos" in os_lower:
            match = re.search(r"(?:centos|release)\s*(\d)", os_lower)
            if match:
                return f"CentOS {match.group(1)}"
            return "CentOS"
            
        # RedHat / RHEL checks
        if "redhat" in os_lower or "red hat" in os_lower or "rhel" in os_lower:
            match = re.search(r"(?:rhel|enterprise|linux)\s*(\d)", os_lower)
            if match:
                return f"RHEL {match.group(1)}"
            return "RHEL"
            
        # Debian checks
        if "debian" in os_lower:
            match = re.search(r"debian\s*(\d+)", os_lower)
            if match:
                return f"Debian {match.group(1)}"
            return "Debian"
            
        return os_clean

    @staticmethod
    def normalize_status(status: Optional[str]) -> Optional[str]:
        """
        Normalizes operational statuses to Active or Inactive.
        """
        if not status:
            return "Active"  # Default assumption if missing
            
        status_lower = status.strip().lower()
        active_terms = {"active", "online", "running", "up", "enabled", "prod"}
        inactive_terms = {"inactive", "offline", "stopped", "down", "disabled", "decommissioned"}
        
        if status_lower in active_terms:
            return "Active"
        if status_lower in inactive_terms:
            return "Inactive"
            
        return status.strip().capitalize()

    @classmethod
    def normalize_asset(cls, raw: RawAsset) -> NormalizedAsset:
        """
        Normalizes all fields of a RawAsset into a NormalizedAsset object.
        """
        return NormalizedAsset(
            external_id=raw.external_id.strip() if raw.external_id else None,
            hostname=cls.normalize_hostname(raw.hostname),
            ip_address=cls.normalize_ip(raw.ip_address),
            cpu=cls.normalize_cpu(raw.cpu),
            ram_gb=cls.normalize_ram(raw.ram_gb),
            os=cls.normalize_os(raw.os),
            status=cls.normalize_status(raw.status)
        )

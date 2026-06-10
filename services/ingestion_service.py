import csv
import json
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RawAsset(BaseModel):
    external_id: Optional[str] = Field(default=None, description="Unique identifier of the asset")
    hostname: Optional[str] = Field(default=None, description="System hostname")
    ip_address: Optional[str] = Field(default=None, description="IP address of the asset")
    cpu: Optional[int] = Field(default=None, description="Number of CPU cores")
    ram_gb: Optional[float] = Field(default=None, description="RAM size in GB or MB (normalized later)")
    os: Optional[str] = Field(default=None, description="Operating System description")
    status: Optional[str] = Field(default=None, description="Operational status")

class IngestionService:
    @staticmethod
    def _map_headers(headers: List[str]) -> Dict[str, int]:
        """
        Maps column headers to standard field indices.
        Case-insensitive and handles common spelling variants.
        """
        mapping = {}
        for idx, h in enumerate(headers):
            h_clean = h.strip().lower().replace("_", "").replace("-", "")
            if h_clean in ("id", "assetid", "externalid"):
                mapping["external_id"] = idx
            elif h_clean in ("hostname", "host", "servername", "name"):
                mapping["hostname"] = idx
            elif h_clean in ("ipaddress", "ip", "address"):
                mapping["ip_address"] = idx
            elif h_clean in ("cpu", "cpucores", "cores"):
                mapping["cpu"] = idx
            elif h_clean in ("ram", "ramgb", "rammb", "memory", "ramsize"):
                mapping["ram_gb"] = idx
            elif h_clean in ("os", "operatingsystem", "osname", "osversion"):
                mapping["os"] = idx
            elif h_clean in ("status", "state", "operationalstatus"):
                mapping["status"] = idx
        return mapping

    @staticmethod
    def _parse_csv_content(content: str) -> List[RawAsset]:
        """
        Synchronous helper function to parse CSV string.
        """
        parsed_assets = []
        lines = content.splitlines()
        if not lines:
            return parsed_assets
            
        reader = csv.reader(lines)
        try:
            headers = next(reader)
        except StopIteration:
            return parsed_assets
            
        mapping = IngestionService._map_headers(headers)
        
        # Verify that we can at least resolve critical fields like ID or IP
        if "external_id" not in mapping and "ip_address" not in mapping and "hostname" not in mapping:
            raise ValueError("Invalid CSV structure: Could not identify asset identifier fields (id, ip, hostname).")
            
        for row_num, row in enumerate(reader, start=2):
            if not row or all(cell.strip() == "" for cell in row):
                continue
            
            data = {}
            for field, idx in mapping.items():
                if idx < len(row):
                    val = row[idx].strip()
                    data[field] = val if val != "" else None
            
            # Map RAM and CPU to float/int if present to prevent validation failure in RawAsset
            if data.get("cpu") is not None:
                try:
                    data["cpu"] = int(float(data["cpu"]))
                except ValueError:
                    data["cpu"] = None
            if data.get("ram_gb") is not None:
                try:
                    data["ram_gb"] = float(data["ram_gb"])
                except ValueError:
                    data["ram_gb"] = None
                    
            try:
                asset = RawAsset(**data)
                parsed_assets.append(asset)
            except Exception as e:
                # Log parsing warning for specific row and continue
                print(f"Skipping CSV row {row_num} due to validation error: {e}")
                
        return parsed_assets

    @staticmethod
    def _map_json_record(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps dictionary fields of JSON to standard RawAsset fields.
        """
        key_mappings = {
            "external_id": ("id", "asset_id", "assetid", "external_id", "externalid"),
            "hostname": ("hostname", "host", "server_name", "name", "servername"),
            "ip_address": ("ip_address", "ip", "ipaddress", "address"),
            "cpu": ("cpu", "cpu_cores", "cores", "cpucores"),
            "ram_gb": ("ram", "ram_gb", "ram_mb", "memory", "ramsize", "ram_size"),
            "os": ("os", "operating_system", "os_name", "osversion", "os_version"),
            "status": ("status", "state", "operationalstatus")
        }
        
        mapped = {}
        for std_key, alternatives in key_mappings.items():
            for alt in alternatives:
                if alt in item:
                    val = item[alt]
                    if isinstance(val, str):
                        val = val.strip()
                        if val == "":
                            val = None
                    mapped[std_key] = val
                    break
        return mapped

    @classmethod
    async def parse_cmdb_csv(cls, filepath: str) -> List[RawAsset]:
        """
        Asynchronously reads and parses a CMDB CSV inventory file.
        """
        def read_file():
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
                
        content = await asyncio.to_thread(read_file)
        return await asyncio.to_thread(cls._parse_csv_content, content)

    @classmethod
    async def parse_actual_json(cls, filepath: str) -> List[RawAsset]:
        """
        Asynchronously reads and parses an Actual Infrastructure JSON file.
        """
        def read_file():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
                
        data = await asyncio.to_thread(read_file)
        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top-level structure must be a list of asset objects.")
            
        parsed_assets = []
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                continue
                
            mapped_item = cls._map_json_record(item)
            
            # Type casting checks
            if mapped_item.get("cpu") is not None:
                try:
                    mapped_item["cpu"] = int(float(mapped_item["cpu"]))
                except ValueError:
                    mapped_item["cpu"] = None
            if mapped_item.get("ram_gb") is not None:
                try:
                    mapped_item["ram_gb"] = float(mapped_item["ram_gb"])
                except ValueError:
                    mapped_item["ram_gb"] = None
                    
            try:
                asset = RawAsset(**mapped_item)
                parsed_assets.append(asset)
            except Exception as e:
                print(f"Skipping JSON item at index {idx} due to validation error: {e}")
                
        return parsed_assets

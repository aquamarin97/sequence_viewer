# file_io/sqx/block_types/project_meta.py
from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field
def _decode_sqx_string(data: bytes) -> str:
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('latin-1')

@dataclass
class ProjectMeta:
    """Metadata stored in the SQX PROJECT_META block."""
    project_name: str = ""
    app_version: str = "0.1.0"
    created_at: int = field(default_factory=lambda: int(time.time()))
    modified_at: int = field(default_factory=lambda: int(time.time()))

    def serialize(self) -> bytes:
        """Serialize to PROJECT_META block bytes."""
        buf = bytearray()
        buf += struct.pack('<qq', self.created_at, self.modified_at)
        av = self.app_version.encode('utf-8')
        buf += struct.pack('<H', len(av)) + av
        pn = self.project_name.encode('utf-8')
        buf += struct.pack('<H', len(pn)) + pn
        return bytes(buf)

    @staticmethod
    def deserialize(data: bytes | bytearray | memoryview) -> ProjectMeta:
        """Deserialize from PROJECT_META block bytes."""
        offset = 0
        created_at, modified_at = struct.unpack_from('<qq', data, offset)
        offset += 16
        av_len = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        app_version = _decode_sqx_string(bytes(data[offset:offset + av_len]))
        offset += av_len
        pn_len = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        project_name = _decode_sqx_string(bytes(data[offset:offset + pn_len]))

        return ProjectMeta(
            project_name=project_name,
            app_version=app_version,
            created_at=created_at,
            modified_at=modified_at,
        )

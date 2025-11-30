import struct
import zstandard as zstd
import brotli
import sys
from typing import Any, Dict
from .core import *
from .schema import Schema, Field

class AdvancedSerializer:
    def __init__(self):
        # Pre-compile structs for performance
        self._struct_H = struct.Struct(">H")
        self._struct_I = struct.Struct(">I")
        self._struct_q = struct.Struct(">q")
        self._struct_d = struct.Struct(">d")
        self._struct_header = struct.Struct(">4sH") # Magic + Version
        
        # Cache codecs
        self._zstd_compress = zstd.compress
        self._zstd_decompress = zstd.decompress
        self._brotli_compress = brotli.compress
        self._brotli_decompress = brotli.decompress

    def serialize(self, schema: Schema, obj: Dict[str, Any]) -> bytes:
        out = bytearray()
        
        # Write header: Magic (4) + Version (2)
        out += self._struct_header.pack(b'AXSR', schema.version)

        # Localize lookups
        pack_H = self._struct_H.pack
        pack_I = self._struct_I.pack
        pack_q = self._struct_q.pack
        pack_d = self._struct_d.pack
        
        # Field loop
        for field in schema.fields:
            value = obj.get(field.name)
            
            if value is None:
                if field.optional:
                    # Skip optional fields if None (assuming strict order is not required for optional? 
                    # Actually, we decided strict order for MVP. So we must write something or handle it.)
                    # For performance, let's assume we write empty bytes for now if optional.
                    encoded = b''
                else:
                     raise ValueError(f"Missing required field: {field.name}")
            else:
                # INLINE _encode_value logic
                # 1. Primitive Encode
                ftype = field.type
                if ftype == INT:
                    raw = pack_q(value)
                elif ftype == FLOAT:
                    raw = pack_d(value)
                elif ftype == STRING:
                    b = value.encode('utf8')
                    raw = pack_I(len(b)) + b
                elif ftype == BOOL:
                    raw = b'\x01' if value else b'\x00'
                elif ftype == LIST:
                    raw = self._encode_list(value)
                else:
                    raise NotImplementedError(f"Unknown type: {ftype}")

                # 2. Compression
                codec = field.codec
                if codec == CODEC_NONE:
                    encoded = raw
                elif codec == CODEC_ZSTD:
                    encoded = self._zstd_compress(raw)
                elif codec == CODEC_BROTLI:
                    encoded = self._brotli_compress(raw)
                else:
                    raise NotImplementedError(f"Unknown codec: {codec}")

            # Field header: type + length
            out += pack_H(field.type)
            out += pack_I(len(encoded))
            out += encoded

        return bytes(out)

    def deserialize(self, schema: Schema, data: bytes) -> Dict[str, Any]:
        obj = {}
        offset = 0
        
        # Read Header
        if data[0:4] != b'AXSR':
             raise ValueError("Invalid magic bytes")
        offset += 4
        
        version = self._struct_H.unpack_from(data, offset)[0]
        offset += 2
        
        if version != schema.version:
             pass

        # Localize lookups
        unpack_H = self._struct_H.unpack_from
        unpack_I = self._struct_I.unpack_from
        unpack_q = self._struct_q.unpack_from
        unpack_d = self._struct_d.unpack_from
        
        # Read Fields
        for field in schema.fields:
            if offset >= len(data):
                break
            
            # Read Field Header
            ftype = unpack_H(data, offset)[0]
            offset += 2
            length = unpack_I(data, offset)[0]
            offset += 4
            
            # Read Content
            content = data[offset:offset+length]
            offset += length
            
            if length == 0 and field.optional:
                obj[field.name] = None
                continue
                
            # INLINE _decode_value logic
            # 1. Decompress
            codec = field.codec
            if codec == CODEC_NONE:
                raw = content
            elif codec == CODEC_ZSTD:
                raw = self._zstd_decompress(content)
            elif codec == CODEC_BROTLI:
                raw = self._brotli_decompress(content)
            else:
                 raise NotImplementedError(f"Unknown codec: {codec}")
            
            # 2. Primitive Decode
            if ftype == INT:
                val = unpack_q(raw)[0]
            elif ftype == FLOAT:
                val = unpack_d(raw)[0]
            elif ftype == BOOL:
                val = (raw == b'\x01')
            elif ftype == STRING:
                l = unpack_I(raw, 0)[0]
                val = raw[4:4+l].decode('utf8')
            elif ftype == LIST:
                val = self._decode_list(raw)
            else:
                raise NotImplementedError(f"Unknown type: {ftype}")
                
            obj[field.name] = val
                
        return obj

    # Kept for compatibility if needed, but unused in main path
    def _encode_value(self, field: Field, value: Any) -> bytes:
        pass 
    def _decode_value(self, field: Field, data: bytes) -> Any:
        pass
    def _primitive_encode(self, t: int, v: Any) -> bytes:
        # Helper for list encoding
        if t == INT:
            return self._struct_q.pack(v)
        if t == FLOAT:
            return self._struct_d.pack(v)
        if t == BOOL:
            return b'\x01' if v else b'\x00'
        if t == STRING:
            b = v.encode('utf8')
            return self._struct_I.pack(len(b)) + b
        if t == LIST:
            return self._encode_list(v)
        raise NotImplementedError

    def _primitive_decode(self, t: int, data: bytes) -> Any:
        # Helper for list decoding
        if t == INT:
            return self._struct_q.unpack(data)[0]
        if t == FLOAT:
            return self._struct_d.unpack(data)[0]
        if t == BOOL:
            return data == b'\x01'
        if t == STRING:
            l = self._struct_I.unpack_from(data, 0)[0]
            return data[4:4+l].decode('utf8')
        if t == LIST:
            return self._decode_list(data)
        raise NotImplementedError

    def _encode_list(self, v: list) -> bytes:
        out = bytearray()
        count = len(v)
        out += struct.pack(">I", count)
        
        if count == 0:
            out += b'\x00' # Generic empty
            return bytes(out)

        # Heuristic for packed arrays
        first = v[0]
        if isinstance(first, int) and all(isinstance(x, int) for x in v):
            # Packed Int64
            out += b'\x01' # Type: Packed Int
            # Use struct.pack for speed on small/medium lists, or array for large
            # struct.pack with *v is fast but has argument limit? 
            # safe to use array
            import array
            # Big endian signed long long
            a = array.array('q', v)
            if sys.byteorder == 'little':
                a.byteswap()
            out += a.tobytes()
        elif isinstance(first, float) and all(isinstance(x, float) for x in v):
            # Packed Float64
            out += b'\x02' # Type: Packed Float
            import array
            a = array.array('d', v)
            if sys.byteorder == 'little':
                a.byteswap()
            out += a.tobytes()
        else:
            # Generic
            out += b'\x00' # Type: Generic
            for item in v:
                # Infer type
                if isinstance(item, int):
                    t = INT
                elif isinstance(item, float):
                    t = FLOAT
                elif isinstance(item, str):
                    t = STRING
                elif isinstance(item, bool):
                    t = BOOL
                elif isinstance(item, list):
                    t = LIST
                else:
                    raise ValueError(f"Unsupported list item type: {type(item)}")
                
                encoded_item = self._primitive_encode(t, item)
                out += struct.pack(">H", t)
                out += struct.pack(">I", len(encoded_item))
                out += encoded_item
        return bytes(out)

    def _decode_list(self, data: bytes) -> list:
        count = struct.unpack(">I", data[:4])[0]
        encoding_type = data[4]
        offset = 5
        
        if encoding_type == 1: # Packed Int
            import array
            # 8 bytes per int
            byte_len = count * 8
            raw = data[offset:offset+byte_len]
            a = array.array('q')
            a.frombytes(raw)
            if sys.byteorder == 'little':
                a.byteswap()
            return a.tolist()
            
        elif encoding_type == 2: # Packed Float
            import array
            byte_len = count * 8
            raw = data[offset:offset+byte_len]
            a = array.array('d')
            a.frombytes(raw)
            if sys.byteorder == 'little':
                a.byteswap()
            return a.tolist()
            
        else: # Generic
            items = []
            for _ in range(count):
                t = struct.unpack(">H", data[offset:offset+2])[0]
                offset += 2
                l = struct.unpack(">I", data[offset:offset+4])[0]
                offset += 4
                val_data = data[offset:offset+l]
                offset += l
                items.append(self._primitive_decode(t, val_data))
            return items

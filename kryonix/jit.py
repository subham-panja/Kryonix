import struct
from typing import Any, Dict
from .core import *
from .schema import Schema

class JITCompiler:
    def __init__(self):
        self._cache = {}

    def compile_serializer(self, schema: Schema):
        if schema.name in self._cache:
            return self._cache[schema.name]

        lines = []
        lines.append(f"def serialize_{schema.name}(obj, pack_funcs):")
        lines.append("    out = bytearray()")
        lines.append("    pack_header = pack_funcs['header']")
        lines.append("    pack_struct = pack_funcs['struct_pack']") # Generic struct.pack
        
        # Header
        lines.append(f"    out += pack_header(b'AXSR', {schema.version})")
        
        # Group adjacent primitives
        # We need to handle:
        # 1. Value retrieval
        # 2. Packing
        # 3. Field Headers (Type + Len) - This is tricky.
        # The current format is: [Type][Len][Value] [Type][Len][Value] ...
        # If we merge values, we break the format?
        # No, the format is fixed. We just want to emit bytes faster.
        # We can pack [Type][Len][Value][Type][Len][Value] all at once!
        # But Length of Value depends on Value?
        # For primitives (INT, FLOAT, BOOL), length is FIXED.
        # INT = 8 bytes. FLOAT = 8 bytes. BOOL = 1 byte.
        # So we CAN merge them!
        
        # We need to build a format string and a list of values.
        
        current_fmt = ">"
        current_args = []
        
        def flush_pack():
            nonlocal current_fmt, current_args
            if len(current_fmt) > 1:
                args_str = ", ".join(current_args)
                lines.append(f"    out += pack_struct('{current_fmt}', {args_str})")
            current_fmt = ">"
            current_args = []

        for field in schema.fields:
            name = field.name
            ftype = field.type
            
            # Get value
            lines.append(f"    v_{name} = obj.get('{name}')")
            if not field.optional:
                lines.append(f"    if v_{name} is None: raise ValueError('Missing {name}')")
            
            # Check if mergeable primitive
            # We need to pack: Type(H), Len(I), Value(?)
            # INT: H, I, q
            # FLOAT: H, I, d
            # BOOL: H, I, c
            
            if ftype == INT and field.codec == CODEC_NONE:
                current_fmt += "HIq"
                current_args.append(str(INT))
                current_args.append("8") # Len of int64
                current_args.append(f"v_{name}")
            elif ftype == FLOAT and field.codec == CODEC_NONE:
                current_fmt += "HId"
                current_args.append(str(FLOAT))
                current_args.append("8")
                current_args.append(f"v_{name}")
            elif ftype == BOOL and field.codec == CODEC_NONE:
                current_fmt += "HIB" # B for unsigned char (byte)
                current_args.append(str(BOOL))
                current_args.append("1")
                current_args.append(f"1 if v_{name} else 0")
            else:
                # Flush pending
                flush_pack()
                
                # Handle complex/compressed types
                if ftype == STRING:
                    lines.append(f"    b_{name} = v_{name}.encode('utf8')")
                    lines.append(f"    l_{name} = len(b_{name})")
                    # Pack Header + Len + String
                    # We can pack Header + Len + StringLen + String
                    # Header: Type(H), Len(I)
                    # Value: StringLen(I) + String(s)
                    # Total Len = 4 + StringLen
                    lines.append(f"    out += pack_struct('>HI', {STRING}, 4 + l_{name})")
                    lines.append(f"    out += pack_struct('>I', l_{name})")
                    lines.append(f"    out += b_{name}")
                elif ftype == LIST:
                     # Fallback
                     lines.append(f"    encoded = pack_funcs['list'](v_{name})")
                     lines.append(f"    out += pack_struct('>HI', {LIST}, len(encoded))")
                     lines.append(f"    out += encoded")
                else:
                     pass # TODO

        flush_pack()
        lines.append("    return bytes(out)")
        
        code = "\n".join(lines)
        # print(code)
        
        namespace = {}
        exec(code, namespace)
        func = namespace[f"serialize_{schema.name}"]
        self._cache[schema.name] = func
        return func

    def compile_deserializer(self, schema: Schema):
        # Similar logic for deserializer
        pass

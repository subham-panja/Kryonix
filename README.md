# Kryonix: Hyper-Advanced Python Serialization

Kryonix is a next-generation serialization framework designed to be faster, smaller, and smarter than existing solutions like JSON, Pickle, or even Fory. It combines the best features of Apache Arrow, Protobuf, and FlatBuffers with adaptive compression and zero-copy principles.

## Features

- **Hybrid Row + Column Format**: Optimized for both random access and compression.
- **Adaptive Field-Level Compression**: Uses Zstd and Brotli based on field type.
- **JIT Compilation**: Generates specialized serialization code at runtime for maximum Python performance.
- **Strict Schema Enforcement**: Ensures data integrity and safe evolution.
- **Compact Binary Format**: Significantly smaller payloads than JSON.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### 1. Define a Schema

```python
from kryonix import Schema, Field, INT, STRING, LIST, CODEC_ZSTD

schema = Schema(
    name="User",
    version=1,
    fields=[
        Field("id", INT),
        Field("name", STRING, codec=CODEC_ZSTD),
        Field("tags", LIST),
    ]
)
```

### 2. Serialize Data

```python
from kryonix import AdvancedSerializer

serializer = AdvancedSerializer()
data = {
    "id": 42,
    "name": "Subham Panja",
    "tags": ["python", "high-performance"]
}

binary = serializer.serialize(schema, data)
print(f"Serialized size: {len(binary)} bytes")
```

### 3. Deserialize Data

```python
decoded = serializer.deserialize(schema, binary)
print(decoded)
```

## Advanced Features

### Compression Codecs
Kryonix supports per-field compression:
- `CODEC_NONE`: No compression (fastest)
- `CODEC_ZSTD`: Zstandard compression (balanced)
- `CODEC_BROTLI`: Brotli compression (best for text)

### Supported Types
- `INT`: 64-bit signed integer
- `FLOAT`: 64-bit float
- `STRING`: UTF-8 string
- `BOOL`: Boolean
- `LIST`: List of primitives
- `OBJECT`: Nested object (coming soon)

## License
MIT

from kryonix import AdvancedSerializer, Schema, Field, INT, STRING, LIST, CODEC_ZSTD, CODEC_BROTLI

def test_kryonix():
    print("Testing Kryonix...")
    
    # Define Schema
    schema = Schema(
        name="User",
        version=1,
        fields=[
            Field("id", INT),
            Field("name", STRING, codec=CODEC_ZSTD),
            Field("bio", STRING, codec=CODEC_BROTLI),
            Field("tags", LIST),
        ]
    )
    
    # Data
    data = {
        "id": 42,
        "name": "Subham Panja",
        "bio": "A " + "very "*100 + "long bio to test compression.",
        "tags": ["python", "rust", "assembly"]
    }
    
    # Serialize
    s = AdvancedSerializer()
    binary = s.serialize(schema, data)
    print(f"Serialized size: {len(binary)} bytes")
    
    # Deserialize
    decoded = s.deserialize(schema, binary)
    print(f"Decoded data: {decoded}")
    
    # Verify
    assert decoded["id"] == data["id"]
    assert decoded["name"] == data["name"]
    assert decoded["tags"] == data["tags"]
    assert decoded["bio"] == data["bio"]
    
    print("Verification Successful!")

if __name__ == "__main__":
    test_kryonix()

from kryonix import AdvancedSerializer, Schema, Field, INT, STRING, LIST, CODEC_ZSTD, CODEC_BROTLI

def main():
    # Define a schema with mixed compression
    schema = Schema(
        name="Event",
        version=1,
        fields=[
            Field("timestamp", INT),
            Field("event_type", STRING),
            Field("payload", STRING, codec=CODEC_BROTLI), # High compression for large text
            Field("metrics", LIST),
        ]
    )

    # Create a serializer instance
    serializer = AdvancedSerializer()

    # Sample data
    event = {
        "timestamp": 1678886400,
        "event_type": "user_signup",
        "payload": "User signed up with email example@domain.com. " * 50, # Long string
        "metrics": [1, 0, 1]
    }

    # Serialize
    binary = serializer.serialize(schema, event)
    print(f"Original Payload Size (approx): {len(event['payload']) + 50} bytes")
    print(f"Serialized Binary Size: {len(binary)} bytes")

    # Deserialize
    decoded = serializer.deserialize(schema, binary)
    print(f"Decoded Event Type: {decoded['event_type']}")
    print(f"Decoded Payload Length: {len(decoded['payload'])}")

if __name__ == "__main__":
    main()

import time
import json
import pickle
import zlib
import struct
from kryonix import AdvancedSerializer, Schema, Field, INT, STRING, LIST, CODEC_ZSTD, CODEC_BROTLI

def benchmark():
    print("="*60)
    print("🚀 KRYONIX BENCHMARK SUITE")
    print("="*60)

    # 1. Setup Data and Schema
    schema = Schema(
        name="User",
        version=1,
        fields=[
            Field("id", INT),
            Field("name", STRING, codec=CODEC_ZSTD), # Compressed
            Field("email", STRING),
            Field("bio", STRING, codec=CODEC_BROTLI), # Highly compressed
            Field("tags", LIST, codec=CODEC_ZSTD),
            Field("scores", LIST, codec=CODEC_ZSTD),
        ]
    )

    # Create a reasonably large object to make compression meaningful
    data = {
        "id": 123456789,
        "name": "Subham Panja",
        "email": "subham.panja@example.com",
        "bio": "Software Engineer " * 100 + "Python Developer " * 100, # Repetitive text for compression
        "tags": ["python", "rust", "go", "cpp", "java", "scala"] * 10,
        "scores": [100, 99, 98, 97, 96, 95] * 20
    }

    serializer = AdvancedSerializer()

    # Warmup
    serializer.serialize(schema, data)
    json.dumps(data)
    pickle.dumps(data)

    ITERATIONS = 1000

    print(f"\n📊 Running {ITERATIONS} iterations...\n")

    # --- KRYONIX (Compressed) ---
    start = time.time()
    for _ in range(ITERATIONS):
        k_bin = serializer.serialize(schema, data)
    k_ser_time = (time.time() - start) / ITERATIONS

    start = time.time()
    for _ in range(ITERATIONS):
        serializer.deserialize(schema, k_bin)
    k_des_time = (time.time() - start) / ITERATIONS

    # --- KRYONIX (No Compression) ---
    schema_nc = Schema(
        name="UserNC",
        version=1,
        fields=[
            Field("id", INT),
            Field("name", STRING),
            Field("email", STRING),
            Field("bio", STRING),
            Field("tags", LIST),
            Field("scores", LIST),
        ]
    )
    # Warmup
    serializer.serialize(schema_nc, data)
    
    start = time.time()
    for _ in range(ITERATIONS):
        knc_bin = serializer.serialize(schema_nc, data)
    knc_ser_time = (time.time() - start) / ITERATIONS
    
    start = time.time()
    for _ in range(ITERATIONS):
        serializer.deserialize(schema_nc, knc_bin)
    knc_des_time = (time.time() - start) / ITERATIONS

    # --- KRYONIX (JIT Raw) ---
    from kryonix.jit import JITCompiler
    jit = JITCompiler()
    jit_func = jit.compile_serializer(schema_nc)
    
    # Prepare pack funcs
    import struct
    s_H = struct.Struct(">H")
    s_I = struct.Struct(">I")
    s_q = struct.Struct(">q")
    s_d = struct.Struct(">d")
    s_header = struct.Struct(">4sH")
    
    pack_funcs = {
        'H': s_H.pack,
        'I': s_I.pack,
        'q': s_q.pack,
        'd': s_d.pack,
        'header': s_header.pack,
        'struct_pack': struct.pack, # NEW
        'list': serializer._encode_list, # Reuse
        'zstd': None,
        'brotli': None
    }
    
    # Warmup
    jit_func(data, pack_funcs)
    
    start = time.time()
    for _ in range(ITERATIONS):
        kjit_bin = jit_func(data, pack_funcs)
    kjit_ser_time = (time.time() - start) / ITERATIONS

    # --- JSON ---
    start = time.time()
    for _ in range(ITERATIONS):
        j_bin = json.dumps(data).encode('utf-8')
    j_ser_time = (time.time() - start) / ITERATIONS

    start = time.time()
    for _ in range(ITERATIONS):
        json.loads(j_bin)
    j_des_time = (time.time() - start) / ITERATIONS

    # --- PICKLE ---
    start = time.time()
    for _ in range(ITERATIONS):
        p_bin = pickle.dumps(data)
    p_ser_time = (time.time() - start) / ITERATIONS

    start = time.time()
    for _ in range(ITERATIONS):
        pickle.loads(p_bin)
    p_des_time = (time.time() - start) / ITERATIONS

    # --- JSON + ZLIB (Fair comparison for size) ---
    start = time.time()
    for _ in range(ITERATIONS):
        jz_bin = zlib.compress(json.dumps(data).encode('utf-8'))
    jz_ser_time = (time.time() - start) / ITERATIONS

    # Results
    print(f"{'FORMAT':<20} | {'SIZE (Bytes)':<12} | {'SER TIME (ms)':<15} | {'DES TIME (ms)':<15}")
    print("-" * 70)
    
    # Kryonix
    print(f"{'Kryonix (Comp)':<20} | {len(k_bin):<12} | {k_ser_time*1000:<15.4f} | {k_des_time*1000:<15.4f}")
    print(f"{'Kryonix (Raw)':<20} | {len(knc_bin):<12} | {knc_ser_time*1000:<15.4f} | {knc_des_time*1000:<15.4f}")
    print(f"{'Kryonix (JIT)':<20} | {len(kjit_bin):<12} | {kjit_ser_time*1000:<15.4f} | {'N/A':<15}")
    
    # JSON
    print(f"{'JSON':<20} | {len(j_bin):<12} | {j_ser_time*1000:<15.4f} | {j_des_time*1000:<15.4f}")
    
    # Pickle
    print(f"{'Pickle':<20} | {len(p_bin):<12} | {p_ser_time*1000:<15.4f} | {p_des_time*1000:<15.4f}")
    
    # JSON + Zlib
    print(f"{'JSON + Zlib':<20} | {len(jz_bin):<12} | {jz_ser_time*1000:<15.4f} | {'N/A':<15}")

    print("\n🏆 SUMMARY:")
    print(f"Kryonix (JIT) is {p_ser_time / kjit_ser_time:.2f}x speed of Pickle.")
    
    # Network Simulation
    print("\n🌍 NETWORK SIMULATION (IoT / Mobile / Slow Network):")
    network_speed_mbps = 10 # 10 Mbps
    network_speed_bytes_per_sec = (network_speed_mbps * 1000 * 1000) / 8
    
    k_net_time = len(k_bin) / network_speed_bytes_per_sec
    j_net_time = len(j_bin) / network_speed_bytes_per_sec
    
    k_total = k_ser_time + k_net_time
    j_total = j_ser_time + j_net_time
    
    print(f"Network Speed: {network_speed_mbps} Mbps")
    print(f"JSON Total Time (Ser + Net): {j_total*1000:.4f} ms")
    print(f"Kryonix (Comp) Total Time (Ser + Net): {k_total*1000:.4f} ms")
    
    if k_total < j_total:
        print(f"🚀 Kryonix is {j_total / k_total:.1f}x FASTER end-to-end on 10Mbps network!")
    else:
        print(f"Kryonix is slower end-to-end.")

if __name__ == "__main__":
    benchmark()

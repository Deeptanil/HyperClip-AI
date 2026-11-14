"""
Procedural Sound Effects Generator using pure Python standard library (wave & math).
Generates royalty-free, copyright-free Vine Boom, Pop, and Whoosh SFX instantly.
"""

import os
import wave
import math
import struct
import random

SAMPLE_RATE = 44100

def create_pop_sfx(output_path):
    """Generates a snappy bubble pop sound (0.08s)."""
    duration = 0.08
    num_samples = int(duration * SAMPLE_RATE)
    data = bytearray()
    
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Rapid downward frequency sweep (1200Hz -> 300Hz)
        freq = 1200 - (900 * (t / duration))
        decay = math.exp(-t * 45)
        sample = int(32767 * decay * math.sin(2 * math.pi * freq * t))
        sample = max(-32768, min(32767, sample))
        data.extend(struct.pack('<h', sample))
        
    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data)

def create_whoosh_sfx(output_path):
    """Generates a fast transition whoosh sound (0.28s)."""
    duration = 0.28
    num_samples = int(duration * SAMPLE_RATE)
    data = bytearray()
    
    random.seed(42)
    last_noise = 0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Envelope: rise then fall
        env = math.sin(math.pi * (t / duration)) ** 2
        # Lowpass filtered noise
        raw_noise = random.uniform(-1.0, 1.0)
        filtered = 0.85 * last_noise + 0.15 * raw_noise
        last_noise = filtered
        
        sample = int(32767 * env * filtered * 0.9)
        sample = max(-32768, min(32767, sample))
        data.extend(struct.pack('<h', sample))
        
    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data)

def create_boom_sfx(output_path):
    """Generates a dramatic sub-bass vine-boom impact sound (1.0s)."""
    duration = 1.0
    num_samples = int(duration * SAMPLE_RATE)
    data = bytearray()
    
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Pitch drop: 90Hz dropping to 42Hz
        freq = 90 - (48 * (t / duration))
        env = math.exp(-t * 4.2)
        
        # Fundamental sine + slight 2nd harmonic distortion
        sine1 = math.sin(2 * math.pi * freq * t)
        sine2 = math.sin(4 * math.pi * freq * t) * 0.35
        combined = (sine1 + sine2) * env
        
        # Soft clipping
        clipped = math.tanh(combined * 1.5)
        sample = int(32767 * clipped * 0.95)
        sample = max(-32768, min(32767, sample))
        data.extend(struct.pack('<h', sample))
        
    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data)

def ensure_sfx_library(assets_dir):
    """Ensures pop.wav, whoosh.wav, and boom.wav exist in the directory."""
    os.makedirs(assets_dir, exist_ok=True)
    sfx_paths = {
        "pop": os.path.join(assets_dir, "pop.wav"),
        "whoosh": os.path.join(assets_dir, "whoosh.wav"),
        "boom": os.path.join(assets_dir, "boom.wav")
    }
    
    if not os.path.exists(sfx_paths["pop"]):
        create_pop_sfx(sfx_paths["pop"])
    if not os.path.exists(sfx_paths["whoosh"]):
        create_whoosh_sfx(sfx_paths["whoosh"])
    if not os.path.exists(sfx_paths["boom"]):
        create_boom_sfx(sfx_paths["boom"])
        
    return sfx_paths

if __name__ == "__main__":
    paths = ensure_sfx_library("./assets/sfx")
    print("SFX Library Ready:", paths)

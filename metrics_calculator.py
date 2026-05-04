import os
import numpy as np
from pydub import AudioSegment
from pesq import pesq
from pystoi import stoi

def load_audio_from_path(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")
    
    fext = os.path.splitext(path)[1].lower()
    audio = AudioSegment.from_file(path, format=fext[1:])
    
    # Metrics usually require 16kHz Mono for standardization
    audio = audio.set_frame_rate(16000).set_channels(1)
    
    # Convert to numpy array
    samples = np.array(audio.get_array_of_samples())
    return samples, audio.frame_rate

def get_metrics(ref_path, deg_path):
    # Load both files
    ref_data, rate_ref = load_audio_from_path(ref_path)
    deg_data, rate_deg = load_audio_from_path(deg_path)

    # Ensure they are the same length for the math to work
    min_len = min(len(ref_data), len(deg_data))
    ref_data = ref_data[:min_len].astype(np.float32)
    deg_data = deg_data[:min_len].astype(np.float32)

    # Calculate STOI
    stoi_score = stoi(ref_data, deg_data, rate_ref, extended=False)

    # Calculate PESQ (Wideband)
    # PESQ is very strict: rate must be 8000 or 16000
    pesq_score = pesq(rate_ref, ref_data, deg_data, 'wb')

    return pesq_score, stoi_score
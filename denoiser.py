import noisereduce as nr
from pydub import AudioSegment
import numpy as np
from scipy.signal import butter , lfilter
import os
import io

def getAudioInput(filename):
    """
    Takes a filename, checks if it exists, and returns the filename 
    along with its binary content.
    """
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            content = f.read()
        return filename, content
    else:
        print(f"Error: The file '{filename}' was not found.")
        return None


def butterBandpass(low , high , fs , order=5):
    nf = 0.5*fs
    highCut = high/nf
    lowCut = low/nf

    y , x = butter(order, [lowCut, highCut], btype='band')
    return y,x

def butterBandpassFilter(data, low , high , fs , order=5):
    b, a = butterBandpass(low, high, fs, order=order)
    z = lfilter(b,a,data)
    return z

def removeNoise(dataSample , samplingRate, lowCut=500, highCut=3000):
    dataFloat = dataSample.astype(np.float32)
    noiseRemoved = nr.reduce_noise(dataFloat, samplingRate)
    audioFiltered = butterBandpassFilter(noiseRemoved, lowCut, highCut, samplingRate, order=6)
    return audioFiltered

def amplifyAudio(audio, ampliFactor=5):
    dataFloat = audio.astype(np.float32)
    amplifiedAudio = dataFloat *ampliFactor
    amplifiedAudio = np.clip(amplifiedAudio, -32768, 32767)
    amplifiedAudio = amplifiedAudio.astype(np.int16)
    return amplifiedAudio

def saveAudio(filename, rate, data, ext):
    if data.dtype != np.int16:
        data = np.clip(data, -32768, 32767).astype(np.int16)
    processed_segment = AudioSegment(
        data.tobytes(), 
        frame_rate=rate,
        sample_width=2, 
        channels=1
    )
    processed_segment.export(f"{filename}.{ext}", format=ext)
    print(f"File saved successfully as: {filename}.{ext}")

def denoise_and_save_audio(inp_fname, op_fname_wo_ext):
    extension = inp_fname.split('.')[-1].lower()
    rawAudio = getAudioInput(inp_fname)
    if rawAudio is None:
        raise ValueError("Audio File Not Found!")
    
    fname , audioDataBytes = rawAudio
    fext = os.path.splitext(fname)[1].lower()
    if fext not in ['.wav', '.mp3']:
        raise ValueError("File is not in .mp3 or .wav format!")
    try:
        audio = AudioSegment.from_file(io.BytesIO(audioDataBytes) , format=fext[1:]) 
    except Exception as e:
        raise RuntimeError("Audio couldn't be loaded!", e)

    audio = audio.set_channels(1)
    rate = audio.frame_rate
    data = np.array(audio.get_array_of_samples())

    filterAudio = removeNoise(data, rate)
    ampAudio = amplifyAudio(filterAudio)
    saveAudio(op_fname_wo_ext, rate, ampAudio, extension)

    return extension
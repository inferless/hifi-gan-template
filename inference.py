from __future__ import absolute_import, division, print_function, unicode_literals

import glob
import os
import argparse
import json
import torch
from scipy.io.wavfile import write
from env import AttrDict
from meldataset import mel_spectrogram, MAX_WAV_VALUE, load_wav
from models import Generator

h = None
device = None


def load_checkpoint(filepath, device):
    assert os.path.isfile(filepath)
    print("Loading '{}'".format(filepath))
    checkpoint_dict = torch.load(filepath, map_location=device)
    print("Complete.")
    return checkpoint_dict


def get_mel(x):
    return mel_spectrogram(
        x, h.n_fft, h.num_mels, h.sampling_rate, h.hop_size, h.win_size, h.fmin, h.fmax
    )


def scan_checkpoint(cp_dir, prefix):
    pattern = os.path.join(cp_dir, prefix + "*")
    cp_list = glob.glob(pattern)
    if len(cp_list) == 0:
        return ""
    return sorted(cp_list)[-1]


def inference(checkpoint_file, input_file):
    generator = Generator(h).to(device)

    state_dict_g = load_checkpoint(checkpoint_file, device)
    generator.load_state_dict(state_dict_g["generator"])

    generator.eval()
    generator.remove_weight_norm()
    with torch.no_grad():
        wav, sr = load_wav(input_file)
        wav = wav / MAX_WAV_VALUE
        wav = torch.FloatTensor(wav).to(device)
        x = get_mel(wav.unsqueeze(0))
        y_g_hat = generator(x)
        audio = y_g_hat.squeeze()
        audio = audio * MAX_WAV_VALUE
        audio = audio.cpu().numpy().astype("int16")
        return audio, sr



def initialize_helper(
    checkpoint_file, input_wavs_dir="test_files", output_dir="generated_files"
):
    print("Initializing Inference Process..")

    config_file = os.path.join(os.path.split(checkpoint_file)[0], "config.json")

    with open(config_file) as f:
        data = f.read()

    global h
    json_config = json.loads(data)
    h = AttrDict(json_config)

    torch.manual_seed(h.seed)
    global device
    if torch.cuda.is_available():
        torch.cuda.manual_seed(h.seed)
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")


if __name__ == "__main__":
    initialize_helper("generator_v3")

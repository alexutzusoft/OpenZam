"""
Constellation-based audio fingerprinting (Shazam-style).

Each fingerprint is a list of (hash, anchor_time) pairs. A hash encodes a pair
of spectral peaks (anchor + target) and the time delta between them; the anchor
time is kept so matching can align hashes by a consistent time offset. This is
what allows recognition of short or noisy clips, not just near-identical files.
"""

import numpy as np
import librosa
from scipy.ndimage import maximum_filter
from typing import List, Tuple, Dict, Optional

# STFT parameters (shared by DB build and query so peak coordinates are comparable)
SR = 22050
N_FFT = 1024
HOP_LENGTH = 256

# Peak picking
PEAK_NEIGHBORHOOD = 20          # size of the local-maximum window (freq/time bins)
AMP_MIN_DB = -60.0              # absolute floor: ignore peaks quieter than this (dB below max)
PEAKS_PER_FRAME_BAND = 15       # cap peaks per time band to keep spread even across the track
BAND_SIZE_FRAMES = 43           # ~0.5s bands at 22050/256

# Combinatorial hashing (target zone in front of each anchor)
FAN_VALUE = 15                  # how many forward peaks to pair each anchor with
MIN_DT = 1                      # min time delta between anchor and target (frames)
MAX_DT = 100                    # max time delta (~1.16s); fits in the dt bit-field

# Bit layout for the 32-bit hash: f1(10) | f2(10) | dt(10). N_FFT=1024 -> 513 bins (<1024).
_F_BITS = 10
_DT_BITS = 10
_F_MASK = (1 << _F_BITS) - 1
_DT_MASK = (1 << _DT_BITS) - 1


def _spectrogram_db(y: np.ndarray) -> np.ndarray:
    """Magnitude spectrogram in dB, referenced to its own max."""
    S = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP_LENGTH))
    return librosa.amplitude_to_db(S, ref=np.max)


def _find_peaks(S_db: np.ndarray) -> List[Tuple[int, int]]:
    """
    Find constellation peaks as (time_frame, freq_bin) using a vectorized local-max
    filter, an absolute amplitude floor, and a per-time-band cap for even coverage.
    """
    local_max = maximum_filter(S_db, size=PEAK_NEIGHBORHOOD) == S_db
    above_floor = S_db > AMP_MIN_DB
    peak_mask = local_max & above_floor

    freq_idx, time_idx = np.where(peak_mask)  # arrays of matching (freq, time)
    if len(time_idx) == 0:
        return []

    amps = S_db[freq_idx, time_idx]

    # Keep only the strongest peaks within each time band so a loud section
    # doesn't crowd out the rest of the track.
    peaks: List[Tuple[int, int]] = []
    band_ids = time_idx // BAND_SIZE_FRAMES
    for band in np.unique(band_ids):
        sel = np.where(band_ids == band)[0]
        if len(sel) > PEAKS_PER_FRAME_BAND:
            strongest = sel[np.argsort(amps[sel])[::-1][:PEAKS_PER_FRAME_BAND]]
        else:
            strongest = sel
        for i in strongest:
            peaks.append((int(time_idx[i]), int(freq_idx[i])))

    peaks.sort()  # by time, then frequency
    return peaks


def _hash_peaks(peaks: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Combinatorial hashing: pair each anchor peak with the next FAN_VALUE peaks in
    its forward target zone. Returns list of (hash, anchor_time).
    """
    fingerprints: List[Tuple[int, int]] = []
    n = len(peaks)
    for i in range(n):
        t1, f1 = peaks[i]
        paired = 0
        for j in range(i + 1, n):
            if paired >= FAN_VALUE:
                break
            t2, f2 = peaks[j]
            dt = t2 - t1
            if dt < MIN_DT:
                continue
            if dt > MAX_DT:
                break  # peaks are time-sorted, so no later peak is closer
            h = ((f1 & _F_MASK) << (_F_BITS + _DT_BITS)) | \
                ((f2 & _F_MASK) << _DT_BITS) | (dt & _DT_MASK)
            fingerprints.append((int(h), int(t1)))
            paired += 1
    return fingerprints


def generate_fingerprint(file_path: str, duration: Optional[float] = None) -> Optional[List[Tuple[int, int]]]:
    """
    Generate a constellation fingerprint for an audio file.

    Args:
        file_path: path to audio file.
        duration: max seconds to analyze (None = whole file). Library tracks use
                  the full song; short query clips just use whatever they contain.

    Returns:
        List of (hash, anchor_time) pairs, or None on failure/empty audio.
    """
    try:
        y, _ = librosa.load(file_path, sr=SR, duration=duration, mono=True)
        if y.size == 0:
            return None
        S_db = _spectrogram_db(y)
        peaks = _find_peaks(S_db)
        if not peaks:
            return None
        return _hash_peaks(peaks)
    except Exception as e:
        print(f"Error fingerprinting {file_path}: {e}")
        return None

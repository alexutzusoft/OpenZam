"""Audio format helpers. Fingerprinting itself lives in hash_fingerprint.py."""

import os

# Supported audio formats
SUPPORTED_FORMATS = {
    '.mp3': 'MP3',
    '.wav': 'WAV',
    '.flac': 'FLAC',
    '.ogg': 'OGG Vorbis',
    '.m4a': 'M4A/AAC',
    '.aac': 'AAC',
    '.wma': 'WMA',
    '.opus': 'Opus'
}


def is_supported_format(file_path):
    """Check if the file format is supported for audio processing."""
    _, ext = os.path.splitext(file_path.lower())
    return ext in SUPPORTED_FORMATS


def get_format_info(file_path):
    """Get format information for an audio file."""
    _, ext = os.path.splitext(file_path.lower())
    return SUPPORTED_FORMATS.get(ext, 'Unknown')

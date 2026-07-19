"""
Fingerprint database: a single inverted index mapping each hash to the songs and
anchor times where it occurs. This layout is what makes time-offset matching fast.

On-disk format (database/fingerprint_index.json):
{
  "format_version": "3.0",
  "songs": {"0": "Artist - Title.mp3", ...},   # song_id -> filename
  "index": {"<hash>": [[song_id, t], ...], ...}
}
"""

import json
import os
import time
from multiprocessing import Pool, cpu_count

from src.hash_fingerprint import generate_fingerprint

DB_DIR = 'database'
DB_FILE = os.path.join(DB_DIR, 'fingerprint_index.json')
FORMAT_VERSION = '3.0'

SUPPORTED_EXTENSIONS = ('.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.opus')

# Legacy files from pre-3.0 formats; removed on rebuild.
_LEGACY_FILES = [
    os.path.join(DB_DIR, 'song_database.json'),
    os.path.join(DB_DIR, 'hash_database.json'),
    'song_database.json',
    'hash_database.json',
]


def _process_single_song(args):
    """Fingerprint one file. Returns (filename, fingerprint or None)."""
    song_file, songs_dir = args
    file_path = os.path.join(songs_dir, song_file)
    fp = generate_fingerprint(file_path)
    return (song_file, fp)


def create_database(songs_dir, parallel=True, show_progress=True):
    """
    Build the inverted-index fingerprint database from every supported file in
    songs_dir, using multiprocessing. Overwrites any existing database.
    """
    song_files = [f for f in os.listdir(songs_dir)
                  if f.lower().endswith(SUPPORTED_EXTENSIONS)]

    if not song_files:
        print("No supported audio files found in directory.")
        print(f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
        return

    total = len(song_files)
    print(f"[*] Processing {total} songs...")

    start_time = time.time()
    songs = {}          # song_id (str) -> filename
    index = {}          # hash (str) -> list of [song_id, t]
    processed = 0

    def _add(song_file, fp):
        nonlocal processed
        if not fp:
            return
        song_id = len(songs)
        songs[str(song_id)] = song_file
        for h, t in fp:
            index.setdefault(str(h), []).append([song_id, t])
        processed += 1

    if parallel and total > 1:
        num_workers = min(cpu_count(), total)
        print(f"[*] Using {num_workers} parallel workers")
        with Pool(processes=num_workers) as pool:
            args = [(song, songs_dir) for song in song_files]
            for i, (song_file, fp) in enumerate(pool.imap_unordered(_process_single_song, args), 1):
                _add(song_file, fp)
                if show_progress:
                    print(f"[{i}/{total}] {song_file[:40]:<40}", end='\r')
    else:
        for i, song_file in enumerate(song_files, 1):
            _, fp = _process_single_song((song_file, songs_dir))
            _add(song_file, fp)
            if show_progress:
                print(f"[{i}/{total}] {song_file[:40]:<40}", end='\r')

    if show_progress:
        print()

    _remove_legacy_files()
    os.makedirs(DB_DIR, exist_ok=True)
    with open(DB_FILE, 'w') as f:
        json.dump({
            'format_version': FORMAT_VERSION,
            'songs': songs,
            'index': index,
        }, f)

    elapsed = time.time() - start_time
    per_song = elapsed / total if total else 0
    print(f"[OK] Database created: {processed}/{total} songs, {len(index)} unique hashes")
    print(f"[OK] Total time: {elapsed:.2f}s | Average: {per_song:.3f}s/song")


def load_database():
    """
    Load the fingerprint database. Returns the parsed dict, or None if it is
    missing or in an incompatible (pre-3.0) format — the caller then rebuilds.
    """
    if not os.path.exists(DB_FILE):
        return None
    try:
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
    if data.get('format_version') != FORMAT_VERSION:
        return None
    return data


def _remove_legacy_files():
    for path in _LEGACY_FILES:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

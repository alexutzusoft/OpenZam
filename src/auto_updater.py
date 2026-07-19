"""
Automatic database updater: detects changes in the songs directory (added,
removed, or modified files) and rebuilds the fingerprint database when needed.
An incompatible/missing DB also triggers a rebuild.
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Tuple

from src.database import load_database, create_database, DB_DIR
from src.audio_processing import SUPPORTED_FORMATS


class DatabaseAutoUpdater:
    def __init__(self, songs_dir: str = 'songs'):
        self.songs_dir = songs_dir
        self.metadata_file = os.path.join(DB_DIR, 'db_metadata.json')
        self.supported_extensions = tuple(SUPPORTED_FORMATS.keys())

    def get_songs_metadata(self) -> Dict[str, Dict]:
        """Map filename -> {size, mtime, hash} for quick change detection."""
        if not os.path.exists(self.songs_dir):
            return {}

        songs_metadata = {}
        for filename in os.listdir(self.songs_dir):
            if filename.lower().endswith(self.supported_extensions):
                file_path = os.path.join(self.songs_dir, filename)
                try:
                    stat = os.stat(file_path)
                    with open(file_path, 'rb') as f:
                        chunk = f.read(8192)
                    quick_hash = hashlib.md5(
                        chunk + str(stat.st_size).encode() + str(stat.st_mtime).encode()
                    ).hexdigest()
                    songs_metadata[filename] = {
                        'size': stat.st_size,
                        'mtime': stat.st_mtime,
                        'hash': quick_hash,
                    }
                except (OSError, IOError) as e:
                    print(f"[!] Warning: Could not read metadata for {filename}: {e}")
                    continue
        return songs_metadata

    def load_stored_metadata(self) -> Dict:
        if not os.path.exists(self.metadata_file):
            return {'songs_metadata': {}, 'last_update': 0}
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("[!] Warning: Corrupted metadata file, treating as new database")
            return {'songs_metadata': {}, 'last_update': 0}

    def save_metadata(self, songs_metadata: Dict[str, Dict]):
        os.makedirs(DB_DIR, exist_ok=True)
        metadata = {'songs_metadata': songs_metadata, 'last_update': time.time()}
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=4)

    def detect_changes(self) -> Tuple[List[str], List[str], List[str]]:
        """Return (added, removed, modified) song filenames."""
        current = self.get_songs_metadata()
        stored = self.load_stored_metadata().get('songs_metadata', {})

        current_names = set(current.keys())
        stored_names = set(stored.keys())

        added = list(current_names - stored_names)
        removed = list(stored_names - current_names)
        modified = [s for s in current_names & stored_names
                    if current[s]['hash'] != stored[s]['hash']]
        return added, removed, modified

    def needs_update(self) -> Tuple[bool, str]:
        # Missing or incompatible-format DB -> rebuild.
        if load_database() is None:
            return True, "No compatible database found"

        if not os.path.exists(self.songs_dir):
            return False, "Songs directory does not exist"

        added, removed, modified = self.detect_changes()
        if added:
            return True, f"New songs detected: {len(added)} files"
        if removed:
            return True, f"Removed songs detected: {len(removed)} files"
        if modified:
            return True, f"Modified songs detected: {len(modified)} files"
        return False, "Database is up to date"

    def auto_update_database(self, show_progress: bool = True) -> bool:
        needs_update, reason = self.needs_update()
        if not needs_update:
            if show_progress:
                print("[OK] Database is up to date")
            return False

        if show_progress:
            print(f"[*] Auto-updating database: {reason}")

        current_metadata = self.get_songs_metadata()
        if not current_metadata:
            if show_progress:
                print("[i] No songs found in directory")
            return False

        added, removed, modified = self.detect_changes()
        if show_progress and (added or removed or modified):
            print("[*] Changes detected:")
            for label, items in (("Added", added), ("Removed", removed), ("Modified", modified)):
                if items:
                    print(f"    - {label}: {len(items)} songs")
                    for song in items[:3]:
                        print(f"      - {song}")
                    if len(items) > 3:
                        print(f"      ... and {len(items) - 3} more")

        try:
            create_database(self.songs_dir, parallel=True, show_progress=show_progress)
            self.save_metadata(current_metadata)
            if show_progress:
                print("[OK] Database automatically updated!")
            return True
        except Exception as e:
            if show_progress:
                print(f"[X] Error during automatic database update: {e}")
            return False

    def get_database_stats(self) -> Dict:
        db = load_database()
        current_songs = self.get_songs_metadata()
        stored_metadata = self.load_stored_metadata()
        return {
            'db_songs': len(db['songs']) if db else 0,
            'current_songs': len(current_songs),
            'last_update': stored_metadata.get('last_update', 0),
            'needs_update': self.needs_update()[0],
        }


def smart_database_check(songs_dir: str = 'songs', show_progress: bool = True) -> bool:
    """
    Ensure the database is ready to use, rebuilding if needed.
    Returns True if the database is ready, False if setup is still required.
    """
    updater = DatabaseAutoUpdater(songs_dir)

    if not os.path.exists(songs_dir):
        if show_progress:
            print(f"[*] Creating songs directory: {songs_dir}")
        os.makedirs(songs_dir)
        print(f"[*] Add your songs to the '{songs_dir}' directory")
        print(f"[*] Supported formats: {', '.join(SUPPORTED_FORMATS.values())}")
        return False

    updated = updater.auto_update_database(show_progress)

    db = load_database()
    if db is None:
        if show_progress:
            print("[X] Database is not ready after update attempt")
        return False

    if show_progress and not updated:
        print(f"[OK] Database ready: {len(db['songs'])} songs indexed")
    return True

import os
import time

from src.utils import get_username
from src.database import create_database
from src.matching import identify
from src.audio_processing import is_supported_format, get_format_info, SUPPORTED_FORMATS
from src.auto_updater import smart_database_check, DatabaseAutoUpdater


def main_flow():
    """The main CLI flow."""
    username = get_username()
    print(f"[*] Welcome to OpenZam, {username}!")
    print(f"[*] Supported formats: {', '.join(SUPPORTED_FORMATS.values())}")

    songs_dir = 'songs'
    print("\n[*] Checking database status...")

    if not smart_database_check(songs_dir, show_progress=True):
        print("[!] Database setup required. Please add songs and restart.")
        return

    stats = DatabaseAutoUpdater(songs_dir).get_database_stats()
    print(f"[*] Ready! {stats['db_songs']} songs indexed")

    force_update = input("\nForce database rebuild? (y/n) [default: n]: ").lower()
    if force_update == 'y':
        print("[*] Rebuilding database...")
        create_database(songs_dir)
        print("[OK] Database rebuilt!")

    file_path = input("\nEnter an audio file path: ").strip().strip('"').strip("'")

    if not os.path.exists(file_path):
        print("[X] Error: Invalid file path.")
        return

    if not is_supported_format(file_path):
        print(f"[X] Unsupported format: {get_format_info(file_path)}")
        print(f"[*] Supported formats: {', '.join(SUPPORTED_FORMATS.values())}")
        return

    print(f"[*] Detected format: {get_format_info(file_path)}")
    print("[*] Identifying...")

    result = identify(file_path, top_n=3)

    if isinstance(result, str):
        print(f"[X] {result}")
        return

    results, elapsed = result
    if not results:
        print(f"[?] No confident match found. ({elapsed:.3f}s)")
        return

    print(f"[OK] Match found in {elapsed:.3f}s:")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r.song_name}")
        print(f"     Confidence: {r.score:.2%} | Aligned votes: {r.votes}")


def check_database_status():
    """Print database status without running the full CLI."""
    print("[*] Database Status Check")
    print("-" * 40)

    updater = DatabaseAutoUpdater('songs')
    stats = updater.get_database_stats()
    needs_update, reason = updater.needs_update()

    print(f"[*] Indexed songs: {stats['db_songs']}")
    print(f"[*] Current song files: {stats['current_songs']}")
    last = stats['last_update']
    print(f"[*] Last update: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last)) if last else 'Never'}")

    if needs_update:
        print(f"[!] Update needed: {reason}")
        if input("\nAuto-update now? (y/n): ").lower() == 'y':
            updater.auto_update_database()
    else:
        print("[OK] Database is up to date!")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--check-db":
        check_database_status()
    else:
        main_flow()

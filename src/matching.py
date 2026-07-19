"""
Song identification via time-offset voting over the inverted hash index.

For each (hash, t_query) in the query fingerprint we look up every (song_id, t_db)
that shares the hash and vote for the pair (song_id, t_db - t_query). A true match
produces a sharp peak: many hashes agree on a single offset (the clip's position in
the track). Non-matches scatter their votes across offsets and never build a peak,
which is how unknown songs get rejected instead of forcing a false positive.
"""

import time
from collections import defaultdict

from src.database import load_database
from src.hash_fingerprint import generate_fingerprint

# A match must clear both bars: enough aligned votes in absolute terms, and a clear
# lead over the runner-up so ambiguous cases are rejected rather than guessed.
MIN_ALIGNED_VOTES = 5
MIN_LEAD_RATIO = 1.5

# Cap how much of a query we analyze. A short segment is enough to identify a
# track, and it avoids decoding an entire multi-minute file for every lookup.
QUERY_DURATION = 30.0


class MatchResult:
    """A single identification result."""

    def __init__(self, song_name, votes, score, offset):
        self.song_name = song_name
        self.votes = votes          # aligned votes at the best offset
        self.score = score          # confidence in [0, 1]
        self.offset = offset        # clip position in the track (frames)

    def __repr__(self):
        return f"MatchResult(song='{self.song_name}', score={self.score:.2%}, votes={self.votes})"


def _score_songs(query_fp, db):
    """
    Return per-song best-offset vote counts, sorted descending.
    Result: list of (song_id, best_votes, best_offset).
    """
    index = db['index']
    # (song_id, offset) -> vote count
    votes = defaultdict(int)
    for h, t_query in query_fp:
        occurrences = index.get(str(h))
        if not occurrences:
            continue
        for song_id, t_db in occurrences:
            votes[(song_id, t_db - t_query)] += 1

    # Collapse to each song's strongest offset.
    best = {}  # song_id -> (votes, offset)
    for (song_id, offset), count in votes.items():
        if song_id not in best or count > best[song_id][0]:
            best[song_id] = (count, offset)

    ranked = [(sid, v, off) for sid, (v, off) in best.items()]
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


def identify(file_path, top_n=3):
    """
    Identify a song from an audio file.

    Returns (results, elapsed_seconds) where results is a list of MatchResult
    (possibly empty if nothing clears the rejection thresholds), or an error string.
    """
    db = load_database()
    if not db or not db.get('index'):
        return "Database is empty. Please build it first."

    start = time.time()
    query_fp = generate_fingerprint(file_path, duration=QUERY_DURATION)
    if not query_fp:
        return "Could not process the audio file."

    ranked = _score_songs(query_fp, db)
    elapsed = time.time() - start

    if not ranked:
        return ([], elapsed)

    songs = db['songs']
    top_votes = ranked[0][1]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0

    # Reject when the best match is weak or not clearly ahead of the runner-up.
    if top_votes < MIN_ALIGNED_VOTES or (runner_up and top_votes < runner_up * MIN_LEAD_RATIO):
        return ([], elapsed)

    results = []
    for song_id, v, offset in ranked[:top_n]:
        score = min(1.0, v / top_votes)
        results.append(MatchResult(songs[str(song_id)], v, score, offset))
    return (results, elapsed)

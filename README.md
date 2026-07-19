<div align="center">

# 🎵 OpenZam — v3

**Open-source song identification powered by advanced audio fingerprinting**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

*Fast • Accurate • Privacy-First*

</div>

---

## ✨ Features

- **🎯 Real Fingerprinting** - Constellation peak-pairs with time-offset alignment (Shazam-style), so it recognizes short and noisy clips, not just identical files
- **⚡ Fast Matching** - Inverted hash index with parallel database builds
- **🔒 Privacy First** - All processing happens locally on your machine
- **📊 Honest Rejection** - Reports "no match" for unknown songs instead of forcing a false positive
- **🎵 Universal Format Support** - Mix and match MP3, FLAC, OGG, WAV, M4A, AAC, WMA, Opus
- **🛠️ Modular Design** - Easy to extend and customize

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/alexutzusoft/OpenZam.git
cd OpenZam

# Create virtual environment using venv (recommended)
uv venv

# Install dependencies
uv pip install -r requirements.txt
```

### Usage

1. **Add your song library** to the `songs/` directory (supports MP3, WAV, FLAC, OGG, M4A, AAC, WMA, Opus)

2. **Run OpenZam**
   ```bash
   python main.py
   ```

3. **Build the database** when prompted (first time or after adding new songs)
   ```
   Do you want to update the song database? (y/n): y
   ```
   > If you're upgrading from an older version, the database format changed — OpenZam
   > detects the old files and rebuilds automatically from your `songs/` directory on first run.

4. **Identify a song** by providing the file path (any supported format)
   ```
   Enter an audio file path: path/to/unknown/song.ogg
   ```
   A short clip works too — it doesn't have to be the whole track.

## 📊 How It Works

OpenZam identifies audio using constellation fingerprinting, the same core idea behind Shazam:

1. **Spectral Peaks**
   - Compute a spectrogram and pick local-maximum peaks (a "constellation")
   - Peaks are spread evenly across time so loud sections don't dominate

2. **Combinatorial Hashing**
   - Pair each anchor peak with nearby forward peaks
   - Encode each pair as `(freq1, freq2, time-delta)` plus the anchor's absolute time

3. **Time-Offset Matching**
   - Store all hashes in an inverted index: `hash -> [(song, time), ...]`
   - For a query, vote for `(song, db_time - query_time)`; the correct song forms a
     sharp peak at a consistent offset, while unknown songs scatter and get rejected

## 📈 Performance

- **Clip Recognition**: Identifies short segments, not just full-file matches
- **Fast Lookup**: Inverted hash index keeps matching quick as the library grows
- **Parallel Builds**: Fingerprints the library across all CPU cores

## 🛠️ Tech Stack

- **Python 3.8+**
- **librosa** - Audio loading and spectrogram analysis
- **numpy** - Numerical computing
- **scipy** - Vectorized peak detection (`scipy.ndimage`)

## 📋 Roadmap

OpenZam is actively being developed with exciting features planned:

- [X] **Update 1**: Multi-format audio support and confidence scoring
- [X] **Update 2**: Hash-based fingerprinting for faster matching
- [X] **Update 3**: Add automatic database updates
- [X] **Update 4**: Constellation fingerprinting with time-offset alignment (real clip recognition)
- [ ] **Update 5**: Real-time microphone input identification
- [ ] **Update 6**: SQLite database with 100K+ song support
- [ ] **Update 7**: Neural audio embeddings with ML models

See [improvements.md](others/improvements.md) for detailed roadmap.

## 🤝 Contributing

Contributions are more than welcome! Whether it's bug fixes, new features, or documentation improvements.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 💡 Notes

- Built as a fun weekend project to explore audio fingerprinting
- Not production-ready but works great for personal use
- All processing is local - your audio never leaves your machine

## 🌟 Show Your Support

If you find OpenZam useful, give it a ⭐️ on GitHub!

---

<div align="center">
Made with ❤️ by a developer who loves music (and Python)
</div>
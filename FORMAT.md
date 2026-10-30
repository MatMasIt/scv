# SCV 1.0 file format

Extension: `.scv`; container: standard ZIP with **stored** (uncompressed) entries. Codecs are already compressed; ZIP adds little benefit.

```
manifest.json
 audio.opus
 slides/00001.webp
 slides/00002.webp
 ...
```

`manifest.json` is UTF-8 JSON. Example:

```json
{
  "format": "SCV",
  "format_version": 1,
  "format_name": "Slide Compressed Video",
  "generator": "SCV Suite 1.0.0",
  "title": "Lecture",
  "duration_seconds": 120.0,
  "audio": {"file": "audio.opus", "codec": "opus", "bitrate": "24k", "channels": 1},
  "image": {"codec": "webp", "quality": 80, "deltas": false},
  "timing": "start_time_seconds",
  "slides": [
    {"time": 0.0, "image": "slides/00001.webp", "text": "Optional OCR text"},
    {"time": 46.5, "image": "slides/00002.webp"}
  ]
}
```

`created_utc` can also be provided. Audio is an uninterrupted Ogg Opus stream, retaining gaps and original clock times. Slide times are absolute seconds since playback begins, monotonically nondecreasing, and the first slide begins at zero. Each image replaces the previous one completely. Unknown format versions are rejected. No delta frames, silence maps, playlists or migration rules.

The optional `text` field on a slide contains OCR text produced during
encoding. It is omitted when OCR is disabled.

To restore MP4, hold each slide until the next timestamp, encode it as H.264, and mux with converted AAC audio. Output size generally grows significantly.

The player stores bookmarks, notes, and annotations outside the archive in an
optional sidecar named `<lecture>.scvnotes` (for example, `lecture.scvnotes`).
The sidecar is not part of the SCV format. When playback resume is enabled,
the player stores the current position every ten seconds and when closing a
lecture. If a saved position is awaiting the user's resume choice, that
checkpoint remains unchanged until the user chooses an action:

```json
{
  "progress": {"position_seconds": 123.4, "slide_index": 7}
}
```

`slide_index` is zero-based. Progress writes preserve the sidecar's saved study
data and do not save unsaved bookmarks, notes, or annotations.

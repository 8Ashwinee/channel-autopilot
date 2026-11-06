"""The video maker: a video.yml in, a narrated MP4 + thumbnail + queue item out.

  video.yml -> voice.py (Kokoro speech, timeline built from the speech) -> template.py (a deterministic HTML scene)
            -> render.py (Chromium frames -> ffmpeg, voice and optional music) -> thumbnail -> queue item
"""

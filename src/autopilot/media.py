"""Instagram and Facebook fetch media from a public https URL, so local files must be hosted first.

config:
  media:
    s3_bucket: my-bucket            # uses the `aws` CLI you already have configured
    prefix: autopilot/              # key prefix
    public_base: https://cdn.example.com/   # how the bucket is reached publicly (must end with /)
  or
  media:
    command: "my-uploader {path} {name}"    # must print the public URL on stdout
"""
from __future__ import annotations

import mimetypes
import subprocess
from pathlib import Path

from .errors import AutopilotError, ConfigError


def host(cfg, path: Path, slug: str) -> str:
    m = cfg.get("media", {}) or {}
    name = f"{slug}-{path.name}"
    if m.get("command"):
        out = subprocess.run(m["command"].format(path=str(path), name=name), shell=True, capture_output=True, text=True)
        url = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
        if out.returncode or not url.startswith("https://"):
            raise AutopilotError(f"media.command failed: {out.stderr.strip()[:300] or out.stdout.strip()[:300]}")
        return url
    if m.get("s3_bucket") and m.get("public_base"):
        key = f"{m.get('prefix', '')}{name}"
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        r = subprocess.run(["aws", "s3", "cp", str(path), f"s3://{m['s3_bucket']}/{key}", "--content-type", ctype,
                            "--cache-control", "public, max-age=604800", "--only-show-errors"], capture_output=True, text=True)
        if r.returncode:
            raise AutopilotError(f"aws s3 cp failed: {r.stderr.strip()[:300]}")
        return m["public_base"].rstrip("/") + "/" + key
    raise ConfigError("Instagram and Facebook need public media URLs: set media.s3_bucket + media.public_base, or media.command")

#!/usr/bin/env python3
"""Add (or update) one channel on your Channel Studio: stores the channel's YouTube sign-in in YOUR AWS SSM (encrypted)
and adds it to the channels list the dashboard shows.

  python3 dashboard/add_channel.py <id> "<name>" <path to the channel's youtube token JSON> [--prefix /chstudio]

The token is the file `autopilot youtube-auth` wrote for that channel (it holds the refresh token and your OAuth client id
and secret). Uses your default AWS credentials (AWS_PROFILE / AWS_REGION)."""
import json, subprocess, sys

a = sys.argv[1:]
if len(a) < 3:
    sys.exit(__doc__)
cid, name, token = a[0], a[1], a[2]
prefix = a[a.index("--prefix") + 1] if "--prefix" in a else "/chstudio"
t = json.load(open(token))
missing = [k for k in ("client_id", "client_secret", "refresh_token") if not t.get(k)]
if missing:
    sys.exit(f"{token} lacks {missing}: run `autopilot youtube-auth` for this channel first")
ssm = lambda *x: subprocess.run(["aws", "ssm", *x], capture_output=True, text=True)
r = ssm("put-parameter", "--name", f"{prefix}/youtube/{cid}", "--type", "SecureString", "--overwrite",
        "--value", json.dumps({k: t[k] for k in ("client_id", "client_secret", "refresh_token")}))
if r.returncode:
    sys.exit(r.stderr)
cur = ssm("get-parameter", "--name", f"{prefix}/channels", "--query", "Parameter.Value", "--output", "text")
chans = json.loads(cur.stdout) if cur.returncode == 0 else []
chans = [c for c in chans if c["id"] != cid] + [{"id": cid, "name": name}]
r = ssm("put-parameter", "--name", f"{prefix}/channels", "--type", "String", "--overwrite", "--value", json.dumps(chans))
print("ok:", [c["id"] for c in chans] if r.returncode == 0 else r.stderr)

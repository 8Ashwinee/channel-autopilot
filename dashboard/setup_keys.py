#!/usr/bin/env python3
"""Store the dashboard's Google service account, the Google Ads account for Keyword Planner and a token for the rotation,
all in YOUR AWS SSM (encrypted).

  python3 dashboard/setup_keys.py <service-account-key.json> <google ads customer id> [--prefix /chstudio]

The service account reads Search Console (add its email as a user of each property) and runs Keyword Planner (add it as a
user of your Google Ads account; its Google Cloud project needs Google Ads API Basic access). Prints the rotation token
once: save it to a file and point rotation.yml dashboard.token_file at it."""
import json, secrets, subprocess, sys

a = sys.argv[1:]
if len(a) < 2:
    sys.exit(__doc__)
prefix = a[a.index("--prefix") + 1] if "--prefix" in a else "/chstudio"
key = open(a[0]).read(); json.loads(key)
tok = secrets.token_urlsafe(32)
for name, value, typ in [("google/sa", key, "SecureString"), ("ads/customer_id", a[1].replace("-", ""), "String"),
                         ("svc_token", tok, "SecureString")]:
    r = subprocess.run(["aws", "ssm", "put-parameter", "--name", f"{prefix}/{name}", "--type", typ, "--overwrite", "--value", value],
                       capture_output=True, text=True)
    print(name, "ok" if r.returncode == 0 else r.stderr)
print("rotation token (save it, e.g. to secrets/studio-token, chmod 600):", tok)

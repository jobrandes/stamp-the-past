#!/bin/sh
# One command to prove nothing broke: build, validate content, check layout, compare every screen to the saved snapshot.
set -e
cd "$(dirname "$0")/.."
python3 build.py
python3 tests/validate_packs.py
python3 tests/check.py
python3 tests/flows.py
python3 tests/nearby.py
python3 tests/offline.py
python3 tests/seo_check.py 2>&1 | grep -v "GET /"
python3 tests/daily_check.py 2>&1 | grep -v "GET /"
python3 tests/snapshot.py index.html /tmp/_now.json
python3 - <<'PY'
import json,sys
a=json.load(open('tests/baseline.json')); b=json.load(open('/tmp/_now.json'))
d=[k for k in a if a[k]!=b.get(k)]
print('SNAPSHOT: '+('OK (every screen matches)' if not d else 'CHANGED: '+', '.join(d)+'  (if intended, run: python3 tests/snapshot.py index.html tests/baseline.json)'))
sys.exit(1 if d else 0)
PY
echo ALL CHECKS PASSED

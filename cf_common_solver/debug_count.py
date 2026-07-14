"""
Debug script: print a breakdown of solved problems to find why
the count (222) doesn't match Codeforces profile (243).
Run with:  python debug_count.py
"""

import requests
import time
from collections import defaultdict

HANDLE = "ramortizedsoul"
USER_STATUS_URL = "https://codeforces.com/api/user.status"
PAGE_SIZE = 10_000


def fetch_all_submissions(handle):
    submissions = []
    start = 1
    while True:
        resp = requests.get(USER_STATUS_URL, params={"handle": handle, "from": start, "count": PAGE_SIZE}, timeout=30)
        data = resp.json()
        page = data["result"]
        submissions.extend(page)
        if len(page) < PAGE_SIZE:
            break
        start += PAGE_SIZE
        time.sleep(0.5)
    return submissions


subs = fetch_all_submissions(HANDLE)
print(f"Total submissions fetched: {len(subs)}")

ok_subs = [s for s in subs if s.get("verdict") == "OK"]
print(f"AC submissions: {len(ok_subs)}")

# Deduplicate by (contestId, index) — same as what CF uses on the profile
by_contest_index = {}
for s in ok_subs:
    p = s.get("problem", {})
    key = (p.get("contestId"), p.get("index"))
    if key not in by_contest_index:
        by_contest_index[key] = s

print(f"\nUnique by (contestId, index): {len(by_contest_index)}")

# Deduplicate by (contestId, index, name) — what the app currently does
by_full_key = {}
for s in ok_subs:
    p = s.get("problem", {})
    key = (p.get("contestId"), p.get("index"), p.get("name", ""))
    if key not in by_full_key:
        by_full_key[key] = s

print(f"Unique by (contestId, index, name): {len(by_full_key)}")

# Show problems where name differs for same (contestId, index) — collision candidates
name_by_ci = defaultdict(set)
for s in ok_subs:
    p = s.get("problem", {})
    ci = (p.get("contestId"), p.get("index"))
    name_by_ci[ci].add(p.get("name", ""))

collisions = {k: v for k, v in name_by_ci.items() if len(v) > 1}
if collisions:
    print(f"\n⚠️  Problems with same (contestId,index) but different names ({len(collisions)}):")
    for k, names in collisions.items():
        print(f"  {k}: {names}")

# Show problems where contestId is None
no_contest = [k for k in by_contest_index if k[0] is None]
print(f"\nProblems with no contestId (gym/practice/other): {len(no_contest)}")
for k in no_contest[:10]:
    s = by_contest_index[k]
    p = s.get("problem", {})
    print(f"  index={p.get('index')} name={p.get('name')} author={s.get('author', {})}")

print("\nDone.")

# pick_sample.py
import json
from digest import build_digest

rows = [json.loads(l) for l in open("data/companies.jsonl", encoding="utf-8")]
digests = [build_digest(r) for r in rows]

print(f"{'id':<12} {'flags':<6} {'years':<6} {'status':<12} defendant")
for d in digests:
    print(f"{d['id']:<12} {len(d['flags']):<6} {len(d['financials']):<6} "
          f"{d['profile'].get('status'):<12} {d['cases_as_defendant']}")

# one example flag of each kind, so you can see what is present in the data
seen = {}
for d in digests:
    for f in d["flags"]:
        seen.setdefault(f.split(" ")[0] + " " + f.split(" ")[1], (d["id"], f))
print("\nFLAG TYPES FOUND:")
for k, (cid, f) in seen.items():
    print(f"  {cid}: {f}")
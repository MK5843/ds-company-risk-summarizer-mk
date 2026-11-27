# explore.py
import json
rows = [json.loads(l) for l in open("data/companies.jsonl")]
print(json.dumps(rows[0], indent=2)[:6000])
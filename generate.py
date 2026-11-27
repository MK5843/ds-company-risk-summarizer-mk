# generate.py
import json, sys, time
from tqdm import tqdm
from digest import build_digest
from llm import complete

V1_SYS = "You summarise company records."
V2_SYS = """You write pre-read summaries for a team vetting companies as suppliers or partners.
Rules:
- 80-120 words, Markdown.
- Start with 'Risk flags:' as bullets (use the flags provided; if none, say 'No major flags').
- Then 'Overview:' with 2-3 sentences: what the company does, where, age, ownership.
- Use ONLY the numbers in the digest. Never calculate or guess. If something is missing, say so.
- Neutral tone, no recommendation."""


def v1_user(rec):
    return f"Write a short summary of this company:\n{json.dumps(rec)}"


def v2_user(digest):
    return f"Digest:\n{json.dumps(digest, indent=1)}"


def load_rows(ids_file=None):
    rows = [json.loads(l) for l in open("data/companies.jsonl", encoding="utf-8")]
    if ids_file:
        wanted = [l.strip() for l in open(ids_file, encoding="utf-8") if l.strip()]
        rows = [r for r in rows if r["registrationNumber"] in wanted]
    return rows


def run(version, ids_file=None, pause=0.0):
    rows = load_rows(ids_file)
    out_path = f"summaries/{version}.jsonl"

    done = set()
    try:
        for l in open(out_path, encoding="utf-8"):
            done.add(json.loads(l)["registrationNumber"])
    except FileNotFoundError:
        pass

    with open(out_path, "a", encoding="utf-8") as out:
        for rec in tqdm(rows, desc=version):
            rid = rec["registrationNumber"]
            if rid in done:
                continue
            try:
                if version.startswith("v1"):
                    s = complete(V1_SYS, v1_user(rec))
                else:
                    s = complete(V2_SYS, v2_user(build_digest(rec)))
            except Exception as e:
                print(f"\nFailed {rid}: {e}. Stopping; rerun to resume.")
                return
            out.write(json.dumps({"registrationNumber": rid, "summary": s}) + "\n")
            out.flush()
            time.sleep(pause)


if __name__ == "__main__":
    # uv run python generate.py v1 sample_ids.txt 2   (sample, 2 s pause)
    # uv run python generate.py v2 all 2              (all 50, 2 s pause)
    version = sys.argv[1]
    ids_file = None if len(sys.argv) < 3 or sys.argv[2] == "all" else sys.argv[2]
    pause = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    run(version, ids_file, pause)
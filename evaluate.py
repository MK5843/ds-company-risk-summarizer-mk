# evaluate.py
import json, re, sys
from digest import build_digest

KEYWORDS = {
    "defendant": ["defendant", "case", "litigation", "court"],
    "net loss": ["loss"],
    "negative equity": ["negative equity", "deficit"],
    "revenue fell": ["revenue", "decline", "fell", "drop"],
    "current ratio": ["current ratio", "liquidity"],
    "interest coverage": ["interest coverage", "coverage"],
    "operating cash flow": ["cash flow"],
    "audit": ["audit", "qualified", "opinion"],
    "of shares": ["shares", "shareholder", "owns", "holds", "stake"],
    "appointed": ["appointed", "new director", "director"],
    "status": ["status", "dormant", "struck", "winding", "inactive"],
    "year(s) of financials": ["year", "financials"],
    "no financial": ["financial", "statements"],
}


def numbers_in(text):
    out = []
    for m in re.findall(r"\d[\d,]*\.?\d*", text):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def allowed_numbers(*sources):
    vals = set()

    def walk(x):
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            vals.add(float(x))
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            vals.update(numbers_in(x))

    for s in sources:
        walk(s)
    return vals


def close(n, vals):
    for v in vals:
        v = abs(v)
        for cand in (v, v * 100, v / 1e6, v / 1e3):   # raw, percent, RM millions, RM thousands
            if abs(n - cand) <= max(0.06, abs(cand) * 0.01):
                return True
    return False


def fact_check(summary, rec, digest):
    ok = allowed_numbers(rec, digest)
    return [n for n in numbers_in(summary) if not close(n, ok)]


def context(summary, n, width=45):
    plain = summary.replace(",", "")
    token = re.escape(f"{n:g}")
    m = re.search(rf"(?<![\d.]){token}(?![\d])", plain)
    if not m:
        return ""
    return plain[max(0, m.start() - width): m.end() + width].replace("\n", " ")


def flag_covered(flag, summary):
    s = summary.lower()
    f = flag.lower()
    for key, words in KEYWORDS.items():
        if key in f and any(w in s for w in words):
            return True
    nums = [n for n in numbers_in(flag) if not (1990 <= n <= 2100)]
    plain = s.replace(",", "")
    return any(f"{n:g}" in plain for n in nums)


def risk_recall(summary, digest):
    if not digest["flags"]:
        return 1.0
    return sum(flag_covered(f, summary) for f in digest["flags"]) / len(digest["flags"])


def main(versions):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recs = {}
    for l in open("data/companies.jsonl", encoding="utf-8"):
        r = json.loads(l)
        recs[r["registrationNumber"]] = r

    for v in versions:
        sums = [json.loads(l) for l in open(f"summaries/{v}.jsonl", encoding="utf-8")]
        total_bad, with_bad, recalls, words, rows = 0, 0, [], [], []
        for s in sums:
            cid = s["registrationNumber"]
            d = build_digest(recs[cid])
            bad = fact_check(s["summary"], recs[cid], d)
            rc = risk_recall(s["summary"], d)
            total_bad += len(bad)
            with_bad += bool(bad)
            recalls.append(rc)
            words.append(len(s["summary"].split()))
            rows.append((rc, cid, bad, d["flags"], s["summary"]))

        in_range = sum(80 <= w <= 120 for w in words)
        print(f"\n=== {v}: {len(sums)} summaries ===")
        print(f"Unsupported numbers (candidates): {total_bad} in {with_bad} summaries")
        print(f"Avg risk recall: {sum(recalls)/len(recalls):.2f}")
        print(f"Summaries with 100% recall: {sum(r >= 1 for r in recalls)}/{len(recalls)}")
        print(f"Avg words: {sum(words)/len(words):.0f} | within 80-120 words: {in_range}/{len(words)}")

        if v == "v2":
            outside = [(s["registrationNumber"], w) for s, w in zip(sums, words) if not 80 <= w <= 120]
            print("v2 outside 80-120 words:", outside)

        limit = None if v == "v2" else 15
        print(f"\nCandidate bad numbers in {v}" + (" (first 15)" if limit else "") + ":")
        shown = 0
        for rc, cid, bad, flags, summ in rows:
            for n in bad:
                if limit and shown >= limit:
                    break
                print(f"  {cid}: {n:g}  ...{context(summ, n)}...")
                shown += 1

        if v == "v2":
            print("\nLowest-recall examples:")
            for rc, cid, bad, flags, summ in sorted(rows)[:3]:
                print(f"\n--- {cid} recall={rc:.2f}")
                print("FLAGS:", *flags, sep="\n  - ")
                print("SUMMARY:", summ[:700])

if __name__ == "__main__":
    main(sys.argv[1:] or ["v1", "v2"])
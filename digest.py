# digest.py
from datetime import date

REF_DATE = date(2025, 12, 31)   # records are as of 31 Dec 2025


def pct_change(old, new):
    if old in (None, 0) or new is None:
        return None
    return round((new - old) / abs(old) * 100, 1)


def ratio(a, b):
    if a is None or not b:
        return None
    return round(a / b, 2)


def build_digest(rec: dict) -> dict:
    p = rec["profile"]
    rel = rec["relationships"]
    years = sorted(rec["financials"]["years"], key=lambda y: y["financialYear"])
    cases = rec["litigation"]["cases"]

    # ---- ownership ----
    shareholders = rel.get("shareholders", [])
    top = max(shareholders, key=lambda s: s.get("percentage") or 0, default=None)
    corporate_holders = [s for s in shareholders if s.get("type") != "individual"]

    # ---- recently appointed directors (within 6 months of record date) ----
    recent_directors = []
    for d in rel.get("directors", []):
        try:
            appointed = date.fromisoformat(d["appointedOn"])
            if (REF_DATE - appointed).days <= 183:
                recent_directors.append(d["name"])
        except (KeyError, ValueError):
            pass

    # ---- financials per year ----
    fin = []
    for y in years:
        st = y.get("statements", {})
        rm = y.get("ratiosAndMetrics", {})
        fin.append({
            "year": y["financialYear"],
            "revenue": st.get("revenue"),
            "profit_after_tax": st.get("profitAfterTax"),
            "total_equity": st.get("totalEquity"),
            "total_liabilities": st.get("totalLiabilities"),
            "operating_cash_flow": st.get("operatingCashFlow"),
            "current_ratio": ratio(st.get("currentAssets"), st.get("currentLiabilities")),
            "interest_coverage": rm.get("capitalStructure", {}).get("interestCoverageRatio"),
            "net_margin": rm.get("profitability", {}).get("netProfitMargin"),
            "audit_opinion": y.get("audit", {}).get("opinion"),
        })

    latest = fin[-1] if fin else {}
    prev = fin[-2] if len(fin) >= 2 else {}

    # ---- litigation: detect role and amount without knowing the exact key names ----
    def role(c):
        for v in c.values():
            if isinstance(v, str) and len(v) < 30:
                low = v.strip().lower()
                if "defendant" in low:
                    return "defendant"
                if "plaintiff" in low:
                    return "plaintiff"
        return ""

    def amount(c):
        for k, v in c.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if "amount" in k.lower() or "claim" in k.lower():
                    return v
        return 0

    defendant = [c for c in cases if role(c) == "defendant"]
    defendant_total = sum(amount(c) for c in defendant)

    # ---- risk flags ----
    flags = []
    if p.get("status", "").lower() != "active":
        flags.append(f"Company status: {p.get('status')}")
    if defendant:
        flags.append(f"Defendant in {len(defendant)} case(s), total claims RM{defendant_total:,.0f}")
    if latest.get("profit_after_tax") is not None and latest["profit_after_tax"] < 0:
        flags.append(f"Net loss in {latest['year']}: RM{latest['profit_after_tax']:,.0f}")
    if latest.get("total_equity") is not None and latest["total_equity"] < 0:
        flags.append(f"Negative equity in {latest['year']}: RM{latest['total_equity']:,.0f}")
    g = pct_change(prev.get("revenue"), latest.get("revenue"))
    if g is not None and g <= -10:
        flags.append(f"Revenue fell {abs(g)}% from {prev['year']} to {latest['year']}")
    if latest.get("current_ratio") is not None and latest["current_ratio"] < 1:
        flags.append(f"Current ratio {latest['current_ratio']} (below 1) in {latest['year']}")
    if latest.get("interest_coverage") is not None and latest["interest_coverage"] < 1.5:
        flags.append(f"Low interest coverage {latest['interest_coverage']} in {latest['year']}")
    if latest.get("operating_cash_flow") is not None and latest["operating_cash_flow"] < 0:
        flags.append(f"Negative operating cash flow in {latest['year']}")
    bad_audits = [f"{f['year']}: {f['audit_opinion']}" for f in fin
                  if f["audit_opinion"] and f["audit_opinion"].lower() != "unqualified"]
    if bad_audits:
        flags.append("Non-clean audit opinion (" + "; ".join(bad_audits) + ")")
    if top and (top.get("percentage") or 0) > 50:
        flags.append(f"{top['name']} holds {top['percentage']}% of shares")
    if recent_directors:
        flags.append(f"Director(s) appointed in the last 6 months: {', '.join(recent_directors)}")
    if 0 < len(fin) < 3:
        flags.append(f"Only {len(fin)} year(s) of financials available")
    if not fin:
        flags.append("No financial statements available")

    return {
        "id": rec["registrationNumber"],
        "profile": p,
        "n_directors": len(rel.get("directors", [])),
        "top_shareholder_pct": top.get("percentage") if top else None,
        "corporate_shareholders": len(corporate_holders),
        "financials": fin,
        "cases_total": len(cases),
        "cases_as_defendant": len(defendant),
        "defendant_claims_rm": defendant_total,
        "flags": flags,
    }
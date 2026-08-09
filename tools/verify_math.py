"""Independent math audit for the CMA Decision Platform.

Usage: with the backend running and the demo seeded (python -m app.seed):

    python3 tools/verify_math.py

Recomputes every number for the seeded demo CMA straight from the documented
formulas in docs/METHODOLOGY.md, using only the standard library and raw API
JSON, then compares against what the platform serves. No application code is
imported, so a bug shared by the code and its unit tests would still be
caught here. Exits non-zero on any mismatch.
"""
import sys
import json
import math
import urllib.request
from datetime import date

BASE = "http://localhost:8000"
TOL = 0.02  # dollars/points tolerance for stored-rounding effects

failures = []
checks = 0


def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.load(r)


def check(label, expected, actual, tol=TOL):
    global checks
    checks += 1
    if expected is None and actual is None:
        return
    if expected is None or actual is None or abs(expected - actual) > tol:
        failures.append("%-55s expected %s, platform says %s" % (label, expected, actual))


def check_eq(label, expected, actual):
    global checks
    checks += 1
    if expected != actual:
        failures.append("%-55s expected %r, platform says %r" % (label, expected, actual))


cma = get("/api/cmas/1")
subject = cma["subject"]
comps = get("/api/cmas/1/comparables")
config = get("/api/cmas/1/config")
valuation = get("/api/cmas/1/valuation")
strategies = get("/api/cmas/1/strategies")
sensitivity = get("/api/cmas/1/sensitivity")

W = config["weights"]
P = config["similarity_params"]
A = config["assumptions"]
R = config["reconciliation"]
CONDITIONS = ["poor", "fair", "average", "good", "excellent"]
TODAY = date.today()


def haversine_miles(lat1, lon1, lat2, lon2):
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def months_since(iso):
    d = date.fromisoformat(iso)
    return max(0.0, (TODAY - d).days / 30.44)


def lin(diff, cap):
    return max(0.0, 1.0 - abs(diff) / cap) * 100.0 if cap > 0 else 0.0


def similarity(comp):
    """Independent similarity per METHODOLOGY section 2."""
    scores = {}
    if None not in (subject["latitude"], subject["longitude"], comp["latitude"], comp["longitude"]):
        dist = haversine_miles(subject["latitude"], subject["longitude"],
                               comp["latitude"], comp["longitude"])
    else:
        dist = comp["distance_from_subject"]
    if dist is not None:
        scores["proximity"] = lin(dist, P["max_distance_miles"])
    if subject["square_feet"] and comp["square_feet"]:
        scores["living_area"] = lin(comp["square_feet"] - subject["square_feet"],
                                    P["living_area_tolerance"] * subject["square_feet"])
    if subject["bedrooms"] is not None and comp["bedrooms"] is not None:
        scores["bedrooms"] = lin(comp["bedrooms"] - subject["bedrooms"], P["bedroom_cap"])
    if subject["bathrooms"] is not None and comp["bathrooms"] is not None:
        scores["bathrooms"] = lin(comp["bathrooms"] - subject["bathrooms"], P["bathroom_cap"])
    if subject["property_type"] and comp["property_type"]:
        scores["property_type"] = 100.0 if subject["property_type"] == comp["property_type"] else 0.0
    if subject["lot_size"] and comp["lot_size"]:
        scores["lot_size"] = lin(comp["lot_size"] - subject["lot_size"],
                                 P["lot_size_tolerance"] * subject["lot_size"])
    if subject["year_built"] is not None and comp["year_built"] is not None:
        scores["age"] = lin(comp["year_built"] - subject["year_built"], P["age_cap_years"])
    scores["recency"] = lin(months_since(comp["sale_date"]), P["recency_cap_months"])
    sc = CONDITIONS.index(subject["condition"]) if subject["condition"] in CONDITIONS else None
    cc = CONDITIONS.index(comp["condition"]) if comp["condition"] in CONDITIONS else None
    if sc is not None and cc is not None:
        scores["condition"] = lin(cc - sc, P["condition_cap_steps"])
    total_w = sum(W[k] for k in scores if W.get(k, 0) > 0)
    if total_w == 0:
        return None
    return sum(W[k] / total_w * v for k, v in scores.items() if W.get(k, 0) > 0)


def suggested_amounts(comp):
    """Independent adjustment amounts per METHODOLOGY section 3."""
    out = {}
    m = months_since(comp["sale_date"])
    if m > 0 and A["monthly_market_pct"]:
        out["market_time"] = comp["sale_price"] * A["monthly_market_pct"] * m
    if subject["square_feet"] and comp["square_feet"] and A["gla_per_sqft"]:
        d = subject["square_feet"] - comp["square_feet"]
        if d:
            out["living_area"] = d * A["gla_per_sqft"]
    if subject["lot_size"] and comp["lot_size"] and A["lot_per_sqft"]:
        d = subject["lot_size"] - comp["lot_size"]
        if d:
            out["lot_size"] = d * A["lot_per_sqft"]
    if subject["bedrooms"] is not None and comp["bedrooms"] is not None and A["per_bedroom"]:
        d = subject["bedrooms"] - comp["bedrooms"]
        if d:
            out["bedrooms"] = d * A["per_bedroom"]
    if subject["bathrooms"] is not None and comp["bathrooms"] is not None and A["per_bathroom"]:
        d = subject["bathrooms"] - comp["bathrooms"]
        if d:
            out["bathrooms"] = d * A["per_bathroom"]
    sc = CONDITIONS.index(subject["condition"]) if subject["condition"] in CONDITIONS else None
    cc = CONDITIONS.index(comp["condition"]) if comp["condition"] in CONDITIONS else None
    if sc is not None and cc is not None and A["per_condition_step"]:
        d = sc - cc
        if d:
            out["condition"] = d * A["per_condition_step"]
    if (subject["parking_spaces"] is not None and comp["parking_spaces"] is not None
            and A["per_parking_space"]):
        d = subject["parking_spaces"] - comp["parking_spaces"]
        if d:
            out["parking"] = d * A["per_parking_space"]
    if A["pool_value"] and bool(subject["has_pool"]) != bool(comp["has_pool"]):
        out["pool"] = A["pool_value"] * (1 if subject["has_pool"] else -1)
    return out


# ---- 1. Similarity scores & breakdown internals -----------------------------
for comp in comps:
    mine = similarity(comp)
    check("similarity: %s" % comp["address"], mine, comp["selection"]["similarity_score"])
    bd = comp["selection"]["similarity_breakdown"]
    contrib_sum = sum(c["contribution"] for c in bd["components"])
    check("contributions sum = total: %s" % comp["address"], bd["score"], contrib_sum, tol=0.06)
    eff_sum = sum(c["effective_weight"] for c in bd["components"])
    check("effective weights sum to 1: %s" % comp["address"], 1.0, eff_sum, tol=0.002)

# ---- 2. Adjustments & adjusted prices ---------------------------------------
for comp in comps:
    mine = suggested_amounts(comp)
    stored = {a["category"]: a["amount"] for a in comp["adjustments"] if a["source"] == "suggested"}
    check_eq("adjustment categories: %s" % comp["address"], sorted(mine), sorted(stored))
    for cat, amount in mine.items():
        check("adjustment %s: %s" % (cat, comp["address"]), amount, stored.get(cat))
    total = comp["sale_price"] + sum(a["amount"] for a in comp["adjustments"])
    check("adjusted price: %s" % comp["address"], total, comp["adjusted_price"])
    if comp["square_feet"]:
        check("ppsf: %s" % comp["address"], total / comp["square_feet"], comp["adjusted_ppsf"])
    gross = sum(abs(a["amount"]) for a in comp["adjustments"]) / comp["sale_price"]
    check("gross pct: %s" % comp["address"], gross, comp["gross_adjustment_pct"], tol=0.001)

# ---- 3. Reconciliation ------------------------------------------------------
included = [c for c in comps if c["selection"]["included"]]
raw = [(c["selection"]["similarity_score"] / 100.0) * c["selection"]["user_weight_multiplier"]
       for c in included]
values = [c["sale_price"] + sum(a["amount"] for a in c["adjustments"]) for c in included]
tw = sum(raw)
norm = [w / tw for w in raw]
central = sum(w * v for w, v in zip(norm, values))
variance = sum(w * (v - central) ** 2 for w, v in zip(norm, values))
std = math.sqrt(variance)
k = R["range_k"]
sv = sorted(values)
n = len(sv)
median = sv[n // 2] if n % 2 else (sv[n // 2 - 1] + sv[n // 2]) / 2
ppsf_pairs = [(w, v / c["square_feet"]) for w, v, c in zip(norm, values, included)
              if c["square_feet"]]
wppsf = sum(w * p for w, p in ppsf_pairs) / sum(w for w, _ in ppsf_pairs)

check("central estimate", central, valuation["central_estimate"])
check("low estimate", central - k * std, valuation["low_estimate"])
check("high estimate", central + k * std, valuation["high_estimate"])
check("dispersion (weighted std)", std, valuation["dispersion"])
check("cov", std / central, valuation["cov"], tol=0.0001)
check("median adjusted", median, valuation["median_adjusted"])
check("weighted ppsf", wppsf, valuation["weighted_ppsf"])
check_eq("included count", len(included), valuation["included_count"])
for w, c, entry in zip(norm, included, valuation["per_comparable"]):
    check("influence: %s" % c["address"], w * 100, entry["influence_pct"], tol=0.06)
check("influences sum to 100", 100.0,
      sum(e["influence_pct"] for e in valuation["per_comparable"]), tol=0.5)

# ---- 4. Strategies ----------------------------------------------------------
V = valuation["central_estimate"]
for s in strategies:
    d = s["derived"]
    pct = (s["list_price"] - V) / V
    check("strategy %s pct" % s["key"], pct, d["pct_vs_value"], tol=0.0002)
    check("strategy %s dollars" % s["key"], s["list_price"] - V, d["dollar_vs_value"])
    below = sum(1 for v in values if v < s["list_price"])
    check("strategy %s percentile" % s["key"], below / len(values) * 100,
          d["position_percentile"], tol=0.1)
    interest = "High" if pct <= -0.02 else ("Moderate" if pct <= 0.03 else "Low")
    risk = "Low" if pct <= 0 else ("Moderate" if pct <= 0.05 else "High")
    check_eq("strategy %s interest" % s["key"], interest, d["buyer_interest"])
    check_eq("strategy %s risk" % s["key"], risk, d["price_reduction_risk"])
    if not s["is_user_modified"]:
        target = {"market_entry": 0.97, "competitive": 1.00, "aspirational": 1.05}[s["key"]]
        check("strategy %s price = round(V*%s, -3)" % (s["key"], target),
              round(V * target, -3), s["list_price"])

# ---- 5. Sensitivity (one full independent recheck: gla_per_sqft) ------------
gla = next(i for i in sensitivity["items"] if i["assumption"] == "gla_per_sqft")


def central_with(assumption_overrides):
    vals = []
    for c in included:
        manual = [a["amount"] for a in c["adjustments"] if a["source"] == "manual"]
        global A
        saved = A
        A = dict(A, **assumption_overrides)
        sugg = suggested_amounts(c)
        A = saved
        vals.append(c["sale_price"] + sum(manual) + sum(sugg.values()))
    return sum(w * v for w, v in zip(norm, vals))


base = central_with({})
check("sensitivity baseline", base, sensitivity["baseline_central"])
lo = central_with({"gla_per_sqft": A["gla_per_sqft"] * 0.8})
hi = central_with({"gla_per_sqft": A["gla_per_sqft"] * 1.2})
check("sensitivity gla delta_low", lo - base, gla["delta_low"])
check("sensitivity gla delta_high", hi - base, gla["delta_high"])

# ---- Hand-checked anchors (computed on paper, not derived from formulas) ----
oak = next(c for c in comps if c["address"] == "1210 Demo Oak Ave")
# Subject 1850 sq ft, comp 1820: (1850-1820) x $150 = +$4,500
check("hand check: Oak Ave living_area = +4500",
      4500.0, {a["category"]: a["amount"] for a in oak["adjustments"]}["living_area"])
# Subject lot 7200, comp 7100: 100 x $5 = +$500
check("hand check: Oak Ave lot_size = +500",
      500.0, {a["category"]: a["amount"] for a in oak["adjustments"]}["lot_size"])
elm = next(c for c in comps if c["address"] == "987 Fictional Elm St")
adj = {a["category"]: a["amount"] for a in elm["adjustments"]}
# Comp has pool, subject doesn't: -$25,000. Comp 2.5 baths vs 2: -0.5 x 12500.
check("hand check: Elm St pool = -25000", -25000.0, adj["pool"])
check("hand check: Elm St bathrooms = -6250", -6250.0, adj["bathrooms"])

print("checks run: %d" % checks)
if failures:
    print("FAILURES (%d):" % len(failures))
    for f in failures:
        print("  " + f)
    sys.exit(1)
print("ALL CHECKS PASSED: independent recomputation matches the platform.")

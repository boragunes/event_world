#!/usr/bin/env python3
"""Build the ESIO (event-only) vs ESVIO (event+image+IMU) comparison on VECtor.

Reads esvio/vector/<seq>/metrics.json (ESVIO) and esvio/vector-esio/<seq>/metrics.json
(ESIO) and prints a table + writes docs/validation/esio_vector.md.

A run is flagged FAILED if it produced < 30 matched poses or MPE > 100 %
(catastrophic init divergence / non-start).
"""
import json, os, glob

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEQS = ["corner-slow", "robot-normal", "robot-fast", "desk-normal", "desk-fast",
        "sofa-normal", "sofa-fast", "mountain-normal", "mountain-fast",
        "hdr-normal", "hdr-fast"]

def load(algo_dir, seq):
    p = os.path.join(REPO, algo_dir, seq, "metrics.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    return dict(mpe=d["paper_metric"]["MPE_percent_ate"],
                ate=d["ate_translation_m"]["rmse"],
                n=d["n_poses_matched"], length=d["gt_trajectory_length_m"])

def status(m):
    if m is None: return "no-run"
    if m["n"] < 30 or m["mpe"] > 100: return "FAILED"
    return "ok"

def fmt(m):
    if m is None: return "     no-run"
    s = status(m)
    if s == "FAILED":
        return f"  FAILED ({m['n']}p)" if m["n"] < 30 else f"  FAILED({m['mpe']:.0f}%)"
    return f"{m['mpe']:7.3f}% "

rows = []
for seq in SEQS:
    v = load("esvio/vector", seq)
    e = load("esvio/vector-esio", seq)
    rows.append((seq, v, e))

print(f"{'sequence':16s} {'ESVIO (E+F+I)':>16s} {'ESIO (E+I)':>16s}   note")
print("-" * 68)
for seq, v, e in rows:
    note = ""
    if status(v) == "FAILED" and status(e) == "ok":
        note = "ESIO recovers"
    elif status(v) == "ok" and status(e) == "FAILED":
        note = "ESIO fails (init)"
    elif status(v) == "FAILED" and status(e) == "FAILED":
        note = "both fail (fast)"
    elif v and e:
        note = f"ESIO x{e['mpe']/max(v['mpe'],1e-9):.1f} MPE"
    print(f"{seq:16s} {fmt(v):>16s} {fmt(e):>16s}   {note}")

# averages over sequences where BOTH ok
both_ok = [(v, e) for _, v, e in rows if status(v) == "ok" and status(e) == "ok"]
if both_ok:
    import statistics
    av = statistics.mean(v["mpe"] for v, _ in both_ok)
    ae = statistics.mean(e["mpe"] for _, e in both_ok)
    print("-" * 68)
    print(f"{'avg (both ok, n=%d)' % len(both_ok):16s} {av:7.3f}%{'':>8s} {ae:7.3f}%")

if __name__ == "__main__":
    pass

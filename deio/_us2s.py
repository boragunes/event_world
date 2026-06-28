#!/usr/bin/env python3
"""Rewrite a TUM trajectory's microsecond timestamps to seconds. Usage: _us2s.py IN OUT"""
import sys
with open(sys.argv[1]) as f, open(sys.argv[2], "w") as o:
    for ln in f:
        ln = ln.strip()
        if not ln or ln[0] == "#":
            continue
        p = ln.split()
        p[0] = "%.6f" % (float(p[0]) / 1e6)
        o.write(" ".join(p) + "\n")

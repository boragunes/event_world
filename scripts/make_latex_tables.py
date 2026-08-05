#!/usr/bin/env python3
"""Emit LaTeX (booktabs) literature tables + a matching .bib for the SE(3) metric baselines.

Scope matches scripts/make_se3_reference.py --lit-only: only methods that recover metric
scale, only SE(3) full-trajectory values, best value per cell across all reporting papers.

Every cell carries the provenance of its number as a superscript, because the paper that
REPORTS a value is frequently not the paper that PROPOSED the method -- that distinction is
the whole point of RESUBMISSION_PLAN section 6.1.

Missing cells are never a bare dash (section 6.1): they carry \\nr = not reported.

Usage: scripts/make_latex_tables.py            # -> paper_tables/literature_se3.tex + .bib
"""
import csv
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "paper_tables")

METHODS = ["Stereo-DEVO", "ESVO2", "ESVIO", "ESIO", "DEIO", "ES-PTAM"]

# BibTeX key + full entry per source paper, from results_db/papers.csv.
# Venues are the PUBLISHED ones, not arXiv (plan section 9.2 / reviewer R6.5).
BIB = {
    "STEREO_DEVO": ("zhong2025stereodevo", """@article{zhong2025stereodevo,
  author  = {Zhong, Junkai and Niu, Junkai and Zhou, Yi},
  title   = {Stereo Deep Event Visual Odometry},
  journal = {IEEE Robotics and Automation Letters},
  year    = {2025},
  note    = {arXiv:2509.08235}
}"""),
    "ESVO2": ("niu2025esvo2", """@article{niu2025esvo2,
  author  = {Niu, Junkai and Zhong, Sheng and Lu, Xiuyuan and Shen, Shaojie
             and Gallego, Guillermo and Zhou, Yi},
  title   = {{ESVO2}: Direct Visual-Inertial Odometry With Stereo Event Cameras},
  journal = {IEEE Transactions on Robotics},
  year    = {2025},
  note    = {arXiv:2410.09374}
}"""),
    "ESVIO": ("chen2023esvio", """@article{chen2023esvio,
  author  = {Chen, Peiyu and Guan, Weipeng and Lu, Peng},
  title   = {{ESVIO}: Event-Based Stereo Visual Inertial Odometry},
  journal = {IEEE Robotics and Automation Letters},
  volume  = {8},
  number  = {6},
  pages   = {3661--3668},
  year    = {2023}
}"""),
    "DEIO": ("guan2025deio", """@inproceedings{guan2025deio,
  author    = {Guan, Weipeng and Lin, Fuling and Chen, Peiyu and Lu, Peng},
  title     = {{DEIO}: Deep Event Inertial Odometry},
  booktitle = {Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)},
  year      = {2025},
  note      = {arXiv:2411.03928}
}"""),
    "SUPEREVENT": ("burkhardt2025superevent", """@article{burkhardt2025superevent,
  author  = {Burkhardt, Yannick and Schaefer, Simon and Leutenegger, Stefan},
  title   = {{SuperEvent}: Cross-Modal Learning of Event-based Keypoint Detection},
  journal = {arXiv preprint arXiv:2504.00139},
  year    = {2025}
}"""),
}
# Methods whose own paper we have never extracted -- flagged so nobody cites a guess.
NO_BIB = {"ES-PTAM": "not in results_db/papers.csv; fill in before submission."}

# bib key for each METHOD's own paper, for the column headers. ES-PTAM's own paper was
# never extracted, so it gets a stub that compiles but is impossible to miss.
METHOD_CITE = {
    "Stereo-DEVO": "zhong2025stereodevo",
    "ESVO2": "niu2025esvo2",
    "ESVIO": "chen2023esvio",
    "ESIO": "chen2023esvio",      # ESIO is ESVIO's event-only variant, same paper
    "DEIO": "guan2025deio",
    "ES-PTAM": "esptam_FIXME",
}
STUB_BIB = """@misc{esptam_FIXME,
  title = {{FIXME --- add the ES-PTAM reference (Ghosh et al.) by hand}},
  note  = {Placeholder: this paper was never extracted into the results database,
           so no verified bibliographic data exists for it in this repository.}
}"""

PLAN = [
    ("RPG", "rpg", ["rpg_box", "rpg_monitor", "rpg_bin", "rpg_desk", "rpg_reader"]),
    ("MVSEC", "mvsec", ["indoor_flying1", "indoor_flying2", "indoor_flying3", "indoor_flying4"]),
    ("DSEC", "dsec", ["city04_a", "city04_b", "city04_c", "city04_d", "city09_a", "city09_b",
                      "city09_c", "city09_d", "city09_e", "city11_a", "city11_b"]),
    ("VECtor", "vector", ["corner_slow", "robot_normal", "desk_normal", "sofa_normal",
                          "hdr_normal", "corridors_dolly", "units_dolly"]),
    ("TUM-VIE", "tumvie", ["tumvie_1d_trans", "tumvie_3d_trans", "tumvie_6dof",
                           "tumvie_desk", "tumvie_desk2"]),
    ("Other", "other", ["hnu_campus", "drone_fast"]),
]


def tex_escape(s):
    return s.replace("_", r"\_")


def is_se3(x):
    a = (x["alignment"] or "").lower()
    return x["metric_type"] == "metric" and "sim3" not in a and "scale-corrected" not in a


def load_best():
    best = {}
    for x in csv.DictReader(open(f"{ROOT}/results_db/results.csv")):
        if x["method"] not in METHODS or x["metric"] != "ATE" or not x["value"] or not is_se3(x):
            continue
        k = (x["dataset"], x["sequence_norm"] or x["sequence"], x["method"])
        v = float(x["value"])
        if k not in best or v < best[k][0]:
            best[k] = (v, x["paper"], x["table"])
    return best


def fmt(v):
    return f"{v:.2f}" if v < 100 else f"{v:.1f}"


def main():
    os.makedirs(OUT, exist_ok=True)
    best = load_best()

    # provenance markers, ordered by how often each source is used
    used = Counter(v[1] for v in best.values())
    marks = {}
    for i, (paper, _) in enumerate(used.most_common()):
        marks[paper] = chr(ord("a") + i)

    L = []
    A = L.append
    A(r"% Auto-generated by scripts/make_latex_tables.py -- do not edit by hand.")
    A(r"% Requires: \usepackage{booktabs}")
    A(r"% Put these macros in the preamble:")
    A(r"%   \newcommand{\nr}{{\footnotesize\textsc{n/r}}}  % not reported in any source")
    A(r"%   \newcommand{\src}[1]{\textsuperscript{#1}}")
    A(r"% A ready-made preamble block is in paper_tables/preamble.tex")
    A("")
    for name, slug, seqs in PLAN:
        ncol = len(METHODS)
        A(r"\begin{table}[t]")
        A(r"\centering")
        A(r"\caption{Absolute trajectory error (ATE, cm) on " + tex_escape(name) +
          r" for stereo/metric event odometry baselines, taken from the literature. "
          r"All values are SE(3)-aligned full-trajectory results; monocular up-to-scale "
          r"(\mbox{Sim(3)}) results are excluded as they are not the same quantity. "
          r"Where several papers report the same method and sequence we quote the best "
          r"published value. Superscripts give the source of each number, which is not "
          r"always the paper proposing the method. \nr{} marks a cell no surveyed source "
          r"reports; such cells must be produced by us or carry a reason code.}")
        A(r"\label{tab:lit-" + slug + "}")
        A(r"\begin{tabular}{l" + "r" * ncol + "}")
        A(r"\toprule")
        A("Sequence & " + " & ".join(
            f"{tex_escape(m)}\\,\\cite{{{METHOD_CITE[m]}}}" for m in METHODS) + r" \\")
        A(r"\midrule")
        used_here = set()
        for s in seqs:
            cells = []
            for m in METHODS:
                hit = best.get((name, s, m))
                if hit:
                    v, paper, _ = hit
                    used_here.add(paper)
                    cells.append(f"{fmt(v)}\\src{{{marks[paper]}}}")
                else:
                    cells.append(r"\nr")
            A(tex_escape(s) + " & " + " & ".join(cells) + r" \\")
        A(r"\bottomrule")
        A(r"\end{tabular}")
        # per-table provenance legend
        legend = ", ".join(
            f"\\textsuperscript{{{mk}}}\\cite{{{BIB[p][0]}}}"
            for p, mk in sorted(marks.items(), key=lambda kv: kv[1])
            if p in BIB and p in used_here)
        A(r"\\[2pt] {\footnotesize Sources: " + legend + r".}")
        A(r"\end{table}")
        A("")

    open(os.path.join(OUT, "preamble.tex"), "w").write(
        "% Macros required by literature_se3.tex\n"
        "\\usepackage{booktabs}\n"
        "\\newcommand{\\nr}{{\\footnotesize\\textsc{n/r}}}  % not reported in any source\n"
        "\\newcommand{\\src}[1]{\\textsuperscript{#1}}\n")
    tex_path = os.path.join(OUT, "literature_se3.tex")
    open(tex_path, "w").write("\n".join(L))

    # every key that appears in a \cite: source-provenance markers AND method headers
    needed = {p for p in marks if p in BIB}
    for meth, key in METHOD_CITE.items():
        for pkey, (bkey, _) in BIB.items():
            if bkey == key:
                needed.add(pkey)
    bib = [BIB[p][1] for p in sorted(needed)] + [STUB_BIB]
    for m, why in NO_BIB.items():
        bib.append(f"% MISSING: {m}. {why}")
    bib_path = os.path.join(OUT, "literature_se3.bib")
    open(bib_path, "w").write("\n\n".join(bib) + "\n")

    total = sum(len(s) for _, _, s in PLAN) * len(METHODS)
    have = sum(1 for (d, s, m) in best
               if any(d == n and s in ss for n, _, ss in PLAN))
    print(f"wrote {tex_path}")
    print(f"wrote {bib_path}")
    print(f"cells: {have}/{total} reported, {total - have} \\nr")
    print("provenance markers: " + ", ".join(f"{mk}={p}" for p, mk in
                                             sorted(marks.items(), key=lambda kv: kv[1])))
    for m in NO_BIB:
        print(f"WARNING: no bib entry for {m} -- add by hand")


if __name__ == "__main__":
    main()

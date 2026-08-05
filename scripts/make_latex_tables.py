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
    "ESPTAM": ("ghosh2024esptam", """@inproceedings{ghosh2024esptam,
  author    = {Ghosh, Suman and Cavinato, Valentina and Gallego, Guillermo},
  title     = {{ES-PTAM}: Event-based Stereo Parallel Tracking and Mapping},
  booktitle = {European Conference on Computer Vision (ECCV) Workshops},
  year      = {2024}
}"""),
}

# bib key for each METHOD's own paper, for the column headers. Methods whose own paper
# never sources a cell are detected at render time and called out in the caption.
METHOD_CITE = {
    "Stereo-DEVO": "zhong2025stereodevo",
    "ESVO2": "niu2025esvo2",
    "ESVIO": "chen2023esvio",
    "ESIO": "chen2023esvio",      # ESIO is ESVIO's event-only variant, same paper
    "DEIO": "guan2025deio",
    "ES-PTAM": "ghosh2024esptam",
}
# Per-cell footnotes for hazards that a checking reviewer would otherwise read as our error.
FOOT = {
    ("DSEC", "city09_d", "Stereo-DEVO"): r"\textsuperscript{$\dagger$}",
}
# Rendered in the notes block below the tabular: \footnotetext inside a float is dropped.
FOOTNOTE_TEXT = {
    "dsec": r"\textsuperscript{$\dagger$}The source reports two different values for this "
            r"cell: 625.81\,cm in its Table~II and 564.33\,cm in its Table~III. We quote "
            r"the lower under the best-published-value rule.",
}
# Datasets whose published numbers are not computed over the full sequence.
CAVEAT = {
    "mvsec": r"\par\smallskip {\footnotesize \textbf{Sequence caveat.} Sources evaluate "
             r"the \emph{edited} MVSEC bags (\texttt{indoor\_flying*\_data\_edited}), and "
             r"further restrict scoring to a sub-window of those: the trajectories released "
             r"with~\cite{niu2025esvo2} span 25.8, 24.2, 25.0 and 5.9\,s against ground truth "
             r"of 70.3, 84.9, 94.0 and 19.8\,s respectively. Numbers here are therefore "
             r"$\approx$26--37\% windows, not whole sequences, and are not comparable with a "
             r"full-sequence run.}",
}

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
    """-> best[(ds, seq, method)] = (value, paper, table)
       failed[(ds, seq, method)] = {papers that explicitly report a failure}

    A source that reports "failed" is asserting a measured outcome: the method ran and
    did not produce a usable trajectory. A source that simply omits the cell asserts
    nothing. Collapsing the two would discard the baseline failure rate, so they are
    tracked separately and rendered with different markers.
    """
    best, failed = {}, {}
    for x in csv.DictReader(open(f"{ROOT}/results_db/results.csv")):
        if x["method"] not in METHODS or x["metric"] != "ATE" or not is_se3(x):
            continue
        k = (x["dataset"], x["sequence_norm"] or x["sequence"], x["method"])
        if x["value"]:
            v = float(x["value"])
            if k not in best or v < best[k][0]:
                best[k] = (v, x["paper"], x["table"])
        elif x["status"] == "failed":
            failed.setdefault(k, set()).add(x["paper"])
    return best, failed


def fmt(v):
    return f"{v:.2f}" if v < 100 else f"{v:.1f}"


def main():
    os.makedirs(OUT, exist_ok=True)
    best, failed = load_best()

    # provenance markers, ordered by how often each source is used
    used = Counter([v[1] for v in best.values()] +
                   [p for ps in failed.values() for p in ps])
    marks = {}
    for i, (paper, _) in enumerate(used.most_common()):
        marks[paper] = chr(ord("a") + i)

    # a method is "second-hand" if its own paper is never the source of any of its cells
    own = {m: METHOD_CITE[m] for m in METHODS}
    src_keys = {BIB[p][0] for p in marks if p in BIB}
    SECOND_HAND = {m for m in METHODS if own[m] not in src_keys}

    L = []
    A = L.append
    A(r"% Auto-generated by scripts/make_latex_tables.py -- do not edit by hand.")
    A(r"% Requires: \usepackage{booktabs}")
    A(r"% Put these macros in the preamble:")
    A(r"%   \newcommand{\nr}{{\footnotesize\textsc{n/r}}}  % not reported in any source")
    A(r"%   \newcommand{\src}[1]{\textsuperscript{#1}}")
    A(r"%   \newcommand{\fail}{{\footnotesize\textsc{fail}}}  % source reports a failure")
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
          r"published value, so each column is a \emph{composite upper bound} over all "
          r"published results rather than any single reported configuration: no baseline "
          r"is understated, and no one configuration ever achieved these numbers "
          r"simultaneously. Superscripts give the source of each number, which is not "
          r"always the paper proposing the method. \nr{} marks a cell no surveyed source "
          r"reports; such cells must be produced by us or carry a reason code. "
          r"\fail{} marks a cell a source explicitly reports as a failure, which is a "
          r"measured outcome rather than missing data." +
          (r" Every " + ", ".join(sorted(SECOND_HAND)) + r" value is second-hand: its own "
           r"paper is not the source of any cell here." if SECOND_HAND else "") + r"}")
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
                k = (name, s, m)
                hit = best.get(k)
                if hit:
                    v, paper, _ = hit
                    used_here.add(paper)
                    cells.append(f"{fmt(v)}\\src{{{marks[paper]}}}" + FOOT.get(k, ""))
                elif k in failed:
                    fp = sorted(failed[k])[0]
                    used_here.add(fp)
                    cells.append(f"\\fail\\src{{{marks.get(fp, '?')}}}")
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
        note = "Sources: " + legend + "."
        if slug in FOOTNOTE_TEXT:
            note += r" \\ " + FOOTNOTE_TEXT[slug]
        A(r"\\[2pt] {\footnotesize " + note + r"}")
        if slug in CAVEAT:
            A(CAVEAT[slug])
        A(r"\end{table}")
        A("")

    open(os.path.join(OUT, "preamble.tex"), "w").write(
        "% Macros required by literature_se3.tex\n"
        "\\usepackage{booktabs}\n"
        "\\newcommand{\\nr}{{\\footnotesize\\textsc{n/r}}}  % not reported in any source\n"
        "\\newcommand{\\src}[1]{\\textsuperscript{#1}}\n"
        "\\newcommand{\\fail}{{\\footnotesize\\textsc{fail}}}  % source reports a failure\n")
    tex_path = os.path.join(OUT, "literature_se3.tex")
    open(tex_path, "w").write("\n".join(L))

    # every key that appears in a \cite: source-provenance markers AND method headers
    needed = {p for p in marks if p in BIB}
    for meth, key in METHOD_CITE.items():
        for pkey, (bkey, _) in BIB.items():
            if bkey == key:
                needed.add(pkey)
    bib = [BIB[p][1] for p in sorted(needed)]
    bib_path = os.path.join(OUT, "literature_se3.bib")
    open(bib_path, "w").write("\n\n".join(bib) + "\n")

    inplan = {(n, sq) for n, _, ss in PLAN for sq in ss}
    total = len(inplan) * len(METHODS)
    have = sum(1 for (d, s, m) in best if (d, s) in inplan)
    nfail = sum(1 for (d, s, m) in failed if (d, s) in inplan and (d, s, m) not in best)
    print(f"wrote {tex_path}")
    print(f"wrote {bib_path}")
    print(f"cells: {have} reported, {nfail} FAIL (source says it failed), "
          f"{total - have - nfail} n/r, of {total}")
    print("provenance markers: " + ", ".join(f"{mk}={p}" for p, mk in
                                             sorted(marks.items(), key=lambda kv: kv[1])))
    for m in SECOND_HAND:
        print(f"NOTE: every {m} value is second-hand (its own paper sources no cell)")


if __name__ == "__main__":
    main()

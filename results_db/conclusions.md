# Author conclusions per table (the "asterisks")

For every results table in the database, the conclusion(s) the **authors themselves** drew.
Each entry is keyed `PAPER — Table N (dataset, metric)`. These are the authors' claims, not ours;
where our own benchmark (`event_world`) found something different, it is flagged `>> OUR NOTE`.

Colour/provenance: see `papers.csv` for the per-paper colour used in `results.tex`.

---

## Ultimate SLAM — Vidal et al., RAL 2018 (1709.06310)
- **Table I (ECD, MPE%/Yaw)** — Fusing frames+events+IMU improves mean position accuracy by **~85%** vs
  frames+IMU and **~130%** vs events+IMU. Frames can still help over events-only on textured scenes
  (e.g. boxes_translation, shapes_6dof).
- **Table II (ECD, MPE%/Yaw)** — Ultimate SLAM (Fr+E+I) beats the prior SOTA event-inertial method
  Rebecq et al. [13] (E+I) on almost all sequences.

## EVIO (Zhu) — Zhu et al., CVPR 2017 (Zhu2017)
- **Table 1 (ECD, MPE%/MRE)** — First EKF that fuses events+IMU for metric 6-DoF tracking; comparable
  to a KLT-frame VIO baseline, markedly better in HDR (hdr_boxes). *These EVIO numbers are exactly the
  "Zhu et al." baseline reused by PL-EVIO T.III and DEIO T.I.*

## ESVO — Zhou et al., TRO 2021 (2007.15548 / Event-Based Stereo VO)
- **Table V (RPG+MVSEC, RPE)** & **Table VI (RPG, ATE)** — First fully event-based **stereo** VO.
  ORB-SLAM2 (frames, esp. with BA) is best overall; ESVO is SOTA among event-only methods and is
  clearly best on the fast drone (UPenn/MVSEC flying) sequences.
  >> OUR NOTE: ESVO's own rpg_monitor ATE = **1.3 cm**, but every later paper that re-ran ESVO
     (DEVO, ESVO2, Stereo-DEVO) reports **3.3 cm** — a reproduction gap, see `discrepancies.csv`.

## EDS — Hidalgo-Carrió et al., CVPR 2022 (Hidalgo2022)
- **Table 2 (RPG, ATE/ARE vs event methods)** — EDS (mono event+frame) outperforms all monocular
  baselines and even the event-only **stereo** ESVO, despite using no stereo parallax and no IMU.
- **Table 3 (RPG, ATE/ARE vs frame methods)** — EDS is consistently better than mono ORB-SLAM, on par
  with DSO, and only slightly worse than stereo ORB-SLAM (F+F) with BA (the best overall).

## PL-EVIO — Guan et al., TASE 2024 (PLEVIO2024)
- **Table I (arclab vicon, DAVIS346 & DVXplorer, MPE%)** — Adding line features (PL-EIO) clearly beats
  the base Mono-EIO; adding images (PL-EVIO) is best in most seqs but **underperforms PL-EIO in
  low-light** (vicon_dark1/2) because image point tracking degrades. Motion compensation (PL-EIO+) gives
  little gain under aggressive motion (IMU bias).
- **Table II (UZH-FPV, MPE%)** — PL-EVIO (mono DAVIS346) beats stereo VIO on a higher-res camera; most
  Ultimate-SLAM and VINS-Fusion runs fail on this aggressive dataset.
- **Table III (ECD, MPE%)** — PL-EVIO is SOTA among EIO/EVIO methods on the classic DAVIS240C benchmark.

## ESVIO — Chen et al., RAL 2023 (2212.13184)
- **Table I (HKU, MPE/MRE)** — First stereo event-inertial system; the big win is **rotation** accuracy
  (avg MRE 0.033 deg/m vs ORB-SLAM3 0.12). Motion-compensated ESIO+ beats ESIO on average (opposite to
  what PL-EVIO found). EVO and ESVO fail on all HKU seqs (strict init, parameter sensitivity).
- **Table II (VECtor+MVSEC, MPE/MRE)** — First VECtor results for a stereo-EVIO method; ESVIO is most
  reliable on large-scale/HDR, though ORB-SLAM3 edges it on a few small "normal" seqs.

## DEVO — Klenk et al., 3DV 2024 (2312.09800)
- **Table 1 (UZH-FPV, MPE)** — Event-only DEVO beats all related work on 4/9; the only successful
  non-IMU peer is its own event-trained DPVO† baseline.
- **Table 2 (VECtor, MPE/ATE)** — DEVO (events only) beats ESVIO (stereo E+F+I) on ~70% of seqs;
  frame methods retain a high-res global-shutter advantage.
- **Table 3 (HKU, MPE/ATE)** — Beats prior work on 5/9; agg_flip/hdr_circle/hdr_slow have sensor
  dropouts; DEVO needs top-P sampling to not fail on agg_walk.
- **Table 4 (EDS, ATE/MPE)** — First pose-estimation results on EDS; clearly beats DPVO on HDR/fast
  (rocket_dark, ziggy_hdr, all_chars). *Here ORB-SLAM3 is monocular (up-to-scale), unlike DEIO T.VI.*
- **Table 5 (TUM-VIE, ATE)** — Beats event-only peers by >=44%; beats even DH-PTAM (4 cameras) on 4/5.
- **Table 6 (RPG, ATE)** — Beats event-only methods by >=63%, USLAM by 88%, EDSO by 28%.
- **Table 7 (MVSEC, MPE/ATE)** — First event-only method that fails on no MVSEC seq; ATE avg 65% lower
  than ESVIO; still worse than frame DPVO due to MVSEC's biased polarity ratio (neg:pos = 3.2).
- **Tables 8–9 (ablation, not in DB)** — photometric voxel augmentation and the learned grid-pooled
  multinomial patch sampler both improve accuracy and robustness.

## ESVO2 — Niu et al., 2024 (2410.09374)
- **Table VI (ARE/ATE)** & **Table VII (RPE)** across RPG/MVSEC/DSEC/VECtor/TUM-VIE — Direct stereo
  event + IMU. ESVO2 is best or near-best on essentially all sequences and is dramatically better than
  ESVO/ESIO/ESVIO on large-scale DSEC. (ATE, ARE, RPE_t and RPE_R all captured.)
- **Tables VIII–IX (ablation, not in DB)** — edge-pixel sampling and the IMU back-end each contribute;
  IMU is necessary for the fast/large-scale seqs.

## DEIO — Guan et al., ICCV 2025 (2411.03928)
- **Table I (ECD, MPE)** — Among non-learning methods EVI-SAM is best; DEIO (learning+IMU) cuts pose
  error up to **71%** vs DEVO. Learning methods (DEVO) rival EVI-SAM using events only.
- **Table II (Mono-HKU vicon, MPE)** — DEIO cuts avg error >=47% vs event baselines; *scale is NOT
  aligned here (metric)*, and DEVO visibly loses scale (mono-event is up-to-scale).
- **Table III (Stereo-HKU, MPE)** — Best average among event methods (full-traj SE3).
- **Table IV (VECtor, MPE)** — DEIO surpasses all image baselines and beats USLAM/PL-EVIO/ESVIO/EVI-SAM
  on >75% of seqs.
  >> OUR NOTE (central finding of our reproduction): these headline VECtor MPE numbers rely on
     **scale-corrected (Sim3)** alignment. Under honest metric (SE3) eval DEIO's released VECtor
     trajectories are **scale-broken** — independently confirmed by **Stereo-DEVO T.II** (DEIO ATE
     254.76 cm on desk_normal, 826.73 cm on units_dolly) and **SuperEvent T.5** (DEIO ATE 492.65 cm on
     corridors_dolly). DEIO *is* genuinely strong & metric on TUM-VIE.
- **Table V (TUM-VIE, ATE)** — Best on 4/5; learning data association already saturates these easy seqs.
- **Table VI (EDS, ATE)** — First event-inertial EDS results; on par with RAMP-VO; beats image-based
  DBA-Fusion by ~80% on HDR ziggy_hdr.
- **Table VII (MVSEC, MPE)** — Best average across all 4 indoor_flying seqs.
- **Table VIII (UZH-FPV, MPE)** — DPVO/DBA-Fusion/EVO/USLAM all fail on every seq (motion blur); DEIO
  best average. Gain over DEVO is modest (aggressive-motion IMU bias).
- **Table IX (DSEC, ATE)** — DEIO (mono!) beats stereo-event baselines by >=66.7% on all seqs.
  GT here is a LiDAR-IMU pseudo-GT (DSEC has no true 6-DoF GT).
- **Table X (ablation, not in DB)** — 96 event patches per voxel is the accuracy/compute sweet spot
  (avg MPE 0.065; P120 0.063; P48 0.071; P96 without IMU 0.219).

## SuperEvent — Burkhardt et al., 2025 (2504.00139)
- **Tables 2–3 (ECD/EDS, keypoint relative-pose AUC, HIGHER better)** — SuperEvent dominates LLAK/RATE/
  EventPoint by a large margin, especially at high precision (<5 deg); generalizes across cameras.
- **Table 4 (TUM-VIE, ATE)** — OKVIS2+SuperEvent (metric stereo E+I) is best at 0.55 cm avg.
  >> The authors explicitly mark DEVO/DEIO results as requiring **scale alignment**; DEIO metric = 1.24
     vs scale-aligned = 1.00 — corroborates the DEIO scale caveat above.
- **Table 5 (VECtor large-scale, ATE)** — OKVIS2+SuperEvent best; DEIO ATE 492.65/826.38 cm = metric
  scale failure; DEVO omitted because "it cannot recover the absolute scale".
- **Table 6 (TUM-VIE loop-floor, ATE)** — loop closure cuts ATE ~30x on the long corridor-loop seqs.

## Stereo-DEVO — Zhong et al., RAL 2025 (2509.08235)
- **Table II (RPG/MVSEC/DSEC/VECtor/TUM-VIE, RPE/ATE)** — Deep **stereo** event VO (no IMU; stereo gives
  metric scale). Best or 2nd-best on every sequence. Drops DEVO entirely "because its poses suffer from
  scale ambiguity".
  >> Independently exposes DEIO's scale problem: under metric eval DEIO shows huge errors on VECtor
     (desk_normal 254.76 cm) and DSEC (city04_c 9128.73 cm) while staying strong on TUM-VIE — the
     authors attribute this to "improper weight between IMU and visual constraints" and note DEIO's raw
     initial poses differ from other methods (inflating its RPE).
- **Table III (DSEC/VECtor vs ESVIO, RPE/ATE)** — Stereo-DEVO beats image-aided ESVIO on all DSEC;
  ESVIO wins the small VECtor normal/HDR seqs, Stereo-DEVO wins large-scale.
- **Tables IV–V (ablation/compute, not in DB)** — the learned update + stereo association beats ZNCC;
  runs ~real-time on desktop, slower on Jetson Orin NX.

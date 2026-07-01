#!/usr/bin/env python3
"""
build_db.py — single source of truth for the event-camera VO/VIO results database.

Each results TABLE from each paper is encoded ONCE as a compact matrix
(rows = methods, cols = sequences), mirroring exactly how it appears in the paper.
This script expands those matrices into:

  results.csv        long-form, one row per (paper, table, method, dataset, seq, metric)
  results.tex        color-coded LaTeX longtable (one color per paper)
  leaderboard.csv    best reported value per (dataset, sequence, metric)
  leaderboard.md     human-readable best-result lookup
  papers.csv         paper metadata

Run:  python3 build_db.py
Query best result:   python3 build_db.py --best VECtor [sequence] [metric]

Conventions
-----------
* value: float, or the string "failed" (ran but diverged) / "-" (not reported).
* lower-is-better for every error metric here (ATE, MPE, MRE, ARE, RPE, Rrmse, RPE_R/t).
  AUC (SuperEvent keypoint tables) is higher-is-better -> marked separately.
* metric_type: "metric"  = method outputs absolute (metric) scale (has IMU and/or stereo);
               "up-to-scale" = monocular vision-only, needs Sim3 scale alignment for ATE/MPE.
* alignment: how GT alignment was done for that table (SE3 / Sim3 / posyaw-5s / etc.),
  as stated by the paper. This matters: a "metric" method scored under Sim3 can hide a
  broken metric scale (the central finding of our own DEIO/VECtor reproduction).
"""
import csv, sys, os, re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Paper metadata.  color = hex used for that paper's provenance tag in the TeX.
# ---------------------------------------------------------------------------
PAPERS = {
 "ULTIMATE_SLAM": dict(short="Ultimate SLAM", authors="Vidal et al.", venue="RAL", year=2018,
    cite="1709.06310", proposed="Ultimate SLAM", color="8B4513"),
 "ZHU_EVIO": dict(short="EVIO (Zhu)", authors="Zhu et al.", venue="CVPR", year=2017,
    cite="Zhu2017", proposed="EVIO", color="A0522D"),
 "EDS": dict(short="EDS", authors="Hidalgo-Carrio et al.", venue="CVPR", year=2022,
    cite="Hidalgo2022", proposed="EDS", color="2E8B57"),
 "PLEVIO": dict(short="PL-EVIO", authors="Guan et al.", venue="TASE", year=2024,
    cite="PLEVIO2024", proposed="PL-EVIO / PL-EIO", color="1F77B4"),
 "ESVIO": dict(short="ESVIO", authors="Chen et al.", venue="RAL", year=2023,
    cite="2212.13184", proposed="ESVIO / ESIO", color="9467BD"),
 "ESVO": dict(short="ESVO", authors="Zhou et al.", venue="TRO", year=2021,
    cite="2007.15548", proposed="ESVO", color="17BECF"),
 "ESVO2": dict(short="ESVO2", authors="Niu et al.", venue="arXiv/TRO", year=2024,
    cite="2410.09374", proposed="ESVO2", color="E377C2"),
 "DEVO": dict(short="DEVO", authors="Klenk et al.", venue="3DV", year=2024,
    cite="2312.09800", proposed="DEVO", color="FF7F0E"),
 "DEIO": dict(short="DEIO", authors="Guan et al.", venue="ICCV", year=2025,
    cite="2411.03928", proposed="DEIO", color="D62728"),
 "SUPEREVENT": dict(short="SuperEvent", authors="Burkhardt et al.", venue="arXiv", year=2025,
    cite="2504.00139", proposed="OKVIS2+SuperEvent", color="7F7F7F"),
 "STEREO_DEVO": dict(short="Stereo-DEVO", authors="Zhong et al.", venue="RAL", year=2025,
    cite="2509.08235", proposed="Stereo-DEVO", color="BCBD22"),
}

# ---------------------------------------------------------------------------
# Sequence-name normalization so the same physical sequence collides across
# papers in the leaderboard (papers spell them differently).
# ---------------------------------------------------------------------------
SEQ_ALIAS = {
 # VECtor small-scale
 "corner-slow":"corner_slow","corner slow":"corner_slow",
 "robot-norm":"robot_normal","robot normal":"robot_normal","robot-normal":"robot_normal",
 "robot-fast":"robot_fast","robot fast":"robot_fast",
 "desk-norm":"desk_normal","desk normal":"desk_normal","desk-normal":"desk_normal",
 "desk-fast":"desk_fast","sofa-norm":"sofa_normal","sofa normal":"sofa_normal","sofa-normal":"sofa_normal",
 "sofa-fast":"sofa_fast","mount-norm":"mountain_normal","mountain-normal":"mountain_normal",
 "mount-fast":"mountain_fast","mountain-fast":"mountain_fast",
 "hdr-normal":"hdr_normal","hdr-fast":"hdr_fast",
 "corr-dolly":"corridors_dolly","corridors-dolly":"corridors_dolly","corr.-dolly":"corridors_dolly","corridors dolly":"corridors_dolly",
 "corr-walk":"corridors_walk","corridors-walk":"corridors_walk","corr.-walk":"corridors_walk",
 "school-dolly":"school_dolly","school-scooter":"school_scooter",
 "units-dolly":"units_dolly","units dolly":"units_dolly","units-scooter":"units_scooter",
 # MVSEC indoor flying
 "indoor flying 1":"indoor_flying1","indoor fly1":"indoor_flying1","flying 1":"indoor_flying1",
 "indoor1 edited":"indoor_flying1","indoor 1":"indoor_flying1",
 "indoor flying 2":"indoor_flying2","indoor fly2":"indoor_flying2","flying 2":"indoor_flying2",
 "indoor2 edited":"indoor_flying2","indoor 2":"indoor_flying2",
 "indoor flying 3":"indoor_flying3","indoor fly3":"indoor_flying3","flying 3":"indoor_flying3",
 "indoor3 edited":"indoor_flying3","indoor 3":"indoor_flying3",
 "indoor flying 4":"indoor_flying4","indoor fly4":"indoor_flying4","flying 4":"indoor_flying4",
 "indoor4 edited":"indoor_flying4","indoor 4":"indoor_flying4",
 # RPG
 "rpg bin":"rpg_bin","rpg_boxes2":"rpg_box","rpg boxes2":"rpg_box","rpg box":"rpg_box","boxes":"rpg_box",
 "rpg_desk2":"rpg_desk","rpg desk2":"rpg_desk","rpg desk":"rpg_desk","rpg_monitor2":"rpg_monitor",
 "rpg monitor2":"rpg_monitor","rpg monitor":"rpg_monitor","monitor":"rpg_monitor","bin":"rpg_bin","desk":"rpg_desk",
 "rpg reader":"rpg_reader","reader":"rpg_reader",
 # TUM-VIE mocap
 "mocap-1d-trans":"tumvie_1d_trans","1d-trans":"tumvie_1d_trans","1d trans":"tumvie_1d_trans",
 "mocap-3d-trans":"tumvie_3d_trans","3d-trans":"tumvie_3d_trans","3d trans":"tumvie_3d_trans",
 "mocap-6dof":"tumvie_6dof","6dof":"tumvie_6dof","6d-trans":"tumvie_6dof","6d trans":"tumvie_6dof",
 "mocap-desk":"tumvie_desk","mocap-desk2":"tumvie_desk2",
 # UZH-FPV indoor_forward
 "indoor_forward_3":"uzhfpv_if3","indoor forward 3":"uzhfpv_if3",
 "indoor_forward_5":"uzhfpv_if5","indoor_forward_6":"uzhfpv_if6","indoor_forward_7":"uzhfpv_if7",
 "indoor_forward_9":"uzhfpv_if9","indoor_forward_10":"uzhfpv_if10",
 "indoor_45_degree_2":"uzhfpv_45_2","indoor_45_degree_4":"uzhfpv_45_4","indoor_45_degree_9":"uzhfpv_45_9",
}
def norm_seq(s):
    k = s.strip().lower()
    if k in SEQ_ALIAS: return SEQ_ALIAS[k]
    return k.replace(" ", "_").replace("-", "_")

# ---------------------------------------------------------------------------
TABLES = []
def add(**kw):
    """Register one table block.  See the data section below for the schema."""
    TABLES.append(kw)

# =========================== INSERT TABLE DATA BELOW ===========================
# (data blocks are added here by the build; marker line -- do not remove)
# ----------------------------- DEIO (2411.03928) -----------------------------
add(paper="DEIO", table="I", dataset="ECD (DAVIS240C)", metric="MPE", unit="%",
    align="SE3, first 5 s (pos+yaw)",
    note="ECD/Event-Camera-Dataset, 240x180. Authors' takeaway: among non-learning methods "
         "EVI-SAM is best; DEIO cuts pose error up to 71% vs DEVO via learning+IMU.",
    methods=[("Zhu et al.","E+I",False),("Rebecq EVIO","E+I",False),
        ("Ultimate-SLAM (EIO)","E+I",False),("Ultimate-SLAM (EVIO)","E+F+I",False),
        ("Jung et al. (EIO)","E+I",False),("Jung et al. (EVIO)","E+F+I",False),
        ("HASTE-VIO","E+I",False),("EKLT-VIO","E+F+I",False),("Dai et al.","E+I",False),
        ("Mono-EIO","E+I",False),("Kai et al.","E+I",False),("PL-EVIO","E+F+I",False),
        ("Lee et al.","E+F+I",False),("EVI-SAM","E+F+I",False),("DPVO","F",False),
        ("DBA-Fusion","F+I",False),("DEVO","E",False),("DEIO","E+I",True)],
    seqs=["boxes_translation","hdr_boxes","boxes_6dof","dynamic_translation","dynamic_6dof",
          "poster_translation","hdr_poster","poster_6dof","average"],
    values=[
     [2.69,1.23,3.61,1.90,4.07,0.94,2.63,3.56,2.58],
     [0.57,0.92,0.69,0.47,0.54,0.89,0.59,0.82,0.69],
     [0.76,0.67,0.44,0.59,0.38,0.15,0.49,0.30,0.47],
     [0.27,0.37,0.30,0.18,0.19,0.12,0.31,0.28,0.25],
     [1.50,2.45,2.88,4.92,6.23,3.43,2.38,2.53,3.92],
     [1.24,1.15,0.98,0.89,0.98,1.83,0.57,0.97,1.07],
     [2.55,1.75,2.03,1.32,0.52,1.34,0.57,1.50,1.45],
     [0.48,0.46,0.84,0.40,0.79,0.35,0.65,0.35,0.54],
     [1.0,1.8,1.5,0.9,1.5,1.9,2.8,1.2,1.56],
     [0.34,0.40,0.61,0.26,0.43,0.40,0.40,0.26,0.39],
     [0.36,0.31,0.32,0.59,0.49,0.23,0.18,0.31,0.35],
     [0.06,0.10,0.21,0.24,0.48,0.54,0.12,0.14,0.24],
     [0.74,0.69,0.77,0.71,0.86,0.28,0.52,0.59,0.65],
     [0.11,0.13,0.16,0.30,0.27,0.34,0.15,0.24,0.21],
     [0.02,0.71,0.59,0.09,0.05,0.20,0.49,0.44,0.32],
     [0.07,0.27,0.10,0.56,0.11,0.13,0.38,0.19,0.23],
     [0.06,0.06,0.71,0.09,0.08,0.06,0.14,0.44,0.21],
     [0.07,0.09,0.05,0.06,0.04,0.04,0.06,0.08,0.06]])

add(paper="DEIO", table="II", dataset="Mono-HKU (arclab vicon)", metric="MPE", unit="%",
    align="SE3, first 5 s, no scale-align (metric)",
    note="arclab-HKU DAVIS346 'vicon_*' handheld HDR/low-light. DEIO cuts avg error >=47% vs "
         "event baselines; DEVO suffers visible scale loss (mono-event up-to-scale).",
    methods=[("ORB-SLAM3","F",False),("VINS-MONO","F+I",False),("DBA-Fusion","F+I",False),
        ("Ultimate-SLAM (EIO)","E+I",False),("Ultimate-SLAM (EVIO)","E+F+I",False),
        ("Mono-EIO","E+I",False),("PL-EIO","E+I",False),("PL-EVIO","E+F+I",False),
        ("DEVO","E",False),("DEIO","E+I",True)],
    seqs=["vicon_hdr1","vicon_hdr2","vicon_hdr3","vicon_hdr4","vicon_darktolight1",
          "vicon_darktolight2","vicon_lighttodark1","vicon_lighttodark2","vicon_dark1","vicon_dark2","average"],
    values=[
     [0.32,0.75,0.60,0.70,0.75,0.76,0.41,0.58,"failed",0.60,0.61],
     [0.96,1.60,2.28,1.40,0.51,0.98,0.55,0.55,0.88,0.52,1.02],
     [0.32,0.41,"failed","failed",0.72,0.55,"failed",2.65,3.32,"failed",1.33],
     [1.49,1.28,0.66,1.84,1.33,1.48,1.79,1.32,1.75,1.10,1.40],
     [2.44,1.11,0.83,1.49,1.00,0.79,0.84,1.49,3.45,0.63,1.41],
     [0.59,0.74,0.72,0.37,0.81,0.42,0.29,0.79,1.02,0.49,0.62],
     [0.57,0.54,0.69,0.32,0.66,0.51,0.33,0.53,0.35,0.38,0.49],
     [0.17,0.12,0.19,0.11,0.14,0.12,0.13,0.16,0.43,0.47,0.20],
     [0.11,0.07,0.12,0.07,0.97,0.12,0.15,0.12,0.07,0.07,0.19],
     [0.14,0.09,0.16,0.07,0.11,0.10,0.11,0.13,0.05,0.08,0.10]])

add(paper="DEIO", table="III", dataset="HKU (stereo)", metric="MPE", unit="%",
    align="SE3, full trajectory (metric)",
    note="arclab-HKU stereo DAVIS346 'hku_agg/hdr'. DPVO/DEVO baselines taken from DEVO paper; "
         "Kai et al. from [42]. DEIO best avg among event methods.",
    methods=[("ORB-SLAM3","Stereo F+I",False),("VINS-Fusion","Stereo F+I",False),
        ("EnVIO","Stereo F+I",False),("MSOC-S-IKF","Stereo F+I",False),("DPVO","F",False),
        ("DBA-Fusion","F+I",False),("Kai et al.","E+I",False),("PL-EVIO","E+F+I",False),
        ("EVI-SAM","E+F+I",False),("ESIO","Stereo E+I",False),("ESVIO","Stereo E+F+I",False),
        ("DEVO","E",False),("DEIO","E+I",True)],
    seqs=["agg_translation","agg_rotation","agg_flip","agg_walk","hdr_circle","hdr_slow",
          "hdr_tran_rota","hdr_agg","dark_normal","average"],
    values=[
     [0.15,0.35,0.36,"failed",0.17,0.16,0.30,0.29,"failed",0.25],
     [0.11,1.34,1.16,"failed",5.03,0.13,0.11,1.21,0.86,1.24],
     ["failed",2.12,2.94,3.38,0.85,0.43,0.37,0.50,"failed",1.51],
     ["failed",1.52,"failed","failed","failed","failed","failed","failed","failed",1.52],
     [0.07,0.04,0.99,1.17,0.31,0.23,0.67,0.29,"failed",0.47],
     [0.13,0.16,0.83,0.37,0.18,"failed","failed",0.10,0.27,0.29],
     [0.21,0.28,0.81,0.35,0.71,0.43,0.50,0.27,0.52,0.45],
     [0.07,0.23,0.39,0.42,0.14,0.13,0.10,0.14,1.35,0.33],
     [0.17,0.24,0.32,0.26,0.13,0.11,0.11,0.10,0.85,0.25],
     [0.55,0.78,3.17,1.30,0.46,0.31,0.91,1.41,0.35,1.03],
     [0.10,0.17,0.36,0.31,0.16,0.11,0.10,0.10,0.42,0.20],
     [0.06,0.05,0.71,0.90,0.39,0.08,0.08,0.26,0.06,0.29],
     [0.06,0.09,0.20,0.48,0.14,0.07,0.09,0.06,0.11,0.15]])

add(paper="DEIO", table="IV", dataset="VECtor", metric="MPE", unit="%",
    align="full-trajectory, SCALE-CORRECTED (Sim3) -- see note",
    note="*** CAVEAT: DEIO is a metric (E+I) method, but its released VECtor trajectories are "
         "metric-scale-broken; these headline MPE numbers rely on scale correction (Sim3). "
         "Independently corroborated: Stereo-DEVO T.II reports DEIO VECtor ATE up to 254.76 cm "
         "(desk_normal) and SuperEvent T.5 reports DEIO ATE 492.65 cm (corridors_dolly) under "
         "metric eval. Our own reproduction reaches these MPE under Sim3 too.",
    methods=[("ORB-SLAM3","Stereo F+I",False),("VINS-Fusion","Stereo F+I",False),
        ("DPVO","F",False),("DBA-Fusion","F+I",False),("EVO","E",False),("ESVO","Stereo E",False),
        ("Ultimate-SLAM","E+F+I",False),("PL-EVIO","E+F+I",False),("ESVIO","Stereo E+F+I",False),
        ("EVI-SAM","E+F+I",False),("DEVO","E",False),("DEIO","E+I",True)],
    seqs=["corner_slow","desk_normal","sofa_fast","mountain_fast","corridors_dolly",
          "corridors_walk","units_dolly","units_scooter","average"],
    values=[
     [1.49,0.46,0.21,2.11,1.03,1.32,7.64,6.22,2.81],
     [1.61,0.47,0.57,"failed",1.88,0.50,4.39,4.92,2.05],
     [0.30,0.09,0.07,0.11,0.56,0.54,1.52,1.67,0.61],
     [1.72,0.48,0.43,"failed",1.37,0.59,1.23,0.48,0.90],
     [4.33,"failed","failed","failed","failed","failed","failed","failed",4.33],
     [4.83,"failed","failed","failed","failed","failed","failed","failed",4.83],
     [4.83,2.24,2.54,4.13,"failed","failed","failed","failed",3.44],
     [2.10,3.66,0.17,0.13,1.58,0.92,5.84,5.00,2.92],
     [1.49,0.61,0.17,0.16,1.13,0.43,3.43,2.85,1.41],
     [2.50,1.45,0.98,0.38,1.58,1.27,0.59,0.83,1.32],
     [0.59,0.11,0.38,0.37,0.51,1.04,0.48,0.88,0.55],
     [0.50,0.13,0.44,0.24,0.78,0.74,0.35,0.35,0.44]])
add(paper="DEIO", table="V", dataset="TUM-VIE", metric="ATE", unit="cm",
    align="full trajectory (metric; DEVO/EVO up-to-scale via Sim3)",
    note="TUM-VIE mocap room, 1280x720 stereo events. DH-PTAM uses all 4 cameras. DEIO best on 4/5.",
    methods=[("EVO","E",False),("ESVO","Stereo E",False),("ESVIO AA","Stereo E+I",False),
        ("ESVO2","Stereo E+I",False),("ES-PTAM","Stereo E",False),("DH-PTAM","Stereo E+F",False),
        ("Ultimate-SLAM","E+F+I",False),("DEVO","E",False),("DEIO","E+I",True)],
    seqs=["mocap-1d-trans","mocap-3d-trans","mocap-6dof","mocap-desk","mocap-desk2","average"],
    values=[
     [7.5,12.5,85.5,54.1,75.2,47.0],
     [12.3,17.2,13.0,12.4,4.6,11.9],
     [3.9,18.9,"failed",9.00,9.5,10.3],
     [3.3,7.3,3.2,6.2,4.0,4.8],
     [1.05,8.53,10.25,2.5,7.2,5.9],
     [10.3,0.7,2.4,1.6,1.5,3.9],
     [3.9,4.7,35.3,19.5,34.1,19.5],
     [0.5,1.1,1.6,1.7,1.0,1.2],
     [0.4,1.1,1.4,1.4,0.7,1.0]])

add(paper="DEIO", table="VI", dataset="EDS", metric="ATE", unit="cm",
    align="full trajectory",
    note="EDS handheld Prophesee Gen3.1, 640x480. First event-inertial results on EDS. DEIO ~ RAMP-VO; "
         "DBA-Fusion (image-based) degrades badly under HDR.",
    methods=[("ORB-SLAM3","Stereo F+I",False),("DPVO","F",False),("DBA-Fusion","F+I",False),
        ("DEVO","E",False),("RAMP-VO","E+F",False),("DEIO","E+I",True)],
    seqs=["peanuts_dark","peanuts_light","peanuts_run","rocket_dark","rocket_light","ziggy",
          "ziggy_hdr","ziggy_flying","all_chars","average"],
    values=[
     [6.15,27.26,16.83,10.12,32.53,26.92,81.98,20.57,21.37,27.08],
     [1.26,12.99,25.48,27.41,63.11,14.86,66.17,10.85,95.87,35.33],
     [7.26,149.36,134.92,114.24,117.09,173.50,140.51,11.81,126.36,108.33],
     [4.78,21.07,38.10,8.78,59.83,11.84,22.82,10.92,10.76,21.00],
     [1.20,9.03,13.19,7.20,17.53,19.05,28.78,6.35,28.61,14.55],
     [1.77,16.27,19.96,8.91,15.41,10.39,23.82,3.84,31.55,14.66]])

add(paper="DEIO", table="VII", dataset="MVSEC", metric="MPE", unit="%",
    align="full trajectory",
    note="MVSEC indoor_flying, stereo DAVIS346. DEIO best avg across all 4 sequences.",
    methods=[("ORB-SLAM3","Stereo F+I",False),("VINS-Fusion","Stereo F+I",False),("EVO","E",False),
        ("ESVO","Stereo E",False),("Ultimate-SLAM","E+F+I",False),("PL-EVIO","E+F+I",False),
        ("ESVIO","Stereo E+F+I",False),("DBA-Fusion","F+I",False),("DEVO","E",False),("DEIO","E+I",True)],
    seqs=["Flying 1","Flying 2","Flying 3","Flying 4","average"],
    values=[
     [5.31,5.65,2.90,6.99,5.21],
     [1.50,6.98,0.73,3.62,3.21],
     [5.09,"failed",2.58,"failed",3.84],
     [4.00,3.66,1.71,"failed",3.12],
     ["failed","failed","failed",2.77,2.77],
     [1.35,1.00,0.64,5.31,2.08],
     [0.94,1.00,0.47,5.55,1.99],
     [2.20,"failed","failed","failed",2.20],
     [0.26,0.32,0.19,1.08,0.46],
     [0.24,0.21,0.12,0.78,0.34]])

add(paper="DEIO", table="VIII", dataset="UZH-FPV", metric="MPE", unit="%",
    align="full trajectory",
    note="UZH-FPV drone racing, mono DAVIS346. DPVO/DBA-Fusion/EVO/USLAM fail on all seqs (motion blur).",
    methods=[("VINS-Fusion","Stereo F+I",False),("ORB-SLAM3","Stereo F+I",False),("EVO","E",False),
        ("DPVO","F",False),("VINS-MONO","F+I",False),("DBA-Fusion","F+I",False),
        ("Ultimate-SLAM","E+F+I",False),("PL-EVIO","E+F+I",False),("DEVO","E",False),("DEIO","E+I",True)],
    seqs=["indoor_forward_3","indoor_forward_5","indoor_forward_6","indoor_forward_7",
          "indoor_forward_9","indoor_forward_10","average"],
    values=[
     [0.84,"failed",1.45,0.61,2.87,4.48,2.45],
     [0.55,1.19,"failed",0.36,0.77,1.02,0.78],
     ["failed","failed","failed","failed","failed","failed","-"],
     ["failed","failed","failed","failed","failed","failed","-"],
     [0.65,1.07,0.25,0.37,0.51,0.92,0.63],
     ["failed","failed","failed","failed","failed","failed","-"],
     ["failed","failed","failed","failed","failed","failed","-"],
     [0.38,0.90,0.30,0.55,0.44,1.06,0.60],
     [0.37,0.40,0.31,0.50,0.61,0.52,0.45],
     [0.39,0.36,0.33,0.32,0.59,0.55,0.42]])

add(paper="DEIO", table="IX", dataset="DSEC", metric="ATE", unit="cm",
    align="full trajectory (GT = LiDAR-IMU odometry from ESVIO-AA authors)",
    note="DSEC zurich_city_04 driving, stereo events. DEIO (mono!) beats stereo-event baselines by "
         ">=66.7% on all seqs. GT is a LiDAR-IMU pseudo-GT (no true 6DoF GT in DSEC).",
    methods=[("ESVO","Stereo E",False),("ESVIO AA","Stereo E+I",False),("ES-PTAM","Stereo E",False),
        ("ESIO","Stereo E+I",False),("ESVIO","Stereo E+F+I",False),("DEIO","E+I",True)],
    seqs=["city04_a","city04_b","city04_c","city04_d","city04_e","average"],
    values=[
     [371.1,116.6,1357.1,2676.6,794.9,1032.9],
     [105.0,66.7,637.9,699.8,130.3,527.9],
     [131.62,29.02,1184.37,1053.87,75.9,494.9],
     [543.5,295.1,896.2,2977.0,2326.4,1587.8],
     [371.2,445.8,1892.7,921.7,352.0,596.9],
     [80.6,35.4,413.8,207.6,86.1,164.5]])
# ----------------------------- DEVO (2312.09800) -----------------------------
# DEVO protocol: monocular methods get global scale estimated once before alignment (Sim3),
# median of 5 trials.  "-" in DEVO tables means FAILURE (per their caption).
DEVO_ALIGN="Sim3, median-of-5"
add(paper="DEVO", table="1", dataset="UZH-FPV", metric="MPE", unit="%", align=DEVO_ALIGN,
    note="DEVO (event-only) beats all on 4/9; only successful non-IMU peer is its own DPVO-dagger.",
    methods=[("ORB-SLAM3","Stereo F+I",False),("VINS-Fusion","Stereo F+I",False),
        ("VINS-Mono","F+I",False),("DPVO","F",False),("Ultimate-SLAM","E+F+I",False),
        ("PL-EVIO","E+F+I",False),("EVO","E",False),("DPVO-dagger","E",False),("DEVO","E",True)],
    seqs=["indoor_forward_3","indoor_forward_5","indoor_forward_6","indoor_forward_7",
          "indoor_forward_9","indoor_forward_10","indoor_45_degree_2","indoor_45_degree_4","indoor_45_degree_9"],
    values=[
     [0.55,1.19,"failed",0.36,0.77,1.02,2.18,1.53,0.49],
     [0.84,"failed",1.45,0.61,2.87,4.48,"failed","failed","failed"],
     [0.65,1.07,0.25,0.37,0.51,0.92,0.53,1.72,1.25],
     ["failed","failed","failed","failed","failed","failed","failed","failed","failed"],
     ["failed","failed","failed","failed","failed","failed","failed",9.79,4.74],
     [0.38,0.90,0.30,0.55,0.44,1.06,0.55,1.30,0.76],
     ["failed","failed","failed","failed","failed","failed","failed","failed","failed"],
     [0.52,0.42,0.55,"failed",0.45,0.54,"failed",1.21,"failed"],
     [0.37,0.40,0.31,0.50,0.61,0.52,0.72,0.45,0.89]])

_DEVO_T2_METHODS=[("ORB-SLAM3","Stereo F+I",False),("VINS-Fusion","Stereo F+I",False),
    ("DPVO","F",False),("ESVIO","Stereo E+F+I",False),("PL-EVIO","E+F+I",False),
    ("ESVO","Stereo E",False),("EVO","E",False),("DPVO-dagger","E",False),("DEVO","E",True)]
_DEVO_T2_SEQS=["corner_slow","robot_normal","robot_fast","desk_normal","desk_fast","sofa_normal",
    "sofa_fast","mountain_normal","mountain_fast","hdr_normal","hdr_fast","corridors_dolly",
    "corridors_walk","school_dolly","school_scooter","units_dolly","units_scooter"]
add(paper="DEVO", table="2", dataset="VECtor", metric="MPE", unit="%", align=DEVO_ALIGN,
    note="DEVO (event-only) beats ESVIO (stereo E+F+I) on ~70% of seqs; baselines (except DPVO/DPVO-dag) "
         "taken from ESVIO paper. Methods using frames have a high-res global-shutter advantage.",
    methods=_DEVO_T2_METHODS, seqs=_DEVO_T2_SEQS,
    values=[
     [1.49,0.73,0.71,0.46,0.31,0.15,0.21,0.35,2.11,0.64,0.22,1.03,1.32,0.73,0.70,7.64,6.22],
     [1.61,0.58,"failed",0.47,0.32,0.13,0.57,4.05,"failed",1.27,0.30,1.88,0.50,1.42,0.52,4.39,4.92],
     [0.30,0.15,0.07,0.09,0.05,0.06,0.07,0.08,0.11,0.13,0.06,0.56,0.54,0.11,0.40,1.52,1.67],
     [1.49,1.08,0.20,0.61,0.13,0.16,0.17,0.59,0.16,0.57,0.21,1.13,0.43,0.42,0.59,3.43,2.85],
     [2.10,0.68,0.17,3.66,0.14,0.19,0.17,4.32,0.13,4.02,0.20,1.58,0.92,2.47,1.30,5.84,5.00],
     [4.83,"failed","failed","failed","failed",1.77,"failed","failed","failed","failed","failed","failed","failed",10.9,9.21,"failed","failed"],
     [4.33,3.25,"failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed"],
     ["failed",0.22,0.73,0.18,0.77,0.22,0.60,0.09,0.31,0.52,0.20,"failed","failed",4.61,0.55,"failed",3.69],
     [0.59,0.17,0.13,0.11,0.15,0.13,0.38,0.09,0.37,0.60,0.24,0.51,1.04,0.29,0.48,0.48,0.88]])
add(paper="DEVO", table="2", dataset="VECtor", metric="ATE", unit="cm", align=DEVO_ALIGN,
    note="ATE column of DEVO Table 2 (Sim3, median-of-5).",
    methods=_DEVO_T2_METHODS, seqs=_DEVO_T2_SEQS,
    values=[
     [1.2,2.9,15.0,3.9,9.9,4.4,6.4,2.6,5.2,1.9,4.0,80,103,92,75,1806,1450],
     [1.3,2.3,"failed",4.0,10.0,3.8,17.0,30.0,"failed",3.8,5.5,146,39,179,56,1039,1147],
     [0.4,0.7,1.7,1.0,1.9,2.1,2.2,0.7,3.7,0.5,1.2,54,50,16,47,452,497],
     [1.2,4.3,4.2,5.2,4.2,4.7,5.2,4.4,3.9,1.7,3.9,88,34,53,63,812,664],
     [1.7,2.7,3.7,31.0,4.3,5.8,5.0,32.0,3.1,12.0,3.6,123,72,311,139,1382,1166],
     [3.9,"failed","failed","failed","failed",53.0,"failed","failed","failed","failed","failed","failed","failed",1371,983,"failed","failed"],
     [3.5,13.0,"failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed"],
     ["failed",2.4,18.9,2.6,30.2,10.1,22.2,0.8,11.5,2.4,4.6,"failed","failed",651,66,"failed",1141],
     [1.2,1.0,3.7,1.1,6.1,4.7,14.4,0.8,14.0,3.1,5.7,53,113,41,58,131,296]])
_DEVO_T3_M=[("ORB-SLAM3","Stereo F+I",False),("VINS-Fusion","Stereo F+I",False),("DPVO","F",False),
    ("ESVIO","Stereo E+F+I",False),("PL-EVIO","E+F+I",False),("DPVO-dagger","E",False),("DEVO","E",True)]
_DEVO_T3_S=["agg_translation","agg_rotation","agg_flip","agg_walk","hdr_circle","hdr_slow",
    "hdr_tran_rota","hdr_agg","hdr_dark_normal"]
add(paper="DEVO", table="3", dataset="HKU (stereo)", metric="MPE", unit="%", align=DEVO_ALIGN,
    note="agg_flip/hdr_circle/hdr_slow have sensor-detection failures; DEVO agg_walk uses top-P sampling. "
         "EVO and ESVO fail on all HKU seqs.",
    methods=_DEVO_T3_M, seqs=_DEVO_T3_S,
    values=[
     [0.15,0.35,0.36,"failed",0.17,0.16,0.30,0.29,"failed"],
     [0.11,1.34,1.16,"failed",5.03,0.13,0.11,1.21,0.86],
     [0.07,0.04,0.99,1.17,0.31,0.23,0.67,0.29,"failed"],
     [0.10,0.17,0.36,0.31,0.16,0.11,0.10,0.10,0.42],
     [0.07,0.23,0.39,0.42,0.14,0.13,0.10,0.14,1.35],
     [0.12,0.28,1.16,"failed",1.19,0.36,0.21,0.54,0.49],
     [0.06,0.05,0.71,0.90,0.39,0.08,0.08,0.26,0.06]])
add(paper="DEVO", table="3", dataset="HKU (stereo)", metric="ATE", unit="cm", align=DEVO_ALIGN,
    note="ATE column of DEVO Table 3.",
    methods=_DEVO_T3_M, seqs=_DEVO_T3_S,
    values=[
     [9.5,23.0,14.0,"failed",8.3,8.6,20.0,28.0,"failed"],
     [6.9,8.8,45.0,"failed",252.0,7.3,7.5,118.0,80.0],
     [9.66,3.70,56.52,107.4,24.10,16.63,53.30,36.10,"failed"],
     [6.3,11.0,14.0,27.0,8.1,5.9,6.5,10.0,39.0],
     [4.8,15.0,15.0,37.0,6.8,6.9,6.8,14.0,125.0],
     [15.42,22.02,60.26,"failed",67.60,24.01,21.60,59.80,47.70],
     [4.03,3.58,44.90,88.27,21.30,4.95,5.91,33.98,6.19]])

_DEVO_T4_M=[("ORB-SLAM3","F",False),("DPVO","F",False),("DPVO-dagger","E",False),("DEVO","E",True)]
_DEVO_T4_S=["peanuts_dark","peanuts_light","peanuts_run","rocket_dark","rocket_light","ziggy",
    "ziggy_hdr","ziggy_flying","all_chars"]
add(paper="DEVO", table="4", dataset="EDS", metric="ATE", unit="cm", align=DEVO_ALIGN,
    note="First pose-estimation results on EDS. Here ORB-SLAM3 is run MONOCULAR (up-to-scale), "
         "unlike DEIO T.VI which uses stereo ORB-SLAM3.",
    methods=_DEVO_T4_M, seqs=_DEVO_T4_S,
    values=[
     [6.15,27.26,16.83,10.12,32.53,26.92,81.98,20.57,21.37],
     [1.26,12.99,25.48,27.41,63.11,14.86,66.17,10.85,95.87],
     [5.76,69.77,43.49,80.89,97.62,23.79,46.41,34.51,76.02],
     [4.78,21.07,38.10,8.78,59.83,11.84,22.82,10.92,10.76]])
add(paper="DEVO", table="4", dataset="EDS", metric="MPE", unit="%", align=DEVO_ALIGN,
    note="MPE column of DEVO Table 4.",
    methods=_DEVO_T4_M, seqs=_DEVO_T4_S,
    values=[
     [0.49,1.14,0.19,0.37,1.79,0.42,1.13,1.33,0.27],
     [0.12,0.44,0.29,1.07,3.64,0.22,1.02,0.73,1.39],
     [0.52,2.36,0.52,3.65,5.08,0.36,0.72,2.05,0.90],
     [0.30,0.75,0.43,0.32,3.40,0.15,0.36,0.71,0.16]])
add(paper="DEVO", table="5", dataset="TUM-VIE", metric="ATE", unit="cm", align=DEVO_ALIGN,
    note="DEVO beats event-only peers (DPVO-dag, EVO, ESVO) by >=44%; even beats DH-PTAM (4-cam) on 4/5.",
    methods=[("ORB-SLAM3","Stereo F+I",False),("BASALT","Stereo F+I",False),("DPVO","F",False),
        ("DH-PTAM","Stereo E",False),("Ultimate-SLAM","E+F+I",False),("ESVO","Stereo E",False),
        ("EVO","E",False),("DPVO-dagger","E",False),("DEVO","E",True)],
    seqs=["mocap-1d-trans","mocap-3d-trans","mocap-6dof","mocap-desk","mocap-desk2"],
    values=[
     [0.7,1.2,1.8,0.7,2.5],
     [0.3,0.9,1.4,1.6,1.1],
     [0.5,1.1,1.2,1.2,0.8],
     [10.3,0.7,2.4,1.6,1.5],
     [3.9,4.7,35.3,19.5,34.1],
     [0.9,2.8,5.8,3.3,3.2],
     [7.5,12.5,85.5,54.1,75.2],
     [2.3,8.2,7.9,5.1,3.7],
     [0.5,1.1,1.6,1.7,1.0]])

add(paper="DEVO", table="6", dataset="RPG", metric="ATE", unit="cm", align=DEVO_ALIGN,
    note="EVO rpg_bin/rpg_box marked * = failed after <=30% of seq (values 13.2/14.2 unreliable). "
         "DEVO beats event-only methods by >=63%. (Table also reports Rrmse[deg], omitted here.)",
    methods=[("ORB-SLAM2 (stereo)","Stereo F",False),("ORB-SLAM2 (mono)","F",False),("DSO","F",False),
        ("DPVO","F",False),("Ultimate-SLAM","E+F+I",False),("EDSO","E+F",False),("ESVO","Stereo E",False),
        ("EVO","E",False),("DPVO-dagger","E",False),("DEVO","E",True)],
    seqs=["rpg_bin","rpg_box","rpg_desk","rpg_monitor"],
    values=[
     [0.7,1.6,1.8,0.8],
     [2.4,3.9,3.8,3.1],
     [1.1,2.0,10.0,0.9],
     [0.7,1.62,3.1,2.12],
     [7.7,9.5,9.8,6.5],
     [1.1,2.1,1.5,1.0],
     [2.8,5.8,3.2,3.3],
     [13.2,14.2,5.2,7.8],
     [4.00,4.20,3.05,2.35],
     [1.03,0.92,1.21,0.71]])

_DEVO_T7_M=[("ORB-SLAM3","Stereo F+I",False),("VINS-Fusion","Stereo F+I",False),("DPVO","F",False),
    ("ESVIO","Stereo E+F+I",False),("Ultimate-SLAM","E+F+I",False),("PL-EVIO","E+F+I",False),
    ("ESVO","Stereo E",False),("EVO","E",False),("DPVO-dagger","E",False),("DEVO","E",True)]
_DEVO_T7_S=["Indoor Fly1","Indoor Fly2","Indoor Fly3","Indoor Fly4"]
add(paper="DEVO", table="7", dataset="MVSEC", metric="MPE", unit="%", align=DEVO_ALIGN,
    note="DEVO is the first event-only method that does not fail on any MVSEC seq; worse than DPVO "
         "(frames) due to MVSEC's biased polarity ratio (neg:pos=3.2).",
    methods=_DEVO_T7_M, seqs=_DEVO_T7_S,
    values=[
     [5.31,5.65,2.90,6.99],
     [1.50,6.98,0.73,3.62],
     [0.16,0.15,0.08,0.30],
     [0.94,1.00,0.47,5.55],
     ["failed","failed","failed",2.77],
     [1.35,1.00,0.64,5.31],
     [4.00,3.66,1.71,"failed"],
     [5.09,"failed",2.58,"failed"],
     ["failed","failed","failed","failed"],
     [0.26,0.32,0.19,1.08]])
add(paper="DEVO", table="7", dataset="MVSEC", metric="ATE", unit="cm", align=DEVO_ALIGN,
    note="ATE column of DEVO Table 7.",
    methods=_DEVO_T7_M, seqs=_DEVO_T7_S,
    values=[
     [142.0,170.0,154.0,58.0],
     [40.0,210.0,39.0,30.0],
     [4.8,6.3,4.6,3.2],
     [25.0,30.0,25.0,46.0],
     ["failed","failed","failed",23.0],
     [36.0,30.0,34.0,44.0],
     [107.0,110.0,91.0,"failed"],
     [136.0,"failed",137.0,"failed"],
     ["failed","failed","failed","failed"],
     [7.76,13.30,10.72,12.57]])
# ----------------------------- ESVIO (2212.13184) -----------------------------
_ESVIO_T1_M=[("ORB-SLAM3","Stereo F+I",False),("VINS-Fusion","Stereo F+I",False),
    ("Ultimate-SLAM (EIO)","E+I",False),("Ultimate-SLAM (EVIO)","E+F+I",False),("PL-EVIO","E+F+I",False),
    ("ESIO","Stereo E+I",False),("ESIO+","Stereo E+I",False),("ESVIO","Stereo E+F+I",True)]
_ESVIO_T1_S=["agg_translation","agg_rotation","agg_flip","agg_walk","hdr_circle","hdr_slow",
    "hdr_tran_rota","hdr_agg","dark_normal","average"]
add(paper="ESVIO", table="I", dataset="HKU (stereo)", metric="MPE", unit="%", align="SE3, full",
    note="arclab-HKU stereo DAVIS346. ESVIO avg MPE 0.14 vs PL-EVIO 0.26; ESVIO's big win is MRE "
         "(0.033 vs ORB-SLAM3 0.12). EVO and ESVO fail on all HKU seqs.",
    methods=_ESVIO_T1_M, seqs=_ESVIO_T1_S,
    values=[
     [0.15,0.35,0.36,"failed",0.17,0.16,0.30,0.29,"failed",0.16],
     [0.11,1.34,1.16,"failed",5.03,0.13,0.11,1.21,0.86,0.76],
     [16.22,"failed",11.15,"failed",0.92,"failed","failed","failed","failed",5.06],
     [0.59,3.14,6.86,2.00,1.32,2.80,2.64,2.47,2.17,1.69],
     [0.07,0.23,0.39,0.42,0.14,0.13,0.10,0.14,1.35,0.26],
     [0.59,1.33,3.79,1.49,1.38,0.29,0.84,2.33,0.30,0.89],
     [0.55,0.78,3.17,1.30,0.46,0.31,0.91,1.41,0.35,0.66],
     [0.10,0.17,0.36,0.31,0.16,0.11,0.10,0.10,0.42,0.14]])
add(paper="ESVIO", table="I", dataset="HKU (stereo)", metric="MRE", unit="deg/m", align="SE3, full",
    note="Mean rotation error column of ESVIO Table I.",
    methods=_ESVIO_T1_M, seqs=_ESVIO_T1_S,
    values=[
     [0.075,0.11,0.39,"failed",0.12,0.058,0.042,0.085,"failed",0.12],
     [0.019,0.024,2.02,"failed",0.60,0.026,0.021,0.27,0.028,0.38],
     [0.45,"failed",2.11,"failed",0.58,"failed","failed","failed","failed",1.05],
     [0.020,0.026,2.04,0.16,0.54,0.099,0.13,0.27,0.031,0.39],
     [0.091,0.12,2.23,0.14,0.62,0.068,0.064,0.30,0.081,0.41],
     [0.16,0.048,0.23,0.23,0.10,0.38,0.30,0.16,0.12,0.19],
     [0.16,0.045,0.23,0.23,0.099,0.39,0.31,0.14,0.12,0.19],
     [0.016,0.015,0.12,0.026,0.035,0.028,0.018,0.021,0.015,0.033]])

_ESVIO_T2_M=[("ORB-SLAM3","Stereo F+I",False),("VINS-Fusion","Stereo F+I",False),("EVO","E",False),
    ("ESVO","Stereo E",False),("Ultimate-SLAM","E+F+I",False),("PL-EVIO","E+F+I",False),
    ("ESVIO","Stereo E+F+I",True)]
_ESVIO_T2V_S=["corner_slow","robot_normal","robot_fast","desk_normal","desk_fast","sofa_normal",
    "sofa_fast","mountain_normal","mountain_fast","hdr_normal","hdr_fast","corridors_dolly",
    "corridors_walk","school_dolly","school_scooter","units_dolly","units_scooter"]
add(paper="ESVIO", table="II", dataset="VECtor", metric="MPE", unit="%", align="SE3, full",
    note="First VECtor results for a stereo event-inertial method. ESVIO best on large-scale; "
         "ORB-SLAM3 slightly better on a few small-scale normal seqs.",
    methods=_ESVIO_T2_M, seqs=_ESVIO_T2V_S,
    values=[
     [1.49,0.73,0.71,0.46,0.31,0.15,0.21,0.35,2.11,0.64,0.22,1.03,1.32,0.73,0.70,7.64,6.22],
     [1.61,0.58,"failed",0.47,0.32,0.13,0.57,4.05,"failed",1.27,0.30,1.88,0.50,1.42,0.52,4.39,4.92],
     [4.33,3.25,"failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed"],
     [4.83,"failed","failed","failed","failed",1.77,"failed","failed","failed","failed","failed","failed","failed",10.87,9.21,"failed","failed"],
     [4.83,1.18,1.65,2.24,1.08,5.74,2.54,3.64,4.13,5.69,2.61,"failed","failed","failed",6.40,"failed","failed"],
     [2.10,0.68,0.17,3.66,0.14,0.19,0.17,4.32,0.13,4.02,0.20,1.58,0.92,2.47,1.30,5.84,5.00],
     [1.49,1.08,0.20,0.61,0.13,0.16,0.17,0.59,0.16,0.57,0.21,1.13,0.43,0.42,0.59,3.43,2.85]])
add(paper="ESVIO", table="II", dataset="VECtor", metric="MRE", unit="deg/m", align="SE3, full",
    note="Mean rotation error column of ESVIO Table II (VECtor).",
    methods=_ESVIO_T2_M, seqs=_ESVIO_T2V_S,
    values=[
     [14.28,1.18,0.70,0.41,0.41,0.41,0.43,1.00,0.64,1.20,0.45,1.37,1.31,1.02,0.49,0.41,0.22],
     [14.06,1.18,"failed",0.36,0.33,0.40,0.34,1.05,"failed",1.10,0.34,1.37,1.31,1.06,0.61,0.42,0.24],
     [15.52,2.00,"failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed","failed"],
     [20.98,"failed","failed","failed","failed",0.60,"failed","failed","failed","failed","failed","failed","failed",1.08,0.63,"failed","failed"],
     [14.42,1.11,0.56,0.56,0.38,0.39,0.36,1.06,0.62,1.65,0.34,"failed","failed","failed",0.61,"failed","failed"],
     [14.21,1.25,0.74,0.45,0.48,0.46,0.47,0.76,0.56,1.52,0.50,1.37,1.31,0.97,0.54,0.44,0.42],
     [14.03,1.17,0.56,0.38,0.32,0.40,0.35,0.77,0.45,1.06,0.33,1.33,1.32,0.73,0.56,0.022,0.39]])
add(paper="ESVIO", table="II", dataset="MVSEC", metric="MPE", unit="%", align="SE3, full",
    note="MVSEC indoor_flying block of ESVIO Table II.",
    methods=_ESVIO_T2_M, seqs=["Indoor Flying 1","Indoor Flying 2","Indoor Flying 3","Indoor Flying 4"],
    values=[
     [5.31,5.65,2.90,6.99],
     [1.50,6.98,0.73,3.62],
     [5.09,"failed",2.58,"failed"],
     [4.00,3.66,1.71,"failed"],
     ["failed","failed","failed",2.77],
     [1.35,1.00,0.64,5.31],
     [0.94,1.00,0.47,5.55]])
add(paper="ESVIO", table="II", dataset="MVSEC", metric="MRE", unit="deg/m", align="SE3, full",
    note="MVSEC MRE block of ESVIO Table II.",
    methods=_ESVIO_T2_M, seqs=["Indoor Flying 1","Indoor Flying 2","Indoor Flying 3","Indoor Flying 4"],
    values=[
     [0.37,0.41,0.30,0.79],
     [0.13,0.15,0.048,0.39],
     [0.92,"failed",1.25,"failed"],
     [0.50,0.43,0.18,"failed"],
     ["failed","failed","failed",0.14],
     [0.11,0.16,0.065,0.23],
     [0.14,0.11,0.043,0.21]])
# ----------------------------- ESVO2 (2410.09374) -----------------------------
# Table VI also reports ARE[deg]; Table VII also reports RPE-R[deg/s] (rotation) -- see conclusions.md.
_ESVO2_M=[("ESVO","Stereo E",False),("ES-PTAM","Stereo E",False),("ESIO","Stereo E+I",False),
    ("ESVIO","Stereo E+F+I",False),("ICRA'24 (ESVIO-AA)","Stereo E+I",False),("ESVO2","Stereo E+I",True)]
_E2N="ESVO2 Table VI/VII; '-'=not reported by that method's paper. ESVO2 = direct stereo event + IMU."
add(paper="ESVO2", table="VI", dataset="RPG", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M,
    seqs=["rpg_box","rpg_monitor","rpg_bin","rpg_desk","rpg_reader"],
    values=[
     [5.80,3.30,2.80,3.20,6.60],
     [4.06,2.34,2.57,2.84,"-"],
     [11.38,7.87,7.08,3.16,"failed"],
     [4.41,3.48,2.28,2.03,"-"],
     [6.67,2.80,5.90,5.33,3.88],
     [4.31,2.31,2.27,1.57,2.68]])
add(paper="ESVO2", table="VI", dataset="MVSEC", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M, seqs=["indoor 1","indoor 2","indoor 3","indoor 4"],
    values=[
     [16.59,14.94,10.03,"failed"],
     [15.02,"-","-","-"],
     [820.36,417.85,"failed",173.51],
     [9.63,"-",8.06,"-"],
     [17.65,17.52,10.45,"failed"],
     [7.63,10.05,7.35,5.59]])
add(paper="ESVO2", table="VI", dataset="DSEC", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M,
    seqs=["city04_a","city04_b","city04_c","city04_d","city04_e","city04_f","city09_b","city11_a","city11_b"],
    values=[
     [370.32,115.56,932.84,2676.11,792.93,1400.26,606.09,366.22,3241.69],
     [131.62,29.02,1184.37,1053.87,75.90,522.00,195.14,"-","-"],
     [940.80,434.87,1153.69,6822.53,1036.23,4595.01,"failed",107.36,300.14],
     [201.53,48.33,1400.76,"-",331.70,1765.48,"-",406.11,"-"],
     [103.85,66.80,637.13,732.13,115.82,579.66,192.44,95.75,869.77],
     [56.17,73.83,508.71,546.58,52.94,257.75,87.83,48.77,441.79]])
add(paper="ESVO2", table="VI", dataset="VECtor", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note=_E2N+" Only ESVO2 (+ESVO/ESIO/ICRA24) run on VECtor here; ESVIO/ES-PTAM not reported.",
    methods=_ESVO2_M,
    seqs=["robot_normal","robot_fast","corner_slow","hdr_normal","sofa_normal","desk_normal"],
    values=[
     [7.32,"failed",13.70,18.40,"failed",20.81],
     ["-","-","-","-","-","-"],
     [5.17,"failed",2.67,27.85,43.94,"failed"],
     ["-","-","-","-","-","-"],
     [15.20,"failed",5.52,16.06,"failed",19.08],
     [4.81,24.18,2.15,13.53,40.28,16.47]])
add(paper="ESVO2", table="VI", dataset="TUM-VIE", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M,
    seqs=["mocap-1d-trans","mocap-3d-trans","mocap-6dof","mocap-desk","mocap-desk2"],
    values=[
     [12.54,17.19,13.46,12.92,4.42],
     [1.05,8.53,10.25,2.50,7.20],
     ["failed","failed","failed","failed","failed"],
     ["-","-","-","-","-"],
     [3.86,18.90,"failed",8.99,9.47],
     [3.33,7.26,3.21,6.16,4.02]])
add(paper="ESVO2", table="VII", dataset="RPG", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M, seqs=["rpg_box","rpg_monitor","rpg_bin","rpg_desk","rpg_reader"],
    values=[
     [7.20,3.20,3.10,4.50,5.60],
     [4.22,2.59,1.82,3.99,"-"],
     [7.87,4.27,6.78,3.79,"failed"],
     [8.71,7.93,7.64,3.65,"-"],
     [5.16,1.85,3.80,6.33,4.65],
     [4.18,1.69,2.53,3.53,2.12]])
add(paper="ESVO2", table="VII", dataset="MVSEC", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M, seqs=["indoor 1","indoor 2","indoor 3","indoor 4"],
    values=[
     [7.38,7.39,5.97,"failed"],
     [6.89,"-","-","-"],
     [228.84,134.48,"failed",181.03],
     [5.92,"-",4.81,"-"],
     [10.72,12.33,6.05,"failed"],
     [5.05,6.12,4.75,10.36]])
add(paper="ESVO2", table="VII", dataset="DSEC", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M,
    seqs=["city04_a","city04_b","city04_c","city04_d","city04_e","city04_f","city09_b","city11_a","city11_b"],
    values=[
     [69.14,32.84,82.03,190.67,183.01,267.62,38.52,56.82,188.97],
     [26.92,26.48,86.21,68.02,14.05,49.39,22.44,"-","-"],
     [187.03,188.23,145.64,540.98,461.23,626.87,"failed",54.53,53.55],
     [62.85,43.07,105.87,"-",101.28,133.11,"-",54.02,"-"],
     [20.91,25.31,71.76,60.18,50.78,290.56,20.25,20.34,91.94],
     [16.98,21.70,39.12,18.00,15.41,20.05,17.84,12.94,14.83]])
add(paper="ESVO2", table="VII", dataset="VECtor", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M,
    seqs=["robot_normal","robot_fast","corner_slow","hdr_normal","sofa_normal","desk_normal"],
    values=[
     [16.79,"failed",6.45,5.55,"failed",5.12],
     ["-","-","-","-","-","-"],
     [3.38,"failed",7.01,15.65,54.32,"failed"],
     ["-","-","-","-","-","-"],
     [6.18,"failed",3.16,6.54,"failed",5.76],
     [3.16,8.22,1.91,3.79,13.59,3.50]])
add(paper="ESVO2", table="VII", dataset="TUM-VIE", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M,
    seqs=["mocap-1d-trans","mocap-3d-trans","mocap-6dof","mocap-desk","mocap-desk2"],
    values=[
     [8.41,7.47,14.28,5.87,6.23],
     [0.71,4.94,12.02,2.53,4.04],
     ["failed","failed","failed","failed","failed"],
     ["-","-","-","-","-"],
     [1.21,3.98,"failed",3.14,4.20],
     [1.06,2.32,2.49,3.41,2.41]])
# ----------------------- Stereo-DEVO (2509.08235) ----------------------------
# Deep STEREO event VO (no IMU; stereo gives metric scale). DEIO column here is METRIC (SE3) ATE and
# exposes DEIO's VECtor/DSEC scale failure (e.g. desk_normal 254.76 cm) -- corroborates our reproduction.
_SDEVO_M=[("ESVO","Stereo E",False),("ES-PTAM","Stereo E",False),("ESIO","Stereo E+I",False),
    ("ESVO2","Stereo E+I",False),("DEIO","E+I",False),("Stereo-DEVO","Stereo E",True)]
_SDN="Stereo-DEVO T.II (RPE+ATE). DEIO shown under METRIC eval (no scale-correction) -> large VECtor/DSEC "
_SDN+="scale errors. Authors also drop DEVO entirely 'because its poses suffer from scale ambiguity'."
add(paper="STEREO_DEVO", table="II", dataset="RPG", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note=_SDN, methods=_SDEVO_M, seqs=["rpg_box","rpg_monitor","rpg_bin","rpg_desk","rpg_reader"],
    values=[
     [5.80,3.30,2.80,3.20,6.60],
     [4.06,2.34,2.57,2.84,"-"],
     [11.38,7.87,7.08,3.16,"failed"],
     [4.31,2.31,2.27,1.57,2.68],
     ["-","-","-","-","-"],
     [1.92,0.91,1.16,1.46,3.78]])
add(paper="STEREO_DEVO", table="II", dataset="MVSEC", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note=_SDN, methods=_SDEVO_M, seqs=["indoor 1","indoor 2","indoor 3","indoor 4"],
    values=[
     [16.59,14.94,10.03,"failed"],
     [15.02,"-","-","-"],
     [820.36,417.85,"failed",173.51],
     [7.63,10.05,7.35,5.59],
     [7.52,6.96,29.75,12.71],
     [3.76,8.00,5.57,4.57]])
add(paper="STEREO_DEVO", table="II", dataset="DSEC", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note=_SDN, methods=_SDEVO_M,
    seqs=["city04_a","city04_b","city04_c","city04_d","city09_a","city09_b","city09_c","city09_d","city09_e","city11_a","city11_b"],
    values=[
     [370.32,115.56,932.84,2676.11,2433.91,742.19,2962.40,5398.48,3345.86,366.22,3241.69],
     [131.62,29.02,1184.37,1053.87,"failed",221.35,3673.80,"failed",1480.79,117.86,"failed"],
     [940.80,434.87,1153.69,6822.53,"failed",2887.84,"failed",1766.16,4201.00,107.36,300.14],
     [56.17,73.83,508.71,546.58,1183.04,107.48,1648.30,1920.36,1075.09,48.77,441.79],
     [184.51,116.44,9128.73,10970.03,"-","-","-","-","-","-","-"],
     [96.86,17.65,481.62,406.20,196.97,267.80,931.15,625.81,246.26,47.56,282.06]])
add(paper="STEREO_DEVO", table="II", dataset="VECtor", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note=_SDN+" DEIO metric ATE here (e.g. desk_normal 254.76, units_dolly 826.73 cm) is the scale failure.",
    methods=_SDEVO_M,
    seqs=["robot_normal","corner_slow","hdr_normal","sofa_normal","desk_normal","corridors_dolly","units_dolly"],
    values=[
     [7.32,13.70,18.40,"failed",20.81,"failed","failed"],
     ["-","-","-","-","-","-","-"],
     [5.17,2.67,27.85,43.94,"failed","failed","failed"],
     [4.81,2.15,13.53,40.28,16.47,"failed","failed"],
     ["-",10.70,"-","-",254.76,516.08,826.73],
     [3.16,1.06,6.71,7.18,6.48,196.53,444.51]])
add(paper="STEREO_DEVO", table="II", dataset="TUM-VIE", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note=_SDN+" Note: DEIO is genuinely strong on TUM-VIE (metric), unlike on VECtor/DSEC.",
    methods=_SDEVO_M, seqs=["mocap-1d-trans","mocap-3d-trans","mocap-6dof","mocap-desk","mocap-desk2"],
    values=[
     [12.54,17.19,13.46,12.92,4.42],
     [1.05,8.53,10.25,2.50,7.20],
     ["failed","failed","failed","failed","failed"],
     [3.33,7.26,3.21,6.16,4.02],
     [1.85,1.28,1.45,1.49,1.45],
     [1.05,1.26,1.69,2.44,1.79]])
add(paper="STEREO_DEVO", table="II", dataset="Other", metric="ATE", unit="cm", align="SE3 / RTK",
    note="hnu_campus = large-scale loop (RTK GT, from ESVO2); drone_fast = aggressive flight.",
    methods=_SDEVO_M, seqs=["hnu_campus","drone_fast"],
    values=[
     [1321.80,"failed"],
     ["-","-"],
     [1420.48,154.04],
     [181.77,"failed"],
     ["-","-"],
     [151.81,13.29]])
add(paper="STEREO_DEVO", table="II", dataset="RPG", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note=_SDN, methods=_SDEVO_M, seqs=["rpg_box","rpg_monitor","rpg_bin","rpg_desk","rpg_reader"],
    values=[
     [7.20,3.20,3.10,4.50,5.60],
     [4.22,2.59,1.82,3.99,"-"],
     [20.39,13.17,12.10,6.18,"failed"],
     [4.18,1.69,2.53,3.53,2.12],
     ["-","-","-","-","-"],
     [2.87,1.65,1.54,3.33,3.59]])
add(paper="STEREO_DEVO", table="II", dataset="MVSEC", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note=_SDN, methods=_SDEVO_M, seqs=["indoor 1","indoor 2","indoor 3","indoor 4"],
    values=[
     [7.38,7.39,5.97,"failed"],
     [6.89,"-","-","-"],
     [228.84,134.48,"failed",181.03],
     [5.05,6.12,4.75,10.36],
     [66.62,53.92,37.55,122.48],
     [3.73,5.73,5.18,14.15]])
add(paper="STEREO_DEVO", table="II", dataset="DSEC", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note=_SDN, methods=_SDEVO_M,
    seqs=["city04_a","city04_b","city04_c","city04_d","city09_a","city09_b","city09_c","city09_d","city09_e","city11_a","city11_b"],
    values=[
     [69.14,32.84,82.03,190.67,271.62,138.33,417.00,280.43,339.24,56.82,188.97],
     [26.92,26.48,86.21,68.02,"failed",68.92,1998.86,"failed",744.30,25.14,"failed"],
     [187.03,188.23,145.64,540.98,"failed",561.41,"failed",105.62,801.43,54.53,53.55],
     [16.98,21.70,39.12,18.00,80.86,32.10,361.56,91.51,125.22,12.94,14.83],
     [641.27,726.44,1501.47,1939.15,"-","-","-","-","-","-","-"],
     [23.70,13.56,34.39,31.18,15.73,55.00,273.98,39.38,38.56,10.32,15.58]])
add(paper="STEREO_DEVO", table="II", dataset="VECtor", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note=_SDN, methods=_SDEVO_M,
    seqs=["robot_normal","corner_slow","hdr_normal","sofa_normal","desk_normal","corridors_dolly","units_dolly"],
    values=[
     [16.79,6.45,5.55,"failed",5.12,"failed","failed"],
     ["-","-","-","-","-","-","-"],
     [3.38,7.01,15.65,54.32,"failed","failed","failed"],
     [3.16,1.91,3.79,13.59,3.50,"failed","failed"],
     ["-",13.25,"-","-",86.55,164.53,138.73],
     [1.84,1.49,1.55,4.44,2.00,16.87,32.43]])
add(paper="STEREO_DEVO", table="II", dataset="TUM-VIE", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note=_SDN, methods=_SDEVO_M, seqs=["mocap-1d-trans","mocap-3d-trans","mocap-6dof","mocap-desk","mocap-desk2"],
    values=[
     [8.41,7.47,14.28,5.87,6.23],
     [0.71,4.94,12.02,2.53,4.04],
     ["failed","failed","failed","failed","failed"],
     [1.06,2.32,2.49,3.41,2.41],
     [24.49,26.43,26.31,30.75,33.65],
     [0.89,1.73,2.55,2.24,2.35]])

# Stereo-DEVO Table III: head-to-head vs ESVIO (image-aided) on DSEC + VECtor.
_SD3_M=[("ESVIO","Stereo E+F+I",False),("Stereo-DEVO","Stereo E",True)]
add(paper="STEREO_DEVO", table="III", dataset="DSEC", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note="Stereo-DEVO vs ESVIO (image-aided) head-to-head. ESVIO/Ours numbers differ slightly from T.II "
         "(separate run). Stereo-DEVO wins all DSEC seqs.",
    methods=_SD3_M, seqs=["city04_a","city04_b","city04_c","city04_d","city09_a","city09_b","city09_c","city09_d","city09_e"],
    values=[
     [508.17,129.70,2938.09,2217.39,328.51,3481.49,8043.46,1677.13,438.19],
     [96.86,17.65,481.62,406.20,196.97,267.80,931.15,564.33,246.26]])
add(paper="STEREO_DEVO", table="III", dataset="VECtor", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note="Stereo-DEVO vs ESVIO on VECtor (T.III). ESVIO wins the small normal/HDR seqs; Stereo-DEVO wins large-scale.",
    methods=_SD3_M, seqs=["robot_normal","corner_slow","hdr_normal","sofa_normal","desk_normal","corridors_dolly","units_dolly"],
    values=[
     [4.95,1.43,1.96,5.06,6.00,92.04,872.07],
     [3.16,1.06,6.71,7.18,6.48,196.53,444.51]])
add(paper="STEREO_DEVO", table="III", dataset="DSEC", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note="RPE column of Stereo-DEVO Table III (DSEC).",
    methods=_SD3_M, seqs=["city04_a","city04_b","city04_c","city04_d","city09_a","city09_b","city09_c","city09_d","city09_e"],
    values=[
     [130.73,260.02,279.17,196.22,34.99,856.53,632.14,128.96,54.11],
     [23.70,13.56,34.39,31.18,15.73,55.00,273.98,39.39,36.49]])
add(paper="STEREO_DEVO", table="III", dataset="VECtor", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note="RPE column of Stereo-DEVO Table III (VECtor).",
    methods=_SD3_M, seqs=["robot_normal","corner_slow","hdr_normal","sofa_normal","desk_normal","corridors_dolly","units_dolly"],
    values=[
     [2.20,1.67,0.90,4.55,2.24,17.32,101.99],
     [1.84,1.49,1.55,4.44,2.00,16.87,32.43]])
# --------------------------- ESVO TRO (2007.15548) ---------------------------
# Original ESVO paper. ORB-SLAM2 (stereo+BA) = bundle-adjustment-enabled variant (parentheses in paper).
# Note: ESVO's OWN rpg_monitor ATE = 1.3 cm here, vs 3.3 cm when re-run by DEVO/ESVO2/Stereo-DEVO.
_ESVO_M=[("ORB-SLAM2 (stereo)","Stereo F",False),("ORB-SLAM2 (stereo+BA)","Stereo F",False),
    ("SGM+ICP","Stereo E",False),("ESVO","Stereo E",True)]
_ESVO_RPG=["rpg_bin","rpg_box","rpg_desk","rpg_monitor"]
add(paper="ESVO", table="VI", dataset="RPG", metric="ATE", unit="cm", align="SE3 (stereo, metric)",
    note="ESVO Table VI. ORB-SLAM2 the best overall (esp. with BA); ESVO best/SOTA among event methods.",
    methods=_ESVO_M, seqs=_ESVO_RPG,
    values=[
     [0.9,2.9,7.7,2.5],
     [0.7,1.6,1.8,0.8],
     [13.8,19.8,8.5,29.5],
     [2.8,5.8,3.2,1.3]])
add(paper="ESVO", table="V", dataset="RPG", metric="RPE_R", unit="deg/s", align="SE3 (stereo, metric)",
    note="ESVO Table V rotation RPE.", methods=_ESVO_M, seqs=_ESVO_RPG,
    values=[
     [0.6,1.8,2.4,1.0],
     [0.5,1.7,1.7,0.6],
     [7.6,7.9,10.1,8.1],
     [1.2,3.4,3.1,1.7]])
add(paper="ESVO", table="V", dataset="RPG", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note="ESVO Table V translation RPE.", methods=_ESVO_M, seqs=_ESVO_RPG,
    values=[
     [1.5,5.1,3.3,1.8],
     [1.2,2.7,2.8,1.0],
     [13.3,15.5,14.6,10.7],
     [3.1,7.2,4.5,3.2]])
add(paper="ESVO", table="V", dataset="MVSEC", metric="RPE_R", unit="deg/s", align="SE3 (stereo, metric)",
    note="ESVO Table V on UPenn/MVSEC flying (drone). ESVO clearly best here.",
    methods=_ESVO_M, seqs=["upenn_flying1","upenn_flying3"],
    values=[
     [5.4,5.6],
     [5.8,3.0],
     [4.8,7.3],
     [1.0,1.2]])
add(paper="ESVO", table="V", dataset="MVSEC", metric="RPE_t", unit="cm/s", align="SE3 (stereo, metric)",
    note="ESVO Table V translation RPE on UPenn/MVSEC flying.",
    methods=_ESVO_M, seqs=["upenn_flying1","upenn_flying3"],
    values=[
     [20.4,22.0],
     [16.2,20.1],
     [31.6,26.3],
     [6.5,7.1]])
# --------------------------- SuperEvent (2504.00139) -------------------------
# SuperEvent is an event KEYPOINT detector; its SLAM results = OKVIS2 + SuperEvent (stereo E + IMU).
# Tables 2/3 are relative-pose AUC (HIGHER is better), not trajectory error.
_SE_KP=[("LLAK","E (keypoints)",False),("RATE","E (keypoints)",False),
    ("EventPoint","E (keypoints)",False),("SuperEvent","E (keypoints)",True)]
add(paper="SUPEREVENT", table="2", dataset="ECD (keypoint pose)", metric="AUC", unit="%",
    align="relative-pose AUC (higher=better)",
    note="Keypoint relative-pose estimation AUC on Event-Camera-Dataset. SuperEvent dominates, "
         "esp. high-precision <5deg. NOT a trajectory metric.",
    methods=_SE_KP, seqs=["@5deg","@10deg","@20deg"],
    values=[[0.7,1.4,2.1],[3.3,8.4,18.0],[1.6,3.0,5.4],[22.7,35.8,46.7]])
add(paper="SUPEREVENT", table="3", dataset="EDS (keypoint pose)", metric="AUC", unit="%",
    align="relative-pose AUC (higher=better)",
    note="Keypoint relative-pose AUC on EDS (Prophesee Gen3.1). Confirms generalization across cameras.",
    methods=_SE_KP, seqs=["@5deg","@10deg","@20deg"],
    values=[[0.5,0.7,1.0],[2.1,5.1,10.3],[1.6,2.8,5.2],[15.2,26.4,40.1]])

add(paper="SUPEREVENT", table="4", dataset="TUM-VIE", metric="ATE", unit="cm",
    align="SE3 metric (first 3 rows Sim3 scale-aligned)",
    note="*** Key cross-check: DEVO/DEIO 'w/ scale alignment' (Sim3) need scale help; DEIO metric=1.24 "
         "vs scale-aligned=1.00. OKVIS2+SuperEvent (metric, stereo E+I) best at 0.55. "
         "ICRA'24 average '-' due to a failed seq.",
    methods=[("EVO (scale-aligned)","E",False),("DEVO (scale-aligned)","E",False),
        ("DEIO (scale-aligned)","E+I",False),("DEIO (metric)","E+I",False),("ESVO","Stereo E",False),
        ("ES-PTAM","Stereo E",False),("ICRA'24 (ESVIO-AA)","Stereo E+I",False),("ESVO2","Stereo E+I",False),
        ("OKVIS2+SuperEvent","Stereo E+I",True),("OKVIS2+SuperEvent (no loop)","Stereo E+I",True)],
    seqs=["mocap-1d-trans","mocap-3d-trans","mocap-6dof","mocap-desk","mocap-desk2","average"],
    values=[
     [7.50,12.50,85.50,54.10,75.20,46.96],
     [0.50,1.10,1.60,1.70,1.00,1.18],
     [0.42,1.11,1.37,1.36,0.73,1.00],
     [1.08,1.12,1.39,1.41,1.19,1.24],
     [12.54,17.19,13.46,12.92,4.42,12.11],
     [1.05,8.53,10.25,2.50,7.20,5.91],
     [3.85,18.90,"failed",8.99,9.47,"-"],
     [3.33,7.26,3.21,6.16,4.02,4.78],
     [0.44,0.89,0.43,0.58,0.41,0.55],
     [0.43,0.89,0.43,0.70,0.40,0.57]])

add(paper="SUPEREVENT", table="5", dataset="VECtor", metric="ATE", unit="cm", align="SE3 metric, online calib",
    note="VECtor LARGE-scale (metric). DEIO ATE 492.65/826.38 cm = scale failure under metric eval "
         "(matches our finding). ESVO fails on most. DEVO omitted ('cannot recover absolute scale').",
    methods=[("OKVIS2+SuperEvent","Stereo E+I",True),("DEIO","E+I",False),("ESVO","Stereo E",False)],
    seqs=["corridors_dolly","corridors_walk","units_dolly","units_scooter","school_dolly","school_scooter"],
    values=[
     [33.13,133.16,122.61,59.05,69.96,39.07],
     [492.65,325.00,826.38,304.14,"-","-"],
     ["failed","failed","failed","failed",1371.0,983.0]])

add(paper="SUPEREVENT", table="6", dataset="TUM-VIE (loop-floor)", metric="ATE", unit="cm", align="SE3 metric",
    note="Loop-closure effect for OKVIS2+SuperEvent: loop closure cuts ATE ~30x on long loop-floor seqs.",
    methods=[("OKVIS2+SuperEvent (loop)","Stereo E+I",True),("OKVIS2+SuperEvent (no loop)","Stereo E+I",True)],
    seqs=["loop_floor0","loop_floor1","loop_floor2","loop_floor3"],
    values=[
     [4.96,4.64,8.92,4.74],
     [132.11,161.92,116.00,129.17]])
# --------------------------- PL-EVIO (TASE 2024) -----------------------------
_PLV_S=["vicon_hdr1","vicon_hdr2","vicon_hdr3","vicon_hdr4","vicon_darktolight1","vicon_darktolight2",
    "vicon_lighttodark1","vicon_lighttodark2","vicon_dark1","vicon_dark2","vicon_aggressive_hdr"]
add(paper="PLEVIO", table="I", dataset="Mono-HKU vicon (DAVIS346)", metric="MPE", unit="%",
    align="SE3, first 5 s",
    note="arclab-HKU 'vicon_*' with DAVIS346. PL-EVIO (E+F+I) best; in dark seqs PL-EIO (event-only) "
         "can beat PL-EVIO since image point tracking degrades. (Average row omitted.)",
    methods=[("VINS-MONO","F+I",False),("ORB-SLAM3","F",False),("PL-VINS","F+I",False),
        ("Ultimate-SLAM (EIO)","E+I",False),("Ultimate-SLAM (EVIO)","E+F+I",False),
        ("Mono-EIO","E+I",False),("PL-EIO","E+I",False),("PL-EIO+","E+I",False),("PL-EVIO","E+F+I",True)],
    seqs=_PLV_S,
    values=[
     [0.96,1.60,2.28,1.40,0.51,0.98,0.55,0.55,0.88,0.52,"failed"],
     [0.32,0.75,0.60,0.70,0.75,0.76,0.41,0.58,"failed",0.60,"failed"],
     [0.67,0.90,0.69,0.66,0.84,1.50,0.64,0.93,0.53,"failed",1.94],
     [1.49,1.28,0.66,1.84,1.33,1.48,1.79,1.32,1.75,1.10,"failed"],
     [2.44,1.11,0.83,1.49,1.00,0.79,0.84,1.49,3.45,0.63,2.30],
     [0.59,0.74,0.72,0.37,0.81,0.42,0.29,0.79,1.02,0.49,0.66],
     [0.67,0.45,0.74,0.37,0.78,0.44,0.42,0.73,0.64,0.30,0.62],
     [0.57,0.54,0.69,0.32,0.66,0.51,0.33,0.53,0.35,0.38,0.50],
     [0.17,0.12,0.19,0.11,0.14,0.12,0.13,0.16,0.43,0.47,1.97]])
add(paper="PLEVIO", table="I", dataset="Mono-HKU vicon (DVXplorer)", metric="MPE", unit="%",
    align="SE3, first 5 s",
    note="Same 'vicon_*' seqs captured with DVXplorer (640x480) event camera.",
    methods=[("Ultimate-SLAM (EIO)","E+I",False),("Mono-EIO","E+I",False),
        ("PL-EIO","E+I",False),("PL-EIO+","E+I",False)],
    seqs=_PLV_S+["average"],
    values=[
     [1.94,2.38,0.83,2.09,1.96,1.57,2.48,1.37,3.79,2.81,"failed",2.12],
     [0.30,0.37,0.69,0.26,0.80,0.57,0.81,0.75,0.35,0.41,0.65,0.54],
     [0.47,0.22,0.47,0.27,0.71,0.56,0.43,0.67,0.51,0.38,0.62,0.48],
     [0.41,0.21,0.36,0.25,0.71,0.47,0.54,0.60,0.41,0.41,0.50,0.45]])
add(paper="PLEVIO", table="II", dataset="UZH-FPV", metric="MPE", unit="%", align="SE3, all",
    note="UZH-FPV. PL-EVIO beats stereo VIO using only a mono DAVIS346; most VINS-Fusion/USLAM seqs fail.",
    methods=[("VINS-Fusion","Stereo F+I",False),("ORB-SLAM3","Stereo F+I",False),("VINS-MONO","F+I",False),
        ("Ultimate-SLAM","E+F+I",False),("PL-EVIO","E+F+I",True)],
    seqs=["indoor_forward_3","indoor_forward_5","indoor_forward_6","indoor_forward_7","indoor_forward_9",
          "indoor_forward_10","indoor_45_degree_2","indoor_45_degree_4","indoor_45_degree_9","average"],
    values=[
     [0.84,"failed",1.45,0.61,2.87,4.48,"failed","failed","failed",5.26],
     [0.55,1.19,"failed",0.36,0.77,1.02,2.18,1.53,0.49,2.10],
     [0.65,1.07,0.25,0.37,0.51,0.92,0.53,1.72,1.25,0.81],
     ["failed","failed","failed","failed","failed","failed","failed",9.79,4.74,7.26],
     [0.38,0.90,0.30,0.55,0.44,1.06,0.55,1.30,0.76,0.70]])
add(paper="PLEVIO", table="III", dataset="ECD (DAVIS240C)", metric="MPE", unit="%", align="SE3, first 5 s",
    note="ECD/Event-Camera-Dataset. PL-EVIO (E+F+I) SOTA among EIO/EVIO. Baselines: [28]=Zhu, [13]=Rebecq, "
         "[14]=Ultimate-SLAM, [47]=Alzugaray-Chli, [29]=EKLT-VIO, [5]=Mono-EIO.",
    methods=[("Zhu et al.","E+I",False),("Rebecq EVIO","E+I",False),("Ultimate-SLAM (EIO)","E+I",False),
        ("Ultimate-SLAM (EVIO)","E+F+I",False),("Alzugaray-Chli","E+I",False),("EKLT-VIO","E+F+I",False),
        ("Mono-EIO","E+I",False),("PL-EVIO","E+F+I",True)],
    seqs=["boxes_translation","hdr_boxes","boxes_6dof","dynamic_translation","dynamic_6dof",
          "poster_translation","hdr_poster","poster_6dof","average"],
    values=[
     [2.69,1.23,3.61,1.90,4.07,0.94,2.63,3.56,2.58],
     [0.57,0.92,0.69,0.47,0.54,0.89,0.59,0.82,0.69],
     [0.76,0.67,0.44,0.59,0.38,0.15,0.49,0.30,0.47],
     [0.27,0.37,0.30,0.18,0.19,0.12,0.31,0.28,0.25],
     [2.55,1.75,2.03,1.32,0.52,1.34,0.57,1.50,1.45],
     [0.48,0.46,0.84,0.40,0.79,0.35,0.65,0.35,0.54],
     [0.34,0.40,0.61,0.26,0.43,0.40,0.40,0.26,0.39],
     [0.06,0.10,0.21,0.24,0.48,0.54,0.12,0.14,0.24]])
# ----------------------------- EDS (CVPR 2022) -------------------------------
# EDS evaluates on the RPG/Zhou stereo-DAVIS sequences (bin/box/desk/monitor). EDS = events+frames (mono).
_EDS_RPG=["rpg_bin","rpg_box","rpg_desk","rpg_monitor"]
add(paper="EDS", table="2", dataset="RPG", metric="ATE", unit="cm", align="SE3 (per-paper)",
    note="EDS vs event-based VO. EVO* (rpg_bin/rpg_box) failed after <=30%. EDS (mono E+F) beats even "
         "stereo ESVO without using stereo parallax or IMU.",
    methods=[("ESVO","Stereo E",False),("Ultimate-SLAM","E+F+I",False),("EVO","E",False),("EDS","E+F",True)],
    seqs=_EDS_RPG,
    values=[
     [2.8,5.8,3.2,3.3],
     [7.7,9.5,9.8,6.5],
     [13.2,14.2,5.2,7.8],
     [1.1,2.1,1.5,1.0]])
add(paper="EDS", table="2", dataset="RPG", metric="ARE", unit="deg", align="SE3 (per-paper)",
    note="Rotation error column of EDS Table 2. EVO* = failed <=30%.",
    methods=[("ESVO","Stereo E",False),("Ultimate-SLAM","E+F+I",False),("EVO","E",False),("EDS","E+F",True)],
    seqs=_EDS_RPG,
    values=[
     [7.61,9.46,7.25,2.74],
     [7.18,8.84,32.46,7.01],
     [50.26,170.36,8.25,7.77],
     [0.99,1.83,1.87,0.60]])
add(paper="EDS", table="3", dataset="RPG", metric="ATE", unit="cm", align="SE3 (per-paper)",
    note="EDS vs frame-based VO. ORB-SLAM(F+F)=stereo+BA is best overall; EDS ~ DSO and beats mono "
         "ORB-SLAM. DSO-dagger runs on E2VID-reconstructed frames; '-' = failed.",
    methods=[("ORB-SLAM (stereo)","Stereo F",False),("ORB-SLAM (mono)","F",False),("DSO","F",False),
        ("DSO-dagger (E2VID)","F",False),("EDS","E+F",True)],
    seqs=_EDS_RPG,
    values=[
     [0.7,1.6,1.8,0.8],
     [2.4,3.9,3.8,3.1],
     [1.1,2.0,10.0,0.9],
     ["failed","failed",1.6,2.1],
     [1.1,2.1,1.5,1.0]])

# ----------------------------- Zhu EVIO (CVPR 2017) --------------------------
_ECD10=["shapes_translation","shapes_6dof","poster_translation","poster_6dof","hdr_poster",
    "boxes_translation","boxes_6dof","hdr_boxes","dynamic_translation","dynamic_6dof"]
add(paper="ZHU_EVIO", table="1", dataset="ECD (DAVIS240C)", metric="MPE", unit="%", align="SE3",
    note="Zhu's EVIO vs a KLT-frame VIO baseline. These EVIO numbers are exactly the 'Zhu et al.' "
         "baseline later cited by PL-EVIO/DEIO.",
    methods=[("EVIO (Zhu)","E+I",True),("KLT-VIO","F+I",False)],
    seqs=_ECD10,
    values=[
     [2.42,2.69,0.94,3.56,2.63,2.69,3.61,1.23,1.90,4.07],
     [1.98,8.95,0.97,2.17,2.67,2.28,2.91,5.65,2.12,4.49]])
add(paper="ZHU_EVIO", table="1", dataset="ECD (DAVIS240C)", metric="MRE", unit="deg/m", align="SE3",
    note="Rotation error column of Zhu Table 1.",
    methods=[("EVIO (Zhu)","E+I",True),("KLT-VIO","F+I",False)],
    seqs=_ECD10,
    values=[
     [0.52,0.40,0.02,0.56,0.11,0.09,0.34,0.05,0.02,0.56],
     [0.04,0.06,0.01,0.08,0.09,0.01,0.03,0.11,0.03,0.05]])

# --------------------------- Ultimate SLAM (RAL 2018) ------------------------
_US_S=["boxes_6dof","boxes_translation","dynamic_6dof","dynamic_translation","hdr_boxes","hdr_poster",
    "poster_6dof","poster_translation","shapes_6dof","shapes_translation"]
add(paper="ULTIMATE_SLAM", table="I", dataset="ECD (DAVIS240C)", metric="MPE", unit="%", align="SE3, 5s (3-8s)",
    note="Sensor-suite ablation: combining frames+events+IMU gives ~85% better accuracy than frames+IMU "
         "and ~130% better than events+IMU on average.",
    methods=[("Ultimate-SLAM (Fr+E+I)","E+F+I",True),("Ultimate-SLAM (E+I)","E+I",False),
        ("Ultimate-SLAM (Fr+I)","F+I",False)],
    seqs=_US_S,
    values=[
     [0.30,0.27,0.19,0.18,0.37,0.31,0.28,0.12,0.10,0.26],
     [0.44,0.76,0.38,0.59,0.67,0.49,0.30,0.15,0.48,0.41],
     [0.30,0.17,0.62,0.67,0.78,0.28,0.59,0.23,0.17,0.29]])
add(paper="ULTIMATE_SLAM", table="I", dataset="ECD (DAVIS240C)", metric="MRE", unit="deg/m", align="SE3, 5s (3-8s)",
    note="Yaw error column of Ultimate SLAM Table I.",
    methods=[("Ultimate-SLAM (Fr+E+I)","E+F+I",True),("Ultimate-SLAM (E+I)","E+I",False),
        ("Ultimate-SLAM (Fr+I)","F+I",False)],
    seqs=_US_S,
    values=[
     [0.04,0.02,0.10,0.15,0.03,0.05,0.07,0.04,0.04,0.06],
     [0.05,0.05,0.06,0.16,0.09,0.04,0.08,0.04,0.06,0.04],
     [0.06,0.03,0.10,0.26,0.17,0.08,0.11,0.08,0.05,0.11]])
add(paper="ULTIMATE_SLAM", table="II", dataset="ECD (DAVIS240C)", metric="MPE", unit="%", align="SE3, 5s (3-8s)",
    note="Ultimate SLAM (Fr+E+I) vs the prior SOTA event-inertial method Rebecq et al.[13] (E+I). "
         "Ultimate SLAM better on almost all sequences.",
    methods=[("Ultimate-SLAM (Fr+E+I)","E+F+I",True),("Rebecq EVIO","E+I",False)],
    seqs=_US_S,
    values=[
     [0.30,0.27,0.19,0.18,0.37,0.31,0.28,0.12,0.10,0.26],
     [0.36,0.31,0.56,0.39,0.59,0.33,0.40,0.46,0.42,0.50]])
add(paper="ULTIMATE_SLAM", table="II", dataset="ECD (DAVIS240C)", metric="MRE", unit="deg/m", align="SE3, 5s (3-8s)",
    note="Yaw error column of Ultimate SLAM Table II.",
    methods=[("Ultimate-SLAM (Fr+E+I)","E+F+I",True),("Rebecq EVIO","E+I",False)],
    seqs=_US_S,
    values=[
     [0.04,0.02,0.10,0.15,0.03,0.05,0.07,0.04,0.04,0.06],
     [0.11,0.08,0.41,0.06,0.20,0.19,0.16,0.10,0.18,0.13]])
# ESVO2 rotation columns (Table VI ARE[deg], Table VII RPE-R[deg/s]) -- completes ESVO2 capture.
add(paper="ESVO2", table="VI", dataset="RPG", metric="ARE", unit="deg", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M, seqs=["rpg_box","rpg_monitor","rpg_bin","rpg_desk","rpg_reader"],
    values=[
     [5.95,6.21,1.98,10.49,3.80],
     [6.62,1.52,3.29,3.44,"-"],
     [12.35,17.67,11.76,3.60,"failed"],
     [4.25,3.79,3.87,7.09,"-"],
     [3.30,3.53,3.54,6.72,1.78],
     [2.79,2.19,1.23,4.11,1.54]])
add(paper="ESVO2", table="VI", dataset="MVSEC", metric="ARE", unit="deg", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M, seqs=["indoor 1","indoor 2","indoor 3","indoor 4"],
    values=[
     [4.40,5.69,2.94,"failed"],
     [14.93,"-","-","-"],
     [22.32,43.49,"failed",32.15],
     [6.57,"-",3.01,"-"],
     [11.16,12.14,2.73,"failed"],
     [1.69,4.53,2.63,10.96]])
add(paper="ESVO2", table="VI", dataset="DSEC", metric="ARE", unit="deg", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M,
    seqs=["city04_a","city04_b","city04_c","city04_d","city04_e","city04_f","city09_b","city11_a","city11_b"],
    values=[
     [8.17,1.97,14.04,21.62,6.89,6.36,5.17,1.96,44.57],
     [3.17,2.04,6.02,37.13,3.97,10.65,1.75,"-","-"],
     [5.07,3.69,7.35,3.63,5.57,6.19,"failed",2.40,3.13],
     [5.59,1.38,14.62,"-",6.28,20.78,"-",7.71,"-"],
     [4.36,2.64,11.39,14.14,5.08,5.52,2.92,4.52,12.78],
     [3.33,1.55,10.26,8.87,3.54,5.00,2.17,1.85,10.61]])
add(paper="ESVO2", table="VI", dataset="VECtor", metric="ARE", unit="deg", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M,
    seqs=["robot_normal","robot_fast","corner_slow","hdr_normal","sofa_normal","desk_normal"],
    values=[
     [19.79,"failed",9.63,24.54,"failed",19.91],
     ["-","-","-","-","-","-"],
     [5.61,"failed",32.67,18.42,12.11,"failed"],
     ["-","-","-","-","-","-"],
     [20.46,"failed",6.15,14.11,"failed",10.36],
     [5.03,16.29,2.96,7.82,20.11,6.82]])
add(paper="ESVO2", table="VI", dataset="TUM-VIE", metric="ARE", unit="deg", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M, seqs=["mocap-1d-trans","mocap-3d-trans","mocap-6dof","mocap-desk","mocap-desk2"],
    values=[
     [13.47,19.20,17.59,14.56,5.86],
     [6.02,15.62,14.01,3.37,10.12],
     ["failed","failed","failed","failed","failed"],
     ["-","-","-","-","-"],
     [6.67,17.93,"failed",6.95,4.32],
     [6.30,6.61,4.17,2.40,3.88]])
add(paper="ESVO2", table="VII", dataset="RPG", metric="RPE_R", unit="deg/s", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M, seqs=["rpg_box","rpg_monitor","rpg_bin","rpg_desk","rpg_reader"],
    values=[
     [3.40,1.70,1.20,3.10,2.50],
     [2.10,1.14,1.00,1.77,"-"],
     [2.91,1.71,2.30,3.94,"failed"],
     [5.11,6.12,4.14,8.56,"-"],
     [2.65,1.29,1.23,2.60,1.37],
     [3.02,1.15,0.94,1.76,1.32]])
add(paper="ESVO2", table="VII", dataset="MVSEC", metric="RPE_R", unit="deg/s", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M, seqs=["indoor 1","indoor 2","indoor 3","indoor 4"],
    values=[
     [1.09,1.72,1.08,"failed"],
     [1.68,"-","-","-"],
     [2.91,3.58,"failed",15.85],
     [1.28,"-",0.92,"-"],
     [2.09,3.77,0.99,"failed"],
     [0.98,1.42,0.77,3.84]])
add(paper="ESVO2", table="VII", dataset="DSEC", metric="RPE_R", unit="deg/s", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M,
    seqs=["city04_a","city04_b","city04_c","city04_d","city04_e","city04_f","city09_b","city11_a","city11_b"],
    values=[
     [1.02,0.50,0.65,1.22,1.40,1.07,0.27,0.56,3.34],
     [0.53,0.44,1.28,1.01,0.25,1.27,0.17,"-","-"],
     [0.66,3.07,0.60,1.17,1.31,1.29,"failed",0.61,0.57],
     [0.95,0.87,0.56,"-",0.81,0.96,"-",0.49,"-"],
     [0.82,0.67,0.93,0.73,0.71,2.26,0.24,0.53,0.95],
     [0.60,0.43,0.55,0.41,0.38,0.38,0.21,0.30,0.45]])
add(paper="ESVO2", table="VII", dataset="VECtor", metric="RPE_R", unit="deg/s", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M,
    seqs=["robot_normal","robot_fast","corner_slow","hdr_normal","sofa_normal","desk_normal"],
    values=[
     [6.72,"failed",4.07,2.27,"failed",2.43],
     ["-","-","-","-","-","-"],
     [2.08,"failed",1.93,3.96,2.03,"failed"],
     ["-","-","-","-","-","-"],
     [4.92,"failed",1.71,2.44,"failed",2.82],
     [2.36,5.05,1.34,1.53,7.15,1.68]])
add(paper="ESVO2", table="VII", dataset="TUM-VIE", metric="RPE_R", unit="deg/s", align="SE3 (stereo, metric)",
    note=_E2N, methods=_ESVO2_M, seqs=["mocap-1d-trans","mocap-3d-trans","mocap-6dof","mocap-desk","mocap-desk2"],
    values=[
     [3.69,3.41,9.49,2.93,2.12],
     [0.23,2.58,3.61,0.99,2.98],
     ["failed","failed","failed","failed","failed"],
     ["-","-","-","-","-"],
     [0.97,1.79,"failed",1.00,2.15],
     [0.81,0.83,1.16,0.98,0.91]])
# @@DATA@@
# =========================== END TABLE DATA ===================================

# ---------------------------------------------------------------------------
# Expansion + generation
# ---------------------------------------------------------------------------
HIGHER_BETTER = {"AUC"}

def infer_mtype(modality):
    """metric (absolute scale) vs up-to-scale (mono vision-only, needs Sim3)."""
    m = modality.lower()
    if "stereo" in m: return "metric"
    if "+i" in m or "imu" in m or m.endswith(" i") or m == "i": return "metric"
    return "up-to-scale"

def rows_from_tables():
    rows = []
    for t in TABLES:
        methods = t["methods"]          # list of (name, modality, proposed_bool)
        seqs    = t["seqs"]
        metric  = t["metric"]; unit = t["unit"]
        for mi, (mname, modality, proposed) in enumerate(methods):
            mtype = t.get("mtype_override", {}).get(mname) or infer_mtype(modality)
            vals = t["values"][mi]
            for si, seq in enumerate(seqs):
                v = vals[si]
                if v == "-" or v is None:
                    status, value = "n/a", ""
                elif v == "failed":
                    status, value = "failed", ""
                else:
                    status, value = "ok", v
                rows.append(dict(
                    paper=t["paper"], paper_short=PAPERS[t["paper"]]["short"],
                    venue=PAPERS[t["paper"]]["venue"], year=PAPERS[t["paper"]]["year"],
                    table=t["table"], method=mname, proposed="yes" if proposed else "no",
                    modality=modality, metric_type=mtype, alignment=t.get("align",""),
                    dataset=t["dataset"], sequence=seq, sequence_norm=norm_seq(seq),
                    metric=metric, unit=unit, value=value, status=status,
                    note=t.get("note","")))
    return rows

FIELDS = ["paper","paper_short","venue","year","table","method","proposed","modality",
          "metric_type","alignment","dataset","sequence","sequence_norm","metric","unit",
          "value","status","note"]

def write_csv(rows):
    with open(os.path.join(HERE,"results.csv"),"w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
        for r in rows: w.writerow(r)

def write_papers_csv():
    with open(os.path.join(HERE,"papers.csv"),"w",newline="") as f:
        w = csv.writer(f)
        w.writerow(["key","short","authors","venue","year","cite","proposed_method","color"])
        for k,p in PAPERS.items():
            w.writerow([k,p["short"],p["authors"],p["venue"],p["year"],p["cite"],p["proposed"],p["color"]])

def leaderboard(rows):
    """best (lowest, or highest for AUC) reported value per dataset/seq_norm/metric."""
    groups = defaultdict(list)
    for r in rows:
        if r["status"]!="ok": continue
        groups[(r["dataset"], r["sequence_norm"], r["metric"], r["unit"])].append(r)
    out = []
    for (ds,seq,metric,unit), rs in sorted(groups.items()):
        hib = metric in HIGHER_BETTER
        best = (max if hib else min)(rs, key=lambda r: float(r["value"]))
        # all distinct methods + their best value (for context)
        permethod = {}
        for r in rs:
            v=float(r["value"]); m=r["method"]
            if m not in permethod or (v>permethod[m][0] if hib else v<permethod[m][0]):
                permethod[m]=(v,r["paper_short"],r["table"])
        out.append(dict(dataset=ds, sequence=seq, metric=metric, unit=unit,
                        best_method=best["method"], best_value=best["value"],
                        best_modality=best["modality"], best_metric_type=best["metric_type"],
                        best_paper=best["paper_short"], best_table=best["table"],
                        n_methods=len(permethod)))
    return out

def write_leaderboard(rows):
    lb = leaderboard(rows)
    with open(os.path.join(HERE,"leaderboard.csv"),"w",newline="") as f:
        w=csv.DictWriter(f, fieldnames=["dataset","sequence","metric","unit","best_method",
            "best_value","best_modality","best_metric_type","best_paper","best_table","n_methods"])
        w.writeheader()
        for r in lb: w.writerow(r)
    # markdown grouped by dataset
    by_ds=defaultdict(list)
    for r in lb: by_ds[r["dataset"]].append(r)
    with open(os.path.join(HERE,"leaderboard.md"),"w") as f:
        f.write("# Best reported result per (dataset, sequence, metric)\n\n")
        f.write("Auto-generated by `build_db.py`. 'Best' = lowest error "
                "(highest for AUC). `metric_type` flags whether the winning method is "
                "metric-scale or up-to-scale (Sim3). Always read alongside the per-row "
                "`alignment` in `results.csv` and the caveats in `conclusions.md`.\n\n")
        for ds in sorted(by_ds):
            f.write(f"\n## {ds}\n\n")
            f.write("| sequence | metric | best | method | type | source |\n")
            f.write("|---|---|---|---|---|---|\n")
            for r in sorted(by_ds[ds], key=lambda x:(x["sequence"],x["metric"])):
                f.write(f"| {r['sequence']} | {r['metric']} ({r['unit']}) | "
                        f"**{r['best_value']}** | {r['best_method']} | {r['best_metric_type']} | "
                        f"{r['best_paper']} T.{r['best_table']} |\n")

def write_tex(rows):
    lines=[]
    lines.append("% Auto-generated by build_db.py.  Requires: \\usepackage[table]{xcolor}, longtable.")
    for k,p in PAPERS.items():
        lines.append(f"\\definecolor{{c{k}}}{{HTML}}{{{p['color']}}}")
    lines.append("% color legend: each paper has a colored provenance tag [short T.<table>].")
    lines.append("\\begin{longtable}{l l l l l r l l}")
    lines.append("\\caption{Event-camera VO/VIO results database (auto-generated). "
                 "Provenance tag color = source paper.}\\\\")
    lines.append("\\hline Dataset & Sequence & Method & Modality & Scale & Value & Metric & Source\\\\ \\hline")
    lines.append("\\endfirsthead \\hline Dataset & Sequence & Method & Modality & Scale & Value & Metric & Source\\\\ \\hline \\endhead")
    def esc(s): return str(s).replace("_","\\_").replace("&","\\&").replace("%","\\%")
    for r in rows:
        val = r["value"] if r["status"]=="ok" else ("\\textit{failed}" if r["status"]=="failed" else "--")
        tag = f"\\textcolor{{c{r['paper']}}}{{[{esc(r['paper_short'])} T.{esc(r['table'])}]}}"
        sc = "metric" if r["metric_type"]=="metric" else "up-to-scale"
        lines.append(" & ".join([esc(r["dataset"]),esc(r["sequence"]),esc(r["method"]),
            esc(r["modality"]),sc,str(val),f"{esc(r['metric'])} [{esc(r['unit'])}]",tag])+"\\\\")
    lines.append("\\hline \\end{longtable}")
    with open(os.path.join(HERE,"results.tex"),"w") as f:
        f.write("\n".join(lines)+"\n")

def write_discrepancies(rows):
    """Cells where the SAME (dataset,seq,method,metric) is reported with DIFFERENT values across
    papers -- exposes differing eval protocols (alignment/GT/run), e.g. DEIO's scale on DSEC/VECtor."""
    g = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["status"]!="ok": continue
        g[(r["dataset"],r["sequence_norm"],r["method"],r["metric"],r["unit"])][r["value"]].append(
            f"{r['paper_short']} T.{r['table']}")
    out=[]
    for (ds,seq,m,met,unit),vals in g.items():
        if len(vals)>1:
            spread=max(float(v) for v in vals)/max(min(float(v) for v in vals),1e-9)
            out.append((round(spread,1),ds,seq,m,met,unit,vals))
    out.sort(reverse=True)
    with open(os.path.join(HERE,"discrepancies.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["max/min_ratio","dataset","sequence","method","metric","unit","values(source)"])
        for sp,ds,seq,m,met,unit,vals in out:
            w.writerow([sp,ds,seq,m,met,unit,
                " | ".join(f"{v} ({','.join(sorted(set(ps)))})" for v,ps in vals.items())])
    return len(out)

def main():
    rows = rows_from_tables()
    write_csv(rows); write_papers_csv(); write_leaderboard(rows); write_tex(rows)
    nd = write_discrepancies(rows)
    print(f"tables encoded : {len(TABLES)}")
    print(f"data points    : {len(rows)}  ({sum(1 for r in rows if r['status']=='ok')} ok, "
          f"{sum(1 for r in rows if r['status']=='failed')} failed, "
          f"{sum(1 for r in rows if r['status']=='n/a')} n/a)")
    print(f"cross-paper discrepant cells: {nd} (-> discrepancies.csv)")
    print("wrote: results.csv, papers.csv, leaderboard.csv, leaderboard.md, results.tex, discrepancies.csv")

def query_best(args):
    rows = rows_from_tables(); lb = leaderboard(rows)
    ds=args[0].lower(); seq=norm_seq(args[1]) if len(args)>1 else None
    metric=args[2].upper() if len(args)>2 else None
    hits=[r for r in lb if ds in r["dataset"].lower()
          and (seq is None or r["sequence"]==seq)
          and (metric is None or r["metric"].upper()==metric)]
    if not hits:
        print("no match. datasets:", sorted({r['dataset'] for r in lb}))
        if seq: print("sequences in matching datasets:",
            sorted({r['sequence'] for r in lb if ds in r['dataset'].lower()}))
        return
    for r in hits:
        print(f"{r['dataset']:14s} {r['sequence']:16s} {r['metric']:5s}={r['best_value']:>8} "
              f"{r['unit']:5s} -> {r['best_method']} ({r['best_metric_type']}) "
              f"[{r['best_paper']} T.{r['best_table']}]  ({r['n_methods']} methods compared)")

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="--best":
        query_best(sys.argv[2:])
    else:
        main()

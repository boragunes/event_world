# SE(3) reference table — metric baselines only

Scope: methods that recover metric scale without external help, which is the
like-for-like set for a stereo submission. Monocular up-to-scale results (DEVO,
DPVO, mono ORB-SLAM3) and every Sim(3)/scale-corrected row are excluded.

Published values are the **best** SE(3) ATE across all papers reporting that
method+sequence (section 6.3: beat a baseline at its strongest showing). ATE in cm.

Cell key: **bold** = our own SE(3) run · plain = published only, we have not run it ·
`div` / `ni` = we ran it, it diverged / never initialised · — = no published value.


## RPG

| sequence | Stereo-DEVO | ESVO2 | ESVIO | ESIO | DEIO | ES-PTAM | staged |
|---|---|---|---|---|---|---|---|
| rpg_box | 1.92 | 4.31 | 4.41 | 11.38 | — | 4.06 | ⬜ |
| rpg_monitor | 0.91 | 2.31 | 3.48 | 7.87 | — | 2.34 | ⬜ |
| rpg_bin | 1.16 | 2.27 | 2.28 | 7.08 | — | 2.57 | ⬜ |
| rpg_desk | 1.46 | 1.57 | 2.03 | 3.16 | — | 2.84 | ⬜ |
| rpg_reader | 3.78 | 2.68 | — | — | — | — | ⬜ |

## MVSEC

| sequence | Stereo-DEVO | ESVO2 | ESVIO | ESIO | DEIO | ES-PTAM | staged |
|---|---|---|---|---|---|---|---|
| indoor_flying1 | 3.76 | 7.63 | 9.63 | 820.36 | 7.52 | 15.02 | ⬜ |
| indoor_flying2 | 8.00 | 10.05 | — | 417.85 | 6.96 | — | ⬜ |
| indoor_flying3 | 5.57 | 7.35 | 8.06 | — | 29.75 | — | ⬜ |
| indoor_flying4 | 4.57 | 5.59 | — | 173.51 | 12.71 | — | ⬜ |

## DSEC

| sequence | Stereo-DEVO | ESVO2 | ESVIO | ESIO | DEIO | ES-PTAM | staged |
|---|---|---|---|---|---|---|---|
| city04_a | 96.86 | 56.17 | 201.53 | 543.50 | 80.60 | 131.62 | ⬜ |
| city04_b | 17.65 | 73.83 | 48.33 | 295.10 | 35.40 | 29.02 | ⬜ |
| city04_c | 481.62 | 508.71 | 1400.76 | 896.20 | 413.80 | 1184.37 | ⬜ |
| city04_d | 406.20 | 546.58 | 921.70 | 2977.00 | 207.60 | 1053.87 | ⬜ |
| city09_a | 196.97 | 1183.04 | 328.51 | — | — | — | ⬜ |
| city09_b | 267.80 | 87.83 | 3481.49 | 2887.84 | — | 195.14 | ⬜ |
| city09_c | 931.15 | 1648.30 | 8043.46 | — | — | 3673.80 | ⬜ |
| city09_d | 564.33 | 1920.36 | 1677.13 | 1766.16 | — | — | ⬜ |
| city09_e | 246.26 | 1075.09 | 438.19 | 4201.00 | — | 1480.79 | ⬜ |
| city11_a | 47.56 | 48.77 | 406.11 | 107.36 | — | 117.86 | ⬜ |
| city11_b | 282.06 | 441.79 | — | 300.14 | — | — | ⬜ |

## VECtor

| sequence | Stereo-DEVO | ESVO2 | ESVIO | ESIO | DEIO | ES-PTAM | staged |
|---|---|---|---|---|---|---|---|
| corner_slow | **11.93** | **`div`** | **1.62** | **8.72** | **3.99** | — | ✅ |
| robot_normal | **3.63** | **6.14** | **3.48** | **`div`** | **2.93** | — | ✅ |
| desk_normal | **6.88** | **16.42** | **3.63** | **35.68** | **3.54** | — | ✅ |
| sofa_normal | **7.21** | **`div`** | **7.44** | **27.29** | **9.99** | — | ✅ |
| hdr_normal | **6.59** | **18.67** | **1.84** | **32.94** | **38.83** | — | ✅ |
| corridors_dolly | 196.53 | — | 92.04 | — | 492.65 | — | ⬜ |
| units_dolly | 444.51 | — | 872.07 | — | 826.38 | — | ⬜ |

## TUM-VIE

| sequence | Stereo-DEVO | ESVO2 | ESVIO | ESIO | DEIO | ES-PTAM | staged |
|---|---|---|---|---|---|---|---|
| tumvie_1d_trans | 1.05 | 3.33 | — | — | 1.85 | 1.05 | ⬜ |
| tumvie_3d_trans | 1.26 | 7.26 | — | — | 1.28 | 8.53 | ⬜ |
| tumvie_6dof | 1.69 | 3.21 | — | — | 1.45 | 10.25 | ⬜ |
| tumvie_desk | 2.44 | 6.16 | — | — | 1.49 | 2.50 | ⬜ |
| tumvie_desk2 | 1.79 | 4.02 | — | — | 1.45 | 7.20 | ⬜ |

## Other

| sequence | Stereo-DEVO | ESVO2 | ESVIO | ESIO | DEIO | ES-PTAM | staged |
|---|---|---|---|---|---|---|---|
| hnu_campus | 151.81 | 181.77 | — | 1420.48 | — | — | ⬜ |
| drone_fast | 13.29 | — | — | 154.04 | — | — | ⬜ |

## VECtor — sequences we ran beyond the plan inventory

| sequence | Stereo-DEVO | ESVO2 | ESVIO | ESIO | DEIO | ES-PTAM | staged |
|---|---|---|---|---|---|---|---|
| mountain_normal | **8.90** | **35.62** | **5.70** | **8.26** | **15.92** | — | ✅ |
| robot_fast | **27.19** | **`div`** | **`div`** | — | **7.46** | — | ✅ |
| desk_fast | **46.57** | **`div`** | **56.60** | — | **4.74** | — | ✅ |
| sofa_fast | **29.00** | **`div`** | **80.16** | **`ni`** | **5.64** | — | ✅ |
| hdr_fast | **22.89** | **`div`** | **23.51** | — | **14.57** | — | ✅ |
| mountain_fast | **165.68** | **`div`** | **`div`** | **`ni`** | **20.29** | — | ✅ |

## Summary — plan inventory only (6 methods × 34 sequences = 204 cells)

- **25** cells we have run ourselves (12 %)
- **124** cells with a published SE(3) value but no run of ours (61 %)
- **55** cells with neither (27 %) — must be self-run or carry a reason code

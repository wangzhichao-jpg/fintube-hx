# Measured validation set v6

This directory supersedes `../measured/` (v5, six points) as the active acceptance set. All six v5 points are historical references only: W1/W2 have an unresolved duct bypass; E1/E2/C1/C2 were computed with the plain-fin correlation substituted for the louver fin. The CETIAT coil is restored here with the louver correlation.

## Rules
- Only measured facts, page/table locators, input-derivation records, tolerances declared before running and the results are published; source PDFs are linked, not included.
- Every input field is graded D0 (published) … D4 (typical value, reported as an interval). Compared quantities never enter a derivation; nothing is fitted and no multipliers are used.
- Results from Professional tube networks are labelled as such; their circuit inputs are not published. The Tan 2015 lumped inputs are rebuilt from the published measurements by `tools/run_measured_v6_tan.py` and reproduce with the open core.

## Results
**CETIAT reversible coil** (IEA HPT Annex 54 2021 report Ch. 4; ICR 2019, doi:10.18462/iir.icr.2019.1439). 3 rows × 32 tubes, 8 circuits, louver fins (2.5 mm pitch), smooth tubes; R410A and R32. File: `cetiat_iea_annex54.json`.
- Capacity (±5 %): 20/20 pass (+0.8 % … +2.7 %).
- Evaporator superheat (±3 K): 11/12 pass (R32-3: +3.3 K).
- Condenser subcooling (±2 K): 2/8 pass (others +2.3 … +3.0 K).
- Pressure drop: diagnostic only. The in-circuit pressure taps (Figs. 6b/7b, digitised) agree with the model; the extra part of the tabulated value sits at the circuit end and, for condensation, barely changes with flow, so it is not a fitting loss.
- Louver dimensions are not published (D4). Over Lh/Lp = 0.24–0.82 the effect is ≤0.5 % on capacity and ≤0.7 K on SC/SH. Transverse pitch and fin pitch exceed the Wang 1999 sample range by 0.4 %; a declared extension `correlation_range_tolerance = 0.005` is used. The six sub-zero evaporation points use the initial-frost limit (D4).

**Tan 2015 fan-coil units, wet** (South China Univ. of Technology thesis, Tables 2-2, 2-3, 3-2 … 3-11). 10 coils × 7 units, louver (lace-edge) fins. Files: `tan2015_fcu_measured.json`, `tan2015_fcu_results.json`.

| Model | Units | Mean ΔQw | Mean ΔSHR | Pass (Qw ±10 %, SHR ±0.05) |
|---|---|---|---|---|
| Lumped counterflow (open core) | 55 | +5.7 % | −0.040 | 36 robust + 2 conditional |
| Tube network (Professional, thesis circuits) | 62 | +3.9 % | −0.028 | 58 |

The difference between the two models comes mainly from the two blind tubes in unit 03#. The remaining positive bias lies within the range produced by published expanded-tube contact conductances (3300–9800 W/m²K, sensitivity only). No default contact conductance is adopted.

**Kang et al. 1994 plain-fin air side** (J. Xi'an Jiaotong Univ. 28(1)). Independent j/f cross-reference, not a coil acceptance case. Seven of eight specimens agree within −22 % … +17 % in the common velocity range. File: `kh1994_airside_crosscheck.json`.

## Out-of-range extrapolation references (not acceptance)
Both data sets are good measurements, but their geometry lies outside the sample range of every published plain-fin correlation, so the software refuses to compute them. The results were obtained in a research script with the range check removed, using the same Wang-Chi 2000 expressions, only to show how far an extrapolation would be from measurement.

- **Batista 2022** (ATE 212:118528), wide-pitch water coil: Pt 60 mm, Pt/Pl 2.0, Dc 16.3 mm. The largest Pt in the plain-fin database is 40 mm.
  - Capacity error +4 % … +10 %. This looks small only because the air-side effectiveness is high, so Q is insensitive to UA.
  - Compared with the authors' U, the model's UA is +21 % … +72 % too high, and the air pressure drop is about 2×.
  - File: `batista2022_extrapolation_reference.json`.
- **Joppolo 2015** (CSTE 6:136, open access), R134a condensers A/B, three conditions each: 11 rows × 6 tubes, single circuit. Rows exceed Wang's 1–6.
  - The measured values were read from Fig. 7; the readings reproduce the deviation ranges stated in the paper's text.
  - Capacity error +1.7 % … +9.2 %. Refrigerant pressure drop: all 12 repeats within ±30 %.
  - Outlet subcooling implied by the measured capacity is about 0–2 K, against 3–6 K in the model. This has the same sign as the CETIAT condenser points. **Condenser subcooling may be over-predicted by 2–5 K**; this is published as a known issue.
  - File: `joppolo2015_extrapolation_reference.json`.

## Not yet included
- ARTI/NIST 2002 evaporator: the fins are a wavy/slit hybrid (report p. 46) with no applicable correlation.
- Micro-fin coil data: none found yet. The micro-fin correlations are implementation-verified only.

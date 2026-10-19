# Measured validation set: six published operating points (v5, historical)

> **Superseded by [`../measured-v6/`](../measured-v6/README.md).** All six points here are historical references: W1/W2 have an unresolved duct bypass; the CETIAT points were computed with a plain-fin substitute and are restored in v6 with the louver correlation.

[ **English** | [简体中文](README.zh-CN.md) ]

This folder documents every published measurement that Fintube HX has been compared with, where each number comes from, how the inputs were mapped, and how far the comparison can be trusted. **Nothing is fitted to these data**: no heat-transfer or friction multiplier, no correlation coefficient and no input was adjusted to reproduce a measured capacity.

- `cases.json` — sources (citation, DOI/URL, page/table/figure locators, SHA-256 of the retrieved PDF), boundary data, measured values, mapping assumptions and every recorded result.
- `inputs/` — Community-runnable inputs for the two water-coil points (lumped geometry model).
- `../../tools/run_measured_validation.py` — re-runs the Community points and prints the comparison; `tests/test_measured_validation.py` keeps them reproducible.

The four refrigerant points need an actual tube-circuit model, which is part of Fintube HX Pro and **not** of this repository. Their Pro results are recorded here only for transparency. The source PDFs are not redistributed; use the links below.

## 1. Sources

| ID | Source | Used for |
|---|---|---|
| Altwieb 2022 | Altwieb M., Mishra R., Aliyu A.M., Kubiak K.J. *Heat Transfer Enhancement by Perforated and Louvred Fin Heat Exchangers.* Energies 2022, 15(2), 400. [doi:10.3390/en15020400](https://doi.org/10.3390/en15020400) (CC BY 4.0) | W1, W2: geometry (Section 2.1.2, Fig. 2b), test matrix (Table 1), measured mean capacity Q_avg = (Q_water + Q_air)/2 (Fig. 5a/5e; text p10: plain fin 523 W at Va = 4 m/s), ±5 % uncertainty |
| Altwieb 2018 | Altwieb M.O. *Modelling and Optimisation of Heat Exchanger Integrated in Fan Coil Unit.* PhD thesis, University of Huddersfield, 2018. [eprints.hud.ac.uk/id/eprint/34544](https://eprints.hud.ac.uk/id/eprint/34544/) | Supporting facts for W1/W2 only: 165 × 175 mm test section (p39), 25 mm return bends and 21 fins (p41, Fig. 3.9), Va is the mean over the gross duct section (p60), diagnostics (Fig. 4.4, 4.11, 4.12) |
| CETIAT / IEA HPT Annex 54 | IEA HPT Annex 54 *2021 Progress Annual Report*, Chapter 4 (CETIAT), [PDF](https://heatpumpingtechnologies.org/content/uploads/sites/63/2022/05/iea-annext-54-2021-annual-report-v3-040422.pdf); study first presented by Pardo, Gaillard, Mondot, ICR 2019, [doi:10.18462/iir.icr.2019.1439](https://doi.org/10.18462/iir.icr.2019.1439) | E1, E2, C1, C2: coil (Fig. 2: 3 rows × 32 tubes, 8 circuits, louvre fins 2.5 mm), instrumentation (Fig. 4), conditions (Tables 2–3), measured capacity, SH/SC and pressure drop (Tables 4–5), air/refrigerant heat balance 0.4–2.5 % (dry evaporation) and 0.5–2.1 % (condensation) |

Six operating points, **two specimens**: W1/W2 are one plain-fin water coil; E1/E2/C1/C2 are one reversible R410A coil tested as evaporator (counter-current) and condenser (co-current).

## 2. Measured points and results

Error = (calculated − measured) / measured. "v4" = mapping reviewed on 2026-10-13; "v5" = v4 plus only source-documented items (Section 4). Pro = Fintube HX Pro 0.6.6.dev1 tube network; Community = this repository, lumped counterflow model (water only).

| Case | Point | Measured | v4 Pro | v5 Pro | v5 Community | Outlet state (v5 Pro vs measured) |
|---|---|---:|---:|---:|---:|---|
| W1 | Altwieb Test 1.3: 0.12 m³/h, 60 °C water, 24 °C air, Va 2.183 m/s | Q_avg 333.5 W | −18.0 % | **−7.6 %** | −7.3 % | — |
| W2 | Altwieb Test 5.5: 0.36 m³/h, Va 3.991 m/s | Q_avg 523.1 W | −25.6 % | **−15.8 %** | −15.8 % | — |
| E1 | CETIAT R410A evaporation Run 1, 230 kg/h | 12.20 kW | −0.4 % | −0.3 % | n/a | SH 15.2 K vs 16.6 K (−1.4 K) |
| E2 | Run 2, 270 kg/h | 14.30 kW | −1.6 % | −1.5 % | n/a | SH 13.3 K vs 17.6 K (−4.3 K) |
| C1 | CETIAT R410A condensation Run 1, 230 kg/h | 13.31 kW | −6.0 % | −6.1 % | n/a | SC 0.2 K vs 6.2 K (−6.0 K) |
| C2 | Run 2, 270 kg/h | 15.29 kW | −7.2 % | −7.2 % | n/a | SC 0.0 K vs 6.6 K (−6.6 K) |

Refrigerant pressure drop (v5 Pro, tubes + return bends only) vs measured P4↔Outlet P: E1 −31 %, E2 −42 %, C1 −83 %, C2 −78 %. The measured span also contains the collector/outlet piping (and, in condensation, a flow-independent 18 kPa), which the model does not include; these differences are reported but not used for acceptance.

## 3. What each comparison can discriminate

For the refrigerant points the mass flow and inlet state are measured inputs, so the capacity is largely fixed by the boundary data. Any model that completes the phase change must land inside this window, whatever its air-side accuracy:

| Case | Capacity window (complete phase change … outlet at air inlet temperature) | Discriminating quantity |
|---|---|---|
| E1 | −8.8 % … +1.3 % | superheat |
| E2 | −8.9 % … +1.9 % | superheat |
| C1 | −6.3 % … +8.6 % | subcooling |
| C2 | −6.7 % … +10.1 % | subcooling |

The small E1/E2 capacity errors are therefore **not** evidence of air-side accuracy. The condenser capacity errors are almost entirely the missing subcooling (the calculated outlet is at the saturated-liquid edge of the window).

## 4. Acceptance assessment (v5)

Criteria used here: capacity within max(10 %, 2 × stated measurement uncertainty) and only where the window is wider than that; superheat/subcooling within ±2 K; pressure drop only where measured and modelled spans match.

| Case | Verdict | Main reason |
|---|---|---|
| W1 | **Consistent** (−7.6 %), boundary-incomplete reference | Core air velocity not reported (see 5) |
| W2 | **Not met** (−15.8 %) — open | Same coil, higher water and air flow; see 5 |
| E1 | **Consistent** (SH −1.4 K; capacity non-discriminating) | Louvre fins modelled as plain fins |
| E2 | **Not met** (SH −4.3 K) | Louvre fins modelled as plain fins |
| C1 | **Not met** (SC −6.0 K) | Louvre fins modelled as plain fins; co-current subcooling region |
| C2 | **Not met** (SC −6.6 K) | as C1 |

Two of six points meet these criteria. This is a comparison at six points on two specimens, not a product accuracy certification.

**CETIAT what-if (not a result):** the coil has louvre fins, but no louvre geometry is published, so the plain-fin Wang–Chi correlation is used. Multiplying every cell UA by 1.3 — an illustrative louvre-type enhancement, not fitted — moves SH to 17.9/18.7 K (measured 16.6/17.6 K) and SC to 7.4 K (measured 6.2/6.6 K) with capacities within +1.4 %. The measured outlet states lie between the plain-fin and the enhanced case, which points to the fin-type substitution as the dominant cause. A louvre-fin correlation needs the louvre pitch/height from the original ICR 2019 paper or the manufacturer.

## 5. Water coil (W1/W2) diagnosis

Facts from the sources:

1. **Air flow basis.** Va is the arithmetic mean over the gross 165 × 175 mm duct section (thesis p60). The finned face (84.3 × 125 mm) is only 37 % of it, and the core/bypass split is not reported. Combining the paper's Q_avg with the thesis effectiveness (Fig. 4.4, ε = 0.132/0.108) gives a C_min flow area of 0.0270/0.0282 m² against 0.0289 m² for the duct, i.e. the authors' air flow is the **duct** flow. Both v4 and v5 set the core face velocity equal to Va; this is the largest unresolved boundary assumption.
2. **Unfinned surface in the air stream.** Each tube is 99.3 mm straight with 84.3 mm finned, and the ten tubes are joined by nine 25 mm return bends inside the duct (paper Fig. 2b; thesis p41). v5 adds this 0.015 m² bare surface with the Churchill–Bernstein cylinder correlation at Va: +26 W (W1), +37 W (W2).
3. **Counted fins.** 21 fins at 4.23 mm pitch span 84.6 mm (20 pitches). The previous model used L/pitch = 19.9 fins. v5 uses `geometry.fin_count = 21`; the hydraulic diameter in the Wang correlation stays periodic so that counting an end fin does not alter j/f.
4. **Water bends.** v5 adds a Crane TP-410 close return bend (L/D = 50) per bend. At 3 L/min this gives 4.61 kPa against the thesis' 5.24–5.40 kPa (Fig. 4.11); straight tubes alone gave 0.79 kPa. This is an independent check of the bend term (capacity is unaffected).

Remaining gap and its limits:

- The calculated/measured ratio is nearly constant over 0.7–4.0 m/s (0.86–0.90 at 2 L/min, 0.81–0.85 at 6 L/min against thesis Fig. 4.4), so the velocity trend is reproduced; the offset grows with water flow.
- The two publications of the same coil differ by about 7 % at Test 1.3 (thesis-derived 357 W vs paper 333.5 W).
- The Wang–Chi (2000) plain-fin j correlation itself represents 88.6 % of its database within ±15 %.
- Sensitivities (v5): exposed-tube velocity ±30 % → ±1.2 %; bend radius 8 mm → −2 %; core velocity ×0.8/×1.2 → −16 %/−0.3 % (W1) and −23 %/−9 % (W2).
- The measured air pressure drop (thesis Fig. 4.12: 3.7 Pa at 2.18 m/s, 5.4 Pa at 3.99 m/s) is about one third of the finned-core friction at core velocity = Va (11.7/35 Pa). That indicates bypass, i.e. a core velocity **below** Va, which would lower the prediction further. Capacity and air-side pressure drop of this data set cannot both be matched by any single core-flow assumption; individual Q_water and Q_air are not published.

Conclusion: W1 is consistent; W2 stays open. The water-coil points are kept as boundary-incomplete references, not as acceptance cases for capacity accuracy. A water coil measured in a sealed duct with Q_water and Q_air reported separately is needed for a quantitative water-coil acceptance.

## 6. Reproduce

```bash
python tools/run_measured_validation.py
pytest -q tests/test_measured_validation.py
```

Community: W1/W2 lumped counterflow with `geometry.fin_count` and `model.exposed_tubes` (both added in 0.1.0.dev7). Pro tube-network inputs are not published here.

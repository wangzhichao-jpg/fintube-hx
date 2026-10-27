# Fintube HX Community

[ **English** | [简体中文](README.zh-CN.md) ]

[![CI](https://github.com/wangzhichao-jpg/fintube-hx/actions/workflows/ci.yml/badge.svg)](https://github.com/wangzhichao-jpg/fintube-hx/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12–3.14](https://img.shields.io/badge/Python-3.12–3.14-brightgreen.svg)](pyproject.toml)
[![YouTube](https://img.shields.io/badge/YouTube-Overview_Video-FF0000?logo=youtube&logoColor=white)](https://youtu.be/anapOEsmAU0)
[![Bilibili](https://img.shields.io/badge/Bilibili-中文宣传片-00A1D6?logo=bilibili&logoColor=white)](https://www.bilibili.com/video/BV1Y1JC6FEs9/)

**An open, reproducible Python core for baseline fin-tube heat-exchanger thermal-hydraulic calculations (MIT Licensed).**  
Supports forward rating, bounded inverse mass-flow solving, parametric scans, and CSV/Excel exports for **water coils, evaporators, and condensers**.  
Repositories: [GitHub](https://github.com/wangzhichao-jpg/fintube-hx) · [Gitee Mirror](https://gitee.com/bigtaurus/fintube-hx) | Video Overview: [YouTube (EN)](https://youtu.be/anapOEsmAU0) · [Bilibili (中文)](https://www.bilibili.com/video/BV1Y1JC6FEs9/)

![Fintube HX 3D Staggered Coil & Thermal-Hydraulic Digital Twin](docs/coil-3d-showcase.png)

## Ecosystem & Scope Overview

Fintube HX follows a three-tier architecture where Community and Pro share the same thermophysical and baseline solver core (regression-tested and reviewed in three external rounds):

| Edition | Target Audience | Key Capabilities & Scope |
|---|---|---|
| **Community (This Repo, MIT)** | Academic research, algorithm benchmarking & scripted workflows | Lumped/segmented baseline solvers, Wang & Chi (2000) plain-fin water geometry, Hausen/Gnielinski tube-side HTC, bounded inverse flow targets, CLI & JSON/CSV/XLSX I/O |
| **Pro Engineering Workbench** | HVAC&R coil design & rating engineers | Engineering unit forms, P-h/P-x state helpers, **interactive tube-by-tube circuit routing & parallel pressure balancing**, two-phase boiling/condensation correlations, multi-condition screening, Word/Excel reports |
| **Enterprise & Lab Validation** | OEMs & coil manufacturers | Physical test-rig calibration, custom fin/tube correlations, and bespoke software by the **Jianke Environment and Energy Technology Co., Ltd. (National Air-Conditioning Equipment Quality Inspection Center)** team, backed by the **State Key Laboratory of Building Safety and Built Environment** |

## Implemented models

| Coil | Heat-transfer model | Geometry / pressure loss |
|---|---|---|
| Pure-water coil | **Lumped counterflow ε-NTU**; dry sensible exchange or wet-contact approximation | Input UA, or continuous plain-fin / staggered smooth-tube UA. Optional **dry air-core friction** and **water straight-tube friction** outputs |
| Evaporator | Constant-pressure P-h **counterflow axial segmentation**, uniform allocation of supplied UA | **Input UA only**; no refrigerant geometry-derived HTC or pressure loss |
| Condenser | Same input-UA P-h model, with finite enthalpy/temperature coupling in single-phase cells | **Input UA only**; no refrigerant pressure loss |

Water geometry uses Wang-Chi plain-fin j/f, Hausen/Gnielinski tube-side convection, Churchill friction and an equal-area annular-fin efficiency approximation. Wet geometry recomputes a **wet-fin efficiency proxy** from the enhanced air-side coefficient. It is not a resolved partially wet coil model. Version 0.1.0.dev8 adds an optional geometry-mode alternative, `model.wet_surface_model: "threlkeld_braun"`: Braun–Klein–Mitchell (1989) enthalpy-potential ε-NTU with the Threlkeld wet-fin efficiency (Lewis number 1, dry j applied to the wet surface, condensate-film resistance neglected); the coil is taken as the larger of the dry and fully wet heat rates. Omitting the field keeps the legacy contact approximation.

Version 0.1.0.dev9 adds two fin types to the water geometry: `geometry.fin_type: "louver"` (Wang, Lee, Chang & Lin 1999, IJHMT 42:1945; requires `louver_pitch_m`, `louver_height_m`) and `"wavy_herringbone"` (Wang, Hwang & Lin 2002, IJR 25:673; requires `wave_height_m`, `wave_projected_length_m`; fin faces use the developed area sec θ). Both are restricted to the published sample ranges and default to the Schmidt plate-fin efficiency used in the papers' data reduction (`geometry.fin_efficiency_method`, also selectable for plain fins). Both published j correlations are split at Re_Dc = 1000; for multi-row coils the two branches differ by up to tens of percent at that point (low-Re "level-off" in the data); the equations are used as published. Wet surfaces use the dry j/f. Version 0.1.0.dev10 adds `geometry.correlation_range_tolerance` (at most 0.01): an explicit, declared extension of the *geometric* sample bounds of the louver/wavy correlations (never Re or rows); every extended parameter is listed in the result and a "boundary extrapolation" warning is issued.

Version 0.1.0.dev7 adds two optional geometry items: `geometry.fin_count` (actual counted fins; changes area only, the Wang hydraulic diameter stays periodic) and `model.exposed_tubes` (unfinned straight tube ends and U-bends standing in the air stream; Churchill–Bernstein single-cylinder crossflow at a declared approach velocity, dry only, heat reported separately to a bypass stream).

Features: JSON input validation, isolated input/result snapshots, CLI single-case and batch execution, parameter scans, CSV/XLSX export, and bounded mass-flow targets for **water outlet temperature, refrigerant superheat or subcooling**. An outlet-air-temperature target is not implemented.

## Quick start

**Python 3.12, 3.13 or 3.14 (`>=3.12`)**; the pinned dependencies below are tested on all three. From PyPI: `pip install fintube-hx`. For development, select the interpreter explicitly rather than using the system default:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-development-lock.txt -e .
# Activate: source .venv/bin/activate (POSIX), .venv\Scripts\activate (Windows)
```

Alternatively, use `python3.12 -m venv .venv` (Windows: `py -3.12 -m venv .venv`), activate it and install with pip. If the mirror lacks a package, use official PyPI with TLS verification enabled.

```bash
fintube-hx capabilities
fintube-hx run examples/water_geometry.json --output output/result.json --xlsx output/result.xlsx
fintube-hx scan examples/water_dry.json --parameter air.volume_flow_m3_h --values "[800,1000,1200]" --output output/scan.json
pytest -q
```

```python
from fintube_hx.engine import run_case
from fintube_hx.storage import load_case
result = run_case(load_case("examples/water_geometry.json"))
print(result["heat_transfer_w"], result["fluid_out"]["temperature_c"])
```

## Input and output conventions

- Temperatures: °C; pressures: **absolute Pa**; dimensions: m; mass flow: kg/s; air volume flow: **actual inlet m³/h**; RH: 0–1.
- Provide either `fluid.inlet_t_c` or `fluid.inlet_h_j_kg`, not both. Two-phase inputs use **P-h**; the JSON contract has no inlet-quality field.
- `model.segments` controls refrigerant axial cells only. Water is lumped: the field may be omitted; legacy supplied values do not subdivide the coil and are reported as **not applied** in `numerical_controls`.
- Inverse flow bounds must bracket the desired root. Same-sign endpoints do not prove that an internal root is absent; the solver does not certify monotonicity or global uniqueness.
- Water pressure outputs are scoped **straight-tube/core friction**, not total installed-coil or system losses; return bends, headers and inlet/outlet fittings are not included. Under the default legacy scope the air side is dry core friction only; the optional `model.pressure_scope: "v1"` (0.1.0.dev16) adds the acceleration term and the wet-surface increment (see below). Every result lists what is included, excluded, extrapolated or degraded in `model_coverage`.

## Current engineering scope

By default the water wet/dry policy uses inlet water temperature and a contact approximation, not local wall temperature or partially wet area; the optional `wet_surface_model: "threlkeld_braun"` (dev8) evaluates the enthalpy-potential wet surface with wet-fin efficiency instead. Air properties are inlet-based; water properties use an iterated mean temperature. Wang uses the fin-collar diameter, not the bare-tube OD. For the equal-thickness collar convention this is Dc = OD + 2×fin thickness; actual formed collar dimensions are not independently specified in this baseline. The default fin count is L/fin pitch; `fin_count` supplies the actual count. The outer-edge geometry is idealized.

Louver and herringbone-wavy fins (dev9), micro-fin tube correlations (dev11, for extensions), optional contact conductance and inner fouling (dev13) and the clean-surface onset-of-frost limit (dev14, tube networks only) are available. There are no actual tube-route networks, row-by-row crossflow, intermediate split/merge junctions, brine properties, transient frost growth or tube-to-tube conduction through shared fins in this core. Evaporation at/below 0°C is rejected unless declared (`subzero_evaporation`). Correlation range checks reject extrapolation rather than silently clipping geometry.

**Known issue (measured):** condenser outlet subcooling tends to be over-predicted — by 2.3–3.0 K on the in-range CETIAT points and by 2.5–5 K on the out-of-range Joppolo 2015 condensers (capacity +1 … +9 %). The cause is not yet identified; nothing has been tuned to it (see `validation/measured-v6/`).

## Measured validation

Current set: [`validation/measured-v6/`](validation/measured-v6/README.md). It records sources with page/table locators, the D0–D4 grade of every input, the tolerances declared before running, and every result. Nothing is fitted and no multipliers are used.

| Data set | Points | Computed with | Capacity | Outlet state | Result |
|---|---:|---|---|---|---|
| CETIAT louver coil, condensation (IEA HPT Annex 54) | 8 | Pro tube network | +0.8 … +2.7 % | subcooling +1.0 … +3.0 K | capacity 8/8 within ±5 %; subcooling 2/8 within ±2 K |
| CETIAT louver coil, evaporation | 12 | Pro tube network | +0.8 … +1.8 % | superheat +0.9 … +3.3 K | capacity 12/12 within ±5 %; superheat 11/12 within ±3 K |
| Tan 2015 wet fan-coil units | 62 | Pro tube network (thesis circuits) | mean +3.9 % (−1.4 … +11.5 %) | SHR mean −0.028 | 58/62 within Qw ±10 % and SHR ±0.05 |
| Tan 2015 wet fan-coil units | 55 | **this repository** (lumped) | mean +5.7 % (+0.6 … +11.9 %) | SHR mean −0.040 | 36 robust + 2 conditional pass; 17 fail on SHR |
| Kang et al. 1994 plain-fin air side | 8 specimens | this repository | — | — | j/f cross-check: 7/8 within −22 … +17 % |
| Batista 2022, Joppolo 2015 | 9 + 6 | extrapolation only | — | — | outside every published correlation range; reference, not acceptance |

**Known issue:** condenser subcooling is over-predicted (by 2.3–3.0 K on CETIAT and 2.5–5 K on Joppolo).

The refrigerant points need a tube-circuit model, which is part of Fintube HX Pro and not of this repository; their Pro results are published for scrutiny.

**Why the lumped model and the tube network give different numbers.** The lumped model in this repository treats the whole coil as ideal counterflow and cannot represent blind (water-free) tubes. The Pro network follows the actual circuits row by row. On the 48 Tan units computed both ways the means are +5.3 % (lumped) and +4.6 % (network). Almost all of that gap comes from coil pre-03#, which has two blind tubes: the two models differ by 5.3 points there and by 0.04 points on average on the other coils. The headline means (+5.7 % and +3.9 %) also differ because the network additionally covers 14 units (post-03#/04#) that the lumped run does not include.

Reproduce the lumped results with `python tools/run_measured_v6_tan.py --check`. It is bit-for-bit on the recording platform; across CPUs and maths libraries the capacity deviation agrees within 1e-7.

The earlier v5 set ([`validation/measured/`](validation/measured/README.md), six points) is superseded. Its water-coil boundaries were incomplete because of a duct bypass, and its CETIAT points used a plain-fin substitute for the louver fin. Its table is kept there for traceability.

## Reproducible comparisons

[`references/python-hvac/`](references/python-hvac/README.md) contains a pinned source reproduction and a mapped water case. The mapped case produces **4363.49 W**, versus **4084.46 W** in the reproduced reference (+6.83%); this is a **software comparison with differing geometry/model definitions**, not a measured accuracy result or a fitted calibration.

Version **0.1.0.dev18** widens the supported Python range to 3.12–3.14 with the same pinned dependencies; no calculation changes (all 230 tests, including the bit-for-bit baselines, pass on 3.12, 3.13 and 3.14).

Version **0.1.0.dev16** (core API 2) adds, without changing any legacy result (bit-for-bit checked on 72 Community and 289 Professional cases):

- **`model.pressure_scope`**: absent or `"legacy_v0"` keeps the previous outputs; `"v1"` reports `air_pressure_drop_breakdown_pa` (core friction, entrance/exit, acceleration, wet increment) and `air_pressure_drop_total_pa`. Checked against the originals, the Wang 1999/2000/2002 friction factors were reduced **with** the entrance/exit losses included, so these are reported as `included_in_f` and not added again; the acceleration term (1+σ²)(ρ1/ρ2−1) that those reductions subtract is added. `v1` requires `geometry.fin_surface` (`"bare_aluminum"` or `"hydrophilic"`, no "unknown").
- **Wet-surface air friction** for non-hydrophilic plain fins: Wang, Lin & Lee 2000 (IJHMT 43:1869, Eqs. 11–15; 31 uncoated samples, Re 300–5000, Fp 1.19–3.2 mm). Hydrophilic coatings, louver and herringbone fins, or values outside the sample range report the wet increment as `not_computed` with the reason; capacity is unaffected.
- **Declared extrapolations**: `geometry.fin_pitch_extrapolation: true` for plain fins 8.7–12 mm (only the pitch and the Dh it implies are extended), and `geometry.row_extrapolation: "saturate_at_row_6"` with the per-row API `air_side_factors_by_row` for 7–12-row tube networks (rows 1–6 use the 6-row average, rows 7+ the row-6 local value 6·j(6)−5·j(5)). The lumped models here still reject more than 6 rows. All extrapolated results are flagged and are not validation evidence.
- **Structured Chinese errors** `fintube_hx.errors.ModelRangeError` (a `ValueError`) with field, allowed range, source and suggested fallbacks; planned-but-unsupported items (slit fins, Dc < 6.9 mm, inline banks, flat tubes, mixtures that CoolProp does not provide such as R454B) say so explicitly.

Version **0.1.0.dev18** adds an optional, declared extrapolation of the wet-friction correlation's fin pitch (plain bare-aluminium fins, 3.2–4.0 mm; flagged as extrapolated, never silent) and removes a private product name from a docstring; results without the new key are unchanged.

Version **0.1.0.dev17** adds exact (bit-identical) shortcuts for the humid-air states used inside the root solvers, about 1.2–1.9× faster tube networks in the Professional edition with unchanged results, an optional `solver.time_limit_s`, and a lower bound j6 ≥ 0.5·j(6) for declared row extrapolation (the difference formula is ill-conditioned at low Re and is refused rather than silently distorted).

Version **0.1.0.dev14** adds `subzero_evaporation: "initial_frost"` support in the wet-surface element (clean-surface onset of frosting: deposit as ice with its fusion enthalpy, piecewise saturation curve at 0 °C; no frost thickness, frost resistance or blockage). The lumped contact-factor refrigerant model rejects it; it is intended for strict wet-surface tube networks. Version **0.1.0.dev13** adds optional `geometry.contact_conductance_w_m2_k` (fin-collar/tube contact conductance on the tube outer area π·Do·L) and `geometry.inner_fouling_resistance_m2_k_w`, both constant series resistances with no default value; nothing changes when they are absent. Version **0.1.0.dev12** adds the optional `model.subzero_evaporation: "dry_only"` for evaporators: surfaces at or below 0 °C are accepted only while they stay at or above the local air frost point (CoolProp humid-air saturation is over ice below 0 °C), i.e. without deposition; otherwise the case is rejected because a frost model would be required. The refrigerant temperature represents the surface in this check, which is conservative. The default (`reject`) is unchanged. Version **0.1.0.dev11** adds `geometry.tube_type: "microfin"` with module `fintube_hx.microfin`: TN 2224 micro-fin geometry (Kedzierski & Lin 2023, NIST), their convective-boiling Nusselt correlation with the mixture glide factor, and the NISTIR 6333 two-phase pressure drop (Choi, Kedzierski & Domanski 1999). Geometric parameters outside the TN 2224 database raise. In this core the lumped water model rejects micro-fin tubes explicitly; the correlations are available to extensions (the Professional evaporator network uses them). They are implementation-verified against the published example and geometry, not yet validated against measured coils. Version **0.1.0.dev10** adds the declared `correlation_range_tolerance`; without it nothing changes. Version **0.1.0.dev9** adds louver and herringbone-wavy fins and the Schmidt fin efficiency (module `fintube_hx.airside`); plain-fin cases without `fin_efficiency_method` are bit-for-bit unchanged. Version **0.1.0.dev8** adds the optional `wet_surface_model` (module `fintube_hx.wet_surface`); without it all existing results are bit-for-bit unchanged. Version **0.1.0.dev7** adds `fin_count`, `exposed_tubes` and the measured-validation set; without these fields all existing results are bit-for-bit unchanged.

For lumped refrigerant models, an omitted `solver.max_iterations` defaults to `max(200, 2*segments + 20)`. An explicit limit is never increased; a low budget is disclosed and an unconverged run still exits with code 2. Version **0.1.0.dev6** adds this budget correction; it does not change heat-transfer equations.

The status of every review item (fixed / clarified / open) is tracked in [docs/EXTERNAL_REVIEW_STATUS.md](docs/EXTERNAL_REVIEW_STATUS.md). The [v3 follow-up](docs/EXTERNAL_REVIEW_V3.md) records the controlled wet-branch diagnostic and corrected current-version status. The [external review response](docs/EXTERNAL_REVIEW_2026-10-13.md) records confirmed issues, corrections and reasons for disputed claims. Version **0.1.0.dev5** corrects fin blockage in the diagonal minimum-flow gap and the misleading inverse-bracket error message; existing transverse-gap reference capacities are unchanged.

## Author and citation

Project lead: [Zhichao Wang](https://github.com/wangzhichao-jpg) (ORCID [0000-0001-6662-835X](https://orcid.org/0000-0001-6662-835X)).
If you use this software in a paper or an engineering report, please cite it as described in [CITATION.cff](CITATION.cff) (the **Cite this repository** button on GitHub exports BibTeX/APA). If it is useful to you, a star on GitHub or [Gitee](https://gitee.com/bigtaurus/fintube-hx) helps other engineers find it. Questions, bug reports and public data: [Issues](https://github.com/wangzhichao-jpg/fintube-hx/issues).

Cooperation and enquiries: [wangzhichao@chinaibee.com](mailto:wangzhichao@chinaibee.com)

## License

Original code: [MIT](LICENSE). Dependencies and adapted python-hvac expressions have separate licences and attribution; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [CORE_API.md](CORE_API.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

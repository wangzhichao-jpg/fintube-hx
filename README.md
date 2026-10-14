# Fintube HX Community

[ **English** | [简体中文](README.zh-CN.md) ]

[![CI](https://github.com/wangzhichao-jpg/fintube-hx/actions/workflows/ci.yml/badge.svg)](https://github.com/wangzhichao-jpg/fintube-hx/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-brightgreen.svg)](pyproject.toml)

A standalone Python core for baseline fin-tube heat-exchanger calculations.
[GitHub](https://github.com/wangzhichao-jpg/fintube-hx) · [Gitee](https://gitee.com/bigtaurus/fintube-hx)

## Implemented models

| Coil | Heat-transfer model | Geometry / pressure loss |
|---|---|---|
| Pure-water coil | **Lumped counterflow ε-NTU**; dry sensible exchange or wet-contact approximation | Input UA, or continuous plain-fin / staggered smooth-tube UA. Optional **dry air-core friction** and **water straight-tube friction** outputs |
| Evaporator | Constant-pressure P-h **counterflow axial segmentation**, uniform allocation of supplied UA | **Input UA only**; no refrigerant geometry-derived HTC or pressure loss |
| Condenser | Same input-UA P-h model, with finite enthalpy/temperature coupling in single-phase cells | **Input UA only**; no refrigerant pressure loss |

Water geometry uses Wang-Chi plain-fin j/f, Hausen/Gnielinski tube-side convection, Churchill friction and an equal-area annular-fin efficiency approximation. Wet geometry recomputes a **wet-fin efficiency proxy** from the enhanced air-side coefficient. It is not a resolved partially wet coil model.

Features: JSON input validation, isolated input/result snapshots, CLI single-case and batch execution, parameter scans, CSV/XLSX export, and bounded mass-flow targets for **water outlet temperature, refrigerant superheat or subcooling**. An outlet-air-temperature target is not implemented.

## Quick start

**Python 3.12 is required (`>=3.12,<3.13`). Python 3.13 is not supported by this pinned environment.** Select the interpreter explicitly rather than using the system default:

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
- Water pressure outputs are scoped **straight-tube/core friction**, not total installed-coil or system losses. Return bends, headers, inlet/outlet contraction/expansion and wet-film losses are not included.

## Current engineering scope

The water wet/dry policy uses inlet water temperature and a contact approximation, not local wall temperature or partially wet area. Air properties are inlet-based; water properties use an iterated mean temperature. Wang uses the fin-collar diameter, not the bare-tube OD. For the equal-thickness collar convention this is Dc = OD + 2×fin thickness; actual formed collar dimensions are not independently specified in this baseline. Equivalent fin count is L/fin pitch. The outer-edge geometry is idealized.

There are no actual tube-route networks, row-by-row crossflow, intermediate split/merge junctions, brine properties, louver/wavy fins, enhanced tubes, fouling/contact resistances, or frost model. Evaporation at/below 0°C is rejected. Correlation range checks reject extrapolation rather than silently clipping geometry.

## Reproducible comparisons

[`references/python-hvac/`](references/python-hvac/README.md) contains a pinned source reproduction and a mapped water case. The mapped case produces **4363.49 W**, versus **4084.46 W** in the reproduced reference (+6.83%); this is a **software comparison with differing geometry/model definitions**, not a measured accuracy result or a fitted calibration.

For lumped refrigerant models, an omitted `solver.max_iterations` defaults to `max(200, 2*segments + 20)`. An explicit limit is never increased; a low budget is disclosed and an unconverged run still exits with code 2. Version **0.1.0.dev6** adds this budget correction; it does not change heat-transfer equations.

The [v3 follow-up](docs/EXTERNAL_REVIEW_V3.md) records the controlled wet-branch diagnostic and corrected current-version status. The [external review response](docs/EXTERNAL_REVIEW_2026-10-13.md) records confirmed issues, corrections and reasons for disputed claims. Version **0.1.0.dev5** corrects fin blockage in the diagonal minimum-flow gap and the misleading inverse-bracket error message; existing transverse-gap reference capacities are unchanged.

## License

Original code: [MIT](LICENSE). Dependencies and adapted python-hvac expressions have separate licences and attribution; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [CORE_API.md](CORE_API.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

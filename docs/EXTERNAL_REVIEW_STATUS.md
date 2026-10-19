# External review: status of every Community item (0.1.0.dev14)

Three independent review rounds were received on 2026-10-13 (round 1 on dev4, round 2 on dev5, round 3 on the developer replies). Detailed replies: [round 1](EXTERNAL_REVIEW_2026-10-13.md), [round 3 follow-up](EXTERNAL_REVIEW_V3.md). This table records the state of each item raised against the public core; items that concern only the Professional application are not listed.

Status: **fixed** = code changed and covered by tests; **clarified** = the claim was withdrawn/corrected by the reviewer or is not a defect; **open** = a real capability gap, stated in the README and results, not yet implemented.

| # | Item | Status | Where |
|---|---|---|---|
| 1 | Diagonal minimum free-flow gap used the transverse fin-blockage term | fixed (dev5) | `geometry.py`, `tests/test_external_review.py` |
| 2 | Inverse solver reported "unreachable" for same-sign endpoints | fixed (dev5): "not bracketed", uniqueness not certified | `inverse.py` |
| 3 | `model.segments` silently ignored for water | fixed (dev5): `numerical_controls` discloses not applied | `water.py` |
| 4 | Python 3.13 not supported, install commands ambiguous | fixed (dev5) | README |
| 5 | `egg-info` build artefact committed | fixed (dev5) | repository |
| 6 | Default iteration budget too small above ~140 refrigerant segments | fixed (dev6): `max(200, 2*segments+20)` when omitted; explicit limits kept | `schema.py`, `tests/test_iteration_budget.py` |
| 7 | Non-integer equivalent fin count L/pitch | fixed (dev7): optional `geometry.fin_count`; hydraulic diameter stays periodic | `geometry.py`, `tests/test_fin_count_exposed.py` |
| 8 | Collar diameter Dc = Do + 2tf | clarified: Wang correlations are defined on the collar diameter; formed collar dimensions are not a separate input | README |
| 9 | "12.5→16.5 °C jump", "wet fin efficiency not corrected", "Cr = 0 always overestimates", "segments required", `tolerance_k` unit | clarified / withdrawn by the reviewer | review replies |
| 10 | Water-side 3× pressure-drop "failure" vs python-hvac | clarified: the reference under-counts by 4 (Darcy/Fanning); this core's straight-tube value agrees with hand calculation | `references/python-hvac/` |
| 11 | Air-side +19 % vs python-hvac | clarified: reference uses bare-tube OD and a different free-flow area | review replies |
| 12 | Whole-coil wet/dry decision from inlet water temperature; no partially wet model (+12 % … +16 % in the mapped case) | **partly addressed (dev8)**: optional `model.wet_surface_model: threlkeld_braun` (enthalpy-potential ε-NTU, Threlkeld wet fin, larger-of-dry-and-wet). Default unchanged; still no resolved dry/wet boundary inside the coil, no wet-surface j, and no measured wet validation yet | `wet_surface.py`, `tests/test_wet_surface.py` |
| 13 | Wet contact-factor / equivalent-cp approximation, not a rigorous enthalpy-potential model | **addressed as an option (dev8)**: `model.wet_surface_model: threlkeld_braun`; default unchanged | `wet_surface.py`, `tests/test_wet_surface.py` |
| 14 | Evaporation at or below 0 °C rejected (no frost model) | **partly addressed (dev12)**: optional dry sub-zero surfaces above the air frost point; dev14 adds the initial-frost (onset) limit; transient frost growth still **open** | `thermal.py`, `tests/test_subzero_dry.py` |
| 15 | Water pressure drop: straight tubes only (no bends, headers, inlet/outlet) | **open** in this core (the Professional tube network now accepts a return-bend equivalent length) | README |
| 16 | Air pressure drop: core friction only (no Kc/Ke, acceleration, wet film) | **open** | README |
| 17 | Annular-fin efficiency proxy; no contact or fouling resistance | **partly addressed (dev9)**: optional Schmidt plate-fin efficiency (`geometry.fin_efficiency_method`); optional constant contact conductance and inner fouling resistance added in dev13 (no default values) | `airside.py`, `tests/test_airside_fin_types.py` |
| 18 | Inlet air properties, no wall-temperature correction | **open** | README |
| 19 | Lumped refrigerant models use an input UA, constant pressure | **open** by design of this core | README |
| 20 | Pure water only, counterflow lumped only, no louvre/wavy fins or enhanced tubes | **partly addressed (dev9)**: louver (Wang 1999) and herringbone wavy (Wang 2002) fins within published ranges; slit fins, solutions and crossflow lumped models still **open**; micro-fin tube correlations added in dev11 (evaporation, implementation-verified only) | `airside.py`, `tests/test_airside_fin_types.py` |
| 21 | Wang range checks reject extrapolation; transition-region interpolation; Hausen over whole path | by design, disclosed | README / warnings |
| 22 | Dense single-line code style | partly: new modules use one statement per line; no bulk reformatting mixed with physics changes | — |

Measured comparisons (six published points) and their acceptance status: [validation/measured](../validation/measured/README.md).

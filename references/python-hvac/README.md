# python-hvac whole-coil reference reproduction (software evidence, not measured)

Pinned MIT source: TomLXXVI/python-hvac commit `94247560a667905bfbf67e45a58965a58254fce8` (project version0.1.3). The three original calculation-cell sets were executed without changing inputs or upstream source. Plotting and unrelated room-system calculations are excluded. 419 source Git blobs are verified by source-tree.json; the separate reference environment is locked. CoolProp8.0.0, NumPy2.5.3 and SciPy1.18.1 match the Community baseline, so the property backend is NOT independent.

| Original notebook | Rerun heat W | Saved rounded heat W | Other rerun values |
|---|---:|---:|---|
| air_cooling_coil/air_cooling_coil_01.ipynb |4084.4590|4084|water11.10789℃, air15.91628℃, dry-air drop13.04820Pa|
| vapor_compression/ex02_air_evaporator.ipynb |5914.8564|5915|142.096339kg/h, air13.12371℃, air drop45.89729Pa|
| vapor_compression/ex03_air_condenser.ipynb |7634.4692|7635|subcool4.16327K, air44.93624℃, air drop39.54049Pa|

These are close reproductions, not bit-identical matches of the author's unrecorded environment. Condenser saved45.83℃/4.17K differs slightly from current45.83657℃/4.16327K, beyond strict last-digit rounding. Numerical solver/property/version tolerances and energy closure residuals are retained in JSON, not concealed. Reference refrigerant pressure-drop outputs are null: constant-pressure assumption is not a calculated0Pa.

## Reproduce independently

Download the official fixed-commit source archive (or a verified mirror of that exact tree), preserving MIT/LICENSE.md. Do not install the unrelated PyPI package named `hvac`.

Create a separate Python3.12 environment and install the local extracted python-hvac project with requirements-reference-lock.txt. For example with uv, using Tsinghua TLS index:

```
uv venv --python 3.12 .refenv
uv pip install --python .refenv/Scripts/python.exe --index-url https://pypi.tuna.tsinghua.edu.cn/simple -c requirements-reference-lock.txt -e PATH_TO_PINNED_PYTHON_HVAC
.refenv/Scripts/python.exe reproduce.py water --source PATH_TO_PINNED_PYTHON_HVAC --output water-rerun.json
.refenv/Scripts/python.exe reproduce.py evaporator --source PATH_TO_PINNED_PYTHON_HVAC --output evaporator-rerun.json
.refenv/Scripts/python.exe reproduce.py condenser --source PATH_TO_PINNED_PYTHON_HVAC --output condenser-rerun.json
```

`reproduce.py` is standalone and imports no private edition. It checks installed hvac origin and all419 Git blobs before running calculation cells. Use a new output filename for each run. Warning filters from the original notebooks remain unchanged (CoolPropWarning suppressed there).

## Community comparison: explicit scope

The reference uses continuous staggered-bank effective counts:
- water:20.2598425 tubes,7.0866142 effective first-row paths;
- evaporator:55.1377953 tubes,9.6062992 first-row paths;
- condenser:63.7480315 tubes,13.1496063 first-row paths.

Community's current geometry requires integer rows×tubes_per_row. Thus there is no exact lossless notebook→Community geometry conversion. We did NOT silently round the original reference or fit UA.

water-community-input.json explicitly maps water to3×7=21 tubes and7 circuits, changes face height180→177.8mm, keeps width/pitches/boundaries, assumes tube conductivity385W/(mK) and zero roughness. Community collarOD+2fin thickness differs from reference collarOD. Wet contact/fin/internal convection/pressure scopes also differ. Its geometry-derived capacity is4363.4854W, +6.8314% versus the original reference. That is a disclosed modified-geometry software comparison, NOT a6.8% measured accuracy claim or exact input parity. No input-UA override or fitted multiplier exists.

Community evaporator/condenser currently require explicit input UA and do not have independent geometric whole-coil refrigerant models. Therefore their original examples are reproduced as external references only, NOT labelled Community whole-coil agreement or superiority. Transferring reference-derived UA would be a parameter-handoff check, not independent validation; no such fitted comparison is used here.

Source URLs and exact inputs/outputs/dependencies are inwater.json/evaporator.json/condenser.json. Geometry assumptions and differences are inwater-community-comparison.json. MIT reference attribution is in../../THIRD_PARTY_NOTICES.md and ../../third_party_licenses/python-hvac/LICENSE.md. Original Community code licensing and remote publication remain pending.

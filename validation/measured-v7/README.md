# Measured validation set v7 (internal acceptance; public facts and results)

v7 re-judges all v6 datasets with requirement spec v1.2 F2-F4. Tolerances, classification order and status rule were
declared before running (2026-10-23T04:25:00Z) and not changed afterwards. Results were computed with Fintube HX
Professional 0.7.0.dev1 (v1 pressure scope) on shared core 0.1.0.dev17; the per-tube circuit inputs belong
to the Professional edition, so the Community core alone cannot reproduce them.

| Metric | Tolerance | Counted | Passed | Status |
|---|---|---|---|---|
| Heat transfer | +-5 % | 62 | 43 | below the 90 % line |
| Air dp dry / wet | +-15 % / +-20 % | 0 | - | no evidence |
| Refrigerant dp (same scope) | +-25 % | 0 | - | no evidence; no measured accuracy is claimed for this scope |
| SHR (auxiliary) | +-0.05 | 62 | 61 | met |

Extrapolated (CETIAT 0.4 % declared bounds, Joppolo 11 rows), refused (Batista; three Joppolo conditions) and
scope-mismatched points are listed separately in `v7_results_public.json` and never counted.

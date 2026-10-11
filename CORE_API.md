# Shared Core API 1 · 0.1.0.dev4

Community is an independent MIT development prerelease published to the approved GitHub/Gitee repositories. Professional now consumes this pinned package; it does not carry a second copy of baseline equations.

Canonical shared modules: properties, thermal, geometry, geometry_performance, wang_plain_fin, water/refrigerant lumped models, inverse, storage, units and common schema boundary/solver/mass-flow-target validation. Professional compatibility files re-export canonical functions, and its water/refrigerant adapters route engineering models privately.

Public model entry remains engine.run_case and rejects actual tube networks, air-column fields and engineering capacity targets. normalize_boundaries accepts explicitly declared extension fields for schema composition only; it is not a private-model simulator.

inverse.solve_mass_flow accepts an optional opaque continuation strategy with capture(case,result), seed.usable(case), evaluate(case,seed). Public code supplies no engineering seed or network solver. Final answers are cold-recomputed; biased or failed initial-state evaluations cannot publish an unchecked answer. Professional owns the actual NetworkSeed implementation.

Unit conversions explicitly name quantity/unit; gauge pressure needs a visible positive atmospheric absolute pressure. No default standard/outlet air-volume convention is inferred.

Professional records package/version/API as scalar provenance fields, preserving existing Excel/Word output contracts. Installation uses a local wheel with a SHA-256 lock; there is no sibling sys.path fallback or hidden import of the private package.

Original code is MIT licensed (see LICENSE); approved public targets are wangzhichao-jpg/fintube-hx on GitHub and bigtaurus/fintube-hx on Gitee. Publication must be checked, not inferred from target URLs. Basic Chinese GUI for Community, three unchanged python-hvac notebooks are now reproduced with independent scripts and locked reference data; exact Community refrigerant geometric comparison and release documentation remain later tasks.

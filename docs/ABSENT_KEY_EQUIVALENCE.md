# Same-platform absent-key equivalence: dev17 vs published dev19

This is a test/documentation addition after published commit `0fc5b2395bd3edec91c749e4633a3e98b922e749`.
It does not rebuild, replace or republish the dev19 wheel or sdist.

## Why a dual run

A whole-JSON digest from Linux was not portable to Windows. The subsequent relative `1e-8`
reference comparison was introduced without prior approval and is **not** the acceptance proof
that an absent declaration leaves results unchanged. It remains historical auxiliary coverage.
Cross-platform agreement and same-platform numerical invariance are different claims.

The primary proof uses original dev17 and published dev19 wheels, the same Python interpreter
and dependencies on each platform, and separate processes and working directories. No pytest
`pythonpath` is used. The runner verifies each imported core version and module location and
records dependency versions, module paths/hashes and source hashes.

- Original dev17 wheel SHA256: `66a182ef5a8316392f543bd7b873390cc9ec3bc59473c9aa7cb0b7b6547c026f`.
- GitHub/Gitee dev19 Release wheel SHA256: `c662942e60a713c44e8ab8be588971a7068afb0baff13cc8eb3187c4b6fd2e64`.
- Eight inputs: `water_geometry.json`, pressure scope v1, bare aluminium, fin pitch
  1.8 / 3.0 / 3.24 / 4.5 mm crossed with relative humidity 0.2 / 0.6, without
  `geometry.wet_friction_fin_pitch_extrapolation`. Exactly the same JSON is given to both versions.

## Reproduce

Extract each wheel into an independent `dev17/` or `dev19/` directory. Use a single pinned
dependency environment for both runs. Example commands (run in separate empty working directories
for each `run`, using absolute paths):

```text
python absent_key_dual_run.py fixtures --example water_geometry.json --out inputs.json
python absent_key_dual_run.py run --core-dir dev17 --version 0.1.0.dev17 --inputs inputs.json --out old.json
python absent_key_dual_run.py run --core-dir dev19 --version 0.1.0.dev19 --inputs inputs.json --out new.json
python absent_key_dual_run.py compare --old old.json --new new.json --out differences.json
```

The script is `tools/absent_key_dual_run.py`. It returns nonzero if import validation or the exact
comparison fails. Raw JSON includes inputs, outputs, dependency metadata and native Python type
records (including tuples before JSON conversion). Floats are compared with `float.hex()` including
signed zero, not a relative or absolute tolerance. Key sets, types, list lengths, all strings,
`warnings`, `model_coverage` and other result fields are compared.

Only these exact per-result provenance paths may differ:

1. `/provenance/version`: exactly `0.1.0.dev17` to `0.1.0.dev19`.
2. `/provenance/calculated_at_utc`: a timezone-aware ISO calculation timestamp on both sides.

Every allowed difference is recorded with its old and new value; no whole subtree is ignored.

## Recorded outcome (2026-10-30)

Linux CPython 3.12.3: eight cases, zero substantive differences, sixteen registered provenance
differences. Wine Windows CPython 3.12.7: the same result. Each platform's dependency metadata
matched exactly between its two processes. Raw evidence and reusable orchestration are kept in
the private execution record; real Windows testing remains to be repeated by the maintainer.

This proves only the specified absent-key cases; it is not a claim of broad measured model accuracy.

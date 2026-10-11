# Public/private porting record

## Approved edition boundary

User confirmed python-hvac as the reference and approved basic models public, actual tube networks and engineering enhancements private for the first release. Public original-code licence remains a publication decision; no remote publishing has occurred.

## What this candidate includes

The nine source files listed in initial-port-provenance.json were extracted from the independently developed basic models. Network routing/imports were removed from water.py and refrigerant.py. The Community schema, engine, CLI, baseline inverse and XLSX layer are public-only implementations. Baseline inverse retains bounded search, exact-flow memoization, nonconverged/nonfinite rejection and final cold verification, without network seeds.

Only nine synthetic/analytical baseline examples are included. tests/baseline-reference.json contains numerical regression outputs and explicitly states that these are historical software results, not measurements. No network examples, enterprise data, proprietary manuals, full releases or original host logs are included.

Adapted MIT plain-fin/minimum-area expressions retain their source notices. Other libraries retain their supplied licences. No restricted EGSim or unconfirmed ACHP implementation is copied.

## Still open

Professional now consumes this pinned shared core through tested adapters and compatibility imports under 软件研发/src/fintube_hx_pro. Duplicated baseline physical/geometry/property implementations were removed. Common boundary, solver and mass-flow-target contracts and the inverse engine are shared; engineering state seeds, tube marching, air-column models and capacity design remain private. See CORE_API.md. Professional consumes the installed wheel, with a version/API/SHA-256 lock, not a sibling source-path fallback.

Public API currently includes engine.run_case, engine.capabilities, schema.validate_case, scan.scan_case and native JSON/CSV/XLSX output. Inputs share schema version0.1 but the public validator is stricter and explicitly rejects inactive/unknown fields. The private validator must reconcile common-field rules during shared-core integration.

GUI forms, complete python-hvac example reproduction, licence approval, publication candidate audit and GitHub/Gitee repositories/releases are later milestones, not completed work.

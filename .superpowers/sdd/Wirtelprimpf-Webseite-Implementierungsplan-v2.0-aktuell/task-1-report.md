# Task 1 report — M00 canonical web plan and status registers

## RED

Command:

```sh
python3 -m unittest tests.test_web_plan -v
```

Expected and observed primary failure (exit 1):

```text
AssertionError: 2 != 0 : /usr/bin/python3: can't open file '/home/teladi/.local/share/wirtelprimpf-webplan-m00/scripts/validate_web_plan.py': [Errno 2] No such file or directory
```

Reason: validator did not yet exist. Fixture tests also reported absent canonical artifacts at this RED point.

## Added

- Byte-identical canonical v2 plan at `docs/plans/WIRTELPRIMPF-WEBSEITE-IMPLEMENTIERUNGSPLAN.md`.
- Deterministic JSON status register: 48 packages, 60 requirements, canonical digest/version and archive Factory pin.
- Deterministic JSON supersession register: authority order, old P00 PR #1 and generator PR #4 evidence.
- Stdlib-only fail-closed validator for artifacts, digests, matrix/register consistency, IDs, freezes/pin and supersession facts.
- Nine real subprocess tests, including temporary negative fixtures.

## Verification

| Command | Exit | Result |
|---|---:|---|
| `python3 -m unittest tests.test_web_plan -v` | 0 | 9 tests passed. |
| `python3 scripts/validate_web_plan.py --root .` | 0 | Canonical artifacts valid. |
| `make check` | 0 | Existing project checks passed; 1 pre-existing skip. |
| `cmp --silent <Vault-source> docs/plans/WIRTELPRIMPF-WEBSEITE-IMPLEMENTIERUNGSPLAN.md` | 0 | Byte-identical copy. |
| `git diff --check` | 0 | No whitespace errors. |
| `git show --check --stat HEAD` | 0 | Committed change clean. |
| `python3 -m py_compile scripts/validate_web_plan.py` | 0 | Validator compiles. |

## Commit

Implementation commit: `a5a42c1aef80261c6234d5be44dae12739d8315b` (`docs(web): add canonical v2 plan governance`).

## Self-review

Found one validator blind spot: checking a freeze SHA anywhere in plan allowed a shortened baseline-table SHA if another reference remained. Added a focused RED test, then changed validation to extract and compare exactly five baseline-table freeze SHAs. Re-ran all checks green.

## Concerns

None. Validator intentionally records frozen evidence only; it does not infer live GitHub state.

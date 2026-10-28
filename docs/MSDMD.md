# MSDMD in The Interdependency's OpenBao fork

GPT generated; context, prompt Erin Spencer.

This fork adds native-first metadata collection for examining OpenBao as a
replaceable secrets-vault component for A0. Existing Go declarations, comments,
module files, documentation and manifests are the owning sources. Supplemental
MSDMD blocks describe only the new integration's otherwise unexpressed contracts.

The source starts at upstream commit
`5486582884a420dbd5a42e37125b59f312db7552`. Reader implementation comes from the
exact `The-Interdependency/skill-lib` commit recorded in
[`msdmd-policy.json`](../metadata/msdmd-policy.json) and
[the vendored inventory](../metadata/msdmd-vendor.json). The
[work graph](../metadata/msdmd-work-graph.json) separates those authorities.
Upstream license and notices remain in place; this is a fork-specific change.

## Collect and inspect

From the repository root, install the pinned metadata readers into an isolated
environment. Python 3.11+ and Node are required; Go and a running vault are not.

```bash
python3 -m venv .msdmd-venv
.msdmd-venv/bin/python -m pip install -r .agents/skills/msdmd/requirements.txt
npm ci --ignore-scripts --prefix .agents/skills/msdmd
.msdmd-venv/bin/python scripts/msdmd_inventory.py --verify-pin
.msdmd-venv/bin/python scripts/msdmd_inventory.py --write
.msdmd-venv/bin/python scripts/msdmd_inventory.py --check
.msdmd-venv/bin/python -m unittest discover -s scripts/tests -p 'test_msdmd_inventory.py'
```

`--write` creates the full schema-2 root collection, `openbao_msdmd.ts`, and
updates [`msdmd-report.json`](../metadata/msdmd-report.json). The full collection
is generated locally and git-ignored because of its size. The tracked report
contains its canonical JSON digest, source identities, reader/runtime identities,
counts, all diagnostics, all conflicts, and every discovery/exclusion record.
It omits the large fact and edge arrays; those remain in the local collection.

Collection reads source bytes without compiling OpenBao, executing directives,
loading application plugins, resolving packages, contacting model providers,
or reading a deployed vault. It requires no provider or vault credentials.
Collection can take several minutes on this repository. The canonical defaults
allow 2 MiB per file and 256 MiB aggregate input; excluded scope stays visible.

## What the result establishes

`--check` verifies reproducibility against the tracked report. It does not mean
every convention was understood or that the vault works. The current report
retains partial/unsupported inputs and parser errors, including Go grammar gaps
around newer `new(value)` syntax. These are extraction findings, not compiler
verdicts. All required module identities must be extracted; missing parser
runtimes, unresolved required metadata, and identity conflicts block output.

Add `--strict` to reject every error diagnostic (exit 2), including retained
known source/parser limitations. A normal replay may succeed while
`strict_clean` remains false. A changed diagnostic or unsupported scope changes
the report and fails replay until deliberately reviewed and regenerated.
`verified_behavior` remains `not-evaluated`.

The report records exact Python, Node, reader and TypeScript versions. Changing
those versions may change the generator identity and require a reviewed refresh.
The [reader matrix](../.agents/skills/msdmd/references/implemented-readers.md)
defines the shipped subsets. No HCL, Handlebars or SCSS semantic reader is
claimed. Build selection, types, module resolution, checksums, vault security
and runtime tests remain **hmmm** outside this inventory's evidence.

## Maintain the fork

Change native owning sources first. Extend readers in canonical `skill-lib`,
test them there, commit, and propagate their exact source using its
`tools/propagate_skills.py`. Do not edit vendored reader copies independently.
Check propagation with canonical `tools/check_consumer_drift.py --require-vendored`.
Update the policy pin, per-file vendor hashes and work graph together, then
regenerate and replay this report. Review changes to unsupported scope and
diagnostics before accepting a refresh. Hashes detect drift; they are not signed
provenance or a security certification.

Keep upstream import paths intact so normal upstream synchronization remains
possible. Route upstream contributions according to upstream's contribution
policy; these AI-assisted metadata changes belong to this fork. Reverting this
adoption removes its metadata files and vendored skills without changing vault
data or OpenBao's runtime implementation. This iteration does not deploy a vault
or connect it to A0.

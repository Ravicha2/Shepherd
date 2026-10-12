# Plan: node/symbol-search response contracts (contract-details pass)

## Objective
Extract response-contract details from three families that converged on node/symbol-search
contracts, to design the `node_search` resolver tool (ADG / ADR 017 tool surface).

NOT a survey. Three families only:
1. LSP `workspace/symbol` (+ VS Code client behavior)
2. ctags / universal-ctags / tree-sitter tag browsers
3. SWE-agent (search/view tools) + Aider repo-map (tree-sitter + PageRank)

## Per-family extraction axes
A. Ranking rule for matched symbols (exact > prefix > substring? fuzzy scoring details)
B. Response cap + overflow shape (truncation, per-kind count grouping, "narrow your query"?)
C. Kind labeling of hits
D. External import targets indexed/searched?
E. Signatures in results + context-budget rationale

## Deliverable
- Canonical: `docs/node-search-response-contracts.md` (commit-ready, inline citations)
- Provenance sidecar: `docs/node-search-response-contracts.provenance.md`

## Ledger
- [x] Family 1 researcher (LSP + VS Code) -> /tmp/opencode/evidence/researcher_0_toolresults.md (+ findings)
- [x] Family 2 researcher (ctags + tree-sitter) -> /tmp/opencode/evidence/researcher_1_toolresults.md (+ findings)
- [x] Family 3 researcher (SWE-agent + Aider) -> /tmp/opencode/evidence/researcher_2_toolresults.md (+ findings)
- [x] Lead spot-verification of load-bearing claims (2026-09-10: LSP 3.18 relaxed-way text + 3.17->3.18 diff;
      VS Code MAX_RESULTS=512 + top() application; gopls symbolScope default "all"; aider binary-search block
      repomap.py:674-700 + line_number=False :729 + 100-char line clamp :782; SWE-agent caps 100/messages,
      WINDOW:100, MAX_RESPONSE_LEN=16000, no list_dir, find_file uncapped; ctags pattern-length-limit 96,
      Python import/reference-tag quotes, signature opt-in artifacts)
- [x] Synthesize contract doc + recommendation table -> docs/node-search-response-contracts.md
- [ ] Verify doc on disk; CHANGELOG entry (repo has no CHANGELOG.md; ledger note only)

## Outcome (2026-09-10)
- Delivered: docs/node-search-response-contracts.md (single canonical artifact; provenance inline in Sources).
- UNVERIFIED register in doc: VS Code "per-kind counts" overflow grouping not found; field.c line-level
  opt-in detail sourced from prior-run researcher notes only.
- Picks: server-side exact>prefix>substring + relaxed subsequence tier; cap + truncated + counts +
  "narrow your search"; explicit kind labels incl. external_import; external-IMPORTS indexing kept ours
  (labeled, never ADG-resolved); definition/signature line per hit, never bodies, under 16K ceiling.
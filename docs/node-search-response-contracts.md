# Node/Symbol-Search Response Contracts

- **Status:** research note (contract-details pass, not a survey) — deliverable for issue #141
- **Date:** 2026-09-10
- **Related:** ADR 017 (`docs/adr/017-search-first-resolution-tools.md`), issue #141, plan note `notes/node_search_lit_review_plan.md`
- **Evidence base:** /tmp/opencode/evidence/{researcher_0,researcher_1,researcher_2}_toolresults.md (fetched 2026-09-10); line refs below were computed against the raw files during the source-gathering run and are cited file:line per source
- **Scope:** response contracts of `node_search`-shaped tools only — ranking, caps/overflow, kind labels, external-import indexing, signatures. NOT a survey of agent tooling.

## Why this doc

ADR 017's `list_dependencies`/`list_dependents` are the current FQN-entry-point tools; issue #141 records a candidate replacement (`node_search`) that does FQN existence checks and enumeration by name instead of by edge kind. Three existing system families already converged on the same response contract, for the same reason we have: every observation competes for the same context budget. This doc steals their contract details and records the picks.

Three families, in their own terms:

1. **LSP `workspace/symbol`** (+ the VS Code client that re-scores it, + gopls as a concrete server)
2. **Tag indexes:** Universal-ctags / `readtags`, tree-sitter tag queries (+ vim's editor-side matching)
3. **Agent repo-map lineage:** SWE-agent's search/view ACI + Aider's repo map (tree-sitter + PageRank)

---

## Family 1 — LSP `workspace/symbol` (+ VS Code, gopls)

### A. Ranking rule

The spec deliberately does **not** mandate exact > prefix > substring server-side. The 3.18 spec added an explicit "relaxed way" rule — verbatim (`WorkspaceSymbolParams.query`, [LSP 3.18 spec, §workspace_symbol](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.18/specification/#workspace_symbol)):

> A query string to filter symbols by. Clients may send an empty string here to request all symbols.
>
> The `query`-parameter should be interpreted in a *relaxed way* as editors will apply their own highlighting and scoring on the results. A good rule of thumb is to match case-insensitive and to simply check that the characters of *query* appear in their order in a candidate symbol. Servers shouldn't use prefix, substring, or similar strict matching.

The "relaxed way" block (including "Servers shouldn't use prefix, substring, or similar strict matching") is new in 3.18 — the [3.17 spec](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#workspace_symbol) has only the empty-string sentence (fetched 3.17 §workspace_symbol; diff captured in evidence).

The **exact > prefix > substring gradient is realized client-side**, in VS Code's scorer thresholds (`src/vs/base/common/fuzzyScorer.ts`):

- `PATH_IDENTITY_SCORE = 1 << 18` (identity match on full path — highest)
- `LABEL_PREFIX_SCORE_THRESHOLD = 1 << 17` (prefix match on the label, plus `prefixLengthBoost` — "typing a file name wins over results that are present somewhere in the label")
- `LABEL_SCORE_THRESHOLD = 1 << 16` (fuzzy/substring match below)

...and the symbol picker sorts by fuzzy score desc, then name, then kind (`compareSymbols` in `src/vs/workbench/contrib/search/browser/quickaccess/symbolsQuickAccess.ts`). Server-side, gopls exposes the same tolerance as a setting: `symbolMatcher` = `CaseInsensitive | CaseSensitive | FastFuzzy | Fuzzy`, default `FastFuzzy` ([gopls settings](https://github.com/golang/tools/blob/master/gopls/doc/settings.md)).

**Reading:** LSP = relaxed server match + client-side scoring; the strict tiers are a *client* implementation detail, not a protocol contract.

### B. Cap + overflow

- **VS Code mixed quick-open** (`src/vs/workbench/contrib/search/browser/quickaccess/anythingQuickAccess.ts`): `private static readonly MAX_RESULTS = 512;`, applied as `top([...filePicks, ...symbolPicks], compareItemsByFuzzyScore, MAX_RESULTS)` in `getAdditionalPicks` and as `maxResults: AnythingQuickAccessProvider.MAX_RESULTS` on the file search — the merged, score-sorted list is truncated to 512. No overflow-grouping UI found in the fetched sources.
- **Symbol picker** (`symbolsQuickAccess.ts`): no cap in current code; the repo's git history for the file shows no cap ever existed (source-gathering run checked the full history). All provider results are returned and sorted client-side.
- **Per-kind counts on overflow:** **UNVERIFIED** — targeted searches for overflow-grouping strings in the VS Code sources fetched found nothing. The issue #141 phrasing "VS Code groups overflow into per-kind counts" could not be confirmed from the evidence; the verified overflow shape is the 512 merged-pick truncation above.
- **Spec:** no response cap defined. Generic-query case is in the spec itself: *empty query = request all symbols* (both 3.17 and 3.18 text). LSP leaves bounding to the server; the client re-ranks.

### C. Kind labeling

Explicit. `SymbolInformation`/`WorkspaceSymbol` carry a required `kind: SymbolKind` enum value plus `containerName`; the `workspace.symbol.symbolKind.valueSet` capability negotiates the supported set ("If this property is not present the client only supports the symbol kinds from `File` to `Array`" — 3.17 spec). VS Code maps kinds to icons (`SymbolKinds.toIcon`) and treats `Class, Enum, File, Interface, Namespace, Package, Module` as "global" symbols (`TREAT_AS_GLOBAL_SYMBOL_TYPES`, symbolsQuickAccess.ts).

### D. External IMPORTS targets

The spec says nothing about dependencies. One documented server precedent extends scope beyond the workspace: **gopls `symbolScope`** ([gopls settings](https://github.com/golang/tools/blob/master/gopls/doc/settings.md)) — *'When the scope is "workspace", gopls searches only workspace packages. When the scope is "all", gopls searches all loaded packages, including dependencies and the standard library.'* **Default: `"all"`.** This is a Go build-model index over *loaded dependency packages* (source available in the module cache), not an index of import-statement targets; symbols in un-loaded/unavailable dependencies are not returned.

No LSP-family system indexes external **import-statement targets** as first-class index entries.

### E. Signatures in results

**No.** `SymbolInformation` = `name, kind, location, containerName` — no signature field; signature content lives in a separate `textDocument/signatureHelp` request, not in symbol search results.

---

## Family 2 — ctags / tree-sitter tag indexes

Universal-ctags 6.2.0 docs; tree-sitter tag model; vim's editor behavior.

### A. Ranking rule

`readtags` NAME action matches are exact by default, with explicit opt-in modes — no automatic tiering, no fuzzy:

- default: exact match, **binary search on sorted tags files** ("The NAME action will perform binary search on sorted (including "foldcase") tags files, which is much faster then on unsorted tags files" — [readtags(1)](https://docs.ctags.io/en/latest/man/readtags.1.html))
- `-p` → prefix match (`readtags -p - mymethod`)
- `-Q '(substr? (downcase $name) "my")'` → substring filter (scheme expression)
- `-i` → case-insensitive

The editor adds ranking *over* the tag file: vim's `tag-priority` orders full matches above ignore-case matches, with static/global and current-file/other-file as secondary axes (8 tiers, `FSC` first) — [vim tags doc, `*tag-priority*`](https://vimhelp.org/tags.txt.html). So the family's rule is: **exact, then ignore-case; prefix and substring are separate modes the client chooses**, and scope/locality is a ranking axis too.

### B. Cap + overflow

**None in the tool.** `readtags -l` lists every tag; the NAME action lists every match; tag files for large repos are enormous (kernel-scale tags files were among the sizing anecdotes in the ctags FAQ captured during source-gathering). The only bounds are per-entry, not per-response:

- `--pattern-length-limit=<N>` — "Truncate patterns of tag entries after *N* characters. Disable by setting to 0 (**default is 96**)" — [ctags(1)](https://docs.ctags.io/en/latest/man/ctags.1.html)
- binary search keeps lookup cheap, so the format leans on client-side paging instead of caps

**This family is the negative precedent for caps.** Every modern consumer of tags files (vim, GitHub's code navigation) adds its own cap/paging; the index itself will happily dump everything.

### C. Kind labels

Explicit and first-class:

- `kind:` tagfield — "Kind of tag. The value depends on the language." For C: `c` class, `d` define, `e` enumerator, `f` function/method, `F` file, `g` enumeration, `m` member, `p` prototype, `s` structure, `t` typedef, `u` union, `v` variable ([tags(5)](https://docs.ctags.io/en/latest/man/tags.5.html)). The `kind:` *name* may be omitted (letter only) to save ~15% of file size. `--list-kinds-full` lists letter + long name + enabled per language.
- Reference tags carry `roles:` ("identifies the *how* of a referenced language object") on top of `kind` ("identifies the *what*") — e.g. Python `module` kind with `imported` role.
- tree-sitter tag queries use the `@definition.*` / `@reference.*` capture vocabulary (switched from the older `@kind.*` model in tree-sitter-python's July 2020 "Update to include new prefixes (#71)" commit; current vocabulary per [tree-sitter issue #2313](https://github.com/tree-sitter/tree-sitter/issues/2313)), with `@scope` for fully-qualified names — [github/code-navigation](https://github.com/github/code-navigation), [tree-sitter code navigation](https://tree-sitter.github.io/tree-sitter/4-code-navigation.html).
- Aider's internal `Tag` records (tree-sitter) carry only `kind ∈ {def, ref}` (`aider/repomap.py`, `get_tags_raw`: `name.definition.*` → `def`, `name.reference.*` → `ref`).

### D. External IMPORTS targets

**Not indexed by default; opt-in only.** Verbatim from the Python parser notes ([ctags-lang-python(7)](https://docs.ctags.io/en/latest/man/ctags-lang-python.7.html)):

> A tag for an imported module has `module` kind with `imported` role. **The module is not defined here; it is defined in another file.** So the tag for the imported module is a reference tag; specify `--extras=+r` (or `--extras=+{reference}`) option for tagging it. "roles:" field enabled with `--fields=+r` is for recording the module is "imported" to the tag file.

(from-imports get a `namespace` role instead). So ctags has the *mechanism* (reference tags) but it is two flags away from the default, deliberately — an import statement is a *use*, not a definition.

### E. Signatures in results

**Opt-in.** Tags carry an optional `signature:` extension field (parser-specific; documented for C-family and Python), and it is **not in the default output** — the canonical default record has none:

```
foo     kinds.c /^int foo() {$/;"       f       typeref:typename:int
```

(default record set, captured from ctags docs; cf. [ctags-client-tools(7)](https://docs.ctags.io/en/latest/man/ctags-client-tools.7.html) example `main input.c /^int main (void).../;" f typeref:typename:int`). With `--fields=+S` the field appears, e.g. `foo foo.cp 2;" f line:2 ... signature:(int a, int b, int c)` ([u-ctags issue #907](https://github.com/universal-ctags/ctags/issues/907)), and `readtags` formatters can print declarations from it (`-F '(list ... $signature ...)'`, [readtags(1)](https://docs.ctags.io/en/latest/man/readtags.1.html)). So: signatures exist in the *index format*, behind a flag; default search results are name-only.

---

## Family 3 — SWE-agent ACI + Aider repo map

### A. Ranking rule

**SWE-agent: none.** `search_file`/`search_dir` are literal `grep -n(H)`; `find_file` matches file names. No scoring, no fuzzy, no ranking; results come back in file/line order (`tools/search/bin/search_file`, `search_dir`, `find_file`).

**Aider: not query-based.** The repo map has no query at all — it ranks tags by **PageRank over a file/identifier graph** (`nx.pagerank(G, weight="weight", personalization=...)`, `aider/repomap.py:525`; edges `referencer → definer` weighted `use_mul * num_refs`, `:514`; files mentioned in chat get multiplier boosts, `:493-509`). Ranking = graph centrality, not lexical matching.

### B. Cap + overflow

**SWE-agent — refuse-don't-dump, with a narrowing instruction:**

- `search_file`: `if [ $num_lines -gt 100 ]; then echo "More than $num_lines lines matched for \"$search_term\" in $file. Please narrow your search."; return` (`tools/search/bin/search_file:42-43`)
- `search_dir`: same shape at 100 files (`tools/search/bin/search_dir:29-30`)
- **`find_file` has no cap** — prints every match (`tools/search/bin/find_file:19-27`)
- **Paper-vs-code discrepancy:** the paper (arXiv:2405.15793) says *"The search commands return at most 50 results for each search query; if a search exceeds this number, we do not report the results and instead suggest that the agent write a more specific query"* and the appendix calls it *"curbing the number of search results to 50 or fewer"*. Current `main` code caps at **100** (lines/files), and `find_file` is uncapped. Cite the code for the contract; cite the paper for the design intent.
- File viewer: bounded `WINDOW` window — `WINDOW: 100` (with `OVERLAP: 2`) in `config/sweagent_0_7/07.yaml:89-90`; `windowed_file.py:101` reads it from the registry; output framed as `[File: path (N lines total)]` + `(... more lines above/below)` (`windowed_file.py:164-174`); paper: *"The file viewer presents a window of at most 100 lines of the file at a time"* (30-line and full-file variants *hurt* in the ablation: 14.3% / 12.7% vs 18.0% at 100).
- Character ceiling on tool responses: `MAX_RESPONSE_LEN = 16000` with a clipping notice telling the agent to `grep -n` first (`tools/edit_anthropic/bin/str_replace_editor:27-28, 57-62`), and tree-sitter filemap elision (`.py` files > 16000 chars → `... eliding lines N-M ...`) instead of raw bodies.
- No `list_dir` in current `main` (verified by repo-tree search; the navigation commands are `find_file`/`search_file`/`search_dir`/`open`/`goto`/`scroll_*`).

**Aider — graceful budgeted degradation, never a dump:**

- Budget: `map_tokens=1024` default (`repomap.py:49`); with no files in chat, `max_map_tokens = min(map_tokens * map_mul_no_files(=8), max_context_window - 4096)` (`repomap.py:117-134`).
- Fit: **binary search over the ranked-tag prefix** — `repomap.py:674-700`: `middle = min(int(max_map_tokens // 25), num_tags)` (`:676`), `while lower_bound <= upper_bound:` (`:677`), render `ranked_tags[:middle]` via `to_tree` (`:693`), 15% tolerance `ok_err = 0.15` (`:690`). Low-ranked tags are dropped until the map fits — the map shrinks, never errors, never dumps the repo.
- Per-line clamp: `output = "\n".join([line[:100] for line in output.splitlines()])` (`repomap.py:782`) — rendered map lines are capped at 100 chars.
- Rendered map has **no line numbers** (`TreeContext(..., line_number=False)`, `repomap.py:729`); elision is shown with `⋮...` markers (see the map example in [aider's repo-map docs](https://aider.chat/docs/repomap.html)).

### C. Kind labels

**SWE-agent: none.** Output is raw `Line N:code` grep lines; there is no symbol model in the ACI.

**Aider: no explicit labels — the code line implies the kind.** The rendered map shows source lines like `│class Coder:` / `│    def create(`; no `kind:` label and no line numbers are attached. Internally the tag carries only `def`/`ref` (see A. above).

### D. External IMPORTS targets

**No.** SWE-agent greps repo files only (`find` even excludes dot-directories). Aider's tags come from tree-sitter captures over files *in the repo* (chat files + other files); reference backfill (pygments token names, `get_tags_raw`) also stays within repo files; `site-packages` is never scanned. Neither system builds index entries for external import targets.

### E. Signatures in results

**Aider: yes — definition/signature lines, never bodies.** The map *"includes the most important classes and functions along with their types and call signatures"* and shows *"the critical lines of code for each definition"* ([repomap docs](https://aider.chat/docs/repomap.html); [blog: aider.chat/2023/10/22/repomap.html](https://aider.chat/2023/10/22/repomap.html)). Context-budget rationale, verbatim: *"If it needs to see more code, the LLM can use the map to figure out which files it needs to look at."* The budget mechanics are the 1024-token default + binary-search tag-dropping above.

**SWE-agent: no signature extraction.** `search_file` shows matched lines (a match *on* a `def` line effectively shows a signature, by accident); bounded bodies only through the 100-line windowed viewer or the 16000-char edit-tool ceiling. The rationale is the same one we have: observations compete for context, so the interface suppresses verbose results (paper §5.1: iterative search that lets agents page through all matches *hurts* — 12.0% vs 15.7% no-search).

---

## Where families disagree → picks for `node_search`

| # | Disagreement | Precedents | Pick |
|---|---|---|---|
| 1 | Who ranks: server or client | LSP 3.18 pushes scoring to the client ("relaxed way", "Servers shouldn't use ... strict matching"); ctags modes are client-chosen (exact/prefix/substr); SWE-agent & Aider don't rank lexically | Server ranks. `node_search` returns pre-ranked hits; agents can't be assumed to have a scorer. |
| 2 | Fuzzy tolerance | LSP 3.18: case-insensitive, query characters in order, no strict matching; VS Code: threshold jump prefix (1<<17) > fuzzy (1<<16) | Tiered: **exact > prefix > substring**, with an LSP-3.18-style **relaxed subsequence tier** (case-insensitive, ordered characters) as the last fallback so near-miss queries still resolve to the right node. |
| 3 | Overflow shape | SWE-agent: refuse + "Please narrow your search"; VS Code: top-512 truncation; Aider: budgeted tag-dropping; ctags: unbounded | **Hard cap + `truncated: true` + hit counts + "narrow your search" guidance** (SWE-agent's refusal shape is the best agent UX because it converts failure into a cheap next query; Aider's graceful drop is the right *map/skeleton* mode). Never the repo dump — that is the ADR 017 `list_modules` failure mode (~400-500K tokens). |
| 4 | Kind labels | LSP `SymbolKind`, ctags `kind:` explicit; SWE-agent none; Aider implicit | **Explicit kind on every hit** (module/class/function/…). Two of four systems label explicitly and it costs nothing; SWE-agent's unlabeled grep is the contract that made agents burn turns opening files to learn what they found. |
| 5 | External IMPORTS targets | None indexed by default. ctags: opt-in reference tags (`--extras=+r --fields=+r`, roles `imported`); gopls: `symbolScope` default `"all"` covers *loaded dependency packages* (Go build model, source available) — nearest precedent, but package-graph-based, not import-statement targets | Keep external-IMPORTS indexing **ours**, as the issue expected — **but** record the two opt-in/opt-out precedents, and mitigate the anchor-bait risk by labeling external hits `kind: external_import` (no ADG node behind them) so constraints can't silently ground on them. |
| 6 | Signatures | LSP: no; ctags: opt-in field; SWE-agent: matched lines only; Aider: yes (definition lines, never bodies) | **Yes, minimally:** one definition/signature line per hit, never bodies, clamped per line (Aider's 100-char precedent) and fitted under the dispatch ceiling (`MAX_RESPONSE_LEN`-style 16K char backstop, SWE-agent precedent). |

## The generic-query case (bare `openlobby`)

The failure this contract must defuse: a query so generic that "matching" includes the whole repo (our eval repos make this concrete — a bare `openlobby` query substring-matches nearly every FQN in that repo). Precedents:

- LSP makes it a *feature*: "Clients may send an empty string here to request all symbols" — acceptable only because the client re-ranks and (in VS Code) truncates to 512.
- SWE-agent makes it a *refusal*: "More than N ... Please narrow your search."
- Aider makes it a *budget problem*: the PageRank prefix simply stops where the tokens run out.

**Pick for `node_search`: SWE-agent's shape.** Empty/near-empty or over-broad queries must not return "everything capped"; they return a bounded refusal with counts and a narrowing hint ("N nodes match; narrow by prefix or kind"). A cap is a floor, not an answer.

## Recommended `node_search` response contract

| Axis | Contract | Closest precedent |
|---|---|---|
| Ranking rule | exact > prefix > substring tiers, plus relaxed ordered-subsequence fallback (case-insensitive) | LSP 3.18 §workspace_symbol + VS Code scorer thresholds (1<<18/1<<17/1<<16) |
| Cap + overflow | hard cap (SWE-agent code uses 100 lines/files; its paper says 50; VS Code truncates to 512) → suggest `top_k` ≈ 10-50 with `truncated: true`, per-tier counts, and a "narrow your search" hint; empty/generic query → refusal + guidance, never the repo dump | SWE-agent `search_file:42-43` / `search_dir:29-30`; Aider budgeted drop; VS Code 512 |
| Kind labels | explicit `kind` per hit (module/class/function/external_import) | LSP `SymbolKind`; ctags `kind:` |
| External-import indexing | no precedent by default (ctags opt-in `--extras=+r`; gopls deps-by-default is a Go package-graph index) → ours; label `external_import`, never resolves to an ADG node | — |
| Signatures | one definition/signature line per hit, never bodies; ≤100 chars/line (Aider `repomap.py:782`); whole response under the 16K dispatch ceiling (SWE-agent `str_replace_editor:28`) | Aider map; SWE-agent 16K + WINDOW=100 viewer |
| Budget rationale | names + signatures, never bodies; budget-driven graceful shrinking, not failure | Aider `--map-tokens` default 1024 + binary-search drop (`repomap.py:674-700`); SWE-agent 100-line viewer ablation |

## Verification status

- Verified in this session against the evidence files: every quoted constant and behavior above (LSP 3.18 relaxed-way text incl. its 3.17→3.18 diff; VS Code `MAX_RESULTS = 512` and its `top()` application; gopls `symbolScope` text + default; ctags `--pattern-length-limit` 96, import/reference-tag quotes, kind field, default record shape, `signature:` artifacts; SWE-agent cap constants and messages, `WINDOW: 100`/`OVERLAP: 2`, `MAX_RESPONSE_LEN = 16000`, no `list_dir`, uncapped `find_file`; Aider `map_tokens=1024`, PageRank, binary-search block, `line_number=False`, 100-char line clamp, docs quotes).
- **UNVERIFIED:** VS Code "per-kind counts" overflow grouping — not found in any fetched VS Code source; recorded as unconfirmed. The `main/field.c` line-level claim (signature/`S` and `line`/`n` disabled by default) comes from the prior run's researcher notes, not re-verified here; the default-output claim it supports is independently confirmed by the default record examples above.
- Prior-run corrections incorporated (do not regress): Aider file is `aider/repomap.py`; rendered map has no line numbers; SWE-agent has no `list_dir` in current main; `find_file` has no cap.

## Sources

Primary (fetched & quoted):

- LSP 3.18 specification — workspace/symbol: <https://microsoft.github.io/language-server-protocol/specifications/lsp/3.18/specification/#workspace_symbol> (HTTP 200 verified; relaxed-way rule is a 3.18 addition over [3.17](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#workspace_symbol))
- VS Code `symbolsQuickAccess.ts`: <https://github.com/microsoft/vscode/blob/main/src/vs/workbench/contrib/search/browser/quickaccess/symbolsQuickAccess.ts>; `anythingQuickAccess.ts` (MAX_RESULTS=512): <https://github.com/microsoft/vscode/blob/main/src/vs/workbench/contrib/search/browser/quickaccess/anythingQuickAccess.ts>; `fuzzyScorer.ts`: <https://github.com/microsoft/vscode/blob/main/src/vs/base/common/fuzzyScorer.ts>
- gopls docs: <https://github.com/golang/tools/blob/master/gopls/doc/features/navigation.md> (workspace symbol section), <https://github.com/golang/tools/blob/master/gopls/doc/settings.md> (symbolScope/symbolMatcher/symbolStyle)
- Universal-ctags: [readtags(1)](https://docs.ctags.io/en/latest/man/readtags.1.html), [ctags(1)](https://docs.ctags.io/en/latest/man/ctags.1.html), [tags(5)](https://docs.ctags.io/en/latest/man/tags.5.html), [ctags-lang-python(7)](https://docs.ctags.io/en/latest/man/ctags-lang-python.7.html), [ctags-client-tools(7)](https://docs.ctags.io/en/latest/man/ctags-client-tools.7.html), [field.c](https://github.com/universal-ctags/ctags/blob/master/main/field.c), [issue #907](https://github.com/universal-ctags/ctags/issues/907)
- tree-sitter code navigation: <https://tree-sitter.github.io/tree-sitter/4-code-navigation.html>, <https://github.com/github/code-navigation>, tree-sitter-python tags.scm `@definition.*`/`@reference.*` (2020-07 "Update to include new prefixes (#71)"), [issue #2313](https://github.com/tree-sitter/tree-sitter/issues/2313)
- SWE-agent: paper "SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering", arXiv:[2405.15793](https://arxiv.org/abs/2405.15793) (v3; NeurIPS 2024, <https://proceedings.neurips.cc/paper_files/paper/2024/file/5a7c947568c1b1328ccc5230172e1e7c-Paper-Conference.pdf>); code: [tools/search/bin/search_file](https://github.com/SWE-agent/SWE-agent/blob/main/tools/search/bin/search_file), [tools/search/bin/search_dir](https://github.com/SWE-agent/SWE-agent/blob/main/tools/search/bin/search_dir), [tools/search/bin/find_file](https://github.com/SWE-agent/SWE-agent/blob/main/tools/search/bin/find_file), [config/sweagent_0_7/07.yaml](https://github.com/SWE-agent/SWE-agent/blob/main/config/sweagent_0_7/07.yaml) (WINDOW: 100), [tools/windowed/lib/windowed_file.py](https://github.com/SWE-agent/SWE-agent/blob/main/tools/windowed/lib/windowed_file.py), [tools/edit_anthropic/bin/str_replace_editor](https://github.com/SWE-agent/SWE-agent/blob/main/tools/edit_anthropic/bin/str_replace_editor) (MAX_RESPONSE_LEN=16000), [tools/filemap](https://github.com/SWE-agent/SWE-agent/blob/main/tools/filemap/config.yaml)
- Aider: [aider/repomap.py](https://github.com/Aider-AI/aider/blob/main/aider/repomap.py) (map_tokens=1024 :49; budget :117-134; PageRank :525; binary search :674-700; line_number=False :729; 100-char lines :782); docs: <https://aider.chat/docs/repomap.html>; blog: <https://aider.chat/2023/10/22/repomap.html>; ctags→tree-sitter switch note: <https://aider.chat/docs/ctags.html>
- vim `*tag-priority*`: <https://vimhelp.org/tags.txt.html>
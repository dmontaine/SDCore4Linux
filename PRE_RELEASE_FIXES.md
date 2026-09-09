# PRE-RELEASE FIXES

**The defect tracker for the final-testing phase.** Things that need deciding or
fixing before **L1.0-0** is released. Started 9 Sep 2026.

***WHAT THIS FILE IS FOR, IN THE OWNER'S WORDS, 9 Sep 2026:*** in SD Core for
Windows it *"was created late in the project, so when the original plan was done
and we started final testing, we could track and fix the errors that the testing
revealed."* **That is its job here too: the place testing's findings go.**

***SO IT HAS BEEN STARTED EARLY, AND THAT IS DELIBERATE RATHER THAN A
MISREADING OF THE PORT.*** This project is at **step 4 of 10** and final testing
has not begun; the port created its copy at the equivalent of step 10. Started
now for two reasons: the owner asked for it on 9 Sep, and the entries below
already exist — they are **structural gaps that testing will never reveal**,
because no test finds a decision nobody made (entries 1, 2, 7) or a plan that is
silent on a subject (entries 1, 2, 5). Those are exactly the kind that go stale
in a handoff document and get lost.

***WHEN TESTING STARTS, THIS FILE'S CHARACTER CHANGES AND ITS RATE WILL DOMINATE
WHAT IS HERE NOW.*** The port reached 186 entries; nearly all of them came from
running the system, not from reading it. Expect the same, and do not read the
present low count as "the system is nearly clean" — it means testing has not
started.

**This file is maintained, not written once.** Add an entry when work or a test
turns something up; strike its number in the table when it is fixed, with the
date and the commit.

***IT LISTS WHAT WE WOULD SHIP, NOT WHOSE FAULT IT IS.*** A defect this project
inherited from upstream `sdb64`, or one the Windows port also has, still belongs
here: being somebody else's bug has never been a reason to ship it.

**Why a separate file from [PROJECT_STATUS.md](PROJECT_STATUS.md).**
PROJECT_STATUS is a *position* — what is done, what is next, what was measured.
This is a *worklist of things that would embarrass the release*. An item can sit
here for weeks without being the next task, which is exactly what PROJECT_STATUS
must not contain.

`SEV` is a recommendation, not a ruling: **B** blocks the release, **S** should
be fixed, **M** minor.

***THE TABLE IS THE INDEX. THE SECTIONS UNDER IT ARE DETAIL.*** A struck number
is done; **read the table, never the section headings** — short entries have no
section at all, so counting `## N.` headings gives an answer that is wrong and
looks authoritative.

***NEXT FREE ID: 12.*** Take it from here and increment it; **do not derive it by
scanning.**

**Ported from SD Core for Windows**, whose `PRE_RELEASE_FIXES.md` is the model
and carries 186 entries. This one starts at 1 — the port's ids are its own and
the two files are not comparable by number.

| ID | SEV | What | Where |
|---|---|---|---|
| 1 | **B** | ***THE PLAN HAS NO ANSWER FOR THE PORT'S 157 POWERSHELL HELPERS, AND §L IS SCHEDULED WITHOUT THE VERIFIERS THAT PROVED IT THERE.*** 51 are on subjects §H already excludes as Windows-only. **21 are verifiers whose subject exists here too** — `verify-tiers`, `-tierapi`, `-tierchange`, `-catgate`, `-txn`, `-vocverbs`, `-fold`, `-lcnames`, `-nocase`, `-setpw`, `-createaccount`, `-delaccount`, `-upgrade` and 8 more — plus 10 neutral guards including `assert-current` and `cycle`. The plan mentions none of them: `verify-`, "the suite", "harness" and "verifier" return **two incidental hits in 1,600 lines**. See §1 | plan §H "Windows-only work"; `sd4windows/sdb_ai/sd64/gplbld/*.ps1` |
| 2 | **S** | ***THE PLAN DOES NOT MENTION THE `MICRO` VERB OR THE EDITOR STORY AT ALL*** — `grep -w -i MICRO` on the plan returns nothing. This tree ships `GPL.BP/MICRO`; the port **deleted it on 17 Aug 2026** and replaced it with `gpl.bp/EDIT`, one program reached by **two** verbs. Under the conformity stance this is unaddressed work, and §H's exclusion of *"editor bundling via winget"* rules out the Windows **mechanism**, not the feature. See §2 | `sdsys/GPL.BP/MICRO`; `sdsys/{VOC_TEMPLATE,NEWVOC}/MICRO`; plan §H:856 |
| 3 | **S** | **`EDIT` MEANS DIFFERENT THINGS IN THE TWO SYSTEMS, WHICH IS A NEAR-MISS NAME WAITING TO BITE.** Here `VOC_TEMPLATE/EDIT` → `$ED`, the **line** editor. In the port `voc_template/edit` → `$EDIT`, the **full-screen** editor. A user or an agent moving between the two gets a different program from the same word | `sdsys/VOC_TEMPLATE/EDIT` vs `sd4windows/.../voc_template/edit` |
| 4 | **M** | **`MICRO` shells out to a hard-coded `micro` with no check that it exists and no test of the result.** `Editor = "micro"` at line 37, `execute "!" : editor : …` at line 201, and nothing between. The port's UPSTREAM #16 records the consequence: it reports *"Record is unchanged"* when the editor is absent, which blames the user's data for a missing binary | `sdsys/GPL.BP/MICRO:37,201` |
| 5 | **S** | ***`bbcmp.py` UPPER-CASES EVERY `$include` NAME, SO A LOWER-CASE INCLUDE IS UNRESOLVABLE ON ext4.*** Found 9 Sep 2026 trying to compile `CPROC`: `$include define_install.h` fails because the file on disk is lower case. **This is a third name lookup that plan §M1 does not name** — §M1 lists the colon prompt/query language and BASIC `OPEN`, and stops there | `sdb_ai/sd64/gplbld/bbcmp.py:7141` |
| 6 | **B** | **Step 2 (`A1`–`A6`) is committed, compiled and NOT ONE ITEM EXERCISED.** Every item touches transactions or index structure; `A5`'s failure mode is a permanently damaged index and `A1`'s a half-applied commit, **both silent**. `A1` needs an *induced* commit failure to reach at all | PROJECT_STATUS "Step 2" ×3 sections |
| 7 | **B** | ***§M, THE LOWER-CASE CONVERSION, IS RELEASE-BLOCKING BY THE OWNER'S RULING OF 9 Sep 2026*** — *"as long as it is done by the end"*. Recorded here as well as in PROJECT_STATUS because the failure mode is silence: deferred once more each step until the port ships with `GPL.BP` and `SYSCOM` still upper case | plan §M; PROJECT_STATUS "Open" |
| 8 | **S** | **No `assert-current` equivalent.** Nothing refuses to run a check against an install older than its source, so a green result can come from the previous build. The port's is PowerShell, so this is a **rewrite, not a copy** — it is entry 1's most valuable single item | `sd4windows/sdb_ai/sd64/gplbld/assert-current.ps1` |
| 9 | **S** | ***`gplbld/check-stale-leads.py` CANNOT RUN HERE AT ALL, AND ADDING THIS FILE DOES NOT CHANGE THAT*** — measured 9 Sep 2026, not predicted. Copied verbatim and run, it exits **2 before any phase executes**: *"REFUSING - could not bound section 7"*. It is keyed to the port's PROJECT_STATUS structure — a section 7, `> ###` START HERE items, a `✅` task table — none of which exists here. **The unadapted copy was removed rather than committed**, because a tool that always exits 2 reads as a guard the project has. See §9 | `sd4windows/sdb_ai/sd64/gplbld/check-stale-leads.py` |
| 10 | **M** | **`sdsys/MESSAGES` lacks records `4100`, `4101`, `-10303`** (plan §D5). That is the runtime message file, not generated from `err.h`, so `gen_includes.py` does not touch it; adding the three is a deliberate data edit | `sdsys/MESSAGES/` |
| 11 | **M** | **`gplbld/check-msglen.py` hard-codes the bound 231 and will not say so if the constants move.** All four were verified against this tree when it was ported on 9 Sep, but nothing re-checks them; a change to `MAX_ERROR_LINES`, `MAX_EMSG_LEN`, the `"%08X: "` prefix or the D1 fix leaves a confident instrument answering from a stale premise | `sdb_ai/sd64/gplbld/check-msglen.py` |

---

## 1. The PowerShell helpers, and the verifiers §L will need

**The plan is silent, and this was measured rather than assumed.** `verify-`,
*"the suite"*, *"harness"*, *"regression"* and *"verifier"* together return two
incidental hits across the plan's ~1,600 lines — plan:246 (a `$CRED` *verifier*,
a different sense of the word) and plan:1402 (a reference to CLAUDE.md's
instrument rule). Neither is about porting the suite.

**§H's "Windows-only work" list is right about what it covers and does not reach
this.** Elevation and consent, Windows groups and ACL lockdowns, firewall rules,
OpenSSH, the service, profile reclamation, RDPACCOUNT — 51 of the 157 scripts
are on those subjects and are correctly excluded. The classification is by
script name and is mine, not the plan's.

***THE PROBLEM IS THE OTHER 31.*** 21 verifiers and 10 guards whose subjects are
this project's too:

| The port proved | With | The plan schedules it at |
|---|---|---|
| the three tiers | `verify-tiers`, `verify-tierapi`, `verify-tierchange` | §6 / §L — *"the largest block in the document and the one where half of it is worse than none of it"* |
| lower-case names | `verify-fold`, `verify-lcnames`, `verify-nocase` | §7 / §M |
| the upgrade path | `verify-upgrade`, `upgrade-voc`, `upgrade-dicts` | §5 / §F1 |
| the catalogue gates | `verify-catgate` | §1 / `B1`,`B2` — **already committed here, unexercised** |
| transactions | `verify-txn` | §2 / `A1`–`A6` — **entry 6** |

***THE DECISION IS NOT "PORT 31 SCRIPTS".*** It is what this project's
verification story is at all, and there are three shapes: reimplement the
relevant verifiers as shell or Python; build a smaller SD-BASIC harness that
runs inside `sd`; or accept manual check tables in PROJECT_STATUS and say so.
**The third is what is happening by default, and by default is the wrong way to
choose it** — steps 1 to 4 have accumulated an unexercised check table each,
which is the shape of a decision nobody made.

## 2. The editors

**What this tree has.** `GPL.BP/MICRO`, catalogued `$MICRO`, reached by
`MICRO` in both `VOC_TEMPLATE` and `NEWVOC`. `EDIT` and `ED` both point at
`$ED`, the line editor.

**What the port has.** No `MICRO` program — the owner ruled it out on 16 Aug
2026 (*"it launches an external editor"*, a containment concern) and it went on
17 Aug. In its place `gpl.bp/EDIT`, catalogued `$EDIT`, reached by **both**
`edit` and `micro`, selecting between **Microsoft Edit** and **micro**. Its
3 Sep 2026 changelog entry — *"the full-screen editors now come with SD,
installing no longer downloads them"* — is about bundling them in the installer.

**So the port's position is not "no external editors".** It removed one program
and shipped a better one, then bundled the editors it calls. Reading the 16 Aug
removal alone gives the opposite impression, and this entry exists partly to
stop that misreading.

***BOTH EDITORS ARE PRESENT ON THE DEVELOPMENT MACHINE*** — `/usr/bin/micro` and
`/usr/bin/edit`, checked 9 Sep 2026 — so on Linux the question is not
availability but whether SD ships them, depends on them, or degrades honestly
when they are absent (entry 4). §H excludes *"editor bundling via winget"*,
which is a **mechanism**; the packaging question here is `apt`/`dnf` and is not
the same question.

**What is undecided and needs the owner:** whether to adopt the port's `EDIT`
program and two-verb arrangement, or keep `MICRO` and fix entry 4, or drop the
full-screen editor entirely and let `ED` be the editor as §I3/§I5 already made
it for the removed screen editors.

## 9. Porting `check-stale-leads.py`

***THE ESTIMATE IN THIS ENTRY'S FIRST DRAFT WAS WRONG AND IS KEPT AS THE
CORRECTION.*** Reading the source suggested only phase 2 was coupled to the
port's documents, so adding this file plus a phase-2 fix would be enough.
**Running it says otherwise:** copied verbatim into `gplbld/` and run with no
arguments, it exits **2 immediately** —

```
REFUSING - could not bound section 7 (found %r..%r).  The headings
  may have been renamed; fix this rather than scanning everything.
```

— before phase 1. The entry-boundary machinery every phase depends on is built
from the port's own headings.

**The first column below is deliberately not a bare number.** `phase 1` rather
than `1`, because phase 4's index regex is `^\| *(~~)? *(\d+)`, and a detail
table whose rows start with a digit is counted as index rows — this table did
exactly that in draft and inflated the count from 11 to 15.

| | Reads | Here |
|---|---|---|
| bounds | "section 7" and the `> ### N.` START HERE items, to find where entries begin | ***refuses; neither exists*** |
| phase 1 | status words within one entry, `OPEN_PAT`/`CLOSE_PAT` | needs the boundaries above |
| phase 2 | the task table against the entries, both directions | its `ROW` regex wants `\| ✅ \| **N.Nx** \|`; **no such table here** |
| phase 3 | an entry that records something and then denies it | needs the boundaries above |
| phase 4 | this file's index rows, `^\| N \|` | **this file now satisfies it** |

***CREDIT WHERE IT IS DUE: EVERY ONE OF THOSE IS A REFUSAL, NOT A CLEAN RUN.***
Phase 2 refuses on zero rows (its line 438), phase 4 on zero index rows (663),
and the boundary step refuses rather than scanning the whole file. The port
built the null-case guards this project's CLAUDE.md asks for, which is why a
verbatim copy fails honestly instead of scoring green.

**So the work is an adaptation, not a copy**, and its scope is: decide what an
"entry" is in *this* PROJECT_STATUS, re-point the boundary detection at it,
either retire phase 2 or give this project the table it needs, and drive the
result against a fixture — the port ships `test-staleleads-units.py` precisely
so a dead scan cannot score clean.

**The fault it looks for is not hypothetical here.** On 9 Sep 2026
PROJECT_STATUS gained a step-4 note headed *"THE LOWER-CASE MIGRATION WAS NOT
FOLDED INTO STEP 4 … IS WITHDRAWN"* whose body said the opposite of what the
heading implied. **The owner caught it, not the tooling** — which is the
argument for doing this adaptation rather than shelving it.

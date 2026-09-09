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

***THE FIRST COLUMN IS THE ID AND ITS HEADER CELL IS DELIBERATELY EMPTY. DO NOT
"FIX" IT TO `| ID |`.*** The port's checker finds this table by matching
`^\|\s*\|\s*SEV\s*\|` (`test-fixlist-units.ps1:106`), so the empty cell is what
makes the table findable. **It said `| ID |` until 9 Sep 2026 and the checker
refused the whole file** — *"no index table found"*, exit 2. Changed on the
owner's ruling that day, for conformity with the port and to adopt the checker.

***NEXT FREE ID: 21.*** Take it from here and increment it; **do not derive it by
scanning.**

**Ported from SD Core for Windows**, whose `PRE_RELEASE_FIXES.md` is the model
and carries 186 entries. This one starts at 1 — the port's ids are its own and
the two files are not comparable by number.

| | SEV | What | Where |
|---|---|---|---|
| 20 | **B** | ***SD DOES NOT KNOW WHICH PERSON IS THE ADMINISTRATOR, AND THAT BLOCKS ENTRY 18's SECOND HALF.*** Measured 9 Sep 2026 by reading `CPROC`, and it **corrects entry 18's premise**. On `sudo sd`, `CPROC:279` sees uid 0, `CPROC:281` drops the effective uid with `!EUID_SET('sdsys')`, and ***`CPROC:285` REPLACES THE SESSION IDENTITY — `logname = kernel(K$USERNAME, 0)` makes `@logname` `sdsys`*** — before `$LOGIN` is called at `:291`. So by the time any gate could read the register, **the real person's name is gone**. The owner's *"is also a registered user of SD as an administrator"* has no person to look up, and `CPROC:2483`'s own `is_grp_member(@logname, …)` entry test is answered for `sdsys` rather than for whoever typed `sudo`. ***THIS ALSO NARROWS ENTRY 18's OTHER CLAIM***: the OS half is *effectively* enforced already, since reaching uid 0 by `sudo sd` requires sudoers membership — what is missing is the register half, not the sudoers half. **The port hit this and answered it with a SEPARATE concept**, `K$OS.ADMINISTRATOR` — *"is the SIGNED-IN PERSON an administrator"* as distinct from the session flag — keeping `@logname` the signed-in user. ***A RULING IS NEEDED BEFORE 18's GATES CAN BE WRITTEN***: whether SD preserves the real identity across the drop, and if so where. See §20 | `GPL.BP/CPROC:279-291`, `:2483`; entry 18 |
| 1 | **B** | ***THE PLAN HAS NO ANSWER FOR THE PORT'S 157 POWERSHELL HELPERS, AND §L IS SCHEDULED WITHOUT THE VERIFIERS THAT PROVED IT THERE.*** Classified 9 Sep from each script's own header: **113 testing, 38 admin, 6 build**. The testing half is 51 `verify-*`, **28 `test-*-units` that test the verifiers themselves**, 18 `probe-*` and 16 harness. Of the 38 admin, 19 are Windows mechanism with no counterpart here, **12 are the `secure-*` ACL family whose INTENT is §L's POSIX security posture**, and 7 have a direct Linux need the plan already schedules (`upgrade-voc`/`-dicts` §F1/F2, `check-install` §F7, `finish-install`, `clean-deadvoc`, `api-listener`, `restart-sd`). The plan mentions none of it: `verify-`, "the suite", "harness" and "verifier" return **two incidental hits in ~1,600 lines**. See §1 | plan §H "Windows-only work"; `sd4windows/sdb_ai/sd64/gplbld/*.ps1` |
| ~~2~~ | **S** | ***RULED AND IMPLEMENTED 9 Sep 2026.*** The plan did not mention the `MICRO` verb or the editors at all. **Owner's ruling:** *"for the linux version we just drop microsoft edit and maintain our practice of using whatever version of micro the distribution ships. The one thing we do want to retain from the windows version is the sdbasic syntax highlighting."* Done in `c8…` — `mkbasicsyntax.py` and `checksyntax.py` ported, `microcfg/syntax/sdbasic.yaml` generated from this tree's `BCOMP`, and `MICRO` now suffixes a BP working copy `.sdbasic` so detection fires. **Placement is entry 12.** See §2 | `sdb_ai/sd64/gplbld/mkbasicsyntax.py`, `microcfg/syntax/sdbasic.yaml`, `sdsys/GPL.BP/MICRO` |
| 3 | **S** | **`EDIT` MEANS DIFFERENT THINGS IN THE TWO SYSTEMS, WHICH IS A NEAR-MISS NAME WAITING TO BITE.** Here `VOC_TEMPLATE/EDIT` → `$ED`, the **line** editor. In the port `voc_template/edit` → `$EDIT`, the **full-screen** editor. A user or an agent moving between the two gets a different program from the same word | `sdsys/VOC_TEMPLATE/EDIT` vs `sd4windows/.../voc_template/edit` |
| 4 | **M** | **`MICRO` shells out to a hard-coded `micro` with no check that it exists and no test of the result.** `Editor = "micro"` at line 37, `execute "!" : editor : …` at line 201, and nothing between. The port's UPSTREAM #16 records the consequence: it reports *"Record is unchanged"* when the editor is absent, which blames the user's data for a missing binary | `sdsys/GPL.BP/MICRO:37,201` |
| 5 | **S** | ***`bbcmp.py` UPPER-CASES EVERY `$include` NAME, SO A LOWER-CASE INCLUDE IS UNRESOLVABLE ON ext4.*** Found 9 Sep 2026 trying to compile `CPROC`: `$include define_install.h` fails because the file on disk is lower case. **This is a third name lookup that plan §M1 does not name** — §M1 lists the colon prompt/query language and BASIC `OPEN`, and stops there | `sdb_ai/sd64/gplbld/bbcmp.py:7141` |
| 6 | **B** | **Step 2 (`A1`–`A6`) is committed, compiled and NOT ONE ITEM EXERCISED.** Every item touches transactions or index structure; `A5`'s failure mode is a permanently damaged index and `A1`'s a half-applied commit, **both silent**. `A1` needs an *induced* commit failure to reach at all | PROJECT_STATUS "Step 2" ×3 sections |
| 7 | **B** | ***§M, THE LOWER-CASE CONVERSION, IS RELEASE-BLOCKING BY THE OWNER'S RULING OF 9 Sep 2026*** — *"as long as it is done by the end"*. Recorded here as well as in PROJECT_STATUS because the failure mode is silence: deferred once more each step until the port ships with `GPL.BP` and `SYSCOM` still upper case | plan §M; PROJECT_STATUS "Open" |
| 8 | **S** | **No `assert-current` equivalent.** Nothing refuses to run a check against an install older than its source, so a green result can come from the previous build. The port's is PowerShell, so this is a **rewrite, not a copy** — it is entry 1's most valuable single item | `sd4windows/sdb_ai/sd64/gplbld/assert-current.ps1` |
| 9 | **S** | ***`gplbld/check-stale-leads.py` CANNOT RUN HERE AT ALL, AND ADDING THIS FILE DOES NOT CHANGE THAT*** — measured 9 Sep 2026, not predicted. Copied verbatim and run, it exits **2 before any phase executes**: *"REFUSING - could not bound section 7"*. It is keyed to the port's PROJECT_STATUS structure — a section 7, `> ###` START HERE items, a `✅` task table — none of which exists here. **The unadapted copy was removed rather than committed**, because a tool that always exits 2 reads as a guard the project has. See §9 | `sd4windows/sdb_ai/sd64/gplbld/check-stale-leads.py` |
| 10 | **M** | **`sdsys/MESSAGES` lacks records `4100`, `4101`, `-10303`** (plan §D5). That is the runtime message file, not generated from `err.h`, so `gen_includes.py` does not touch it; adding the three is a deliberate data edit | `sdsys/MESSAGES/` |
| 11 | **M** | **`gplbld/check-msglen.py` hard-codes the bound 231 and will not say so if the constants move.** All four were verified against this tree when it was ported on 9 Sep, but nothing re-checks them; a change to `MAX_ERROR_LINES`, `MAX_EMSG_LEN`, the `"%08X: "` prefix or the D1 fix leaves a confident instrument answering from a stale premise | `sdb_ai/sd64/gplbld/check-msglen.py` |
| ~~19~~ | **B** | ***DONE 9 Sep 2026 — MEASURED, THEN FIXED TO MATCH THE PORT.*** The C hole was real at **both** ends (`op_kernel.c:302-312`): any positive argument set `USR_ADMIN` without calling `IsAdmin()`, and the `\|\| IsAdmin()` made `kernel(26,0)` *re-grant* rather than clear whenever the caller ran as root, so `CPROC:2713`'s admin-drop on `LOGTO` did nothing for a root OS user. ***BUT THE READING "bypassable from any BASIC program" IS REFUTED:*** `KERNEL` is an `int.intrinsics` entry resolved only in internal mode (`BCOMP:3758`), and a non-internal probe (`kernel(26,1)`) compiled from the non-root `don` account **fails with "Unrecognised statement", 2 errors** — KERNEL is unreachable from ordinary BASIC. So the opcode can only be emitted by an `$internal` program (LOGIN, CPROC). **Fixed by gating the flag change on `HDR_INTERNAL`**, the port's exact fix (its entry 170 / 13 Aug 26). Build clean, 0 warnings; `bin/sd` boots. The `$internal`-path effect is reasoned + conformity, not witnessed (an ordinary user cannot compile `$internal`). Unblocks entry 18 | `gplsrc/op_kernel.c:302-312` |
| 18 | **B** | ***HALF BUILT 9 Sep 2026 (commit 1 of 2): THE REGISTER RECORDS A TIER, AND NOTHING READS IT YET.*** `SYSCOM/KEYS.H` gains `ACC$TIER` 5 / `ACC$PRIOR.TIER` 6; `CREATEA` takes `ADMINISTRATOR`/`PROGRAMMER` (token text, not `KW$`, so **no abbreviation**) and writes field 5, `STANDARD` being the default. **Field 4 is free in this tree — unlike the port — and is left free for conformity anyway.** ***Commit 2 is the gates, `sdadmin` membership and the ten call sites.*** Every account still gets the same VOC (§L1, undesigned). Compile check was **bounded**: `$internal`, so error classes were compared against HEAD and are identical, none on an added line. ***"ADMINISTRATOR" IN THE CATALOGUE GATES MEANS UID 0 — LITERAL root — AND §L'S ADMINISTRATOR TIER WILL NOT SATISFY IT.*** `CATALOG` (`:108`, `:202`) and `DELCAT` (`:119`) all gate on `system(27) # 0`, and `system(27)` is **`getuid()`** (`gplsrc/op_sys.c:222-223`). `sd` is not setuid, so a session runs as the invoking Unix user: **an SD ADMINISTRATOR who is not root is refused, and any ordinary user who is root is admitted.** The tier has no bearing on it. **Measured 9 Sep 2026 on the 11:35 install**, as uid 1000: `CATALOG BP $X`, `CATALOG GLOBAL BP X` and `DELETE.CATALOG $X` each refuse with sysmsg 2001, and a *local* `CATALOG BP X` does not — so the gate discriminates and works. **The defect is not the gate, it is what "administrator" is defined as.** ***OWNER'S DEFINITION, 9 Sep 2026, WHICH SETTLES IT:*** *"an administrator is a person who is a member of sudoers and is also a registered user of SD as an administrator. If they are not a registered user they should be refused entry."* And on the model: *"that is the current path in the windows version — you can be a windows administrator and still not have access to sd."* **Two conditions, ANDed, and neither is `getuid() == 0`.** See §18 for the measured gap | `GPL.BP/CATALOG:108,202`; `GPL.BP/DELCAT:119`; `gplsrc/op_sys.c:222` |
| 17 | **S** | ***THE SHIPPED BINARY TELLS THE USER IT IS VERSION 1.0-2, WHICH IS UPSTREAM'S NUMBER, NOT THIS PROJECT'S.*** Measured on the 11:35 install of 9 Sep 2026: `sd --version` answers *"String Database (sd) Version 1.0-2 64 Bit"* and every session banner says *"version 1.0-2 (AI modified)"*, while `sdsys/changelog` opens **`L1.0-0 - in progress`** and the project stance says release numbering follows SD Core for Windows rather than upstream. Source is `gplsrc/revstamp.h:43`, `#define SD_REV_STAMP "1.0-2"`. **`revstamp.h` also feeds `GPL.BP/REVSTAMP.H` through `gen_includes.py`**, so one edit carries to both — but the banner text and `MAJOR_REV`/`MINOR_REV` need checking with it. Plan §N | `gplsrc/revstamp.h:40-43`; `sdsys/changelog:1` |
| 16 | **S** | ***THE BUILD RUNS AS ROOT AND DOES NOT NEED TO*** — `installsdai.sh:359` is `sudo make -B`, so `gplobj/` and `terminfo/` inside the download come out owned by `root`. That is what made the 9 Sep install "fail" after it had succeeded: the ordinary-user `rm -fr` at the end could not remove them, returned 1, and `set -euo pipefail` aborted with no message. **Fixed by making the two cleanups `sudo rm -fr`, which treats the symptom.** The cause is that compiling needs no privilege at all — only *installing* does. Building as the calling user and `sudo`-ing just the copy into `/usr/local/sdsys` would remove a whole class of this | `installsdai.sh:359` |
| 15 | **S** | ***AN INSTALL NOW TESTS `origin/main`, NOT THE WORKING TREE — SO COMMIT AND PUSH BEFORE TESTING, OR YOU ARE TESTING SOMETHING ELSE.*** Owner's decision, 9 Sep 2026: the installer always clones `main` from GitHub. That **reverses plan §F9**, which removed the download precisely so an install would build the bundled `sdb_ai/` tree, and it reverses CLAUDE.md's *"builds from the `sdb_ai/` tree bundled in this repository, not from a clone."* The decision is the owner's and stands; **the consequence is that uncommitted work is invisible to an install and nothing detects that.** The port's answer to the same class of problem is `assert-current` (entry 8), which refuses to test a tree source has moved past. **Until something checks, the discipline is manual.** CLAUDE.md's project-constraint wording needs correcting to match | `installsdai.sh`; plan §F9; CLAUDE.md "Project constraints" |
| 14 | **B** | ***RULED 9 Sep 2026, AND THE MECHANISM IS BUILT — BUT IT IS NOT WIRED UP AND THE HANG IS NOT YET FIXED.*** `gplbld/sd-elevate` (one validated helper), `gplbld/sdcore.sudoers` (`%sdadmin` → that one command, **not** the eight raw ones), installer/uninstaller wiring with `visudo -cf` and an `includedir` check, and `test-sd-elevate.py` **30 passed / 0 failed — 24 refusals, 6 controls — with the test watched FAILING (6/24) against a permissive stub.** ***THE TEN CALL SITES STILL CALL RAW `sudo` AND `sdadmin` HAS NO MEMBERS***, so migrating them now would deny account creation outright: **the migration belongs with entry 18**, which is what puts anybody in the group. Unrun — nothing installed. Also found: `MODIFYA:131`'s `deluser` is **Debian-only** and cannot work on the Arch/RHEL branches. ***"ELEVATION DOES NOT APPLY HERE" IS WRONG — IT IS SPELLED `sudo`, AND IT IS ALREADY LOAD-BEARING IN THE SHIPPED BASIC.*** **8 `GPL.BP` programs shell out to `sudo`** from `OS.EXECUTE`: `useradd -m` (`CREATE_USER:64`), `passwd` (`SET_PASSWD:115`), `userdel`/`groupdel` (`DELACC:223,197`), `usermod -aG`/`groupadd`/`chmod g+s` (`CREATEA:331,634,306`), `usermod`/`deluser` (`MODIFYA:108,131`). ***AND NOTHING CONFIGURES sudoers*** — zero hits for `sudoers`/`NOPASSWD`/`visudo` across the installer, uninstaller and all of `GPL.BP`. So an SD ADMINISTRATOR's real privilege is whatever the machine's sudo rules already say, not what §L1 grants: with broad sudo they are root (`sudo passwd root`), without it account management silently fails or blocks on a password prompt inside an SD session. **The plan says `sudo` zero times in ~1,600 lines.** ***MEASURED 9 Sep 2026: THE HANG IS REAL*** — `sudo -n -v` as `don` answers *"a password is required"* (exit 1) and **0 of 10 call sites pass `-n`**, so `create.account` blocks on a password prompt inside the session. **And the membership test has three answers, not two**: `sudo -n -l` exits 1 both for "needs a password" and for "may not sudo", so a test on that exit code refuses a legitimate administrator. Three shapes and a recommendation in §14 — **the ruling gates entry 18** |  `GPL.BP/{CREATE_USER,SET_PASSWD,CREATEA,DELACC,MODIFYA}`; plan:17, §H:853, §L1, §L5:1164 |
| 13 | **B** | ***RULED 9 Sep 2026 — A STANDARD ACCOUNT DOES NOT GET A REAL LOGIN SHELL; THE TIER IS TO BE A BOUNDARY*** (owner's selection), ***WHICH COMMITS SD TO WRITING `sshd_config`*** — the port's fenced block + refusing preflight is the model. Mechanism (`ForceCommand` vs restricted shell vs `AllowGroups`) and PROGRAMMER's case are still open; see §13. **Not built.** ***ssh IS AN UNGUARDED WAY PAST THE TIER MODEL, AND THE INSTALLER TURNS IT ON.*** Every distro branch installs an ssh server (`installsdai.sh:254,272,285,295`) and the Arch branch starts and enables `sshd` (`:265-266`). SD users are **ordinary Unix users** — `CREATEA:331` does `usermod -aG sdusers` on an account that already exists, so it keeps its login shell. **Nothing in this project writes `AllowGroups` or `ForceCommand`** (grep: zero hits across the installer and `GPL.BP`). So a STANDARD account that §L1 denies `SH` and `!` **just ssh's in and gets a shell**, never touching SD. This is the exact failure the port measured on 21 Aug 2026 — *"a stock sshd_config: no AllowGroups and, worse, no ForceCommand, so an sdsshonly account got a PowerShell prompt"* — except here it is the **default state rather than a regression**. ***MEASURED 9 Sep 2026: every SD account has a real login shell*** (`don` `/bin/bash`, `sdsys` `/bin/sh`, none `nologin`), so §L1's verb withholding is **a convenience, not a boundary**. `sshd` is inactive on this box, which makes the exposure latent here but not absent. See §13 | `installsdai.sh:254-296`; `sdsys/GPL.BP/CREATEA:331`; plan §L5, §H:854, plan:17 |
| 12 | **S** | ***`sdbasic.yaml` IS GENERATED AND VALIDATED BUT NOTHING PUTS IT WHERE micro LOOKS***, so entry 2's highlighting does not yet reach a user. **Measured on this box, 9 Sep:** micro **2.0.15**, config dir `~/.config/micro`, and **no `/usr/share/micro`** — micro has no system-wide syntax path, so placement must be per-user and an installer running as root cannot do it for everyone. Three shapes in §12; the port's answer to the same problem was a per-user config home. **Until this lands the feature is inert, and inert is indistinguishable from working** — micro reports an unusable syntax file by not highlighting | `installsdai.sh`; `gplbld/microcfg/syntax/sdbasic.yaml` |

---

## 1. The PowerShell helpers, and the verifiers §L will need

**The plan is silent, and this was measured rather than assumed.** `verify-`,
*"the suite"*, *"harness"*, *"regression"* and *"verifier"* together return two
incidental hits across the plan's ~1,600 lines — plan:246 (a `$CRED` *verifier*,
a different sense of the word) and plan:1402 (a reference to CLAUDE.md's
instrument rule). Neither is about porting the suite.

***THE FIRST COUNT IN THIS ENTRY WAS A NAME-BASED GUESS AND UNDER-COUNTED THE
TESTING SIDE BADLY*** — it said "51 excluded, 31 relevant". Reclassified 9 Sep
2026 from **each script's own header line**, which is the classification below.
It is still mine rather than the plan's, but it is read rather than inferred.

| | | |
|---|---:|---|
| **Testing & verification** | **113** | 51 `verify-*` · **28 `test-*-units`** · 18 `probe-*` · 16 harness (`VerifyInstall1`/`2`, `assert-current`, `suite-only`, `elevate-once`, `capture-state`/`diff-capture`, the throwaway test account, the VM scripts) |
| **SD admin / operational** | **38** | see the split below |
| **Build & dev tooling** | **6** | `cycle`, `strip-comments`, `stale-binaries`, `check-datatree-litter`, `cleanup-devlitter`, `reword-yn-prompts` |

***A THIRD OF THE TESTING CODE TESTS THE TESTS*** — 28 `test-*-units` drive the
verifiers against fixtures. That is not over-engineering: it is the same rule
CLAUDE.md states, that a check which passes because it did nothing must fail.
**Whatever verification this project builds needs that layer or it will not know
when a check has gone blind.**

**The 38 admin scripts split three ways, and only the first is genuinely gone:**

- **13 Windows mechanism, no counterpart here** — the service, 3
  elevation/logon, profile reclamation, 3 Windows-account, system PATH, Windows
  Firewall, route groups, `micro-home` (an ACL problem Linux does not have), and
  `install-editors` (ruled out by entry 2). ***THE 3 ELEVATION SCRIPTS ARE IN
  THIS BUCKET FOR THEIR MECHANISM ONLY — UAC CONSENT HAS NO ANALOGUE — AND THE
  OWNER WAS RIGHT TO PUSH BACK ON THE WORDING.*** The **requirement** they serve,
  that some operations run with more privilege than the caller has, applies here
  in full and is `sudo`. That is **entry 14**, and it is not a porting job: this
  tree already does it, unconfigured.
- ***4 ssh SCRIPTS THAT THIS ENTRY FIRST GOT WRONG.*** They were filed as
  "Windows mechanism, no counterpart" and **the owner challenged it: this project
  uses ssh.** He is right, and the error is the same one this entry criticises in
  the `secure-*` family — sorting by mechanism and putting policy in the wrong
  bucket. Only `install-ssh` and `remove-ssh` are Windows-only (Linux gets sshd
  from the distribution; **this installer already installs it**).
  `allow-ssh-groups` writes `AllowGroups` and `ForceCommand`, which are
  **OpenSSH directives in `sshd_config`, identical on Linux** — it transfers more
  literally than almost anything else in the port. `restore-sshonly` and
  `ssh-firewall` are policy with a Linux mechanism (`ufw`/`firewalld`/`nftables`).
  `ssh-preflight` needs rethinking rather than porting: refusing to install
  because sshd exists is right on Windows and absurd here, but its real concern —
  **SD writing into an `sshd_config` it does not own** — is sharper on Linux, not
  softer. **This is entry 13.**
- ***12 `secure-*` — WINDOWS MECHANISM, TRANSFERABLE INTENT.*** Lock the global
  catalogue, the pcode library, the credential store, the audit log, the dump
  directory, the SDSYS system directories. On Linux these are POSIX modes,
  ownership and UMASK — **which is precisely §L's security posture**. Not ports;
  reimplementations of the same policy, and the port's scripts are the clearest
  statement of what that policy is.
- **7 with a direct Linux need, most already scheduled** — `upgrade-voc` and
  `upgrade-dicts` (§F1/§F2), `check-install` (§F7), `finish-install`,
  `clean-deadvoc`, `api-listener`, `restart-sd`.

***SO THE GAP IS NOT "31 SCRIPTS". IT IS AN ENTIRE VERIFICATION LAYER PLUS THE
POSIX EXPRESSION OF 12 SECURITY POLICIES.***

### PowerShell is on the development machine — measured 9 Sep 2026

***THE OWNER INSTALLED THE `pwsh` SNAP (7.6.5) FOR DEVELOPMENT AND RULED IT MUST
NOT BECOME AN INSTALL REQUIREMENT.*** Nothing this project ships uses it, and
the language split below is unchanged. **It is a reading aid, not a dependency.**

**What it actually buys, measured rather than hoped:**

| | |
|---|---|
| `.ps1` in the port | **157** |
| reference Windows-only mechanism (`Get-LocalUser`, ACLs, registry, services, `.exe`) | ***130*** — these cannot run here whatever interpreter exists |
| no obvious Windows mechanism | 27 |

***SO `pwsh` DOES NOT MAKE THE PORT'S SUITE PORTABLE, AND IT SETTLES ENTRY 8 BY
MEASUREMENT RATHER THAN BY READING***: `assert-current.ps1` carries **40**
Windows-mechanism hits, so *"a rewrite, not a copy"* stands.

***WHAT IT DID BUY, AND IT FOUND A REAL DEFECT IN AN HOUR.***
`test-fixlist-units.ps1` **runs on Linux** and is a consistency checker for
`PRE_RELEASE_FIXES.md` — index rows against detail sections, struck-in-index vs
silent-in-section, and citations of ids that do not exist. Against the port:
**284 passed, 0 failed**. It takes `-Root`, so it can be aimed here.

***AIMED AT THIS FILE IT REFUSED RATHER THAN SCORING GREEN*** — *"no index table
found - every check below would have passed by measuring nothing"*, exit 2 —
**the same null-case discipline entry 9 found in `check-stale-leads.py`**. The
sole blocker is one cell: it matches `^\|\s*\|\s*SEV\s*\|` (line 106), so the
port's header is `| | SEV | … |` and this file's said `| ID | SEV | … |`.

***AND WITH THAT ONE CELL CHANGED IT FOUND TWO GENUINE DEFECTS HERE:*** three
citations reading `PRE_RELEASE 170` and one reading `PRE_RELEASE 100 and 103`
**meant the PORT's entries** but are indistinguishable — to a reader or a tool —
from citations of *this* file's ids. **This file's own header says the two
numbering spaces are not comparable**, so the ambiguity was already a defect;
the tool merely named it. ***CONVENTION, ADOPTED 9 Sep 2026: A PORT ENTRY IS
CITED AS "the port's entry N", NEVER AS "PRE_RELEASE N".*** Fixed at all four
sites; the checker then reports **26 passed, 0 failed, exit 0**.

***ADOPTED ON THE OWNER'S RULING, 9 Sep 2026: THIS FILE'S HEADER IS NOW
`| | SEV | What | Where |` AND THE CHECKER RUNS AGAINST THE REAL FILE.***
**26 passed, 0 failed, exit 0**, and `## 2`'s heading gained its `DONE` marker
to clear the one standing NOTE — a note that is always present is a note nobody
reads. Run it with:

```sh
pwsh -NoProfile -File /home/don/Projects/SDCoreProject/sd4windows/sdb_ai/sd64/gplbld/test-fixlist-units.ps1 -Root /home/don/Projects/sdcore4linux
```

***IT HAS BEEN WATCHED REFUSING AND FAILING ON THIS FILE, NOT ONLY PASSING***,
which is what makes the green worth anything: **exit 2** *"no index table
found"* before the header changed, and **2 FAILs** on the citations before they
were fixed. **It is `pwsh`-only and lives in the port's tree** — a development
convenience, so nothing may come to depend on it; a Linux-native replacement is
still entry 9's business.

***AND IT ONLY CHECKS THIS FILE.*** It says nothing about PROJECT_STATUS.md,
which is the document `check-stale-leads.py` was for and where entry 9's real
gap remains.

### What language, and it should not default

**The owner's expectation, 9 Sep 2026:** *"most powershell scripts will need to
be converted to bash."* True for the count. **But the tree already answers this
two different ways, and the split is not arbitrary:**

- **`installsdai.sh` is bash and stays bash** — CLAUDE.md makes that a rule.
- ***EVERY BUILD AND CHECKING TOOL HERE IS ALREADY PYTHON*** — `bbcmp.py`,
  `bootstrap`-era `pcode_bld.py`, `gen_includes.py`, and this week
  `check-msglen.py`, `mkbasicsyntax.py`, `checksyntax.py`.

**A recommendation rather than a survey:**

| Kind | Language | Why |
|---|---|---|
| operational — start/stop, install packages, write a config block, set modes | **bash** | shell-shaped work, matches `installsdai.sh`, and the reader is an administrator |
| verifiers and their unit tests | **Python** | they parse output, compare before/after state and hold exit-code discipline. PowerShell's structured output has no bash analogue, and rewriting 51 verifiers plus **28 unit tests** in bash reproduces in `awk` and `sed` what the port got from objects |

***THE 28 UNIT TESTS ARE THE ARGUMENT.*** They are test code that drives other
test code against fixtures. In bash that is a large amount of quoting and
temporary files; in Python it is `unittest`, which is already available because
the build requires Python.

**Not a decision this file can take** — it is the owner's, and it should be taken
before the first verifier is written rather than discovered after twenty.

### The verifiers whose subjects are this project's too

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

## 2. The editors — **S** — ***DONE 9 Sep 2026***

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

***THE OWNER RULED ON 9 Sep 2026 AND THE REASONING IS THE USEFUL PART.*** The
port bundled both editors *"as we wanted to know what version was included
rather than having a situation where whatever the user got was dependent on the
date of the download."* **That reason does not transfer**: on Linux the
distribution's package manager already pins and updates micro, and it is the
practice this project keeps. So:

- **Microsoft Edit is dropped.** Not excluded as Windows-only — it runs on Linux
  — but not wanted.
- **micro stays, at whatever version the distribution ships.** No bundling, no
  download step, nothing in the installer that fetches an editor.
- ***THE SD BASIC SYNTAX HIGHLIGHTING IS RETAINED, AND IT IS THE ONLY PIECE OF
  THE PORT'S EDITOR WORK THAT COMES ACROSS.***

**Implemented the same day.** `gplbld/mkbasicsyntax.py` and
`gplbld/checksyntax.py` ported; `gplbld/microcfg/syntax/sdbasic.yaml` generated
from **this tree's** `sdsys/GPL.BP/BCOMP` — 218 statements, 37 reserved words,
176 intrinsics, validated at 24 quoted patterns and 0 bad. Generated rather than
copied on principle: BCOMP is the compiler, so the highlighting cannot drift
from the language. **It came out byte-identical to the port's** apart from the
header, which is itself the measurement that the two trees' BCOMP tables agree.

***AND ONE THING HAD TO CHANGE IN SD OR THE FILE WOULD HAVE DONE NOTHING.***
micro picks a syntax file by matching a regex against the **file name it is
given** — the working copy's, not the record's. This tree's `MICRO` wrote
`<record>.editing`; `sdbasic.yaml` detects `\.sdbasic$`. So `MICRO` now appends
`.sdbasic` for a BP record, using the port's own test
(`DictText # "DICT" and upcase(InFileName[-2,2]) = "BP"`). Checked against the
regex: `MYPROG.editing.sdbasic` highlights, `MYPROG.editing` and
`DICT.MYPROG.editing` do not — which is the intended answer for a VOC or data
record.

**Still undecided, and NOT settled by the above:** whether `EDIT` should stop
meaning the line editor (entry 3), and whether `MICRO` should check the editor
exists before shelling out (entry 4). The ruling was about which editors ship,
not about those two.

## 14. `sudo` is this project's elevation model, and nothing defines it

***RULED 9 Sep 2026: SD SHIPS A `sudoers.d` DROP-IN FOR A GROUP SD OWNS.***
Shape 3 below, chosen by the owner from the three offered. **This is recorded as
a selection, not as his words** — he picked the shape; the wording here is mine.

**What the ruling settles, and what it therefore commits to:**

- **Entry 18's second gate reads SD's own group**, not `sudo`/`wheel` and not
  `sudo -n -l`. That is what makes it portable across the distributions the
  installer serves, and it sidesteps the three-answer problem below entirely.
- **The 10 call sites stop hanging**, because the named commands are `NOPASSWD`
  for that group.

***THE COST THE RULING DOES NOT REMOVE, AND IT MUST BE DESIGNED FOR:*** `sudo
passwd` is **unrestricted by argument**, so a drop-in that names it plainly is
root by another route — `sudo passwd root`. The same is true of `usermod -aG`
(add yourself to `sudo`). **These need wrapping in a script SD owns that refuses
`root` and any name not an SD account**, or the drop-in grants more than the
tier does.

**Open sub-decisions this ruling creates** (none is settled by it):

| | |
|---|---|
| the group's name | `sdusers` (all SD users) and `sdu_<name>` (per account) are taken. Something like `sdadmin` is the gap |
| who is put in it | `CREATEA` on an ADMINISTRATOR-tier account, presumably — which ties this to §L2 and entry 18 |
| where it is written | the installer, and `deletesdai.sh` must remove it |

***A TRAP TO WRITE INTO WHATEVER BUILDS THIS: A MALFORMED `sudoers` FILE CAN
LOCK `sudo` OUT OF THE MACHINE.*** The drop-in must be validated with
`visudo -cf <file>` **before** it is moved into `/etc/sudoers.d/`, installed
mode **0440**, and given a name with no `.` or `~` (sudo ignores those silently
— a file that is ignored looks exactly like one that grants nothing). **And
`#includedir /etc/sudoers.d` must be confirmed present in `/etc/sudoers` rather
than assumed**, or the drop-in is inert.

### Built 9 Sep 2026 — the mechanism. ***IT IS NOT YET WIRED UP***

| | |
|---|---|
| `gplbld/sd-elevate` | the helper. Verbs `useradd`/`userdel`/`passwd`/`groupadd`/`groupdel`/`addgroup`/`delgroup`/`setgid`. Installed `/usr/local/sbin/sd-elevate`, **root:root 0755** |
| `gplbld/sdcore.sudoers` | `%sdadmin ALL=(root) NOPASSWD: /usr/local/sbin/sd-elevate` — **one command, not eight**. Installed `/etc/sudoers.d/sdcore` 0440 |
| `gplbld/test-sd-elevate.py` | 30 rows: **24 refusals, 6 controls** |
| `installsdai.sh` | creates `sdadmin`, installs the helper, `visudo -cf` **before** installing the drop-in, and refuses if `/etc/sudoers` has no `includedir` |
| `deletesdai.sh` | removes drop-in, helper, group — **drop-in first**, so a sudoers rule never outlives the group it names |

**Whitelists, not blacklists**: groups must be `sdusers`/`sdu_*`/`sdg_*`, so
*"add me to `sudo`"* has no spelling; users must be ≥ `UID_MIN` and never
`root`/`sdsys`; `setgid` is confined to the accounts root with `realpath` first,
so a planted symlink cannot aim it out.

***THE HELPER IS NOT UNDER `/usr/local/sdsys` AND THAT IS DELIBERATE.***
`installsdai.sh` does `chown -R sdsys:sdusers "$sdsysdir"` and `chmod -R 755`.
A helper living there would be **sdsys-writable**, so reaching the `sdsys`
account would mean rewriting the one command sudoers grants — root. It lives in
`/usr/local/sbin`, root-owned, outside that recursive chown.

**Measured, not asserted:** self-test **30 passed / 0 failed** as uid 1000; and
***the test was watched FAILING*** — pointed at a stub that permits everything
it scores **6 passed / 24 failed, exit 1**, so the 30/0 is not a test that
passes regardless. `visudo -cf` likewise **discriminates**: the drop-in parses
OK, a deliberately malformed copy is rejected exit 1. All four scripts
`bash -n`/`py_compile` clean, no BOM, 0 CR.

***WHAT IS STILL INERT, AND THIS IS ENTRY 12's TRAP: THE TEN CALL SITES STILL
CALL RAW `sudo`.*** `CREATE_USER:64`, `SET_PASSWD:115`, `DELACC:197,223`,
`CREATEA:306,331,634,636`, `MODIFYA:108,131` are **unchanged**. So the helper
ships and nothing invokes it — **the hang is not yet fixed.**

***AND MIGRATING THEM NOW WOULD BREAK ACCOUNT CREATION, WHICH IS WHY THEY WERE
LEFT.*** `sdadmin` has **no members**: nothing puts anybody in it, because who
belongs there is the tier, which is §L2 / entry 18 and does not exist. Point the
call sites at `sudo sd-elevate` before that lands and every one is **denied**
rather than merely prompting. ***So the call-site migration and `CREATEA`
writing the tier are one change, not two***, and they belong with entry 18.

**Nothing here has been installed** — the installer edits are unrun
(`PRE_RELEASE` 15: an install builds `origin/main`).

**One latent bug found while writing it, worth having anyway:**
`MODIFYA:131` shells out to **`deluser`, which is Debian-only** — it cannot work
on the Arch and RHEL branches the installer serves. The helper uses portable
`gpasswd -d`. Same for `groupadd -U`, recent shadow-utils only; the helper adds
members with `gpasswd -a`.

***RAISED BY THE OWNER, 9 Sep 2026:*** *"I assume some scripts need to run as an
administrator here as they did on windows."* Correct, and it is already true of
code that ships — this is not future porting work.

**Eight `GPL.BP` programs shell out to `sudo` from `OS.EXECUTE`:**

| Program | Command |
|---|---|
| `CREATE_USER:64` | `sudo useradd -m <name>` |
| `SET_PASSWD:115` | `sudo passwd <name>` |
| `DELACC:197,223` | `sudo groupdel`, `sudo userdel` |
| `CREATEA:306,331,634,636` | `sudo chmod g+s`, `sudo usermod -aG sdusers`, `sudo groupadd` |
| `MODIFYA:108,131` | `sudo usermod -aG`, `sudo deluser` |

***AND NOTHING IN THE PROJECT CONFIGURES sudoers*** — zero hits for `sudoers`,
`NOPASSWD` or `visudo` across `installsdai.sh`, `deletesdai.sh` and all of
`GPL.BP`.

**So the ADMINISTRATOR tier's real privilege is decided outside SD**, by whatever
sudo rules the machine already has, and there are only two states:

- **Broad sudo** — then the SD administrator is root. `sudo passwd root` is in
  reach, and so is everything §L withholds. **The tier is then a UI convention,
  not a boundary**, exactly as entry 13 finds for ssh.
- **No sudo** — then `CREATE.ACCOUNT`, `DELETE.ACCOUNT` and password setting
  fail, or **block on a password prompt inside an SD session**, which is a
  hang rather than an error.

***THE PLAN SAYS `sudo` ZERO TIMES.*** It reasons about root — §L5:1164 says the
Windows elevated-session carve-out's *"Linux equivalent is root, and it should be
stated rather than inherited by accident"*, which is exactly the right instinct —
but it never connects that to the `sudo` calls already in `GPL.BP`, and plan:17
and §H:853 file elevation under *"none of it applies here"*.

**What has to be decided:** whether SD ships a `sudoers.d` drop-in naming exactly
these commands for a group (the narrow, auditable answer, and the closest thing
to the port's explicit elevation helper), or whether it documents a prerequisite
and refuses to run the verbs when it is absent. **What must not happen is the
present state**, where the answer depends on a machine's history and neither
outcome is detected. Note `sudo passwd` is unrestricted by argument, so a
`sudoers` entry for it is root by another route unless it is wrapped.

### Measured on this machine, 9 Sep 2026 — the hang is real, not predicted

| | |
|---|---|
| `sudo -n -v` as `don` | ***"a password is required", exit 1*** — sudo here is password-required, not NOPASSWD |
| `sudo -n` at the call sites | ***0 of 10*** pass `-n`; none handles a password (grep over the 5 programs) |
| group names | `don` is in **`sudo`**; **`wheel` does not exist** on this box |

***SO `create.account` REACHING `sudo useradd` BLOCKS ON A PASSWORD PROMPT
INSIDE THE SD SESSION.*** That is the hang this entry predicted, now measured.

***AND THE MEMBERSHIP TEST HAS THREE ANSWERS, NOT TWO — THE PORT'S PRE_RELEASE
93 LESSON ARRIVING HERE.*** `sudo -n -l` exits **1** both when the caller is a
sudoer who needs a password **and** when the caller may not sudo at all. The
exit code cannot separate them; only locale-dependent message text can. **A
membership test built on that exit code refuses a legitimate administrator**,
which is entry 18's second gate failing closed on its own instrument.

**Three shapes, each with its flaw stated:**

1. **Group membership of `sudo`/`wheel`** — no password, deterministic, readable.
   **But the group name is distro-dependent** (`sudo` on Debian/Ubuntu, `wheel`
   on RHEL/Arch/SUSE) and this installer serves both families; and it **misses a
   user granted by a per-user `sudoers.d` rule** with no group.
2. **Ask sudo** (`sudo -n -l`) — authoritative, and defeated by the three-answer
   problem above.
3. ***SD SHIPS A `sudoers.d` DROP-IN FOR ITS OWN GROUP*** — then the test is
   membership of a group **SD owns and names**, identical on every distribution,
   and the 10 call sites stop hanging because the named commands are `NOPASSWD`.
   **This is the only one of the three that fixes the hang and the test with the
   same change.** Its cost is unchanged: `sudo passwd` unrestricted by argument
   is root by another route, so those commands need wrapping or constraining.

**Recommended: 3, with the wrapping caveat. It is the owner's ruling, not this
file's** — and it should be taken before entry 18 is implemented, because it
decides what entry 18's "member of sudoers" test actually reads.

## 20. SD does not know which person is the administrator

***FOUND 9 Sep 2026 WHILE STARTING ENTRY 18's SECOND COMMIT, AND IT STOPPED
IT.*** The gates were to be swapped for "read the register for this person's
tier". **There is no this-person to read.**

```
CPROC:279    if system(27) = 0 then          ;* entered as root?
CPROC:281      call !EUID_SET('sdsys',rstat) ;* drop to sdsys
CPROC:285      logname = kernel(K$USERNAME, 0)  ;* username in syscom -> sdsys
CPROC:288      void kernel(K$ADMINISTRATOR, 1)  ;* set admin bit
CPROC:291    i = '$LOGIN' ; call @i(j,0)
```

***THE IDENTITY IS REPLACED BEFORE `$LOGIN` RUNS.*** After `sudo sd`, `@logname`
is **`sdsys`**, not the person who typed it. Consequences, none of them
hypothetical:

- **Entry 18's register test has no subject.** *"A registered user of SD as an
  administrator"* needs a name, and the name is gone by `:285`.
- ***`CPROC:2483` IS ALREADY AFFECTED***, and it is shipped code, not planned
  work: `if not(is_grp_member(@logname, acc.record<ACC$GROUP>))` decides who may
  enter an account, and on this path it asks about `sdsys`.
- **An audit trail cannot name the administrator**, for the same reason.

***AND IT CORRECTS ENTRY 18 IN THE OTHER DIRECTION TOO, WHICH IS THE HALF THAT
MAKES THIS CHEAPER THAN IT LOOKS.*** Entry 18 says *"nothing tests sudoers"*.
**Reaching uid 0 through `sudo sd` requires sudoers membership**, so the OS half
is largely enforced already, by the operating system, before SD starts. What is
genuinely missing is the **register** half. (`su` with the root password, or
root's own shell, reach uid 0 without sudoers — so it is "largely", not
"wholly", and that gap is worth stating rather than rounding away.)

**The port's answer, and it is a design rather than a patch:** a separate
`K$OS.ADMINISTRATOR` — *"is the SIGNED-IN PERSON an administrator"* — kept
distinct from the session's `USR_ADMIN` flag, with `@logname` and the audit
message continuing to read the signed-in user.

***WHAT HAS TO BE RULED, AND IT IS NOT THIS FILE'S TO TAKE.*** Whether SD
preserves the real identity across the privilege drop — and if so whether the
person's name lives beside `sdsys` (two identities, as the port has) or replaces
the drop entirely. **Until that is decided, entry 18's gates cannot be written
against the register**, because there is nothing to key them on.

***A WARNING FOR WHOEVER IMPLEMENTS IT, FROM THE PORT'S RECORD RATHER THAN FROM
HERE.*** Its `sdusers` gate ran at `LOGIN:380` *before the account was chosen*,
and the model gave an administrator no account — so **every administrator would
have been refused at the door**. A login-path gate is the one change in this
area that can lock everybody out of the machine, and it should be built with
that failure in front of you.

## 18. What "administrator" means — the owner's definition, and the gap to it

***OWNER, 9 Sep 2026:*** *"An administrator is a person who is a member of
sudoers and is also a registered user of SD as an administrator. If they are not
a registered user they should be refused entry."* And: *"that is the current path
in the windows version — you can be a windows administrator and still not have
access to sd."* **So OS privilege is necessary and not sufficient**, which is the
opposite of what this tree implements.

**Measured against that, 9 Sep 2026 — three parts, and only one exists:**

| The definition needs | Today |
|---|---|
| member of **sudoers** | **nothing tests it.** Both admin tests are `getuid() == 0` — `system(27)` (`op_sys.c:222`) in the catalogue gates, and `IsAdmin()` (`linuxlb.c:54-55`) behind `kernel(K$ADMINISTRATOR)`. Root is not sudoers, and a sudoer is not root |
| **registered** in SD as an administrator | ***THERE IS NOWHERE TO RECORD IT.*** `@SDSYS/ACCOUNTS` has three fields — `ACC$PATH` 1, `ACC$DESCR` 2, `ACC$GROUP` 3 (`SYSCOM/KEYS.H:257-260`) — and no tier. Both shipped records carry an empty field 2 |
| unregistered → **refused entry** | **partly there.** `LOGIN:210-213` refuses a forced account (`sd -Aname`) not in the register with sysmsg 5018 and terminates the connection. Whether the *default* path refuses an unregistered user is not established |

***THE PORT ALREADY HAS THE FIELD AND CONFORMITY SAYS TAKE IT:*** its
`syscom/KEYS.H:292,294` define **`ACC$TIER 5`** — STANDARD, PROGRAMMER,
ADMINISTRATOR — and **`ACC$PRIOR.TIER 6`**, the tier SUSPENDED displaced. **Field
4 is skipped in both trees and is retired** (`ACC$USERS`); do not reuse it.

**So the work is §L2, and it is now specified rather than open:** add
`ACC$TIER`/`ACC$PRIOR.TIER` to `SYSCOM/KEYS.H` at 5 and 6, have `CREATEA` write
the tier, replace `system(27) # 0` and `IsAdmin()` with a test that reads the
register **and** checks sudoers membership, and make the login path refuse an
unregistered user rather than only a forced one. **Entry 19 has to be settled
first** — if `kernel(K$ADMINISTRATOR, 1)` grants the flag to any caller, none of
this holds. ***ENTRY 19 IS SETTLED (9 Sep) — it does not.***

### Half built, 9 Sep 2026 — the register records a tier; nothing reads it

**Commit 1 of two.** `SYSCOM/KEYS.H` gains `ACC$TIER` **5** and
`ACC$PRIOR.TIER` **6**, and `CREATEA` takes `ADMINISTRATOR`/`PROGRAMMER` and
writes field 5 for every account type.

***FIELD 4 IS SKIPPED FOR A DIFFERENT REASON THAN THE PORT'S, AND THE
DIFFERENCE IS WORTH KEEPING.*** The port must skip it: records written there
between 13 and 14 Aug 26 carry a retired grant list, so a new meaning would read
old data as new. ***HERE FIELD 4 WAS NEVER WRITTEN*** — `ACC$USERS` survives
only as a history line, the define was never present, and the one shipped record
`ACCOUNTS/SDSYS` has **three** fields (checked, not assumed). **So field 4 is
genuinely free here and is left free anyway, for conformity** — the two
`ACCOUNTS` layouts stay comparable. A later session must not "reclaim" it.

**Keywords are matched on token text, not a `KW$` constant** — `PARSER.H`'s
numbers are a positional table shared by every verb, so adding one for a single
verb is the larger change. **The cost is that they cannot be abbreviated.**
`STANDARD` is the default and is *not* a keyword; `ADMINISTRATOR` wins over
`PROGRAMMER` in either order, so a later `PROGRAMMER` cannot silently downgrade.

***WHAT THIS HALF DOES NOT DO, AND IT IS MOST OF IT.*** Nothing reads field 5 —
the gates are commit 2 — and **every account still gets the same VOC**, because
the per-tier VOC delta is §L1 and is not designed. **A tier recorded here does
not yet change what an account may do.**

***THE COMPILE CHECK WAS BOUNDED AND SAYS SO.*** `CREATEA` is `$internal`, so an
ordinary account cannot compile it — `INT$KEYS.H` is internal-only. What was run
instead is a **controlled comparison**: HEAD's `CREATEA` and the edited one
compiled the same way, and the error classes are **identical** (`INT$KEYS.H not
found`, `$CATALOG`, `@ variable as lvalue`), every one landing on a
**pre-existing** `@system.return.code` line and **none on a line this change
added**. The one extra `@` row is the same error set shifted by the comment
lines (offset +21, checked). ***THAT IS NOT A COMPILE; THE INSTALL'S TWO-STAGE
BOOTSTRAP IS STILL THE ONLY REAL ONE***, and a syntax error there aborts the
install, which is the loud failure this relies on. Fixtures removed —
`COUNT VOC` 410 before and after.

## 13. ssh is an unguarded way past the tier model

***RAISED BY THE OWNER, 9 Sep 2026, AS A CHALLENGE TO A CLASSIFICATION*** — *"we
will be using ssh here so why is there no counterpart"* — and the answer turned
out to be bigger than the misfiling.

**Three measurements, none of them inferred:**

1. **The installer installs an ssh server on every distribution** —
   `installsdai.sh:254` (`openssh`), `:272` and `:285` (`openssh-server`), `:295`
   (`openssh`) — and the Arch branch **starts and enables `sshd`** at `:265-266`.
2. **An SD user is an ordinary Unix user with a login shell.** `CREATEA:331` runs
   `usermod -aG sdusers <name>` on an account that **already exists**; it does not
   create one and does not set a shell, so the account keeps whatever `adduser`
   gave it.
3. ***NOTHING IN THIS PROJECT WRITES `AllowGroups` OR `ForceCommand`.*** Grep
   across `installsdai.sh`, `deletesdai.sh` and all of `GPL.BP`: **zero hits.**

**So the tier boundary §L1 draws does not hold at the edge of the machine.** A
STANDARD account is denied `SH` and `!` inside SD, and then reaches a shell by
running `ssh` — never entering SD at all. **The port measured this exact failure**
on 21 Aug 2026, on a machine found with a stock `sshd_config`: *"no AllowGroups
and, worse, no ForceCommand, so an sdsshonly account got a PowerShell prompt."*
Here it is not a regression to guard against; **it is the state the installer
leaves behind.**

***THE PLAN EXCLUDES THIS BY NAME AND THE EXCLUSION IS TOO BROAD.*** Line 17
lists *"elevation, Windows groups and ACLs, the firewall, OpenSSH"* and says
**"None of it applies here"**; §H:854 repeats *"OpenSSH install/removal"*. What
those name is install/removal, which genuinely is Windows-only. **The ssh-only
account model is neither named nor considered anywhere in the plan** — `ssh`
appears on 4 lines of ~1,600.

***AND §L5 IS RIGHT ABOUT WHAT IT ADDRESSES, WHICH IS WHY THE GAP IS EASY TO
MISS.*** It argues that reaching a shell is *"a policy question, not a
privilege-escalation one"* here, because `sd` is not setuid so `SH` hands the
person a shell **as themselves**. That reasoning is sound — and it is entirely
about reaching the shell **from inside SD**. ssh reaches it from outside, with
SD absent from the path, and §L5 never considers it. **The conclusion "then
`os.users` is not needed and §L1 is the whole of the answer" does not survive
that.**

***RULED 9 Sep 2026: A STANDARD ACCOUNT DOES NOT GET A REAL LOGIN SHELL — THE
TIER IS TO BE A BOUNDARY.*** Chosen by the owner from the three offered;
**recorded as a selection, not as his words.** So the answer to this section's
first bullet is *no*, and `ForceCommand` or a restricted shell is the fix rather
than a documentation change.

***THAT DECIDES THE THIRD BULLET TOO: SD MUST WRITE TO `sshd_config`.*** There
is no way to hold the boundary without it. **The port's answer is the model to
copy** — an explicit, removable fenced block, plus a preflight that **refuses**
when someone else has written the file, rather than editing an administrator's
configuration silently. `allow-ssh-groups.ps1` writes exactly these directives
and is the one port script that transfers almost literally (entry 1).

**Still to decide inside the ruling** (it fixes the direction, not the
mechanism): whether the restriction is `ForceCommand` into `sd`, a restricted
login shell, or `AllowGroups` excluding STANDARD; and what PROGRAMMER gets,
which this ruling did not cover. ***AND THE MEASUREMENT BELOW IS WHAT THE FIX
WILL BE CHECKED AGAINST***: today every SD account has a real shell, so a
verifier for this has a known-bad starting state to prove it moved away from.

**What has to be decided, and it belongs with §L rather than after it:**

- Do SD accounts get a **real login shell** at all? If the answer for STANDARD is
  no, that is `ForceCommand` or a restricted shell, and it is the whole fix.
- If yes, then **§L1's verb withholding is a convenience, not a boundary**, and
  the documentation must say so rather than implying containment.
- Either way, **does SD write to `sshd_config`?** Doing so silently to a file the
  administrator owns is worse than not doing it; the port's answer was an
  explicit, removable fenced block plus a preflight that refuses when someone
  else has written the file.

### Measured on this machine, 9 Sep 2026

| | |
|---|---|
| shells of `sdusers` members | `don` **`/bin/bash`**, `sdsys` **`/bin/sh`**, `root` `/bin/bash` — ***every SD account has a real login shell***, none is `nologin` |
| `AllowGroups`/`ForceCommand` written by this project | **0** (installer + all of `GPL.BP`) |
| `sshd` on this box | **inactive** — installed, not running |

***SO THE FIRST BULLET ABOVE IS ANSWERED FOR THE PRESENT STATE: SD ACCOUNTS DO
GET A REAL LOGIN SHELL, AND NOTHING RESTRICTS IT.*** §L1's verb withholding is
therefore **a convenience, not a boundary**, exactly as the second bullet
warns — and that is now measured rather than argued.

**One thing the measurement does NOT establish**, written in the conditional:
`sshd` being inactive here makes the exposure **latent on this box, not
absent**. The Arch branch starts and enables it (`installsdai.sh:265-266`), and
any administrator may start it on any distribution; **an inactive daemon is a
property of this machine today, not of the product.**

**Related verifiers that exist there and nowhere here:** `verify-sshonly`,
`verify-sshadmin`, `verify-allowgroups`, `probe-sshfirewall`,
`probe-sshpreflight`, `probe-sshremote` — the last of which is the one that
proved the scoping actually blocks a **remote** machine, host to guest, because
NAT could not show it.

## 12. Getting `sdbasic.yaml` to where micro looks

**Measured on the development machine, 9 Sep 2026:** micro **2.0.15**, its
configuration directory is `~/.config/micro`, and there is **no
`/usr/share/micro`** — stock micro has no system-wide syntax path. So the file
has to land in a **per-user** directory, and `installsdai.sh` runs under `sudo`
and cannot populate the home of every user who will ever run SD.

Three shapes, and the first is recommended:

1. ***`MICRO` PLACES IT ON FIRST USE.*** Before launching, copy the shipped
   `sdbasic.yaml` into `$HOME/.config/micro/syntax/` if it is absent or older.
   Per-user, needs no privilege, self-heals for accounts created later, and
   leaves the user's own micro settings alone. **Closest to the port**, whose
   `micro-home.ps1` solved the same problem by giving the caller a config home.
2. **The installer seeds it** for existing users and the skeleton profile.
   Misses every account created afterwards.
3. **`MICRO` passes `-config-dir`** at a shared location. Works, but **bypasses
   the user's own micro configuration**, which is theirs and not SD's to
   override.

***UNTIL THIS LANDS THE FEATURE IS INERT, AND INERT LOOKS EXACTLY LIKE
WORKING*** — `checksyntax.py`'s own header makes the point: micro reports a
syntax file it cannot use by simply not highlighting, which is what a file it
never found looks like too. **Whoever does this must check highlighting on a
real record, not just that the file was copied.**

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

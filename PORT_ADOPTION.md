# PORT_ADOPTION.md

Owner, 10 Sep 2026: for every feature of SD Core for Windows not implemented
here, review the port's code and **adopt or adapt it unless it would fail on
Linux**; keep a list of the code that could not be adopted, the feature it
belongs to and why, and **use this list as the basis for future tasks**.
Reference tree: `/home/don/Projects/SDCoreProject/sd4windows`. Update this file
in the same commit as the work.

## Adopted so far (10 Sep 2026)

- Parity audit corrections — PROJECT_STATUS "Parity audit" (`8a1b343`).
- `gpl.bp/EDIT` as `NANO`/`MICRO`, `test-edittokens-units.py` (`2d759f7`).
- UPSTREAM_FIXES 1, 3, 8, 9, 10, 14, 18, 20, 29, 35 and port PRE_RELEASE 174
  (C). Witnessed pre/post: 9, 18, 20 (branch), 35. Compile-only: 1, 3, 8, 10,
  14, 29, 174.
- QSELECT list-number (UPSTREAM 21) + DELETE.INDEX case-fold (UPSTREAM 22),
  11 Sep 2026 (`af879d3`). ***BOTH WITNESSED ON THE `af879d3` INSTALL*** (stamp
  02:19:18, `assert-current` 0):
  - **QSELECT** — `qselect voc * saving 3` → `410 record(s) selected to select
    list 0`; `... to 2` → `... select list 2`. The number is present and TRACKS
    the TO argument, so %2 is the real target list, not a constant. 410 > 0, so
    not the null case. ***NOTE THE GRAMMAR: a record specifier is required***
    (`qselect voc saving 3` answers "No records specified to process" — the
    `qselect voc saving 3` in UPSTREAM 21's write-up does not run here).
  - **DELETE.INDEX** — fixture: dict entry `F1` written by a scratch BASIC
    program, `create.index zzak F1` → `Added index for F1`. Then
    `delete.index zzak f1` (LOWER) → ***`Deleted index F1`***. Control
    `delete.index zzak nosuchidx` → `Unrecognised index name (nosuchidx)`, so
    the refusal path still works and the success is not blind acceptance; the
    control also confirms an unmatched name is echoed AS TYPED.
  - Fixtures removed; DON back to `COUNT VOC` 410.

## UPSTREAM_FIXES reconciliation — all 37, 11 Sep 2026

Measured against this tree's source, because this file named only 19 of the 37
and most of the rest had been fixed on 8–9 Sep under the parity plan's own ids
(`PROJECT_STATUS` "Step 1" / "Step 2") without being cross-referenced here.

- **Done here (28):** 1, 3, 8, 9, 10, 14, 18, 20, 29, 35 (10 Sep C batch) ·
  21, 22 (11 Sep, witnessed) · 7 = B1/B2 · 19 = D2 · 24 = D3 · 25 = C1 ·
  26 = E1 · 28 = D1 · 30 = A5 · 33 = A6 · 32 = A1 (`txn.c:20`) · 36 = A2
  (`txn.c:257`) · 17 (`txn.c:831`) · 31 (`txn.c:338`) · 5 (`LOGIN:545`) ·
  37 (`CPROC:3185` already says verb 15) · 15 (VFS removed, plan G2) · 16
  (MICRO superseded by the port's EDIT).
- **Not applicable (1):** 2 — resolved in the port as *not* upstream's bug.
- **Open (8):** 23, 27 → queue 3 · 12 → queue 5 · 11 → queue 6 · 4, 6, 13, 34
  → queue 20.

## PRE_RELEASE_FIXES reconciliation — all 186 of the port's entries, 11 Sep 2026

Each entry read from the port's index row, and every product-code entry checked
against this tree's source (not against this file's earlier claims). Classes:

- **Done here (25):** 1, 17, 18 (EDIT adopted, `2d759f7`) · 7 (`sort.item` not
  in `TIER.OMIT.STANDARD`) · 11, 12, 13, 15, 23, 24, 25, 87, 100, 101, 102,
  103, 154 (UPSTREAM fixes, see above) · 21 (no `ACC$PRIOR.TIER` test exists
  here to delete) · 79 (every Y/N message shows its default) · 94 (group calls
  test `OS.ERROR()`) · 95, 97, 110, 128 (parity audit / 10 Sep) · 174 (SH1 argv).
- **Open, already queued:** 8 → 7 · 14, 26 → 3 · 16 → 10 · 19, 111 → 12 ·
  22 → 8 · 27, 98 → 13 · 57, 91, 92 → 14 · 65, 93 → 19 · 70 → 16 ·
  104, 113 → 4 · 142 → 9 · 144 → 21.
- **Open, NEW — added to the queue as 23–25, and 63/136 folded into 9:** 5
  (`.D name`), 114 (BCOMP hang), 28 (dump directory), 63 + 136 (file-record
  descriptions).
- **Does not transfer — Linux privilege/access model (15, with 168):** 2, 37, 42, 56, 64,
  68, 69, 72 (CREATUSR is off, so CREATE.ACCOUNT makes no OS user to strand),
  96, 99, 125, 130, 167, 169 — `os.users`, `$cred`, S4U, routes and logon
  rights; Linux has entries 13/18/20/23 instead. ***And 168: the port deleted
  `EUID_SET`/`EUID_RESTORE` and `sdext_eguid.c` as dead code; HERE THEY ARE LIVE
  (`sudo sd` drops to `sdsys` through `sdext_eguid.c`). DO NOT ADOPT.*** Nor
  anything else that removes from the extension layer: embedded Python is kept
  and improved (owner, 11 Sep).
- **Ruled not a defect / no change in the port (8):** 3, 9 (UMASK kept both
  sides), 20, 44 (5161 left unchanged there too — but its Linux analog is real:
  a group added by CREATE.ACCOUNT reaches the person only at their next login),
  61, 62, 157, 163.
- **Windows mechanism — installer, service, firewall, ssh capability,
  profiles, registry (55):** 6, 29, 32, 33, 35, 36, 39, 49, 50, 66, 67, 74,
  75, 76, 77, 78, 81, 83, 85, 88, 89, 90, 115–124, 126, 127, 129, 132, 133,
  135, 138, 139, 140, 141, 145, 146, 147, 148, 150, 153, 155, 161, 171, 172,
  173, 176, 184.
- **Port's PowerShell verify/test harness (46) — intent is queue 22:** 10, 30,
  31, 38, 40, 41, 43, 45, 46, 47, 48, 51, 54, 59, 60, 73, 82, 84, 86, 105–109,
  112, 131, 134, 137, 143, 149, 151, 152, 156, 158, 159, 160, 162, 164, 165,
  166, 170, 177, 178, 182, 183, 185. (178 and 185 are still open in the port.)
- **Port's documentation set (13):** 4, 34, 52, 53, 55, 58, 71, 80, 175, 179,
  180, 181, 186, and 163's documentation half.

Counts **measured, not typed**: 25 + 19 + 5 + 15 + 8 + 55 + 46 + 13 = 186, no
number missing or in two classes (163 counted under "ruled"). The checker is a
throwaway script; re-derive by expanding the lists above. *A first hand-typed
count was wrong in six of eight classes — which is why it was checked.*

## Queue — adoptable, not yet done (suggested order)

| # | Feature | Port code | Linux adaptation |
|---|---|---|---|
| 3 | DELETE.FILE NO.QUERY never prompts, msg 10117 (UPSTREAM 23 **and 27**) + prompt loops need an EOF exit (no UPSTREAM entry) — ***REPRODUCED HERE 11 Sep, see below*** | `DELETEF` | direct |
| 4 | DELETEF takes the ospath result, msg 2636 (port PRE_RELEASE 104) | `DELETEF` | direct |
| 5 | LOGIN falls back when TERM has no terminfo (UPSTREAM 12) | `LOGIN` | direct |
| 6 | ED return-code preset sign (UPSTREAM 11 note) | `ED` | verify first |
| 7 | HELP / F1 say something, msg 10149 (port 8) | `CPROC` | direct |
| 8 | CREATE.ACCOUNT names why a password failed, 10118–10121 (port 22) | `CREATEA`, `SET_PASSWD` | map PAM/passwd status |
| 9 | `NEWVOC/NEWVOC` description (port 142), and every file record's field 1 a description rather than a bare `F` (port 63, 136) | data, `VOC_TEMPLATE`/`NEWVOC` | direct |
| 10 | LOGOUT reaps a dead user 10167; CNAME names the holder (port 16) | `CPROC` + C | review |
| 11 | `[locked]` VOC records, 10165/10166 (port 70) | `LOGIN update.voc` | direct |
| 12 | SUSPENDED tier, 10110/10112/10159 | `MODIFYA tier.set`, `LOGIN`, `CPROC logto`, `APISRVR` | SD doors only |
| 13 | K$AUDIT trail + records (MODIFYA ADD/DELETE, grants, elevation) | `op_kernel` `K_AUDIT`, `k_error.c` `audit_message`/`audit_rotate`, callers | key from the Linux block (93); O_APPEND + file mode instead of `win32audit.c` |
| 14 | TIERGATE, GRANT/REVOKE/LIST.GRANTS, ADD tier ordering, promotion report 10126–10129 (port 57) | `TIERGATE`, `GRANTA`, `CPROC`, `MODIFYA` | `os_group` → `sd-elevate addgroup/delgroup`; `getent group` |
| 15 | ADOPT keyword + installer seed | `CREATEA` | PROJECT_STATUS "ADOPT" |
| 16 | Upgrade runs UPDATE.ACCOUNTS ALL (port 70) | `upgrade-voc.ps1` | `installsdai.sh` when accounts are kept |
| 17 | MODIFY.PASSWORD | `SET_ACC_PASSWORD` | `sd-elevate passwd`; no `$cred` |
| 18 | Lower-case conversion §M — ***COMPLETE, NOT THE PORT'S PARTIAL RESULT*** (owner, 11 Sep; see below) | port 5.12 | release-blocking; goes past the port |
| 19 | Register/OS reconciliation at start (port 93) | `reconcile-accounts.ps1` | systemd `ExecStartPre` script — review |
| 20 | UPSTREAM 4, 6, 13, 34 — read each entry and verify against this tree | — | — |
| 21 | `check-stale-leads.py` (PRE_RELEASE 9 here) | `gplbld` | adapt to this tree's docs |
| 22 | Verifier intent (the port's `verify-*`/`test-*` .ps1) | `gplbld` | Python, per PRE_RELEASE 1 |
| 23 | `.D name` folds case, reports 5043 instead of falling through with a stale `voc.rec`, and releases the lock it took (port PRE_RELEASE 5) | `CPROC` `.D` | direct; also a lock leak here — the miss path releases `at.command` after a failed `readu` on `upcase(at.command)` |
| 24 | BCOMP hangs on an unterminated TRANSACTION construct (port 114) | `BCOMP` inner loop, `until end.source` | direct |
| 25 | Process dumps in their own directory, writable but not readable by SD users (port 28) | `sd.conf DUMPDIR`, installer | mode/group bits instead of the port's ACL; `pdump.c` already honours `DUMPDIR` |

## Queue 18 — lower case: the owner's ruling and where the port stopped short

***OWNER, 11 Sep 2026: "here everything needs to be lowercase so that we don't
have the situation of multiple commands, files or record ids that have the same
name but multiple casing."*** The port's §5.12 set that goal and did not reach it
— NTFS matches names regardless of case, so what was missed never failed there.
Filed to the port as a bug for its next version (`BUGS_FROM_LINUX_PORT.md` 5).

**Nothing of §M exists here yet** — measured 11 Sep: sdsys directories 12 of 18
upper, `NEWVOC` 395 upper / 1 lower, `VOC_TEMPLATE` 418 upper, and 0 lookups in
`GPL.BP` with a lower-case tier (the port has 76 in 38 files).

**What the port left upper case — do each of these here, rather than copy the
port's result** (measured on the port tree 11 Sep):

| Left upper in the port | Where | Plan §M covers it? |
|---|---|---|
| Files `CREATE.FILE` makes: OS name upper-cased unless `CREATE.FILE.CASE` is set, and nothing sets it | port `CREATEF:309-311` (here `:304-306`) — `create.file zzak` made `ZZAK` on this box | **no** |
| All 203 `gpl.bp` program sources, 12 of 15 `syscom` includes | `CPROC`, `QSELECT`, `ERR.H`, `KEYS.H` … | **no** |
| Case inversion at sign-on | port `LOGIN:624` / here `:250`, `pterm(PT$INVERT, @true)` | **no** |
| Account names, "forced to uppercase" | port `syscom/KEYS.H:269` | kept deliberately by the plan (§M3) — ***RE-RULE*** |
| VOC ids `$ACC`, `$MAP`, `$RELEASE`, `SD.VOCLIB`, `TIER.ADD.ADMINISTRATOR`, `TIER.OMIT.STANDARD` | port `newvoc`, `voc_template` | partly — §M3 renames "the `$` records" without naming these |
| Lookup sites the first pass missed | `.D` (port entry 5, open here — audit below), `_VOC_REF`, the `$SAVEDLISTS` literals | yes for the last two |

Not names, so correctly left alone: `%E` `%G` `%L` (and pairs) are the escaped
filenames of records `=` `>` `<`; `#` `&` `!` are symbols.

***OPEN FOR THE OWNER, NOT RULED:*** does "record ids" reach **record ids in a
user's own data files**? Plan §M3 keeps directory-file record ids case-sensitive
on ext4 because `SUE` and `sue` are two files there. Forcing an application's
data ids to lower case would change its data, so this was not assumed either way.
Likewise account names (row 4 above).

## Queue 3 — measured here, 11 Sep 2026, not read

***`delete.file zzak no.query` PROMPTED ANYWAY***, on an ordinary account file
with no system-account part, on the `af879d3` install. Measured while clearing a
DELETE.INDEX fixture, not while looking for it:

```
:delete.file zzak no.query
OK to delete DATA portion 'ZZAK'? OK to delete DATA portion 'ZZAK'? ...
```

**Two separate faults. The first is the port's UPSTREAM 27, which this file
failed to list; the second is in no UPSTREAM entry.** *(Corrected 11 Sep: an
earlier version of this note said UPSTREAM 23 named neither and presented fault
1 as new. The port had already written it up as #27 — "Separate from #23".)*

1. ***`NO.QUERY` IS PARSED AND SIMPLY DOES NOT REACH THESE TWO PROMPTS***
   (= UPSTREAM 27). `DELETEF:84` sets `no.query` and `:109` honours it for the
   select-list query, but the DATA-portion prompt at `DELETEF:221-232` and the
   DICT-portion prompt at `:295-304` are each guarded by ***`if not(force)`
   ALONE***. UPSTREAM 23 is the separate `check.sdsys.file` prompt; queue 3
   must take both 23 and 27.
2. ***BOTH PROMPTS BUSY-LOOP ON EOF, BY CONSTRUCTION.*** Each is
   `loop … input yn … until yn = 'Y' or yn = 'N' repeat`. At EOF `input` yields
   empty, `yn[1,1]` is neither `Y` nor `N`, and the loop has no escape — it spins
   rather than blocking (pid observed in state `R`, 98.9 MB in 40 s). The same
   `loop/until` shape is at `:112`, `:155`, `:187` and `:350`, so this is a
   pattern in the verb, not one bad site.

**Why a plain `zzak` hit it — settled by UPSTREAM 27, and consistent with what
was measured:** the test is `data.path # default.path` (`:221`) with
`default.path = file.name` (`:219`), and `CREATE.FILE` upper-cases the OS name
unless `CREATE.FILE.CASE` is set, so `zzak` is stored as `ZZAK` (seen on disk:
`/home/sd/user_accounts/don/ZZAK`) and the two always differ for a lower-case
name.

**Consequence for instruments:** drive `sd` down a pipe only with verbs known not
to prompt, and always under `timeout`. `list.index` hung the same way earlier in
the session. The clean-up that avoids the verb entirely is `rm -rf` the file's
two directories plus `DELETE VOC <name>`.

## Not adoptable — code, feature, reason

| Port code | Feature | Why it cannot be adopted or adapted on Linux |
|---|---|---|
| `sd.iss`, `stage.py`, `bootstrap.py`, `test-upgradeiss-units.py`, `finish-install.ps1`, `install-service.ps1`, `check-install.ps1` | Windows installer and service | Inno Setup and the Windows service manager; the Linux installer is `installsdai.sh` |
| `ELEVATE`, `elevate-once.ps1`, `sd-elevate.ps1`, `sd-elevate-helper.ps1`, `PS_SCRIPT`, `PS_SCRIPTO` | Elevation | UAC and PowerShell do not exist; Linux uses `sudo` + `gplbld/sd-elevate` |
| `OS_GROUP`, `DELETE_USER` profile half, `PROFILE_DIR`, `reclaim-profiles.ps1`, `clean-test-profiles.ps1`, `secure-reclaim.ps1` | Local groups and user profiles | Win32 group APIs and the registry ProfileList; Linux: `sd-elevate` group verbs, `userdel [-r]` |
| `CRED_SET`, `CRED_VERIFY`, `$cred`, SCRAM in `APISRVR` (`vb.scram.first/final`), `secure-cred.ps1` | API login without OS passwords | Exists because a Windows service cannot check a Windows password; Linux `APISRVR` verifies the OS password (`login_user`). Would run on Linux but needs a client-protocol change on both sides — **owner decision** (the password crosses TCP 4243) |
| `os.users`, `secure-osusers.ps1`, `verify-osusers.ps1` | Per-person OS grants | Ruled model difference: per-account `ACC$SH`/`ACC$OS.EXEC` (privilege model) |
| `K$WINPATH`, `K$WINPID`, `K$SET.USERNAME`, `K$ASSUME.USER`, `K$IMPERSONATING`, `win32s4u.c` | Path conversion, S4U impersonation | Cygwin and Win32 token APIs; a Linux session already runs as its user |
| `K$OS.ADMINISTRATOR`, `K$INTERACTIVE`, `SDADMIN` | Elevation and desktop tests | Windows token/desktop; Linux answers with `sudo` + `CPROC grant.administrator` |
| `REMOTEAPI`, `REMOTESSH`, `SSHSRVR`, `api-firewall.ps1`, `ssh-firewall.ps1`, `install-ssh.ps1`, `remove-ssh.ps1`, `allow-ssh-groups.ps1`, `sync-route-groups.ps1`, `deny-logon.ps1`, `restore-sshonly.ps1`, `api-listener.ps1`, `ssh-preflight.ps1` | REMOTE.API / REMOTE.SSH / SSH.SERVER, ssh/api/both/none routes | Windows Firewall, the OpenSSH capability and logon rights; Linux ruled the ForceCommand tier boundary (PRE_RELEASE 13) and installer prompts. A systemctl/ufw version is possible — **owner ruling needed** |
| `APNDPATH` / APPEND.SD.PATH, `sd-path.ps1` | SD on the PATH | Registry PATH; the installer links `/usr/local/bin/sd` |
| `micro-home.ps1`, `install-editors.ps1`, Microsoft Edit | Editor configuration and bundling | Linux micro's home is already per-user writable; MS Edit is not packaged (owner); editors come from the distribution |
| `secure-*.ps1` (account-dirs, accounts, audit, dumps, gcat, log, pcode, psdir, sysdirs), `verify-*acl.ps1` | NTFS ACL hardening | ACL model does not exist; **the intent** (who may write gcat, audit, dumps, pcode) should be reviewed as owner/group/mode — future task |
| `win32audit.c` | Append-only audit file | Win32 FILE_APPEND_DATA; the feature itself is queue 13 |
| `exepath.c` directory split, `sdwind` naming | Program layout | Windows keeps executables apart from pcode; Linux keeps `sdsys/bin` |
| `mkvocdoc.py`, `SDCoreWindowsDocs` | Documentation build | Coupled to `sd.iss` and the Windows doc set |
| `probe-*.ps1`, `verify-*.ps1`, `test-*-units.ps1`, `cycle.ps1`, `VerifyInstall*.ps1`, `vm-*.ps1`, `capture-state.ps1` | Test and cycle instruments | PowerShell and Windows state; the intent is queue 22 |
| UMASK removal | Port removed UMASK | Kept here on purpose: real on Linux (stance) |

## Port defects found while adopting

Written to the port as `BUGS_FROM_LINUX_PORT.md` (10 Sep 2026, uncommitted
there): MODIFYA `tier.build.rec` strips field 1; sdtic end-of-file skips the
failure count; 10114 can be false; CREATEA stale description.

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

## Queue — adoptable, not yet done (suggested order)

| # | Feature | Port code | Linux adaptation |
|---|---|---|---|
| 3 | DELETE.FILE NO.QUERY never prompts, msg 10117 (UPSTREAM 23) — ***REPRODUCED HERE 11 Sep, see below*** | `DELETEF` | direct |
| 4 | DELETEF takes the ospath result, msg 2636 (port PRE_RELEASE 104) | `DELETEF` | direct |
| 5 | LOGIN falls back when TERM has no terminfo (UPSTREAM 12) | `LOGIN` | direct |
| 6 | ED return-code preset sign (UPSTREAM 11 note) | `ED` | verify first |
| 7 | HELP / F1 say something, msg 10149 (port 8) | `CPROC` | direct |
| 8 | CREATE.ACCOUNT names why a password failed, 10118–10121 (port 22) | `CREATEA`, `SET_PASSWD` | map PAM/passwd status |
| 9 | `NEWVOC/NEWVOC` description (port 142) | data | direct |
| 10 | LOGOUT reaps a dead user 10167; CNAME names the holder (port 16) | `CPROC` + C | review |
| 11 | `[locked]` VOC records, 10165/10166 (port 70) | `LOGIN update.voc` | direct |
| 12 | SUSPENDED tier, 10110/10112/10159 | `MODIFYA tier.set`, `LOGIN`, `CPROC logto`, `APISRVR` | SD doors only |
| 13 | K$AUDIT trail + records (MODIFYA ADD/DELETE, grants, elevation) | `op_kernel` `K_AUDIT`, `k_error.c` `audit_message`/`audit_rotate`, callers | key from the Linux block (93); O_APPEND + file mode instead of `win32audit.c` |
| 14 | TIERGATE, GRANT/REVOKE/LIST.GRANTS, ADD tier ordering, promotion report 10126–10129 (port 57) | `TIERGATE`, `GRANTA`, `CPROC`, `MODIFYA` | `os_group` → `sd-elevate addgroup/delgroup`; `getent group` |
| 15 | ADOPT keyword + installer seed | `CREATEA` | PROJECT_STATUS "ADOPT" |
| 16 | Upgrade runs UPDATE.ACCOUNTS ALL (port 70) | `upgrade-voc.ps1` | `installsdai.sh` when accounts are kept |
| 17 | MODIFY.PASSWORD | `SET_ACC_PASSWORD` | `sd-elevate passwd`; no `$cred` |
| 18 | Lower-case conversion §M | port 5.12 | release-blocking |
| 19 | Register/OS reconciliation at start (port 93) | `reconcile-accounts.ps1` | systemd `ExecStartPre` script — review |
| 20 | UPSTREAM 4, 6, 13, 34 — read each entry and verify against this tree | — | — |
| 21 | `check-stale-leads.py` (PRE_RELEASE 9 here) | `gplbld` | adapt to this tree's docs |
| 22 | Verifier intent (the port's `verify-*`/`test-*` .ps1) | `gplbld` | Python, per PRE_RELEASE 1 |

## Queue 3 — measured here, 11 Sep 2026, not read

***`delete.file zzak no.query` PROMPTED ANYWAY***, on an ordinary account file
with no system-account part, on the `af879d3` install. Measured while clearing a
DELETE.INDEX fixture, not while looking for it:

```
:delete.file zzak no.query
OK to delete DATA portion 'ZZAK'? OK to delete DATA portion 'ZZAK'? ...
```

**Two separate faults, and UPSTREAM 23 names neither.** Both read off the source
after the measurement:

1. ***`NO.QUERY` IS PARSED AND SIMPLY DOES NOT REACH THESE TWO PROMPTS.***
   `DELETEF:84` sets `no.query` and `:109` honours it for the select-list query,
   but the DATA-portion prompt at `DELETEF:221-232` and the DICT-portion prompt
   at `:295-304` are each guarded by ***`if not(force)` ALONE***. So `FORCE`
   suppresses them and `NO.QUERY` never could. UPSTREAM 23 is about the
   unguarded `check.sdsys.file` calls — ***a different prompt, on a different
   path***; the entry's scope is narrower than the defect, and a fix that only
   does what 23 says would leave this live.
2. ***BOTH PROMPTS BUSY-LOOP ON EOF, BY CONSTRUCTION.*** Each is
   `loop … input yn … until yn = 'Y' or yn = 'N' repeat`. At EOF `input` yields
   empty, `yn[1,1]` is neither `Y` nor `N`, and the loop has no escape — it spins
   rather than blocking (pid observed in state `R`, 98.9 MB in 40 s). The same
   `loop/until` shape is at `:112`, `:155`, `:187` and `:350`, so this is a
   pattern in the verb, not one bad site.

**The prompt fires for ordinary files, which is why a plain `zzak` hit it.** The
test is `data.path # default.path` (`:221`) where `default.path = file.name`
(`:219`) — a bare name — so a file whose stored path is anything fuller than its
VOC name compares unequal and asks. Confirm that reading before fixing; if it
holds, `DELETE.FILE` without `FORCE` prompts for very nearly every file.

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

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

## Queue — adoptable, not yet done (suggested order)

| # | Feature | Port code | Linux adaptation |
|---|---|---|---|
| 1 | QSELECT prints list number (UPSTREAM 21) | `gpl.bp/QSELECT` | direct |
| 2 | DELETE.INDEX folds case (UPSTREAM 22) | `DELETEI` | direct |
| 3 | DELETE.FILE NO.QUERY never prompts, msg 10117 (UPSTREAM 23) | `DELETEF` | direct |
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

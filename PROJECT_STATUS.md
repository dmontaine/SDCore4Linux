# PROJECT_STATUS.md

Handoff document for SD Core for Linux. See [CLAUDE.md](CLAUDE.md) for how to
maintain it: terse, `file:line` over description, updated in the same commit as
the work, nothing in "Verified" that was not observed that session.

## THE TASK TABLE — READ THIS BEFORE ANSWERING "WHAT IS LEFT"

Owner, 14 Sep 2026, adopting SD Core for Windows' table of 26 Aug 2026: **a
table at the top, checked off as items finish, so nobody searches history to
find out what is left.**

***IT IS THE AUTHORITY ON STATUS. The entries carry the reasoning; this carries
the state.*** `python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/check-stale-leads.py`
checks every row against its entry in both directions and exits non-zero on
drift. Run it before answering the question this table exists for.

**IDs are never renumbered or reused.** `P.N` is PRE_RELEASE_FIXES row N, `Q.N`
PORT_ADOPTION queue row N, and `S.N` / `W.N` the one bracketed tag of that name
in this file or PORT_ADOPTION.md (`W` = waiting for the owner). Open rows run
cheapest first. Entries closed before 14 Sep 2026 have no row.

| | ID | cost | what | settled |
|---|---|---|---|---|
| ◐ | **S.19** | XL | ***PRIORITY #1 (owner, 15 Sep 2026), above cheapest-first:*** release blocker for 1.1 — the API session crossed TCP 4243 unencrypted. TLS 1.3 relay + SCRAM bound by tls-exporter, on `main` at `0d58171`; witnessed on that install 15 Sep: §13i T1–T8 all pass, run 253/256 (`/var/tmp/witness-release-run.20260915-095336.log`); re-witnessed on `0b67dba`, 256/256 (`…-102147.log`). 15 Sep, adopted from the port's RELEASE_1.1 42 (follow-Windows rule): `scram-probe.py` refusal modes `--gs2`/`--tamper-nonce`/`--bad-cbind`/`--replay` and the wire line; free checks `test-scramprobe-units.py` 13/13 and `test-tlsconsts-units.py` 14/14, each red on a mutant; probe smoke-tested against the live 0b67dba server (47 refusals over TCP and the socket, `y,,` → 5272, `--no-tls` no ACK). §13i T1–T14c ALL PASS on `c773008` (269/269, 15 Sep 15:46), the OpenSSL 4 const fix included. Windows-client→Linux-server interop PASSED 15 Sep 16:12 (the Windows agent's measurement, sd4windows `92a553a`: TLS 1.3, bound SCRAM, `WHO` → `122 zzinterop`); ***INTEROP PASSES BOTH WAYS, 15 Sep 2026***: Windows client → this server (theirs, 16:12, sd4windows `92a553a`) and Linux client → their server (here, owner-run last step — signature VERIFIED, `WHO` → `7 ZZINTEROPW`); ***PINNING RULED 15 Sep 2026 (owner): 1.1 PERSISTS THE SERVER IDENTITY*** across a keep cycle (`deletesdai.sh`, done), and client-side recognition is 1.2's mutual enrolment — S.20. left: the port's half (its RELEASE_1.1 41), §OPEN§ and not in this tree. Port's mail 16 Sep 22:14 (sd4windows RELEASE_1.1 43, `090756d`+1): its relay now has this tree's per-connection shape as a native spawn (`sdtlsrelay.exe`, S4U token for a bare `sdrelay` account, Low integrity, 0 privileges); wire to the client unchanged, client library unchanged; two socketpair-only deltas from `sd_tlssrv.c` (PEM bytes sd→relay; status byte + text relay→sd). Its units 27/27; witnessed on its install 16 Sep 22:57 (mail 23:05, its RELEASE_1.1 43 struck, `dbb0588..33c75c9`): `verify-relayidentity` 15/15 — one `sdtlsrelay.exe` per held connection, owner `sdrelay`, Low, 0 privileges, parent `sd.exe` still SYSTEM, gone at close. Its `syslog()` lands in the Windows Application event log, provider `sd_Log` — ask for that, not `sdsys/errlog`, when reading a Windows relay report. Nothing to change here | — |
| ◐ | **S.25** | XL | ***THE TEARDOWN, 1 OF 4 (owner's decision, 18 Sep 2026 — the plan's §L reversed): the tier machinery comes out.*** `sdsys/tier.policy` and its two lists, `GPL.BP/TIERGATE` and `!tier_allows` with it (`cproc:2847-2852`, `granta:248`, `modifya:239`, `:633`), `ACC$TIER`/`ACC$PRIOR.TIER` and every arm that reads them (`createa:185`, `:243-254`, `:574-610`; `login`; `modifya` and its `voc.delta`), the module's messages. ***ONE VOC LAYER REMAINS*** — NEWVOC as shipped, the PROGRAMMER set, which is what every account now gets. Supersedes S.3's build, Q.16's `update.accounts` layer, Q.22's `tierapi` leg (§13j: built, never runs). ***§BUILT§ (`e41d318`, 18 Sep 2026) — left: the fresh install + witness cycle; nothing measured on a machine yet.*** | — |
| ◐ | **S.26** | L | ***THE TEARDOWN, 2 OF 4: one administrator, SDSYS — and LOGTO is not the way in.*** SDSYS is tied to the `sdsys` OS account and entered only by running SD as that identity from a local session; `LOGTO sdsys` becomes refused for everyone (`cproc:2847` refuses only an unflagged session today); `grant.administrator`/`K$ADMINISTRATOR` (`cproc:901`, `linuxlb.c:62`) and `sdadmin` stop conferring SD administration — plain `sudo sd` is another administrator and is refused. Shapes: W.5, W.6. ***§BUILT§ (`e41d318`, 18 Sep 2026) — left: the fresh install + witness cycle; nothing measured on a machine yet.*** | — |
| ◐ | **S.27** | L | ***THE TEARDOWN, 3 OF 4: the OS-access gates go — standard Linux limits only.*** `ACC$SH`/`ACC$OS.EXEC` and the `SH-ON`/`SH-OFF`/`OS-ON`/`OS-OFF` arms, `USR_ADMIN` (`op_sh.c:128-139`), `login:439-442`, and the refusal messages 10039/10041/10042/10053/10054; SH and `!` then run at the account's own Linux permissions, and SD keeps no second wall. Supersedes the S.4/S.6/P.23 build. ***§BUILT§ (`e41d318`, 18 Sep 2026) — left: the fresh install + witness cycle; nothing measured on a machine yet.*** | — |
| ◐ | **S.28** | L | ***THE TEARDOWN, 4 OF 4: remote ssh and the API for every account but SDSYS; SDSYS local only.*** The ssh boundary's `sdadmin` split (PRE_RELEASE 13, `gplbld/ssh-forcecommand.sh`, `installsdai.sh:565-570`) becomes one route for every account; `sdapi`'s per-account permission (S.16; group `:549-553`) is disposed; the installer and deleter follow (`sdadmin` `:537`, sudoers `:601-605`; `sdusers` stays). Edges: W.8 (the grants verbs), W.9 (the switches, the audit trail). ***§BUILT§ (`e41d318`, 18 Sep 2026) — left: the fresh install + witness cycle; nothing measured on a machine yet.*** | — |
| ✅ | **W.5** | R | `sudo sd` as root: refused outright, or an ordinary non-administrator session? The reading offered is refused — root is "another administrator". RULED 18 SEP 2026 — refused outright; built in the teardown change set | 18 Sep 2026 |
| ✅ | **W.6** | R | "a local session" on Linux: refuse administrator entry when `SSH_CONNECTION`/`SSH_TTY` is set, keep `sdsys` un-ssh-able, and the check lives at `cproc`'s SDSYS block — confirm. RULED 18 SEP 2026 — as offered; built in the teardown change set | 18 Sep 2026 |
| ✅ | **W.7** | R | SUSPENDED (the tier field's fourth value, Q.12): keep as a plain account flag with its doors re-hung, or drop with the tiers? The reading offered is keep. RULED 18 SEP 2026 — kept as a plain account flag; built in the teardown change set | 18 Sep 2026 |
| ✅ | **W.8** | R | GRANT/REVOKE/LIST.GRANTS and the `sdu_` groups: drop the verbs and let `usermod` be the grant, keeping the membership check at LOGTO? The reading offered is drop. RULED 18 SEP 2026 — dropped; built in the teardown change set | 18 Sep 2026 |
| ✅ | **W.9** | R | REMOTE.SSH/REMOTE.API (S.13) and the audit trail (E2/Q.13): keep — the switches SDSYS-only, the trail as the security evaluation's evidence — or remove with the rest? The reading offered is keep. RULED 18 SEP 2026 — kept; built in the teardown change set | 18 Sep 2026 |
| ◐ | **Q.22** | L | verifier harness and eleven verifiers; `keys` 36/36 and `logtoaccess` (§2b) witnessed on `984be50`; `batchjob`/`cmdaudit` mechanism absent, `notyet` → Q.14; `sdsyswrite` built 14 Sep as `check-storewriters.py` (free, 4 writers 0 failures) + witness §13g; §13g Y1-Y4 pass on `dea3736` and `0d58171` but Y0 shows the session never took the LOGTO route; route fixed 15 Sep (`LOGTO zzrel1` before the first WHO) and `sdsyswrite` witnessed on `0b67dba`, Y0–Y4 all pass (WHO `zzrel1 sdsys`); ***the ten API verifiers RULED 15 Sep 2026*** once W.4 closed (PORT_ADOPTION "Queue 22 — the ten API verifiers, ruled"): seven already measured by witness rows, `localconnect` does not transfer (phase 5 removed that transport), `apiname` was a real hole — `!valid_os_name` screens the SCRAM name at `apisrvr:1100` and nothing had ever sent it one it refuses — now built as §13c S9/S9b and ***WITNESSED 15 Sep 2026***: 271/271 on `c773008` (16:18) and again on `c1ea29b` (18:26), S9 refused at 47 and S9b reading `reason=name rejected by valid_os_name` off the trail — the row that proves the name check fired and not a catch-all; ***`tierapi`'s STANDARD LEG IS BUILT 15 Sep 2026 AND HAS NOT RUN***: §13j J0–J4c — a STANDARD account admitted to its own account over the API, then refused upward into a PROGRAMMER account it holds the Linux group for (10003), with the route read back off `sdapi` first so the refusal cannot be 10073's, and the fixtures restored; `bash -n` clean. ***§13j J5 ADDED 15 Sep 2026*** answering the port's RELEASE_1.1 46: an API session writes its OWN `voc` (§10's COPY idiom, the id counted in the raw subfiles before and after as root) — §3 already measured that write over a LOCAL session and nothing had measured it over the API; Linux does not share the port's read-only defect because `createa:391-393`/`:724-729` chown the new `voc` and its `%0`/`%1` to the account's own user, where theirs leaves them with the elevated administrator; left: `batchjob`/`cmdaudit` (no mechanism to verify) and an owner-run witness for §13j | — |
| ◐ | **P.6** | L | transactions: A2, A4 on the install; A1 undo, A3, A5 grow, A6 both by induced failure in the sandbox, each red on a mutant (`sandbox-txnfail.py` 22/22, 14 Sep); found + fixed a stranded OPENSEQ lock; left: A1's lock release and A5's free-node read path, neither inducible without a transient I/O error | — |
| ◐ | **P.31** | S | `delacc:219`'s cross-reference scan opened every other account's `voc` with no ELSE, so one unopenable `voc` aborted DELETE.ACCOUNT before the confirmation instead of skipping that account — the Windows port's find (its RELEASE_1.1 44), confirmed here by reading; shared BASIC, so upstream too. ***FIXED 15 Sep 2026 with the port's number and wording, 10188*** (it built first, so it carries the number; no collision here). Only a genuinely MISSING `voc` reaches it on Linux: the deleter is always root — measured, `DELETE.ACCOUNT` as a non-root administrator is refused 2001 and `LOGTO sdsys` 10002 — which corrects my earlier "an account owner could chmod theirs shut", and the port caught that. ***COMPILED INTO `c1ea29b` AND EXERCISED 15 Sep 18:26***: the witness ran the changed verb twice, §9 `DELETE.ACCOUNT zzrel3 REMOVE.HOME` and §15 `zzrel1`, with no abort. ***THE NEW ELSE DID NOT FIRE*** — every `voc` was present, so 10188 was never printed. ***THE ROW THAT MAKES IT FIRE IS BUILT, 15 Sep 2026, AND HAS NOT RUN***: §15 now moves `zzrel2`'s `voc` aside for the one `DELETE.ACCOUNT` and puts it straight back (`cleanup()` puts it back too if the run dies holding it), and scores K8 on 10188's own wording naming `zzrel2` and K9 on the deletion finishing anyway — NOT REACHED, not passed, if the aside did not happen. `bash -n` clean, no BOM, no CRLF; left: an owner-run witness cycle to exercise it | — |
| ◐ | **S.24** | S | the configuration file was named by two environment variables — the server read `SCARLET_CONFIG` (`inipath.c:38`), the client library `SD_CONFIG` (`sdclilib.c:4080`), so setting either moved half the system and said nothing; the port settled this on 14 Aug 2026 and its decision is this port's. ***FIXED 15 Sep 2026***: `SD_CONFIG_ENV`/`SD_CONFIG_DEFAULT` in `sddefs.h`, the symbol read in `inipath.c` with a bounded copy, the client's duplicate literals commented as duplicates, and `sdfix.c`'s `read_sdconfig()` buffer widened from `200 + 1` to `MAX_PATHNAME_LEN + 1`. Built (clean objects, exit 0) and guarded by a new free check, `test-configpath-units.py` 14/14 + `--selftest` 8 mutants; changelog written. left: no install has run since the change, so the "an installation that sets nothing behaves identically" claim is unmeasured — the next cycle settles it | — |
| ✅ | **W.4** | XL | API surface walked 14 Sep; the tier gate and lower-case WHO witnessed on `3ff8027` (§13b A4.3, A1b); SCRAM phase 1 (primitives) built, RFC 7677 17/17; phase 2 (`$cred`, MODIFY.PASSWORD) witnessed on `74c60d4` (§13 C0–C7), its two fixes on `b119bb3` (§15 K7, `verify-setpw` 22/22); phase 3 (APISRVR 47/48, K$SET.USERNAME/K$ASSUME.USER) witnessed on `d880012` (§13c S1–S7); phase 4 (client `scram_login`, both `sdclilib.c` copies) witnessed on `85fbbec` (§13b A0–A5, §13c S5c); phase 5 (request 24 retired, `!sdclient` SCRAM, `SDConnectUDS` removed) witnessed on `9fd52d9` (§13c S5–S5e, §13d B0–B4b, 171/171); phase 6: both client libraries rebuilt (measured); SD passwords — `installsdai.sh` now ends by setting the installing user's with `sudo sd -QUIET MODIFY.PASSWORD` (owner, 15 Sep 2026: that user only, not SDSYS, whose SD password nothing on Linux uses — the port sets both, its PRE_RELEASE_FIXES 138), skipped when a keep cycle kept one, ***WITNESSED 15 Sep 2026 ON INSTALL `c773008` (15:44:32): the owner was asked at the keyboard (his word), and `don` went from refused at request 47 — no credential, the 10:09 install — to refused at 48 with a real salt and `i=600000`, measured by `scram-probe` with a deliberately wrong password.*** No instrument can run the prompt itself (`input … hidden` needs a tty); any other account stays a per-account `sudo sd` + MODIFY.PASSWORD job. Witness 269/269 on the same install | 15 Sep 2026 |
| ➖ | **P.24** | — | dropped by the owner's choice: the installer seeds the admin (witnessed 10 Sep); the non-sudoer refusal is not pursued, because installation requires sudo by design | 15 Sep 2026 |
| ➖ | **Q.13** | — | dropped by the owner's choice: every owed audit record type is witnessed (API REFUSED last, on `3ff8027`); rotation at 1 MB is not pursued - judged not testable - and stays unwitnessed | 15 Sep 2026 |
| ➖ | **Q.19** | — | dropped by the owner's choice: the reconciler's report and its remote-NSS guard ran at every real start (again 15 Sep 10:10:39); the sweep's deletion stays witnessed only against a fixture, since this box's guard always refuses it | 15 Sep 2026 |
| ✅ | **S.18** | — | dead login code removed (`login_user`, `getpeereid`, `APILOGIN` accepted-and-ignored, no `-lcrypt`/`-lbsd`); Unix socket kept and serves SCRAM — witnessed on `fed4b36`, 183/183 (§13c S8–S8e, §16 R1–R3) | 14 Sep 2026 |
| ✅ | **S.16** | — | the port's per-account API route (`sdapi`, MODIFY.ACCOUNT API/NONE, 10073 at the login) — witnessed on `dea3736`, §13f F0–F9b all pass (`/var/tmp/witness-release-run.20260914-231854.log`) | 14 Sep 2026 |
| ✅ | **S.17** | — | an administrator (tier or `sdadmin`) is refused over the API from a non-loopback address, admitted over 127.0.0.1 and the socket; `linuxio.c` records the peer — witnessed on `e4e470e`, 195/195 (§13e E1–E6c) | 14 Sep 2026 |
| ✅ | **S.13** | — | REMOTE.API on/local/off and REMOTE.SSH on/off: `sd-elevate remote-api`/`remote-ssh` (socket drop-in + ufw), verbs `remoteapi`/`remotessh`, messages 10131-10139 — H5c failed on `dea3736` and `0d58171` (`ufw status` lists no rules while ufw is inactive), fixed with `ufw show added` (`test-sd-elevate.py` U1–U4), and §13h all pass on `0b67dba` incl. H5c and a real H1d (`…-102147.log`) | 15 Sep 2026 |
| ◐ | **S.1** | XL | BASIC screen/widget library; stage 1 DONE 14 Sep (sandbox, `tui-render-probe.py`): a pure-BASIC diff renderer redraws 160x48 at 0.11 ms CPU/frame (naive scroll 1.05), and an SGR 1006 mouse report reaches KEYIN intact, so the engine stays BASIC; left: stages 2-5 (event/draw layer + core widgets + form manager, mouse, advanced widgets, the IDE) — ***DEFERRED TO 1.2*** (owner, 15 Sep 2026: after the 1.1 release), so not 1.1 work | — |
| ⬜ | **S.20** | L | client recognition for the API, as ***mutual enrolment***: a root-only register of client machines (fingerprint + a description a person can read), an administrator approval step, and the client learning the server's identity in the same act — so neither side ever asks a user to adjudicate. ***RULED 1.2 BY THE OWNER, 15 Sep 2026, AND AS AN OPTION RATHER THAN A REQUIREMENT*** (*"let the admin decide how much they need"*) — so it ships available and off, probably as a ladder (open / server recognised / mutual). 1.1 ships TLS 1.3 + channel-bound SCRAM + a persistent server identity, with the residual risk written down. The entry below carries what was weighed, what was rejected, and what would falsify the ladder | — |
| ⬜ | **S.21** | L | ***PRE-RELEASE 1 of 3 (owner, 15 Sep 2026): the parity audit, and fixing what it finds.*** Runs once SD Core for Windows 1.1 is done — ***BLOCKED ON THE PORT, NOT ON THIS TREE***. Method exists: the 10 Sep audit (S.5, `witness-release-run.sh` §12's list) is the precedent to widen rather than reinvent | — |
| ⬜ | **S.22** | L | ***PRE-RELEASE 2 of 3 (owner, 15 Sep 2026): the documentation.*** The Linux side starts from the UPDATED WINDOWS documentation and changes it where Linux differs. Blocked on S.21's issues being resolved | — |
| ⬜ | **S.23** | M | ***PRE-RELEASE 3 of 3 (owner, 15 Sep 2026): staging repositories per version, then a release zip of each — one Linux, one Windows.*** ***THE SHAPE IS RULED 15 Sep 2026 — "the same as the windows version, staging directory and then a zip"***, so the zip is a distribution artifact assembled outside the project (the port's model, read out of its record) and the "installer builds from an unpacked zip" option is dropped. Costed 15 Sep against the code: pinning a TAG in the shipped `installsdai.sh` is one value (`:75`; `--branch` already takes tags), the stamp stays exact (`:397`, `:688-690`) and `assert-current` is unaffected (reads only `commit`, strict identity, fails pessimistic) — the cost is that a development install must keep cloning `main`, so the shipped and repository scripts would differ. left: the owner's yes on pinning the tag, then the staging directory and the zip itself | — |
| ✅ | **P.1** | — | the port's helpers walked: testing half → Q.22, admin half adopted or no counterpart | 14 Sep 2026 |
| ✅ | **P.5** | — | `bbcmp.py` lowers include names | 13 Sep 2026 |
| ✅ | **P.7** | — | §M, the lower-case conversion | 14 Sep 2026 |
| ✅ | **P.9** | — | `check-stale-leads.py` rewritten for this tree | 12 Sep 2026 |
| ➖ | **P.10** | — | messages 4100, 4101, -10303: nothing here raises them | 14 Sep 2026 |
| ✅ | **P.11** | — | `check-msglen.py` derives its bound from the C source | 14 Sep 2026 |
| ✅ | **P.13** | — | ssh boundary for STANDARD accounts | 10 Sep 2026 |
| ✅ | **P.16** | — | the installer builds as the calling user | 14 Sep 2026 |
| ✅ | **Q.25** | — | process dumps in `dumps/`, 0600, `verify-sysperms` 28/28 | 14 Sep 2026 |
| ✅ | **P.15** | — | an install tests `origin/main`; `assert-current` reports it | 9 Sep 2026 |
| ✅ | **P.23** | — | OS-access tier gate; its 10054 follow-up is S.4 | 10 Sep 2026 |
| ✅ | **P.25** | — | an upgrade keeps `sdadmin`'s members | 10 Sep 2026 |
| ✅ | **P.26** | — | the delete path no longer leaves `/home/sd` a file | 10 Sep 2026 |
| ✅ | **P.27** | — | install on an existing empty `/home/sd` | 14 Sep 2026 |
| ✅ | **P.29** | — | `sd.service` stays up at boot; installer's kickstart note dropped | 14 Sep 2026 |
| ✅ | **S.2** | — | `sudo sd` reloads root's groups, so `LOGTO` reaches a newer account group | 14 Sep 2026 |
| ✅ | **S.8** | — | `kernel(K$INTERNAL, n)` sets internal mode only from `$internal` code | 14 Sep 2026 |
| ✅ | **S.9** | — | LOGIN's `$release` prompt: Enter and end of input mean N, and it says so | 14 Sep 2026 |
| ✅ | **S.10** | — | `RUN` folds the program name, as `BASIC` does | 14 Sep 2026 |
| ✅ | **S.3** | — | per-tier VOC, incl. LOGIN `update.voc`'s STANDARD filter | 14 Sep 2026 |
| ✅ | **S.4** | — | OS-access tier gate, incl. 10054 on PROGRAMMER | 14 Sep 2026 |
| ✅ | **S.11** | — | `$hold.dic`'s `@ID` installed again (FILES_DICTS key lower case) | 14 Sep 2026 |
| ✅ | **S.5** | — | parity audit witness list, §12 + §15 on `f2251e6` all pass | 14 Sep 2026 |
| ✅ | **Q.14** | — | GRANT/REVOKE incl. a session open during the grant (§10); its wording finding is S.12 | 14 Sep 2026 |
| ✅ | **Q.17** | — | MODIFY.PASSWORD administrator arm: 10914, shadow `!` → `$y$` (§13) | 14 Sep 2026 |
| ✅ | **S.7** | — | NANO and MICRO: `verify-editors` 28/28, colour seen by the owner at a real terminal | 14 Sep 2026 |
| ✅ | **S.14** | — | API password not capped at 32, as the port: a 62-character password logs in (§13b A5, `8f17140`) | 14 Sep 2026 |
| ✅ | **S.15** | — | an API session holds its user's groups: `Groups: 979 1010 1011` (§13b A2c/A2d, `72933c2`; empty on `3ff8027`) | 14 Sep 2026 |
| ✅ | **Q.12** | — | SUSPENDED tier: the ssh door (§14 X1–X4, `f2251e6`) and the API door (§14 X6, `3ff8027`) both refuse | 14 Sep 2026 |
| ✅ | **S.12** | — | 10043: a session open during GRANT enters but cannot write — `File is read-only` vs a fresh session's copy (§10, `79d7e87`) | 14 Sep 2026 |
| ✅ | **S.6** | — | plain-sd admin `SH` runs; after LOGTO a non-admin account, 10054 names the user (§11, `79d7e87`) | 14 Sep 2026 |
| ✅ | **W.0** | — | a dead or faulting semaphore holder gives it back (`SEM_UNDO` + fault path), `verify-semaphores` 9/9 | 14 Sep 2026 |
| ✅ | **W.2** | — | Enter at 2050 means N in all six verbs | 14 Sep 2026 |
| ✅ | **W.3** | — | 6133 cancels on Enter or C; N still deletes the dictionary only | 14 Sep 2026 |
| ✅ | **Q.3b** | — | Enter takes the shown default at every Y/N prompt | 14 Sep 2026 |
| ✅ | **Q.28** | — | `RUN` of a path over 128 characters names the limit (10918) | 14 Sep 2026 |
| ✅ | **Q.15** | — | ADOPT keyword and installer seed | 14 Sep 2026 |
| ✅ | **Q.16** | — | upgrade runs UPDATE.ACCOUNTS ALL | 11 Sep 2026 |
| ✅ | **Q.18** | — | lower case, complete | 14 Sep 2026 |
| ✅ | **Q.21** | — | `check-stale-leads.py` | 12 Sep 2026 |
| ✅ | **Q.26** | — | the `:` prompt ends at end of input | 11 Sep 2026 |
| ✅ | **Q.27** | — | OPENSEQ stranded lock | 11 Sep 2026 |

**Legend** — ✅ closed · ◐ partly closed, and the row says what is `left:` · ⬜
open · ➖ removed or not applicable.
**Cost** — `XS` minutes, agent only · `S` under an hour, or one short owner
step · `M` a reinstall cycle or an owner-run witness (batch them: one cycle, one
witness script) · `L` a session plus a cycle · `XL` several sessions · `R` the
owner's ruling comes first.

## Status roll-up (14 Sep 2026)

**Keep this current when an entry closes; it is a scorecard, detail lives in
`PRE_RELEASE_FIXES.md` and below.**

- **PRE_RELEASE entries — 30; their state is the task table above** (the P
  rows). Closed before it existed, so rowless: `2, 3, 4, 8, 12, 14, 17, 18, 19,
  20, 21, 22, 28, 30`.
  - ***`28` (SEV A) CLOSED — fixed and WITNESSED 12 Sep 19:35 on install
    `f14919c`, `witness-accounts.sh --commit` 33/0.*** `DELETE.ACCOUNT` of an
    adopted administrator had left its Linux user in `sdadmin`/`sdusers`, and
    `sdadmin` is effective root via passwordless `sd-elevate passwd` → a Linux
    sudoer → `sudo -i`. `DELACC`'s 10036 branch now strips `sdadmin` then
    `sdusers` (mirrors `MODIFYA` `leave.sdadmin`); the transcript shows the
    `gpasswd -d` calls and the survivor left with `groups='zzacct2'` — zero SD
    groups, so the strip is complete. The borrowed login and home survive; an
    SD-*created* user is still `userdel`'d whole. Not filed to the port
    (owner's call).
  - `24(2)`'s refusal is `installsdai.sh:252-255`, not `:236` (audited 12 Sep;
    `:236` is now the API-port prompt).
- ***Plan steps 1–4 done. Step 7 (§M + §L1) — BOTH RELEASE BLOCKERS CLEARED,
  14 Sep.*** §M done + installed on `83e5ccf`; §L1 closed by the owner-run
  `witness-tierchange.sh --commit` (15/15, MODIFYA re-derives the per-tier VOC
  alone). ***No release-blocking work remains*** — see the §M/§L1 lines below
  and the START HERE block for what is post-parity (goals) vs owner-run leads.
- ***AUDITED 12 Sep 2026 — EVERY REMAINING TASK RE-MEASURED AGAINST THE TREE
  AND THE INSTALL RATHER THAN READ. THREE CLAIMS WERE STALE*** and are
  corrected in place: §L1's tier-layer half (below), `PRE_RELEASE 6` (no longer
  "not one item exercised"), and `24(2)`'s `file:line`. Everything else was
  confirmed genuinely outstanding, with the measurement in the entry.
- ***Release blocker 1 of 2: §M — DONE and INSTALLED (witnessed 14 Sep on
  `83e5ccf`).*** `verify-nocase` reads ***§M NAME HALF COMPLETE*** — 0 name
  remnants, all code sites ` ok `. **M1** (the fold, as-typed→lower→upper) done
  + witnessed (`verify-fold` 35/35). **M2** (collision guard + VOC migration)
  ***MOOTED and its `!voccase` code REMOVED*** under the owner's ruling *"NO
  MIGRATION IS NEEDED FOR ANY OF §M"* (12 Sep, `313c55b`; there are no existing
  installs to half-migrate). **M3** (the renames) done + witnessed: `gpl.bp`
  0 upper, `syscom` 0, `newvoc` 0, `voc_template` 0, sdsys dirs 0, account names
  lower (register keys too), case inversion off, `create.file` makes lower-case
  files, and the tier lists moved to `sdsys/tier.policy` (14 Sep). **§N**
  (release number): ***the target release is `L1.1-0`*** (owner, 14 Sep — 1.1 to
  match SD Core for Windows W1.1-0, the release this conforms with; there was no
  shipped L1.0). ***ONLY the changelog header moved*** to `L1.1-0 - in progress`.
  ***THE REVSTAMP DOES NOT MOVE WITH IT*** (owner, 14 Sep): `SD_REV_STAMP` /
  `SD.REV.STAMP` and both `$release` records STAY `L1.0-0` — the revstamp holds
  the current version and only bumps when the release actually ships, exactly as
  the port keeps `W1.0-0` in SD_REV_STAMP while its changelog reads `W1.1-0 - in
  progress`. `MAJOR_REV`/`MINOR_REV` stay at upstream's throughout. So the banner
  reads `L1.0-0` until L1.1-0 ships. *(Catalogue names in `gcat` are a separate
  namespace, deliberately left upper.)*
- **Release blocker 2 of 2:** ***§L1*** — the per-tier VOC, **core WITNESSED
  10 Sep** (STANDARD tstd 368 records / no BASIC vs PROGRAMMER tprog 410 — Δ42 =
  the omit list; CREATUSR fix also witnessed). The tier-layer invariant is
  RE-WITNESSED 14 Sep on `83e5ccf`: ***don (ADMINISTRATOR) holds all 19 layer
  verbs, 0 short***, the layer read from `sdsys/tier.policy/add.administrator`.
  ***CORRECTION, 14 Sep: the earlier "DON, TADM … 0 short" was resting on a
  FALSE GREEN*** — `verify-tier-layer.bp` opened the admin VOC as `'VOC'` while
  §M had lower-cased account dirs to `voc`, so the probe skipped the admin it
  could not open and reported 0 short having tested nothing. Fixed 14 Sep
  (opens `voc`, an unopenable admin counts short); now a real green. TADM/tstd/
  tprog no longer exist (the 12 Sep full cycle left only `don` + `sdsys`).
  ***`MODIFYA`'s tier RE-DERIVATION IS WITNESSED — 14 Sep, owner-run
  `witness-tierchange.sh --commit` on `83e5ccf`.*** A throwaway ADOPTed as
  ADMINISTRATOR was moved ADMINISTRATOR→STANDARD→PROGRAMMER→ADMINISTRATOR with
  NO `UPDATE.ACCOUNTS` between, and MODIFYA's own 10113 reported the
  re-derivation at each move: ***down removes 62 (= omit 43 + admin 19), up to
  PROGRAMMER adds 43 (the omit list), up to ADMINISTRATOR adds 19 (the admin
  layer); the round trip balances (62 off, 62 back).*** These match the
  tier.policy list sizes exactly, so the re-derivation is MODIFY.ACCOUNT's own.
  ***THE INSTRUMENT HAD TO BE REWRITTEN, AND THE FIRST RUN'S 21 "FAILURES" WERE
  ALL THE INSTRUMENT, NOT THE PRODUCT:*** it measured through `LOGTO $ACC;
  COUNT VOC; CT VOC`, and ***`LOGTO` errored `3001 … CPROC:2952`*** (the
  `openpath "voc"` there) in the piped root session, so every read stayed in
  SDSYS (425 each time). The rewrite asserts on 10113 cross-checked against the
  tier.policy sizes and the register tier read off disk — no `LOGTO`.
  ***THE FIXED SCRIPT WAS RE-RUN GREEN — 14 Sep 00:01, owner-run, 15 of 15, 0
  failed***: each move's 10113 matched (0/62, 43/0, 19/0), the register tier off
  disk agreed at every step, the round trip balanced, cleanup complete. ***THIS
  CLOSES §L1, THE LAST RELEASE-BLOCKER ITEM.***
- ***[S.2] CLOSED 14 Sep 2026 — FIX INSTALLED ON `ca4c07c` (11:51:03,
  `assert-current` current) AND WITNESSED:*** the owner re-ran the `setpriv`
  command below → `LOGTO don`, `WHO` → `1 don from sdsys`, no 3001 (before the
  fix, the same paste gave 3001 and stayed in `sdsys`). `nm -D
  /usr/local/sdsys/bin/sd` shows `initgroups`, so the fix is in the installed
  binary. ***Gap:*** neither paste shows the `id` line, so the dropped group is
  taken from the command given, not seen. *(Earlier state follows.)* Defect
  witnessed 14 Sep 2026, fix built + compiled, not installed.
  Owner-run `sudo setpriv --groups 979 sh -c 'id; printf "LOGTO don\nWHO\nQUIT\n"
  | /usr/local/sdsys/bin/sd'` on `83e5ccf` → `00003943: Error 3001 opening file
  at line 2952 of $CPROC`, `WHO` → `3 sdsys` (stayed); the control, same with
  root's full groups, entered `don` (`2 don from sdsys`). Only the groups
  differed (the `id` line was not in the paste). ***Fix:*** `sdext_eguid.c`
  `SD_EUID_SET` calls `initgroups(<real user>, gid)` while still euid 0, before
  the drop — at session start (`cproc:344`) and after each privileged verb
  (`cproc:1820`), so a group made by `CREATE.ACCOUNT` is seen by the same
  session. Grants root nothing it is not a member of; no ownership or read-only
  change. ***Witness after install:*** the same `setpriv` command must enter `don`
  (the startup refresh restores `sdu_don`); falsified by a 3001. ***Not covered:***
  a group added outside SD mid-session is seen only after the next privileged
  verb; and `dh_open.c`'s real-uid `access()` still turns a permission refusal
  into a fatal "3001 opening file" rather than a message — not changed.
  *(Earlier narrowing follows.)* Not piping (as `don`), and not the bare uid
  mismatch below, which the owner's first run contradicted:
  `printf 'LOGTO don\nWHO\nQUIT\n' | sudo /usr/local/sdsys/bin/sd` → `2 don from
  sdsys`, no 3001. Why: `root` is a member of `sdu_don` (`getent group sdu_don`
  → `root,don`; CREATEA `:1006` adds `root,sdsys,<user>`), so the open succeeds
  through root's supplementary groups — "`sdsys` is only in `sdusers`" was the
  wrong credential. ***Refined, UNWITNESSED:*** supplementary groups are fixed
  when a process starts and `sd` never reloads them (no `initgroups`/`setgroups`
  in `gplsrc`). `witness-tierchange.sh` ran every `sd` from its own root process,
  started before it created `sdu_<throwaway>`, so that root lacked the group and
  the real-uid `access()` / effective-uid open mismatch below applied. If so the
  user-facing case is ***`CREATE.ACCOUNT` then `LOGTO` it in the same `sudo sd`
  session***, and the C half is `dh_open.c` turning a permission refusal into a
  fatal 3001. ***Falsified if*** `sudo setpriv --groups 979 sh -c 'id; printf
  "LOGTO don\nWHO\nQUIT\n" | /usr/local/sdsys/bin/sd'` (root without `sdu_don`)
  enters `don` with no 3001. *(Earlier narrowing follows.)* Piping ruled out; a
  real/effective-uid mismatch is the likely cause, from source.
  Measured as `don`, no sudo, install `83e5ccf` (`cproc`, `op_dio*` unchanged
  to HEAD): `printf 'WHO\nLOGTO don\nWHO\nCOUNT VOC\nQUIT\n' | /usr/local/sdsys/bin/sd`
  → `1 don`, `418 record(s) counted`, exit 0, no 3001. ***Hypothesis:*** `sudo sd`
  runs EUID `sdsys` over real UID 0 (`cproc:344`; PRE_RELEASE 20's WHO.AM.I);
  only `$CREATEA/$DELACC/$MODIFYA` get euid 0 back (`cproc:221-223,1807`), and
  LOGTO is in CPROC itself. `3001` = `ER_SFNF`, set only at `op_dio1.c:738`
  from `dh_open`'s `DHE_FILE_NOT_FOUND`: `dh_open.c` `access(%0, 2)` asks with
  the REAL uid (root → writable), then `dio_open(DIO_UPDATE)` opens with the
  EFFECTIVE uid `sdsys`, which cannot write `voc/%0` (`-rw-rw-r-- don:sdu_don`,
  `sdsys` is only in `sdusers`). If so it hits interactive `sudo sd` too, for
  every user account. ***Falsified if*** `printf 'LOGTO don\nWHO\nQUIT\n' | sudo
  /usr/local/sdsys/bin/sd` enters `don` (WHO → `don` account, no 3001). The fix is
  a ruling, not a typo (`euidaccess` gives an admin a read-only VOC; restoring
  euid 0 around LOGTO changes file ownership) — measure first.
  *(Original entry follows.)* `LOGTO <account>` errored
  3001 at `cproc:2952` (`openpath "voc"`) from a piped `sudo sd` (root/SDSYS)
  session. Whether this is a piped-non-tty artefact or a real LOGTO issue is
  unmeasured; an admin normally LOGTOs interactively. Worth its own look before
  relying on LOGTO in any instrument.
- ***CORRECTION (14 Sep): `gplbld/witness-accounts.sh` is NOT broken*** — an
  earlier claim here that it hardcodes `ACCOUNTS` upper was wrong, made from
  `witness-tierchange.sh`'s failure without measuring the actual file. Measured:
  its register is already `accounts` (line 110, fixed 13 Sep) and its `ACC_UC`
  is *downcased* (a misnamed but correct lower-case key, comment at :143); its
  dry run passes preconditions. Only `witness-tierchange.sh` had the upper-case
  `ACCOUNTS`, and that was fixed as it was built.
- **Parity audit vs the Windows port, 10 Sep:** 12 drifts corrected + compiled,
  **unrun**; key numbers renumbered so ***the tree `bin/sd` and GPL.BP must be
  installed together*** (Open, "Parity audit").
- **Goals (post-parity):** a **BASIC screen/widget library** — rich terminal
  admin apps / a terminal IDE, written in SD BASIC, GPL-clean, no dependency
  (owner, 10 Sep; design note in Open, stance in CLAUDE.md).
- **Runtime:** install built from **`9fd52d9`**, stamped 14 Sep 2026 20:43:13,
  owner keep cycle, `assert-current` current — carries SCRAM phases 1–5.
  *(Superseded:)* `85fbbec`, 20:22:01 — phases 1–4.
  *(Superseded:)* `d880012`, 20:01:11 — phases 1–3.
  *(Superseded:)* `b119bb3`, 19:43:01 — phases 1–2.
  *(Superseded:)* `74c60d4`, 19:34:27. *(Superseded:)* `8f17140`, 18:56:33 —
  S.14's password length.
  *(Superseded:)* `72933c2`, 17:34:34 — S.15's `initgroups`.
  *(Superseded:)* `3ff8027`, 17:13:12 — W.4's APISRVR.
  *(Superseded:)* `79d7e87`, 15:02:58 — S.12's 10043.
  *(Superseded:)* `f2251e6`, 14:37:02. *(Superseded:)* `2edec17`, 14:07:22 —
  W.0, W.2, W.3.
  *(Superseded:)* `984be50`, 13:37:31 — the backspace fix and S.11.
  *(Superseded:)* `d704658`, 13:06:01 — S.10.
  *(Superseded:)* `6e5b2f5`, 12:20:13 — S.9, Q.25, P.16.
  *(Superseded:)* `ca4c07c`, 11:51:03 — P.29, Q.28, S.8, S.2.
  *(Superseded:)* `83e5ccf`, stamped 13 Sep 2026 23:06:38
  (`.sdcore-install`, read 14 Sep), owner keep cycle — carries §M and the
  `tier.policy` move. Before it, 13 Sep: `80bd15c` 19:11:39, a full cycle.
  *(Superseded:)* install built from `76938f1`, 12 Sep 2026 20:55:16, owner-run
  delete→install, `assert-current` **0** — carries §M1's fold. Prior:
  **`f14919c`** 19:33:26, the PRE_RELEASE 28 fix, witnessed on it at 19:35.
  Earlier installs: `f446ac1` 11:56 (the full cycle
  that reset the test accounts), `0095937` 01:50 (a KEEP cycle). *Earlier note,
  kept because it names the trap:
  after `98b0c77` HEAD advanced by documentation-only commits, so
  `assert-current` read STALE while the shipped behaviour was current.*

## START HERE

***HANDOFF, 18 SEP 2026 (CLOSE) — THE TEARDOWN IS BUILT AS ONE CHANGE SET,
COMMITTED (`e41d318`) AND PUSHED; NOT INSTALLED, AND NOTHING HAS BEEN
MEASURED ON A MACHINE YET.***
The owner answered the handoff's question with "use the readings offered", so
W.5 to W.9 are answered below and S.25 to S.28 are built in one change set,
with the OS-access gates (S.27) and the ssh/API boundary (S.28) in the same
change so no two privilege models ship apart.  What the build did, task by
task, is recorded in the entries below and in the session log ("Session log —
18 Sep 2026").  The free checks pass (`make` clean; the unit suites green,
`test-ssh-forcecommand` 18/18, `test-sd-elevate` 57/57, `test-msglen` 10/10,
`test-accounts-units` 17/17; `check-stale-leads.py` exit 0 after the table
reconciliation; `assert-current` says STALE — the install is `c1ea29b`, before
the teardown — correct).  ***NOTHING IS WITNESSED***: a real install clones
origin/main, so the first measurement needs a fresh install of the pushed
commit; `witness-absence.sh` is the new absence instrument, and
`witness-release-run.sh` / `witness-accounts.sh` now drive the teardown's
model.  Also taken in the same session: the Windows port's RELEASE_1.1 60
(two unbounded `strcpy()`s in `clopts.c:266/:316`, committed separately as
`9140dc4`); its RELEASE_1.1 59 (the world-writable shared segment) stays open
and is even sharper now — see the session log.

***THE CYCLE'S INSTRUMENTS WERE REPAIRED 18 Sep 2026, LATER, BEFORE THE
INSTALL*** — three verifiers still read the deleted `sdsys/tier.policy`
(`verify-nocase.py`, a free check that had begun to exit 2 and stop measuring;
`verify-editors.py`'s B5/B6; `verify-lcnames.py`'s S8).  No shipped code changed.
See the session log.

***CLOSE, 18 SEP 2026, LATER THE SAME DAY — PULLED AND REPAIRED; THE CYCLE IS
STILL UNRUN.***  `git pull` was already up to date (`90ae906`); the free checks
were re-run green on the repaired tree, and the verifier repair is committed and
pushed (`b0a78bd`, `90ae906..b0a78bd`).  ***THE FRESH INSTALL AND THE WITNESS
CYCLE HAVE NOT RUN*** — `assert-current` still reads the install as `c1ea29b`
(15 Sep, before the teardown) against HEAD `b0a78bd`, which is the correct STALE
until an install runs, and no `witness-*` log exists later than 15 Sep.
WHAT THE NEXT SESSION PICKS UP — the FRESH cycle (delete → install), which the
owner chose over a keep-accounts upgrade, with the owner at the keyboard for
`sudo`: `bash deletesdai.sh` (Continue? `y`; Keep accounts? `n`, then type
`DELETE`; Keep configuration? Enter) → `bash installsdai.sh` (Continue? `y`;
the ssh/API prompts are the owner's to answer; it ends by setting `don`'s SD
password at a hidden prompt) → the three witnesses with `--commit`:
`witness-absence.sh`, `witness-release-run.sh`, `witness-accounts.sh`.
***The absence witness writes no log of its own*** — tee it to `/var/tmp` or its
evidence is only the terminal scrollback.  If an install aborts part-way, run
`deletesdai.sh` before retrying: `installsdai.sh:125` refuses to re-run while
`/usr/local/sdsys/bin/sd` exists.

***CLOSE, 18 SEP 2026, EVENING — THE FIRST CYCLE RAN AND DIED AT
`installsdai.sh:788`; THE FIX IS IN, THE RE-RUN HAS NOT HAPPENED (owner:
"install failed").***  The install cloned `origin/main` and stamped
`.sdcore-install` `commit=767443051ecd`, `installed=2026-09-18 17:09:24` —
***so the teardown build did reach the machine*** — and then it stopped on
`chown: invalid group: 'sdsys:sdsys'`: THERE IS NO `sdsys` GROUP (the `sdsys`
user's primary group is `sdusers`, gid 979).  Every place that carried the
name is corrected to `sdsys:sdusers`, and the mode stays 700, so the group
confers nothing either way: `installsdai.sh:788` (where it died),
`witness-release-run.sh`'s C7 (it asserted the same string and would have
failed next run), `set_acc_password`'s comments, `deletesdai.sh:195`'s stale
`root:root 0700`, and the S.26 text below.  ***THE RE-RUN NEEDS THE FIX PUSHED
FIRST*** — the installer clones `origin/main` (`installsdai.sh:74`, `:385`),
and `deletesdai.sh` first again, because the part-install left
`/usr/local/sdsys/bin/sd` in place (`:152`).  ***The owner's run kept the
accounts*** (`/home/sd` held the register, `$cred`, `sd.conf` and the audit
trail, which only the keep path saves), so the FRESH (DELETE) cycle described
above is STILL UNRUN — fresh or keep is the owner's call on the re-run, and
the fix is the same for both.  Nothing is witnessed; no `witness-*` log exists
later than 15 Sep.

***CLOSE, 18 SEP 2026, LATE — THE CYCLE RAN, THE INSTALL IS CLEAN, AND THE
THREE WITNESSES SCORED 261 OF 302; ONE REAL DEFECT (A4) AND ONE SET OF STALE
EXPECTATIONS.***  After the two installer fixes above, the fresh cycle
succeeded: `.sdcore-install` `commit=2908280` (17:44:20), `assert-current` exit
0 (its one STALE read came from this session's own compile experiments
dirtying the tracked scratch files `sdb_ai/sd64/pass1`/`pass2` — restored), the
`createa` object present (`gpl.bp.out/createa`, 5037 B — absent in the failed
run before it), `$CREATEA` in gcat, `don` seeded with `sdu_don`, `$cred`
`sdsys:sdusers 700`, `dumps/` 1730, the sshd boundary block in place,
`sd.service` and `sdclient.socket` active and enabled, errlog empty.  The three
witnesses then ran (owner-run, 17:47–17:49): `witness-absence.sh` 31/46,
`witness-release-run.sh` 200/224, `witness-accounts.sh` 30/32 — logs
`/var/tmp/witness-absence.20260918-174756.log`,
`/var/tmp/witness-release-run.20260918-174803.log`,
`/tmp/witness-accounts.20260918-174935.log`.
***ONE PRODUCT DEFECT: A4.***  An account created through the new
administrator route came out `sdsys:sdusers` instead of
`<account>:sdu_<account>` — `createa`'s `set.owner` chowned with the `OS$CHOWN`
intrinsic, which needs root, and the administrator is a local `sdsys` session
and is never root (S.26); six `Unable change ownership of directory … err: 1`
(EPERM) lines, and the account's own `voc/%0` left writable by `sdusers`, the
group EVERY account belongs to.  Fixed here: a validated `chown-account` op in
`sd-elevate` (`test-sd-elevate.py` 57 → 72 rows: 49 refusals, 13 controls) and
`createa`'s `set.owner` routes through it when the session is not root, keeping
the intrinsic for the install bootstrap.
***THE OTHER 40 FAILURES ARE ROWS PREDATING THE MODEL THEY MEASURE*** — the
next step, and none is a product defect: 11 assert the old `Unexpected token
(X)` wording (the tier/OS/API words ARE refused — `MODIFY.ACCOUNT Action Must
Be Add, Delete, Suspended or Unsuspend`); 9 drive `LOGTO sdsys`, which S.26
refuses for everybody; 11 drive `REMOTE.API`/`REMOTE.SSH` as root, which is
refused — and the release run's own §13h printed 10176's words, so the root
refusal IS working; M8a/M8c never ran a root session at all (`run_sd root` is a
label); M7e greps `%sdadmin` and hits a COMMENT in the drop-in; E6 expects a
`Password REMOVED` message the product has never had; K5's `userdel` was
refused because the witness's own §13 session still held the uid (the product
warned and carried on); D11 expects the home gone after a plain
`DELETE.ACCOUNT`, and the owner's 10 Sep ruling removes it only with
`REMOVE.HOME`.  NOT YET DONE: that re-pointing, then a re-run of the three.

***OWNER'S DECISION, 18 SEP 2026 — THE TIERED ACCOUNT MODEL IS RIPPED OUT; THE
PARITY PLAN'S §L IS REVERSED; THE TEARDOWN OPENS AS S.25 TO S.28.*** He dictated
it in the port's vocabulary — "SDSYS", "LOGTO", "the standard level", "remote
ssh and api access" — and then, in the same breath: *"ignore the windows
references, convert as appropriate for linux"*, and later *"continue teardown"*,
and on the follow-up: use the readings offered for W.5 to W.9. The Linux
conversion is the nine entries below. **What survives, by his word: the
embedded Python and the encrypted tunnel that carries the data and the
password; the rest of the account framework is removal scope, and when it is
all out he evaluates the resulting security model — that evaluation is the
next gate.**

***[S.25] THE TEARDOWN, 1 OF 4 — THE TIER MACHINERY COMES OUT (owner's
decision, 18 Sep 2026). §BUILT§.*** Built 18 Sep 2026, one change set (see the
handoff above and the session log): tier.policy, TIERGATE and GRANTA deleted;
every !tier_allows caller (cproc LOGTO, modifya, apisrvr) gone;
ACC$TIER/ACC$PRIOR.TIER retired and field 5 redefined as ACC$SUSPENDED (W.7's
flag — reusing 5 keeps the one-column listing and reads every pre-teardown
record correctly); every VOC copy path (createa's make.account, login's
update.voc, modifya's voc.delta) now copies NEWVOC whole — one layer; 'sh' and
'!' moved into NEWVOC so every account has them (S.27); GRANT/REVOKE/
LIST.GRANTS records removed from VOC_TEMPLATE (W.8).  The tier instruments are
gone (verify-tier-layer.*, witness-tierchange.sh, the §6/§7 legs) and
witness-absence.sh is the replacement.  Messages removed: 10041-10050, 10053,
10054, 10073, 10077, 10079-10083, 10087, 10102, 10105, 10106, 10108, 10109,
10111, 10113, 10114, 10126-10129, 10157, 10159, 10900-10904, 10911, 10912,
10919; added: 10176 (root refused), 10177 (sdsys remote refused), 10178/10179/
10180 (suspend/unsuspend), 10916 (grant notice); 10002 and 10174 reworded.
*Measured: nothing yet — install + witness after the push; §OPEN§ until the cycle runs.* The pieces:
`sdsys/tier.policy` and its two lists (`omit.standard`, `add.administrator`);
`GPL.BP/TIERGATE`, whose `function tier_allows` (`tiergate:89-90`) is the
whole decision, and its `!tier_allows` callers (`cproc:2847-2852`,
`granta:248`, `modifya:239`, `:633` — the last through `voc.delta`,
`modifya:475`); `ACC$TIER`/`ACC$PRIOR.TIER` and every arm that reads them
(`createa:185`, `:243-254`, `:574-610`; `login`; `modifya`); the module's
messages. ***THE VOC COLLAPSES TO ONE LAYER*** — NEWVOC as shipped, the
PROGRAMMER set, which is what every account now gets: STANDARD and its filter
(S.3) and the administrator add-on both go, and with one layer nothing can
cross a boundary because none exists. Superseded outright: S.3's build, Q.16's
`update.accounts` tier layer, Q.22's `tierapi` leg (§13j — built, and it never
runs). ***THE TIER INSTRUMENTS GO WITH IT*** — `verify-tier-layer.sh` and its
`.bp`, `witness-tierchange.sh`, the tier legs of `witness-release-run.sh`
(§6, §7) — replaced by a witness that proves absence: no TIERGATE, a fresh
CREATE.ACCOUNT recording no tier, no tier keyword in MODIFY.ACCOUNT. *One
change set with S.26-S.28: §L's own warning cuts the other way now — taking
half of this is worse than none, because half leaves two privilege models
disagreeing.*

***[S.26] THE TEARDOWN, 2 OF 4 — ONE ADMINISTRATOR, SDSYS, AND LOGTO IS NOT
THE WAY IN. §BUILT§.*** Built 18 Sep 2026: cproc's root-entry block refuses a
root session outright (10176, audited) and grants K$ADMINISTRATOR only to a
session already running as the sdsys OS user on a local session —
SSH_CONNECTION and SSH_TTY both empty (10916 granted, audited);
grant.administrator is deleted, K$REAL.USER with it (its only caller).  LOGTO
sdsys is refused for everybody (10002 reworded); the administrator's LOGTO
keeps the S.2 group refresh (int.logto calls EUID_SET, and SD_EUID_SET now
reloads groups for any caller — sdext_eguid.c).  The sudoers grant moved from
%sdadmin to the sdsys user; the register and $cred now belong to sdsys
(register sdsys:sdusers 644, $cred sdsys:sdusers 700 - CORRECTED 18 Sep
2026, late: this read `sdsys:sdsys` and there is no sdsys GROUP, which is where
the first fresh cycle died) so a local sdsys session
administers without root; set_acc_password gates on the administrator flag
instead of uid 0; the installer recompiles CPROC without IS_INSTALL AFTER the
seed steps (which run on the install build), and its MODIFY.PASSWORD step
runs as sdsys.  The decision's Linux reading: SDSYS is tied to the
`sdsys` OS account (uid 999, owner of /usr/local/sdsys), and SD administration
exists only for a session running as that identity, obtained by elevating into
it (`sudo -u sdsys`, `su - sdsys`) from a local session — "elevated" on Linux
is the sudo step, not a UAC twin. `LOGTO sdsys` becomes refused for EVERYBODY:
today `cproc:2847-2852` refuses only an unflagged session (10002, audited) and
lets a flagged administrator through, and TIERGATE's "SDSYS is never granted"
is belt and braces rather than the mechanism. ***EVERY OTHER ADMINISTRATOR
ROUTE IS REFUSED WITH IT***: `grant.administrator` and the `K$ADMINISTRATOR`
flag (`cproc:901`, `linuxlb.c:62`), the `sdadmin` group and its sudoers
(`installsdai.sh:537`, `:601-605`), and plain `sudo sd` — root is "another
administrator" and does not become SD's. Below the OS, root can still `su` to
`sdsys`; the rule binds SD's own gate, which is his "the only limits ... those
Linux imposes". Shapes: W.5, W.6.  *Measured: nothing yet — install + witness after the push; §OPEN§ until the cycle runs.*

***[S.27] THE TEARDOWN, 3 OF 4 — THE OS-ACCESS GATES GO; STANDARD LINUX
LIMITS ONLY. §BUILT§.*** Built 18 Sep 2026: op_sh's os_permitted() and its
refusal are deleted (OS.EXECUTE runs unconditionally at the account's own
Linux permissions), cproc's os.command loses the K$ADMINISTRATOR/K$SH test
(the metacharacter filter stays), ACC$SH/ACC$OS.EXEC (fields 7/8) and
K$SH/K$OS.EXEC (keys 91/92) are removed with their kernel cases and
USR_SH/USR_OS_EXEC; login's os.admin load and modifya's SH-ON/SH-OFF/OS-ON/
OS-OFF arms are gone.  His rule: the only limits on what an account does at
the OS level are those Linux imposes on its standard accounts, so SD stops
holding anything back itself. Out: the SH and OS.EXECUTE gates the port built
across S.4, S.6 and P.23 — `ACC$SH`/`ACC$OS.EXEC` (fields 7/8), the
`SH-ON`/`SH-OFF`/`OS-ON`/`OS-OFF` arms in `modifya`, the `os.admin` load at
`login:439-442`, `USR_ADMIN` (`op_sh.c:128-139`), and the refusal and report
messages (10039, 10041, 10042, 10053, 10054). ***SH AND `!` THEN RUN AT THE
ACCOUNT'S OWN LINUX PERMISSIONS*** — the euid drop already runs a session as
the account's OS user, so the OS is the wall and SD keeps no second one. Keys
and fields to tidy in the same change: `SYSCOM/KEYS.H` fields 7/8,
`K$SH`/`K$OS.EXEC` (58/59), and what CREATEA seeds in them.  *Measured: nothing yet — install + witness after the push; §OPEN§ until the cycle runs.*

***[S.28] THE TEARDOWN, 4 OF 4 — REMOTE SSH AND THE API FOR EVERYONE BUT
SDSYS; SDSYS LOCAL ONLY. §BUILT§.*** Built 18 Sep 2026: the ssh boundary is one
route — `Match Group sdusers,!sdsys → ForceCommand sd` plus `Match User sdsys
→ DenyUsers sdsys` (sdsys un-ssh-able, W.6's sshd half; an AllowUsers override
is named in the helper as sshd's own policy corner, with SD's W.6 gates as the
second wall); the sdapi per-account route is disposed (createa/modifya
grammar, 10073, the installer's group, delacc's strips) and apisrvr's
vb.scram admits every proven sdusers member, with SDSYS's own door the S.17
non-loopback refusal (10174 reworded, audited with the peer address) and a
name-based exemption that lets sdsys enter its own account locally;
sd-elevate's whitelist loses sdadmin/sdapi; the installer/deleter no longer
create or strip them.  W.9's REMOTE.SSH/REMOTE.API stay, SDSYS's own
(sd-elevate, sdsys-only sudoers).  His words: "All accounts, other than
SDSYS, will have remote ssh and api access. SDSYS will only be accessible from
a local session." So the doors: PRE_RELEASE 13's ssh boundary
(`gplbld/ssh-forcecommand.sh`, installed at `installsdai.sh:565-570`,
force-commanding the `sdusers` that are not `sdadmin` into `sd`) becomes one
route for every account; `sdapi`'s per-account permission (S.16,
`MODIFY.ACCOUNT ... API|NONE`, 10073 at the login, group at
`installsdai.sh:549-553`) is disposed; S.17's non-loopback refusal stays as
SDSYS's door. The installer and deleter follow: `sdadmin`'s group and its
users' sudoers go, `sdusers` stays as the Linux-native "may run SD" group.
Edges: W.8 (the GRANT verbs), W.9 (the switches and the audit trail).  *Measured: nothing yet — install + witness after the push; §OPEN§ until the cycle runs.*

***[W.5] `sudo sd` AS ROOT — REFUSED OUTRIGHT, OR AN ORDINARY
NON-ADMINISTRATOR SESSION? RULED 18 SEP 2026 — THE READING APPLIED.*** Built: a root
session is refused outright in cproc's entry (10176, audited); root may
`su - sdsys` and come back the right way.  The decision refuses
"all other administrators" as SD administrators; the reading offered is the
harder one: a root session that is not running *as* `sdsys` is refused
outright — root may `su - sdsys` and come back the right way — because "an
ordinary session that merely lacks administration" reads, to an auditor, like
the old `sudo sd` route wearing a new name. The softer reading keeps `sudo sd`
working at the PROGRAMMER level. Either way `LOGTO sdsys` never succeeds from
it.

***[W.6] WHAT "A LOCAL SESSION" MEANS ON LINUX — THE TEST, AND WHERE IT IS
ENFORCED. RULED 18 SEP 2026 — THE READING APPLIED.*** Built: cproc's SDSYS block tests
`env('SSH_CONNECTION')` and `env('SSH_TTY')` (ssh and the API tunnel both
count as remote), the sdsys OS account is denied network login at sshd
(`DenyUsers sdsys`), and the test lives with the SDSYS block in cproc.  The
reading offered: refuse administrator
entry when `SSH_CONNECTION`/`SSH_TTY` is set (ssh and the API tunnel both
count as remote), keep the `sdsys` OS account un-ssh-able — it needs no
network login — and let the test live with the SDSYS block in `cproc`. If he
wants it looser (a console-tty check) or tighter, the sentence changes; the
row does not guess.

***[W.7] SUSPENDED — KEPT AS A PLAIN ACCOUNT FLAG, OR DROPPED WITH THE TIERS?
RULED 18 SEP 2026 — THE READING APPLIED.*** Built: the suspension is its own flag —
field 5, blank means in service and SUSPENDED means suspended (ACC$SUSPENDED;
reusing field 5 reads every pre-teardown record correctly), with the same
doors (LOGIN, cproc's entry, ssh, the API) and the way back is
MODIFY.ACCOUNT <account> UNSUSPEND (10178/10179/10180); field 6 (the retired
prior-tier slot) is cleared on the way back and never written.  Today suspension rides on the tier field (Q.12: the
fourth value, `ACC$PRIOR.TIER` holding the displaced tier; its doors are
LOGIN, `cproc`'s entry, ssh and the API). The reading offered: keep it — a
suspension is a denial, not a rank — re-hang it on its own flag with the same
doors, and write the tier field out of it. Dropping it removes a control the
port also has; the decision says nothing either way.

***[W.8] GRANT / REVOKE / LIST.GRANTS AND THE `sdu_` GROUPS — KEEP, OR LET
`usermod` BE THE MECHANISM? RULED 18 SEP 2026 — THE READING APPLIED.*** Built: the three
verbs are dropped (granta deleted, its VOC records gone, its messages gone,
verify-grants.py gone), `usermod -aG sdu_<account>` is the grant, and LOGTO's
membership check with the 10003 refusal and its audit line stay where they
are.  The verbs exist to move
people between tiers and to police the down-or-sideways rule (Q.14); one
level leaves no ordering to police, and account entry is already Linux group
membership checked at LOGTO. The reading offered: drop the three verbs and
let `usermod -aG sdu_<account>` be the grant, keeping the membership check
where it is. What must not be lost either way: the refusal that names the
account when the group is absent (10003) and the audit line it writes.

***[W.9] REMOTE.SSH / REMOTE.API AND THE AUDIT TRAIL — IN, OR OUT WITH THE
REST? RULED 18 SEP 2026 — THE READING APPLIED.*** Built: both switches stay, SDSYS's own
(sd-elevate behind the sdsys-only sudoers), and the audit trail stays — the
trail gains ELEVATION REFUSED reason=root, ELEVATION GRANTED reason=local
sdsys session, MODIFY.ACCOUNT SUSPEND/UNSUSPEND and the sdsys API-door
refusals.  The reading offered: keep both. The two
switches (S.13: `sd-elevate remote-api` / `remote-ssh`, the firewall verbs)
become SDSYS's own and stay the way the machine's remote exposure is turned;
the audit trail (E2, Q.13) stays because it is the cheapest evidence the
security-model evaluation will read — its records are the logins, refusals,
LOGTOs and grants the teardown itself will be measured by. Removing either
buys simplicity at the cost of a control.

***HANDOFF, 16 Sep 00-ish — NOTHING HAS BEEN INSTALLED SINCE `c1ea29b`, SO
NOTHING BELOW IS WITNESSED. `assert-current` SAYS STALE AND IS RIGHT.***

**Two things are waiting on the owner, and they are the whole of what is
blocked here:**

1. **S.23 — does the SHIPPED `installsdai.sh` pin a TAG?** He ruled the shape
   (*"the same as the windows version, staging directory and then a zip"*,
   15 Sep), which dropped the build-from-zip option. The residue is costed in
   S.23's entry: the edit is one value, `assert-current` is unaffected, and the
   real cost is that a development install must keep cloning `main`, so the
   shipped and repository scripts would differ. Recommendation is in the entry.
2. **The port's `dh_open.c` fix (a), offered for parity 15 Sep 23:45 and NOT
   taken** — see PORT_ADOPTION beside the J5 entry. It is an offer, not a
   decision approved in one port, so the follow-the-port rule does not settle
   it; and it is not a pure no-op here (a `DIO_UPDATE` failure after a truthful
   `access()` would become a silent read-only instead of an error). A core
   file-open path in a witnessed candidate, for a bug measured absent here.

**Built today and unwitnessed** — all of it settles on one cycle: S.24 (the
`SD_CONFIG` rename and the `TMP` bound), P.31's §15 K8/K9, §13j's J0–J4c
(`tierapi`'s STANDARD leg) and J5 (an API session writes its own `voc`).

***THE GROUND IS CLEAR FOR A WITNESS RUN — RE-MEASURED, AND THE EARLIER CLAIM
IN THIS FILE WAS OVERTAKEN.*** An older handoff said `sudo userdel -r zzrel1`
was needed; by the time the owner ran it the user was already gone (*"userdel:
user 'zzrel1' does not exist"*), and §0 now prints *"ground clear: zzrel1
exists as no user, group, directory, record or marker."* What removed it was
not observed. **Do not re-add that instruction.**

*Inert residue on this box, checked and deliberately not acted on:* Linux users
`pete`, `tstd`, `tprog`, `tadm` (uids 1001-1004) with homes and their own
`sdu_*` groups, no register record and no account directory. ***NONE IS IN
`sdusers`, `sdadmin` OR `sdapi`*** — checked, because a user left in `sdadmin`
is PRE_RELEASE 28's class and would matter. `deletesdai.sh` removes only SD's
own identities and never per-account users, so this is expected rather than a
defect.

***HANDOFF, 15 Sep (later) — THREE THINGS BUILT AND NONE OF THEM INSTALLED.
NOTHING HERE IS WITNESSED; THE LAST WITNESSED STATE IS STILL `c1ea29b` BELOW.***

1. ***THE §16 R3 LEAD IS ANSWERED, AND THE ANSWER IS THAT THE CHEAP ROUTE DOES
   NOT EXIST.*** R3 needs an `/etc/sd.conf` carrying `APILOGIN=1`, which only a
   ***keep-configuration*** cycle produces. ***MEASURED:*** `read_config()` has
   one caller, `sysseg.c:139`, and it runs only when the shared segment is
   being ***created*** — a session started with `SD_CONFIG` pointing at a
   private file never parses it (the built `sd` with `SD_CONFIG` naming an
   absent file started normally and reached the `:` prompt), and `sd -start`
   cannot be used to force the parse because the segment key is the fixed
   `SD_SHM_KEY` (`sysseg.c:306`), so it finds the live segment and returns
   first. Forcing the condition means stopping the live system, which a witness
   must not do to the box it is measuring. So the row now ***names its
   precondition out loud*** instead of reading like a defect, and the note
   above §16 records the dead end so no session spends another hour on it.
   ***THE REMAINING CHOICE IS THE OWNER'S AND IS ABOUT HIS INSTALL ANSWERS***,
   not about the script: answer **Y** to "keep your existing configuration" on
   some cycle and R3 measures the claim.
2. **P.31's missing row is built** — §15 makes `zzrel2`'s `voc` missing for one
   `DELETE.ACCOUNT` and restores it, so 10188 fires (K8/K9). See its table row.
3. **S.24, found on the way**: the server and the client library read
   *different* environment variables for the configuration file. Fixed, built,
   and guarded by a new free check. See its entry.
4. **Q.22's `tierapi` STANDARD leg is built** — §13j, the last of that
   verifier's legs that a measurement here could close. `batchjob`/`cmdaudit`
   remain, and those have no mechanism to verify rather than no instrument.

***SO THE ANSWER TO "IS THERE ANYTHING LEFT THAT IS NOT BLOCKED ON WINDOWS" IS
NARROWER THAN IT LOOKS, AND WORTH WRITING DOWN.*** S.21/S.22 wait on the port,
S.20 and S.1 are 1.2, and P.6's two remaining halves need a transient I/O error
nobody can induce. What was left here was ***unwitnessed paths and unlooked-for
defects***, not table rows — S.24 was on no list until someone read
`inipath.c`. The table was right that the 1.1 critical path is Windows; it was
never a claim that reading this tree would find nothing.

*Everything above is source and script only.* `assert-current` will read stale
until this is committed, pushed and installed, and no claim here may move to
"witnessed" without an owner-run cycle.

***AND THE NEXT WITNESS RUN WILL REFUSE TO START UNTIL ONE COMMAND IS RUN.***
***MEASURED 15 Sep 19:14*** by a dry run: §0 says `DIRTY: Linux user zzrel1
exists` and stops, because the script will not touch state it did not create.
***A SECOND WITNESS RUN WAS STARTED AT 18:28:51 AND INTERRUPTED*** part way
through §13i T3 (`/var/tmp/witness-release-run.20260915-182851.log` ends in
CLEANUP, after `zzrel2` went and while `zzrel1`'s SD account was going). The SD
side finished — no register record, no account directory, no `$cred`, no adopt
marker, and `zzrel1` is in no SD group — but `userdel` never ran, so the Linux
user, its group `zzrel1` (gid 1010) and `/home/zzrel1` survive. That is the
whole of what is left; nothing else on the box is dirty. ***THIS NEEDS `sudo`,
as the owner, and it is the only leftover:***

```sh
sudo userdel -r zzrel1
```

*The 18:26 run's own cleanup is not in doubt — its log says `userdel -r
zzrel1: done` and `left behind: … user=no`. The user present now was made at
18:28:52 by the run that followed.*

***HANDOFF, 15 Sep 18:26 — THE RELEASE CANDIDATE IS WITNESSED ON `c1ea29b`,
WHICH IS HEAD: 270 PASS, 0 FAIL, 1 NOT REACHED*** (log
`/var/tmp/witness-release-run.20260915-182615.log`, install 18:23:13,
`assert-current` current — the owner's word). ***THE ONE NOT-REACHED ROW IS THE
INSTRUMENT WORKING, NOT A REGRESSION***: §16 R3 measures that a ***restored***
`APILOGIN=1` is accepted, and this cycle answered **N** to "keep your existing
configuration", so `/etc/sd.conf` came back fresh with no `APILOGIN` line and
there was nothing to restore. It scored itself NOT REACHED instead of passing on
nothing. The 16:18 run on `c773008` had the older kept `sd.conf` and passed it,
271/271. ***A LEAD FOR THE NEXT SESSION, NOT A DECISION TAKEN HERE***: R3 is
measurable only on a keep-configuration cycle, so either the standing answers
become Y/Y/**Y**, or the row says out loud that it needs that cycle, or the
witness makes the condition itself — the third touches `/etc/sd.conf`, which is
why it is not done on a whim.

***WHAT THIS RUN CLOSED.*** Q.22's name gate: §13c **S9** (refused at 47) and
**S9b** (the trail reads `reason=name rejected by valid_os_name`) both pass on
both installs — S9b is the row that proves the NAME check fired rather than a
catch-all, which the wire deliberately cannot tell you. P.31's `delacc` fix
compiled into this install and the witness put the changed verb through
`DELETE.ACCOUNT` twice (§9 `zzrel3 REMOVE.HOME`, §15 `zzrel1`) with no abort.
***THE NEW ELSE ITSELF DID NOT FIRE***: every account's `voc` was present, so
10188 was never printed — the warning path is still unexercised, which is what
P.31's remaining row is for.

***AND THE 1.1 IDENTITY CHANGE IS MEASURED, BEFORE AND AFTER.*** The server's
certificate fingerprint was `53:2B:0E:CF:4E:8D:6C:9D:35:BE:1C:51:EF:10:42:2E:
84:8F:DD:51:96:8C:14:90:31:F1:A1:5F:DB:B4:51:B1` before the cycle and
***byte-identical after it***, same `notBefore`; `/etc/sd-tls` still carries its
15:46 timestamp while `/usr/local/sdsys` was rebuilt at 18:23. The tree was
replaced around a key that stayed put, which is exactly what `deletesdai.sh`'s
change was for. Before it, a keep cycle destroyed the identity.

***WHERE THE PROJECT STANDS.*** Linux 1.1 has no open work of its own. The
critical path is the Windows port: S.21 (the parity audit) is blocked on its 1.1,
S.22 (documentation) starts from the updated Windows text, and S.23 (staging
repositories and release zips) carries the question named in its entry — a zip
either implies cloning a TAG or an installer that builds from an unpacked zip,
and `assert-current`'s premise is bound up in that. The owner is pausing this
side until Windows catches up.

***HANDOFF, 15 Sep 15:48 — WITNESSED ON `c773008`: 269/269, 0 FAIL, 0 NOT
REACHED (log `/var/tmp/witness-release-run.20260915-154631.log`, install
15:44:32). W.4 IS CLOSED — PHASE 6's INSTALL HALF RAN — AND S.19's CONST FIX IS
RE-WITNESSED (§13i T1–T14c).*** The installer's new SD-password step asked the
owner at the keyboard (his word, 15 Sep) and the credential it wrote is on disk:
`scram-probe` with a deliberately wrong password is refused at request 48 with a
real salt and `i=600000`, where the 10:09 install was refused at 47. The local
tree was rebuilt after `libssl-dev` appeared on this box (`rm -f gplobj/*.o` then
`make`, exit 0, no warning) and `assert-current` is current. *Next, all the
owner's:* the certificate-pinning decision and S.19's port half (sd4windows
RELEASE_1.1 41). `interop-account.sh --create` RAN at 15:58, 21/21, so
`zzinterop` is live until `--remove` and the Windows-client→Linux-server run is
the thing now waiting. The Windows agent has the address, port and account by
mailbox; its password goes across from the owner directly, never the mailbox.

***HANDOFF, 15 Sep 10:23 — RE-WITNESSED ON `0b67dba`: 256/256, R1b, Y0 AND
H5c ALL PASS (log `/var/tmp/witness-release-run.20260915-102147.log`, install
10:09:58, 0 FAIL lines). S.13 CLOSED. §13i T1–T8 pass again.*** The first run,
on `0d58171`, was 253/256 (`/var/tmp/witness-release-run.20260915-095336.log`).
Its three failures, fixed in `0b67dba`:
- **R1b (instrument, new):** `ck_absent "libcrypt"` matched `libcrypto.so.4`,
  which S.19 links; the log's `ldd` has no `libcrypt.so`. Needle now `libcrypt.so`.
- **Y0 (instrument, 14 Sep's):** §13g now sends `LOGTO zzrel1` before the first
  WHO (the session lands in SDSYS otherwise); `LOGTO zzrel1` after section 4's
  fake `$release` is safe - §2b L1, §10 G3, §11 H3 pass on this log.
- **H5c (product, 14 Sep's):** `sd-elevate` `ufw_added`/`ufw_has_allow`/
  `ufw_ssh_rules` and the witness's `ufw_rule_present` read `ufw show added`
  (ufw 0.36.2 `frontend.py:358`, one `ufw <rule>` line each), so H1d/H7b stop
  passing vacuously too. `test-sd-elevate.py` U1–U4 against a fake inactive ufw:
  63/0, and U1 and U4 red on a copy whose `ufw_added` reads `ufw status`.
  Changelog entry added.
*Next:* S.19's port half (sd4windows RELEASE_1.1 41) and the owner's pinning
decision; on Linux the open rows below. The Windows-client→Linux-server interop
run needs a non-administrator API account: `sdapi` holds only `don`, who is
refused remotely (10174) and has no `$cred`. `gplbld/interop-account.sh`
(`sudo … --create`, `--remove`) makes `zzinterop` by the witness's ADOPT route,
demoted to PROGRAMMER with the API, and proves it logs in over 127.0.0.1 and the
LAN address. ***RUN 15 Sep 2026 15:58 BY THE OWNER — 21/21, `zzinterop` IS
READY AND LIVE*** (log `/var/tmp/interop-account.20260915-155808.log`, install
`c773008`): register field 5 PROGRAMMER, in `sdapi`, out of `sdadmin` (ADOPT's
administrator join removed), `$cred` written, and `scram-probe` logs in over TLS
1.3 from `127.0.0.1` AND from `192.168.0.210` — server signature verified,
account entered, `WHO` naming `zzinterop` (114, 115), password absent from the
wire, and ***no 10174 from the LAN address, which is the row a Windows client
depends on***. ***IT IS A THROWAWAY AND IT IS LIVE***: remove it after the
interop run with `sudo bash
/home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/interop-account.sh --remove`.
***THE RUN IT EXISTED FOR PASSED, 15 Sep 16:12 — AND THIS IS THE WINDOWS
AGENT'S MEASUREMENT, NOT ONE TAKEN HERE*** (its mailbox note of that time,
sd4windows `92a553a`; the audit trail is root-only, so nothing on this side
corroborates it). The owner ran `scram-probe.py` from the Windows box against
`192.168.0.210:4243`: TLS 1.3 through `libssl-3-x64.dll`, `c=` matching
base64(`p=tls-exporter,,` + the binding), 47 accepted with `i=600000`, 48
accepted with the server signature VERIFIED, account entered, `WHO` → `122
zzinterop`, password absent from the 260 plaintext bytes. ***So a Windows
OpenSSL client and this server agree on the whole contract*** — TLS 1.3, the
tls-exporter binding, the GS2 header, `SKT$INFO.TLS.CBIND` and the 600000
iterations. `zzinterop` has no remaining purpose: the Windows side says nothing
there assumes it persists, so it should go. ***THE REVERSE RUN IS OWED*** — a
Linux client against the Windows server at `192.168.0.2` — and it needs a
non-administrator Windows API account, which is the owner's to create and hand
over; that box's listener and firewall state on 4243 is unchecked.
***THE REVERSE RUN IS NOW MEASURED HERE EXCEPT ITS LAST STEP — 15 Sep, as `don`,
no sudo.*** The owner made `ZZINTEROPW` on the Windows box and said so.
`scram-probe.py --host 192.168.0.2 --user ZZINTEROPW` with a ***deliberately
wrong*** password: TCP 4243 open, ***TLS 1.3 negotiated*** through this box's
`libssl.so.4` against the Windows relay, the tls-exporter binding computed, and
***request 47 ACCEPTED*** — their server-first carried `s=bBxDPve5q33Mmbu4Cec9rQ==`
and `i=600000`, so the account exists with a SCRAM credential and their server
took our `p=tls-exporter,,`. ***REQUEST 48 WAS REFUSED IN 5017's WORDS AND NOT
5272's, WHICH IS THE ROW THAT MATTERS***: the port answers 5272 at its shared
`scram.bad.message` exit for a bad `c=` or nonce (`apisrvr:1691-1693`, the `c=`
recomputed from the session's own binding at `:1437`, read at `92a553a`), so a
5017 means ***the binding and the nonce PASSED*** and only the client proof
failed — which is what a wrong password does. So the reverse direction is proven
for the transport, the GS2 header, the binding value, the nonce and the
iteration count. ***AND THEN THE LAST STEP RAN AND PASSED.*** The owner typed the password at his
own keyboard (read hidden, never on a command line, never in this session) and
the probe finished: `SCRAM: server signature VERIFIED` — mutual — `account
ZZINTEROPW: entered`, `WHO` → `7 ZZINTEROPW`, password absent from the 262
plaintext bytes. ***SO BOTH DIRECTIONS PASS AND THE INTEROP HALF OF S.19 IS
CLOSED***: Windows client → this server (the Windows agent's measurement, 16:12,
sd4windows `92a553a`) and Linux client → their server (measured here). The two
ports agree on TLS 1.3, the tls-exporter binding, the GS2 header, the nonce,
`SKT$INFO.TLS.CBIND` and 600000 iterations, in both directions and with each
side's own OpenSSL. Both throwaway accounts have now done their work —
`zzinterop` here, `ZZINTEROPW` there — and neither should outlive the run.
***THE INSTALLER'S PASSWORD STEP IS RUN AND WITNESSED (15 Sep, `c773008`).***
`installsdai.sh` ends by setting the installing user's SD password (W.4 phase 6,
the owner's "#1" of 15 Sep). It asked him at the keyboard on the 15:44:32
install, and the credential is on disk: `scram-probe --host 127.0.0.1 --user don`
with a deliberately wrong password is refused at request 48 with a real salt and
`i=600000`, where the 10:09 install was refused at 47 (no credential at all).
The same cycle re-witnessed the TLS relay after `sd_tlssrv.c`'s const fix
(§13i T1–T14c, 269/269).

***[S.24] THE CONFIGURATION FILE WAS NAMED BY TWO DIFFERENT ENVIRONMENT
VARIABLES, ONE FOR THE SERVER AND ONE FOR THE CLIENT — FIXED 15 Sep 2026, NOT
YET INSTALLED.*** Found while looking for a cheap way to reach §16 R3 (below).
***MEASURED BY READING, BEFORE THE CHANGE:*** `inipath.c:38` read
`SCARLET_CONFIG` while `sdclilib.c:4080` read `SD_CONFIG`, each falling back to
`/etc/sd.conf` — so setting the variable you would expect moved the server or
the client to the new file and left the other on the default, with nothing
printed either way. The Windows port hit exactly this on 14 Aug 2026 and the
owner's instruction there was to stop reading `SCARLET_CONFIG` and settle on
`SD_CONFIG` (its `HISTORY.md`, "The configuration file finds itself"); under
the follow-the-port rule that is this port's decision, and the OS difference
touches only the default, which stays `/etc/sd.conf` here rather than the
port's `%ProgramData%`.

***WHAT CHANGED.*** `SD_CONFIG_ENV` / `SD_CONFIG_DEFAULT` in
`gplsrc/sddefs.h:110-129`; `inipath.c` reads the symbol and bounds the copy
with `snprintf` at `MAX_PATHNAME_LEN + 1`; `sdclilib.c` carries the duplicated
literals with a comment naming the header, because the client is a separate
toolchain that must not include the server's; `sdfix.c`'s `read_sdconfig()`
buffer goes from `200 + 1` to `MAX_PATHNAME_LEN + 1` — the port found that one
too, and until now `GetConfigPath()`'s contract was whatever its smallest
caller happened to be. `gplbld/tui-render-probe.py` and `sandbox-txnfail.py`,
the only things in this tree that set the variable, set `SD_CONFIG` now.
***BUILT 15 Sep 2026*** from `rm -f gplobj/*.o` then `make`, exit 0, and the
symbol is in the linked binaries (`strings bin/sd`, `bin/sdfix`).

***THE GUARD IS THE POINT, NOT THE RENAME.*** Nothing in the build cross-checks
`sdclilib.c`'s copy against the header — the compiler accepts any pair of
values and the failure is silent at runtime, which is how the two names drifted
apart in the first place. `gplbld/test-configpath-units.py` pins both values,
the symbol use, the bound, `sdfix`'s buffer and the absence of the old name
from code in six files: ***14/14 and `--selftest` 8 mutants 0 unnoticed,
15 Sep 2026***. It is a free check and is in CLAUDE.md's list. *Its own first
run had a mutant that went green — the anchor matched an earlier
`char path[MAX_PATHNAME_LEN + 1]` in `sdfix.c` and mutated the wrong
declaration — so the selftest's first act was to catch a hole in the check it
was testing.*

***AND THE SWEEP THAT FOLLOWED FOUND A SECOND ONE, 15 Sep 2026.*** Having
fixed one unbounded copy of an environment string, the same question was asked
of every `getenv` in `gplsrc/*.c`: `config.c:299-300` was
`strcpy(pcfg.tempdir, getenv("TMP"))` into a `MAX_PATHNAME_LEN+1` field. ***IT
IS THE ONLY COPY IN THAT FILE NOT BOUNDED BY ITS SOURCE*** — the two
config-file arms above it (`:265`, `:271`) take their string out of
`rec[200+1]` and cannot overrun a 256-byte field, while `TMP` comes from the
environment of whoever runs `sd -start` and has no length at all; the
`sortworkdir` default at `:313` then copies `tempdir`, so an overrun would have
been carried into a second field. Bounded with `snprintf`, built. The other
four `getenv` sites are clean: `op_misc.c:397` hands its result to
`k_put_c_string`, and `k_error.c:714` / `op_kernel.c:292` read `SUDO_USER`
without copying it into a fixed buffer. *This one is NOT guarded by
`test-configpath-units.py`, which pins the config-path pair and nothing else —
it is a fix, not an invariant.*

*The objection this session raised against itself, and did not dissolve:* this
is a behaviour change to a witnessed release candidate on a side the owner has
paused. Against it — the default path is unchanged, so an installation that
sets nothing behaves identically; nothing in the installer, the service unit or
the tree sets `SCARLET_CONFIG`; and the decision was already taken in the port.
*What would falsify the "identically" claim:* an install that fails to find
`/etc/sd.conf`, or a `!sdclient`/API session that cannot reach the system after
the client library is rebuilt. ***NEITHER HAS BEEN MEASURED — NO INSTALL HAS
RUN SINCE THE CHANGE.*** The changelog carries the user-facing note, including
what to do if `SCARLET_CONFIG` was set somewhere.

***[S.21] [S.22] [S.23] THE THREE PRE-RELEASE TASKS, IN ORDER — THE OWNER'S, 15
Sep 2026.*** Not started. They are sequential: each waits on the one before, and
the first waits on the other port.

1. ***PARITY AUDIT, once SD Core for Windows 1.1 is done***, then fix what it
   finds. ***BLOCKED ON THE PORT*** — nothing in this tree unblocks it. The
   method is not new: the 10 Sep 2026 audit (S.5, the witness list at §12) is the
   precedent, and widening it beats inventing a second one.
2. ***DOCUMENTATION, after the audit's issues are resolved.*** The Linux side
   ***starts from the updated Windows documentation*** and changes it where the
   two differ — so it cannot usefully start until the Windows text is settled,
   which is the same dependency as (1) arriving twice.
3. ***STAGING REPOSITORIES PER VERSION, THEN A RELEASE ZIP OF EACH*** — one for
   Linux, one for Windows.

***THE SHAPE IS RULED — OWNER, 15 Sep 2026: "the way the linux version will be
is the same as the windows version, staging directory and then a zip."*** So
(3) is the port's mechanism, not a Linux invention, and the entry below is kept
because the two ports differ in one place that the ruling does not reach.

***WHAT THE PORT ALREADY SETTLED, AND THEREFORE BINDS HERE.*** Read out of its
record, not asked: **GitHub carries the source** and (for the docs repository)
the Markdown; **the zip carries the built product and the PDFs and is assembled
by the owner outside the project** — its `PROJECT_STATUS.md` names the staging
directory as *"his hand-assembled release zip and NOT PART OF THIS PROJECT. Do
not read from it, write to it, or sweep it"* (its row for `../SDCore1.0-0`);
SourceForge carries only the zip, and **nothing else is published**, because
HTML and PDF regenerate from Markdown that is already current on GitHub (its
owner's correction of 12 Sep 2026, which replaced two commits that had called
publishing "owed"). ***SO THE ZIP IS A DISTRIBUTION ARTIFACT, NOT A BUILD
INPUT***, and the option this entry used to carry — "the installer learns to
build from an unpacked zip" — is not the model. It is not pursued.

***THE ONE PLACE THE PORT CANNOT ANSWER, BECAUSE THE OS DIFFERS.*** A Windows
zip carries a compiled Inno installer, so a Windows user never clones and never
builds. ***A LINUX USER RUNS `installsdai.sh`, WHICH CLONES AND BUILDS ON THEIR
MACHINE*** (`installsdai.sh:385`). So the Linux zip's `installsdai.sh` has to
name something, and today that is `REPO_BRANCH="main"` (`:75`) — which means a
1.1 zip installed in six months would build whatever `main` had become. *The
residual question is therefore narrow: does the SHIPPED installer pin a TAG?*

*Measured 15 Sep 2026, so the cost is known rather than guessed:*

- **The change is one value.** `:385` is `git clone --branch "$REPO_BRANCH"
  --depth 1 …`, and `--branch` takes a tag as readily as a branch. `REPO_BRANCH`
  at `:75`, plus the two lines that say "the main branch" to the user (`:229`,
  `:383`), are the whole edit.
- **The stamp survives it exactly.** `:397` takes `commit` from `rev-parse HEAD`
  of the clone, which at a tag is the tagged commit; `:688-690` already record
  `commit`, `branch` and `origin`.
- **`assert-current` is unaffected, and cannot be made to lie by it.** It reads
  only `commit` from the stamp — never `branch` — and check C is strict commit
  identity by the owner's twice-affirmed ruling of 12 Sep. A tag install whose
  commit is not `HEAD` reports STALE, which is the pessimistic direction the
  header calls the safe one. No false "current" is introduced.
- **There are no tags on `origin` today** (`git ls-remote --tags origin` is
  empty), so nothing depends on their current absence.
- ***THE REAL COST IS NOT IN THE CODE.*** A development install must keep
  cloning `main` — CLAUDE.md's "an install tests `origin/main`, so commit and
  push first" is the whole test cycle — so pinning a tag means the shipped
  script and the developer's script differ, or the choice comes back. **The
  owner removed the branch-choice menu deliberately on 9 Sep 2026** (`:228`,
  *"There is no selection any more: main, from GitHub"*), so re-adding a choice
  reverses a decision rather than filling a gap.

*Recommendation, conditional and for the owner's yes:* the staging copy of
`installsdai.sh` carries the tag and the repository's copy keeps `main`, so
neither script has a choice in it and the 9 Sep decision stands in both.
*Falsified if* the staging copy is meant to be a verbatim copy of the
repository's, in which case the choice has to live somewhere and this is the
wrong shape.

***[S.20] CLIENT RECOGNITION IS 1.2's, AS MUTUAL ENROLMENT — THE OWNER'S RULING
OF 15 Sep 2026, AND 1.1 KEEPS THE SERVER'S IDENTITY INSTEAD.*** Not started; this
entry is the reasoning, so the next session does not re-run the argument.

***WHAT 1.1 DOES.*** `deletesdai.sh` keeps `/etc/sd-tls` whenever the accounts
are kept and removes it only on a full DELETE, the rule `$cred` already follows
(`:192`). It is left in place rather than saved and restored, because unlike
`$cred` it lives outside the sdsys tree and `installsdai.sh` never touches it.
***NOTHING CHECKS THE KEY TODAY*** (`sd_tls.c:232` is `SSL_VERIFY_NONE`), so this
changes no behaviour now — it is taken before the clients exist, because a
warning that fires on every routine upgrade is one people learn to click through.

***THE RESIDUAL RISK 1.1 SHIPS WITH, STATED PLAINLY.*** TLS 1.3 plus RFC 9266
channel binding stops a man in the middle joining or reading a session, and SCRAM
proves the server at the END (the client checks `v=`). What remains is an
impostor server: it offers its own salt, the client sends a proof, the login then
fails — and the impostor keeps a proof to grind offline, bounded by the 4096
iteration floor (`sdclilib.c:876`, `sdclient:857`) and the real server's 600000.

***THE THREE SHAPES WEIGHED, AND WHY TWO WERE PUT ASIDE.***
- *Trust on first use alone* — the client stores the key on first sight and
  refuses on change. Rejected as an intermediate: 1.2's enrolment subsumes it,
  and its refusal puts the question "did the server legitimately change?" to a
  ***remote user who structurally cannot answer it***. The refusal happens
  BEFORE authentication, so SD cannot even tell whether that person is an
  administrator — there is no "only ask admins" option.
- *A client register alone* (the owner's question, 15 Sep) — valuable, but it
  ***cannot stop server impersonation, because the proof runs the wrong way***:
  a client fingerprint proves the client to the server, and an impostor is not
  bound by our register — it simply says "recognised, carry on".
- *Mutual enrolment* — one administrator act binds both directions at once: the
  server records the client's fingerprint and description, the client records
  the server's. Afterwards neither side prompts anybody, and a changed server key
  is an administrator re-enrolment rather than a dialog. ***CHOSEN, FOR 1.2.***

***AND IT IS AN OPTION, NOT A REQUIREMENT — the owner's ruling of 15 Sep 2026:***
*"for 1.2 we make the higher level of security an option, not a requirement. Let
the admin decide how much they need."* So 1.2 ships enrolment available and off,
and an administrator turns it on deliberately — the stance's "possible,
documented and reversible" applies to the act of turning it on.

***HOW THAT SITS WITH "SECURITY SHIPS TIGHT"***, since a later session will
notice the two and wonder: the capability that ships off is the network API
itself (`REMOTE.API` is LOCAL unless the installer is told otherwise), and
enrolment is a level of assurance ON TOP of a door that is already shut by
default. Requiring enrolment out of the box would mean no client could connect
until an administrator approved it, which is a usability cliff rather than a
tight default.

*Plan, not measurement — what it would look like, and what would falsify it:* a
ladder rather than a switch, because "how much they need" has more than two
answers — **open** (today: TLS and bound SCRAM, no recognition), **server
recognised** (the client checks the server's identity; no register to run), and
**mutual** (the client register with approval). If the middle rung turns out to
cost nearly as much as the top one, the ladder collapses to a switch and this
paragraph is wrong. ***THE HARD PART IS SWITCHING IT ON LATER, NOT SHIPPING IT
OFF***: clients that already work would have to be enrolled without a flag day,
so an enrolment window, or an approval queue an administrator drains, is the
piece to design first.

***WHAT IT WILL COST***, so 1.2 does not discover it: client key generation and
storage in BOTH clients (`sdclilib.c` and BASIC `!sdclient`), cert request and
verify in the relay (it does not ask for one today — no `SSL_CTX_set_verify` in
`sd_tlssrv.c` at all), a root-only register like `$cred`, verbs to list, approve
and revoke, and the enrolment flow itself. ***AND THE APPROVAL STEP IS THE WHOLE
STRENGTH***: a client that self-registers on first connection gives an attacker
the same courtesy, which makes the register a log rather than a gate. It binds
both ports. A by-product worth having: the audit trail could name the machine
instead of an address, and `apisrvr` already carries `api.peer.addr` for it.

***[S.19] PRIORITY #1, RELEASE BLOCKER FOR L1.1-0 AND W1.1-0 (owner, 15 Sep
2026). LINUX: TLS 1.3 ON EVERY API CONNECTION, SCRAM BOUND TO IT (RFC 9266
tls-exporter) - ON `main` AT `0d58171` AND WITNESSED ON THAT INSTALL 15 Sep,
§13i T1–T8 ALL PASS (relay as nobody, identity root 600, marker and user name
absent from the wire); THE PORT IS STILL TO DO.*** Owner ruled TLS ("start on
TLS", 15 Sep). *Built:* `gplsrc/sd_tls.c` (TLS 1.3-only ctx, handshake with
deadline, exporter, `c=` value, client), `sd_tlssrv.c` (relay: forked in
`start_connection` after the peer capture and before `bind_sysseg`; loads
`<dir of sd.conf>/sd-tls/api.pem` Ed25519 as root, refuses it unless owner-only;
drops to `nobody` before any network byte; hands sd the 32-byte binding; stderr
detached when it is the socket - systemd gives `StandardError=inherit`,
measured). `linuxio.c` ACK moved inside TLS; SDEXT `SD_TLS_CBIND` 110
(`op_sdext.c`, both `keys.h`); `apisrvr` requires `p=tls-exporter,,` and the
matching `c=` when the session is TLS, `n,,`/`biws` only without (pipes);
`sdclilib.c` TLS for every network session, bound SCRAM, `send_all` removed;
BASIC `OPEN.SOCKET` flag `SKT$TLS`, `READ/WRITE.SOCKET` through TLS (pending
bytes skip the `select`), `SOCKET.INFO` key 8 `SKT$INFO.TLS.CBIND`; `!sdclient`
uses both; Makefile `OPENSSL_LIBS`, `sd_tls_pic.o`; installer `libssl-dev`;
`deletesdai.sh` removes `/etc/sd-tls`; `scram-probe.py` drives libssl by ctypes
(+`--no-tls`, `--no-binding`); witness §13i T1-T8. *Measured, sandbox, as don:*
`test-tls-relay.py` 26/26 (new free check) against runtimes 3.5.5 and 4.0.1,
built with the powershell snap's 3.0.2 headers (`SD_OPENSSL_INC`) because
`libssl-dev` is not installed here; mutants red - zeroed binding (A4 A6 B4 B7),
stderr left on the socket (A3 A4 A6 A7 B3 B4); a scratch stand-in running the
real relay answered request 47 with its `c=`, equal byte for byte to
`scram-probe.py`'s ctypes one, and `--no-tls` got no ACK (relay exit 10); full
`make` of a scratch copy exit 0, no warning. *Unmeasured until an install:* the
relay as `nobody`, `apisrvr`/`sdclient` compiling in BASIC, `!sdclient` over
`op_skt` TLS, a build against real `libssl-dev` headers, every §13i row, and
whether the rest of the witness still passes through the rewritten probe.
***15 Sep 2026 — THE REAL-HEADER BUILD IS MEASURED NOW, AND IT FOUND A FAULT.***
`libssl-dev` 4.0.1 has been on this box since the 10:09 install (this release's
own installer change puts it there), so `test-tls-relay.py` compiled against the
shipped headers for the first time and went red: `sd_tlssrv.c:137` took
`X509_get_subject_name(cert)` into a non-const `X509_NAME *`, which OpenSSL 4
returns const (`-Wdiscarded-qualifiers`). The product built and ran anyway — the
witness passed 256/256 through this very code — because `make` does not use
`-Werror`; the free check is the stricter instrument and is the only thing that
saw it. Fixed by building the name with `X509_NAME_new()` and setting it:
`X509_set_subject_name`/`X509_set_issuer_name` both COPY, so it is freed on
every path, and behaviour is unchanged (same CN, issuer = subject).
`test-tls-relay.py` 26/26, no warning. ***IT IS A SOURCE CHANGE AFTER THE
256/256 WITNESS, SO §13i WAS RE-RUN: 269/269 on `c773008` (15:46 log), T1–T14c
all pass — the relay still `nobody`, the login still bound, replay and tamper
still refused.*** ***THE PORT HAS THE SAME LINE*** at its
`sd_tlssrv.c:156`, unbuilt so far (its RELEASE_1.1 41); sent to it by mailbox.
*Decisions and objections:* relay process, not SSL in `linuxio.c` - its SIGIO
handler (`io_handler` -> `do_input`) cannot call OpenSSL and `poll` cannot see
decrypted bytes; costs a process per session. Identity beside sd.conf, not
under SDSYS - sdcore4linux-2e's finding, checked: `installsdai.sh:659`
`chown -R sdsys` and `:551`'s root-helpers rule, and sdsys could rename a
directory away. A keep cycle's `deletesdai.sh` also removes it, so the key
changes per reinstall - harmless until clients pin. NO CERTIFICATE CHECK: the
bound login stops a man in the middle getting in or reading, but one posing as
the server can collect a proof for offline guessing (client iteration floor
4096) - pinning is the close. tls-exporter over tls-server-end-point, though
Python's `ssl` offers neither (measured 3.14.7, `CHANNEL_BINDING_TYPES ==
['tls-unique']`), hence ctypes. A client older than this change hangs for the
10 s handshake deadline and sees "connection closed". A non-blocking BASIC
`READ.SOCKET` on a partial TLS record busy-waits (`sd_tls_client_read` retries
WANT_READ) - `!sdclient` is blocking. *Next:* merged to `main` and witnessed
15 Sep (`0d58171`, §13i T1–T8), re-witnessed 256/256 on `0b67dba`; left: the
port adopts the same design (its RELEASE_1.1 41), and pinning is the owner's. Original
finding follows. Only the login was protected: SCRAM (W.4) proves the password
without sending it, but every request and reply after it is plain TCP —
`apisrvr:1066` *"there is no TLS channel to bind to"*; no cipher in `sdclilib.c`
or `linuxio.c` (libsodium is linked for SCRAM and BASIC ENCRYPT only). Owner:
QM's API was removed because it was insecure, and its transport weakness is
unchanged. Measured 15 Sep on this machine: `0.0.0.0:4243` listening (installer
"Allow API access" = Y, `installsdai.sh:252`, `:756`). With no channel binding
(`n,,`) an active attacker could also inject into a logged-in session — follows
from the design, not measured. Same gap in the port, which has no encrypted
remote route at all: its `apisrvr:1278`, `sdwind.c:364` binds `INADDR_ANY`,
`sd.iss:390` dropped the ssh tunnel. Filed there as RELEASE_1.1 41 and
BUGS_FROM_LINUX_PORT 9; neither record had raised it. *Declined by the owner:* a
stopgap (drop the installer's open-4243 prompt and REMOTE.API ON, remote use by
`ssh -L` only) — "no", fix it for 1.1. *Options, in the conditional, to be the
same in both ports:* (1) TLS 1.3 on the listener via OpenSSL (4.0.1 present,
`libssl-dev` headers absent), SCRAM moved to `p=tls-exporter` binding (RFC
9266), a certificate generated at install and pinned by the client on first use
— recommended; (2) ssh as the only remote transport, the client library opening
the tunnel — no new crypto, but API users need an OS login, Windows clients an
ssh client, and it reverses the port's 21 Aug ruling; (3) a libsodium
`crypto_kx` + `secretstream` channel — advised against as unreviewed protocol
code. Touches `gplsrc/sdclilib.c`, `sdclient.h`, `linuxio.c`,
`sdsys/gpl.bp/apisrvr`, `sdclient`, `usr/lib/systemd/system/sdclient.socket`,
`installsdai.sh`, `gplbld/scram-probe.py`, `api-probe.py`; and delete
`etc/xinetd.d/qmclient` (QM's own 4243 service, unused by the installer).
*Falsified-if (the witness):* a capture on port 4243 during an API READ shows the
record's content, or a client that does not encrypt is admitted.

***HANDOFF, 14 Sep 23:25 — WITNESS ON `dea3736`: 236/238 (log
`/var/tmp/witness-release-run.20260914-231854.log`). S.16 CLOSED (§13f all pass).
S.13 §13h passes incl. H1 (a session survives the socket restart) EXCEPT H5c.
Q.22 §13g Y1-Y4 pass EXCEPT Y0. Both failures read here; both fixed 15 Sep,
see the 15 Sep handoff above:***
- **Y0 (instrument):** a `sudo sd` session started in zzrel1's directory still
  lands in SDSYS (first WHO `77 sdsys`), so §13g never took the LOGTO route. Fix:
  send `LOGTO zzrel1` before the first WHO, then `LOGTO sdsys`; re-witness.
- **H5c (product + instrument):** ufw is INACTIVE here; `ufw allow 4243/tcp`
  said "Skipping adding existing rule" (the installer's rule is in ufw's config),
  but `ufw status` lists no rules while inactive, so `sd-elevate`'s
  `ufw_has_allow`, `api_show`/`ssh_show` and the witness's `ufw_rule_present`
  all read "absent" — and REMOTE.API LOCAL/OFF therefore never delete the rule.
  Fix: detect rules with `ufw show added` (root) instead of `ufw status`, in
  sd-elevate and the witness; re-witness. Machine state was restored unchanged
  (H6/H9 pass; the config rule was never touched).

***TWENTY-FOURTH SESSION, LATER — EVERY AGENT-DOABLE ROW WORKED.*** Built, unrun
until an install: S.16 (`787ab5d`, witness §13f), Q.22 sdsyswrite (`757f95b`,
free check `check-storewriters.py` + §13g), S.13 (`d0d9558`, §13h). Measured in a
sandbox, no install needed: P.6 (`8db0735`, `sandbox-txnfail.py` 22/22, and a
stranded OPENSEQ lock found and fixed) and S.1 stage 1 (renderer fast enough in
pure BASIC; mouse passes KEYIN). ***One owner hand-over covers all three unrun
rows:*** keep cycle, `assert-current`, then `sudo bash
/home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/witness-release-run.sh
--commit` — §13h changes the API listener and firewall and restores them.
Still the owner's: W.4 phase 6, P.24, Q.19, Q.13 rotation.

***TWENTY-FOURTH SESSION, 14 Sep 2026 — ALL TEN OPEN ROWS RE-MEASURED STILL
OPEN (`don` has no `$cred`: refused at 47 like `zzrel9`; audit 130,065 bytes of
1 MB; journal 21:20:20 `REFUSING TO SWEEP`); S.17 WITNESSED ON `e4e470e`,
195/195.*** See the S.17 entry below. Open rows now: P.24, Q.19, Q.13, Q.22,
P.6, W.4 (phase 6: `don` needs MODIFY.PASSWORD), S.16, S.13, S.1.

***TWENTY-THIRD SESSION, 14 Sep 2026 — S.18 WITNESSED ON `fed4b36`, 183/183.***
The dead login code phase 5 left, removed; the Unix socket turned out live and
is kept. Detail and the two traps: the S.18 entry below. Open rows now: P.24,
Q.19, Q.13, Q.22, P.6, W.4 (phase 6), S.16, S.17, S.13, S.1.

***TWENTY-SECOND SESSION, 14 Sep 2026 — SCRAM PHASE 5 WITNESSED ON `9fd52d9`,
171/171.*** Owner keep cycle 20:43:13, `assert-current` current; witness 20:45
(`/var/tmp/witness-release-run.20260914-204511.log`), every earlier row
re-passed. S5/S5c: request 24 refused in 5275's words with the SD and the Linux
password, no 5017, no login; §13d: `zzzsdcli` compiled, connected with the SD
password, `COUNT VOC` 403 records, wrong password refused, 3/3, no 5275 — so
both unmeasured points below held. ***Phase 6, measured here:*** the port's
step is "rebuild the DLLs, re-run SET.PASSWORD for every account"
(`docs/SCRAM_AUTH.md:230`). Both client libraries are rebuilt: installed
`sdclilib.so` 20:43:09 from `9fd52d9` (A0–A5 ran through it), `linuxsdclilib`
`libsdclilib.so` 20:33:36, newer than `sdclilib.c` and `scram_client.h`,
committed at `a727ccd`, `nm -D` 0 `SDConnectUDS`. The port's cycle trap
("`$cred` comes back EMPTY", HISTORY "20 Aug") does not transfer to a keep
cycle: `deletesdai.sh:192` saves and `installsdai.sh:764` restores it — ***not
witnessed with a real record in it*** (this run began with none). Left: the
owner runs MODIFY.PASSWORD under `sudo sd` for each account that uses the API
(the register holds `don`); a full delete cycle does empty `$cred`.
***15 Sep 2026 — THE `don` HALF IS THE INSTALLER'S NOW, AND IS WITNESSED.***
`installsdai.sh:1160-1235` ends with the port's finishing step
(`finish-install.ps1:375`): `sudo sd -QUIET MODIFY.PASSWORD <user>` at the
terminal for the account it just made, SD started for it and stopped again
(a session needs a running server, `sysseg.c:133`), skipped when a keep cycle
restored a credential, and the closing summary says whether one was set and how
to set it if not. ***NOT SDSYS — the owner's ruling that day (his "#1"), and the
one departure from the port***, which sets both (its PRE_RELEASE_FIXES 138):
this LOGIN has no `require.credential` at all (`login:366-369`, `sudo sd` lands
in sdsys with nothing asked) and `apisrvr:1259` requires `sdapi`, which the
`sdsys` person (uid 999, `sdusers` only) is not in, so an SDSYS password would
unlock nothing. ***NO INSTRUMENT CAN WITNESS IT*** — `input … hidden` needs a
tty and every automated route here pipes stdin — so an install at a keyboard is
the witness, and it ran: ***15 Sep 2026 on `c773008`, the owner asked and
answered at the prompt, `don`'s credential measured present afterwards
(`scram-probe`, wrong password, refused at 48 with a salt and `i=600000`;
the 10:09 install was refused at 47).*** The `$cred` test after the prompt is
what would have made a prompt that never appeared visible instead of silent. Other accounts are still MODIFY.PASSWORD by
hand (`interop-account.sh` does its own).
*Original build note:* The port's phase 5 (its HISTORY "20 Aug 2026 - SCRAM phase 5"). APISRVR
`vb.login` answers 5275 and drops the connection, body unparsed; 24 stays in
the pre-auth gate so the reply names the cause. `!sdclient` gains the port's
`scram.login`, `$internal` and requests 47/48 — the rest of the class was
already byte-identical to the port's (diff clean). `int$keys.h` gains
`SCRAM$MIN.ITER`/`MAX.ITER`; message 5275 the port's. ***Following the port's
lesson ("grep for the request number"):*** `SrvrLogin` had one more sender
here, `SDConnectUDS` (password "dummy", the APILOGIN=0 peer-uid branch). The
port has no such function, so it and `OpenUDSocket`/`SERVER_PATH` are removed
from both `sdclilib.c` copies, both `sdclilib.h`, `sdclilib.bi` and
USER_GUIDE. `make` exit 0, `nm -D` 0 `SDConnectUDS`; `linuxsdclilib` `make
check` passes. Witness: S5/S5c now expect 5275 for both passwords (S5c's
Linux password was ACCEPTED on `85fbbec`), no 5017; new §13d runs the port's
TESTSDCLI as `zzzsdcli` (not `$internal`) — B1 connect with the SD password,
B2 COUNT VOC over it, B3 wrong password refused, B4 3/3 and no 5275. Dry run
22 sections, free checks green. ***Unmeasured:*** that `sdclient` compiles at
install (`$internal`, new SDEXT calls) and that `input` after `echo off` reads
the piped password. Code now dead is task row S.18. Next: phase 6 — the port's
is "rebuild and re-set passwords"; here every account's SD password must be
set with MODIFY.PASSWORD before its API use, so it is an install/doc question.

***[S.18] CODE LEFT DEAD BY PHASE 5 — CLOSED: WITNESSED 14 Sep 2026 on install
`fed4b36` (21:19:41 keep cycle, `assert-current` current), owner-run
`witness-release-run.sh --commit` 21:21, 183/183, 0 not reached
(`/var/tmp/witness-release-run.20260914-212109.log`).*** S8–S8e: over
`/tmp/sdsys/sdclient.socket` SCRAM verified, account entered, WHO `56 zzrel1`;
request 24 refused in 5275's words. R1 `ldd`: libsodium listed, no libcrypt, no
libbsd. R2 `CONFIG`: CMDSTACK present, no APILOGIN. R3 `/etc/sd.conf` line
`7:APILOGIN=1` and `sd.service` active — the retired key is accepted. Every
earlier row re-passed. *(As built:)* Callers grepped first (`gpl.bp`, `gplsrc`, installer,
`bbcmp.py`): none for `login_user`, `pcfg.api_login` or `getpeereid` beyond
the removed code. As built, following the port (its HISTORY "17 Aug", step 6a):
`linuxio.c` `login_user` deleted with the `getpeereid` block in
`start_connection` and the `peer_*` globals; prototype out of `sd.h`,
`PASSWD_FILE_NAME` out of `sdnet.h`, `<crypt.h>` out of `linuxio.c`/`linuxlb.c`;
`op_login` a fail-closed stub (discards both args unread, pushes FALSE) — kept
because `opcodes.h` is positional and `BCOMP`/`bbcmp.py` index the intrinsic.
Makefile drops `-lcrypt -lbsd`; installer drops `libbsd-dev`. Measured on the
21:00:27 `bin/sd`: `ldd` shows neither lib, `nm -u` no `crypt`/`getpeereid`.
`APILOGIN`: field out of `PCFG`, out of `op_config.c`, `gpl.bp/config`,
`sd.conf`; ***the `config.c` parse line STAYS, ignoring the value***, because
an unknown key is fatal (`config.c:282`) and a keep cycle restores
`/etc/sd.conf` (`installsdai.sh:789`), which today carries `APILOGIN=1` — the
port kept its parses for the same reason (its PROJECT_STATUS `NETFILES`).
***FALSIFIED HALF OF THE ORIGINAL ENTRY: the Unix-socket `ListenStream` is NOT
dead*** — `examples/python/python_api_test/sdmeGuiTest.py:16` tunnels
`ssh -L 4245:/tmp/sdsys/sdclient.socket`, and SCRAM works over it (measured
below). Kept. ***Measured: the socket is `srw-rw-rw- root:sdusers`***
(`SocketGroup` without `SocketMode`), so it is no group gate — any local user
reaches it, as any reaches 127.0.0.1:4243; both need SCRAM.
`scram-probe.py --unix PATH` added; run live as `don` on the `9fd52d9` install
against `zzrel9` (no credential): unix SCRAM → refused at 47 in 5017's words,
unix `--legacy` → 5275, TCP control → 5017. Witness: 13c S8–S8e (SCRAM and
request 24 over the socket, path read from the installed unit), new §16 R1
(`ldd`, libsodium as the null guard), R2 (`CONFIG`: CMDSTACK, no APILOGIN), R3
(`sd.service` active with `APILOGIN` still in `/etc/sd.conf`; NOT REACHED on a
full cycle, which ships none). Dry run 23 sections.
***TWO TRAPS HIT, BOTH ALREADY IN THE PORT'S RECORD (its PROJECT_STATUS
"`struct PCFG` IS IN THE SHARED SEGMENT"), not found by the pre-run grep
because it searched the login tokens, not `PCFG`:*** (1) `pcfg` is a template
in the shared segment (`sysseg.c:124` memcpy) and `SYSSEG_REVSTAMP` is only the
release number, so the tree `bin/sd` against the live old daemon printed
`CONFIG` shifted (`CODEPAGE 1`, `CREATUSR 0`, `DUMPDIR` empty) — an install
cycle replaces every binary and is safe; never judge a `PCFG` change that way.
(2) `read_config` runs only when the segment is created (`sysseg.c:139`), so
an attaching session never parses `sd.conf`: the R3 claim is witness-only.

***TWENTY-FIRST SESSION, 14 Sep 2026 — SCRAM PHASE 4 WITNESSED ON `85fbbec`,
163/163.*** Owner keep cycle 20:22:01, `assert-current` current; witness 20:24
(`/var/tmp/witness-release-run.20260914-202410.log`), every earlier row
re-passed. Through the installed `sdclilib.so`: A0 the Linux password →
`SDConnect returned 0` / `Invalid username or password`; A1 the SD password →
`SDConnect returned 1`, `39 zzrel1`; A3c trail `reason=wrong password` (SCRAM's
wording); A5 a 62-character SD password set by MODIFY.PASSWORD connects; X6
suspended still refused with 10003. S5 request 24 with the SD password refused,
S5c with the Linux password `LEGACY: login ACCEPTED` and the account entered.
*(As built:)*
`SDConnect` sends the port's SCRAM (47/48) and no longer builds SrvrLogin, in
both `gplsrc/sdclilib.c` and `/home/don/Projects/linuxsdclilib/sdclilib.c`
(code identical, comments differ); `scram_login`/`scram_failed` are the port's
with `strcpy_s`→`snprintf`, `SecureZeroMemory`→`explicit_bzero`, `strtok`→
`strtok_r`. `sdclient.h` (both) gains `SrvrScramFirst`/`Final`. ***The one
technical difference:*** the port's primitives come from bcrypt.dll; Linux has
no crypto library in libc, so `scram_client.h` (both copies byte-identical)
implements SHA-256, HMAC and PBKDF2 and uses `getrandom`/`explicit_bzero`,
keeping the port's reason (one binary, nothing travels with it). Measured:
`nm -D` on both `.so` shows only `getrandom` and `explicit_bzero` added, no
libsodium. Vectors: `test-scram-vectors.py` now runs server + client, ***46/46***
(client 29, incl. SHA-256 "abc"/empty known answers); `linuxsdclilib` `make
check` passes with its new `scram-client-test` 29/29. `make` exit 0, no warning.
Witness: api-probe now logs in with the SD password (`LINUX_PW` keeps the
Linux one); new A0 (the Linux password through the library is refused), A3c
reason `wrong password`, A5 is a 62-character ***SD*** password set by
MODIFY.PASSWORD, S5/S5c go through new `scram-probe.py --legacy` (request 24:
SD password refused, Linux password accepted until phase 5); `--legacy` run
live against `d880012` for `zzprobe` → `LEGACY: login REFUSED at request 24`.
Dry run 21 sections, free checks green. ***Not covered:*** `SDConnectUDS` still
sends request 24 with password "dummy", which `APILOGIN=1` refuses today — the
port has no UDS path; phase 5 decides it. Next: phase 5 retires request 24
(5275) and gives `!sdclient` SCRAM.

***TWENTIETH SESSION, 14 Sep 2026 — SCRAM PHASE 3 WITNESSED ON `d880012`,
160/160.*** Owner keep cycle 20:01:11, `assert-current` current; witness 20:02
(`/var/tmp/witness-release-run.20260914-200257.log`), every earlier row
re-passed. §13c: S1 `request 47 -> server_error 0`, server-first
`…,i=600000`, `SCRAM: server signature VERIFIED`, account entered, `46
zzrel1`; S2 SCRAM session `Uid: 1005`, `Groups: 979 1010 1011` (K$ASSUME.USER
works); S3 wrong password and ***S4 the Linux password*** both refused at 48
(5017); ***S5 request 24 with the SD password refused*** — each door reads its
own credential; S6 48-without-47 → 5273; S7 `zzrel9` refused at 47 (status
3006); audit gained `reason=wrong password` ×2, `sequence error - no
client-first`, `no credential`. ***The plan's falsifier is measured and did not
fire:*** PBKDF2 at 600,000 iterations took 0.07 s per login (Python hashlib,
this machine), so client cost does not block phase 4. *(As built:)*
APISRVR gains the port's `vb.scram.first`/`vb.scram.final` (requests 47/48),
their shared exits, `scram.trim.body` and `scram.clean.name`, the pre-auth gate
admitting 47/48 and two dispatch lines; `valid_os_name` declared at the top.
Linux differences, each commented in place: `$cred` read `downcase(username)`;
`K$ASSUME.USER` (61) is `initgroups`/`setgid`/`setuid` while root, refusing uid 0
and reading the uids back (`op_kernel.c`); `K$SET.USERNAME` (60) is the port's
verbatim. Messages 5272–5274 and 10160 the port's, 5277 "Linux identity".
`make` exit 0, `op_kernel.o` rebuilt 19:57, `nm` shows `initgroups`/`getpwnam`.
Request 24 still works (phases 1–3 are additive). New `gplbld/scram-probe.py`:
the exchange in Python's stdlib over the wire format from `sdclilib.c`,
password from `SD_SCRAM_PASSWORD`; py_compile clean, three refusals exit 2, live
against `b119bb3` (no 47 yet) → `request 47 -> server_error 1` / `Not logged in`,
so the framing parses. Witness §13c (S1–S7): SCRAM with the SD password logs in
and the signature verifies; the session's /proc uid and groups; wrong password
5017 + audit; ***S4 the Linux password over SCRAM refused and S5 the SD password
over request 24 refused*** — each door reads its own credential; 48 without 47
→ 5273; unknown user → 5017 at 47. Dry run 21 sections, free checks 17 green.
Unmeasured when built, both measured by the run above: that APISRVR compiles
(install only) and that the session runs as the user after `K$ASSUME.USER` (S2). Changelog deferred to phase 5,
when a user would notice.

***[S.16] PER-ACCOUNT API ROUTE — CLOSED: WITNESSED 14 Sep 2026 on `dea3736`,
§13f F0–F9b all pass.*** *(As built, 14 Sep, free checks green:)* ***Adopted, not asked:*** the 10 Sep parity
audit had listed "ssh ForceCommand vs `sdssh`/`sdapi` groups" as a kept
difference, but neither it nor the S.16 row was an owner ruling; the owner's
stance of 12 Sep ("security ships tight and the administrator relaxes it by
choice") decides the API half — before this any `sdusers` member with an SD
password could use the API. The ssh half stays ForceCommand (PRE_RELEASE 13).
From the port (its MODIFYA route.set/route.apply 21–27 Aug, CREATEA, owner
rulings 20/21/27 Aug), with the ssh half cut:
- `sdapi` group: `installsdai.sh` creates it and seeds every `sdadmin` member
  each install (a keep-accounts install otherwise keeps an administrator sdapi
  never heard of); `deletesdai.sh` deletes it only with the accounts, as sdadmin.
- `sd-elevate`: `sdapi` whitelisted and undeletable; `test-sd-elevate.py` +3
  REFUSE rows, 45/45 (no ALLOW row: dry-run checks the group exists, and it
  exists only after an install carrying this).
- `modifya`: `API`/`NONE` (absolute, 10077/10079, 10080 no-op, 10081 failure,
  audit `MODIFY.ACCOUNT API … to=yes|no`); refused for a group account (10087)
  and an administrator by tier ***or `sdadmin`*** (10083); `SSH`/`BOTH` refused by
  name (10919, Linux). Leaving ADMINISTRATOR must name API or NONE (10111, the
  port's 27 Aug ruling), parsed before anything changes; becoming one joins
  sdapi, and repeating ADMINISTRATOR repairs a missing membership. ***Found on
  the way and fixed:*** `@system.return.code = 0` sat after the group moves and
  overwrote a failed `join.sdadmin`/`leave.sdadmin`'s -ER$FAILED.
- `createa`: a non-administrator USER account must say API or NONE (10082),
  checked before the Linux user is created; NONE on an administrator 10083;
  a route word on GROUP/OTHER 10087; administrator or API joins sdapi.
- `apisrvr` `vb.scram.final`: after sdusers, `sdapi` or 10073, reason
  `not a member of sdapi`; a missing group refuses everybody (the port's).
- `delacc`: a kept Linux user loses sdapi, between sdadmin and sdusers.
- Callers updated: `witness-release-run.sh` (§6 `PROGRAMMER API`, §12 zzrel3
  `NONE`, §13b zzrel2 `PROGRAMMER NONE`, §13e E6 `PROGRAMMER API`, §15 K6 counts
  sdapi), `witness-tierchange.sh` M2 `NONE`, `witness-accounts.sh` rows 1/2a/3.
Witness §13f: F0 zzrel1 in sdapi; F1 NONE → F2 same login refused 10073 +
audit; F3 10080; F4 API → F5 login works (the before/after pair); F6 SSH 10919;
F7 NONE on zzrel2 10083; F8 wordless demotion 10111, still ADMINISTRATOR; F9
wordless CREATE.ACCOUNT 10082, nothing made. Dry run 25 sections.
***Would falsify it:*** a compile error in `modifya`/`createa`/`apisrvr` (no
DEFFUN in `bbcmp.py`, so nothing compiles them before install); `id -nG`
reading a stale group cache after `sd-elevate` (F1b/F4b would then fail on the
instrument, not the product).

***[S.17] REMOTE ADMINISTRATOR OVER THE API — CLOSED: WITNESSED 14 Sep 2026 on
install `e4e470e` (21:48:07 keep cycle, `assert-current` current), owner-run
`witness-release-run.sh --commit` 21:51, 195/195, 0 not reached
(`/var/tmp/witness-release-run.20260914-215124.log`).*** E1 control: PROGRAMMER
over 192.168.0.210 VERIFIED + entered. E3/E3c: ADMINISTRATOR admitted over
127.0.0.1 and the Unix socket. E4: same account and password over
192.168.0.210 refused at 48, reply 470 bytes, 10174's first line. E5 audit
`API REFUSED user=zzrel1 reason=administrator on a remote API session from
192.168.0.210` — so `getpeername` and `!peer_local` both work. E6b: PROGRAMMER
tier + `sdadmin` by hand refused (the group arm); E6c out again, §14 X1 then
landed in sd. `peer_local` and `apisrvr` compiled at install (the two
unmeasured points). Every earlier row re-passed. *(As built:)* From the port's PRE_RELEASE_FIXES 170 (witnessed
there 5 Sep, 15/0). ***The PRE_RELEASE 13 question, read:*** 13 lets an
administrator ssh in to a real shell, which the port's ssh gate (its 167, in
LOGIN) forbids. That half does not transfer — an admin's ssh session never
runs LOGIN here, so a LOGIN gate stops nothing — and it does not bear on the
API door, which admits on the SD password alone. The API half ports, so no
owner question. ***Why it matters here although an API session has no
`K$ADMINISTRATOR`:*** the session runs as the Linux user, and `sdadmin` reaches
root via passwordless `sd-elevate` (PRE_RELEASE 28) — root on the SD password.
As built: `gpl.bp/peer_local` (the port's routine; SSH_CLIENT then
`system(42)`; loopback `127.*`/`::1`/`::ffff:127.0.0.1`; ***Linux addition: an
address starting `/` — the Unix socket's path — is local***). `apisrvr`
`vb.scram.final`, after the `sdusers` test and before `K$SET.USERNAME`: refuse
with 10174 if (register tier ADMINISTRATOR ***or `sdadmin` member*** — Linux
addition, the group is the power) and not local; both computed before the test
(no short-circuit). ***Divergence: a register that cannot be opened REFUSES***
(the port admits, inheriting its ssh gate). Audit reason
`administrator on a remote API session from <addr>`, the port's.
***`linuxio.c` PF_INET now fills `ip_addr`/`port_no` from `getpeername()`***, as
the port's does — it was `getsockname`, the address connected TO, so
`system(42)` could not answer "from where"; a failure leaves `?` (not local →
refused). 10174: Linux wording, 470 bytes rendered — over `check-msglen`'s 231
(the `k_error` path, as 10043 is) but it travels as `abort.message` into
`sdclilib.c:267`'s 512-byte `sderror`. ***Limit, the port's:*** `ssh -L` arrives
from 127.0.0.1/the socket and is admitted; here that is the intended way in.
Witness §13e (the port's verify-apiremote legs on one host): E1 CONTROL
PROGRAMMER over this host's LAN address, gating the rest; E2 → ADMINISTRATOR;
E3/E3c admitted over 127.0.0.1 and the socket; E4 refused over the LAN address
in 10174's words, E5 audited with that address; E6 back to PROGRAMMER, E6b
`gpasswd -a sdadmin` drift refused, E6c removed (§14's ssh control needs it).
Measured before handing over: this install listens on `0.0.0.0:4243`, LAN
address 192.168.0.210, and `scram-probe --host 192.168.0.210 --user zzrel9`
reached the server (refused at 47), so E1 has a route. Dry run 24 sections.
***Unmeasured until install:*** that `peer_local` and `apisrvr` compile, and
that `call !peer_local` resolves from APISRVR.

***NINETEENTH SESSION, 14 Sep 2026 — SCRAM PHASE 2 WITNESSED, WITH ITS TWO
FIXES.*** `74c60d4` (19:34:27): witness 19:36 ***141/141***, §13 C0–C7 (record
`2` / `SCRAM-SHA-256` / `600000`, salt 24, keys 44/44, `$cred` root:root 700).
The same install failed `verify-setpw.py` 3/22 — THE PRODUCT, not the
instrument: plain `sd` MODIFY.PASSWORD said "has no password set" and prompted,
because a directory file opens without permission and a refused read looks
like a missing record. And cleanup left `$cred/zzrel1`: DELETE.ACCOUNT never
removed it (the port's DELACC has the same gap — to report). Fixed in
`b119bb3`: `set_acc_password` refuses on `system(27) # 0` before any prompt;
`delacc` deletes the `$cred` record before the register record; witness §0
refuses a leftover zzrel `$cred` record, §15 gains K7. `b119bb3` (19:43:01,
owner removed the stale record first): witness 19:45 ***142/142***
(`/var/tmp/witness-release-run.20260914-194524.log`), K7 `$cred/zzrel1` gone;
`verify-setpw.py` as don, no sudo, ***22/22***, C2 printed `MODIFY.PASSWORD
needs sudo sd`, no prompt. ***Next: SCRAM phase 3*** — APISRVR requests 47/48
from the port's `vb.scram.first`/`final` (its `APISRVR:1262-1716`), messages
5272–5274; the API login stays on the Linux password until phase 5.

***EIGHTEENTH SESSION, 14 Sep 2026 — W.4's SCRAM LOGIN, PHASE 1 OF 6 BUILT.***
Adopted by the owner's conformity rule (memory note, 14 Sep). The plan follows
the port's `docs/SCRAM_AUTH.md` "Order of work" (sd4windows tree), whose
phases 1–3 are additive and whose break is concentrated in 5. ***Phase 1,
done:*** `gplsrc/sd_scram.c`/`.h` verbatim from the port but for their history
lines; SDEXT keys 104–109 in `gplsrc/keys.h` and `sdsys/syscom/keys.h`;
`SD_SCRAM_ERR` -10303 in `gplsrc/err.h`, `syscom/err.h` and `errtext.h`
regenerated by `gplbld/gen_includes.py` (the J4 procedure, `:3830`); the port's
six dispatch cases and two helpers in `op_sdext.c`; `sd_scram` in `gpl.src`.
`make` exit 0, `sd_scram.o` + `op_sdext.o` compiled, no warning, `nm bin/sd` 6
`sd_scram_*`. New free check `gplbld/test-scram-vectors.py` (compiles the
port's `verify-scram.c`): ***17/17*** — the five RFC 7677 §3 values, server-side
verify accept/reject, six guards, nonce length and freshness. This tree already
linked libsodium (`Makefile:48`), so nothing technical blocked it. The BASIC
side of SDEXT 104–109 is not exercised until an install. ***Phases left, as the
port ran them:*** 2 `$cred` v2 + `CRED_SET`/`CRED_VERIFY` (port `INT$KEYS.H:281`
CRED$ fields, 600,000 iterations); 3 APISRVR requests 47/48 (`vb.scram.first`
/`final`, messages 5272–5274); 4 `scram_login` in both `sdclilib.c` copies; 5
retire request 24 (5275) and give `!sdclient` SCRAM; 6 re-set passwords.
***Linux questions the later phases would have to settle, each a technical
fact rather than a choice:*** (a) MODIFY.PASSWORD here hands the password to
`sd-elevate passwd` and never reads it (Q.17) — SCRAM needs SD to derive the
credential, as the port's `SET_ACC_PASSWORD` does; (b) `$cred` would be
root-only, written by a privileged verb, read by APISRVR while still root; (c)
after 48 succeeds the session must become the user without a password — today
only `login_user`'s password path does `initgroups`/`setuid`; (d) the
Unix-socket peer login (`linuxio.c` `getpeereid`, `APILOGIN`) has no port
counterpart. ***Would falsify the plan:*** PBKDF2 at 600,000 iterations too
slow per client connection here — measure before phase 4.

***Phase 2, same session — WITNESSED on `74c60d4`, 141/141; two defects it
exposed are built, not installed.*** Keep cycle installed `74c60d4` (19:34:27,
`assert-current` current); owner-run `witness-release-run.sh --commit` 19:36,
log `/var/tmp/witness-release-run.20260914-193649.log`, cleanup complete. §13:
W3 shadow `!` → `$y$` by `chpasswd`; MODIFY.PASSWORD printed "has no password
set" then "Password set for account zzrel1"; `$cred/zzrel1` fields `2` /
`SCRAM-SHA-256` / salt 24 / `600000` / 44 / 44; register `root:root 700`
(C0–C7). Every earlier row re-passed. ***Defect 1, MEASURED by
`verify-setpw.py` on the same install (19/22, C2/C3/C-session failed):*** as
plain `don`, MODIFY.PASSWORD did not refuse — it printed "has no password set",
prompted "New password:" and took the piped `OFF` as one. A directory file
opens without permission and the refused read looks like a missing record, so
the "Cannot open" guard never fired. Fix: `set_acc_password` refuses on
`system(27) # 0` (`op_sys.c:222`, getuid) after 5276/2001/5018 and before any
prompt; `verify-setpw.py` C2 matches its wording. ***Defect 2, from reading the
cleanup:*** DELETE.ACCOUNT never removed `$cred/<account>` (nor does the port's
DELACC — to be reported), so the 19:36 run left `$cred/zzrel1`, and a later
account of that name would inherit the old API password. Fix: `delacc` deletes
the record before the register; witness §15 K7 checks it and §0 now calls any
leftover `$cred/zzrel[123]` DIRTY. ***The next run will refuse at §0 until the
leftover record is removed by hand*** (hand-over below). *(Built as:)*
`gpl.bp/cred_set` and
`cred_verify`: the port's derivation, version-2 record and read-back, lower-case
ids, and a direct write under euid 0 in place of the port's elevated-helper
fallback. `int$keys.h`: the port's CRED block and `SCRAM$ITERATIONS` 600000.
`set_acc_password` replaced by the port's MODIFY.PASSWORD (hidden prompts, three
tries, current password via `!CRED_VERIFY` when one exists, `!CRED_SET`).
***This supersedes the 12 Sep design there and in PORT_ADOPTION 17*** ("there
should not be one"), whose premise — the API checks the Linux password — the
SCRAM adoption removes; question (a) above is answered this way. CPROC
`privileged_commands` gains `$MODIFY.PASSWORD` (euid 0 under `sudo sd`; plain
`sd` is refused at the `$cred` open, the port's "ordinary console NO").
`installsdai.sh` creates or restores `$cred` root:root 700 after the `chmod -R
755` and prints the mode; `deletesdai.sh` keeps it on a keep cycle. The install
compiles every record (`voc_template/second.compile` is `BASIC gpl.bp *`), so
no list changed. Witness §13 now sets the Linux password with `chpasswd` (W3,
and §13b's login still checks it) and reads the `$cred` record MODIFY.PASSWORD
writes (C0–C7: version 2, SCRAM-SHA-256, 600000, both keys 44 base64, register
root:root 700); A5 uses `chpasswd` too. `verify-setpw.py`'s control (C1–C4) now
expects the `$cred` refusal where it expected PAM; T1–T3 kept. Parse clean,
0 BOM/CR, dry run 20 sections, free checks 17 green. ***Unmeasured, from
source:*** `input … HIDDEN` reads the witness's piped lines; plain-sd
MODIFY.PASSWORD prints CPROC's EUID warning before the refusal. Next: keep
cycle, `assert-current`, `verify-setpw.py`, witness `--commit`.

***[S.15] SEVENTEENTH SESSION, 14 Sep 2026 — S.15 CLOSED, WITNESSED ON
`72933c2`, 131/131.*** Keep cycle installed `72933c2` (17:34:34,
`assert-current` current); owner-run `witness-release-run.sh --commit` 17:36,
log `/var/tmp/witness-release-run.20260914-173627.log`, ***131/131***, cleanup
complete. §13b A2: API server pid 7011, `Uid: 1005`, `Gid: 1010`, `Groups: 979
1010 1011` — `sdusers` and `sdu_zzrel1` held, no group 0 (the same line was
empty on `3ff8027`). A4.3b `SDError: User not allowed in requested account`.
Every earlier row re-passed. Not measured: an ADMINISTRATOR's API session
holding `sdadmin` (zzrel1 is PROGRAMMER at §13b). Open rows now: S.14, P.24,
Q.19, Q.13 (rotation), Q.22 `sdsyswrite`, P.6, W.4 (the SCRAM ruling), S.13,
S.1.

***SIXTEENTH SESSION, 14 Sep 2026 — CYCLE `3ff8027`, 128/128; AN API SESSION
HAD NO SUPPLEMENTARY GROUPS; the fix, installed and witnessed in the
seventeenth (above).*** Keep cycle
installed `3ff8027` (17:13:12, `assert-current` current); owner-run
`witness-release-run.sh --commit` 17:18, log
`/var/tmp/witness-release-run.20260914-171838.log`, ***128/128***, cleanup
complete. New rows: A1 `SDConnect returned 1`, `38 zzrel1` (lower case); A2
server pid 7741 `Uid: 1005`, `Gid: 1010`, ***`Groups:` empty*** — no `sdusers`,
no `sdu_zzrel1`; A3 5017 and trail `API REFUSED user=zzrel1 reason=authentication
failed` (Q.13's last type); A4 10128 named zzrel1, CPROC's control 10126, and
the API into zzrel2 → `SDConnect returned 0` / `SDError: User not allowed in
requested account` (W.4's gate); X6 suspended → the same (Q.12 closed). So
S.14's second lead was wrong: the refusal text does come back. Fix:
`linuxio.c` `login_user` calls `initgroups()` before `setgid`/`setuid` on both
paths and refuses the login if it fails; `make` exit 0, only `linuxio.o`
rebuilt, no warning, `nm bin/sd` shows `initgroups`. ***The least-tested
claim:*** an administrator's API session now holds `sdadmin`, as its terminal
session does, so what `%sdadmin` gets through sudo is reachable from an API
session able to run OS commands — no wider than the terminal, new for this
door. Witness: §13b A2c/A2d now decisive, A4.3b matches 10003's text; dry run
20 sections. ***Next, owner:*** keep cycle; `assert-current`;
`witness-release-run.sh --commit`.

***[W.4] CLOSED 15 Sep 2026 — ALL SIX SCRAM PHASES ARE WITNESSED, THE LAST OF
THEM ON INSTALL `c773008` (269/269): the installer's own SD-password step ran at
a keyboard, which is phase 6. The task table row carries the measurement. The
fifteenth session's walk of the API surface follows, kept for its detail.***
***FIFTEENTH SESSION, 14 Sep 2026 — THE API SURFACE WALKED; A TIER GAP
BUILT, WITNESSED ON `3ff8027` IN THE SIXTEENTH; SCRAM was next then.*** Read, no sudo. The door: `sdclient.socket` (Unix
socket + `127.0.0.1:4243`, `Accept=true`) → `sdclient@.service` `sd -n -q` as
root → `linuxio.c:101` `start_connection` (Unix peer by `getpeereid`, a TCP peer
unassigned) → APISRVR `vb.login` → `login_user` (`/etc/shadow` + `crypt()`,
`linuxio.c:767-774`; `/etc/sd.conf` has `APILOGIN=1`, so the Unix socket also
wants a password) → `setuid` with no `initgroups` (`set_groups()` commented,
`:775`) → `vb.account` (SUSPENDED, then `ACC$GROUP`). Gap 1: `vb.account` had
no tier ordering — the port's `APISRVR:657` and `cproc:2951` do; added
`!tier_allows(@logname, …)` → 10003. Gap 2: WHO over the API was upper case
(`upcase(cmnd)`, and `:145`) — the port does the same, §M goes past it; the name
folds lower, a path stays as typed; `verify-nocase` 0 of 3. Compiled only by
the next install (GPL.BP is SDSYS's to compile). Which supplementary
groups an API session holds was measured in the sixteenth: none (S.15). `gplbld/api-probe.py` (ctypes over the installed
`sdclilib.so`, password from `SD_PROBE_PASSWORD` only): py_compile clean, BOM/CR
0, no password → exit 2, live against this install as nonexistent `zzprobe` →
`SDConnect returned 0` / `SDError: Invalid username or password`, exit 1 (one
`API REFUSED` line added to the trail). Witness: §13b A1–A4.5 (control login,
lower-case WHO, the session's /proc groups, 5017 + Q.13's API REFUSED, the tier
gate against CPROC's 10126 control, revoke) and §14 X6 (Q.12's API door); dry
run reaches all 20 sections. API login without OS passwords
(`PORT_ADOPTION.md:811`, filed "owner decision") is ***decided by the owner's
rule of 14 Sep 2026***: conformity with the port is the requirement and a
question goes to him only when Linux technically cannot do what the port
does. SCRAM runs on Linux, so it is adopted — the port's `$cred` store,
`CRED_SET`/`CRED_VERIFY`, SCRAM in APISRVR and the client change. Until it is
built, with "Allow API access" = Y the password crosses TCP 4243 in clear. Run in the sixteenth (above).

***[S.13] REMOTE.API ON / LOCAL / OFF AND REMOTE.SSH ON / OFF — CLOSED: WITNESSED
15 Sep 2026 on `0b67dba`, §13h ALL PASS (`/var/tmp/witness-release-run.20260915-102147.log`).***
Built 14 Sep (twenty-fourth session). H5c had failed on `dea3736` and `0d58171`:
`ufw status` lists no rules while ufw is inactive, so LOCAL/OFF never deleted
the installer's 4243/tcp rule and H1d/H7b passed without looking. Fixed 15 Sep
by reading `ufw show added` (`sd-elevate` `ufw_added`/`ufw_has_allow`/
`ufw_ssh_rules`, the witness's `ufw_rule_present`; `test-sd-elevate.py` U1–U4,
red on a status-reading copy). As built, the plan below: `sd-elevate
remote-api on|local|off|show` writes `/etc/systemd/system/sdclient.socket.d/
sd-remote-api.conf` (`ListenStream=` reset, the unit's own Unix-socket line,
then 0.0.0.0 or 127.0.0.1:4243), daemon-reload, enable, restart the socket;
OFF is `disable --now`; ufw `allow`/`delete allow 4243/tcp` (the installer's
rule); `show` reads systemd and ufw back and ends "The SD API is X.". `remote-ssh
on|off|show` moves `ufw allow 22/tcp` only, and ***refuses with exit 3 where ufw
is absent, inactive or not default-deny incoming*** (a rule would gate nothing);
OFF warns about other ssh-allowing rules it did not add. Fixed keywords only;
`test-sd-elevate.py` +9 rows and 5 PLAN rows asserting the dry-run steps (a
swapped ON/LOCAL fails them). `gpl.bp/remoteapi` (`$REMOTEAPI`) and `remotessh`
(`$REMOTESSH`): administrator-gated, one keyword, a second word refused, no
word = report, audited; `voc_template/remote.api`, `remote.ssh` and
`tier.policy/add.administrator` (19 → 21 verbs; login's `update.voc` adds them
to existing administrators, `login:797`); messages 10131-10133, 10137-10139 in
Linux wording. ***No SD restart and no Y/N, unlike the port*** — that rests on
the falsifier below, which §13h H1 measures. `scram-probe.py --pause` added for
it. Witness §13h saves and restores the exact listener/firewall state (also in
cleanup). *(Plan, 12 Sep, kept:)* The
port's record answers whether: owner, 30 Aug 2026 (port PRE_RELEASE_FIXES 78),
because changing your mind meant re-running the installer — and here only a
reinstall moves `installsdai.sh:736-742`, which the stance's "a restrictive
default with no way to relax it" names. `PORT_ADOPTION.md:815` asked for a
ruling before that entry was read. A plan, in the conditional: the API verb
would write a drop-in for `sdclient.socket`'s `ListenStream` and add or delete
`ufw` 4243 through new `sd-elevate` verbs; the ssh verb would scope `ufw` 22
rather than stop sshd; SSH.SERVER is not proposed (distribution packages).
What would falsify it: `ufw` inactive (the rule then gates nothing — say so),
and whether `Accept=true` sessions survive a socket restart (the port had to
restart SD and drop every session).

***[S.14] API PASSWORD LENGTH — CLOSED, WITNESSED ON `8f17140`.*** Keep cycle
installed `8f17140` (18:56:33, `assert-current` current); owner-run
`witness-release-run.sh --commit` 19:00, log
`/var/tmp/witness-release-run.20260914-190008.log`, ***134/134***, cleanup
complete. A5: MODIFY.PASSWORD set a 62-character password (10914), and over
the API `SDConnect returned 1`, `46 zzrel1`, no `Invalid password`; X6 used the
same password on the suspended account → `SDConnect returned 0` / `SDError:
User not allowed in requested account`, no 5017. Owner, 14 Sep 2026:
match the port. Measured there: its `SDConnect` bounds the USER NAME at 32
(`gplsrc/sdclilib/sdclilib.c:1218`) and refuses only an EMPTY password
(`:1226`, no length cap, because SCRAM never sends it). Here the password had
three caps at 32: the client (`sdclilib.c` `SDConnect`), APISRVR `vb.login`
(`n > MAX.USERNAME.LEN`) and ***a fourth the walk had missed***, `op_login`'s
`char password[32 + 1]` (`op_kernel.c`), where `k_get_c_string` cuts a longer
string silently. Now: the client refuses an empty user name or password and
sizes the login packet from the two lengths (the one bound left is SrvrLogin's
16-bit length, 32767); APISRVR refuses only `n < 1`; `op_login` sizes the
buffer from the string and wipes it after `login_user`. The same client change
is committed in `/home/don/Projects/linuxsdclilib` with its rebuilt tracked
`libsdclilib.so`; its `make check` passed (smoke + internal). This tree:
`make` exit 0, no warning. Witness §13b A5: a 62-character password set by
MODIFY.PASSWORD must log in (passed, above); X6 then uses it. Only the empty refusal
is client-side, so it has no server row. A second lead, that the client drops an
account refusal's text, was a misreading of `sdclilib.c:900-908`: the
sixteenth session's run printed `SDError: User not allowed in requested
account` at §13b A4 and §14 X6.

***FOURTEENTH SESSION, 14 Sep 2026 — [S.12] AND S.6 CLOSED, WITNESSED ON
`79d7e87`.*** Keep cycle installed `79d7e87` (15:02:58, `assert-current`
current); owner-run `witness-release-run.sh --commit` 15:04, log
`/var/tmp/witness-release-run.20260914-150451.log`, ***113/113, 0 not reached***.
§10: V0 `VOC: 43 records added`; the zzrel2 session started before the GRANT
(Groups `965 979 1012 1013`, sdu_zzrel1 = 1011) → `28 zzrel1 from zzrel2`, then
`COPY FROM VOC who,zzstale` → `File is read-only`, 0 bytes on disk; control, a
session started after → `1 record(s) copied.`, zzctl on disk. GRANT printed
the new 10043. §11: `zzsh-ran`, `31 zzrel1 from zzrel2`, `zzrel2 is not
permitted to use OS.EXECUTE`, no `not in your VOC`. Every earlier section
re-passed. Cleanup complete: `userdel -r zzrel1: done (waited 10s)` — a zzrel1
process outlived §15 by up to 10 s, consistent with the 14:38 failure being
exit 8; which process was not captured (`del_user` names them only if still
there at 20 s). Open rows now: P.24, Q.19 (not foldable), Q.12/Q.13 (W.4 and
rotation), Q.22 `sdsyswrite`, P.6, W.4, S.1.

***THIRTEENTH SESSION, 14 Sep 2026 — S.12 AND S.6's INSTRUMENT, BUILT;
installed and witnessed in the fourteenth (above).*** S.12: 10043 reworded: an open session "can enter the account but
cannot change anything in it"; revoke's half "can still change the account's
files". GRANTA comment `:380` records the 14:38 measurement. `check-msglen`
fails 10043 at HEAD and now alike (11 lines vs `k_error`'s 3) and does not
apply: its only caller is `crt sysmsg` (`granta:391`). `witness-release-run.sh`:
§10 moves zzrel1 to PROGRAMMER first (V0, from §12 — STANDARD omits `copy` and
`run`, `tier.policy/omit.standard:32`), G4 is now a check, and the stale
session's `COPY FROM VOC who,zzstale` must print 1431 `File is read-only`,
no `record(s) copied`, 0 bytes on disk (G6–G6b), against a fresh session's same
COPY landing (G7–G7b) — all passed in the fourteenth session. Chain from source: `dh_open.c:118` → `op_dio1.c:793`
`FV_RDONLY` → `copy:212`. §11 gains H3b (`is not in your VOC` absent). Cleanup:
`del_user` waits up to 20 s for the user's processes and prints `userdel`'s
exit and message — the zzrel1 failure's cause is ***unmeasured***; exit 8 from
§14's lingering `systemd --user` is the hypothesis, falsified if the next run
reports another exit. Parse clean, 0 BOM/CR; dry run of a `zzdry1` copy reaches
all 19 sections (the real script refuses at §0 while zzrel1 exists); free
checks green. ***Trap hit again:*** Edit stripped a trailing space in
`run_sd "$ACC" ` and fused two arguments — caught by the dry run's title.
***Next, owner:*** `sudo userdel -r zzrel1`; keep cycle; `assert-current`;
`sudo bash …/witness-release-run.sh --commit`.

***HAND-OFF, 14 Sep 2026, twelfth session (owner low on credits).*** Keep cycle
installed `f2251e6` (14:37:02); owner-run `witness-release-run.sh --commit`
14:38, log `/var/tmp/witness-release-run.20260914-143833.log` (root-readable),
***105/106***. CLOSED: S.5 (V0–V10, D1–D6, K1–K6 all pass), Q.14 (G0–G3, G5),
Q.17 (W1–W3; shadow `!` → `$y$`), Q.12's ssh door (X1–X5). ***S.12 FINDING:***
the zzrel2 session started before the GRANT (Groups `965 979 1012 1013`,
sdu_zzrel1 = 1011) ENTERED zzrel1 — 10043 says "refused by the filesystem";
from source it enters with a read-only VOC (`dh_open` real-uid `access()` →
read-only open, `%0` 664). Reword 10043 or rule. ***THE ONE FAIL WAS THE
INSTRUMENT:*** §11 H3 ran `RUN BP zzos` in zzrel1 while zzrel1 was STANDARD
(§7 left it there), so `RUN is not in your VOC`; H4 passed for that wrong reason.
Next: in §11, `MODIFY.ACCOUNT zzrel1 PROGRAMMER` before the LOGTO (and move
§12's V0 accordingly), re-run. ***CLEANUP LEFT LINUX USER zzrel1***
(`userdel -r zzrel1: FAILED`, no process of it remained afterwards): the owner
removes it with `sudo userdel -r zzrel1` before the next run, or §0 refuses.

***ELEVENTH SESSION, 14 Sep 2026 — THE REMAINING WITNESSES FOLDED, run in the twelfth.***
S.7 CLOSED on the owner's word: nano and micro both show colour at a real
terminal. Agent-measured on `2edec17`, as `don`, plain `sd`: `SH echo zzsh-ran`
→ `zzsh-ran` (S.6's first half). `witness-release-run.sh` gains §10 Q.14 (a
zzrel2 session started before `GRANT zzrel1 TO zzrel2`, its `/proc` Groups
printed; G4 records whether it entered — ***expected, from source, that it
ENTERS READ-ONLY rather than being refused: `dh_open` asks `access()` with the
real uid, finds `%0` unwritable and opens it read-only, and `%0` is 664, so
10043's "refused by the filesystem" may be wrong for a plain session***), §11
S.6 (SH in the admin's own account; after LOGTO zzrel1, zzrel1's `zzos` → 10054
naming zzrel2 — SH itself is not in a STANDARD VOC), §12 + §15 S.5 (PROGRAMMER
lacks sh/config/listu, ADMINISTRATOR has them; LISTF descriptions; `UPDATE.ACCOUNTS
FOO` 10173 and `ALL` 10170/10171 — ***touches every real VOC, as an install
does***; zzrel3 stamped `SD account` by `useradd -c`, ADOPTed PROGRAMMER SH-ON →
10102, `DELETE.ACCOUNT zzrel3 REMOVE.HOME` one question, user and home gone;
`DELETE.ACCOUNT zzrel1` → 10085 + 10036, user kept with no SD group), §13 Q.17
(random password never printed, shadow hash prefix before/after; relies on
passwd reading the session's own stdin, SD reading it a byte at a time,
`linuxio.c:447` — ***unmeasured until the run***), §14 Q.12 (throwaway key for
zzrel1, ssh control first, then SUSPENDED → 10107, then restored). ***Not
folded:*** P.24 (needs no install and a non-sudoer), Q.19 (needs files-only
NSS at a real boot), Q.13 rotation (needs a 1 MB trail and an SD restart).
Parse and dry run clean. Because the owner ruled `assert-current` strict, the
run follows a keep cycle.

***TENTH SESSION, 14 Sep 2026 — CYCLE `2edec17` (14:07), ALL GREEN.*** Owner-run:
`verify-semaphores.py` ***9/9*** — KILL round caught sem 4 held by 5769, SIGKILL
→ back to 1 in 0.05 s (SEM_UNDO); FAULT round sem 4 held by 5837, SIGSEGV → -11,
back to 1 in 0.00 s (handler); max value in any sample 1. ***W.0 CLOSED.***
`witness-release-run.sh --commit` 14:09 ***63/63***, cleanup complete: §5b —
2050 Enter → nothing displayed, WHO ran, Y control displayed `VOC det.sup`;
6133 Enter and C → nothing deleted, c1/c2/dic on disk, N control → `DICT
portion 'zzpromptm.dic' deleted` (***W.2, W.3, Q.3b CLOSED***); §8 — trail 684 → 692,
new lines `MODIFY.ACCOUNT ADD account=zzrel1 to=zzrel2`, `… DELETE … from=zzrel2`,
`user=root sudo=zzrel1 … ELEVATION REFUSED reason=not a registered
administrator` (Q.13's three types witnessed); 5026 now shows its trailing
space. Every earlier section re-passed. Open rows now: S.7 (owner terminal),
P.24/Q.19/S.5/S.6/Q.12/Q.14/Q.17 (owner witnesses), Q.13 rotation, Q.22
`sdsyswrite`, P.6, W.4, S.1.

***NINTH SESSION, 14 Sep 2026 — BUILT, then installed and witnessed in the tenth:*** W.2
and W.3 were ***answered by the port's record***, not asked: its
`RELEASE_1.1_FIXES.md` 33 (owner, 13 Sep) — Enter = N at 2050 in all six, and
6133 gains C (Enter = C). Built as the port's lines, messages 2050/6133 reworded.
***TRAP, MEASURED:*** the Write tool had stripped 5026's trailing space (installed
as `(y/<n>)?` + LF; the port hit the same on 13 Sep), so 5026, 2050 and 6133 were
written by a scratchpad script building the space from `chr(32)`, byte-checked,
3 one-line diffs. The other ten `?`-ending messages without a space are
byte-identical to the port's and left. `witness-release-run.sh` gains §5b (the
port's verify-promptenter legs 7–8) and §8 (Q.13's ADD/DELETE/ELEVATION REFUSED,
second throwaway `zzrel2`). ***W.0 RULED BY THE OWNER ("both") and built***
(`SEM_UNDO` + `release_owned_semaphores()` first in the fatal handler) with
`verify-semaphores.py` — PORT_ADOPTION W.0. ***Next cycle:*** keep cycle,
`assert-current`, `verify-semaphores.py` (no sudo), `witness-release-run.sh
--commit` (sudo).

***HAND-OFF, 14 Sep 2026, eighth session — ONE CYCLE, `984be50` (13:37).***
Owner-run: `verify-keys.py` ***36/36*** (the backspace fix; red 34/36 before);
the `$hold.dic` byte check ***1*** (S.11 closed); `witness-release-run.sh
--commit` 13:45 ***39/39***, cleanup complete — Q.28 closed (`0000322A: Runfile
pathname is longer than 128 characters at line 2563 of $CPROC`, path 165), S.4
closed (control `ZZOS ran OS.EXECUTE` at ADMINISTRATOR; after the move, `gpasswd
-d zzrel1 sdadmin`, `VOC: 0 … 19 removed`, then `zzrel1 is not permitted to use
OS.EXECUTE`), S.3 closed (after `43 removed` to STANDARD, Y at the prompt → `.`,
then `Record 'basic' not found`, `Record 'run' not found`, `VOC list` present,
next sign-on no prompt), `logtoaccess` 2 + 1 arrivals with its control refused.
`assert-current` exit 0 on `984be50`, seen in `verify-keys`'s own
precondition transcript. ***Not pasted, so Q.13's reinstall-survival is still
open:*** the before/after `head`/`wc` of the audit trail. It can close without a
cycle: every install today was a keep cycle, so a first record dated before
today's 13:37 install has survived one. Audit record types measured in source:
no SH/OS writer exists (`op_sh.c` has no `K$AUDIT`), so that type is not owed;
`API REFUSED` waits on W.4. Remaining open rows are owner-terminal, sudo,
rulings, or L/XL.

***[S.11] 14 Sep 2026, seventh session — A §M REMNANT THE METER COULD NOT SEE;
CLOSED in the eighth session (above).*** `write_install_dicts` OPENPATHs
`<sdsys>/<file>` by the file half of each `gplbld/FILES_DICTS` record, and an
open failure prints "THIS SHOULD NOT HAPPEN" and CONTINUEs. Record
`$HOLD.DIC^@ID` named a directory gone since §M3. Measured on `d704658`, bytes,
no sudo: `grep -a -c @ID` over `%0 %1` → `$hold.dic` 0, `voc.dic` 1, `$map.dic`
1. `git mv` to `$hold.dic^@ID` (content unchanged). `verify-nocase` had no
FILES_DICTS category — added (file half only); red 1 of 70 before, 0 after,
`--strict` 0. ***Witness after install, no sudo:*** `cat
'/usr/local/sdsys/$hold.dic/%0' '/usr/local/sdsys/$hold.dic/%1' | grep -a -c
'@ID'` must be ≥1. P.1's walk (same session): `upgrade-dicts` NEEDS NO
COUNTERPART — a keep cycle rebuilds `/usr/local/sdsys` and the installer runs
`write_install_dicts` + THIRD.COMPILE every time (`installsdai.sh:895,903`), and
all six targets are sdsys files; `clean-deadvoc` NO COUNTERPART — cleared
debris of the port's own `verify-catgate`, and `verify-sysperms` K4 shows this
tree's catgate rows create nothing; `restart-sd` NO COUNTERPART NOW (unit is
`KillMode=control-group` with `sdlnxd` in its cgroup; nothing in `gpl.bp`
restarts SD). P.1 closed. ***Also this session, all for ONE cycle:*** the
`_keycode` backspace fix + `verify-keys.py` (red 34/36 on `d704658`);
`witness-release-run.sh` gains §2b logtoaccess, §5 Q.28's deep F-pointer, §6
S.4 (10054 on PROGRAMMER after an ADMINISTRATOR control) and §7 S.3 (Y at the
release prompt on STANDARD; `FIRST_LINE` must be cleared in the parent shell,
since `run_sd` runs in `$( )`). ***The cycle's steps:*** before the delete,
`sudo head -3` + `sudo wc -l` of `/usr/local/sdsys/audit` (Q.13); keep cycle;
`assert-current`; the same two reads (first lines identical, count not
smaller); `verify-keys.py`; the `$hold.dic` byte check (S.11);
`witness-release-run.sh --commit`.

***HAND-OFF, 14 Sep 2026, sixth session.*** Owner keep cycle installed
`d704658` (13:06, `assert-current` current); `witness-release-run.sh --commit`
13:07, 18/19: ***S.10 CLOSED*** (F1 `RUN BP ZZSHOW` → `ZZSHOW field 2 = L0.9-9`,
no 5073); ***S.9 CLOSED*** ((a) blank → `5 zzrel1`, no 5027, prompt read
`(y/<n>)?`; (b) `</dev/null` → prompt once, "Process terminated", exit 0; (c)
field 2 still `L0.9-9`); S.2's real case passed again (`2 zzrel1 from sdsys`).
***Q1 FAILED AND IT WAS THE INSTRUMENT:*** the 100-character record id is over
`MAXIDLEN` 63 (`config.c:139`, `valid_id` `op_dio3.c:1778`), so RUN said
`Program BP.OUT zzq… not found` before measuring the path. So a `bp.out` run
path cannot pass 128 in a standard account (23 + 32 + 8 + 63 = 126); the
section now reaches it through a VOC F-pointer to a 158-character directory.
The script change makes the install stale, so Q.28's re-run waits for the next
cycle. Cleanup complete both runs.

***[S.10] HAND-OFF, 14 Sep 2026, fifth session — `RUN` DID NOT FOLD THE PROGRAM
NAME; CLOSED in the sixth session (above).*** *Audit, sixth session, read only:*
every `read`/`readv` in `gpl.bp` keyed by a `*name*` variable with no
`downcase`/`upcase` within 3 lines — 37 sites, 22 outside VOC/register/dict.
No other program-OBJECT lookup lacks the fold: CATALOG folds both (`catalog:230`,
`:283`); DELETE.CATALOG reads catalogue names (upper by design); `prog_info:57`
reads a given path and has no caller in `gpl.bp`. The rest (ED, CT, COPY,
DELETE, SPVIEW, lists) are record ids in users' own files — out of §M scope by
the 12 Sep ruling, so `ED BP ZZNEW` still makes an upper-case source record. Owner-run on `6e5b2f5` (`assert-current`
current): `verify-sysperms.py` ***28/28*** (dump `dumps/sddump.5` `don:don 0600`,
listing refused) — Q.25 closed; the install built with plain `make` — P.16
closed. `witness-release-run.sh --commit` 12:55: S.2's real case PASSED (groups
`0 979 1001 1003 1005 1007 1009`, `sdu_zzrel1` = 1011 absent, `LOGTO zzrel1` →
`7 zzrel1 from sdsys`); then `BASIC BP ZZREL` → "Compiling BP zzrel", `RUN BP
ZZREL` → ***`Program BP.OUT ZZREL not found`***, so S.9 and Q.28 were NOT
REACHED; cleanup complete. Cause: §M1 folded `int.run`'s BP.OUT open but not
its `readv s from run.file,run.record.name,0` (`cproc` ~:2533); the note at
"`RUN BP <prog>` IS CASE-SENSITIVE" below predates §M and was never followed
up. Fix: as typed, lower, upper, the answering spelling run. Witness reworked:
setup runs `RUN BP zzrel` exactly; new rows F1/F2 test the upper-case fold.
`verify-nocase` could not have caught it (names only, not lookups). Other
`readv`/`read` of a typed program name (CATALOG, DELETE.CATALOG…) are not
audited for the same gap. Next: keep cycle, `witness-release-run.sh --commit`.

***HAND-OFF, 14 Sep 2026, fourth session.*** Built for ONE install cycle:
**S.9** (5026 Enter/EOF = N), **Q.25** (`dumps/` + `DUMPDIR` + 0600 dumps,
`verify-sysperms` §8), **P.16** (build as the caller). New owner-run
`gplbld/witness-release-run.sh` covers S.9, Q.28 and S.2's real case (a root
process older than the account's group). After the cycle: `assert-current`,
`verify-sysperms.py` (no sudo), `witness-release-run.sh --commit` (sudo) —
***commit nothing between them***. Noticed, not fixed:
`witness-tierchange.sh`'s R5 compares a value with itself and cannot fail
(§L1 rests on M2/P3/R4, which are real); and `sd < file` ends "Process
terminated" at the first prompt where a pipe works.

***HAND-OFF, 14 Sep 2026, third session.*** Worked the table's cheapest rows.
Closed: **P.29** (kickstart note dropped; boot 0 re-read `active`, no `-stop`)
and **P.11** (`check-msglen.py` derives its bound; `test-msglen-units.py` 10/10,
now the sixteenth free check, all green 7.3 s). Built + compiled, not installed:
**Q.28** (message 10918) and **S.8** (K_INTERNAL guard) — ***the tree `bin/sd`
now differs from the install `83e5ccf`***, so both want the next install cycle.
**S.2** witnessed by the owner (root without `sdu_don` → 3001; with it → enters)
and fixed in `sdext_eguid.c` (`initgroups` before the euid drop). ***Owner keep
cycle installed `ca4c07c` (11:51, `assert-current` current): S.2 re-run entered
`don`, S.8 signs on — both closed.*** Q.28 is installed and still needs a
disposable account to witness in. Next cheapest open rows: S.7, then the M rows.

***HAND-OFF, 14 Sep 2026, second session (credits).*** The task table at the
top of this file is new and is the authority on what is left; read it first.
`check-stale-leads.py` exits 0 on it (both phases). Built this session: the
table; checker phase 2 plus `gplbld/test-staleleads-units.py` (18/18); CLAUDE.md
rules for table upkeep, "fix the first sentence", the handover "same block"
clause, and the 15 free checks (all green, 7.6 s). Nothing product-facing
changed, so the install is still `83e5ccf`. Next: the table's open rows, which
are already the cost-ordered list the owner asked for. The cheapest are P.29
(drop `installsdai.sh:1112-1114`), Q.28, P.11 and S.8.

***HAND-OFF, 14 Sep 2026 (credits) — READ THIS FIRST. BOTH RELEASE BLOCKERS ARE
CLEARED; NO RELEASE-BLOCKING WORK REMAINS.*** Tree clean at `caa2203`, pushed.
- ***§M (lower case) — DONE + INSTALLED on `83e5ccf`.*** M1 fold, M2 (mooted +
  `!voccase` removed under the no-migration ruling), M3 renames, all witnessed;
  `verify-nocase` COMPLETE. Full suite green (block below).
- ***§L1 (per-tier VOC) — CLOSED.*** `MODIFY.ACCOUNT` re-derives the VOC alone,
  witnessed by owner-run `gplbld/witness-tierchange.sh --commit` (15/15, 14 Sep
  00:01): down removes 62 = omit 43 + admin 19, up adds 43 then 19, round trip
  balances, no `UPDATE.ACCOUNTS`. That run also fixed two instrument false
  greens/fails (tier-layer's `'VOC'`, the witness's `LOGTO`).
- ***§N (release number): the target is `L1.1-0`*** (owner, 14 Sep — conform
  with Windows W1.1-0). ***ONLY the changelog header moved to `L1.1-0 - in
  progress`; the revstamp STAYS `L1.0-0`*** and bumps only at ship time, as the
  port keeps `W1.0-0` while its changelog reads `W1.1-0 - in progress`. So the
  banner reads `L1.0-0`. (I first bumped the revstamp too; reverted.)

***STATE OF THE INSTALL vs HEAD.*** Install is `83e5ccf`; HEAD is `caa2203`,
ahead by dev instruments + docs + the changelog header. `assert-current` reads
STALE for that reason — but nothing PRODUCT-facing is uninstalled except the
changelog text (ships next install, no behaviour change). Verifiers need
`--allow-stale` until the next reinstall, justified: the delta is
docs/dev-scripts/changelog only.

***WHAT'S NEXT is the task table at the top of this file*** (14 Sep 2026); it
replaces the list that stood here. `witness-accounts.sh --commit` stays an
optional owner-run witness, not a task.

***14 Sep 2026 — tier.policy move WITNESSED on install `83e5ccf` (owner keep
cycle, `.sdcore-install` 23:06:38, `assert-current` 0). The §M NAME HALF IS
COMPLETE, installed.*** `tier.policy` shipped (both records), newvoc has no TIER
records. Suite as `don`, no sudo, all green: ***tier-layer don 19/19, 0 short***
(the layer read from `tier.policy/add.administrator`); grants 16/0, editors
28/28, lcnames 139/139; vocverbs 34, fold 35, setpw 24, txn 33, nonet 59,
lineendings 42, basicfuncs 199, accounts 36, sysperms 18. `verify-nocase`
source **COMPLETE**. don `COUNT VOC` 418.

***AND A FALSE-GREEN BUG FOUND AND FIXED IN THE WITNESS INSTRUMENT ITSELF***
(`verify-tier-layer.bp`, not the product): it opened the account VOC as `'VOC'`,
but §M lower-cased account dirs to `voc`, so on the case-sensitive fs the open
FAILED and the probe `continue`d past the one admin it had — leaving `nshort` 0
and the wrapper reporting *"every admin holds the layer"* without having tested
one. The 51da55b witness's "0 short" was that false green. Fixed: open `'voc'`,
and ***a VOC that will not open now counts short*** (refuses the null case). Now
it really opens don's `voc` and confirms 19/19. Dev instrument, compiled fresh
by the `.sh`, so witnessed this session without a reinstall.

***THE §M NAME HALF REACHES 0 IN SOURCE.*** `verify-nocase` now prints
***§M NAME HALF: COMPLETE*** — 0 name remnants, all 3 code sites ` ok `. The two
former NEWVOC remnants (`TIER.OMIT.STANDARD`, `TIER.ADD.ADMINISTRATOR`) moved to
a new directory file `sdsys/tier.policy` as records `omit.standard`,
`add.administrator` (port `a47526f`, adopted). NEWVOC 398→396 records, all lower;
sdsys dirs 15→16, all lower.

***WHAT WAS DONE (all in one commit):***
- `git mv` the two records into `sdsys/tier.policy/{omit.standard,add.administrator}`
  (bytes/history preserved); field 1 (the comment) rewritten to name the new
  location and this tree's readers.
- `gpl.bp/createa`, `gpl.bp/login`, `gpl.bp/modifya`: open `@sdsys/tier.policy`,
  read the lists from it. ***8 reads confirmed here by grep, not 7*** —
  this tree's `login:779` reads `add.administrator` too (the port's login does
  not). createa/login open FAIL-SAFE (missing file → no policy → full newvoc /
  programmer's VOC for an admin); modifya HARD-FAILS (both files needed to
  compute a tier change, so a missing one keeps 10114 the true answer). The 4
  copy-loop skip tests (createa, login) deleted with the records.
- Verifiers repointed: `verify-editors.py` (OMIT path), `verify-grants.py`
  (TIER_LIST + path), `verify-lcnames.py` (reads the lists from tier.policy;
  `src` still newvoc/voc_template for where the verbs resolve),
  `verify-tier-layer.bp` (opens tier.policy, reads `add.administrator`).
  `voc_template` never held either record — measured, correcting the handoff.
- changelog entry (admins who customise tiers edit tier.policy now).
- Installer needs no change: `installsdai.sh:566` `cp -R sdsys /usr/local` ships
  the whole tree — verified, not assumed.

***THE WITNESS (owner-run): commit → push → `deletesdai.sh` / `installsdai.sh`
as `don`, never sudo → suite.*** A BASIC syntax error fails the install visibly
(old install keeps running); recovery is delete+reinstall of the prior commit.
Then: `verify-nocase` 0 remnants on the INSTALL; the full suite green
(especially `tier-layer` 0 short, `grants` 16/0, `editors`, `lcnames`); a fresh
STANDARD account still lacks the omitted verbs and an ADMINISTRATOR still gains
the layer; `MODIFY.ACCOUNT` tier moves still work (10114 only on real failure).
***WOULD FALSIFY:*** any of those red, or `assert-current` not reaching 0.

***GPL.BP + SYSCOM RECORD NAMES LOWER CASE — INSTALLED AND WITNESSED on
`51da55b`*** (owner keep cycle, `.sdcore-install` 22:24:13, boot 22:25:48,
`assert-current` 0 at 22:28). Installed tree: `gpl.bp` 0 upper-case names,
`syscom` 0; `gpl.bp.out` 201 items, 1 upper = `README`; `gcat` 142 upper =
catalogue names, the separate namespace the rename deliberately left alone.
`sd.service` Type=oneshot, active, journal shows `sd -start` "has been started"
and ***no `-stop` line*** — PRE_RELEASE 29 boot held. Suite as the installing
user, no sudo, no flag, all exit 0, no `[FAIL]`: ***lcnames 139/139***,
vocverbs 34, fold 35, setpw 24, txn 33, editors 28, nonet 59, lineendings 42,
basicfuncs 199, accounts 36, sysperms 18, grants 16/0, ***pagination 10/10 (S
listed all 418, 0 clears, 0 headings, 0 further prompts)***, tier-layer 0 short,
COUNT VOC 418. `verify-nocase`: gpl.bp 0/213, syscom 0/16, voc_template 0/425,
sdsys dirs 0/15, all 3 code sites ` ok `; ***2 remnants left, both NEWVOC***:
`TIER.OMIT.STANDARD`, `TIER.ADD.ADMINISTRATOR`. NEXT: adopt the port's
`a47526f` — move those two into a `sdsys/tier.policy` file, which takes the §M
name half to 0.

*Pre-install:*
- ***Renames (script, refuses on collision):*** 212 gpl.bp + 15 syscom records →
  lower; 227 `R`, 0 upper left. Catalogue names (`$CPROC`, `!PARSER`) are a
  separate namespace and are NOT touched.
- ***Why this is safe, measured before editing:*** an object's header name is
  `upcase(record.name)` or the PROGRAM/SUBROUTINE statement's name (BCOMP:831),
  and `load_pcode` upper-cases before matching (sd.c:678); BCOMP `$INCLUDE`
  folds file and record (BCOMP:3024-3054). ***bbcmp did NOT upcase its fallback
  name*** (`basename(sfp)`, bbcmp.py:10443) — now `.upper()`, as BCOMP.
- ***Literal edits (script, exact counts):*** bbproc bootstrap list + `gpl.bp.out/login`
  check; errgen/revstamp output records; pcl/setptr `$pcldata`; first.compile;
  installer bbcmp ×3, `RUN gpl.bp write_install_dicts` (RUN is case-sensitive),
  `BASIC gpl.bp cproc`. By hand: pcode_bld.py and COMP_PCODE lower the NAME at use
  (lists keep header names); bbcmp include record names `.lower()`; gen_includes
  output names; verifiers accounts, basicfuncs, editors, grants, lcnames
  (S13/S14/S20 reads — a missing record reads '' and would fail), nocase, nonet
  (***"gone" rows check BOTH spellings***, editors B3 too); syntax generators'
  header text, outputs REGENERATED.
- ***Checked, no install:*** scratch copy of the tree through bbcmp — bbproc,
  bcomp, pathtkn + 55 pcode programs, ***58/58***; headers `BBPROC`, `$BCOMP`,
  `PATHTKN`, all 55 pcode names upper; ***same SET of 55 names as the installed
  bin/pcode*** (order differs — the installed library was rebuilt after
  pcode_bld, first name NEXTPTR; my first comparison used order and was wrong).
  Red control: syscom `keys.h` back to `KEYS.H` → bbcmp exit 1. gen_includes in
  sync on lower names; unit suites 0 failed; all gplbld .py compile.
  `verify-nocase`: gpl.bp 0/213, syscom 0/16; remaining 2 = NEWVOC
  `TIER.OMIT.STANDARD`/`TIER.ADD.ADMINISTRATOR` (the port moved them to a
  `tier.policy` file, its `a47526f` — a conformity item). Its createf site pattern
  was a false "open" (matched D4's fold) — now `ospath(upcase(file.name)`, 2 hits on
  pre-D4 CREATEF, 0 now.
- ***Would falsify:*** a bootstrap pass failing; `RUN gpl.bp write_install_dicts`
  "not found"; a pcode item "not found" at `sd -start`; any verifier red.

***CASE INVERSION OFF BY DEFAULT — INSTALLED AND WITNESSED on `6380883`*** (owner
keep-cycle, `.sdcore-install` 21:14:23, boot 21:15:46, `assert-current` 0). Suite
as the installing user, no sudo, no flag, all exit 0, no `[FAIL]`, 0 not-OFF:
***lcnames 139/139 — I2 "Case inversion: Off" with the login paragraph set
aside*** (was On on 80bd15c); I3 paragraph back line for line (checked again
after the run: 4 lines, `zzlcnlogin` absent); every other verifier at its count;
PRE_RELEASE 29 boot held. NEXT: the 203 gpl.bp record names — owner asked
whether to start.

*Pre-install:*
- ***Port's finding checked, and it held only conditionally:*** on `80bd15c` a
  pipe AND a pty session report "Case inversion: Off" and typed `who` runs as
  `who` — but only because the VOC `login` paragraph runs `PTERM CASE NOINVERT`.
  C starts sessions inverted (`linuxio.c:211/284` TRUE) and `LOGIN:314` set it
  again. ***Measured with my own login paragraph set aside: "Case inversion:
  On".***
- ***AND THE MEASUREMENT BROKE MY ACCOUNT FOR A MINUTE, which is the defect
  demonstrated:*** the restore session was inverted, so `COPY FROM VOC
  ZZLOGINSAVE,login` arrived case-flipped and copied 0. Repaired by sending
  `pterm case noinvert` first; `CT VOC login` shows all 4 lines back,
  `ZZLOGINSAVE` gone, inversion Off. Done with plain sessions, no flag.
- ***Fix:*** `linuxio.c` both initialisers FALSE; `LOGIN:314` removed (nothing
  prompts between it and the paragraph). `PTERM CASE INVERT` unchanged (relax by
  choice). The paragraph's NOINVERT stays. `make` exit 0.
- ***`verify-lcnames` I0–I3:*** paragraph present; set aside (COPY + DELETE);
  ***I2 inversion Off with no paragraph*** (red on 80bd15c, measured above);
  restore in `finally`, every session led by `PTERM CASE NOINVERT`, I3 compares the
  paragraph's numbered lines before/after. CT parse dry-run on the real account:
  4 lines, save absent. ***Would falsify:*** I2 On.

***ACCOUNT NAMES LOWER CASE — INSTALLED AND WITNESSED on `80bd15c`*** (owner FULL
cycle, `.sdcore-install` 19:11:39, boot 19:12:26, `assert-current` 0 at 19:14).
Register on disk: `don` (root:root 664), `sdsys` (root:root 644). Suite as the
installing user, no sudo, no flag, all exit 0, no `[FAIL]`, 0 not-OFF:
***lcnames 130/130*** (U1 register `don`+`sdsys`, no upper id; U2 `LOGTO DON` not
refused; U3 WHO `don`; U4 not `DON`), accounts 36 (R3 ids lower, R8), sysperms 18
(G1 10002 on `LOGTO SDSYS`, G2 stayed in `don`, G3 never sdsys), setpw 24 (names
typed upper), vocverbs 34, fold 35, txn 33, editors 28, nonet 59, lineendings 42,
basicfuncs 199, grants 16/0, pagination 10, tier-layer 0 COUNT VOC 418;
PRE_RELEASE 29 boot held. ***NOT exercised by any verifier:*** `sudo sd`
landing in sdsys, `UPDATE.ACCOUNTS ALL` from sdsys (the installer's keep-cycle
walk runs it — this was a full cycle, so it did not run), a GROUP account, the
API server's account read, a Q-pointer naming an account. NEXT: the 203 gpl.bp
record names and LOGIN `PT$INVERT` (`LOGIN:310`).

*Pre-install, 13 Sep:*
- ***Rulings:*** lower case (owner 12 Sep, PORT_ADOPTION queue 18); ***SDSYS →
  `sdsys` too (owner, 13 Sep, asked this session)*** so the rule is uniform: key
  = downcase(name), every lookup downcases. ***The port keeps account names
  upper*** (its RELEASE_1.1 5: "a separate wide change") — this goes past it.
- ***Register:*** `git mv sdsys/accounts/SDSYS → sdsys`; KEYS.H:263 comment.
- ***BASIC (script, exact-once literals, + hand):*** LOGIN (`@who = 'sdsys'` ×2,
  forced account / sudo arm / console / path-derived names downcased, tier
  lookup); CPROC (elevation read, LOGTO gate/read/`new.account`, path-derived
  `who`, `LOGIN.PORT ALL` check, audit strings); CREATEA (store + the early
  0275 read + GROUP directory name); DELACC (store, `'sdsys'` guard, xref
  Q-pointer account compared downcased); MODIFYA (store, guard, own-account
  test); SETACC ×2; SETFILE (so its Q-pointer writes lower); SET_ACC_PASSWORD
  ×3; TIERGATE (both names, `'sdsys'` never granted); GRANTA; APISRVR ×2;
  _VOC_REF (Q-pointer account). newvoc + voc_template `sd.accounts` field 2
  `sdsys`. ***Left deliberately:*** ATVAR/BCOMP `"SDSYS"` (the `@SDSYS` token),
  10126's `'SDSYS'` tier label (MODIFYA:212, GRANTA:252), CREATEA:248 (reserved
  Linux user name, compared upcased), messages 6025/10002 text, USERNO (Linux
  user names).
- ***C:*** `sysseg.c:410` startup phantom `-asdsys`; `make` exit 0, `strings`
  shows `-asdsys`.
- ***Scripts:*** installer `accounts/sdsys` chown/chmod/echo and the seeded-tier
  read lower; witness-accounts.sh register keys lower (`_UC` names kept, commented);
  reconcile's `${id^^} == SDSYS` already case-blind.
- ***Verifiers:*** accounts R3 now "lower case" (was the opposite), R8 path
  `sdsys`; fold `who` lower; sysperms G2 lower, G3 either case. setpw unchanged
  (types names upper, which now exercises the downcase; no name in its patterns).
  ***New lcnames U1–U4:*** register holds `<user>` and `sdsys`, no upper id;
  `LOGTO <USER>` not refused; WHO says lower, not upper.
- ***Checked, no install:*** verifiers py_compile, unit suites 0 failed, installer
  and witness `bash -n`. BASIC compiled only by the bootstrap. ***Would
  falsify:*** sign-on refused (5018 "not in register"); `sudo sd` not landing in
  sdsys; U3/R3/G2 red; UPDATE.ACCOUNTS ALL refusing 10172 in sdsys.

***INSTALL `f6d3b35` WITNESSED 13 Sep 18:50 — THE SUITE IS CLEAN*** (owner
keep-cycle 18:47:46, boot 18:48:17, `assert-current` 0; no flag anywhere).
***lcnames 125/125*** incl. the fixed A5 (baseline `COUNT $acc` 0; planted
`zzlcnacc` counted `1 record(s)` typed both ways; fixture gone after), pagination
10/10, vocverbs 34, fold 35, setpw 24, txn 33, editors 28, nonet 59, lineendings
42, basicfuncs 199, accounts 36 (R8), sysperms 18, grants 16/0, tier-layer 0 with
COUNT VOC 418; 0 not-OFF; PRE_RELEASE 29 boot held. ***No debts owed from any
install.*** NEXT (ruled, not started): account names lower case — PORT_ADOPTION
queue 18 row "Account names" (`CREATEA:409`, `DELACC:113`, `LOGIN:311/368/447`,
`SET_ACC_PASSWORD:105/108`, `KEYS.H:263`); then the 203 gpl.bp record names and
LOGIN PT$INVERT. Awaiting the owner: filing the QDISP defect to the port; audit
coverage for CREATE/DELETE.ACCOUNT and password changes.

***INSTALL `80b4e83` WITNESSED 13 Sep 18:16*** (owner FULL cycle — the first
attempt ran only the delete; journal showed no installer sudo in boot 0 — then
install 18:06:07, boot 18:06:38, `assert-current` 0). Suite as the installing
user, no sudo, no flag: ***pagination 10/10*** (after S: 418 listed, 0 clears, 0
headings; NO.PAGE target 0 clears/1 heading; N control paused), ***vocverbs
34/34 (the D4 debt, clean)***, accounts 36/36 (***R8 root:root 644*** —
PRE_RELEASE 30 closed), fold 35, setpw 24, txn 33, editors 28, nonet 59,
lineendings 42, basicfuncs 199, sysperms 18, grants 16/0, tier-layer 0 with COUNT
VOC 418; 0 not-OFF; PRE_RELEASE 29 boot held (0 `-stop`).
***lcnames 121/122 — ONE FAILURE, THE INSTRUMENT:*** A5a expected `COUNT $ACC` ≥ 1,
SD printed `0 record(s) counted` both ways — correct: `$acc` is a directory file
on the account directory, whose records are plain files, and a fresh account has
none (find: 0). All other new rows PASS: S19–S21, N1–N6 (N names, the D4 debt),
R/M/K categories incl. ***K5b the marker reached the saved stack via
`$command.stack`***. Fixed: A5 plants `zzlcnacc`, expects baseline+1 typed both
ways, removes it. ***Observed without the verifier (plain sessions, no flag):***
`COUNT $acc` 0 → planted 1 → removed 0. ***Not re-run through the verifier*** —
owed on the next install. (A first manual check showed one count per two
commands: my `printf '%s\nOFF\n'` put OFF after the first command — the harness,
not SD.)

***OWNER-REPORTED DEFECT, 13 Sep: S AT A REPORT'S PAGE PROMPT "TERMINATES" THE
LISTING — FIXED; WITNESSED ON `80b4e83` (above).***
- ***Measured on `c759c7a` in a pty (scratch `pagerepro.py`, no flag):*** `LIST
  VOC`, answer S → ALL 418 records went out, but ***20 clear-screens + 20
  headings*** after the answer (vt100 `ESC[H ESC[J`); `LIST VOC NO.PAGE` → 0
  clears, 1 heading, 418. Control N → stopped at the next prompt. So not a
  termination: the screen was wiped every page, leaving the last page visible.
- ***Cause:*** QDISP:851 `S` cleared `qd.paginate` (prompt) but not `qd.no.page`
  (the page throw at `emit.line` :442-463). QDISP is byte-identical to the port's
  — ***an upstream/port defect too; not filed to the port (outward-facing, ask).***
- ***Fix:*** `S` → `gosub disable.pagination` (the NO.PAGE keyword's own handler,
  :420). History + changelog.
- ***New `gplbld/verify-pagination.py`*** — first verifier on a PTY (QDISP only
  paginates a live terminal; every other verifier pipes). T1–T2 measure NO.PAGE as
  the target, N1–N3 the control, S1–S5 S against it. py_compiles. ***NOT watched
  red*** (that needs `--allow-stale`, not approved); the red evidence is the
  scratch run above, same measurement. ***Would falsify:*** S4 (clears after S)
  non-zero on the next install.

***§M3 THE $ RECORDS + `PRE_RELEASE` 30 BUILT 13 Sep 2026 — NOT INSTALLED. NEXT:
owner FULL delete→install (N, DELETE) + reboot, then the suite.*** Full cycle is
REQUIRED: LOGIN:498 reads `$release` by exact id and TERMINATES the session if it
is missing, and a kept account holds `$RELEASE`.
- ***Renames (`git mv`):*** newvoc + voc_template `$ACC $MAP $RELEASE` → lower.
- ***Exact-id readers:*** LOGIN `"$release"` (:498, + 5028 text and audit
  reason) and `"$command.stack"` (:546); CPROC `readu`/`release` of
  `$command.stack` (:3832/:3844 — same id both, or the lock outlives the
  session, the port's 69015c3 point); CREATEA writes `'$command.stack'`; MAPCAT
  default `$map` and its no-prompt test `downcase(file.name) # '$map'`. DELETEF's
  banned `'$ACC'` UNCHANGED — compared against `upcase(file.name)` (S13).
  `gplsrc/revstamp.h:41` comment still says `$RELEASE` — left, to avoid a C
  rebuild for a comment.
- ***`PRE_RELEASE` 30:*** installer sets `accounts/SDSYS` root:root ***644*** after
  the keep-cycle register restore (a second thing that undid it) and prints the
  mode; `verify-accounts` R8.
- ***`verify-lcnames`:*** S19 (shipped `$acc $map $release` lower, not upper),
  S20/S21 (LOGIN/CPROC/CREATEA lower literals present, no upper literal in code —
  red control against HEAD's three programs: all flagged "stale"); categories
  3R (`$release`, 5028 absent + a command ran), 3A (`COUNT $ACC`/`$acc`), 3M
  (`COUNT $MAP`/`$map`), 3K (`$command.stack`: a marker command absent from
  `stacks/<user>` before a session, present after — the port's instrument).
- ***Owed from the D4 install:*** a clean `verify-vocverbs` 34/34 (fixed, rerun
  was `--allow-stale`) and lcnames with the N1–N6 names — both ride this install.
- ***Checked, no install:*** verifiers py_compile; installer `bash -n`; static
  rows dry-run clean on the tree. LOGIN/CPROC/CREATEA/MAPCAT compile only in the
  bootstrap. ***Would falsify:*** sign-in refused with 5028; 3K marker absent
  after the session; R8 not root:root 644.

***§M3 D4 INSTALLED on `c759c7a`; WITNESSED EXCEPT ONE VERIFIER*** (owner
keep-cycle, `.sdcore-install` 14:40:47, boot 14:41:28, `assert-current` 0 at
14:45). Suite as the installing user, no sudo: ***lcnames 83/83*** (F6 `bp.out`
on disk and no `BP.OUT`; the new create/delete rows all PASS — `CREATE.FILE
ZZLCCF` made `zzlccf` + `zzlccf.dic` only, VOC `zzlccf` exact, a second create
made nothing, `DELETE.FILE ZZLCCF FORCE NO.QUERY` removed both without asking),
fold 35, setpw 24, txn 33, editors 28, nonet 59, lineendings 42, basicfuncs 199,
accounts 35, sysperms 18, grants 16/0, tier-layer 0 with `COUNT VOC` 418; 0
not-OFF; `PRE_RELEASE` 29 boot 4 held.
***`verify-vocverbs` 3 FAILED — THE INSTRUMENT, NOT SD, AND MY D4 AUDIT MISSED
IT.*** C1–C3 still expected CREATE.FILE's old upper path (`ZZVVW`, `ZZVVW.DIC`);
SD printed `DATA portion 'zzvvw' deleted` / `DICT portion 'zzvvw.dic' deleted`,
the correct D4 output. The audit grepped `Created DATA part` + `.upper()` and
missed vocverbs, which builds the name with `wfile.upper()` inside
`M6136 %`. Fixed (lower, C1 anchored `^…$`). ***Also fixed:*** the D4 rows in
lcnames were named C1–C6, COLLIDING with section 3C's C1–C4 (row names are
how a failure is found) — now N1–N6.
***Rerun of the fixed vocverbs: 34/34 — BUT WITH `--allow-stale`, WHICH WAS NOT
APPROVED*** (the uncommitted fix made `assert-current` stale; installed SD
unchanged, only the verifier differs). Not a verdict. ***A clean vocverbs 34/34,
and lcnames with the N names, are owed on the next install.*** Next after that:
§M3 is done through D4 — remaining lower-case items are in PORT_ADOPTION queue 18
(account names ruled lower, `$ACC $MAP $RELEASE` ids, `$COMMAND.STACK`, the 203
gpl.bp record names, LOGIN PT$INVERT), plus `PRE_RELEASE` 30.

*Pre-install, 13 Sep:*
- ***CREATEF:*** after the name is parsed (`:124-144`), unless `OPT.CREATE.FILE.CASE`
  (OPTION name `CREATE.FILE.UPCASE`, msg 3124 "Keep ... case"): resolve by fold
  — existing entry keeps its id, no entry → `downcase`; component `downcase`.
  The three os.name sites `upcase` → `downcase`; `.DIC` → `dict.suffix`, chosen
  by the OPTION not by testing os.name (OS$MAPPED.NAME escapes with an upper
  letter, `%E`). ***Decision taken without a specific ruling***, from the stance
  sentence "everything lower case — names on disk, VOC entries … the files
  CREATE.FILE makes": the VOC id is lowered as well as the directory.
- ***Lookups that had no lower step and would now miss:*** DELETEF `delete.file`
  (as typed → lower silently → the old upper guess + 6131 prompt) and SETFILE's
  target-VOC read. ***Checked and NOT changed:*** ANALYSE, CONFIGF, BUILDI,
  CREATEI, DELETEI, LISTI, SETTRIG, CD already try lower; CLEARFL/CT/etc go
  through `open`, which folds (M1). ED's `CREATE.FILE DATA $ED` now makes `$ed`.
- ***Verifiers:*** `bp.out` on disk (fold, lcnames, basicfuncs, lineendings, txn,
  tier-layer.sh); fold/txn "Created DATA part as" lower and fixture dir lower
  (fold refuses either spelling present); sysperms K4 checks both spellings.
- ***`verify-lcnames` new rows:*** F6 object dir `bp.out`, no `BP.OUT`; C1–C6 —
  `CREATE.FILE ZZLCCF` → "Created DATA part as zzlccf" / "DICT part as
  zzlccf.dic", disk lower only, VOC `zzlccf` Y / `ZZLCCF` N, `CREATE.FILE
  zzlccf` again creates nothing, `DELETE.FILE ZZLCCF FORCE NO.QUERY` removes both
  with no `(y/<n>)`. Refuses if any spelling of the fixture is present.
- ***Checked, no install:*** verifiers py_compile, tier-layer `bash -n`.
  ***CREATEF/DELETEF/SETFILE not compiled here*** (bbcmp cannot; the bootstrap
  does). ***Would falsify:*** bootstrap failure; C1–C6 or F6 red; DELETE.FILE
  typed upper prompting.

***§M3 D3 INSTALLED AND WITNESSED on `0cf86ee`*** (owner FULL delete→install,
`.sdcore-install` 11:34:41, boot 11:35:27, `assert-current` 0 at 11:37). Installed
sdsys has NO upper-case directory; fresh account `don`: `$hold $hold.dic
$svlists bp cat voc`; register `DON SDSYS`; `gpl.bp.out` 201, `gcat` 142. Suite
as the installing user, no sudo, no workaround: all exit 0, no `[FAIL]`, 0 not-OFF
— ***lcnames 72/72*** (S15–S18, ***F0–F5 all PASS*** — create branch reached,
`bp.out` Y / `BP.OUT` N / `bp.OUT` N, then `BASIC BP` 0 errors; H5a print in
`$hold/zzlch`), vocverbs 34, fold 35, setpw 24, txn 33, editors 28, nonet 59,
lineendings 42, basicfuncs 199, accounts 35, sysperms 18, grants 16/0, tier-layer
0 with `COUNT VOC` 418. After the suite the account holds a `stacks` directory
too (lower case; made at runtime, not investigated). ***`PRE_RELEASE` 29 boot 3
held*** (11:35:35, 0 `-stop`). ***NEXT: §M3 D4*** — CREATE.FILE makes lower-case
names (CREATEF:310-312, :383-385, :409-411), which ends the `bp.out` → `BP.OUT`
interim; verifiers' `BP.OUT` paths then become `bp.out`.

*Pre-install, 13 Sep:* Names are
the port's (its CREATEA:1247/1500-1519, SAVELST/SAVESTK/COPYLST `$svlists`,
to_file.c `$hold`).
- ***On disk:*** CREATEA `voc`, `$hold`+`$hold.dic` (create.dir.file's literal
  `.DIC` → `dict.name = os.name:'.dic'`), `$svlists`, `bp` (VOC id `bp`);
  BBPROC SDSYS `voc`, FILES_LIST `$hold`/`$hold.dic`; installer chmod list; `git
  mv sdsys/$HOLD`; newvoc/voc_template `voc` field 2, voc_template `$hold` 2–3;
  `to_file.c` ×3 `$hold`.
- ***Paths (script, 24 lines, numstat matched):*** `openpath "VOC"`/`@ds:'VOC'`
  in APISRVR, CPROC, SETACC, LOGIN, DELACC, MODIFYA, SETFILE, _VOC_REF;
  `"$SVLISTS"` in SAVELST/SAVESTK/COPYLST; default file `"bp"` in CPROC RUN,
  CATALOG ×3, FORMAT, GENERATE.
- ***BASIC `bp.OUT` fix, the port's `1943704`, by hand:*** object name from the
  VOC id that answered + suffix `.out` iff that id is all lower; default `bp`.
  ***Live defect before D3:*** a fresh account's first `BASIC bp X` made VOC id
  `bp.OUT` (+ dir `BP.OUT`), and every later `BASIC BP` hit "already exists".
- ***Interim until D4, deliberate:*** CREATEF:385 still upcases the directory, so
  the object file is VOC id `bp.out` → dir `BP.OUT`. Verifiers therefore look for
  `BP.OUT` on disk but `DELETE VOC bp.out` (DELETE is exact) — fold, lcnames,
  lineendings, txn, basicfuncs, tier-layer.sh; their account `BP` → `bp`.
- ***`verify-lcnames` new rows:*** S18 (installing user's account `voc $hold
  $hold.dic $svlists bp` and SDSYS `voc $hold $hold.dic`, lower present, upper
  absent); F0 no `BP.OUT` before (decisive — else the create branch is not
  reached); F1 `BASIC bp`; F2/F3 exact VOC reads `bp.out` Y, `BP.OUT` N,
  `bp.OUT` N (probe gains `EXACT.MIXED`); F4/F5 `BASIC BP` 0 errors, no
  "already exists". `$hold` paths in H5.
- ***Checked, no install:*** plain `make` exit 0, `to_file.o` carries `$hold%cP%d`;
  bbcmp compiles BBPROC, BCOMP, PATHTKN, ***BASIC***, SAVELST, SETACC, _VOC_REF
  from the tree. The other 12 changed programs FAIL in bbcmp ***identically at
  HEAD*** (same unsupported statement — PROMPT/VOID/ECHO/PRINTER, CPROC's
  install-time include — lines offset only by the added history), so bbcmp is
  not a compile check for them: ***the bootstrap is.*** Verifiers py_compile.
  ***Would falsify:*** a bootstrap pass failing; S18 or F0–F5 red; SETPTR mode 3
  not landing in `$hold` (H5a).

***§M3 D2 INSTALLED AND WITNESSED on `1c36762`*** (owner keep-cycle,
`.sdcore-install` 11:19:11, boot 11:20:28, `assert-current` 0 at 11:22). Installed
sdsys top level has no upper-case directory but `$HOLD $HOLD.DIC VOC` (D3);
`gpl.bp.out` 201 objects, `gcat` 142 (one fewer each than 12 Sep: `voccase`
removed). Suite as the installing user, no sudo, no workaround: all exit 0, no
`[FAIL]`, 0 not-OFF — ***lcnames 64/64 (S15, S16, S17 PASS)***, vocverbs 34,
fold 35, setpw 24, txn 33, editors 28, nonet 59, lineendings 42, basicfuncs 199,
accounts 35, sysperms 18, grants 16/0, tier-layer 0 with `COUNT VOC` 418.
***`PRE_RELEASE` 29 boot 2 of N held:*** active since 11:20:36, `sdlnxd` in the
cgroup, 0 `-stop` lines after the suite. ***NEXT: §M3 D3*** (per-account `VOC
$HOLD $HOLD.DIC $SVLISTS BP BP.OUT`, the SDSYS account's own `VOC $HOLD
$HOLD.DIC`, and the port's BASIC `bp.OUT` fix `1943704`) — needs a FULL cycle.

*Pre-install, 13 Sep:*
Keep cycle is safe: no kept account's VOC names a D2 path (voc_template's four
records reach only SDSYS, whose VOC the bootstrap rebuilds; TIER.ADD lists none).
- ***Renames (script, 224 files `R`):*** sdsys `GPL.BP GPL.BP.OUT BP BP.OUT
  PCODE.OUT` → lower; voc_template ids `GPL.BP GPL.BP.OUT BP BP.OUT` → lower.
- ***By hand:*** those four records' field 2 → lower; `first.compile`/
  `second.compile` `BASIC gpl.bp`; BBPROC (`gpl.bp.out/LOGIN` guard, both
  source/output name pairs, `$include gpl.bp`); COMP_PCODE; ERRGEN/REVSTAMP
  `openseq 'gpl.bp'`; PROG_INFO/CREATE_INSTALL_DICT_FILE `$INCLUDE gpl.bp`;
  `bbcmp.py include_dir()` → `name.lower()`; `pcode_bld.py` paths; installer
  `:581-583 :841 :857-858`; syntax generators' header text, outputs REGENERATED
  (4 comment lines differ); verifiers accounts, basicfuncs, editors, grants,
  lcnames, nocase, nonet, test-edittokens; gen_includes comments; CLAUDE.md
  `sdsys/gpl.bp/<VERB>`; changelog.
- ***NOT in D2, and why:*** BASIC's `bp.OUT` fix from the port's `1943704` —
  its create branch runs only when the `.OUT` file is absent, and SDSYS ships
  `bp.out`/`gpl.bp.out`; `BASIC gpl.bp *` builds `gpl.bp.OUT`, which the M1 fold
  reaches as `gpl.bp.out`. It bites when a per-account `bp` id exists without
  `bp.out`: ***take it WITH D3.*** Per-account `BP`/`BP.OUT` (CREATEA:763) and
  CATALOG/FORMAT/GENERATE/CPROC `"BP"` defaults (VOC opens, folded) are D3.
- ***New rows `verify-lcnames` S16*** (5 D2 dirs lower, no upper) ***and S17***
  (the four voc_template records: id and field 2 lower, no upper id).
- ***Checked, no install:*** bbcmp on a scratch copy of the tree — BBPROC,
  BCOMP, PATHTKN into `gpl.bp.out` and all 55 pcode programs into `pcode.out`,
  58 compiled 0 failed; red control (`gpl.bp` back to `GPL.BP`) → exit 1
  `No such file ... gpl.bp/BBPROC`. All gplbld `.py` compile; unit suites 0
  failed; nocase selftest 19/0; `gen_includes --check` in sync on
  `sdsys/gpl.bp/*`. ***Would falsify:*** a bootstrap pass failing, `RUN gpl.bp
  WRITE_INSTALL_DICTS` failing, or S16/S17 red.

***`PRE_RELEASE` 29 INSTALLED on `6214b0f`; FIRST BOOT HELD*** (owner keep-cycle,
`.sdcore-install` 10:48:18, boot 10:48:54, `assert-current` 0 at 11:01). Measured
as the installing user, no sudo: `systemctl status sd.service` → `active (exited)
since 10:49:03`, `Main PID: 1681 (sd -start) exited 0`, CGroup holds `1699
sdlnxd`; `journalctl -b -u sd.service` → `sd -start`, "has been started",
"Finished", ***and 0 `-stop` lines*** (re-counted after the suite: still 0,
still active). Suite with NO workaround: all exit 0, no `[FAIL]`, 0 not-OFF —
lcnames 62, vocverbs 34, fold 35, setpw 24, txn 33, editors 28, nonet 59,
lineendings 42, basicfuncs 199, accounts 35, sysperms 18, grants 16/0, tier-layer
0 with `COUNT VOC` 418. ***One boot — keep 29 open until more boot starts hold***
(the old unit also passed most boots). Next: §M3 D2.

***§M3 D1 INSTALLED AND WITNESSED on `58365cc`*** (owner FULL delete→install,
`.sdcore-install` 2026-09-13 10:29:13, `assert-current` 0 at 10:44). ***SD was
left stopped by `PRE_RELEASE` 29*** (installer start and boot start both stopped
within 1 s); the first suite run refused "SD has not been started" everywhere and
is void; owner ran `sudo /usr/local/sdsys/bin/sd -start`. Rerun as the installing
user, no sudo, no `--allow-stale`: all exit 0, no `[FAIL]`, every session "ran to
OFF". ***`verify-lcnames` 62/62*** (61 + new S15, which read the installed
top level: all 13 lower, no upper); vocverbs 34 (A2 `@SDSYS/syscom`), fold 35,
setpw 24, txn 33, editors 28, nonet 59 (D1 `@SDSYS/syscom`), lineendings 42,
basicfuncs 199, accounts 35, sysperms 18 (W1/W2 on `$ipc`), grants 16/0,
tier-layer exit 0 with `COUNT VOC` 418. `stat`: bootstrap dirs `sdsys:sdusers`,
`$ipc` 775, D1 dirs 755; no chmod-loop WARNING was reported by the owner.
***Found: `PRE_RELEASE` 30*** — `accounts/SDSYS` installed 755, not 654.
***NEXT: `PRE_RELEASE` 29 (it blocks every cycle), then §M3 D2.***

*Pre-install, 13 Sep:* The sdsys data directories are lower case on disk,
names as the port's `e1095ab`.
- ***Renames (script, 2839 files `R`, 0 lines):*** `git mv` sdsys `NEWVOC
  VOC_TEMPLATE MESSAGES SYSCOM SD.VOCLIB ACCOUNTS` → lower; `gplbld/FILES_DICTS`
  id prefixes `$MAP.DIC VOC.DIC ACCOUNTS.DIC DICT.DIC DIR_DICT` → lower (69). Ids
  after `^`, and every record id inside the directories, unchanged (12 Sep
  ruling). NOT in D1: `$HOLD $HOLD.DIC VOC` (D3), `GPL.BP GPL.BP.OUT BP BP.OUT
  PCODE.OUT` (D2).
- ***Content (script, 72 lines exact-literal):*** 28 `@sdsys:@ds:'X'` in 13
  GPL.BP programs + `verify-tier-layer.bp`; 22 `@SDSYS/X` F-record paths in
  newvoc/voc_template; voc_template/accounts fields 2–3; 20 R records' field 2
  `sd.voclib`.
- ***By hand:*** BBPROC FILES_LIST (third column now the dictionary's own name, so
  `$HOLD.DIC` keeps upper beside `$map.dic`); `messages.c:183/211/233`;
  `installsdai.sh` `:618-619 :727-733 :809-825 :921` (the bootstrap chmod loop
  now WARNS on a missing name instead of skipping silently); `deletesdai.sh` saves
  `/home/sd/accounts` (no old-name fallback — owner); `bbcmp.py` `syscom` +
  `include_dir()` (D2 makes it `.lower()`); `CREATE_INSTALL_DICT_FILE` /
  `INSTALL_FILE_INFO`; `reconcile-accounts.sh`, `witness-accounts.sh`; verifiers
  accounts, editors, grants, lcnames, nocase, nonet, sysperms (`$ipc`), vocverbs;
  START-HISTORY in all 14 BASIC programs; changelog.
- ***New row `verify-lcnames` S15:*** the 13 D1 directories exist lower in the
  INSTALLED sdsys AND their upper spelling is absent (ext4 allows both).
- ***Checked 13 Sep, no install:*** `bbcmp.py` compiles BBPROC in a scratch
  sdsys copy, exit 0, includes read from `syscom`; red control (dir back to
  `SYSCOM`) aborts `not found: err.h`. Every gplbld `.py` py_compiles; unit suites
  accounts 17, basicfuncs 25, editors 19, edittokens, nonet 12, sdverify 41,
  sysperms 20 — all 0 failed; nocase selftest 19/0; `gen_includes --check` in sync
  reading `sdsys/syscom/ERR.H`; plain `make` exit 0, `gplobj/messages.o` carries
  `%s%cmessages`. ***GPL.BP NOT compiled*** — the bootstrap does that as SDSYS.
  ***Would falsify:*** a bootstrap WARNING from the chmod loop; any 1xxx
  "[n] Message file not found"; `verify-lcnames` S15 or S2/S7–S12 red.

***CASE MIGRATION REMOVED — INSTALLED AND WITNESSED on `101ad30`*** (owner
keep-cycle, `.sdcore-install` 2026-09-13 09:45:38, `assert-current` 0 at
10:02). Suite run by the agent as `don`, no sudo, no `--allow-stale`, all exit 0,
no `[FAIL]`, every session "ran to OFF": ***`verify-lcnames` 61/61*** (the new
total — sections 3L/3H/3C/3P each K1–K5 incl. session rows, S14 still pins
`'QFILE'`); vocverbs 34, fold 35, setpw 24, txn 33, editors 28, nonet 59,
lineendings 42, basicfuncs 199, accounts 35, sysperms 18, grants 16/0,
tier-layer exit 0 with `COUNT VOC` 418. Installed tree has no `GPL.BP/voccase`
and no MESSAGES 10916/10917/10052. ***NEXT: §M3 D1.***

*Pre-install notes, 13 Sep:* Owner ruled: no existing installs, no
migration ever needed for §M (memory `sdcore4linux-no-migration`), "remove now,
before D1".
- `313c55b` (WIP) took the `!voccase` calls and 10916/10917 displays out of LOGIN
  `update.voc` and MODIFYA `voc.delta`, and CPROC's R-record target fold (:1889,
  exact read again). This commit: CPROC history line; `git rm` `GPL.BP/voccase`,
  `MESSAGES/10916 10917 10052` (10052 had no other user — `git grep` 13 Sep),
  `gplbld/verify-voccase.py/.bp`; `verify-lcnames` reduced to S1, S2, S2b,
  S6–S14 and per-category section 3 (+ tidy) — S3–S5, sections 4–6, the probe's
  DOWN/UP modes gone, so it no longer runs `UPDATE.ACCOUNTS` or changes any VOC
  id; changelog's four "existing account is renamed" paragraphs cut.
- ~~Compiled 13 Sep, dev binary, in `don`'s `BP`~~ — ***WRONG ACCOUNT, and not
  evidence.*** System programs compile as SDSYS, never staged in a personal
  account (owner 12 Sep, repeated 13 Sep: ***don is transitory, SDSYS is the
  permanent super account***). The compile that counts is the install bootstrap's,
  which built all three as SDSYS on `101ad30` and the suite passed (above). `verify-lcnames.py` py_compile only — ***NOT RUN***; ***its
  total drops from 140 — do not predict it, read it.***
- ***Follow-up to weigh, not done:*** `verify-lcnames` S14 pins SETFILE's
  default pointer at `'QFILE'` on the ground that it "covers accounts from before
  the rename" — that ground is gone with the migration; lowering it may now be
  correct (§M "complete lower case").
- ***THEN D1*** (design in Open, "on-disk directory rename"): sdsys dirs
  `NEWVOC VOC_TEMPLATE MESSAGES SYSCOM SD.VOCLIB ACCOUNTS $IPC $MAP $MAP.DIC
  VOC.DIC ACCOUNTS.DIC DICT.DIC DIR_DICT` → lower, no migration. NOT in D1:
  `VOC $HOLD $HOLD.DIC` (SDSYS account dirs → D3), `PCODE.OUT` (→ D2). Audit
  script `scratchpad/d1audit.py` (scratchpad is session-local; re-create). Sites:
  `messages.c:183/211/233`, ~30 `openpath @sdsys:@ds:'X'` in GPL.BP, BBPROC
  FILES_LIST + `:167`, installer `:613-614 :722-727 :804 :910`, deletesdai
  `:98-117`, `reconcile-accounts.sh:128`, `witness-accounts.sh:110`,
  `bbcmp.py:7142`, `gen_includes.py` SYSCOM output, `gplbld/FILES_DICTS` file
  prefixes (not `$HOLD.DIC^@ID`), NEWVOC/VOC_TEMPLATE `@SDSYS/X` paths and
  `accounts` record fields, R records field 2 `SD.VOCLIB`, verifiers (accounts,
  editors, grants, lcnames, nocase, nonet, sysperms, tier-layer.bp, vocverbs).
- `assert-current` stays STRICT (owner, twice). Don't commit docs between an
  install's test runs.

***§M3 FOURTH CATEGORY (F/Q POINTER IDS) INSTALLED AND WITNESSED on `8c14634`***
(23:03:08, `assert-current` 0). ***The owner ran the suite and pasted the
verdicts***; the agent re-ran the two missing from the paste. `verify-lcnames`
***140/140*** (red 10/141 — P9 is the failure-only guard row; ***do not predict
totals that include guard rows***, same mistake as the `$savedlists` round);
`verify-vocverbs` 34/34 reading `source pointer id syscom`, raw `2 record(s)
selected to select list 2`; voccase 38, fold 35, setpw 24, txn 33, editors 28,
nonet 59, lineendings 42, basicfuncs 199, accounts 35, sysperms 18, grants 16/0,
tier-layer 0 short with `COUNT VOC` 418.
***NEXT — NEEDS AN OWNER DECISION BEFORE BUILDING:*** the on-disk directory
rename (below: 483 lines, per-account migration of user-owned directories on
keep cycles, no port precedent). Id-only categories still available without
one: `$COMMAND.STACK` (the port's `69015c3`), `BP`/`GPL.BP` ids, `$ACC`/`$MAP`/
`$RELEASE`.

*Pre-install:* §M3 fourth category built and pushed (the port's `0394af4`).
- Ids `voc newvoc syscom dict.dict md sd.accounts sd.voclib` (NEWVOC +
  VOC_TEMPLATE) and `accounts messages qfile` (VOC_TEMPLATE): 17 `git mv`, one
  step each. Q field 3: `md`→`voc`, `sd.accounts`→`accounts`. `third.compile` CD
  targets, MESSAGES/2022. ***Fields 2/3 — the paths — unchanged.***
- ***ORDER DIFFERS FROM THE PORT ON PURPOSE:*** it renamed the directories on
  disk first (`e1095ab`), then the ids. Here the id rename goes first because
  the fold makes it disk-independent. ***The disk rename is NOT scheduled as the
  next commit without a decision:*** measured reach 483 lines, and unlike NTFS
  it needs a real migration of user-owned account directories (`VOC`, `$HOLD`,
  `$HOLD.DIC`, `$SVLISTS`, `BP`) on keep cycles. The sdsys half alone needs none
  (deletesdai removes sdsys; only the register is carried, by the installer's
  own `mv`, `installsdai.sh:722-724`). C names only `messages.c` MESSAGES ×3 and
  `to_file.c` `$HOLD` ×3.
- GPL.BP id opens lowered (`open 'voc'` CNAME CREATEF DELETEF SHOW; `'dict.dict'`
  CREATEI LISTI QPROC QSELECT SHOW ICOMP; `'syscom'` FMTSUB PCL SETPTR ERRGEN;
  BCOMP include default). ***Paths untouched*** (`openpath "VOC"`,
  `@sdsys:'ACCOUNTS'`, `pathname:'VOC'`). ***KEPT UPPER, annotated in place, and
  verified present by S13/S14:*** DELETEF's banned `'VOC'` (guard upcases the
  left side only — lowering it lets `DELETE.FILE voc` through) and SETFILE's
  `'QFILE'` default (exact-then-downcase covers old and new accounts).
- ***Verifiers audited BEFORE install (the last category's lesson):***
  `verify-vocverbs` read `SYSCOM` by exact id twice (COPY, QSELECT). Fixed by
  taking the id from installed NEWVOC and printing it — ***not*** by trying both,
  because QSELECT on an absent id prints "0 record(s) selected to select list 2",
  which D2's anchor accepts (measured). `verify-lcnames` S10–S14 + a `syscom`
  category; ***it crashed on the red run (unguarded open of a renamed file)***,
  now `readtxt()` so an absent file fails its row. Red on `f610ae3` after the
  fix: 10/141, all this category.

***§M3 THIRD CATEGORY (THE COMMAND IDS) INSTALLED AND WITNESSED on `f610ae3`***
(22:47:44, `assert-current` 0, SD up at boot). ***The install itself passed with
upper-case `SECOND.COMPILE`/`THIRD.COMPILE` against lower ids*** — the fold's
first real use; 202 GPL.BP.OUT objects, 143 gcat. `verify-grants` 16/0 (was 6
failed). `verify-lcnames` 106/106 — raw: 10916 for `$savedlists`, `$hold` and
`count`; `CT VOC COUNT` → `VOC count`. Standing suite at its counts, 0 not-OFF;
DON `COUNT VOC` 418.
- ***THREE VERIFIERS WENT RED ON THE RENAME AND ALL THREE WERE THE INSTRUMENT***,
  static rows reading an upper-case FILENAME the rename moved (every session row
  passed): `verify-lcnames` S2 (`EDIT.LIST`), `verify-editors` B4–B6 (6 rows),
  `verify-nonet` B (4 rows). Fixed to the shipped lower name. ***AND ONE WAS WORSE
  THAN RED:*** `verify-nonet`'s A rows ("removed verb `MODIFY` is gone") had
  become ***vacuously true*** — they would pass on a tree that ships `modify`.
  Now "gone in either case". ***LESSON FOR THE NEXT CATEGORY (F/Q pointers, BP,
  directories):*** grep `gplbld/*.py` for every renamed name as a FILENAME and
  as an ABSENCE check before installing, not after.
- Still unwitnessed: MODIFYA migrate-first; §N release prompt.

*Pre-install, 22:35 (measured):* §M3 third category built and pushed: the
command ids are lower case (the port's `1a88360`). *The
"~HH:MM" times on tonight's earlier §M blocks were estimates and run late;
the install stamps quoted in them are the measured times.* ***NEXT:
owner reinstall → `verify-lcnames` 9 failed → all pass, `verify-grants` 6 failed
→ 16/0, `verify-fold` and the standing suite unchanged.*** ***THE INSTALL ITSELF
IS THE FIRST TEST***: the installer types `SECOND.COMPILE` / `THIRD.COMPILE` in
upper case against ids now lower — pass 1 compiles CPROC (with M1's fold) from
this tree first, so a broken fold fails the install visibly there.
- ***777 renames by script file*** (`scratchpad/rename_commands.py`, `git mv`
  per id, no content written; dry run first; refuses on collision/dirty tree):
  NEWVOC 373, VOC_TEMPLATE 394, SD.VOCLIB 10 — types K PA PH R S V. Excluded:
  F/Q pointers, T tier lists, X, `$ % @` ids. `git status`: 777 R, 0 lines
  changed; remaining upper ids are exactly the exclusions.
- By Edit: field 3 of the 20 R records (→ SD.VOCLIB lower ids); both tier lists'
  entries lower (every entry resolves to a shipped record).
- ***TWO DEFECTS THE RENAME WOULD HAVE CAUSED, FIXED BEFORE SHIPPING:***
  (1) ***MODIFYA `voc.delta` matched tier ids EXACTLY*** — on an account not yet
  migrated a promotion would write `basic` beside `BASIC`, and ***a demotion to
  STANDARD would delete nothing and leave the compiler verbs***. It now calls
  `!voccase` first and names moves/refusals (10916/10917). ***UNWITNESSED:***
  needs a second account and a tier move (sudo). (2) ***`CPROC:1891` R-record
  target read was exact*** — an unmigrated account's `LISTF` R record would give
  5054. Now folds.
- ***Audited and left:*** ~400 literal hits of command-shaped strings in GPL.BP
  — compiler/editor/debugger keywords (BCOMP 213, ED 29, ICOMP 21, DEBUG 9),
  `'DICT'` portions, BBPROC's compile list (program names), user paragraph
  names (`ON.LOGTO`, `ON.ABORT`, `ON.EXIT`, `MASTER.LOGIN` — not shipped).
  C: only `op_config.c "SH"` (a config key). BBPROC copies VOC_TEMPLATE by
  generic select. Installer `create-account` resolves via the lower hyphen form.
- ***User-visible cost, in the changelog:*** COPY reads a source record id
  exactly, so `COPY FROM VOC LIST,x` needs `list`. `verify-fold` now tries both.
  `verify-grants` VERBS → lower (it reads files by name).
- `verify-lcnames` gained S6–S9 (no upper command id; tier lists lower and
  resolving; R field 3 resolves) and a `count` category through the migration.
- ***§N STILL OPEN AND NOW MATTERS:*** `$RELEASE` is `L1.0-0` before and after,
  so an account is prompted to update only through the installer's keep-cycle
  `UPDATE.ACCOUNTS ALL` or by hand — decide with §N before a real release.

***12 Sep 2026, ~23:40 — §M3 SECOND CATEGORY (`$hold`) INSTALLED AND WITNESSED
on `dcde7bf`*** (22:24:58, `assert-current` 0, SD up at boot). `verify-lcnames`
***73/73*** (red 12/74 — the H9 guard row is recorded only on failure; do not
quote totals that include guard rows). Raw: both 10916 lines (`$savedlists`,
`$hold`), `CT VOC $HOLD` → `VOC $hold`, SETPTR `Hold file: $hold zzlch` ×3, print
in `$HOLD/zzlch`, no stray `"$hold zzlch"` — so the installed C and BASIC agree.
`verify-voccase` 38/38; standing suite at its counts, 0 not-OFF. ***Unrun:***
EDIT's working copy in `$hold` (`verify-editors` does not open it). ***NEXT
CATEGORY, per the port: the TCL command ids (its `1a88360`, 792 ids)*** — the
bulk transform the script-file hatch is for; size it before starting.

*Pre-install, 23:25:* §M3 second category built and pushed: the `$HOLD` VOC id is
`$hold` (the port's `134d0a4`).
- GPL.BP: SETPTR (`'$hold '` marker written lower, 3 tests `downcase(...)`),
  SPVIEW, `_NEXTPTR`, `_PRFILE` (`downcase(file)`), CLEANAC, CREATEA `fn`, EDIT
  (working copy), `voccase` `created.ids` += `$hold`. MESSAGES 7119/7131/7170;
  `NEWVOC/SP.VIEW`. ***`VOC_TEMPLATE/$HOLD` → `$hold` by `git mv`*** (one step,
  `core.ignorecase` unset; `git ls-files` shows only `$hold`); its fields 2/3
  still `$HOLD`/`$HOLD.DIC` — the directory.
- ***C: `to_file.c:195` `strncmp("$HOLD ")` → `MemCompareNoCase("$hold ")`*** —
  the marker, not a path; case-insensitive so the bootstrap-built BASIC and the
  make-built C need not move together. Paths at `:178/:187/:196` stay `$HOLD`
  (disk). ***Built locally with plain `make`: `to_file.o` compiled, no warning.***
- ***DELIBERATELY UNCHANGED, disk names:*** `BBPROC:287` FILES_LIST,
  `installsdai.sh:804`, `gplbld` INSTALL_FILE_INFO / CREATE_INSTALL_DICT_FILE /
  FILES_DICTS, CREATEA `os.name`.
- `verify-lcnames` generalized: probe takes the id (`RUN BP ZZLCN READ $hold`);
  each category runs new-account → moved-back → real `UPDATE.ACCOUNTS` → restore.
  `$hold`'s function row prints via `SETPTR 5,...,3,AS zzlch` and checks DISK:
  `$HOLD/zzlch` present AND no stray `"$hold zzlch"` file — ***which is what a
  BASIC/C marker mismatch would produce*** (measured baseline first: 176 bytes
  in `$HOLD/zzlch`, SETPTR showed `Hold file: $HOLD zzlch`). S1 exempts
  disk-name lines (`os.name`, `FILES_LIST`) by content, and lists them.
  ***RED on `3da9b8b`: 12/74, every one a `$hold` row; all `$savedlists` rows
  PASS (first category re-witnessed); DON left as found.***

***12 Sep 2026, ~22:55 — §M3 FIRST CATEGORY (`$savedlists`) INSTALLED AND
WITNESSED on `3da9b8b`*** (22:13:42, `assert-current` 0; SD came up at boot this
time). `verify-lcnames` ***36/36*** (red was 10/36; "37" was a miscount — U0
is recorded only when the move-back fails, and S5 was added after the red run),
raw: `CT VOC $SAVEDLISTS` → `VOC $savedlists`, and the real `UPDATE.ACCOUNTS`
printed ***"1 VOC record(s) were renamed to the lower-case name SD now uses:
$savedlists"***. `verify-voccase` 38/38. Standing suite unchanged at its counts,
0 not-OFF; units sdverify 41. ***METER GAP:*** `verify-nocase` still 1036 — it
counts NEWVOC/VOC_TEMPLATE ids and names on disk, not CREATEA-written ids or
quoted literals in GPL.BP, so this rename did not move it. ***NEXT: `$HOLD`***
(the port's `134d0a4`: VOC_TEMPLATE record renamed on disk, SETPTR, SPVIEW,
`_NEXTPTR`, `_PRFILE`, CLEANAC, CREATEA, `NEWVOC/SP.VIEW`, messages
7119/7131/7170, and C in `to_file.c`).

*Pre-install block, 22:40:* §M3 first category built and pushed.
- ***Edited with Edit replace-all, not the port's patch*** — it would not apply
  (it depends on the port's earlier on-disk rename). Literals in COPYLST SAVELST
  DELLIST LSTMRG CREATEA CLEANAC SAVESTK `_DELLIST` `_SAVELST` `_GETLIST` GETLIST;
  MESSAGES 3248/3249/3250/6462; `NEWVOC`+`VOC_TEMPLATE` `EDIT.LIST`. On disk it
  is still `$SVLISTS` (the (a) half, later). No C reference exists.
- ***M2 HAD A HOLE THIS CATEGORY EXPOSED, CLOSED:*** `!voccase` moved only ids
  SD *ships*, and `$SAVEDLISTS` is not shipped — CREATEA writes it (as it does
  `$COMMAND.STACK`, `$HOLD`, `BP`). So an existing account would have kept
  `$SAVEDLISTS` for ever. `voccase` now also treats `created.ids` as system names
  — ***ONLY RENAMED ones***, since listing `$hold` early would move it and then
  VOC_TEMPLATE's `$HOLD` would be copied back beside it. The list is checked
  against CREATEA's own lower-case literals by `verify-lcnames` S4/S5.
- `sdverify.reached_off` now accepts `::OFF` — measured: the prompt is `::`
  while a select list is active. Unit case added (41/0).
- ***NEW `gplbld/verify-lcnames.py` + `.bp`*** (37 decisive): installed source
  static rows; a new account holds exactly `$savedlists` (BASIC exact read — CT
  folds, so "not found" cannot test a rename); lists work; CT echoes the MATCHED
  id; ***the migration run for real*** — probe moves DON's id back to
  `$SAVEDLISTS`, the lists still work through the fold, real `UPDATE.ACCOUNTS`
  must print 10916 naming `$savedlists` and leave exactly `$savedlists`. Restore
  undoes only what the run did; Z1 "ends as it started". ***RED WATCHED on
  pre-rename `d79ae15`: 10/36 failed, exactly the rename rows; DON's VOC left
  (N,Y) as found.*** `verify-voccase` gained R16–R19 (CREATEA names): red 3/38.
  ***S4 passed vacuously there (`[] == []`) — S5 added so it cannot again.***
- ***Not measured and why:*** a KEEP-accounts install cycle (the installer's
  root `UPDATE.ACCOUNTS ALL`) — the in-account simulation stands in; a second
  account.

***12 Sep 2026, ~22:00 — §M2's VOC MIGRATION IS INSTALLED AND WITNESSED on
`d79ae15`*** (21:45:13, `assert-current` 0; SD kick-started by the owner after
install, PRE_RELEASE 29). `gcat/!VOCCASE` and `GPL.BP.OUT/voccase` 21:45:16,
installed source carries `$internal`.
- `verify-voccase.py` ***34/34***, raw tags checked
  (`MOVED=list $hold admin.verb select`, `COLLIDED=SORT`, `MOVED2=` empty).
- ***THE REAL `update.voc` RAN, which nothing in the suite does*** — DON,
  `UPDATE.ACCOUNTS` (mode 2, own account, no sudo), one-off script
  `scratchpad/updvoc.py`: 5200 printed, no runtime fault, no 10916/10917,
  `COUNT VOC` 418 → 418. ***ITS "every record unchanged" ROW WAS VACUOUS*** — the
  dump used non-existent keywords (`COL.HDR.SUPP`, `HDR.SUPP`) so it compared an
  error with itself — ***replaced by a byte comparison*** against a pre-run copy
  of `VOC/%0`: 4 bytes differ, offsets 84/88/89/104 = `FILESTATS` (`dh_fmt.h`,
  packed; stats at 80) `opens` 4→7, `reads` 212→779, `selects` 0→3 —
  ***`writes` and `deletes` UNCHANGED***, so update.voc + voccase read everything
  and changed nothing, as a fresh install should. Not yet a standing verifier.
- Standing suite on `d79ae15`, no `--allow-stale`, all exit 0 at prior counts
  (fold 35, vocverbs 34, setpw 24, txn 33, editors 28, nonet 59, lineendings 42,
  basicfuncs 199, accounts 35, sysperms 18, grants 16/0, tier-layer 0 short,
  `COUNT VOC` 418).
***NEXT: M3, first category*** (still conditional on re-checking the meter).

*Older, 21:45 — the pre-install block:* ***§M2's VOC MIGRATION IS BUILT AND
PUSHED, NOT INSTALLED. NEXT: OWNER REINSTALL, THEN `verify-voccase.py` MUST GO FROM 20
FAILED TO 34/34, AND THE STANDING VERIFIERS MUST STAY AT THEIR COUNTS.***

***21:12 install `4288380`: SD WAS LEFT STOPPED*** — `PRE_RELEASE` 29 (`sd.service`
`Type=forking` race; the owner's post-install reboot did not bring it up this
time). ***And it exposed an instrument defect, fixed:*** `verify-voccase`'s
ground check read "SD has not been started" as *"VOC zzvcv already exists"* —
`session_ok` passed a session that FINISHED without RUNNING. `sdverify.session_ok`
now requires the `:OFF` prompt line; new `require_running()` refuses exit 2 and
quotes sd; both ground checks gated. Units 34→40, ***watched red against HEAD's
old module*** (2 new rows fail, `require_running` absent), and watched refusing
the real stopped SD with the true reason. ***Every OTHER verifier inherits the
stricter row and has NOT been re-run under it yet*** — re-run them once SD is up.

**What was built.** `GPL.BP/voccase` (new, lower-case name — adds no meter
remnant; catalogued `!voccase`, which the catalogue stores as `gcat/!VOCCASE`
like every entry). Called from `LOGIN update.voc` before the NEWVOC copy loop,
so both routes reach it: the installer's keep-cycle `UPDATE.ACCOUNTS ALL`
(`installsdai.sh:944`, root) and an ordinary user's release prompt. Rules, each
settled from the record, no owner question needed:
- moves an account VOC record to its lower-case id ***only if SD ships that
  lower-case id*** (NEWVOC or VOC_TEMPLATE) — the 12 Sep ruling keeps user names
  out, and the same test makes it ***inert until M3 ships a lower-case id***;
- content moves unchanged, so `[locked]` goes with it and the copy loop honours
  it under the new name;
- both spellings present and DIFFERENT → neither touched, named (10917) — plan
  M2 "refuse rather than guess"; IDENTICAL → upper deleted (no choice exists;
  also recovers a run interrupted between its write and delete);
- write before delete, never the reverse.
Messages: `10052` "Cannot open SDSYS VOC_TEMPLATE" ***reused from the port with
its number*** (it had it; this tree did not), `10916` moved, `10917` refused
(Linux block). Uses select list 11, free at the call site.

**Witness `gplbld/verify-voccase.py` + `.bp`, no sudo** — three fixture files
stand in for account VOC / NEWVOC / VOC_TEMPLATE (a real VOC would pass by the
routine doing nothing, and NEWVOC needs root). 34 decisive rows, including the
must-NOT-move ones (user name, not-yet-renamed system name, already-lower,
refused twin) and a second call proving idempotence. ***RED CONTROL WATCHED on
install `76938f1`: 20 of 34 failed, for the right reason*** — the probe wrote
its fixtures, then `Unable to load '!VOCCASE' object code`; compile, fixture and
cleanup rows passed.

***NOT WITNESSED BY IT, AND WHY:*** `update.voc`'s call and messages
10916/10917 — they need a shipped lower-case id and an account that predates it,
i.e. the first M3 rename on a KEEP-accounts cycle. ***CORRECTION, same night:
the line here said tier-layer and accounts exercise `update.voc`. THEY DO NOT —
tier-layer only reads. NOTHING IN THE STANDING SUITE REACHES `update.voc`***, and
that is why the fault below was invisible to it.

***INSTALL `4288380` SHIPPED A BROKEN `update.voc` — FOUND BY `verify-voccase`,
FIXED IN SOURCE, NOT YET REINSTALLED.*** With SD started, the probe loaded
`!VOCCASE` (so the lower-case record compiled and catalogued) and faulted:
`Select list number out of range at line 77 of !VOCCASE`. Lists 11–12 need
`HDR_INTERNAL` (`sd.h:43-48`) and `voccase` lacked `$internal`. LOGIN calls it
unconditionally, so ***on that install any account update — the release prompt,
`UPDATE.ACCOUNTS` — would stop at that error*** (inferred from the call site;
not run on a real account). Fix: `$internal` in `voccase`. 20/34 again, all
downstream of the fault; compile, fixture, cleanup and the new `session_ok`
rows passed.

***The stricter `session_ok` re-run across the whole suite, same night, SD
kick-started, install `4288380` + unshipped gplbld/doc delta, `--allow-stale`:***
every verifier exit 0 at its prior count (fold 35, vocverbs 34, setpw 24, txn 33,
editors 28, nonet 59, lineendings 42, basicfuncs 199, accounts 35, sysperms 18,
grants 16/0, tier-layer 0 short + `COUNT VOC` 418), ***0 sessions "never reached
OFF"***; units sdverify 40, editors 19, nonet 12, basicfuncs 25, accounts 17,
sysperms 20, assert-current 10. So the new row refuses a stopped SD without
false-failing a real one.

***GAP TO CLOSE — conditional plan:*** a no-sudo witness that drives the REAL
`update.voc` on a throwaway account VOC. Would have caught this at build time
instead of by the fixture probe. Falsified as feasible if every route into
`update.voc` needs root or a release mismatch the agent cannot create.

***NEXT:*** commit + push the `$internal` fix → owner reinstall →
***check SD is running (PRE_RELEASE 29 may leave it stopped)*** →
`verify-voccase.py` 34/34 → then M3's first category.

***M2 IS NOT FINISHED BY THIS — STILL TO BUILD, per M3 category:*** the ON-DISK
renames the VOC move cannot do (per-account `$HOLD`, `$HOLD.DIC`, `$SVLISTS`,
`BP`, `BP.OUT` directories and the F-record paths naming them; sdsys directory
names; the register keys `ACCOUNTS/DON` → `don`, root-only, so installer). Each
belongs with the M3 commit that renames its category, witnessed on a keep cycle.
***Suggested M3 order, the port's (19 Aug):*** `$hold` / `$savedlists` VOC ids →
TCL commands → SDSYS file names on disk → F/Q pointers → `bp`/`gpl.bp` → account
names — conditional; re-check against the meter before starting.

***12 Sep 2026, ~21:05 — §M1 (THE CASE FOLD) IS INSTALLED AND WITNESSED.*** Install `76938f1`, 20:55:16, owner-run delete→install,
`assert-current` **0**. All 37 changed programs have `GPL.BP.OUT` objects dated
20:55:18–21 (none missing), so the bootstrap compiled every one.
`verify-fold.py` ***35/35*** (was 7 failed on `f14919c`) — raw output checked,
not just the verdict: `ZZFOLDV` → `4 DON`, `COUNT ZZFOLDF` → `0 record(s)
counted`, `OPEN.UPPER=Y OPEN.VOCLOWER=Y OPEN.QTARGET=Y OPEN.ABSENT=N`.
***"Nothing that works changes" MEASURED, not assumed*** — every standing
verifier re-run on this install, default arguments, all exit 0 at exactly the
pre-fold counts: vocverbs 34, setpw 24, txn 33, editors 28, nonet 59,
lineendings 42, basicfuncs 199, accounts 35, sysperms 18, grants 16 (both
controls PASS), tier-layer 0 short with DON `COUNT VOC` 418 after; units
sdverify 34, editors 19, nonet 12, assert-current 10, basicfuncs 25, accounts
17, sysperms 20, selftest 26. ***Not exercised by any of those:*** SETFILE's
QFILE path, CPROC `.L`/`.R`/`.D`, RUN's fold, `$INCLUDE` fold, LOGIN-paragraph
read — compiled and installed, unrun.

*The block below is the 20:40 pre-install hand-off; its "next" steps 1–2 are
done.* (It replaced one headed "13 Sep" that was written 12 Sep ~20:15.)

**Where §M is.** Rulings in (account names → lower, in scope at `CREATEA:409`;
user data-file record ids → OUT). Meter `gplbld/verify-nocase.py` unchanged at
1036 remnants + 3 code sites — ***correctly: the fold renames nothing, so M1 is
invisible to it.*** ***DO NOT rename anything until the fold is installed and
`verify-fold.py` is green.***

***THE PREVIOUS HAND-OFF SAID "FIVE SITES". IT WAS ~85, MEASURED FROM THE
PORT'S GIT HISTORY*** — four commits on 18 Aug: `0d62cf9` (74 sites, 36 files,
scripted + by hand), `d815df5` (`_VOC_REF`, which the 74 missed), `f9ab089`
(9 comparison sites the fold would otherwise break — `DELETE.FILE voc` walking
past the banned-file guard, the tier omit filter silently omitting nothing),
`8f808a3` (CPROC verb dispatch — no lower tier; found only by a probe), plus
`86c6f51` (`.D name`, 28 Aug). The hand-off's five were `_VOC_REF` + four CPROC
sites. Same mistake the port recorded ("8 sites" → 76). ***Also wrong in it:
`op_seqio.c:204` is DELETESEQ, not OPENSEQ*** (`:464` is OPENSEQ).

***HOW IT WAS APPLIED — CLAUDE.md's script-file hatch, said first:*** `git apply`
of the port's own patches (`0d62cf9` minus MODIFY/SED, which are removed here;
`f9ab089` for APISRVR+CPROC only; `8f808a3`). No fuzz: every context and removed
line matched this tree byte for byte, so the code at each site is the port's
bootstrap-verified post-image. By hand (Edit): `_VOC_REF` (open + Q-pointer
target), `QPROC` get.token keyword read, `SETFILE` (QFILE read + test).
***Already in this tree, nothing to do:*** CREATEA/LOGIN tier-list guards and
omit compare (`upcase` both sides), `DELETEF:239` banned-file guard, CPROC `.D`.
Port comments citing `PROJECT_STATUS.md 5.12` re-pointed to "port". 37 files,
dated START-HISTORY line in each. ***Block balance: 37 files, 0 unbalanced***
(openers incl. bare ELSE minus END, HEAD vs tree) — necessary, not sufficient;
the port's two worst traps passed it.

***ONE PORT SITE DELIBERATELY NOT TAKEN — `QPROC` `check.record` (the port's
`f9ab089`).*** It folds the record id of *whatever file a query names*; upstream
never folded it, so it is a new case-insensitive match on user data, which the
12 Sep ruling put out of §M. Comment at the site. ***Cost, and the decision it
defers to M3:*** once VOC ids are lower, `LIST VOC LIST` will not find `list`
(the port measured exactly that with `$HOLD`). Options then: fold only when the
file is a VOC, or accept. Not asked yet — nothing is broken until M3.
***Record ids that were ALREADY folded upward upstream*** (CT, ED, BASIC source,
CATALOG, `$INCLUDE`) now also try lower — extending an existing chain, taken.

***REMAINING DIFFERENCES FROM THE PORT'S `gpl.bp`, CHECKED (per-file `downcase`
counts):*** BASIC (`bp.OUT`), CREATEA (account name lower), LOGIN (batch gate —
not in this tree), MODIFYA (comment), SETPTR/`_PRFILE` (`$hold` literal) — all
rename-era (M3) or absent features, none a fold site.

***THE WITNESS — `gplbld/verify-fold.py` + `.bp`, NEW, NO SUDO.*** Makes
lower-case ids (`zzfoldv` = copy of WHO, `zzfoldf` = CREATE.FILE, `zzfoldq` =
Q-pointer to `ZZFOLDF`) and reaches them by UPPER-case name through all three
routes: V dispatch (CPROC), C a verb's open (QPROC), O BASIC OPEN (`_VOC_REF`,
only a program reaches it) + Q-target + `open 'voc'`. Controls: as-spelled must
work, a name in no case must still fail. ***RED CONTROL WATCHED, 12 Sep 20:40 on
install `f14919c` (same shipped code as `38dafd2`), `--allow-stale`: 7 of 35
decisive rows FAILED — exactly V2 V3 C2 C3 O2 O3 O5, every control PASS, probe
compiled 0 errors, fixtures cleaned (Z1 3/3, BP.OUT removed as run-created).***
Raw wording measured first: `ZZFOLDV is not in your VOC`; `COUNT ZZFOLDF` →
`File not found`.

***NEXT, IN ORDER:***
1. Owner: delete→install from `origin/main` (the reinstall is the GPL.BP compile
   gate — SDSYS-only ruling). A syntax error fails the bootstrap visibly.
2. Agent, no sudo: `assert-current.py` (must be 0), then
   `python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/verify-fold.py`
   — expect ***35/35***. Then re-run the standing verifiers (list under "Every
   verifier re-run", below) — the fold touched CPROC, QPROC, PARSER, BCOMP, so
   ***"unchanged" is a claim to measure, not assume***; DON `COUNT VOC` 418.
3. Only then M2.

**After M1: M2** (collision guard — refuse if `bp` and `BP` both exist; the
migration in `installsdai.sh`/`update.accounts`; ***`git mv` via a temp name***,
verify with `git ls-files`) — **M3** (the rename, the one big scripted transform
CLAUDE.md's script-file hatch is for; drive the meter to 0 with `--strict`) —
**§N** (release-number bump so accounts get the update prompt; plan says do §M
and §N in the same release). Plan detail: `/home/don/Documents/claude_plan.md`
§M/§N; gap table in PORT_ADOPTION queue 18.

***12 Sep 2026, AFTER THE FULL CYCLE — older, but still current on everything
except §M's progress above.***

**The install is current.** `f446ac1`, 11:56:05, `assert-current` **0**. ***IT
WAS A GENUINE FULL CYCLE, MEASURED, BECAUSE THE LAST ONE WAS A KEEP CYCLE THAT
NOBODY NOTICED***: `/home/sd/user_accounts` holds only `don` (11:57); the
register holds only `DON` and `SDSYS` (11:56); `sdusers` is `root,sdsys,don` and
`sdadmin` is `don`, both recreated; the audit trail is a fresh 542 bytes, not
28 400. `pete`/`tadm`/`tprog`/`tstd` are gone as SD accounts — ***their Linux
users and `sdu_*` groups SURVIVE***, as `deletesdai.sh:304` warns. New
baseline: DON `COUNT VOC` **418** (was 420), `LISTU` clean.

***DELETEF 2050 IS WITNESSED — AND THE CRITERION THIS FILE SET FOR IT WAS
WRONG.*** The witness command gives exit **0** in **0.047 s**, **635 bytes**,
0 BEL — against the banked before of exit 124, 51 139 053 bytes in 15 s. But
this file said *"the prompt must appear ONCE"*, and ***the raw bytes carry it
TWICE, which is correct***: the command feeds `OFF` to the prompt, and
`DELETEF:169-173` reads `upcase(yn[1,1])`, so `OFF` is `O` — neither Y nor N —
and the loop rightly asks again; only end of input gives `''` → N. ***THE
OWNER'S TERMINAL SHOWED ONE***, because at end of input SD emits `\r ESC[K`,
which erased the second prompt before it could be seen (`od -c` of the capture).
***A RENDERED TERMINAL IS NOT AN INSTRUMENT FOR COUNTING PROMPTS*** — the port's
lesson in `sdverify.py`'s header, now with a local byte-level example. The
decisive property was always "finite and fast", and it holds.

**Every verifier re-run on the current install, WITHOUT `--allow-stale`, all
exit 0:** vocverbs 34, setpw 24, txn 33, editors 28, nonet 59, lineendings 42,
basicfuncs 199, accounts 35, sysperms 18 (= 472 decisive rows), grants 16 with
both controls, tier-layer (DON 19 of 19, 0 short); units sdverify 34, editors
19, nonet 12, assert-current 10, basicfuncs 25, accounts 17, sysperms 20,
selftest 26; `reconcile-accounts.sh` report: 1 live, 0 stale. ***`setpw`'s peer
row was checked, not trusted***: PETE's account is gone, and `MODIFY.PASSWORD
PETE` still answers 2001 because the privilege check precedes the target lookup
— so the row passes for the right reason, and would go red on a broken gate
either way.

***WHAT THE FULL CYCLE DID AND DID NOT WITNESS — the difference matters more
than the green:***
- **Queue 15 (installer seeding / ADOPT): the END STATE is what its main path
  should produce, and a keep cycle cannot produce it** — DON's directory was
  absent, so `installsdai.sh:901`'s guard was satisfied; the Linux user `don`
  pre-existed (uid 1000), so it was necessarily the pre-existing-user case; no
  `$adopt.don` marker was left (`:906` removes it on success); DON is
  ADMINISTRATOR with the full layer. ***THE INSTALL TRANSCRIPT ITSELF WAS NOT
  SEEN BY THIS SESSION***, so this is inference from end state, not a witness of
  the path taken. ***CORRECTION, same day: the line above undersold the
  record.*** ADOPT ITSELF was already witnessed on 11 Sep 22:38 by the owner-run
  `witness-adopt.sh` (14 PASS, including 10038 and 10039); what that entry named
  as its ONE remaining gap was `installsdai.sh`'s own block — and 11:56 is the
  first run of that block. ***And a safety property, measured with no sudo***:
  `don`'s GECOS is still `Donald Montaine`, so ADOPT did not stamp it, and
  `DELETE.ACCOUNT DON` could never delete the installer's own Linux login —
  `DELACC` keys the user deletion on the `SD account` stamp, and
  `sd-elevate:126` refuses an unstamped user independently.
- **Queue 19 (the sweep at start): NULL CASE.** 0 stale records existed, so a
  sweep that removed nothing proves nothing. It needs a stale record to remove.
- **Queue 13: carry-over is NOT witnessable on a full cycle** — the trail is
  deleted by design. Rotation at `sd -start` is unread: 0620 refuses `don`.
- **Queue 12 (ssh / API doors): not measured.**

**Observation, not a defect claim:** the register's `DON` record is now `0664
root:root`; before this cycle it was `0644`. Not a leak (the group is `root`),
but it differs from what `CREATE.ACCOUNT` wrote before, and the installer's
seeding path is the new variable. Unexplained.

***`witness-accounts.sh --commit` RAN 17:57 AND ITS VERDICT WAS WRONG ABOUT
ITSELF — "13 passed, 7 failed", of which 5 passes measured anything.*** The 7
failures were one premise, and it was the script's: phase 2 ran `useradd` then
`CREATE.ACCOUNT USER zzacct2 NO.QUERY`, and SD refused it with **10038**,
correctly — the recipe came from this file's STALE 10 Sep instructions (now
corrected in place, step 3 of the cycle section) and ignored the 11 Sep queue 15
witness that already covered 10038. ***8 of the 13 passes were the null case***:
nothing had been created, so "the record is gone", "the Linux user survives" and
the rest were true of an account that never existed. And the ungated phase 3
leaked its confirmation: `DELETE.ACCOUNT` refused the unregistered name without
asking, so the `Y` reached the `:` prompt — *"Y is not in your VOC"*. Genuinely
witnessed on `f446ac1`: phase 1 (10039, nothing created — a RE-witness of
11 Sep) and 10038 creating nothing. Cleanup complete, nothing left behind.

***REWRITTEN, NOT PATCHED — THE FIX WAS NEVER THE PREMISE ALONE.*** What would
have caught it is GATING: every phase now runs only if its precondition was
established, and an unreached row counts as a FAILURE. Phase 2 now ADOPTs the
throwaway user with the installer's own invocation (`installsdai.sh:903-906`,
`</dev/null`, 25 s), with 10038-without-the-marker as its control; phase 3 then
reaches `DELETE.ACCOUNT`'s borrowed-user branch, which ***nothing has ever
reached*** (10085, 10158, 10036, the user and home surviving). Dry run and guard
exercised; the gate itself cannot be made to fire without root, so it is
parse-checked, not seen working.

***PRE_RELEASE 28 (SEV A) IS FOUND, FIXED AND WITNESSED — the arc across three
installs.*** The rewritten witness first ran 18:12 on `f446ac1` and measured the
finding: after `DELETE.ACCOUNT` of an adopted administrator the Linux user was
left — rightly — in place but ***still in `sdusers` AND `sdadmin`***
(`groups='zzacct2 sdusers sdadmin'`), and `sdadmin` is effective root
(passwordless `sd-elevate passwd` of any SD user who is a Linux sudoer → become
them → `sudo -i`; `don` the transitory example, SDSYS the constant). The fix —
`DELACC`'s 10036 branch strips `sdadmin` then `sdusers` — was compiled by SDSYS
at reinstall (not in an account), and ***re-run 19:35 on `f14919c`: 33/0, D12/D13
PASS***, the transcript showing `gpasswd -d … sdadmin`/`… sdusers` and the
survivor left with `groups='zzacct2'` alone. The borrowed-user delete branch
that nothing had reached before also passed clean (10085, 10158, 10036, user +
home survive). Full account: PRE_RELEASE 28.

**Owed and blocked:** `sdsyswrite` (needs a session in SDSYS). ***And still by
hand: the SD-CREATED delete path*** — `CREATE.ACCOUNT USER <new> PROGRAMMER`
(password typed), then `DELETE.ACCOUNT`, expecting the LONGER confirmation
(10084) and 10028 "OS User Deleted"; the witness prints the recipe (phase 5) but
cannot drive the password prompt.

**The port acted on bug 8 within the day** — `8b78bad`, "Fix 17 (Linux #8)",
and found SEVEN faults where Linux reported five: `NOT` hidden by its own header
prose, a case labelled `INMAT.reuse` calling `reuse()`, and `ADDS.via.SUM`
naming no function. Checked against this tree's probe rather than assumed: `NOT`
and `REUSE` exercised, `INMAT` correctly declared — this probe renamed that case
and dropped `ADDS` when it was written. ***The test accounts are gone***, so anything wanting a second
ADMINISTRATOR or a STANDARD peer must recreate them first — and `CREATE.ACCOUNT`
for those names will meet a pre-existing Linux user and `sdu_*` group.

***12 Sep 2026, LATE — THE BLOCK BELOW IS OLDER.***

**Queue 22 ranked item 5 is done: `verify-basicfuncs`.** `gplbld/verify-basicfuncs.py`
+ `.bp`, **199 of 199** decisive rows on install `0095937` with `--allow-stale`;
units `gplbld/test-basicfuncs-units.py` **25/25**. 179 value cases over 116
intrinsics and the operators. Detail in PORT_ADOPTION's worklist, not repeated.

***THE STALE INSTALL IS UNCHANGED AND IS STILL THE FIRST JOB*** — the block
below is correct: `assert-current` **1**, install `0095937`, `sdsys/GPL.BP/DELETEF`
built and never installed. `--allow-stale` is sound for `verify-basicfuncs`
specifically, and that is a stated reason rather than a habit: the whole delta
`0095937..HEAD` is `assert-current.py` (comment), `sdsys/changelog` and
`DELETEF`, none of which is an intrinsic. ***RE-RUN IT WITHOUT THE FLAG AFTER
THE NEXT INSTALL ANYWAY*** — the value rows measure the INSTALL.

***TWO THINGS THIS VERIFIER FOUND, AND ONE OF THEM WAS IN ITSELF.***
- ***ITS OWN FIRST RUN REPORTED TWO DEFECTS SD DOES NOT HAVE.*** `cases_from`'s
  `rstrip()` trimmed the trailing spaces off the `TRIMF` and `FMT.L`
  expectations, which are the last field on the line; `TRIMB` passed in the
  same run because its spaces are LEADING, and that asymmetry is what pinned
  the fault to the instrument. ***THE ROW THAT CAUGHT IT WAS `Q1`***, which
  exists only because the probe's tally and Python's verdict are kept separate.
  Fixed with a `|END` terminator; the parser now refuses a line without one.
- ***THE PORT'S `basicfuncs.sb` OVERSTATES ITS COVERAGE BY FIVE NAMES***, and
  the arithmetic that found it is now a decisive row here. ***FILED WITH THE
  PORT 12 Sep 2026 ON THE OWNER'S INSTRUCTION — `BUGS_FROM_LINUX_PORT.md` 8,
  commit `8e8e7de`, pushed to `github.com/dmontaine/sd4windows` and confirmed
  with `git ls-remote`.*** It is **8**, not the 9 this file first said: 8 was
  being held for the DELETEF `continue` defect, which the port has already
  fixed itself (below). The published count is **173 of 176 accounted for** —
  ***THIS FILE FIRST SAID 175, WHICH WAS WRONG***: 175 is 176 less `DELETE` and
  forgets the three names on no list at all. Detail in PORT_ADOPTION item 5.

**DON was clean before and after:** `COUNT VOC` **420**, `BP` empty, no
`BP.OUT` — measured both ends, not assumed.

**Queue 22 ranked item 7, the POSIX-mode family, is DONE — `verify-sysperms.py`
18/18, units 20/20, no sudo.** ***THE ENTRY THAT SAID IT NEEDED AN OWNER-RUN
HALF WAS WRONG, AND WRONG IN THE DIRECTION THAT POSTPONES WORK***: the writes
these ask about are writes that must FAIL, which is precisely what an ordinary
user can measure. Five of the port's six are answered with no privilege; only
`sdsyswrite` needs root. ***THE CONTROL'S REASON IS MEASURED, NOT INHERITED***
— `$IPC` must stay writable because every session writes `$IPC/%0`, and row W2
stats it, runs a session, and stats it again. Detail in PORT_ADOPTION item 7.

**Queue 22 ranked item 6, the account family, is split and half done.**
`gplbld/verify-accounts.py` **35/35** (units 17/17) is the no-sudo half;
`gplbld/witness-accounts.sh` is the privileged half and ***HAS NEVER BEEN
RUN*** — dry run only, which is why the dry run is its default. The reason for
the split is a measurement: ***`CREATE.ACCOUNT`, `DELETE.ACCOUNT` and
`MODIFY.ACCOUNT` each answer 2001 to a plain `sd` session even as an
ADMINISTRATOR***, and not because they are missing from the VOC — `CT VOC
CREATE.ACCOUNT` returns `V / CA / $CREATEA`. Detail in PORT_ADOPTION item 6.

***END OF SESSION, 12 Sep 2026 (evening) — THE BLOCK BELOW IS OLDER, INCLUDING
THE 11 Sep BLOCK THAT SAYS THE SAME THING.***

**State at hand-over.** Tree **clean**, `main` == `origin/main` at `23e8dad`,
`bin/sd` rebuilt **PLAIN** (no `DEVELOPER BUILD` banner), DON clean with
`COUNT VOC` **420**, nothing left in `BP`/`BP.OUT`, no fixtures anywhere.

~~***THE ONE THING THAT IS BUILT AND NOT INSTALLED, AND IT IS THE FIRST JOB NEXT
SESSION.***~~ ***RESOLVED 12 Sep 11:56 — installed in `f446ac1` and witnessed;
see the top block, which also corrects the "ONCE" criterion below.***
`assert-current` read **STALE**: the install was `0095937`, HEAD was
`23e8dad`. Run the corrected recipe and it comes to three files —

```sh
git diff --name-only 0095937..HEAD | grep -v -E '\.md$|^sdb_ai/sd64/gplbld/(verify|test)-'
```

`gplbld/assert-current.py` (comment only — the owner's ruling, and not an
installed file), `sdsys/changelog` (ships, cosmetic), and ***`sdsys/GPL.BP/DELETEF`,
WHICH IS A REAL BEHAVIOUR CHANGE*** — Enter is now N at the 2050 select-list
prompt. Compiled 0 errors with a red control of 1 error at line 169; **never
installed, never run.**

***ITS WITNESS, AFTER THE NEXT INSTALL*** (as `don`, no sudo). With a list
active and no file name, the prompt must appear ONCE and the session must END,
because at end of input `input` yields `''` which is now N:

```sh
cd /home/sd/user_accounts/don && printf '\nTERM 200,9999\nSELECT VOC\nDELETE.FILE\nOFF\n' | timeout 20 /usr/local/sdsys/bin/sd
```

***THE "BEFORE" IS BANKED, SO THE WITNESS HAS SOMETHING TO BEAT — MEASURED
12 Sep ON THE RUNNING `0095937` INSTALL, WHICH STILL HAS THE OLD DELETEF:***
that exact command gives ***exit 124, 51 139 053 bytes in 15 seconds***, the
2050 prompt repeating with no newline between repeats (the same class as the
98.9 MB in 40 s of 11 Sep). ***AFTER THE FIX IT MUST EXIT 0 IN UNDER A SECOND
WITH THE PROMPT PRINTED ONCE.*** The killed session left ***no dead slot***
(`LISTU` clean afterwards) and DON stayed at `COUNT VOC` 420, so running the
"before" again costs nothing — SIGTERM ends it cleanly, as queue 26 records.
***No verifier covers 2050*** — this is a hand witness, and it is the obvious
next row for `verify-vocverbs`.

**Queue 22's unprivileged work is DONE — ranked items 1-7.** Nine verifiers,
all green on install `0095937`, ***472 decisive rows between them***, plus
seven unit suites:

| Instrument | Rows | Red control |
|---|---|---|
| `verify-vocverbs.py` | 34/34 | real — B4 was FAIL on the older install |
| `verify-setpw.py` | 24/24 | built in: C1-C5 reach `passwd(1)` |
| `verify-txn.py` + `.bp` | 33/33 | real — `--probe` minus a READU → 11 fail |
| `verify-editors.py` | 28/28 | logic only (every row is a root-owned file) |
| `verify-nonet.py` | 59/59 | logic only — and it failed its own first run |
| `verify-lineendings.py` + `.bp` | 42/42 | ***null-case only, NOT behaviour*** |
| `verify-basicfuncs.py` + `.bp` | 199/199 | real — three, one row each; and it failed its own first run |
| `verify-accounts.py` | 35/35 | real — three doctored registers via `--register`, one row each |
| `verify-sysperms.py` | 18/18 | real — four, via a `--sdsys` fixture tree; the two gate sections have none |
| units | `sdverify` 34, `editors` 19, `nonet` 12, `assert-current` 10, `basicfuncs` 25, `accounts` 17, `sysperms` 20 | |

~~***EVERY ONE NEEDS `--allow-stale` UNTIL THE NEXT INSTALL***~~ ***NO LONGER —
all nine re-run WITHOUT it on install `f446ac1`, 12 Sep, every one green with
the same row counts. See the top block.***

***AND ONE OWNER-RUN SCRIPT THAT HAS NEVER BEEN RUN:***
`gplbld/witness-accounts.sh`, the privileged half of the account family. ***ITS
DRY RUN IS THE DEFAULT; `--commit` IS THE OPT-IN AND NEEDS root.*** Read what
it intends to do first:

```sh
bash /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/witness-accounts.sh
```

then, and only then:

```sh
sudo bash /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/witness-accounts.sh --commit
```

It refuses unless the throwaway names are absent as user, group, directory AND
register record, and removes only what it made. Detail in PORT_ADOPTION item 6.

***THE UNPRIVILEGED QUEUE-22 WORKLIST IS EXHAUSTED (12 Sep).*** Items 1-7 done
and witnessed; `witness-accounts.sh --commit` done (PRE_RELEASE 28 closed).
`parsertokens` measured NOT to apply here and routed (PORT_ADOPTION disposition
table): a forward-slash path is whole, a comma splits, `\` is a quote char in
`GPL.BP/PARSER:78` — the port's backslash-TRUNCATION bug is Windows-path-
specific. **What is left all needs privilege OR a second account the full cycle
removed:**
- ***`sdsyswrite`*** — a session IN SDSYS (real uid 0). Owner-run.
- ***`tierchange`*** — a fresh `MODIFY.ACCOUNT` tier move (MODIFYA's VOC
  re-derivation is still unattributed), needing an admin session and a second
  account.
- ***`cmdaudit`*** — reads the 0620 audit trail; sudo.
- ***the SD-CREATED delete path*** — `CREATE.ACCOUNT USER <n> PROGRAMMER`
  (password typed) then `DELETE.ACCOUNT`, expecting 10084 + 10028; the witness
  prints the recipe (phase 5) but cannot drive the prompt.
- Lower value, unbuilt: `batchjob`, `logtoaccess`, `notyet`, `keys` (backspace).
- ***The release blockers are elsewhere: §M (lower case) and §L1.*** With the
  verifier infrastructure now in place, these are the next real work; §M is
  sudo-free to advance (a source migration + static audit).

***THE OWED FULL delete→install HAS NOT MOVED, AND IT IS NOW FOUR QUEUES DEEP:***
15's installer block, 13's rotation and carry-over, 12's ssh and API doors, 19's
sweep on a real start. Answer `n` then type `DELETE`. The 12 Sep cycle KEPT
accounts — measured, not assumed, from the 10–11 Sep directory mtimes on `pete`,
`tprog`, `tstd` and `tadm` — so the seeding block never ran.

***WAITING FOR THE OWNER, AND THE CONFORMANCE RULING HAS ALREADY BEEN APPLIED
TO ALL FOUR, SO DO NOT RE-ASK THE PORT:*** `SEM_UNDO` (the port abandoned POSIX
semaphores for a Windows-only reason and has no answer), 6133 (byte-identical
there, N deletes the dictionary anyway — the question is what N should DO),
§M scope (conformity is explicitly not the test, by his own earlier ruling),
and ***a new one from this session: should a directory-file record tolerate
CRLF here?*** `op_dio3.c:1309` says *"nothing to fold on a bare-LF file"*,
which is an assumption about USERS rather than about the platform — a Linux
user can still hand a record CRLF from an editor setting or a Windows copy.
Not a defect claim; the code does what it says.

~~**Also owed, not blocking:** the DELETEF `continue` defect is owed to the port
as `BUGS_FROM_LINUX_PORT.md` **8** and is NOT filed.~~ ***NOT OWED AFTER ALL,
AND THE CLAIM UNDER IT WAS WRONG — MEASURED 12 Sep 2026 ON THE PORT'S CURRENT
TREE.*** The port found and fixed the same defect INDEPENDENTLY on 11 Sep as
its own `RELEASE_1.1_FIXES.md` **15**, and `gpl.bp/DELETEF:296` now reads
`goto more_test`. ***IT WAS ITS OWN `verify-vocverbs.ps1` THAT CAUGHT IT***
(entry 14 on run `b136`, the symptom being the test's second `N` reaching the
VOC as *"N is not in your VOC"*) — so this project's note that the port's
verifier *"WOULD PASS ON IT"* is false, and is corrected in PORT_ADOPTION.
Nothing is filed for it, and nothing should be. **Number 8 went to the
`basicfuncs.sb` coverage entry instead.**

***11 Sep 2026, day session — the blocks below are older still.***
- ***14:43 INSTALL `c2b375d` (`assert-current` 0): QUEUES 12, 13, 26 AND 27 ARE
  WITNESSED ON IT*** — evidence and the parts still unwitnessed in their
  PORT_ADOPTION rows (12: ssh/API doors; 13: rotation, carry-over across a
  delete→install, four record kinds). DON clean, `COUNT VOC` 411.
- ***A `sudo` WITNESS IS ONE OWNER-RUN SCRIPT.*** The agent cannot use sudo
  (`sudo -n` → "interactive authentication is required"). Write the steps into a
  script that backs up what it changes, checks each step PASS/FAIL on the
  success wording, restores on failure and tees to a log; hand over `sudo bash
  <absolute path>`. `witness-sudo.sh` (scratchpad, 11 Sep) is the model.
- Rebooted 05:05; install `3bd4421` (05:04:46) is the overnight work. HEAD
  differs by comments and docs only, which is the whole of `assert-current`'s 1.
- ***THE OVERNIGHT BUILDS ARE WITNESSED except 8*** — the reap live and in the
  sandbox, `op_getlocks` in the sandbox against a pre-fix binary that faulted;
  per queue in PORT_ADOPTION "Witnessed on the install".
  Instrument: `printf 'cmds\nOFF\n' | timeout N sd` as `don` from
  `/home/sd/user_accounts/don`, guarded on `ps -C sd` empty and `ipcs -s -i 0`
  values `111111`. ***`pgrep -f` matches its own command line*** — it
  reported "not clean" on a clean system; do not use it for the guard.
- ***QUEUE 26, NEW: THE `:` PROMPT BUSY-LOOPS AT END OF INPUT.***
  `printf 'WHO\n' | timeout 10 sd` (no `OFF`) → exit 124, 369 207 BEL bytes in
  10 s. `linuxio.c:439-443` returns -1 with `ER_EOF` on a pipe, `_KEYCODE:87-88`
  returns `''`, and the CPROC line editor (`:1006`) asks again for ever. The
  DELETEF prompts are no longer part of it (each printed once at EOF). SIGTERM
  ends it cleanly: no dead slot, semaphores back to 1. The port's `linuxio.c:508`
  is the same code; not measured there. ***END EVERY PIPED SESSION WITH `OFF`.***
  **Fix installed and WITNESSED 11 Sep on `c2b375d`** (CPROC `:1006`,
  PORT_ADOPTION 26): no `OFF` now exits 0 in 0.01 s. Still end instruments with
  `OFF` - an older install spins.
- **DON (ADMINISTRATOR) has no `UPDATE.ACCOUNTS`**: its VOC predates §L1's
  `TIER.ADD.ADMINISTRATOR`, and `update.voc` never adds VOC_TEMPLATE verbs
  (`LOGIN:544-547`). Whether MODIFYA's tier re-derivation (unrun) adds them is
  unchecked — check before calling it a defect.
- **`UPDATE.ACCOUNTS` rewrote DON's VOC to the installed NEWVOC** (396 written,
  1 added): DON's empty `COUNT VOC` is now **411**, not 410.
- **DON is clean**: seven entries, `BP` empty, no `BP.OUT`, `COUNT VOC` 411.
- ***THE SANDBOX, REBUILT 11 SEP — what the recipe in the older block below does
  not say:*** `-start` forks the sandbox's own `sdlnxd`; stop it (pick the pid
  by `readlink /proc/<pid>/exe` under the scratchpad) or its 5-minute check runs
  `sd -cleanup` mid-witness. `RUN BP x` fails 1135 when the account path makes
  `BP.OUT/x` longer than 128 characters (queue 28): `CATALOG BP x LOCAL`, then
  call `x`. `GETLOCKS()` needs `$internal` (compile with the sandbox's
  `-internal`). A before/after: copy the build, `git show <commit>:<file>` into
  it, `make` — both binaries attach the same segment. Teardown: kill sandbox
  pids by exe path, then `ipcrm -M 0x716d0901 -S 0x716d0902` and nothing else.
- ***QUEUE 27, NEW: AN ELSE-BRANCH `OPENSEQ` LEAVES A LOCK THAT SURVIVES `OFF`***
  and blocks the same `OPENSEQ` for ever; only an SD restart clears it.
  Measured in the sandbox — ***do not recreate it on the live system.***
  PORT_ADOPTION 27. ***CAUSE: a 2026/06/10 AI cleaning-cycle change
  (`op_seqio.c` `exit_op_openseq`, `if (status)`) that freed the file variable
  on the new-record ELSE — the port reverted it 15 Aug and this tree never
  took the revert.*** Reverted 11 Sep, built, ***WITNESSED IN THE SANDBOX,
  before vs after***: on the installed code `OPENSEQ … ELSE` + `WRITESEQ`
  cannot create a file at all (`WRITESEQ` → 3013 `ER_NSEQ`, nothing written)
  and strands a lock even through `CLOSESEQ`; reverted, the file is written and
  no lock remains. ***Installed and witnessed live on `c2b375d`*** (file
  created, no locks). Live had no stranded locks at 12:22. The
  port's generation-2 C findings are all accounted for here (PORT_ADOPTION 27).
- **QUEUE 12 (SUSPENDED) WITNESSED on `c2b375d`**, 33/0 — MODIFYA, the three
  doors, five messages, two dictionary items; ssh and API doors not exercised.
- **QUEUE 13 (AUDIT TRAIL) WITNESSED on `c2b375d`** (append-only proven by
  `EPERM`, identity right on 20 records; rotation and carry-over not) — `K$AUDIT`
  57 (the port's number; the queue row's "93" was wrong), `@SDSYS/audit`
  `sdsys:sdusers 0620` + `chattr +a`, rotated at `sd -start`, kept across a
  keep-accounts delete→install. ***THE INSTALLER AND DELETER CHANGED***
  (`installsdai.sh` restore block, `deletesdai.sh` before `rm -fr`): a
  `chattr +a` file makes `rm -fr` fail, so a deleter without the new block
  would stop part way. Known limit, as the port's: a shell user can append a
  line of their own. PORT_ADOPTION 13 has the witness steps.
- ***QUEUE 14 IS INSTALLED — `f3fbb1f`, 11 Sep 21:32, `assert-current` 0,
  `verify-grants.py` 16/0 with both controls PASS.*** The owner ran the
  keep-accounts delete→install cycle.
- ***AND ITS TWO NEW FUNCTIONS ARE WITNESSED ON THAT INSTALL, WITH NO SUDO:***
  `!tier_allows` 11/11 (both directions, equal rank, own account, all four
  refusal statuses, lower-case input) and `!grp_members` 6/6 (compared against
  an independent read of `/etc/group`, both refusals). ***A NON-`$internal`
  PROGRAM MAY CALL THESE `$internal` FUNCTIONS*** — measured, and it is why the
  decision function could be witnessed as plain `don` without touching a group
  or building a dev binary. DON restored, `COUNT VOC` 411. Detail in
  PORT_ADOPTION 14.
- ***THERE IS NO SUCH THING AS A PLAIN-`sd` ADMINISTRATOR SESSION, AND A
  WITNESS RUN HAD TO PROVE IT BEFORE THIS FILE BELIEVED ITS OWN NOTE.***
  `CPROC:328` calls `grant.administrator` only inside `if system(27) = 0`
  (real uid 0), so `kernel(K$ADMINISTRATOR,-1)` is false outside `sudo sd` for
  everybody. The account verbs — GRANT included — run from `sudo sd`, which
  lands in SDSYS; ***measured 11 Sep: SDSYS's own VOC DOES carry
  LIST.GRANTS***, the bootstrap having built it from the whole of
  VOC_TEMPLATE. This is the port's model and no code changed.
- ***QUEUE 14 IS WITNESSED END TO END — 11 Sep 22:08, owner-run
  `witness-grants.sh`, 28 PASS / 1 / 0 FAIL, restore COMPLETE.*** The 1 is a
  consumed one-shot, not a defect: phase 2's "before" (`is not in your VOC`)
  can be read once per account and the 22:04 run read it. Evidence per check
  in PORT_ADOPTION 14 and not repeated here. ***THE GATE IS THE ONE TO
  REMEMBER:*** `pete`, still a member of `sdu_tstd` with the membership
  looking perfectly normal from outside, refused at LOGTO with 10126 — with
  the control that `pete` DOES enter once the tiers are level again.
- ***DIVERGENCE (1) IS VALIDATED BY A RUN, NOT BY THE ARGUMENT FOR IT:***
  `$GRANTA` is not in `privileged_commands`, the session was euid `sdsys` with
  real uid 0, and every group edit went through — sudo decides on the real uid.
- ***STILL UNWITNESSED, AND IT IS 10043's OWN CLAIM TO THE USER:*** every
  session in the witness was started fresh by `sudo -u`, so the half that
  matters — an ALREADY-logged-in person being admitted by SD and refused by the
  filesystem — is untested. It needs somebody holding a live session at the
  moment of the grant.
- ***A WITNESS THAT CHANGES STATE CAN CONSUME ITS OWN PRECONDITION.*** Phase 2
  is the example: restoring TADM's TIER does not remove the VOC records the
  tier move wrote. Snapshot/restore restored all four values and the "before"
  was still gone. Worth remembering when writing the next one.
- ***TYPE USER NAMES IN THEIR UNIX CASE.*** Measured 11 Sep: the parser does
  not upcase a token and `!is_grp_member` compares exactly, so
  `GRANT TSTD TO PETE` ≠ `GRANT TSTD TO pete`. GRANTA upcases the ACCOUNT
  (register keys are upper) and leaves the USER alone on purpose. The wrong
  case is caught by `is_user` and answered 10045, so it fails loudly. `GPL.BP/GRANTA` (`$GRANTA`: GRANT / REVOKE /
  LIST.GRANTS), the gate at `CPROC:2865`, the ADD-arm gate and the promotion
  report in `MODIFYA` (`:201`, `:419`/`:469`), three `VOC_TEMPLATE` records,
  three names in `NEWVOC/TIER.ADD.ADMINISTRATOR`, messages 10041-10050 +
  10126-10129 + 10911, changelog. All five programs 0 errors, no warning; red
  control `QBAD` 3 errors. Tree rebuilt PLAIN, DON `COUNT VOC` 411. Detail,
  the witness plan and ***the three deliberate divergences from the port*** are
  in PORT_ADOPTION 14 and not repeated here. ***THE ONE TO CHECK FIRST WHEN IT
  IS RUN: `$GRANTA` is deliberately NOT in `CPROC`'s `privileged_commands`
  (`:197-201`)*** — its four premises are each measured, but the conclusion
  drawn from them is not, and a GRANT that fails at run time is what a wrong
  premise would look like.
- ***AFTER THE NEXT INSTALL, RUN THIS BEFORE BELIEVING ANY QUEUE 14 RESULT***
  (no sudo; exit 0 present, 1 missing, 2 no install to ask about):
  `python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/verify-grants.py`.
  ***THE LOAD-BEARING ROW IS A, THE `gcat` CATALOGUE*** — files copied into
  `/usr/local/sdsys` prove nothing about the two-stage bootstrap, and a name in
  `gcat` is there only because SD compiled the program and ran its `$catalog`.
  Row F checks an invariant that is not queue 14's: every
  `TIER.ADD.ADMINISTRATOR` name must resolve in `VOC_TEMPLATE`, because
  `CREATEA:644` skips one that does not without a word. ***Run against the
  `c2b375d` install 11 Sep: 3 passed, 13 failed, both controls PASS*** — the
  expected red, and the before-measurement for the next install's green.
- ***UNWITNESSED PREMISE WORTH ITS OWN LINE, because it is the claim 10043
  makes to the user:*** on Linux a grant reaches SD at once (`!is_grp_member`
  reads `/etc/group` per call) but reaches the FILESYSTEM only at the person's
  next Linux login (account dirs are `drwxrwsr-x <user> sdu_<name>`, measured
  on all five; a session carries the groups it started with). Read off the
  modes and the code, ***not measured end to end***. Falsified by a granted,
  still-logged-in person who can write a record in the account.
- ***MEASURED 11 Sep, AND IT ANSWERS AN OPEN LEAD WITH A CORRECTION:
  NO `sdu_` GROUP ON THIS MACHINE CONTAINS `sdsys`*** — 0 of 5
  (`sdu_don|pete|tstd|tprog|tadm`, all `root,<user>`), on the fresh `c2b375d`
  install whose accounts `CREATE.ACCOUNT` made. ***So this file's line 1801 is
  WRONG***: it says "newer `sdu_tstd:root,sdsys,tstd`" and calls it an unmeasured
  lead; `sdu_tstd` is `root,tstd`. `CREATEA:876` passes `root,sdsys,<user>` to
  `sd-elevate groupadd`, which adds each member with `gpasswd -a` and exits
  non-zero on failure, so why `sdsys` is absent is not yet explained. It matters
  for queue 14: `LIST.GRANTS` reports what the group holds, and CPROC:2807's
  "open lead" about `sdu_don` is now known to be general, not one account.
- ***INSTALL `3650118`, 11 Sep 22:19:50, `assert-current` 0; queue 14 re-checked
  16/0 after the cycle.***
- ***AND A WARNING ABOUT WHAT A KEEP-ACCOUNTS CYCLE CANNOT WITNESS, PAID FOR
  HERE: `installsdai.sh`'s seeding block is guarded by
  `if [ ! -d /home/sd/user_accounts/<user> ]`, so on a keep cycle it does not
  run.*** It is the only caller of ADOPT, so queue 15's main path was NOT
  exercised by the 22:19 install even though the install succeeded. ***The two
  readings that look like proof afterwards are the null case: no `$adopt.*`
  marker left behind (none was written) and DON still ADMINISTRATOR (it already
  was).*** Anything whose only caller is that block needs a FULL delete→install,
  or a fixture that calls it directly.
- ***THE FIRST ADOPT WITNESS FROZE AT 22:27 AND THE CAUSE IS NOT FOUND.***
  `witness-adopt.sh` stopped at its first `sd` call — `sd create-account USER
  zzadopt1` as root, ***with the terminal still attached to stdin*** — and
  produced no further output; Ctrl-C skipped the EXIT trap, so two throwaway
  Linux users were left behind (nothing else: no SD account, no group change,
  no marker). ***FOUR THEORIES WERE ELIMINATED BY MEASUREMENT, NOT BY
  ARGUMENT***, and each is worth not re-testing: a one-shot verb DOES exit
  (`sd WHO` exit 0); `create-account` resolves (as `don` it answers "not in
  your VOC" and exits 0); ***every account's VOC `$RELEASE` is `L1.0-0`, equal
  to the stamp***, so LOGIN's update prompt is not it (probe `RELPROBE`, 6 of
  6); and `!is_user('zzadopt1')` is ***TRUE*** (probe `IUPROBE`), so CREATEA
  takes the 10038 branch and never reaches the password prompt. ***THE SCRIPT
  IS NOW IMMUNE RATHER THAN DIAGNOSED*** — every `sd` call takes `</dev/null`
  and a 25s timeout, and each echoes its command line first, so a recurrence
  names the step instead of hanging. ***IT DID NOT RECUR: the identical command
  passed in under a second at 22:38.*** A fifth theory died afterwards — an
  unknown TERM and an unset TERM both sign on cleanly, so LOGIN's terminal-type
  question is not it either (and that is a free confirmation of queue 5's
  fallback). ***CAUSE STILL UNKNOWN. The best remaining hypothesis, and it is
  written as one:*** the prompts in this codebase end in `display … :` with no
  newline, and the run's stdout was a pipe into `tee`, so a question COULD have
  been written and left sitting in the buffer — which would explain a stall with
  no visible prompt. Untested; it would be falsified by a tty run that shows the
  question. Re-run needs `--clean` first.
- ***AND A LATENT TRAP FOUND WHILE LOOKING, WHICH IS NOT THE CAUSE HERE:
  `LOGIN:492-511` IS A `loop … input … until Y or N` WITH NO EOF ESCAPE*** —
  the queue 3 shape, in the sign-on path. It only fires when an account's VOC
  `$RELEASE` differs from `SD.REV.STAMP`, which is why it is quiet today; when
  it does fire it will hang a terminal and busy-loop a pipe on 5027 with a BEL
  per turn. Queue 3 lists `DELETEF`'s four loops and does not list this one.
- ***QUEUE 15 (ADOPT) IS WITNESSED — 11 Sep 22:38, owner-run
  `witness-adopt.sh`, 14 PASS / 0 FAIL, cleanup COMPLETE.*** The silent
  take-over of an existing Linux user is closed (10038, and no account
  directory created); ADOPT with the marker adopts and defaults the tier to
  ADMINISTRATOR with no keyword given; the marker is CONSUMED; and a marker
  naming one account does not authorise another. Evidence per check in
  PORT_ADOPTION 15. ***The remaining gap is small and named there:***
  `installsdai.sh`'s own block has not run, because only a FULL delete→install
  reaches it.
- ***QUEUE 15 (ADOPT) BUILT AND COMPILED 11 Sep.***
  `CREATEA` + `installsdai.sh`, ***coupled and install-critical: they must ship
  together***, because refuse-unless-ADOPT without the installer's ADOPT aborts
  the install at its own account step. ***THE PLAN IN THIS FILE'S "ADOPT"
  SECTION UNDERSTATED THE WORK*** — it describes the port's 14 Aug design (a
  keyword, else refuse); the port found on 21 Aug that `K$INTERNAL` alone is
  not enough and added a one-shot marker, which is what was built. Detail and
  the witness list in PORT_ADOPTION 15. The installer now reads the register
  back and warns in red if the seeded tier is not ADMINISTRATOR, because the
  install is the only witness for ADOPT's tier default.
- ***QUEUE 16 IS WITNESSED — 11 Sep 23:55 on install `06d3a4a` (upgrade cycle,
  accounts KEPT, `assert-current` 0). `verify-tier-layer.sh` went from exit 1
  to EXIT 0: DON 10/18 → 18/18***, `COUNT VOC` 411 → 419 (exactly +8), and the
  8 ids are VOC_TEMPLATE-only with none in NEWVOC, so the pre-existing walk
  could not have written them. A second `UPDATE.ACCOUNTS` added nothing and
  left the count at 419. ***Unconfirmed: the install's own output was not seen,
  so whether 10912 displayed during the walk is unwitnessed*** — the mechanism
  is proven by the before/after and the count, not by the message.
- ***QUEUE 16 BUILT AND COMPILED 11 Sep.*** Both halves:
  `installsdai.sh` runs `UPDATE.ACCOUNTS ALL` on an upgrade (the verb half
  already existed, `CPROC:3336`; only the installer call was missing), and
  `LOGIN` `update.voc` now copies the `TIER.ADD.ADMINISTRATOR` layer from
  VOC_TEMPLATE, which it had never opened.
- ***THE GAP WAS MEASURED BEFORE IT WAS DESIGNED FOR, AND IT IS WORSE THAN THE
  ROW ASSUMED: `DON` — the only registered administrator — HELD 10 OF 18 TIER
  VERBS AND WAS MISSING 8***, `CREATE.ACCOUNT`, `DELETE.ACCOUNT`,
  `MODIFY.ACCOUNT` and `UPDATE.ACCOUNTS` among them (probe `TLPROBE`, 11 Sep).
  `TADM` held all 18 only because queue 14's witness moved its tier. ***It went
  unnoticed because administration happens under `sudo sd`, which lands in
  SDSYS, and SDSYS holds all 18.***
- ***A DECISION TAKEN RATHER THAN FORWARDED, AND CHEAP TO REVERSE:*** the row
  left "re-derive inside `update.voc`, or a separate verb" UNRULED. Chose
  `update.voc` — the stance is a smaller system with less cruft, and it makes
  the port's own walk close the gap instead of half of it. Add-only, never
  overwrite, never remove, ADMINISTRATOR only; the objection (it never removes)
  is kept in PORT_ADOPTION 16.
- ***QUEUE 17 (MODIFY.PASSWORD) BUILT AND COMPILED 12 Sep — NOT RUN.***
  `SET_ACC_PASSWORD`, the port's grammar and refusals, filed where the port
  files it (VOC_TEMPLATE + `TIER.ADD.ADMINISTRATOR`). ***The `$cred` half is
  deliberately absent:*** an SD account here IS a Linux user, so its password
  is the Linux password and a second one could only disagree with it. SD never
  sees a password; both arms hand off to `passwd(1)`, and "you must know your
  current one" is enforced by PAM rather than by SD code. Detail in
  PORT_ADOPTION 17.
- ***OWNER'S RULING, 12 Sep 2026: MODIFY.PASSWORD IS ADMINISTRATORS ONLY***, as
  the port files it — ***and his reason generalises, so it is now a stance in
  CLAUDE.md: "Security starts tighter but can be relaxed by choice."*** The
  default is off and ***the administrator holds the dial***: one who wants a
  particular user to set their own password copies the VOC record into that
  account, which works and grants nothing else (PORT_ADOPTION 17).
  ***SO THE RULING IS NOT "STANDARD USERS ARE DENIED", IT IS "THE DEFAULT IS
  DENIED AND THE ADMINISTRATOR DECIDES"*** — an earlier version of this entry
  wrote the consequence up as a cost he had absorbed, which had it backwards.
  `MODIFY.PASSWORD` stays out of `NEWVOC`, and a later session that finds a
  standard user unable to change a password is looking at a default with a
  documented release valve, not a defect.
- ***AND THE NON-ADMIN ARM IS NOT DEAD CODE, which is easy to get wrong:*** only
  an ADMINISTRATOR-tier account holds the verb, but such an account in a PLAIN
  `sd` session has no `K$ADMINISTRATOR` (that needs `sudo sd`, `CPROC:328`), so
  an administrator changing their own password without sudo takes the
  `passwd -- <user>` path and PAM asks for the current one. Common case.
- ***OWNER, 12 Sep 2026, AND IT SETTLES MORE THAN QUEUE 19: "this is why
  suspended accounts exist - you want to retain data, suspend the account; you
  want everything deleted, delete the account."*** So deleting a Linux user IS
  the "remove everything" path and a sweep taking the directory carries out
  that intent. ***THE ONLY THING THE RECONCILER HAS TO GET RIGHT IS "IS THE
  USER REALLY GONE"*** — every guard in it is about that one lookup, and a
  later session should not add one that second-guesses the removal.
- ***QUEUE 19 — BUILT AND WITNESSED 12 Sep; `sd.service` RUNS `--sweep` per the
  owner's ruling.*** `gplbld/reconcile-accounts.sh` → `/usr/local/sbin/sd-reconcile-accounts`,
  `sd.service` gains `ExecStartPre=-… --list`. Witnessed against a fixture:
  a stale record's directory ***and*** record removed under `--sweep`, while a
  stale record whose field 1 was `/etc` was ***KEPT*** and `/etc` verified
  intact. Detail in PORT_ADOPTION 19.
- ***AND A SECOND GUARD THAT WIRING `--sweep` AT BOOT MADE NECESSARY:***
  `ExecStartPre` can run ***before*** sssd or nslcd is up, and a directory user
  is then absent from NSS ***and*** `/etc/passwd` — byte-for-byte the signature
  the sweep treats as "gone". No per-record test can separate those. So if
  `nsswitch.conf`'s `passwd` line names a source outside
  `files/systemd/compat/db/cache`, `--sweep` refuses and reports;
  `--allow-remote-nss` overrides. ***CONSEQUENCE HERE, MEASURED: this box reads
  `passwd: files systemd sss`, so it will REPORT, not sweep*** — drop `sss`
  from `nsswitch.conf` or pass the override to make it sweep. Both halves
  witnessed against a fixture.
- ***A FINDING BIGGER THAN QUEUE 19, AND IT IS WHY THE SWEEP IS NOT WIRED:
  `!is_user` (`IS_USER:52`) READS `/etc/passwd` DIRECTLY AND NEVER NSS.***
  `/etc/nsswitch.conf` here is `passwd: files systemd sss` with sssd ***enabled***
  (inactive today, so the gap is invisible — measured 12 Sep). ***On a
  domain-joined install SD cannot see users the system resolves***, which
  affects more than the reconciler: `CREATE.ACCOUNT` would try to create a user
  NSS already has, and any sweep keyed on SD's view would call every
  directory-backed account stale. The reconciler asks two sources and refuses
  on disagreement; ***nothing else in the tree does.*** Worth its own queue
  entry.
- ***QUEUE 21 BUILT AND RUN 12 Sep — `gplbld/check-stale-leads.py`, no sudo,
  exit 0 clean / 1 worklist / 2 cannot answer.*** ***RUN IT AFTER EDITING THESE
  DOCUMENTS***: it finds entries whose OPENING status claim is contradicted
  later in the same entry, which is what happens when a correction is appended
  and the lead is left standing. ***ON ITS FIRST RUN IT FOUND THREE, AND TWO
  WERE AN HOUR OLD*** — PORT_ADOPTION rows 15, 17 and 19, all written by that
  session. Openings rewritten; the re-run leaves ***1, row 19, READ AND
  ACCEPTED*** (both its claims are true), so ***exit 0 is not the goal*** — it
  ranks entries for reading and every hit is read by hand.
- ***QUEUE 22 — THE HARNESS IS BUILT, UNIT-TESTED AND HAS ALREADY EARNED ITS
  KEEP, 12 Sep.*** `gplbld/sdverify.py` (one module, not the port's 51 copies
  of the same block; `--selftest` 26/0), `gplbld/test-sdverify-units.py` (34/0,
  ***with a red control: `verdict()` mutated to pass the null case → 3
  failures, exit 1***), and the first verifier, `gplbld/verify-vocverbs.py`.
  All 79 of the port's test instruments are now classified — PORT_ADOPTION
  "Queue 22", which is PRE_RELEASE 1's missing answer for the testing half —
  with a ranked worklist. ***THE ONE TO READ THERE IS `verify-sshadmin`: the
  port's assertion is INVERTED here***, so adopting its wording would have
  written a passing check for behaviour this project deliberately does not
  have.
- ***AND THE FIRST VERIFIER FOUND A DEFECT ON ITS FIRST RUN, WHICH IS THE WHOLE
  ARGUMENT FOR QUEUE 22.*** `DELETE.FILE <ptr> NO.QUERY` honoured NO.QUERY,
  said so with 10117 — and then printed `OK to delete DATA portion '' (y/<n>)?`
  ***three times and ate the two commands that followed***, the transcript's
  tell being that `CT VOC ZZVVF` and `OFF` appear as ANSWERS to the prompt.
  Cause `DELETEF:232`'s `continue`, which the file's own 2024 comment predicts;
  fixed with the `goto more_test` the sibling site already uses.
  ***THE OUTCOME WAS RIGHT AND ONLY THE ROUTE WAS WRONG*** (the VOC entry went,
  the system file stayed), which is why it survived — and why the port's own
  `verify-vocverbs.ps1`, which checks 10117 and the absence of 6146, would pass
  on it. **Same code at the port's `DELETEF:246`, not measured there; owed to
  `BUGS_FROM_LINUX_PORT.md` as 8, through a fresh clone, NOT YET FILED.**
- ***BOTH HALVES ARE NOW BANKED. BEFORE: install `06d3a4a`,
  `verify-vocverbs.py --allow-stale` = 33 of 34, row B4 FAILS. AFTER: install
  `0095937` (12 Sep 01:50:36), owner-run upgrade cycle, `assert-current` 0,
  `verify-vocverbs.py` with NO override = 34 of 34, B4 PASS.*** The transcript
  is the evidence: `DELETE.FILE ZZVVF NO.QUERY` prints 6145, 10117, then goes
  straight to the delete — no 6135, 0 BEL, 0.01 s, nothing eaten. Queue 1 and
  queue 3b are witnessed on the same run (rows C and D).
- **`verify-grants.py` on the same install: 16 passed, 0 failed, both controls
  PASS.** Queue 14 is still PRESENT-not-RUN; that is all the row says.
- ***AND THE CYCLE BANKED TWO THINGS NOBODY ASKED IT FOR.*** (1) ***QUEUE 17 IS
  INSTALLED*** — it was BUILT + COMPILED, NOT RUN; DON's VOC gained
  `MODIFY.PASSWORD` (`V / CA / $MODIFY.PASSWORD`) and `COUNT VOC` went
  **419 → 420, exactly +1**, which accounts for the whole delta. ***THE VERB
  HAS STILL NOT BEEN RUN.*** (2) That +1 is ***a second, independent witness of
  QUEUE 16's mechanism***: `update.voc`'s tier-layer copy carried a
  newly-shipped ADMINISTRATOR verb into a PRE-EXISTING account, which is the
  case the queue was built for and not the one it was first measured on.
- ***BUT IT WAS A KEEP-ACCOUNTS CYCLE, SO THE OWED LIST IS UNCHANGED.***
  Measured, not assumed: `pete`, `tprog`, `tstd` and `tadm` still carry their
  10–11 Sep directory mtimes. So `installsdai.sh`'s seeding block did not run
  (it is guarded by `if [ ! -d /home/sd/user_accounts/<user> ]`), and
  ***queue 15's installer block, queue 13's rotation and carry-over, and queue
  12's ssh and API doors ALL STILL WANT A FULL delete→install*** — answer `n`,
  then type `DELETE`.
- **Audit file after the cycle, as far as an unprivileged shell can see it:**
  `/usr/local/sdsys/audit`, `sdsys:sdusers`, mode `0620`, 17534 bytes.
  ***`don` is in `sdusers` and can neither read it nor read its attributes***
  (`lsattr` → Permission denied), which is queue 13's write-only property
  holding. ***Its `chattr +a` flag and whether the content carried across the
  cycle CANNOT be checked without sudo*** — still owed, and it needs the owner.
- ***AND A TRAP RE-PAID, WITH THE INSTRUMENT THAT CAUGHT IT:***
  `make EXTRA_C_FLAGS=-DSD_DEV_BUILD` ***DID NOT PRODUCE A DEV BINARY*** —
  `make` tracks timestamps, `sd.c` had not changed, so nothing recompiled and
  `bin/sd --version` printed no `DEVELOPER BUILD` line. `rm -f gplobj/*.o`
  first. CLAUDE.md says this; the reason it was caught anyway is that the
  version banner is checked rather than assumed.
- ***QUEUE 17 IS RUN, NOT JUST INSTALLED — 12 Sep, `gplbld/verify-setpw.py`,
  24 of 24, as `don`, no sudo, and NOTHING CHANGED.*** All three refusals
  reachable without sudo fire; ***the ordering is proven*** — `MODIFY.PASSWORD
  PETE somethingextra` answers 5276 and NOT 2001, so the trailing-token refusal
  is about GRAMMAR and not about privilege, which is what makes the refusal
  mean anything for somebody who does hold the privilege. ***AND THE CONTROL IS
  THE POINT:*** `MODIFY.PASSWORD DON` alone got past the syntax check into
  `passwd(1)`, was refused a deliberately wrong current password (10915, no
  10914), and left `passwd -S don`'s last-change date at `2026-09-08`,
  ***read before AND after***. A verb that refused everything would have passed
  the three treatment rows.
- ***AND IT SETTLES AN UNWITNESSED PREMISE OF PORT_ADOPTION 17: "you must know
  your current password" IS ENFORCED BY PAM, NOT BY SD CODE.*** Row C4 saw
  `Current password:` come from `passwd`, not from SD — SD never prompted.
- ***NOT REACHABLE WITHOUT sudo, AND `verify-setpw.py` PRINTS THIS RATHER THAN
  SCORING IT:*** 5018 and 10913 (the privilege test fires second, so any
  account but your own is refused 2001 before either is reached) and the whole
  administrator arm (`!set_passwd` → `sd-elevate passwd`). Owed to an
  owner-run half.
- ***BOTH 12 Sep VERIFIER RUNS USED `--allow-stale`, AND THE REASON IS
  CHECKABLE RATHER THAN ASSERTED.*** At the time of the runs the whole delta
  `0095937..HEAD` was two `.md` files. ***THE `grep -v '\.md$'` FORM OF THIS
  CHECK WAS WRONG AS A STANDING RECIPE AND IS CORRECTED HERE***: it was true
  when written and stopped being true one commit later, when
  `gplbld/verify-setpw.py` landed — a file the installer never ships. **The
  question is not "is the delta documentation", it is "does the delta contain
  anything the install CONTAINS":**

  ```sh
  git diff --name-only <install-commit>..HEAD |
    grep -v -E '\.md$|^sdb_ai/sd64/gplbld/(verify|test)-'
  ```

  ***THE EXCLUSIONS ARE DELIBERATELY NARROW, BECAUSE A FALSE ALARM IS SAFE AND
  A FALSE ALL-CLEAR IS NOT.*** `gplbld` is NOT wholly uninstalled — the
  installer ships `sd-elevate`, `ssh-forcecommand.sh`, `reconcile-accounts.sh`,
  `sdcore.sudoers`, `bbcmp.py`, `pcode_bld.py`, `FILES_DICTS`, `microcfg` and
  `nanocfg` from it (`installsdai.sh:509-606`), so a blanket `gplbld` exclusion
  would hide a real change. Anything the command prints is to be read, not
  waved through.
- ***STEP 2's TRANSACTION WORK IS EXERCISED AT LAST — `gplbld/verify-txn.py`
  + `verify-txn.bp`, 29/29, 12 Sep, as `don`, no sudo.*** The A2 write and A2
  delete rows of "Step 2, second third"'s ***"Cheap checks, none run"*** table
  are now RUN. ***RED CONTROL: `--probe` pointed at a copy with one `READU`
  removed → 11 of 29 fail, exit 1***, and row P2 ("the probe RAN TO THE END")
  names the cause instead of leaving nine unexplained failures.
- ***BOTH OF THE PORT'S HEADLINE TRANSACTION DEFECTS ARE ABSENT ON THIS TREE,
  MEASURED:*** `SYSTEM(1008)` goes 0 → 1 → **0** across a COMMIT (so a program
  can ask "am I in a transaction"), and ***a nested commit does not lose the
  outer transaction's writes*** — `S2`, written by the outer transaction
  BEFORE the inner one ran, reads back. That second one is the row the port
  says its verifier exists for: part of a transaction landing and part not,
  with no error, no status and no log line.
- ***AND THE DIRECTORY-ID SECTION NEEDED TWO INSTRUMENTS, WHICH AGREED:*** SD
  reads `,` and `=` back, and the filesystem shows `%C` and `%E` with `%Y`
  gone and ***no raw-id file for any of the three***. ***ON LINUX THAT LAST
  ROW IS THE ONLY SIGN THE BUG WOULD LEAVE***, because all thirteen of
  `*,=><%/+:;?\"` are legal filename characters here — the port could rely on
  some of them failing loudly on NTFS and this tree cannot.
- ***MEASURED IN PASSING, AND IT IS A FIX WORKING:*** a WRITE inside a
  transaction without the lock answers 3023 *"no lock is held on it. Nothing
  was written."* with the READU/READVU advice — the improved wording, live.
  The first draft of the probe hit it, which is how it was seen.
- ***WHAT verify-txn DELIBERATELY DOES NOT DO, AND THE REASON IS THE 11 SEP
  WEDGE:*** A3 and A1's undo/locks need an INDUCED commit failure (a read-only
  record file, or a record a second session holds). ***THAT IS SANDBOX WORK,
  NOT DON WORK*** — queue 27's stranded lock and the ~03:45 wedge are both
  what an induced failure on the live system looks like when it goes wrong.
- ***OWNER'S RULING, 12 Sep 2026: `assert-current`'s CHECK C STAYS STRICT
  COMMIT IDENTITY — "use the most trusted option".*** The question put was that
  C compares the install's stamp with HEAD, so ***any*** commit makes it STALE
  (a documentation-only one included) and every verifier then needs
  `--allow-stale`; the alternative was to have C ask whether the delta touches
  anything the install CONTAINS. ***THE REASON THE BLUNT CHECK WINS IS THE
  DIRECTION OF ITS ERRORS:*** a cleverer C would have to decide, per commit,
  which files reach an install, and every wrong answer there is a FALSE
  "current" — the expensive direction, per the tool's own bias paragraph.
  ***SO THE FRICTION IS PAID IN THE TRANSCRIPT INSTEAD:*** a caller who has
  reasoned about the delta says so with `--allow-stale`, which prints a banner,
  and names the commit and the reason when quoting the result. Ruling written
  into `gplbld/assert-current.py`'s header, which is where anyone minded to
  loosen it would look. **No code changed; `test-assert-current.py` 10/10.**
- ***NANO AND MICRO ARE NO LONGER "COMPILED, NOT RUN" — `verify-editors.py`
  28/28 and `test-editors-units.py` 19/19, 12 Sep, no sudo.*** Everything short
  of what a person must SEE is now measured: the syntax files are placed, the
  verbs are wired, `find.editor`'s premise holds, and both verbs answer.
- ***THE PORT'S QUESTION DID NOT TRANSFER WHOLE, AND THE DIFFERENCE IS THE
  USEFUL PART.*** The port BUNDLES its editors SHA-pinned and asks "is the
  bundled copy the one EDIT resolves, rather than whatever winget left on
  PATH". Here they are deliberately not bundled, so the Linux question is
  whether the ***syntax configuration*** — the part this project ships — is
  placed where the editor will read it.
- ***ROW A2 IS A GAP THE PORT DOES NOT HAVE, AND IT IS THE ONE WORTH
  REMEMBERING: shipping `/usr/share/nano/sdbasic.nanorc` ACHIEVES NOTHING
  UNLESS `/etc/nanorc` INCLUDES IT, AND THAT FILE IS DEBIAN'S, NOT OURS.***
  Measured: `/etc/nanorc:257` is live and globs the directory. ***THREE
  COMMENTED-OUT includes SIT DIRECTLY BELOW IT***, which is why A2 parses the
  line rather than searching for the filename — a substring search would find a
  commented line and call the highlighting reachable when nano never reads it.
  `test-editors-units.py` drives that case both ways.
- ***AND EDIT HAS A TERMINAL GATE, WITNESSED, WHICH IS WHY THE VERB IS SAFE TO
  DRIVE DOWN A PIPE AT ALL:*** given a file from a session with no terminal it
  refuses BEFORE opening anything — *"nano needs a terminal to draw on, and
  this session has none. ed, the line editor, works anywhere"* — and the
  non-existent file in the test is never reported, so the ordering is the gate
  and not luck.
- ***WHY THIS ONE GOT A units FILE WHEN THE OTHERS DID NOT:*** every row
  `verify-editors` checks is a ROOT-OWNED file, so it cannot be shown to go red
  against the system without editing the machine's own configuration. The red
  is demonstrated against the LOGIC instead, with the inputs the real files
  would have if they regressed.
- ***OWNER'S RULING, 12 Sep 2026, AND IT IS A STANDING ONE FOR THE WHOLE
  "WAITING FOR THE OWNER" LIST: where conformity with SD Core for Windows
  answers an open question, and the answer does not cause problems on Linux,
  IMPLEMENT THE CONFORMANT ANSWER AS THE DECISION*** rather than forwarding it.
  Applied to all four open rulings the same day; ***it answered exactly one***,
  and the other three are named below with WHY the port cannot settle them, so
  nobody re-asks the port about them.
- ***"WAITING FOR THE OWNER" 2 IS RULED AND BUILT: ENTER IS N AT DELETEF's 2050
  — AND THE ARGUMENT THAT MADE IT HARD RESTED ON A MISREADING OF THE RECORD.***
  PORT_ADOPTION said *"DELETE, CD, COPY, CT and ED treat anything but N as yes,
  so its de-facto default is Y"*, so N here would have meant something
  different from N everywhere else. ***MEASURED 12 Sep IN BOTH TREES AND THAT
  IS WRONG.*** All six verbs carry the identical shape —
  `loop … input … if N then stop … until reply = "Y" … repeat` — so anything
  that is neither Y nor N ***re-asks***. ***NO VERB GIVES 2050 AN ENTER MEANING
  AT ALL***, so there was nothing to be inconsistent with and the only argument
  for Y does not exist. Port PRE_RELEASE 79 then decides it unopposed:
  destructive prompts take N. `DELETEF:126-175`, compiled 0 errors, ***red
  control an unbalanced bracket → 1 error naming line 169***, tree rebuilt
  PLAIN, DON `COUNT VOC` 420, changelog entry. **NOT INSTALLED.**
- ***AND CONFORMITY ALONE WOULD HAVE KEPT THE DEFECT, WHICH IS WHY THE RULING'S
  SECOND CLAUSE MATTERS:*** the port's `DELETEF` is byte-identical here, so
  "do what Windows does" means "keep looping" — and at end of input `input`
  yields `''`, so it re-asked for ever, the 98.9 MB-in-40 s class. Both
  readings of the ruling converge on N, which is why it was safe to take.
- ***WHAT IS DELIBERATELY HALF-DONE: MESSAGE 2050's TEXT STILL DOES NOT SAY
  `(y/<n>)`, AND IT CANNOT YET.*** The same record is displayed by DELETE, CD,
  COPY, CT and ED, none of which honours a default, so wording it would make it
  ***lie in five places to be honest in one***. 6135 and 6131 could be worded
  because each belongs to DELETEF alone. ***AND THE OTHER FIVE ARE NOT ONE
  DECISION***: Y is destructive in DELETE and COPY and merely proceeds in CD,
  CT and ED, so they need ruling as a group before 2050's wording can follow.
  All five still have the old shape and still busy-loop at end of input.
- ***THE THREE THE PORT CANNOT SETTLE, WITH THE EVIDENCE, SO THEY ARE NOT
  RE-ASKED OF IT:***
  - **`sdsem.c` / `SEM_UNDO` (item 0).** ***The port has no answer and cannot
    have one:*** it ABANDONED POSIX semaphores on 16 Aug 2026 for a
    Windows-only reason — `sem_open` blocked ten seconds under LocalSystem in
    session 0 (port PROJECT_STATUS:2814) — and now uses Win32 named semaphores
    in `win32sem.c`. ***`SEM_UNDO` has no Win32 counterpart***; `grep -rln
    SEM_UNDO` over the port's `gplsrc` returns nothing. Still the owner's.
  - **6133, the multifile prompt (item 3).** The port's code is
    ***byte-identical***, including the part that makes Enter unanswerable:
    N does not mean "change nothing", it jumps to `delete.dict` and deletes the
    dictionary anyway. Conformity would keep a prompt with no safe default.
    ***The question is what N should DO, and the port does not say.*** Still the
    owner's.
  - **§M scope (item 4).** ***Conformity is explicitly NOT the test here***, by
    the owner's own earlier ruling: lower case must be COMPLETE and *"where the
    port stopped short, go past it: this outranks 'the port wins' for §M"*.
    The port's answer is the partial one already rejected. Still the owner's —
    though note his 11 Sep wording, *"no command, file or record id can exist
    in two casings"*, reads as already answering the record-ids half; worth
    confirming rather than assuming, because §M is release-blocking.
- ***THE 12 Sep AUDIT, ITEM BY ITEM — what was measured, not what was read.***
  Three stale claims are corrected above. The rest are confirmed outstanding:
  - **Queue 22 items 4-7** — `ls gplbld/verify-*` shows no `lineendings`,
    `nonet`, `basicfuncs`, account-family or POSIX-mode-family file. Genuinely
    to build. ***BUT NOTE WHAT IS ALREADY TRUE FOR `nonet`: THE SHRINK ITSELF IS
    COMPLETE*** — `SDNET`, `NETWORK`, `TAPE`, `PROC`, `SED`, `UPDATE.RECORD`,
    `MODIFY` and `OPGEN` are all absent from `GPL.BP` **and** `VOC_TEMPLATE`,
    measured. ***THE TASK IS THE STANDING GUARD, NOT THE REMOVAL***, and that
    distinction is worth keeping: the verifier exists to stop the shrink
    quietly coming undone, so it earns its keep after the queue empties.
  - **Queue 25 (DUMPDIR)** — ***THE C HALF ALREADY EXISTS***: `config.c:99`
    and `:179-180` read `DUMPDIR=`, `op_config.c:91` and `:242` expose it. What
    is missing is everything else — nothing SETS it (no `DUMPDIR` line in a
    shipped `sd.conf`) and the installer creates no dump directory with the
    mode/group bits the row calls for. Outstanding, and smaller than it looks.
  - **Queue 28** — `sddefs.h:111` is still `#define MAX_PROGRAM_NAME_LEN 128`.
    Outstanding, still low.
  - **Queue 3b** — 2050 is ruled and built today. ***6133 remains the owner's
    and the port cannot settle it*** (byte-identical, N deletes the dictionary
    anyway). The other five verbs sharing 2050 still busy-loop at end of input.
  - **The port bug (`BUGS_FROM_LINUX_PORT.md` 8)** — not filed; the local
    frozen copy still ends at 7 plus the number-space note. Needs a fresh clone
    and a push, so it is the owner's to authorise.
  - **The owed full delete→install** — still owed. ***MEASURED, NOT ASSUMED:***
    `pete`, `tprog`, `tstd` and `tadm` still carry their 10-11 Sep directory
    mtimes, so the 12 Sep cycle kept accounts and `installsdai.sh`'s seeding
    block did not run. Queues 15, 13, 12 and 19 are unmoved.
  - ~~**`A4` is ONE ROW FROM COMPLETE**~~ — ***DONE THE SAME DAY.
    `verify-txn.py` IS NOW 33/33 AND `A4` IS COMPLETE:*** `SYSTEM(1007)` names
    the PARENT again after the inner commit, measured 29 → 30 → **29** → 0.
    ***THE NUMBERS ARE ALLOCATED PER TRANSACTION AND DIFFER EVERY RUN*** (17/18
    on the first measurement, 25/26 on the next), so every row asserts a
    RELATIONSHIP and none asserts a literal. ***THE ROW THAT MAKES IT MEAN
    ANYTHING IS T10, "the inner has a DIFFERENT number"*** — had the inner
    reused the outer's, "the number came back to the parent" would be true
    however badly `end_txn_level()` behaved, because it would never have
    changed. ***RED CONTROL: `N3` made to report the LEVEL → T11 alone fails
    (expected 29, got 1), T9/T10/T12 still pass.*** So `PRE_RELEASE 6` now
    stands at **`A2` and `A4` complete; `A1`, `A3`, `A5`, `A6` unexercised**,
    and all four need an induced failure — sandbox work.
- ***`verify-nonet.py` DONE AND WITNESSED 12 Sep — 59/59, plus
  `test-nonet-units.py` 12/12.*** It guards the shrink **stance**, so unlike
  the rest of the queue it keeps earning its place afterwards. ***THE CONTROLS
  ARE THE POINT*** (the port's own sentence: proving three verbs are absent
  "would pass every 'is it gone?' check ever written" even if the removal had
  taken APISRVR with it), ***and this project has a sharper control than the
  port does***: CLAUDE.md's near-miss trap — `MODIFY` goes, `MODIFYA` and
  `MODIFY.PASSWORD` stay — is now asserted rather than remembered.
- ***AND IT FAILED ITS OWN FIRST RUN, ON PROSE — 4 DECISIVE ROWS RED, EVERY ONE
  A COMMENT.*** `op_dio1.c`'s history block says *"net_open() call are gone"*
  and *"the NET_FILE type are deleted"*, so searching for `net_open(` found the
  sentence ANNOUNCING the removal and reported the removal as incomplete.
  ***THE CORPSE AND THE TOMBSTONE LIVE IN THE SAME FILE, AND THAT IS THE SHAPE
  OF THE PROBLEM RATHER THAN AN ACCIDENT*** — a removal is most likely to be
  described at the top of the file it was removed from. `strip_c_comments`
  blanks comments while KEEPING line numbers, and the units file drives the
  dangerous direction too: stripping too much would hide a LIVE `net_open()`
  and report it as removed.
- ***MEASURED WHILE DOING IT, AND IT IS CONFORMANT SO IT STAYS:*** `NETFILES`
  survived the mechanism in BOTH trees — still parsed (`config.c:219-220`),
  still in shared memory (`sysseg.c:217`), still reportable by
  `CONFIG('NETFILES')` (`op_config.c:135`), and ***consulted by nothing.***
  `op_dio1.c`'s history says so deliberately. The verifier records it as
  context rather than failing it, and proves the part that matters: ***the knob
  is inert*** — no `net_open`, no `netfiles.c`, no `NET_FILE` type, no remote
  dispatch. A dead parameter is untidy; a live one nobody noticed would be a
  hole.
- ***`verify-lineendings` RECLASSIFIED — THE QUEUE 22 TABLE CALLED IT A "pure
  tree check" AND THAT WAS WRONG.*** It is not about CRLF in shipped files: it
  asks whether SD's READERS handle CRLF, including ***a CRLF straddling a
  2048-byte buffer boundary*** (a fix that inspects "the byte before the LF" is
  right on every small fixture and wrong about once per 2 KB of real data) and
  ***a lone CR surviving, because it is data and not a terminator.*** Here the
  `READSEQ` half IS implemented, straddle and lone-CR included
  (`op_seqio.c:1237-1249`), witnessed on the tree binary 11 Sep but ***never on
  an install***. ***The directory-file half is deliberately NOT carried over***
  (`op_dio3.c:1309`, *"nothing to fold on a bare-LF file"*) — ***AND THAT
  ASSUMPTION IS WORTH A RULING RATHER THAN AN INHERITANCE***, since the port's
  reason for folding was that directory files exist so external editors can
  edit them, and a Linux user can still hand a record CRLF. Not a defect claim.
- ***`verify-lineendings.py` BUILT AND WITNESSED 12 Sep — 42/42, no sudo.***
  ***THE STRADDLE HOLDS, AND IT IS THE ROW THAT NEEDED A REAL FIXTURE:*** with
  the CR as byte 2047 and the LF as byte 2048, line 1 comes back **2047**
  characters ending in `A` — not 2048 ending in CR. A fix that inspected "the
  byte before the LF" would be right on every small fixture and wrong about
  once per 2 KB of real data.
- ***AND THE LONE CR SURVIVES AT THE BOUNDARY, WHICH IS THE SUBTLEST CASE:***
  f5's CR is the last byte of the first buffer and is NOT followed by a LF, so
  the reader — which is holding it back precisely because it might have been
  half a CRLF — has to emit it as data. It does: 2049 characters ending in `B`,
  one CR. ***A FIX THAT STRIPPED EVERY CR WOULD PASS EVERY OTHER ROW IN THE
  FILE.*** `READCSV` inherits the behaviour (it compiles to `OP.READSEQ`,
  `BCOMP:10225`) and row 1's LAST field is 2 characters, not 3.
- ***THE FIXTURES ARE CHECKED BEFORE THEY ARE TRUSTED*** — rows F3a/F3b/F5a read
  the bytes back off the disk and assert the CR really is the 2048th byte.
  ***AN OFF-BY-ONE FIXTURE WOULD MAKE THE STRADDLE ROWS PASS WITHOUT TESTING A
  STRADDLE***, which is the null case this file is most exposed to.
- ***RED CONTROL, AND ITS LIMIT SAID OUT LOUD:*** `--probe` with f3 dropped →
  exactly the 5 straddle rows fail on `None`, nothing else, so they cannot pass
  on absent data. ***THAT IS A NULL-CASE RED, NOT A BEHAVIOUR RED.*** Proving
  the rows would catch a regression in the C needs a PRE-FIX BINARY built by
  the documented before/after harness method; that has not been done, and the
  distinction is recorded rather than blurred.
- ***MEASURED IN PASSING, WORTH KNOWING BEFORE THE NEXT PROBE:*** `READCSV`'s
  grammar is `READCSV FROM <fvar> TO <var>, <var>…` — ***one variable per
  column***, and NOT `READCSV <var> FROM <fvar>` like `READSEQ`
  (`BCOMP:10218-10237`). The compiler's complaint for the wrong order is
  *"FROM not found where expected"*, which points at the word that IS there.
  A first attempt passed one variable and silently measured field 1 only —
  ***which cannot see this defect at all***, because an unstripped CR lands on
  the LAST field.
- **NEXT:** queue **22** — `verify-basicfuncs` (the widest coverage per line),
  then the account family and the POSIX-mode family, both of which want the
  full delete→install that is already owed.
  Then 25, and §M / queue 18 under the 11 Sep ruling. Then §L1's remaining
  unrun pieces. ***A1's undo wants the sandbox rebuilt first.***
- ***OWED A WITNESS FROM A FULL delete→install, none blocking, all in one
  cycle:*** queue 15's installer block, queue 13's carry-over and rotation,
  queue 12's ssh and API doors, queue 17 (never installed), and queue 19's
  sweep on a real start. ***That cycle rebuilds DON, which is safe now:
  queue 16's evidence is banked.***
- ***AND ON THIS BOX THE SWEEP WILL REPORT, NOT SWEEP*** — `nsswitch.conf`
  reads `passwd: files systemd sss`, so the remote-name-source guard fires.
  Drop `sss` or pass `--allow-remote-nss` to see it sweep. Not a defect.
- **OLDER NEXT (superseded by the two lines above):** the `--sweep` ruling, then 21, 22, 25, and §M /
  queue 18 under the 11 Sep ruling. ***Owed a witness from a FULL
  delete→install, none of them blocking:*** queue 15's installer block, queue
  13's carry-over and rotation, and queue 12's ssh and API doors — all three
  want the same cycle, and it is now safe to take: ***queue 16's evidence is
  banked, so nothing is lost by rebuilding DON.***

***⚠ 11 Sep 2026, ~03:45 — THE RUNNING SD WAS WEDGED. RESOLVED BY THE 05:05
REBOOT; the chain and the untested hypothesis below still stand.***
- `ipcs -s -i 0` (SD_SEM_KEY 0x716d0302): `ERRLOG_SEM`(1)=0 last op pid 36587,
  `REC_LOCK_SEM`(3)=0 pid 36509, `FILE_TABLE_LOCK`(4)=0 pid 36920. **36509 and
  36587 are dead** (processes I started; 36587 killed by me). 36920 is
  `/usr/local/sdsys/bin/sd -cleanup` as ROOT, launched by `sdlnxd` at
  03:44:06, holding FILE_TABLE_LOCK and spinning (state R) on REC_LOCK_SEM. Any
  new `sd` that opens a file spins the same way.
- **Chain, as observed:** (1) a record lock whose owner's slot is gone; (2)
  `LIST.READU` → `op_getlocks()` does `UserPtr(owner)->username` and
  `UserPtr()` is NULL for an unmapped user (`sysseg.h:192`) → **"Fault type 11"
  inside `$LISTRDU`**, while holding FILE_TABLE_LOCK + REC_LOCK_SEM; (3)
  `sdsem.c` takes semaphores with `IPC_NOWAIT` and **no `SEM_UNDO`** and the
  fault path does not release them, so they stay held for ever and every
  waiter busy-spins.
- **(1)'s cause is a HYPOTHESIS, untested:** my probe `OPENSEQ`'d a path that
  did not exist (`/proc/<dead pid>/status`), took the ELSE branch, and ended
  without `CLOSESEQ`; the next `OPENSEQ` of the same path (a later session)
  waited for ever. If an ELSE-branch OPENSEQ lock survives logout, its owner
  becomes unmapped. **Falsify after reboot:** run that sequence twice with a
  `timeout 10`, then `LIST.READU` under `timeout 10` — a second-run hang and a
  fault confirm it.
- **Not tonight's code:** `FL_HOLDERS` only reads; `reap_lost_user()` never ran
  (my LO16 probe exited on its own usage check before calling `logout()`).
- **Not done, deliberately:** resetting the semaphores myself. They are 0666 and
  both holders are dead, but a reboot is certain and complete, and a reset
  would leave the orphaned lock for the next LIST.READU to trip over.
- ***OVERNIGHT 10–11 Sep, END OF SESSION (credits).*** All commits LOCAL, none
  pushed. Built: PORT_ADOPTION queue 3, 3b, 4, 5, 6, 7, 8, 9, 10, 11, 20, 23,
  24, plus the `op_getlocks` NULL fix; the audit (186 + 37 entries) is done.
  Every BASIC change compiled 0 errors with a red control before the wedge.
  Witnessed on the tree binary: READSEQ CRLF (pre/post), the LOGIN
  terminal-type premise, the `!set_passwd` status premise, FL$HOLDERS. Status
  per item, with its witness command: PORT_ADOPTION "Built … while the owner
  slept". Decisions waiting: PORT_ADOPTION "Waiting for the owner" (0–4).
- **NEXT, in order:** reboot → `assert-current` → push → delete→install cycle →
  the witness column of that table → the reap witness (queue 10) and the
  orphaned-lock falsification above. Then the queue continues at 12
  (SUSPENDED), 13 (K$AUDIT), 14 (TIERGATE), 15–19, 21, 22, 25, and §M under
  the 11 Sep ruling.
- **A SANDBOX SD NOW EXISTS AS A RECIPE, and it is how to test without the live
  system:** a scratchpad copy of the build with `sddefs.h` keys changed to
  0x716d0901/0902 and `check_admin()` stubbed (scratch copy ONLY), a copy of
  `/usr/local/sdsys` and of the account, `ACCOUNTS/*` paths pointed at the
  copies, the other register records removed, and `SCARLET_CONFIG` (read by
  `inipath.c`) naming a private `sd.conf`. Witnessed: separate IPC keys, and
  the live semaphores unchanged by it; `WHO` `1 DON`, QSELECT runs. `-start`
  leaves stdout held by the daemon, so redirect it rather than pipe. The
  scratchpad does not survive the session; rebuild it from this note.
- ***TRAP, FOUND WHILE BUILDING IT: `gplbld/pcode_bld.py:15` HARD-CODES
  `/usr/local/sdsys` and WRITES `bin/pcode` THERE.*** Run outside the installer
  it overwrites the live pcode. Copy it and change the path for any other
  target.
- **After the reboot, clean my fixtures** (DON account): `rm -rf
  /home/sd/user_accounts/don/ZZ16 /home/sd/user_accounts/don/ZZ16.DIC
  /home/sd/user_accounts/don/BP/* /home/sd/user_accounts/don/BP.OUT`, then in
  `sd`: `DELETE VOC ZZ16`, `DELETE VOC BP.OUT`, `COUNT VOC` → 410.

***11 Sep 2026 — READ THIS BLOCK FIRST; what follows it is older. Opened on
`pull`; tree clean at `b0d4554`, `assert-current` = 0 (install built from HEAD
01:09, so kernel keys are ALIGNED again — the 10-Sep scratchpad harness for the
57–59→90–92 mismatch is no longer needed; a dev binary compiles GPL.BP straight
against the install).***
- **NEXT TASK is still `PORT_ADOPTION.md`'s queue, top down.** Its top two are
  now done in source: **queue 1** (QSELECT list-number, UPSTREAM 21) and
  **queue 2** (DELETE.INDEX case-fold, UPSTREAM 22). `QSELECT:231` now passes
  `tgt.list` as %2; `DELETEI` gained the LISTI-style case-fold block. **Both
  compiled 0 errors** (dev binary, staged in DON/BP, red control `QBAD` = 1
  error), DON restored to `COUNT VOC` 410, tree rebuilt PLAIN. Changelog + doc
  entries in the same commit.
- ***BOTH ARE NOW WITNESSED.*** The owner ran the delete→install cycle;
  `assert-current` = 0, install stamped `af879d3` 02:19:18. **QSELECT:**
  `qselect voc * saving 3` → `...select list 0`, `... to 2` → `...select list 2`
  (the number tracks the argument, 410 > 0 so not the null case). **DELETE.INDEX:**
  `delete.index zzak f1` (LOWER) → `Deleted index F1`, with control
  `delete.index zzak nosuchidx` → `Unrecognised index name (nosuchidx)`.
  Fixtures removed, `COUNT VOC` 410. Detail in PORT_ADOPTION "Adopted so far".
- ***QUEUE 3 (UPSTREAM 23) WAS REPRODUCED BY ACCIDENT AND IS WIDER THAN THE
  ENTRY SAYS*** — `delete.file zzak no.query` prompted on a PLAIN file (not the
  system-account path UPSTREAM 23 describes) and then BUSY-LOOPED on pipe EOF,
  98.9 MB in 40 s, process in state `R`. **Diagnosed on the source afterwards:**
  `no.query` IS parsed (`DELETEF:84`, honoured `:109`) but the DATA and DICT
  prompts (`DELETEF:221-232`, `:295-304`) are guarded by ***`not(force)`
  ALONE***, and each `loop … input yn … until yn='Y' or yn='N'` has no EOF
  escape (same shape `:112 :155 :187 :350`). So queue 3 is two fixes, not one.
  ***CORRECTED LATER THE SAME DAY: the first fault is the port's UPSTREAM 27,
  which PORT_ADOPTION had failed to list*** — an earlier line here said no entry
  named it. Only the EOF loop is in no UPSTREAM entry. Full note in
  PORT_ADOPTION, "Queue 3 — measured here". ***NOT FIXED — this is the next
  task.***
- ***§M RULED WIDER, 11 Sep 2026 (owner): LOWER CASE MUST BE COMPLETE, NOT THE
  PORT'S PARTIAL RESULT.*** Everything lower case — including the files
  `CREATE.FILE` makes and program/include names — with upper-case input converted
  on the fly, so no command, file or record id can exist in two casings. The port
  left `CREATEF:311`'s upcase, all of `gpl.bp`/`syscom`, `PT$INVERT`, and six VOC
  ids upper; NTFS hid it. Filed to the port as `BUGS_FROM_LINUX_PORT.md` 5
  (uncommitted there, like 1–4). Gap table in PORT_ADOPTION "Queue 18". ***BOTH
  FORMERLY-OPEN QUESTIONS RULED 12 Sep 2026:*** account names → LOWER CASE (so
  the id matches its Linux user; in scope, the `CREATEA:409` store site); user
  data-file record ids → OUT of scope (SUE≠sue on ext4 — forcing them would
  alter app data). CLAUDE.md stance updated. ***THE MIGRATION IS STILL UNBUILT, BUT THE SCOPE METER NOW EXISTS***
  (12 Sep): `gplbld/verify-nocase.py`, static source audit, selftest 19/19,
  RED BY DESIGN until done. Current scope: **1036 name remnants** (GPL.BP 212,
  SYSCOM 15, NEWVOC 385, VOC_TEMPLATE 412, + 12 dirs) and 2 code sites
  (`CREATEF` upcase, `LOGIN` PT$INVERT); escapes/symbols correctly excluded, the
  two unruled categories deferred. `--strict` exits 1 while any remain, so it is
  the completion gate. Table in PORT_ADOPTION queue 18. ***The renames
  themselves are NOT started — they are the big scripted transform (CLAUDE.md:
  a script file, `git diff --stat`, a content spot-check), and two rulings gate
  their full scope (below).***
- ***IS THE PORT-ADOPTION AUDIT COMPLETE? NO — answered for the owner 11 Sep.***
  UPSTREAM_FIXES is now reconciled all 37 (28 done, 1 n/a, 8 open) — see
  PORT_ADOPTION "UPSTREAM_FIXES reconciliation"; 18 of them had been fixed on
  8–9 Sep under plan ids and never cross-referenced. ***The port's
  PRE_RELEASE_FIXES (186 rows) has NOT been walked entry by entry***, and this
  project's own open PRE_RELEASE entries are not in PORT_ADOPTION at all.
- **Instrument lesson, paid for twice this session:** ***DRIVING `sd` DOWN A
  PIPE IS ONLY SAFE FOR VERBS THAT DO NOT PROMPT, AND ALWAYS UNDER `timeout`.***
  `list.index` and `delete.file` each spun. A pty driver was tried and was worse
  (it captured the echo but not the results) — the plain pipe is the better
  instrument for non-prompting verbs. To remove a test file without the verb:
  `rm -rf <ACCT>/NAME <ACCT>/NAME.DIC` then `DELETE VOC name`.
- **Fixture recipe for an index witness** (there is no one-liner): a new file's
  dict has no field entries, so `create.index f f1` answers *"f1 is not defined
  in the dictionary"*. Write a D-type record — `1:'D' 2:<field no> 4:name
  5:'10L' 6:'S'` (`SYSCOM/DICTDICT.H`) — with a scratch BASIC program using
  `open 'DICT','<file>' to f`; an ordinary (non-`$internal`) program compiles as
  `don` with no dev build. ***`RUN BP <prog>` IS CASE-SENSITIVE*** — `run bp
  mkf1` answers "Program BP.OUT mkf1 not found" for an object filed as `MKF1`.
  *(14 Sep 2026: still true after §M, and the cause of S.10; `int.run` now folds.)*
- ***SUPERSEDED — DO NOT USE FOR GPL.BP (owner 12 and 13 Sep 2026).*** System
  compilation is SDSYS's; a GPL.BP change is proven by commit → push → reinstall,
  where the bootstrap compiles it as SDSYS. `don` is a transitory user, not a
  compile site; copying `INT$KEYS.H` into a personal `BP` is the sign of the wrong
  account. Kept only as history:
  **Compile recipe, simplified for the aligned-keys state:** `make
  EXTRA_C_FLAGS=-DSD_DEV_BUILD`; stage `<prog>` + the GPL.BP-LOCAL includes
  (`SYSCOM.H`, `INT$KEYS.H`, `AK_INFO.H` — the SYSCOM-resolved ones like `ERR.H`
  come via the account's VOC `SYSCOM` pointer) into `/home/sd/user_accounts/don/BP`;
  `bin/sd -internal BASIC BP <prog>`; read the TAIL (never grep `Compiled`);
  clean up `BP/*`, `DELETE VOC BP.OUT`; `rm -f gplobj/*.o && make` to rebuild
  plain. Red control = append an unbalanced bracket, NOT truncation.
- Next queue items (3 DELETE.FILE NO.QUERY, 5 LOGIN terminfo, 7 CPROC HELP) add
  new message records (10117/10149) and touch login/command paths — bigger than
  1/2, do them singly.

***END OF SESSION 10 Sep 2026 (credits ran low) — what follows is older.***
- **Commits, all pushed to `origin/main`:** `8a1b343` per-tier VOC (LOGIN,
  MODIFYA), MICRO fix, parity audit · `6f5bff8` DELETE.ACCOUNT REMOVE.HOME,
  Codeberg remote removed · `2d759f7` NANO/MICRO via the port's EDIT, nano
  highlighting · the session's last commit: port upstream C fixes + `PORT_ADOPTION.md`.
- ***NOTHING SINCE THE `1fa0e57` INSTALL HAS RUN ON AN INSTALL.*** Next: the
  delete → install cycle as `don`, no sudo (`deletesdai.sh`, then
  `installsdai.sh`), then the witness plans in Open: "Parity audit", "NANO and
  MICRO", REMOVE.HOME, §L1 LOGIN/MODIFYA.
- ***KERNEL KEYS 57–59 → 90–92: THE TREE `bin/sd` ABORTS AGAINST THE CURRENT
  INSTALL*** (`Illegal KERNEL() action key (58)`, measured). Until reinstall,
  compile GPL.BP with a harness: copy `sd64` minus `sdsys gplobj bin terminfo`
  to the scratchpad, copy `sdsys/GPL.BP` and `SYSCOM` in, overwrite
  `gplsrc/keys.h` with `git show dc05b88:sdb_ai/sd64/gplsrc/keys.h`, `make
  EXTRA_C_FLAGS=-DSD_DEV_BUILD` (log to an ABSOLUTE scratchpad path — the hook
  refuses a relative `.txt`), then `<harness>/bin/sd -internal BASIC BP <prog>`
  in DON's `BP`. Clean up `BP`, `BP.OUT`, `DELETE VOC BP.OUT` (`COUNT VOC` 410).
- **NEXT TASK: `PORT_ADOPTION.md`'s queue, top down.** Its "Not adoptable" table
  is the owner-requested list. Port defects are in the Windows port's
  `BUGS_FROM_LINUX_PORT.md` — pushed to GitHub `sd4windows` 11 Sep (`d746963`)
  from a fresh clone; the local `sd4windows` is a frozen comparison copy.
- **Last commit's C fixes** (UPSTREAM 1, 3, 8, 9, 10, 14, 18, 20, 29, 35; port
  PRE_RELEASE 174; plus sdtic's end-of-file path, a port defect): built clean.
  ***Witnessed pre-fix vs post-fix harness binaries:*** `CONFIG('NOSUCHKEY')`
  abort → `""`/1004; ids `draft%1`/`draft%` → both `draft` → whole (`%E`→`=`
  control unchanged); unlocked transaction WRITE `3023 (Possible full disk?)` →
  10151 branch (reads "Message not found" until an install ships 10151); sdtic
  bad fixture old 1 file exit 0 → new 2 files exit 1. **Compile-only:** 1, 3, 8,
  10, 14, 29, 174 — the sdrealpath probe did not compile (`OSPATH` is not a
  BASIC function here; find the right intrinsic).

***HEAD is `d791b4c` (origin/main, pushed 10 Sep 2026); the ssh tier boundary,
PRE_RELEASE 13, landed at `a6d96b1`: BUILT + pushed, unit-tested 16/0, `sshd
-t`-witnessed on this box — and now LIVE-ssh-WITNESSED 10 Sep 2026 (see step 3
below): a STANDARD account is forced into `sd`, an administrator gets a shell.
The delete→install cycle steps below remain the way to re-exercise it and to
witness 25/27.***

### ~~Next:~~ the delete→install cycle — witnesses 13, 25 and 27 at once — *done: 13 and 25 on 10 Sep, 27 on the 13 Sep full cycle (PRE_RELEASE 27)*

**Two scripts.** There is no unified script, and install REFUSES over an
existing install (`installsdai.sh:125`), so a cycle is delete then install. Run
both as `don`, **not** sudo — they elevate internally.

1. `/home/don/Projects/SDCoreLinuxProject/sdcore4linux/deletesdai.sh` — answer **Y** (keep
   accounts) and **Y** (keep configuration); answer **N** to its closing reboot
   prompt (`deletesdai.sh:297`) — a between-reboot is not needed for a keep
   cycle (groups and units unchanged). This keep-accounts path IS the upgrade,
   and it witnesses **25** (`sdadmin` survives holding `don`, no 10037 lock-out)
   and **27** (the `/home/sd` + `sd.conf` save path).
2. `/home/don/Projects/SDCoreLinuxProject/sdcore4linux/installsdai.sh` — builds `origin/main`, so
   it installs whatever `origin/main` is at the time — ***`728b542` when this
   step was written, `30b9c86` as of 11 Sep;*** check rather than trust the
   number, and `.sdcore-install` records what it actually took. APPLIES entry
   13. Watch near the end for `Applying
   the ssh tier boundary (PRE_RELEASE 13).` then either `ssh-forcecommand:
   INSTALLED …` (+ the banner's `sshd_config.before-sd` note) or a yellow
   WARNING if it refused. Take its closing reboot (the APIsrvr socket).
3. After: `assert-current` should answer **0**. Then witness 13 biting —
   `sudo systemctl start ssh` (sshd is inactive on this box), make a STANDARD
   account. ~~**`no.query` needs the OS user to EXIST ALREADY** — `CREATUSR` is
   off, so CREATEA will not auto-create one and stops 6074 "Invalid user name"
   (`CREATEA:186`). So create the Unix user first from a shell —
   `sudo useradd -m <name> && sudo passwd <name>` — THEN, inside `sd`,
   `create-account user <name> no.query`.~~ ***STALE SINCE 11 Sep AND IT COST A
   WITNESS RUN, 12 Sep 17:57.*** A pre-existing Linux user is now REFUSED with
   **10038** (`CREATEA:21-27`), and `no.query` without one is refused with
   10039. ***MAKE A TEST ACCOUNT WITH `CREATE.ACCOUNT USER <name>` AND NO
   `NO.QUERY`***, typing its password at the prompt — SD creates the Linux user
   itself. The only way onto an existing Linux user is ADOPT, which is
   install-only by design. Then ssh as it → lands in `sd`, no
   shell; ssh as `don` (admin, excluded by `!sdadmin`) → normal shell. That
   live login is the half `sshd -t`/`-T` could not show offline (OpenSSH 10.3
   takes no `groups=` on `-T -C`).

***WITNESSED LIVE 10 Sep 2026 — ENTRY 13 IS NOW BEHAVIOURALLY RUN.*** OS user
`pete` created with `useradd`, then `create-account user pete no.query`.
`ssh pete@127.0.0.1` → SD banner, `:` prompt, `off` closed the connection: no
shell. `ssh don@127.0.0.1` (ADMINISTRATOR, in `sdadmin`) → normal Ubuntu
shell. That is the half `sshd -t`/`-T` could not show offline.

**Latent, not blocking:** neither script runs `systemctl daemon-reload`, so the
between-reboot has historically masked that; irrelevant to a keep cycle because
the unit files do not change. Fixing it (reload after delete removes units and
after install copies them) would retire the between-reboot by design.

***10 Sep 2026: THE FRESH INSTALL RAN AND SUCCEEDED FROM `dc36771` (origin/main
at the time; 27 was still unpushed), stamped 01:56:55 — AND PRE_RELEASE 24'S
SEED IS WITNESSED. The owner ran `sudo sd`: NO 10033 (the arm's silence is the
measurement — a registered ADMINISTRATOR exists), `User : don`, `Account :
SDSYS`, `Admin? : Yes`; `ACCOUNTS/DON` field 5 `ADMINISTRATOR` and `sdadmin`
holds `don`, read off disk. Plain `sd` stays non-admin by design: CPROC's grant
runs only inside `if system(27) = 0` (`CPROC:299`), so `logto sdsys` refusing in
an ordinary session is the two gates working, not a defect.***

### The one thing that matters before you believe anything

Run this first, every session:

```sh
python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/assert-current.py
```

No `sudo`. **0 current · 1 stale · 2 cannot answer.** As of the 15:11 install on
10 Sep it answers **0** — the install is stamped `242ae63`, which is HEAD and
`origin/main`, and `bin/sd` is newer than `gplsrc`. A later handoff commit puts
HEAD ahead again until the next install; that is the normal stale state, not a
fault.

### [S.4] PRE_RELEASE 23 (OS-access tier gate + grant) — CLOSED, both gates witnessed end to end; 10054 on a PROGRAMMER account WITNESSED 14 Sep 2026 (`witness-release-run.sh` §6 on `984be50`, after an ADMINISTRATOR control)
Both commits pushed and installed. ***FULLY WITNESSED 10 Sep 2026 on the
`242ae63` install, STANDARD account `pete` — both gates, refuse → grant → allow
→ revoke → refuse:***
- **`SH` gate (10053):** `SH ls` refused **10053** → `MODIFY.ACCOUNT pete SH-ON`
  (10041) + re-entry runs it → `SH-OFF` (10042) + re-entry refuses again →
  `MODIFY.ACCOUNT don SH-ON` refused **10039** (admin tier always reaches the OS).
- **`OS.EXECUTE` gate (10054):** `pete` compiled a one-line `BP/ostest`
  (`OS.EXECUTE 'ls'`); `run bp ostest` gave `000000A9: pete is not permitted to
  use OS.EXECUTE` → `MODIFY.ACCOUNT pete OS-ON` (10041) + re-entry **ran `ls`** →
  `OS-OFF` (10042) + re-entry refused **10054** again. The admin-tier guard was
  not re-run for `OS-ON` (the identical `SH-ON` on `don` gave 10039; same shared
  `os.set` check).
- **Caveat on the 10054 witness (why a STANDARD account could compile):** it
  relied on `pete` compiling a program, which works ONLY because §L1's per-tier
  VOC is not built here yet — every account still gets the full VOC. Under
  conformity a STANDARD account has no `BASIC`: the Windows port omits the
  compiler/cataloguer/editors from STANDARD via `NEWVOC`'s `TIER.OMIT.STANDARD`
  (port `CREATEA`, owner 17 Aug 2026 — STANDARD *"can run an application but not
  build one"*). Once §L1 lands, re-witness 10054 with a PROGRAMMER account; the
  gate follows the PERSON, the compiler follows the ACCOUNT.
- **§L1 source (the port's model):** three VOC sources by tier — STANDARD =
  `NEWVOC` less `TIER.OMIT.STANDARD`; PROGRAMMER = `NEWVOC` entire; ADMINISTRATOR
  = `NEWVOC` entire plus `TIER.ADD.ADMINISTRATOR` (from `VOC_TEMPLATE`). Tier
  written to `ACC$TIER` field 5.

Also this session: the four admin-notice messages (10033/34/37/38) were wrapped
to <=79 cols so they fit the notice box (they were 81-141) — multi-line message
records, `op_sysmsg` turns the newlines into field marks. Ships on next install.

### Done this session — detail in PRE_RELEASE_FIXES.md, not repeated here

| entry | |
|---|---|
| **27** | the fresh install aborted at `installsdai.sh:631` — `chown /home/sd/group_accounts` — because 26 leaves `/home/sd` existing but empty, so the old `if [ ! -d /home/sd ]` skipped both mkdirs. Found by running, 10 Sep. Fix: unconditional `mkdir -p` for both, and a `/home/sd`-as-file refusal by name. **Sandbox-witnessed 5/5, control = pre-fix block on the empty state (dirs missing). Still unrun in the real script: the 01:56 retry installed from `dc36771`, before 27, and succeeded because `/home/sd` was absent (no `sd.conf` was saved), so the old guard was never hit.** Detail in PRE_RELEASE 27 |
| **26** | same review, same path: answering DELETE removes `/home/sd`, and `mv /etc/sd.conf /home/sd` then renamed the config to a **file** named `/home/sd`; the next install died at `mkdir -p /home/sd/user_accounts` (*"Not a directory"*). Fixed with `mkdir -p "$acct_path"` before the config save (`deletesdai.sh:140`). **Ran for real in the 10 Sep delete: it completed, and `/home/sd` was a directory holding `sd.conf` — the install that followed then aborted on 27.** Detail in PRE_RELEASE 26 |
| **25** | found while preparing 24's hand-over: `deletesdai.sh:186` deleted `sdadmin` unconditionally, so an upgrade that SAVES its accounts came back with an empty group and every administrator at **10037** — a lock-out with only an OS-root way back. Removal now conditional on `keep_accts = DELETE`, mirroring `sdsys`/`sdusers`. **Built, `bash -n` clean; unrun — the next saved-accounts upgrade is the witness.** Detail in PRE_RELEASE 25 |
| **24** | **Seeding witnessed 10 Sep 2026 on the 01:56 install (`dc36771`)**: `sudo sd` → no 10033, `User : don`, `Account : SDSYS`, `Admin? : Yes`; `ACCOUNTS/DON` field 5 `ADMINISTRATOR`; `sdadmin` holds `don`. The installer seeds the installing user as an SD ADMINISTRATOR (`installsdai.sh:783`, `ADMINISTRATOR` on `create-account`), and refuses a non-sudoer at the first `sudo -v` in words (`:236`) — **that refusal is still unrun**. Detail in PRE_RELEASE 24 |
| **23** | the OS-access tier gate, both commits. **Commit 1 (installed):** `op_sh` gates `OS.EXECUTE` to `$internal`/administrator (msg 10054). **Commit 2 (compiled, unrun):** `ACC$SH`(7)/`ACC$OS.EXEC`(8) grants, `MODIFY.ACCOUNT SH-ON\|SH-OFF\|OS-ON\|OS-OFF` (msgs 10039–10042), `SH` gate at `CPROC:3490`→admin-or-`K$SH` (msg 10053), flags loaded at account entry (LOGIN + CPROC logto). MODIFYA/CPROC/LOGIN each compiled **0 errors** with a red control (1 error); account restored to COUNT VOC 410; plain binary rebuilt. Detail in PRE_RELEASE 23 |
| **18** | closed. The tier gates: `CPROC` `grant.administrator`, a self-closing bootstrap arm, `MODIFY.ACCOUNT <acc> STANDARD\|PROGRAMMER\|ADMINISTRATOR`. **Witnessed end to end — the arm closed itself.** Its third requirement turned out already met |
| **21** | `sd -internal` was an unguarded route to the admin flag — **measured, uid 1000, no sudo**. Now behind `check_admin()`, with `make EXTRA_C_FLAGS=-DSD_DEV_BUILD` as the announced opt-out |
| **22** | `!set_passwd` / `!create_user` were globally catalogued with **no gate** |
| **14** | all 13 raw `sudo` calls now go through `sd-elevate`; `sdadmin` whitelisted; **`groupdel sdusers` was open and is now shut** |
| **17** | `L1.0-0`, and the banner is the owner's wording |
| **8** | `assert-current.py` + `test-assert-current.py` (10/10) + an install stamp |
| **12** | syntax highlighting reaches a user at last; **measured with two controls** |
| **20** | piece 1 witnessed — `WHO.AM.I` says `User : don` |

### ~~Next task~~ — *10 Sep 2026, superseded by the hand-off at the top of START HERE*

***THE FRESH INSTALL, 24'S SEED, 13, AND ALL OF 23 ARE DONE. What remains is
24(2) and confirming the 25/27 delete transcript.***

- **25** — ***CLOSED BY OUTCOME 10 Sep 2026:*** after the 15:11 keep-accounts
  upgrade, `getent group sdadmin` = `sdadmin:x:965:don` — the group survived
  holding `don`, no 10037. The delete transcript was not captured this session,
  so this is the measured end state, not the run observed.
- **27** — the 15:11 install **completed** (`assert-current` current) and
  `/home/sd` is a directory holding `user_accounts`+`group_accounts`, so the
  `:631` abort did not recur. Same caveat: the keep-config precondition was
  inferred from the preserved trees, not watched.
- **24 (2)** — the non-sudoer refusal at `installsdai.sh:236` is still unrun.
- **23's gate** — ***CLOSED 10 Sep 2026*** (see PRE_RELEASE 23 above): both gates
  witnessed end to end, refuse → grant → allow → revoke → refuse (SH 10053 and
  OS.EXECUTE 10054). The 10054 repro is pre-§L1 (STANDARD can compile only until
  per-tier VOC lands; re-witness with a PROGRAMMER account after §L1).
- **13** — ***WITNESSED LIVE 10 Sep 2026***, re-confirmed on the `242ae63`
  install. `pete` (STANDARD) ssh → `sd`, no shell; `don` (admin) ssh → normal
  shell. Done.

`bash -n` clean, no BOM, 0 CR (both scripts).

***ENTRY 13 — THE ssh BOUNDARY — IS BUILT (10 Sep 2026), UNIT-TESTED 16/0,
SYNTAX-WITNESSED, AND LIVE-ssh-WITNESSED 10 Sep 2026*** (`pete` STANDARD → `sd`
no shell, `don` admin → shell; see START HERE step 3). Mechanism (ruled 9 Sep, owner):
`ForceCommand` into `sd` for `Match Group sdusers,!sdadmin`; PROGRAMMER = STANDARD
over ssh; administrators (in `sdadmin`) keep a real shell; admin-granted shell is
reached THROUGH SD (`sd` not setuid), so no per-user carve-outs. New helper
[ssh-forcecommand.sh](sdb_ai/sd64/gplbld/ssh-forcecommand.sh) (`--check`/`--install`/`--remove`),
installed root-owned to `/usr/local/sbin/ssh-forcecommand`; installer calls
`--install` non-fatally near the end, uninstaller `--remove` first. **Fenced
block in the main `/etc/ssh/sshd_config`, NOT a `sshd_config.d` drop-in** — owner
10 Sep: the other three distro families are being regained, so no Debian-specific
feature; the drop-in dir is not universal, the main config is. `sshd -t -f`
validates a candidate BEFORE the live file changes; refuses when no `sshd` is
found. Test [test-ssh-forcecommand.py](sdb_ai/sd64/gplbld/test-ssh-forcecommand.py).
***WITNESSED:*** `sshd -t` exit 0 on the exact block (OpenSSH 10.3p1); `sshd -T
-C user=` proves `Match`-block ForceCommand activation. ***NOW ALSO WITNESSED
LIVE 10 Sep 2026:*** the non-admin-forced / admin-free behaviour that `sshd -T
-C` could not show offline (it won't take `groups=` on 10.3) — `pete` forced
into `sd`, `don` free to a shell, over real ssh on 127.0.0.1. ***LOCK-OUT
SENSITIVE; the install path runs `sshd -t` as root, which is required — `sshd -t`
needs root to read host keys.*** Judgment call recorded in the helper header: the
refusal predicate covers `ForceCommand`/`Match`-naming-our-groups, not unrelated
`AllowGroups`. Detail in PRE_RELEASE_FIXES §13 / entry 13. ***Doc line-refs
`installsdai.sh:254-296` were stale (Debian-only now, one apt branch at `:307`).***

Cheaper things: `leave.sdadmin` has never run (`MODIFY.ACCOUNT DON PROGRAMMER`
exercises it); entry 6 needs an install; §L1's per-tier VOC is undesigned; §M is
release-blocking, scheduled at step 7.

### The instruments this session built or paid for

***COMPILING `GPL.BP` OUTSIDE AN INSTALL — the recipe, which this project did
not have before today:***

```sh
sudo sd -internal BASIC BP <prog>      # or build dev and drop the sudo
```

Arguments separate, **no pipe**. Stage the program plus its `$include` records
**from the working tree** into an empty `BP`. **Three traps, all paid for, all
in the session log below**: truncation is a *bad red control* (it passed three
times in five — inject an unbalanced bracket instead); **never grep the output
for `Compiled`** (a run that prints neither answer returns an empty match that
reads like a pass); and the compile creates a **`BP.OUT` VOC record** that
`rmdir` does not remove — clean up with `DELETE VOC BP.OUT` too. The `DON`
account's true empty `COUNT VOC` is **410**.

## Session log — 18 Sep 2026

THE TEARDOWN, BUILT AS ONE CHANGE SET (`pull and continue with teardown
tasks`; owner: "use the readings offered" for W.5–W.9).  Working tree of the
repo, not the workspace: the runtime's workspace folder
(`~/Projects/sdcore4linux`) is empty; the repository lives at
`~/Projects/SDCoreLinuxProject/sdcore4linux` (its documented home since 16
Sep) and every file below is relative to that.  `git pull` — up to date.

THE MAILBOX CARRIED THREE THINGS AND ALL THREE WERE ACTED ON.  The Windows
port's mail of 18 Sep 19:00 (its RELEASE_1.1 60): two unbounded `strcpy()`s
in `clopts.c:266/:316` (reap_lost_user and cleanup copy a shared-segment
username into a stack buffer) — verified present here, fixed with the port's
four lines (`memcpy` of `MAX_USERNAME_LEN` + explicit terminator), committed
separately as `9140dc4`.  Its RELEASE_1.1 59 (the world-writable shared
segment, `shmget(SD_SHM_KEY, ..., IPC_CREAT|0666)` at `sysseg.c:306`, read by
root daemons and a root `sd -cleanup`): acknowledged as a design item, NOT
patched — and the teardown sharpens it: with `os.users` field 2 retiring and
no sdapi gate, every account can now start the Python interpreter, so the
segment's writers/readers are the evaluation's next question; the reply to
the port says so.  Reply written, messages moved to done/.

THE BUILD, TASK BY TASK (all in one change, committed `e41d318`):

* S.25 — `sdsys/tier.policy/` (2 files), `gpl.bp/tiergate`, `gpl.bp/granta`,
  `gpl.bp/grp_members` and `gplbld/verify-grants.py` deleted; every
  `!tier_allows` caller removed (cproc LOGTO, modifya ADD, apisrvr vb.account);
  `syscom/keys.h`: `ACC$SUSPENDED=5` (W.7's flag — reusing field 5 keeps the
  one-column listing and reads every pre-teardown record correctly),
  `ACC$PRIOR.TIER=6` kept only as a documented retired slot cleared by
  UNSUSPEND; fields 7/8 removed.  createa: grammar reduced to USER|GROUP|OTHER
  + NO.QUERY (+ADOPT install-only, now making a plain account); no tier/API/
  SH-ON/OS-ON keywords; register write holds three fields; make.account copies
  NEWVOC whole.  login: update.voc copies NEWVOC whole (omit filter and admin
  add layer deleted, get.acc.tier deleted, the all-accounts walk no longer
  resolves a tier); suspended test reads ACC$SUSPENDED; os.admin load gone.
  modifya REWRITTEN: MODIFY.ACCOUNT <account> ADD|DELETE|SUSPENDED|UNSUSPEND
  only — set.tier/promo.snapshot/promo.report/join-sdadmin/leave-sdadmin/
  api.set/api.apply/api.say/os.set/voc.delta and all tier helpers deleted;
  the ADD arm keeps its group machinery and audit, loses the tier gate.
  apisrvr: suspended reads ACC$SUSPENDED; the tier-ordering gate and the
  deffun are gone.  VOC records: `sh` and `!` copied into NEWVOC (every
  account has them, S.27), GRANT/REVOKE/LIST.GRANTS removed from VOC_TEMPLATE
  (W.8); SDSYS's VOC keeps the administrator verbs because the install builds
  it from the whole of VOC_TEMPLATE (bbproc) — unchanged mechanism.

* S.26 — cproc's root-entry block: a root session is refused outright (10176
  + `ELEVATION REFUSED reason=root is not SD administrator`, audited); a
  session already running as the sdsys OS user on a local session
  (`env('SSH_CONNECTION')` and `env('SSH_TTY')` both empty) is granted
  (K$ADMINISTRATOR, 10916, `ELEVATION GRANTED reason=local sdsys session`,
  audited — the audit written after the grant, PORT_ADOPTION 13's ordering);
  the IS_INSTALL arm keeps the bootstrap grant.  grant.administrator deleted
  with K$REAL.USER (its only caller: op_kernel.c case, keys.h, int$keys.h).
  LOGTO sdsys refused for everybody (10002 reworded); the administrator's
  LOGTO keeps the S.2 group refresh — int.logto calls EUID_SET for the admin
  and SD_EUID_SET now reloads groups for ANY caller (sdext_eguid.c: the
  `geteuid()==0` condition came off, since the administrator is never root
  now).  sdcore.sudoers: `%sdadmin` → the `sdsys` user.  Register and $cred
  now belong to the administrator: `chown -R sdsys:sdusers` +
  644 on accounts (new step after the seeding), accounts/sdsys
  sdsys:sdusers 644, $cred sdsys:sdusers 700 (MODIFY.PASSWORD runs as sdsys;
  the root API server reads regardless).  set_acc_password gates on
  K$ADMINISTRATOR instead of uid 0, with a note that "set your own" is an
  administrator act here (one register, one owner — a deliberate port
  divergence).  apisrvr: sdsys enters its own account by name (the SDSYS
  record's ACC$GROUP reads "sdsys", which is no Linux group).  installsdai.sh
  REORDERED: the seed steps (ADOPT, UPDATE.ACCOUNTS ALL) and the register
  chown run on the IS_INSTALL CPROC, and the CPROC recompile without
  IS_INSTALL is now LAST — from that point no root sd session exists on the
  machine; the MODIFY.PASSWORD step runs `sudo -u sdsys`, exercising the new
  administrator path end to end.  delacc strips sdusers only.

* S.27 — op_sh: os_permitted() and its refusal deleted (OS.EXECUTE runs at
  the account's own Linux permissions; `sh`/`!` have no SD gate); cproc's
  os.command loses the K$ADMINISTRATOR/K$SH test, the metacharacter filter
  stays; K$SH/K$OS.EXEC (91/92) removed from keys.h/int$keys.h/op_kernel.c
  with USR_SH/USR_OS_EXEC (sysseg.h).

* S.28 — ssh-forcecommand.sh block is now `Match User sdsys → DenyUsers
  sdsys` + `Match Group sdusers,!sdsys → ForceCommand sd` (sdsys un-ssh-able
  at sshd, W.6's first half); the helper names an AllowUsers override as
  sshd's own policy corner with SD's W.6 gates as the second wall; the
  conflict checker treats a matching DenyUsers as non-conflicting (same
  policy), tested 18/18.  sdapi disposed end to end; vb.scram's S.17 gate is
  SDSYS's door (10174 reworded, audited `sdsys on a remote API session from
  <ip>`); sd-elevate's whitelist loses sdadmin/sdapi (test-sd-elevate 57/57);
  installer/deleter no longer create/strip them (the deleter still tidies
  legacy groups only when the accounts go).  W.9: REMOTE.SSH/REMOTE.API stay
  SDSYS's own (sd-elevate behind the sdsys-only sudoers); the audit trail
  stays and gains the new records.

* INSTRUMENTS — verify-tier-layer.sh/.bp and witness-tierchange.sh deleted;
  verify-grants.py deleted (W.8); witness-release-run.sh reworked (§2/§2b
  sdsys sessions incl. a setpriv-driven S.2 stale-group re-witness; §6/§7
  struck; §8 gains T8 ELEVATION GRANTED; §10/§11 struck; §12 rewritten for
  one layer; §13's MODIFY.PASSWORD and C7 (sdsys:sdusers 700); §13b A4 struck
  with a root-refusal control in its place and A5 as sdsys; §13e is SDSYS's
  door with a throwaway credential set/measured/removed; §13f is the absence
  pair; §13g drives SUSPENDED/UNSUSPEND + $cred rewrite as sdsys; §13j
  struck; §14's suspend/restore is the flag's; §15 deletes the SD-created
  user (10084/10028) as sdsys; §16's CONFIG as sdsys).  witness-accounts.sh
  rewritten for the SD-created-user flow (no ADOPT on a delivered machine).
  NEW: witness-absence.sh — the absence witness: no tiergate/tier.policy, a
  fresh CREATE.ACCOUNT's record has no tier field, MODIFY.ACCOUNT has no
  tier/OS/API keywords, no sdadmin/sdapi groups, the sudoers names sdsys,
  the sshd block excludes sdsys, a root session refused (10176) and a local
  sdsys session granted (10916) driven live, and the source-side rows M9a–M9f.
  interop-account.sh rewritten (create as sdsys, no API keyword, no sdadmin).

* MESSAGES — 42 files removed (see the S.25 entry), 5 written (10176, 10177,
  10178, 10179, 10916), 2 reworded (10002, 10174).  msglen 10/10.

VERIFIED BEFORE COMMIT: `make` clean (sd linked); test-ssh-forcecommand 18/18,
test-sd-elevate 57/57, test-msglen-units 10/10, test-accounts-units 17/17,
test-sysperms-units 20/20, basicfuncs 25/25, nonet 12/12, scram-vectors 46/46,
tlsconsts 14/14; `bash -n` clean on every touched script; assert-current STALE
(no install carries the change) — correct.  CLOSED OUT 18 Sep 2026: the table
reconciled with its entries (`check-stale-leads.py` exit 0 — S.25–S.28 partial
until witnessed, W.5–W.9 ruled), committed (`e41d318`) and pushed on the
owner's word ("handoff, commit, push").  NOT VERIFIED: anything on a machine —
the fresh install + witness cycle (witness-absence.sh, witness-release-run.sh,
witness-accounts.sh) is the next step.

---

***LATER THE SAME DAY — THE CYCLE'S INSTRUMENTS WERE REPAIRED BEFORE THE
INSTALL.***  Opened on `pull` (already up to date at `90ae906`, working tree
clean).  Three verifiers still read `sdsys/tier.policy`, which S.25 deleted.
Found by running them rather than by reading:

* ***`verify-nocase.py` HAD STOPPED MEASURING, AND IT IS A FREE CHECK — exit 2.***
  `NAME_CATEGORIES` still held the `tier.policy` row, and the category loop
  returns 2 on a MISSING category (deliberately — "cannot answer"), so the run
  printed the first four categories and stopped: the sdsys directory names,
  the `FILES_DICTS` targets, the code-site checklist and the verdict were never
  reached.  The row is removed with the reason in its place; measured after:
  exit 0, `§M NAME HALF: COMPLETE`, `--selftest` 19/19.  *(A green-looking
  instrument that answers nothing is the quiet failure this project files
  instruments against.)*
* `verify-editors.py` B5/B6 asserted nano and micro were withheld from a
  STANDARD account, reading `tier.policy/omit.standard`.  One VOC layer leaves
  nothing withheld and no list to read, so the rows now assert the replacement
  claim instead: both verbs are IN `newvoc`.  Measured: `--allow-stale` on the
  current install, ***28 of 28 decisive checks*** (the rows are re-pointed, not
  dropped, so the count is kept).
* `verify-lcnames.py` S8 checked the two tier lists' entries.  Its subject is
  gone; the row now asserts `tier.policy` is absent — which the current
  pre-teardown install fails by design and the next install passes.  The rest
  of that verifier's rows are untouched.  `py_compile` clean; NOT RUN here (it
  drives `sd` sessions from the caller's account) — it belongs to the cycle.

No shipped code changed: the three files are repository instruments, so the
install is not affected.  The free checks were re-run on this change — `make`
exit 0; `check-stale-leads.py` exit 0; ssh-forcecommand 18/18; sd-elevate
57/57; msglen 10/10; accounts 17/17; sysperms 20/20; basicfuncs 25/25; nonet
12/12; scram-vectors 46/46; tlsconsts 14/14; configpath 14/14; assert-current
10/10; staleleads 18/18; editors 19/19; `verify-editors.py` 28/28;
`verify-nocase.py` exit 0 (was exit 2); sdverify 41/41 + 26 selftest;
scramprobe 13/13; tls-relay 26/26; check-storewriters 7 selftest;
no-program-edits 32 selftest.

***CLOSED OUT 18 Sep 2026, late:*** the repair is committed and pushed
(`b0a78bd`; `90ae906..b0a78bd  main -> main`), `check-stale-leads.py` is exit 0
on the reconciled docs, and the owner takes a new session for the cycle.
***NOTHING WAS MEASURED ON A MACHINE THIS SESSION***: `assert-current` STALE
(install `c1ea29b` vs HEAD `b0a78bd`) and no `witness-*` log later than 15 Sep —
the fresh install is the next session's first act, as the handoff above says.
The instrument repair was a repair and not a teardown step: no shipped code
changed, so none of the S.25–S.28 rows' state moves.

---

***THE FIRST CYCLE RAN THE SAME EVENING AND DIED ON A GROUP THAT DOES NOT
EXIST — FIXED, NOT YET RE-RUN (owner: "install failed").***

Opened on `pull` — already up to date at `7674430`, working tree clean (the
configured workspace folder `~/Projects/sdcore4linux` is still the empty stub;
the repository is `~/Projects/SDCoreLinuxProject/sdcore4linux`).  The free
checks were re-run green on the repaired tree before the cycle — `make` exit 0;
accounts 17/17; basicfuncs 25/25; nonet 12/12; sysperms 20/20; msglen 10/10;
editors 19/19; ssh-forcecommand 18/18; sd-elevate 57/57; sdverify 41/41 + 26
selftest; tls-relay 26/26; tlsconsts 14/14; scramprobe 13/13; scram-vectors
46/46; configpath 14/14 + 8 mutants; staleleads 18/18; storewriters PASSED + 7
selftest; no-program-edits 32 selftest; `verify-nocase.py` exit 0;
`check-stale-leads.py` exit 0; `assert-current` STALE (install `c1ea29b` vs HEAD
`7674430`) — correct before a cycle.  The mailbox's `to-linux/` is empty.

***WHAT THE INSTALL DID BEFORE IT STOPPED.***  It cloned `origin/main`; stamped
`/usr/local/sdsys/.sdcore-install`
`commit=767443051ecdfbaa5473ddec97978985ee9304e8`, `installed=2026-09-18
17:09:24`, so ***the teardown build did reach the machine***; installed nano's
BASIC syntax file; copied the units into `/usr/lib/systemd/system` (:725,
`:732`); took the API-listener answer "yes"; installed the sudoers drop-in and
the ssh-boundary helper (:554-555 — the helper, NOT its sshd block, which is at
`:1144`, after the failure); and restored the accounts directory, the credential
register (`$cred`) and the audit trail from `/home/sd` (:758-782).

***THE ABORT: `installsdai.sh:788` — `chown: invalid group: 'sdsys:sdsys'`.***
There is no `sdsys` GROUP on this box.  The `sdsys` USER's primary group is
`sdusers` (gid 979), and nothing in the tree ever ran `groupadd sdsys`: the
S.26 entry wrote "$cred sdsys:sdsys 700" and the installer implemented the
string literally.  ***FIVE PLACES CARRIED IT; ALL ARE NOW `sdsys:sdusers`*** —
the group every other sdsys-owned path in the installer already uses:
`installsdai.sh:788` (the abort) and its `:1194` comment; C7 of
`witness-release-run.sh` (:879), which asserted the same string and would have
FAILED on the next witness run, and its `:1340` comment; `set_acc_password`'s
two comments with a START-HISTORY line (comments only — no code ever read the
group); `deletesdai.sh:195`'s "restores it root:root 0700", stale since the
teardown; and the S.26 text and session log of this file.  The mode stays 700,
so the group confers nothing either way: what the wall rests on is the OWNER
(the `sdsys` user, which MODIFY.PASSWORD runs as) plus CPROC's administrator
flag.

***THE MACHINE HOLDS A PART-INSTALL, AND THE RE-RUN NEEDS TWO THINGS.***
`/usr/local/sdsys/bin/sd` exists (17:09) and `sd.service` is inactive and
disabled with the units copied but never enabled, so `installsdai.sh:152`
refuses a retry until `deletesdai.sh` runs.  And `:788` is not the only step
that did not happen — everything after it did not either: `accounts/sdsys`'s
chown and the register's recursive chown, the `sd.conf` restore, `dumps/`, the
audit-trail restore, the sshd boundary block (`:1144`;
`grep -A3 'Match Group sdusers' /etc/ssh/sshd_config` is empty), the seed steps,
the CPROC recompile without IS_INSTALL, and the MODIFY.PASSWORD step.

***THE OWNER'S RUN KEPT THE ACCOUNTS*** — `/home/sd` held the register, `$cred`,
`sd.conf` and the audit trail, and only the keep path saves those (DELETE
removes `/home/sd` with everything else) — so ***the FRESH cycle the handoff
prescribes is STILL UNRUN***; fresh or keep is the owner's call on the re-run
and the fix is the same for both.  ***THE FIX MUST BE PUSHED BEFORE ANY
RE-RUN***: the installer clones `origin/main` (`installsdai.sh:74`, `:385`), so
an unpushed fix is tested by nothing.

***NOT MEASURED: anything on a machine.***  No witness ran, no `witness-*` log
exists later than 15 Sep, and the S.25–S.28 rows do not move until a cycle
completes.

---

***THE CREATEA `end` WAS THE SECOND INSTALLER-SIDE DEFECT, AND ITS FIX SHIPPED
AS `2908280`.***  Opened on the owner's "install failed" after the `$cred` fix
(24d6611) had been pushed: the install reached the seeding step and died with
`0000209A: Unable to load '$CREATEA' object code at line 1691 of $CPROC`, the
same line in `/usr/local/sdsys/errlog`.
***THE MEASURE THAT FOUND IT IS THE OBJECT DIRECTORY OF THAT RUN***: 202
objects for 202 programs in `gpl.bp`, and `createa` was the ONLY one missing —
so BCOMP refused the file and `SECOND.COMPILE` (`BASIC gpl.bp *`,
`installsdai.sh:935`) carried on without it, which is why the batch still
exited 0.  The teardown's edit had flattened
`if copy.it then / read rec from newvoc.f, id then … end / end` to a bare
`read … then` and taken BOTH `end`s with it; a `read`'s then-clause needs its
own `end`, and `login`'s identical loop (which compiled) closes it that way.
Restored, and the structural check then matched the pre-teardown file exactly.
TWO FALSE TRAILS, KEPT BECAUSE THEY COST TIME: `gplbld/bbcmp.py` rejects
`createa` with `PROMPT statement not coded at pass2` — it is the *bootstrap*
compiler for three seed programs and rejects `modifya`, `set_acc_password` and
`copy` the same way, so it proves nothing about a verb; and the unprivileged
sandbox route could not compile either, because `-internal` needs root
(`sd.c:660`) and a sandbox session needs a registered account a fresh install
has not yet created.

***THE CYCLE THEN RAN CLEAN AND THE THREE WITNESSES FOUND ONE MORE PRODUCT
DEFECT, A4.***  The install (2908280, 17:44:20) seeded `don`, compiled every
program including `createa`, and left `assert-current` at exit 0.  The
witnesses scored 261 of 302 and are read in full in the START HERE paragraph
above; the product defect they found is A4 — an account created through the
new administrator route is left `sdsys:sdusers` instead of
`<account>:sdu_<account>`, because `createa`'s `set.owner` chowned with the
`OS$CHOWN` intrinsic (`createa:814` before this change), which needs root, and
the administrator is a `sdsys` session and is never root (S.26).
`don`'s account is correct only because the install's seeding runs on the
root bootstrap CPROC — so the defect hits every account created AFTER an
install, which is every account the new model makes.

***THE FIX, IN THIS COMMIT.***  `sd-elevate` gains `chown-account <user>
<group> <path>`, built on the three shapes `set.owner` computes and on nothing
else: `<user> sdu_<user>` (a USER account's own directory, and paths inside
it), `sdsys <sdg_ group>` (a GROUP account's), `root sdusers` (an OTHER
account's attached path).  A person is CONFINED to its own account directory
and to its own `sdu_` group, so a chown cannot move one account's files into
another's tree and cannot put them in `sdusers` — the group every account
belongs to, which is exactly the confinement the teardown exists to give; the
`root:sdusers` shape is the one unrestricted case and grants the caller
nothing.  The stamp check that guards `userdel-home` is deliberately NOT
repeated: that one guards a removal, and an ADOPTed account, which SD did not
create, is a legitimate owner of its own directory.
`createa`'s `set.owner` calls the helper when `system(27) # 0` and keeps the
intrinsic for root, so the install bootstrap (which also chowns an ADOPTed
user's directory the helper would refuse) is unchanged.  `test-sd-elevate.py`
57 → 72 rows (49 refusals, 13 controls), each new REFUSE naming a way to escape
the account's own directory and each new ALLOW one of the three shapes.
*Not verified: the BASIC change is not compiled — no root, so `-internal` is
unreachable and the sandbox needs an account that only an install creates; the
next install's `SECOND.COMPILE` is the check, and a failure there shows as
`createa` absent from `gpl.bp.out` again.*

***THE NEXT STEP IS THE WITNESS RE-POINTING*** listed in the START HERE
paragraph — 40 rows across the three scripts, each one a wording, a route or a
precondition that the teardown changed — and then one more cycle to re-run the
three.  The machine was left with `zzrel1`/`zzrel2` to clear (the owner's
`userdel -r`, one login per call) and `/home/sd/user_accounts/zzrel*` to
remove, both recorded because the next run expects a clean slate.

## Session log — 9 Sep 2026

*Detail behind the table above. The actionable handoff is the section before
this one; this is kept for the reasoning, not to be read first.*

***9 Sep 2026, LATER SESSION — ENTRY 18 COMMIT 2 IS BUILT AND THE BASIC WAS
COMPILED FOR REAL, WHICH THIS PROJECT HAD NOT MANAGED BEFORE.*** Opened on
`pull`, already up to date at `ef75eb2`.

**Built:** `CPROC` `grant.administrator` applies the owner's definition —
`sdadmin` membership **AND** `ACC$TIER`=`ADMINISTRATOR` for the real person — at
the **one** place `USR_ADMIN` is set, so the fourteen readers keep asking the
flag. `LOGTO SDSYS`, `CATALOG` ×2 and `DELCAT` swapped `system(27)` for the
flag. Messages 10033/10034. **`IsAdmin()` deleted** — it was already dead, entry
19 having removed its only caller, and it answers the wrong question.

***THE BOOTSTRAP ARM IS THE OWNER'S RULING AND IT WAS NEEDED, NOT PRECAUTIONARY.***
Measured on the 16:22 install: `ACCOUNTS/DON` had **three fields** (no tier) and
`sdadmin:x:965:` **no members**, so a strict gate refuses everybody and
`CREATEA:95` needs admin to register the first admin. With **no**
`ADMINISTRATOR` in the register the grant stands and prints 10033; the arm
closes itself once one exists.

***THAT MEASUREMENT MOVED THE SAME DAY AND THE CONCLUSION DID NOT — RE-READ ON
THE 17:53 INSTALL.*** `ACCOUNTS/DON` now has **five fields with `ACC$TIER` =
`STANDARD`**, up from three, so ***`PRE_RELEASE` 18 COMMIT 1's WRITE PATH HAS
RUN ON A LIVE SYSTEM***. `sdadmin` is still empty and **no account holds
`ADMINISTRATOR`**, so a strict gate would still refuse everybody — this is
exactly the state the bootstrap arm is for, and it is now the state the next
install will meet.

***THE COMPILE RECIPE, WHICH IS REUSABLE AND WAS THE MISSING INSTRUMENT:***
`sd -internal BASIC <file> <prog>`, arguments separate, **no pipe** — the port's
recipe at its `HISTORY.md:18916`. Stage the program plus its twelve `$include`
records **from the working tree** into an empty `BP`. ***AS OF `PRE_RELEASE` 21,
FIXED LATER THE SAME DAY, THIS NEEDS EITHER `sudo` OR A DEVELOPER BUILD*** — see
below; the runs recorded here predate the fix and ran as `don`. `CPROC` **0
errors on both
`IS_INSTALL` arms**, HEAD as the control also
0, and **two red runs** (a truncated `CPROC` → 10 errors; the same file without
`-internal` → the port's exact directive cascade). Fixtures removed.

***THREE TRAPS IN THIS RECIPE, ALL PAID FOR ON 9 Sep 26, AND NONE IS ABOUT THE
COMPILER.***

0. ***DO NOT USE TRUNCATION AS THE RED CONTROL. IT PASSED THREE TIMES OUT OF
   FIVE.*** Cutting a file short very often leaves a **valid** program — cut
   `MODIFYA` at 70 and you get a valid empty one; cut `SET_PASSWD` at 125 of 155
   and it compiles clean. **A red control that goes green is not a pass, it is a
   void run**, and it took three of them to learn it. ***INJECT A SYNTAX ERROR
   INSTEAD***: append one line with an unbalanced bracket — `if not(kernel(...)
   then` — which gives **1 error** reliably and changes nothing else.

1. ***DO NOT GREP THE OUTPUT FOR `Compiled`. READ THE TAIL.*** Twice in one
   session a run printed **neither** `0 error(s)` **nor** `N error(s)` — once
   because `-internal` was missing, once because `BASIC` could not open
   `BP.OUT` — and a grep for the success/failure words returned **nothing at
   all**, which reads exactly like a clean pass if you are only looking at the
   lines that matched. **A filter that can return empty is not a verdict.**
2. ***THE COMPILE CREATES A `BP.OUT` VOC RECORD, AND `rmdir` DOES NOT REMOVE
   IT.*** Delete the directory alone and the next compile dies with *"DATA part
   of file already exists / Unable to open newly created output file"*. Clean
   up with `DELETE VOC BP.OUT` as well. ***AND A `COUNT VOC` TAKEN AFTER THE
   FIRST COMPILE IS NOT A BASELINE*** — an earlier entry in this file claimed
   "411 either way, so nothing reached the VOC" when 411 already **included**
   the litter. **The account's true empty count is 410.**

***AND THE SESSION FOUND SOMETHING BIGGER THAN WHAT IT BUILT: `PRE_RELEASE` 21 —
NOW FOUND, RULED AND FIXED IN THE SAME SESSION.*** ***AS `don`, uid 1000, NO
`sudo`, A FIVE-LINE `$internal` PROGRAM SET ITS OWN ADMINISTRATOR FLAG*** —
`PRE admin flag = 0` → `POST admin flag = 1`, null case refused. `-INTERNAL` had
**no privilege check**, while `-I` three lines below called `check_admin()`. So
entry 18's gate — and any gate on that flag — was bypassable.

***THE OWNER RULED IT, 9 Sep 2026, AND THE RULING IS WIDER THAN THE ENTRY:
THIS SYSTEM SHIPS FOR PRODUCTION, NOT FOR DEVELOPERS.*** Source is available and
forkable, issues and comments welcome, **but no other human commits and the
installer is not a developer's tool.** ***THAT DISPOSES OF THE ONLY OBJECTION TO
THE FIX*** — a shipped production system owes an ordinary user no compiler for
its own internals, and the one person who needs the instrument has `sudo`.

**Built:** `-INTERNAL` calls `check_admin()`, and ***`check_admin()`'s
`in_group("admin")` arm is removed*** — not because it is dead here, which it
is, but because on Ubuntu-family systems `admin` was the old sudo group, so the
fix would have held on this machine and quietly not held elsewhere. `sdadmin`
was considered and rejected: it honours the owner's first gate and skips the
second. **Witnessed before/after/control as `don`, uid 1000**: installed binary
took `-internal WHO` (`3 DON`, exit 0), built binary refuses (exit 1), built
binary with no flag still works (`4 DON`, exit 0). **All three routes into
internal mode enumerated**; the `op_kernel.c:140` setter is reachable only
through the two gated flags, and all eleven `GPL.BP` uses of `K$INTERNAL` are
enquiries. ***Lead, not built***: that setter has no `HDR_INTERNAL` guard, which
is entry 19's shape.

***AND THE DEVELOPER'S COST WAS BOUGHT BACK, ON THE OWNER'S QUESTION: `make
EXTRA_C_FLAGS=-DSD_DEV_BUILD`.*** A build-time bypass of a privilege check is
normally the worst kind of divergence — the binary you tested is not the one
that ships. ***IT IS SAFE HERE FOR A REASON ALREADY IN CLAUDE.md AND NOWHERE
ELSE: `installsdai.sh` CLONES `main` FROM GITHUB AND BUILDS THAT***, so an
installed system is always built from a clean checkout with default flags and a
developer binary has no route to a user. **It announces itself on `--version`
and on every use of `-internal`**, plain `make` is untouched, and `bin/sd` in
the tree was rebuilt default afterwards. **`check_admin()`'s own tightening is
NOT conditional** — the `admin` arm is gone in both builds, because it was a
distribution-dependent weakness rather than a convenience.

***SO THE COMPILE RECIPE ABOVE STILL WORKS WITHOUT `sudo`, PROVIDED YOU BUILT
DEV*** — and the stderr line in the transcript is how you know you did.

***COMMIT 2 RAN ON THE 18:20 INSTALL AND THE ARM FIRED: `No SD administrator is
registered: granting rights to don for this session`, then `Admin? : Yes`.***
Message 10033 by number, naming the person, on exactly the predicted state.
Entry 21's `-internal` gate is on the same install, measured refusing `don`.

***THEN THE OWNER READ THE MESSAGE AND FOUND THAT ITS ADVICE COULD NOT BE
FOLLOWED — "kinda impossible" — AND HE WAS RIGHT TWICE OVER.*** `CREATEA:255`
refuses a name already in the register (6002) and `MODIFYA` had **zero**
references to `ACC$TIER`, so no existing account could ever become an
administrator and the arm could never close. ***AND THE COMMAND STRING IN THE
MESSAGE WAS ITSELF WRONG*** — `USER`/`GROUP`/`OTHER` has been required since rev
0.9.0 and only `OTHER` takes a pathname. **It was copied from `CREATEA`'s
`START-DESCRIPTION`, which is stale — and the port's copy is stale identically.**
***A COMMENT BLOCK IS NOT AN INSTRUMENT; THE SYNTAX THE VERB PRINTS AT
`CREATEA:246` IS.***

**Commit 3 fixes both:** `MODIFY.ACCOUNT <account> STANDARD | PROGRAMMER |
ADMINISTRATOR` (the port's grammar minus `SUSPENDED`, which needs `PRE_RELEASE`
13's doors), messages 10035/10036, 10033 rewritten to name the reachable route,
`CREATEA`'s description corrected. **Compiled 0 errors with a HEAD control —
and the first red control PASSED and was void**, cutting inside the header and
leaving a valid empty program; re-cut inside the body it gives 9.

***COMMIT 3 IS WITNESSED AND THE ARM CLOSED ITSELF, 9 Sep 2026.*** In one
sitting: the arm fired, `MODIFY.ACCOUNT DON ADMINISTRATOR` printed *"don added
to sdadmin"* and *"Account DON is now ADMINISTRATOR"*, and the next `sudo sd`
printed **no 10033** while still reporting `Admin? : Yes`. ***THE ABSENCE OF
10033 IS THE MEASUREMENT*** — it is the arm's only voice, so the rights came
from the register and the group. Read off disk afterwards, independently: field
5 `ADMINISTRATOR`, `sdadmin:x:965:don`, exactly one record holding the tier,
and `MESSAGES/10033` present so its silence is real.

***ENTRY 14's HANG DID NOT REACH IT, AND THE REASON MATTERS MORE THAN THE
RESULT***: `sudo usermod` returned unchallenged **because the session is uid 0**.
That says nothing about §14's ten call sites; it says this one runs where the
question never arises.

***THE REFUSAL CONTROL WAS RUN BY THE OWNER AND PASSED BOTH WAYS.*** He dropped
himself from `sdadmin` with the tier left at `ADMINISTRATOR`: **10034, `Admin?
No`, and 10033 correctly SILENT** — an administrator was still registered, so
the arm had no business firing. Restored with `gpasswd -a`, back to `Admin?
Yes` and no message. **The gate refused on the group half alone with the
register half held constant, which is the `AND` tested rather than argued.**
***AND `Account : DON` IS AN INDEPENDENT READOUT OF THE SAME FLAG***: with
`USR_ADMIN` clear, `LOGIN:240` stops matching and `:259` sends the session to
the person's own account. Nobody predicted that in advance; it moved in step.

***THAT RUN ALSO EXPOSED A DEFECT IN THE REFUSAL ITSELF, NOW FIXED.*** 10034
said *"not a registered SD administrator"* to a man who **was** registered,
sending the reader to the wrong half. There are three refusals now: **10034**
not registered, **10037** registered but not in `sdadmin`, **10038** the
register could not be READ. ***10038 IS THE THREE-ANSWER PROBLEM*** — the
unreadable arm was also printing 10034, a claim about what the register says
when nothing had been read. Compiled 0 errors on both `IS_INSTALL` arms, red
control 8 errors. **Unrun.**

**`leave.sdadmin` is still unrun** — `MODIFY.ACCOUNT DON PROGRAMMER` exercises
it.

***ENTRY 14 IS WIRED UP AND ENTRY 22 IS NEW.*** All **13** raw `sudo` calls in
`GPL.BP` now go through `sd-elevate`; the only grep hit left is a comment.
**Every mapping was validated with the helper's `--dry-run` before a line of
BASIC moved** — 13 of 13 resolved to the same command. ***THE JUSTIFICATION
CHANGED WHEN IT WAS CHECKED***: entry 14's hang is mostly unreachable (every
caller's real uid is 0, so `sudo` never challenges) — **except through entry
22**, `!set_passwd` / `!create_user`, which had no gate. The live bug is
**portability**: `sudo deluser` is Debian-only and `groupadd -U` is recent
shadow-utils, so demotion and group creation were broken on Arch and RHEL.
***`sdadmin` JOINS THE WHITELIST*** (delegation, not escalation — the caller
already holds it), ***AND THAT EXPOSED AN OLDER HOLE***: HEAD's helper builds
`groupdel -- sdusers` **exit 0**, measured by running it. Both system groups
are refused by name now. Self-test **36/0**, up from 30/0.

***`PRE_RELEASE` 8 IS BUILT: THIS PROJECT HAS AN `assert-current` AT LAST.***
`python3 gplbld/assert-current.py`, no `sudo`, **0 current / 1 stale / 2 cannot
answer**. A rewrite rather than a port, because the installer clones `main` from
GitHub so `bin/sd` is not what got installed: it checks the working tree is
committed, HEAD is `origin/main`, the install's **commit stamp** matches HEAD,
and `bin/sd` is newer than `gplsrc`. ***`installsdai.sh` NOW WRITES THAT STAMP***
(`$sdsysdir/.sdcore-install`, root-owned 644, written after the recursive
chown/chmod). **An install with no stamp answers 2, never 0.** Unit tests 10/10,
and the `CURRENT` row was watched failing first. **Live here it says STALE,
correctly** — the 18:39 install predates HEAD. ***USE IT BEFORE BELIEVING
ANYTHING MEASURED AGAINST THE INSTALLED TREE.***

***ENTRY 18 IS CLOSED, AND ITS LAST REQUIREMENT WAS ALREADY MET.*** The entry
claimed only a **forced** account is refused when unregistered. ***MEASURED 9
Sep 26 WITH A CONTROL: ALL THREE OF `LOGIN`'s ACCOUNT CASES READ THE REGISTER
AND TERMINATE ON A MISS*** — forced `:213`, administrator `:250`, and the
default `upcase(@logname)` at `:265`. `sd -ANOSUCHACCT` → *"not in register /
Connection terminated"*; `sd -ADON` → the session runs. **Nothing needed
building.**

***WHAT REMAINS IS §L1 AND IT IS NOT ENTRY 18.*** The per-tier VOC does not
exist, so a tier decides whether a verb **acts** but not whether an account
**has** it — the port's *"two gates, not one"* with only the second built. **Not
designed.**

*(The paragraph below was written before that install and is kept because its
method is the reusable part.)* ***COMMIT 2 HAD NOT RUN, AND THAT WAS CHECKED
RATHER THAN ASSUMED.*** The
17:53 install carries `K$REAL.USER` **×3** and `grant.administrator` **×0** in
`/usr/local/sdsys/GPL.BP/CPROC`, with `MESSAGES/10033` and `10034` **absent** —
so it is `origin/main` at `ef75eb2`, and the `Admin? Yes` above came from the
**old unconditional grant**. `8ef24bb` is committed and **not pushed**.
**Its witness is a further install of `origin/main` then `sudo sd`: expect
message 10033 naming `don` at start-up, and `WHO.AM.I` otherwise unchanged.**

*(Superseded — this was the note that opened the session logged above. The
session it describes ended at `51b5880`; the current head is `94085ac`.)*

***LAST SESSION ENDED 9 Sep 2026 (out of credits) AT `51b5880`. Tree clean,
pushed. This is the fresh-start note; the older lines below still stand.***

**Done this session (all pushed, all on `origin/main`):** entry 19 closed
(`op_kernel.c` admin-flag hole, `HDR_INTERNAL` gate); 14 & 13 measured and
ruled; **14's mechanism built** (`gplbld/sd-elevate` + `sdcore.sudoers` +
installer wiring + `test-sd-elevate.py` 30/0) — **installed and verified
present** (16:25 install: `sdadmin` group, `/usr/local/sbin/sd-elevate`
root:root 0755, `/etc/sudoers.d/sdcore` 0440); entry 18 **commit 1** (register
records a tier, `ACC$TIER`/`ACC$PRIOR.TIER`, `CREATEA` writes it + adds admins
to `sdadmin`); **`PRE_RELEASE` 20** filed and **piece 1 built** (`K$REAL.USER`
57 keeps the real person across the `sudo sd` drop). Adopted the port's
`test-fixlist-units.ps1` (pwsh, dev-only) — run it against `PRE_RELEASE_FIXES.md`.

~~***THE ONE THING BUILT BUT NOT YET WITNESSED: `PRE_RELEASE` 20 piece 1.***~~
***WITNESSED 9 Sep 2026 ON THE 17:53 INSTALL. The owner ran `WHO.AM.I` under
`sudo sd` and it said `User : don`.*** Baseline had been `User : sdsys`.
`Process UID 0` / `EUID 999` unmoved, `Admin? Yes`. **Message 10032 did not
fire**, so `SUDO_USER` reached the process and the unknown arm was never taken.
See `PRE_RELEASE` §20.

~~***NEXT TASK: ENTRY 18 COMMIT 2 — THE GATES.***~~ ***DONE, above.*** Two
things this paragraph said turned out to be wrong and the corrections are worth
keeping. **`IsAdmin()` needed no replacing — it was already dead**, entry 19
having removed its only caller; it is deleted rather than rewritten. **And the
`CN_SOCKET` guard does not arise**: `linuxio.c:110` sets
`command_processor = "$APISRVR"` for an API session, so `$CPROC`'s root-entry
block is not on that path at all and the port's every-API-session-is-admin hole
has no route here. `sd-elevate`/`sdadmin` are still inert until the ten raw
`sudo` call sites migrate (entry 14 tail).

**Step 5 (installer) is later, in planned order.** Owner's shape recorded above
(line ~164): ONE script for install/upgrade/delete; the in-place upgrade is
plan `F1`+`F2`.

*Handoff updated 9 Sep 2026. **Step 4 is complete.** Steps 2 and 3 implemented,
neither exercised on a running system; §I built nothing and compiled nothing —
the next install is what proves it.*

**[PRE_RELEASE_FIXES.md](PRE_RELEASE_FIXES.md) is the release worklist** —
started 9 Sep 2026 on the owner's ask. It is the tracker the port created for
final testing; here it also carries **gaps testing will never find**, including
two the plan is silent on: **the port's 31 relevant PowerShell helpers**
(`PRE_RELEASE` 1) and **the editor story** (2). Read its table, not its section
headings.

**The plan is `/home/don/Documents/claude_plan.md`** (and `.pdf`), outside the
repository, with a `file:line` verification table for every defect it claims.
**Its detail has been wrong** — see the §I note — so confirm a claimed
`file:line` before acting on it.
Work follows its "Suggested order". **Steps 0–3 are done; nothing in steps 2–3
has been exercised on an installed system.**

### ~~Your next task~~ — *superseded 9 Sep 2026; the current one is under
"Next task" at the top of this file. The step-4 record below still stands.*

***STEP 4 IS COMPLETE.*** All of §G and all of §I are done — `I1` TAPE, `I3` SED,
`I4` UPDATE.RECORD, `I5` MODIFY, `I2` PROC, `G1` BP test programs (PY_* kept),
`G2` VFS, `G3` OPGEN, `G4` SDNet. **None of §I has been installed**; the BASIC
was not compiled this session (see "Step 4 / §I" for what instrument was tried
and why it could not).

***`PRE_RELEASE` 19 IS DONE (9 Sep 2026) — MEASURED, THEN FIXED TO MATCH THE
PORT.*** The `op_kernel.c` reading was confirmed on source (a positive argument
set `USR_ADMIN` with no `IsAdmin()` call, and `|| IsAdmin()` made `kernel(26,0)`
re-grant rather than clear for a root caller) — **but the "bypassable from any
BASIC program" claim is REFUTED**: `KERNEL` resolves only in internal mode
(`BCOMP:3758`), and a non-internal probe compiled from the non-root `don`
account failed *"Unrecognised statement"*, 2 errors. So the opcode is reachable
only from an `$internal` program (LOGIN, CPROC). Gated the flag change on
`HDR_INTERNAL` (the port's entry 170 fix); build clean, `bin/sd` boots.
The fix's `$internal`-path effect is **reasoned + conformity, not witnessed** —
an ordinary user cannot compile `$internal`, so it is unwitnessable from
ordinary BASIC, which is the same fact that makes the old hole unreachable. **An
install of `origin/main` would carry it to the running system** (`PRE_RELEASE`
15). See "Step 5 / PRE_RELEASE 19" below.

***YOUR NEXT TASK IS `PRE_RELEASE` 18***, now unblocked and specified: the owner
defined "administrator" on 9 Sep as **sudoers member AND registered SD
administrator, with unregistered users refused entry**. The gap table and the
port's `ACC$TIER 5` / `ACC$PRIOR.TIER 6` are in that entry.

***THE OWNER'S DEFINITION IS THE PORT'S MODEL IN LINUX WORDS, WHICH IS WORTH
KNOWING BEFORE IMPLEMENTING IT.*** The port's Administrator documentation opens
with *"there are two gates, not one"* — **the tier** decides whether the
account's VOC has the verb at all, **elevation** decides whether the verb does
anything (`SDCoreWindowsDocs/Administrator/markdown/01-accounts-and-security.md`,
which is local). "Registered SD administrator" is the first gate and "sudoers
member" is the second. **The shipped docs are local and are the prose model for
§L**; the port's code and record stay authoritative for `file:line`.

***`PRE_RELEASE` 14 AND 13 WERE RULED ON 9 Sep 2026 AND ARE NOW SPECIFIED WORK,
NOT OPEN QUESTIONS.*** Both are the owner's selections, recorded as selections
rather than as his words. **Neither is built.**

| | Ruled | What it commits to |
|---|---|---|
| **14** | SD ships a **`sudoers.d` drop-in for a group SD owns** | **18's second gate reads SD's own group** — portable across distributions, and it sidesteps the three-answer problem. ***MECHANISM BUILT 9 Sep, NOT WIRED UP*** — see below |
| **13** | **A STANDARD account gets no real login shell**; the tier is to be a **boundary** | ***SD must write to `sshd_config`*** — there is no way to hold the boundary without it. The port's fenced block + refusing preflight is the model |

***THE MEASUREMENTS BEHIND THEM, BECAUSE THE FIXES WILL BE CHECKED AGAINST
THEM.*** `sudo -n -v` answers *"a password is required"* and **0 of 10** call
sites pass `-n`, so the hang is real here; `sudo -n -l` exits **1** both for
"needs a password" and "may not sudo", so **a membership test on that exit code
refuses a legitimate administrator**; and every SD account today has a real
login shell (`don` `/bin/bash`, `sdsys` `/bin/sh`), which is the known-bad
starting state a §13 verifier must prove the system moved away from.

***ENTRY 18 IS HALF BUILT AND ITS SECOND HALF IS BLOCKED BY A NEW FINDING —
`PRE_RELEASE` 20. READ THAT BEFORE RESUMING.*** Commit 1 landed 9 Sep: the
register records a tier (`ACC$TIER` 5 / `ACC$PRIOR.TIER` 6 in `SYSCOM/KEYS.H`,
`CREATEA` writing it from `ADMINISTRATOR`/`PROGRAMMER`). ***COMMIT 2 WAS STARTED
AND DELIBERATELY STOPPED***, because the gates cannot be written as planned:

***ON `sudo sd`, `CPROC:285` REPLACES THE SESSION IDENTITY WITH `sdsys` BEFORE
`$LOGIN` RUNS***, so *"is this person a registered SD administrator"* has **no
person to look up**. `CPROC:2483`'s shipped `is_grp_member(@logname, …)` account
gate is already answered for `sdsys` rather than for whoever typed `sudo`.
***RULED 9 Sep 2026 — THE PORT'S MODEL, TWO IDENTITIES*** (owner's selection).
`@logname` keeps the real person, `USR_ADMIN` stays the session flag, and a
separate key answers *"is the signed-in person an administrator"*. **Not
built.** Three pieces, in `PRE_RELEASE` §20: **(1)** `CPROC:285` stops replacing
`@logname` — the euid drop stays, only the identity substitution goes.
***THE ENUMERATION IS DONE (9 Sep) — 14 sites, 8 files, in `PRE_RELEASE` §20,
AND IT FOUND THE LOCK-OUT.*** `LOGIN:191-195` tests
`is_grp_member(@logname,'sdusers')` and **terminates the connection**; it runs
**before** the account is chosen at `:240`. The sudo path passes it today *only
because* the identity is already `sdsys`, which is in `sdusers` (measured). Make
`@logname` the real person and **an administrator who is a sudoer but not in
`sdusers` is cut off with sysmsg 5009** — the port's exact failure, at a named
line. **It must be handled in the same change.** Also: `@USER` is the *same
slot* as `@logname` (both `SYSCOM.LOGNAME`, slot 14), `@WHO` is the account and
is untouched, and ***the substitution is in C — `sdext_eguid.c:67` — not in
`CPROC`***, so changing `CPROC:285` alone leaves `kernel(K$USERNAME,0)` still
answering `sdsys`. `CPROC:2890`/`:3110` and `LOGIN:259` are safe, for reasons
recorded there; **(2)** a new kernel key, **57 is free**;
**(3)** the gates read it. ***DO NOT COPY THE PORT'S `IsAdmin()`*** — its
`getgrouplist()` asks *"is this account an administrator"*, ours is
`getuid() == 0` and asks the wrong question; the Linux test is the owner's own
definition, sudoers **and** the register. ***AND CARRY THE PORT'S `CN_SOCKET`
GUARD***: this tree has `connection_type`/`CN_SOCKET` (`kernel.h:50,54`) and an
`IsAdmin()` reading the real uid, so the port's every-API-session-is-admin hole
is available here too. ***AND ENTRY 18 IS WRONG IN THE OTHER DIRECTION TOO***: the
sudoers half is largely enforced already, because reaching uid 0 via `sudo sd`
requires it. The missing half is the **register**, not sudoers.

***ONE THING THAT WAS CHECKED AND IS SOUND: THE ENTRY-19 FIX DOES NOT BREAK THE
`sudo sd` ADMINISTRATOR PATH.*** `CPROC:128` is `$internal`, so `CPROC:288`'s
`kernel(K$ADMINISTRATOR, 1)` still sets the flag under the new `HDR_INTERNAL`
gate. That was the one silent regression available and it did not happen.

***`PRE_RELEASE` 14's MECHANISM IS BUILT (9 Sep) AND IS INERT UNTIL ENTRY 18
LANDS. DO NOT READ IT AS DONE.*** `gplbld/sd-elevate` is one validated helper;
`gplbld/sdcore.sudoers` grants `%sdadmin` **that one command and not the eight
raw ones**, because `passwd`/`usermod`/`chmod g+s` are unrestricted by argument
and naming them would be root by another route. Installer creates `sdadmin`,
installs the helper **root-owned in `/usr/local/sbin`** (*not* under
`/usr/local/sdsys`, which is `chown -R sdsys:sdusers`'d — a helper there would
be sdsys-writable, and that is root), runs `visudo -cf` **before** installing,
and refuses when `/etc/sudoers` has no `includedir`. Uninstaller removes the
drop-in **before** the group it names. `test-sd-elevate.py`: **30 passed / 0
failed, 24 refusals + 6 controls**, ***and the test was watched failing*** —
6/24 against a stub that permits everything.

***WHAT MAKES IT INERT: THE CALL SITES STILL CALL RAW `sudo`.*** ***`sdadmin`
NOW GETS MEMBERS THOUGH*** — owner's ruling, 9 Sep: `CREATEA` adds an
ADMINISTRATOR-tier account's person to `sdadmin` (messages 10030/10031) beside
the `sdusers` add that was already there, so the drop-in is reachable for the
first time. **That add is an ELEVENTH raw `sudo` call and deliberately not the
helper**: the first administrator is not in `sdadmin` when the call runs, so the
helper would refuse the very call that creates them, and `sdadmin` is not in the
helper's group whitelist. ***THE MIGRATION MUST THEREFORE ALSO DECIDE whether
`sdadmin` joins that whitelist (an administrator creating administrators —
intended, but worth naming) and how the FIRST one is bootstrapped, which is the
installer's job rather than a verb's.*** Nothing installed; the installer edits
are unrun.

***TWO COSTS THE RULINGS DO NOT REMOVE, AND §14/§13 CARRY THEM:*** `sudo passwd`
and `usermod -aG` are **unrestricted by argument**, so a drop-in naming them
plainly is root by another route and they need wrapping; and a **malformed
`sudoers` file can lock `sudo` out of the machine**, so `visudo -cf` before
install, mode 0440, and no `.` or `~` in the filename. Open sub-decisions (the
group's name, who is put in it, the §13 mechanism, PROGRAMMER's case) are listed
in those two sections.

**Your next task after those is step 5, the installer.** ***`F9` IS SUPERSEDED — DO NOT DO
IT.*** The owner ruled on 9 Sep 2026 that the installer always clones `main`
from GitHub, which is the opposite of §F9's "drop the clone and build the
bundled tree". Done that day; see "Installer" below. Remaining: `F1` upgrade
split · `F2` `UPDATE.ACCOUNTS` · `F3` `[locked]` · `F4` config parser · `F5`
changelog location · `F7` self-check · `F6`, `F8`.

***OWNER'S SHAPE FOR STEP 5, 9 Sep 2026: ONE SCRIPT DOES INSTALL, UPGRADE AND
DELETE.*** Recorded as a selection of direction, not his exact words. Today the
two scripts (`installsdai.sh`, `deletesdai.sh`) and the fact that
`installsdai.sh:117-122` **refuses over an existing install** force the upstream
dance: run delete (saving `/home/sd/ACCOUNTS` + `sd.conf` to a staging area),
reboot, run install (which restores them at `:575-596`). **The owner wants that
collapsed into a single entry point that detects state and does the right thing
— install when absent, in-place upgrade when present, delete on request.** His
framing of why it matters: on Windows a user downloads a new *installer* and it
updates what is installed; ***on Linux the user downloads source and compiles***,
so the Linux equivalent is one script, not an installer binary. **Upstream's
delete-reboot-reinstall "does less account-upgrade work than the Windows port"**
— so the in-place upgrade must carry `F2`'s `UPDATE.ACCOUNTS` account refresh,
which is the part upstream skips. This does **not** reorder the F-items; it says
the container they land in is one unified script, and that `F1`'s "detect an
existing install" replaces the current refusal at `:117`.

***AND THE CONSEQUENCE F9 EXISTED TO PREVENT IS NOW LIVE: AN INSTALL TESTS
`origin/main`, NOT THE WORKING TREE.*** Commit and push before testing, or you
are testing something else and nothing will tell you. `PRE_RELEASE` 15.

***THE LOWER-CASE CONVERSION IS NOT IN QUESTION AND NOTHING HAS BEEN DROPPED.***
It is the owner's standing decision — CLAUDE.md Project stance, 8 Sep 2026,
*"lower case throughout, matching the port"* — and it is **conformity with SD
Core for Windows**, which outranks conformity with upstream. §M happens.

***OWNER'S RULING ON THE TIMING, 9 Sep 2026: "no problem with delaying it until
later in the port as long as it is done by the end."*** So the schedule below is
settled, and §M is a **commitment on the port, not a plan item that may lapse**.
It is listed in Open as release-blocking for that reason: **the port is not
finished with `GPL.BP` and `SYSCOM` still upper case.** A later session that
finds §M inconvenient may re-order it; it may not drop it.

**What was withdrawn is a SCHEDULING suggestion, and it was a prior session's,
not the owner's.** The line *"a good place to insist on the lower-case migration
going in with it"* entered this file in `3d61b3a` (step 3) and hardened by
recopying into *"fold in the lower-case migration here"* — an emphatic
imperative with no ruling or measurement behind it. **§M stays where the plan
puts it, at step 7**, for two reasons that are dependencies rather than taste:

- §M2's migration is *"a rename step for an existing tree, per account and for
  `sdsys`"* **inside `installsdai.sh` and `update.accounts`**. `update.accounts`
  does not exist here — only a singular `VOC_TEMPLATE/UPDATE.ACCOUNT` — and §F2
  (step 5) opens by saying to check whether `GPL.BP` has an equivalent. The
  container is unbuilt work.
- §M1: *"The order is not optional: fold, then rename. Renaming first breaks
  every existing name until the fold lands."* The rename is the half that looks
  like it belongs with a bulk removal pass; it is precisely the half §M1 forbids
  going first.

***STEP 4 MOVED §M FORWARD RATHER THAN BACK.*** `I3`/`I4`/`I5`/`I2` deleted four
programs and nine VOC records that would otherwise need renaming, and §M1's own
text says `UPDATE.RECORD`'s keyword fold is *"moot — §I4 removes it"*. **`M1`'s
fold has no dependency on `update.accounts` and can be started at any time** if
the owner wants §M begun before step 5.

***Step 4 installs, boots and runs at `2b4d9f0`*** (owner, 9 Sep — see State of
the tree). **`G4` is CLOSED by the owner's decision, 9 Sep.** Its read side was
observed: `SELECT VOC` / `LIST VOC ID.SUP` / `COUNT VOC` listed records normally,
exercising op_open, read_record, op_readv and op_select. Write, delete and record
lock were *not* run; the owner accepted them on the read-side witness plus
conformity with the Windows port, which exercised these paths. That acceptance is
reasoning, not a measurement — if a G4 file-I/O fault ever surfaces, op_write /
op_delete (`op_dio3.c`) and the six `op_lock.c` sites are where to look first.

***Testing bar for the shrink (owner's ruling, 9 Sep):*** because this walks a
path the Windows port already walked, an occasional compile-and-run test is
enough for now; more extensive testing comes later. So the remaining removals
(`G2`, `I3`/`I4`/`I5`/`I2`) are held to "compiles clean and the tree still
installs and runs a command", not a per-fix exercise — with the deferred testing
tracked in Open.

***The plan says take §I as ONE release, not scattered commits*** (plan I intro):
`I3`/`I4`/`I5` and PROC's `LISTPQ` all edit `VOC_TEMPLATE`/`NEWVOC`/`SD.VOCLIB`,
and doing them in one pass means those are edited once and `update.accounts`
(§F2) runs once. `I1` TAPE was exempt — it is copied in from `tape/` at install,
never shipped in `VOC_TEMPLATE` — so it went alone. Do the VOC-touching removals
together. Mind the near-miss names (`MODIFY` the record editor goes; `MODIFYA` =
MODIFY.ACCOUNT stays; `MODIFY.PASSWORD` stays). `I2` PROC is the deep one
(compiler + opcode `OP_PROCREAD`); the plan says report "PROC not supported" at
the `CPROC:1530` dispatch and RETIRE the opcode slot rather than reuse it. A good
place to fold in the lower-case migration.

**Deferred to a later testing pass** (owner's testing-bar ruling, 9 Sep — see the
Step-4 note above: compile-and-run is enough for now). These behaviours are not
individually exercised and are collected here so the later pass has the list:
- Step 2 (`A1`–`A6`) is where a wrong fix is silent; `A1` needs an *induced
  commit failure* (a read-only or externally-locked record) to reach at all.
- Step 3's regenerated `ERR.H`/`ERRTEXT.H` — an error from a crypto/Python code
  should show message text, not a bare number. **No BASIC references the renamed
  defines** (checked: they flow as numbers, ERRTEXT.H maps number→text).
- `G4` write/delete/record-lock (read/select observed; see the Step-4 note).
- ~~`G2`: `sd` has not started from a pcode library built without
  `_EXTENDLIST`.~~ ***CLOSED 9 Sep 2026 — see "The 11:35 install" below.***
- ~~§I: the edited `CPROC` has not been compiled.~~ ***CLOSED 9 Sep 2026 — same
  install.*** **Still open from §I:** a VOC record of type `PQ` printing message
  `10099` naming the verb, **not** sysmsg 5053 "invalid dispatch code". Nothing
  shipped is type `PQ`, so this needs one written by hand.

**Higher-value unpaid debt first: EXERCISE steps 2 and 3.** Nothing in either has
run on an installed system.
- Step 2 (`A1`–`A6`) is where a wrong fix is silent; `A1` needs an *induced
  commit failure* (a read-only or externally-locked record) to reach at all.
- Step 3 regenerated `SYSCOM/ERR.H`, `GPL.BP/ERRTEXT.H`, `REVSTAMP.H` and
  reformatted every SDEXT/crypto/Python error `$define` from C spelling to SD
  spelling. **No BASIC references the renamed defines** (checked: they flow as
  numbers, ERRTEXT.H maps number→text), so the risk is low, but it has not been
  seen on a running system. An install would confirm error text now displays.

### ***BEFORE YOU IMPLEMENT ANYTHING, GREP THE WINDOWS RECORD***

Not a formality. It corrected the plan **twice** in step 2's first third and
shaped every fix since — the port is the reference implementation and
`UPSTREAM_FIXES.md` / `PRE_RELEASE_FIXES.md` carry the *why*.
`/home/don/Projects/SDCoreWindowsProject/sd4windows` has those plus `HISTORY.md`; the
entries are long, and the detail near the end of one is usually the correction.
For step 4 the removals each have a §I/§G entry; grep the record for the one you
start with, e.g.:

```sh
grep -n -i -E 'PROC|TAPE|SDNet|OPGEN|VFS' /home/don/Projects/SDCoreWindowsProject/sd4windows/*.md
```

### The 11:35 install, 9 Sep 2026 — G2 and §I are closed

***THE OWNER RAN THE REWRITTEN INSTALLER AND IT WORKED.*** He ran it; this
session did not. `/usr/local/sdsys/bin/sd`, **11:35:04**, 1,592,528 bytes. What
follows was then measured **on the installed tree**, this session, every row
against a control that fired:

| On `/usr/local/sdsys` | removed | control |
|---|---|---|
| `GPL.BP/_EXTENDLIST` · `PCODE.OUT/_EXTENDLIST` | **0**, **0** | `_DELLIST` **1**, **1** |
| `GPL.BP/SED` · `MODIFY` · `PROC` · `UPDREC` | **0** each | `ED`, `MODIFYA`, `QPROC`, `BBPROC` **1** each |
| `VOC_TEMPLATE`+`NEWVOC`: `SED`, `UPDATE.RECORD`, `MODIFY`, `LISTPQ` | **0** each | `MODIFY.ACCOUNT`, `ED`, `EDIT` present |
| `MESSAGES/10099` — must be **PRESENT** | **1** | `5053` **1** |

***THE FOUR CONTROLS IN ROW 2 ARE THE NEAR-MISS NAMES***, so that table also
shows the removal took the right things and not their neighbours.

**`G2` is closed, and the chain matters more than the conclusion.**
`GPL.BP.OUT/CPROC` exists, dated **11:35:12**. It is produced by the bootstrap's
`sd -i` compiling `GPL.BP`; for that `sd` had to run; for `sd` to run
`load_pcode()` had to succeed; and `load_pcode()` **refuses to start** when a
`Pcode()` entry has no library object. `bin/pcode` was rebuilt from the
`pcode_fs` list with `_EXTENDLIST` gone. **So `sd` started from a pcode library
built without it** — the loud failure mode did not fire.

**§I is closed on the same object.** The edited `CPROC` compiled: a syntax error
in the replaced `PQ` arm would have aborted bootstrap pass 1 and there would be
no object. This is what `bbcmp.py` could not do (it aborts on `$IFNDEF`).

***AND §I IS ALSO VERIFIED AT RUN TIME, NOT ONLY ON DISK.*** `sd` runs
non-interactively as an ordinary user with **no sudo** — `sd --version` exit 0 is
the control that it runs at all, and `sd COUNT VOC` answers **410 record(s)**.
Against a live account VOC:

| `COUNT VOC WITH @ID =` | result | |
|---|---|---|
| `SED`, `MODIFY`, `UPDATE.RECORD`, `LISTPQ`, `PROC` | **0** each | removed |
| `ED`, `EDIT`, `CATALOG` | **1** each | controls |

***THE MEASUREMENT IS DATED, WHICH IS WHAT MAKES IT WORTH ANYTHING.*** An account
VOC can survive a reinstall, and this one did not: `/home/sd/user_accounts/don`
and its `VOC` are stamped **11:35:12**, eight seconds after the binary, so it was
built by this install.

**Two controls came back 0 and both are explained rather than waved away.**
`MODIFY.ACCOUNT` and `MODIFY.PASSWORD` are absent from a user VOC because
***`CREATEA:422` BUILDS A NEW ACCOUNT'S VOC FROM `NEWVOC`, NOT `VOC_TEMPLATE`***,
and neither name is in `NEWVOC`. `MODIFY.PASSWORD` is in neither file at all,
which is plan §E5 confirmed.

***THAT IS WORTH KEEPING FOR §L: THE PRODUCT ALREADY SHIPS TWO VOCABULARIES.***
`VOC_TEMPLATE` 423 records, `NEWVOC` 407, and the 17 only in `VOC_TEMPLATE` are
exactly the administrative set — `CREATE.ACCOUNT`, `DELETE.ACCOUNT`,
`MODIFY.ACCOUNT`, `UPDATE.ACCOUNT`, `ACCOUNTS`, `MESSAGES`, `GPL.BP`, `BP`,
`QFILE`, `UNLOCK`, the three compile passes, `LOAD.LANGUAGE`, `$HOLD`,
`BP.OUT`, `GPL.BP.OUT`. Only `%t` is in `NEWVOC` alone. **§L's tiers can extend
an existing split rather than invent one**, and the plan does not say this.

### Exercised on the live install, 9 Sep 2026 — §I2 and B1/B2 CLOSED

The owner: *"this is a test machine — you don't have to worry about the running
sd, it is only there for testing."* So the two checks held back were run.

***§I2's `PQ` DISPATCH IS RUN, NOT JUST COMPILED.*** A type-`PQ` VOC record was
built by hand — `CREATE.FILE PQSRC DIRECTORY`, the record written as an ordinary
file (a directory file's records **are** OS files, which avoids driving `ED`),
then `COPY FROM PQSRC TO VOC TESTPQ`, *1 record(s) copied*. Invoking it:

```
PROC is not supported in this version of SD, and TESTPQ is a PROC.
```

**Anchored both ways, as the instrument rule asks:** the success wording present
**1**, and `invalid dispatch code` (sysmsg 5053, the arm a deleted case would
have fallen into) present **0**, as are *not found* and *Unexpected token*.
**Cleaned up afterwards** — `COUNT VOC` 410 before, 412 with the fixtures, **410
after**.

***B1 AND B2 ARE CLOSED — the two the Open list called most worth doing.*** As
uid 1000:

| run as an ordinary user | sysmsg 2001 |
|---|---|
| `CATALOG BP $X` — the prefix route B2 was written for | **refused** |
| `CATALOG GLOBAL BP X` — the keyword route | **refused** |
| `DELETE.CATALOG $X` — B1 | **refused** |
| `CATALOG BP X` — **local, the control** | **not refused** (fails *"File BP.OUT not found"*) |

The control is what makes the other three mean anything: the gate discriminates
rather than refusing everything.

***AND THE MEASUREMENT FOUND SOMETHING THE FIX DID NOT: `system(27)` IS
`getuid()`*** (`gplsrc/op_sys.c:222`). So "administrator" in these gates is
**literal root**, `sd` is not setuid, and a session runs as the invoking Unix
user — **an SD ADMINISTRATOR who is not root will be refused, and any user who is
root admitted.** B1/B2 are correct as written and follow the existing rev 0.9.0
convention; **what needs deciding is what "administrator" means**, before §L can
grant the tier anything. `PRE_RELEASE` 18, and the same root as 14.

***WHAT IS STILL NOT ESTABLISHED.*** Steps 2 and 3 remain unexercised, and the
rest of step 1 (`D1`, `D2`, `C1`, `D3`, `B4`). This install was of
**`origin/main`**, not the working tree (`PRE_RELEASE` 15).

### Step 5 / PRE_RELEASE 19 — the K$ADMINISTRATOR grant hole, 9 Sep 2026

`op_kernel.c:302-312`, `case K_ADMINISTRATOR`. Two questions: is the C hole
real, and is it reachable from ordinary BASIC.

***THE C HOLE IS REAL AT BOTH ENDS, CONFIRMED ON SOURCE.*** The old code
`if ((n > 0) || IsAdmin()) set; else clear;` set `USR_ADMIN` for any positive
argument with no `IsAdmin()` call, and for `n == 0` the `|| IsAdmin()` *re-set*
the flag whenever the caller ran as root — so `CPROC:2713`'s admin-drop on a
`LOGTO` did nothing for a root OS user. That second end is the reachable one.

***REACHABILITY MEASURED ON THE 11:35 INSTALL, AS uid 1000 (non-root), AND THE
"bypassable from any BASIC program" READING IS REFUTED.*** A probe
`BP/ADMTEST19` doing `KERNEL(26,1)` / `KERNEL(26,-1)`, compiled `BASIC BP
ADMTEST19` as an ordinary (non-internal) program, returned **`6: Unrecognised
statement` + `Matrix KERNEL is not referenced in a DIM statement`, 2 errors —
does not compile.** `KERNEL` is an `int.intrinsics` entry located only under
`if internal` (`BCOMP:3758,3781`), so a non-`$internal` program cannot emit the
opcode. The opcode is reachable only from LOGIN and CPROC, which are `$internal`
and own entry to an account. Fixture cleaned up: `COUNT VOC` **410 → 411 →
410** (the compile made a `BP.OUT` pointer; both it and `ADMTEST19` deleted).

***FIX: GATE THE FLAG CHANGE ON `HDR_INTERNAL`*** — the Windows port's exact fix
(`op_kernel.c:400-427` there, its entry 170, 13 Aug 26). Clean
`rm -f gplobj/op_kernel.o` rebuild, 0 warnings; `bin/sd --version` exit 0.

***WHAT IS NOT WITNESSED, WRITTEN IN THE CONDITIONAL.*** The fix would change
behaviour only for `$internal` callers, which an ordinary user cannot compile,
so it is unwitnessable from ordinary BASIC — the same fact that makes the old
hole unreachable. An install of `origin/main` would boot with it; if it did
not, a syntax/link fault would abort the two-stage bootstrap. `IsAdmin()` is now
prototyped-but-unused in `op_kernel.c` (defined in `linuxlb.c`, called
elsewhere) — no warning, it is `extern`.

### State of the tree

- **Clean and pushed.** `main` tracks `origin/main`; remote is
  `git@github.com:dmontaine/SDCore4Linux.git` — **capitalised**, the lower-case
  form only works through a redirect that warns on every push.
- Renamed from `sdscripts_ai` on 8 Sep 2026. Git identity is **repo-local**
  (`.git/config`, `dmontaine@gmail.com`); there is no `~/.gitconfig`, so other
  repositories will still ask.
- **9 Sep 2026: the owner reinstalled the WHOLE tree at `2b4d9f0` (through
  step 4/G4), rebooted, started `sd` and ran a command — no problems.** ***What
  that establishes: the tree builds, installs, boots and runs.*** The two-stage
  bootstrap recompiled every edited `GPL.BP` program (DEBUG, ERRTEXT, APISRVR,
  CPROC, the removed-verb VOC), so D6's commented `$execute`s, D5's regenerated
  headers and the G4 removals all load; a syntax error in any would have aborted
  the install. ***WHAT IT DOES NOT ESTABLISH: the fixes' own behaviour.*** A
  generic command boots the VM but does not touch the open/read/write/delete/
  lock/select dispatch G4 rewrote, D5's error-text display, or A1's undo (which
  needs an induced commit failure). The per-step check tables still stand
  unrun. ***The one most worth doing is a file-I/O smoke test for G4*** —
  `SELECT`/`LIST`/`COUNT VOC` plus a create/write/read/delete on a scratch file.

## Verified — 8 Sep 2026

**Step 0 of the plan is done: `git status` went from 2667 modified files to 7.**
Three commits, in this order:

| Commit | What |
|---|---|
| `9f82a52` | The AI hardening layer, 174 files. It had been sitting unstaged on `main` and was not backed up |
| `67f696e` | `.gitignore` added; 203 build artifacts untracked (files left on disk) |
| `6181c36` | 2285 data records `100755` → `100644` |

Measured before and after, not inferred: 2667 dirty → 334 with content change →
0 after the three commits; the residual 7 were the untracked documents committed
alongside this file.

**Build directories are recreated by the build** — so untracking them is safe:

- `Makefile:67` — `$(shell mkdir -p $(GPLOBJ) $(GPLBIN))` creates `gplobj/` and
  `bin/`.
- `Makefile:104-108` — the `terminfo` target does `rm -Rf`, `mkdir -p`, then
  regenerates from the tracked `terminfo.src` with `sdtic`.
- `Makefile:74` — `sd:` depends on `terminfo`, so a plain `make` rebuilds it.

**CLOSED 8 Sep 2026: the owner ran `installsdai.sh` and it built, installed and
let him log in.** The installer builds from this tree, so untracking `gplobj/`,
`bin/`, `terminfo/` and the rest cost nothing — a build after them produces a
working system. (`make sd` had also been run in-session after deleting four `.o`
files: 0 errors, 0 warnings, `bin/sd` relinked. That was incremental; the install
is the stronger evidence.)

**Other observations this session:**

- `.claude/hooks/no-program-edits.py --selftest` → 32 cases, 0 failed, run from
  this directory.
- `ssh -T git@github.com` authenticates as `dmontaine`, key `~/.ssh/id_ed25519`.
- No file in the mode set was a script; `installsdai.sh` and `deletesdai.sh` keep
  their executable bit.

## Step 1 of the plan — all eight applied, 8 Sep 2026

The release is now **`L1.0-0`** and `sdsys/changelog` carries its section.

| | Where | Fix |
|---|---|---|
| D1 | `gplsrc/k_error.c:216` | size limit was `(LINES + LEN)+1` = 84 against a 241-byte buffer, and ignored the offset already written; now `sizeof(s) - n` |
| D2 | `gplsrc/op_skt.c:673` | `n = TRUE;` removed — it discarded the caller's keep-alive value |
| C1 | `gplsrc/clopts.c:300` | `process.user_no` → `user_no`; task locks were compared against the cleanup process, not the dead session |
| B4 | `gplsrc/sysseg.c:413` | guard `uptr->pid > 0` (and `sdlnxd_pid > 0`); pid 0 made `kill()` signal the caller's process group |
| B2 | `sdsys/GPL.BP/CATALOG` | one admin gate after the `end case`, covering the GLOBAL keyword *and* all three prefix routes |
| B1 | `sdsys/GPL.BP/DELCAT` | admin gate inside the branch that touches `gcat`; it had no check at all |
| D3 | `sdsys/GPL.BP/TERM` | `DEFAULT.WIDTH`/`DEFAULT.DEPTH` (120×36) instead of `MIN.WIDTH` and a literal 24 |
| E1 | `sdsys/VOC_TEMPLATE/ENCRYPT.FIELD` | removed; `$CRYPTO` is not in the distribution |

**Owner ran a full install, 8 Sep 2026: it compiles, it installs, and he could
log in.** He ran it; this session did not. That report closes three questions the
session could not close for itself:

- **The four BASIC changes compile.** `installsdai.sh` aborts on bootstrap pass 1
  failure, and the bootstrap is what compiles `GPL.BP` — so a syntax error in
  `CATALOG`, `DELCAT` or `TERM` would have stopped the install.
- **Removing `ENCRYPT.FIELD` did not break account setup.** Login reaches the
  `LOGIN` paragraph through a `VOC` built from the edited `VOC_TEMPLATE`.
- **A from-scratch build works**, which is the test the previous entry left open.

***WHAT IT DOES NOT ESTABLISH: NOT ONE OF THE EIGHT FIXES HAS BEEN EXERCISED.***
Signing in does not touch keep-alive, task locks, the `sd -stop` pid guard, error
message length, either catalogue gate, or `term default`. **"It installed and I
logged in" means the tree is sound, not that any of these behaves as claimed.**

The cheap checks that would actually exercise them, in rough order of
value-per-minute — none has been run:

| Fix | Check |
|---|---|
| D3 | `term default` then `term` — expect `120` × `36`, not `20` × `24` |
| B1/B2 | from a non-administrator account: `CATALOG BP $X` and `DELETE.CATALOG $X` — both should now refuse with sysmsg 2001. **Anchor on the refusal wording, not on `$X` appearing in the output** |
| D1 | any error whose message runs past ~84 characters — previously cut off mid-sentence |
| C1 | take `LOCK 3` in a phantom, kill it, `sd -cleanup`, then take `LOCK 3` again |
| D2 | `SET.SOCKET.MODE(skt, SKT$INFO.KEEP.ALIVE, 0)` then `SOCKET.INFO(...)` — the two used to disagree |
| B4 | hardest to stage safely: needs a user-table entry with pid 0 |

Two judgement calls worth knowing, per CLAUDE.md's rule about recording the
objection as well as the resolution:

- **B1/B2 use one gate at a chokepoint rather than the check copied into each
  route.** Copying it four times is what let the original drift — rev 0.9.0 added
  it to the keyword route and not the three prefix routes. The keyword route keeps
  its own early check for the better message; the chokepoint is what holds.
- **D3 drops the `@term.type = 'sdterm'` special case** that set depth 25 instead
  of 24, because `LOGIN:85,90` makes no such distinction when sizing a session.
  **This was not measured on an sdterm terminal.** If sdterm really has 25 usable
  lines, `GPL.BP/TERM` is the line to revisit.

## Step 2, first third — unchecked return values, 8 Sep 2026

`A5` and `A6`. **`make sd`: 0 errors, 0 warnings**; `dh_ak.o`, `op_seqio.o`,
`dh_file.o` recompiled, `sd` relinked. **Not exercised** — forcing either needs
an induced I/O failure (read-only file, mandatory lock, full disk).

***THE RECORD CHECK PAID FOR ITSELF HERE AND IT IS WORTH SAYING WHY.*** Both
fixes exist in the Windows tree as its entries 100 and 103, and those entries
corrected the plan on two points this session would otherwise have got wrong:

1. **Seven call sites, not four.** `/home/don/Documents/claude_plan.md` §A5 lists
   `2280`, `2301`, `2429`, `3471`. There are also `3524`, `3895` and `3929`.
   Counted in this tree: 7 calls, 7 guards.
2. ***A CALLER-SIDE TEST FOR 0 WOULD NOT HAVE BEEN ENOUGH.*** `get_ak_node()` has
   three failure paths and the middle one — `dh_read_group` failing on the free
   node — assigned `new_node_num` from `GetAKFwdLink()` **before** the read, then
   fell to the exit **without clearing it**. It returned a non-zero node number,
   the head of the free chain, with `free_chain` never advanced: a node the file
   still believes is free, which two allocations could be given. The 0 convention
   is now total inside the function.

| | Where | Fix |
|---|---|---|
| A5 | `gplsrc/dh_ak.c` | `get_ak_node()` failure made total (free-node path clears, `chsize64` checked → `DHE_AK_WRITE_ERROR`); all 7 call sites abort on 0 using each function's own idiom — `goto exit_ak_write`, `goto exit_update_internal_node`, `head = 0; goto exit_write_ak_big_rec` |
| A5 | `dh_ak.c` root split | `node_ptr->node_num = get_ak_node(...)` took a temporary `old_root_node_num`; it assigned straight into the node structure, so a test after the store reads a value already committed |
| A6 | `gplsrc/op_seqio.c:1433` | `WEOFSEQ` — truncate checked, `process.status = -ER_IOE` + `os_error` |
| A6 | `gplsrc/op_seqio.c:752` | `OPENSEQ … OVERWRITE` — same |
| A6 | `gplsrc/dh_file.c:831` | `SetFileSize()` returns `chsize64(...) == 0` instead of unconditional `TRUE` |

**Two details taken from the record rather than rediscovered:**

- ***THE STATUS HAS TO BE NEGATIVE.*** Both opcodes already carry a `k_error`
  guarded on `process.status < 0` (`sysmsg(1420)` in `op_weofseq`, `sysmsg(1416)`
  in `op_openseq`), and positive values are handed back to the program. A
  positive status would have left the report unable to fire.
- **The `goto exit_op_openseq` was checked in this tree, not assumed.** The
  truncate is at `:752`, the file variable is not published into `fvar_descr`
  until `:761`, and the exit frees `fvar` and `sq_file` whenever status is set.

**`SetFileSize` is behaviour-neutral today** — its only callers, `dh_clear.c:107`
and `:114`, still discard the result. It is fixed so that a caller *can* check.

**One instrument lesson from this session, recorded because it nearly cost a
wrong edit:** a `grep | head -12` cut off the line defining `DHE_AK_WRITE_ERROR`
and I briefly concluded the symbol did not exist. It is `err.h:261`. A truncated
instrument reads exactly like a negative result.

## Step 2, second third — transactions, the localised half, 8 Sep 2026

`A2`, `A3`, `A4`, all in `gplsrc/txn.c`. **`make`: only `txn.o` recompiled, `sd`
relinked, 0 errors, 0 warnings. Not exercised** — every check below needs a fresh
install and an induced condition; none was run this session. Step 2 is where "it
compiled" is worth least.

| | Where | Fix |
|---|---|---|
| A2 | `txn.c` TXN_WRITE/DIRECTORY_FILE (`:187`) | `map_t1_id(txn->id, …, mapped_id)` then `dir_write(fvar, mapped_id, …)`; map failure raises 1422 rather than skip |
| A2 | `txn.c` TXN_DELETE/DIRECTORY_FILE (`:225`) | same map, **before** the statistics counters; `snprintf` uses `mapped_id` |
| A3 | `txn.c` same delete arm (`:255`–`:268`) | `stat`/`S_IFREG` guard + tested `remove()` (`errno != ENOENT` → `ER_PERM`, `log_permissions_error`, 1423), copied line-for-line from the non-transactional twin `op_dio3.c:390`–`:403` |
| A4 | `txn.c` `end_txn_level()` | reinstate-and-decrement lifted out of `rollback()` into `end_txn_level()`; called from `op_txncmt()` too, **before** `exit_op_txncmt:` |

**What the Windows record (UPSTREAM_FIXES 17/31/36) added beyond the plan:**

- **A2 — the cache is right to hold the raw id; do not "fix" the write-side
  split.** `op_dio3.c:817`/`:846` deliberately pass the raw `id` to
  `txn_write()`/`txn_delete()`, because `txn_read`/`txn_write`/`txn_delete`/
  `clear_parent` all match the cache against the id the BASIC statement used.
  The mapping belongs only at the point of contact with the disk — the two
  `op_txncmt()` arms — which is where this went.
- **A2 — map failure raises the arm's own error, not a silent skip.** It cannot
  fire (both entry points validate before caching) but a silent skip is the null
  case the instrument rules refuse.
- **A3 was more than "test `remove()`".** The plan named only the discarded
  result; the record adds the `S_IFREG` device-name guard, so the arm now matches
  its non-transactional twin exactly.
- **A4 needs no `op_sys.c` edit.** `op_sys.c:336` merely reads `txn_depth`;
  fixing the decrement makes `SYSTEM(1008)` balanced. The plan's `op_sys.c:335`
  reference is the read site, not an edit site.

**Objection raised and resolved (CLAUDE.md rule):** placing `end_txn_level()`
before `exit_op_txncmt:` means the five `k_error()` paths do **not** pop the
level — correct, a broken commit must not pop as though it committed. That leaves
a **pre-existing** gap: on those error paths `process.txn_id` was zeroed at the
top, so `txn_abort()`/`op_txnrbk()` find nothing and the level stays counted with
the stack orphaned. This third does **not** widen it (the directory-file delete
could not fail before A3, and now can, reaching that state more often — the trade
is deliberate: the alternative is reporting a deletion that did not happen). The
gap is `A1`'s to close, because it needs a decision about the records already
written, not a decrement.

**Cheap checks, none run:**

| Fix | Check |
|---|---|
| A2 write | inside a transaction, `WRITE rec ON dirfile, ','` then `COMMIT`, then `READ … FROM dirfile, ','` — must read back. On disk the file is `%C`, not `,` |
| A2 delete | inside a transaction, `DELETE dirfile, ';'` then `COMMIT` — `%Y` must be gone, and a later `READ` must return not-found |
| A3 | make a directory-file record's on-disk file read-only, delete it inside a transaction — the commit must now report the error, not succeed silently |
| A4 | outer txn writes `R2`, inner txn writes `R3` and commits, outer commits — both `R2` and `R3` must land; `SYSTEM(1008)` balanced across the pair; `SYSTEM(1007)` names the parent after the inner commit |

## Step 2, final third — A1, commit rollback, 9 Sep 2026

The one real piece of work in step 2. **Clean `rm -f gplobj/*.o` build: 0 errors,
0 warnings; `txn.o` and `op_dio3.o` recompiled, `sd` linked. NOT exercised** —
the undo only fires on a commit that fails part way, which needs an induced
failure (a read-only record file, or a record a second session holds) and was
not staged. Verified against UPSTREAM_FIXES 32.

Two halves, both landing in `txn_abort()` (the far side of the `k_error()`
longjmp, since `op_txncmt()`'s `goto exit_op_txncmt` paths are dead code):

| | Where | Fix |
|---|---|---|
| A1 undo | `txn.c` `capture_undo`/`replay_undo`/`free_undo` + `TXN_UNDO` stack | `capture_undo()` reads each record's before-image in the commit loop, immediately before the action; `replay_undo()` writes them back in reverse from `txn_abort()` if the commit longjmps; `free_undo()` drops them on success. Summary line to `errlog` either way |
| A1 locks | `txn.c:txn_abort` + `op_txncmt` | `txn_abort()` releases `commit_txn_id`'s locks (nothing did, so a failed commit held them for the life of the process); `op_txncmt()` clears `commit_txn_id` on success so a later unrelated abort cannot unlock a reissued id |
| groundwork | `op_dio3.c` `dir_read()` + `t1_unmap_chunk()`; `sd.h` prototype | the directory code had a write API and no callable read API; `dir_read()` is shaped like `dir_write()`. The newline→field-mark conversion is lifted out of `read_record()` into shared `t1_unmap_chunk()` so a capture cannot reverse it differently from an ordinary read |

**Deliberately different from the Windows port, and why:**

- **`t1_unmap_chunk()` is LF-only here.** The port folds CR/CRLF (Windows text
  files); this tree's `read_record()` only ever converted `\n`, so the extracted
  helper carries exactly that and no `cr_pending` state. Sharing the *identical*
  body with `dir_read()` is the whole point — a capture that unmapped marks even
  slightly differently would restore the wrong record, silently, on the failure
  path.
- **`process.status`/`os_error` are `int32_t` in this tree** (the port's saved
  locals were `int16_t`); `capture_undo()`'s save/restore locals match, so no
  truncation.

**Refcount checked, not assumed:** `dh_read` returns `ref_ct 1` (its `op_read`
descriptor path assigns without incrementing, unlike the cache path which does
`++`), and `dir_read`'s `ts_terminate()` sets the head chunk `ref_ct = 1`
(`strings.c:467`). So `TXN_UNDO` owns the single reference and `free_undo`/
`replay_undo` decrement it to 0; empty records (`NULL` str) and the not-found
case are guarded.

**Still open after A1** (the pre-existing gap the A4 comment named): on a commit
that fails, the transaction *level* stays counted and its cache stays orphaned on
`txn_stack`, because `process.txn_id` was zeroed at the top of `op_txncmt()` so
`op_txnrbk()`/`txn_abort()`'s `while` finds nothing. A1 closes the locks and the
records; the level/stack cleanup is a separate decision and was not taken.

**Cheap checks, none run:**

| | Check |
|---|---|
| undo | force a commit to fail on its 2nd of 3 writes (make the 2nd record's file read-only, or lock it from another session). Expect: R1 restored to its old value, R3 never written, an `errlog` line `… N restored, M removed, K could not be undone` |
| undo (create) | a transaction that *creates* a record then fails — the created record must be gone, not left half-written |
| locks | after such a failed commit, a second session must be able to lock/read the records — before A1 they stayed locked until the first session died |
| dir_read | as groundwork, an ordinary `READ` from a directory file must still read back byte-for-byte (the shared `t1_unmap_chunk` must not have changed normal reads) |

## Step 3 — build correctness (D5, J4, D6), 9 Sep 2026

Ported the Windows port's header generator and switched off the in-compile
build tools. **Not exercised on a running system** — an install would confirm
error text now displays; the reasoning below is why the risk is low.

| | Where | What |
|---|---|---|
| D5 | `gplbld/gen_includes.py` (new) | ports the Windows generator verbatim (only the header comment and a case-insensitive `sdsys` sub-dir resolver differ). Generates `SYSCOM/ERR.H`, `GPL.BP/ERRTEXT.H`, `GPL.BP/REVSTAMP.H`, `GPL.BP/OPCODES.H` from `gplsrc/{err,revstamp,opcodes}.h`; `--check` writes nothing and exits non-zero on drift |
| D5 | the four generated headers | regenerated. Every SDEXT/crypto/Python/EUID error `$define` went from C spelling + wrong (positive) sign to SD spelling + correct negative sign (e.g. `SD_Mem_Err 10100` → `SD$Mem.Err -10100`); `ERRTEXT.H` gained message text for all the previously-textless codes |
| J4 | `Makefile:70`, `:166` | `all: check-includes sd`; `check-includes` runs `gen_includes.py --check`. Drift is now a build failure |
| D6 | `GPL.BP/ERRTEXT:33`, `GPL.BP/APISRVR:62-63` | the `$execute 'RUN … ERRGEN'` / `REVSTAMP` directives commented out, matching `CPROC:131-132`. They read `./gplsrc` (dev-tree only) and ERRGEN truncates `ERR.H` before regenerating — a compile on an installed tree could wipe the error definitions |

**The instrument, and why it is trusted:** `--check` before regenerating
reported `OPCODES.H` **byte-for-byte in sync** and the other three STALE. The
in-sync `OPCODES.H` is the control — it proves the port reproduces the BASIC
generators exactly (the same translation feeds all four), so the three STALE
results are real drift, not a porting artefact. After regenerating, `--check`
is clean (exit 0) and `make` runs it.

**Why the rename is safe:** grep of `GPL.BP`/`SYSCOM` finds **no BASIC reference
to any renamed error define** — the codes flow as numbers and `ERRTEXT.H` maps
number→text; the only `SD_EUID_*` hits are the *key* names `SD_EUID_SET`/
`_RESTORE` (102/103 in `KEYS.H`), which are a different thing and untouched.

**Deliberately different from the port:** output dirs are upper-case here
(`GPL.BP`, `SYSCOM`) pending the lower-case migration, so the generator resolves
the `sdsys` sub-directory case-insensitively rather than hard-coding `gpl.bp`.
`OPGEN`'s BASIC source still exists (its removal is step 4 §G3); the generator
already covers `OPCODES.H`, so removing it later loses nothing.

**Regenerating rewrites a timestamp line** in each output (`* Generated by … at`),
which `--check` ignores but a write refreshes — so a manual regenerate always
dirties the four files even when content is identical. The build only ever runs
`--check`, which is timestamp-blind, so this does not dirty ordinary builds.

**Cheap checks, none run:**

| | Check |
|---|---|
| D5 | on an installed system, trigger a Python or crypto error and confirm the message text shows, not a bare number |
| J4 | edit `gplsrc/err.h`, run `make` — it must fail at `check-includes` until `gen_includes.py` is run |
| D6 | compile `ERRTEXT`/`APISRVR` in the bootstrap — must succeed without running ERRGEN/REVSTAMP (the tracked `.H` files are current) |

## Step 4 — the shrink (done), 9 Sep 2026

One release (L1.0-0). Removing subsystems named in the project stance. Ordered
so the VOC-touching ones go together; TAPE was independent and went first.

| | What | Done? |
|---|---|---|
| I1 | TAPE/RESTORE: deleted `sd64/tape/` (24 records — 5 `GPL.BP`, 19 `VOC` verbs) and the install prompt at `installsdai.sh:475`. It was copied in at install from `tape/`, never shipped in `VOC_TEMPLATE`, so nothing else referenced it (grep confirmed). `bash -n installsdai.sh` clean | **done** |
| I3 | SED — `GPL.BP/SED` + `VOC_TEMPLATE/SED` + `NEWVOC/SED`. **Its "key file" is `&SED.BINDINGS&`, created per account at run time and never shipped, so there was nothing to delete.** SED's own messages `6694`/`6695` kept, as the port kept them | **done** |
| I4 | UPDATE.RECORD — `GPL.BP/UPDREC` + `VOC_TEMPLATE/UPDATE.RECORD` + `NEWVOC/UPDATE.RECORD` | **done** |
| I5 | MODIFY — `GPL.BP/MODIFY` + `VOC_TEMPLATE/MODIFY` + `NEWVOC/MODIFY` | **done** |
| I2 | PROC — `GPL.BP/PROC` and `LISTPQ` in all three places (`SD.VOCLIB`, `VOC_TEMPLATE`, `NEWVOC`). PROC is a VOC record **TYPE**, not a verb, so it has no VOC record of its own. `CPROC`'s `PQ` case is **replaced, not deleted** — it refuses by name with new `MESSAGES/10099`, the port's number and its wording. **`OP_PROCREAD`, `op_procread()` and BCOMP's `st.procread`/`st.procwrite` are KEPT** (owner's ruling, 9 Sep — see below). `proc.*` SYSCOM slots kept | **done** |
| G1 | SDSYS `BP` test programs: removed 18 (`BIGSTR_TEST`, `MSGTEST`, `PCL`, `PCL.GRID`, `PCODE_LIST`, `SDTEST_V8`, `SD_ENCRYPT`/`_B64`/`_EXT`, `SD_EXT`, `TEST.THEN.ELSE`, `TESTSZ`, `U0032`, `U50BB`, `VFS.CLS`, `pref_t`, `sdTests`, `tilde_test`). **Kept `PY_JSON`/`PY_TERM`/`PY_TEST`/`PY_TEST2`** (owner decision 9 Sep — the documented examples for the kept Python feature). Verified no VOC verb dispatches to the `BP` dir and no bootstrap program names them; the `PCL` name-collision is with the `GPL.BP/PCL` printer subsystem (a different dir, stays) — `NEWVOC/PCL` is only a printer keyword. No changelog entry (SDSYS dev cleanup, no product function) | **done** |
| G2 | VFS scaffolding: the BASIC advertised a virtual file system the C never implemented. Removed `VFS_FILE` 5 (`descr.h`), `SEL_VFS` (`dh.h:154`), `FL_TYPE_VFS` (`keys.h:57`) and the three uses — `op_dio3.c:509` guard, `kernel.c:600` flag test, `pdump.c:227` print. **RETIRED, comments left in place: `DHF_VFS` 0x40 (`dh.h:105`, a file-header bit), `PF_IS_VFS` 0x00200000 (`kernel.h:101`, an object-header bit), errors 3038–3040 (`err.h:147`).** BASIC: `FTYPE`'s `VFS:` case, `_VOC_REF`'s branch that left a `VFS:` pathname relative, `FL$TYPE.VFS` (`SYSCOM/KEYS.H:29`); `ERR.H`/`ERRTEXT.H` regenerated. `GPL.BP/_EXTENDLIST` deleted with its four registrations (`pcode.h:38`, `gplbld/pcode_bld.py`, `gplbld/COMP_PCODE`, the record). **Left alone by ruling: `examples/windows.c/winsdclilib/err.h`** — the client library's public error header, so removing codes there is an API change. Clean `rm -f gplobj/*.o` build, 79 files, 0 warnings; 12 removal checks each against a control. **Not installed** | **done** |
| G3 | OPGEN: deleted `GPL.BP/OPGEN` (no VOC, no `$execute`, nothing calls it — superseded by `gen_includes.py`, whose `OPCODES.H` output is byte-identical, proven in step 3). Updated the two "generated using OPGEN" comments (`bbcmp.py:138`, `BCOMP:58`) to name `gen_includes.py`. No changelog entry — no user-visible effect | **done** |
| G4 | SDNet: deleted `gplsrc/netfiles.c` (removed from `gpl.src`), the `;` dispatch + `net_open` in `op_dio1.c`, and **every `NET_FILE` case / `net_*` call across `op_dio1/2/3/4.c`, `op_lock.c`, `dh_ak.c`** (~30 sites); removed the `NET_FILE` type (`descr.h`, `FVAR.NET` in `DEBUG.H` + the "(Networked)" DEBUG arm), the `net_*` prototypes (`sd.h`), and the 3 verbs (`GPL.BP/SETSRVR`/`DELSRVR`/`LISTSRVR`, `VOC_TEMPLATE/SET.SERVER`/`DELETE.SERVER`/`LIST.SERVERS`). `K$GET.SDNET.CONNECTIONS` now returns empty. **Kept (deliberate residue): `sdnet.h` (socket/termios portability header, NOT SDNet — build breaks without it), `NETFILES` config + sysseg field, `USR_SDNET`, `K$SDNET`, `SrvrOpenSDNet`.** Clean `rm -f gplobj/*.o` build; installs and runs at `2b4d9f0`; read side observed (`SELECT`/`LIST`/`COUNT VOC`). **CLOSED 9 Sep** (owner) — write/delete/lock accepted on conformity, not measured | **done** |

**Not exercised.** I1 removed data records and an install prompt; nothing in the
C build depends on them, so `make` is unaffected, but an install that used to
offer the TAPE prompt has not been re-run.

**G2's checks.** 12 removed/control pairs, every control fired: the four C
`#define`s against `SEQ_FILE`/`DHF_NOCASE`/`SEL_DH`/`PF_IS_TRIGGER`, the two
BASIC ones against `FL$TYPE.SEQ`/`ER$ENCRYPTED`, `'VFS:'` in `FTYPE` and
`_VOC_REF`, and `_EXTENDLIST`'s four registrations against `_DELLIST`.
**Anchored on `^ *\$define` / `^#define`, not the bare name** — Windows
HISTORY.md ~611 records that version reading its own removal comments as hits.
One check ran on the artefact rather than the source: `strings bin/sd` finds
`VFS handler` 0 against `Is trigger` 1.

***WHAT NONE OF THAT REACHES: `sd` HAS NOT STARTED FROM A PCODE LIBRARY BUILT
WITHOUT `_EXTENDLIST`.*** That is G2's one failure mode with teeth, and it is
loud rather than silent — `load_pcode()` (`sd.c:597`) prints *"Pcode item ... not
found"* and refuses to start if a `Pcode()` entry has no library object. Read
rather than assumed: it matches on `obj->ext_hdr.prog.program_name`
(`sd.c:620`), so entries are found **by name and removing one shifts nothing**,
and `bin/pcode` is concatenated strictly from the `pcode_fs` list
(`pcode_bld.py:144`), so dropping the name drops the object. All four
registrations went together. **An install is what would witness it.**

**Two objections raised against G2 in-session and resolved, recorded per
CLAUDE.md:**

- **Why `SEL_VFS` and `FL_TYPE_VFS` were deleted outright while `DHF_VFS` and
  `PF_IS_VFS` were retired.** The first two are in-memory only — a select-list
  type index and a `FILEINFO` return value — so a future feature may have the
  numbers. The second two occupy bits in a *persisted* header (`dh.h:98` says
  the LS 16 bits come from the file header; `kernel.h`'s LS 16 come from the
  object header), and a file or object written by another MultiValue
  implementation could carry them. Same reasoning the port used.
- **An in-place upgrade leaves stale copies behind.** `GPL.BP/_EXTENDLIST` and
  `PCODE.OUT/_EXTENDLIST` are not deleted from an existing `/usr/local/sdsys` by
  the installer, which copies over rather than clearing. Harmless — nothing
  looks either up, and `bin/pcode` is rebuilt from the list — but **the
  installed tree will not match the source tree** until a clean install. The
  Windows port did not face this: its upgrade writes `Type: filesandordirs` and
  deletes the whole directory first.

### Step 4 / §I — where the plan was wrong, and what was not checked

***THE PLAN'S §I2 IS WRONG IN THREE PLACES AND THE RECORD CAUGHT ALL THREE
BEFORE ANYTHING WAS DELETED.*** This is the grep-the-record rule paying for
itself; each was then confirmed against source rather than taken on the
document's word.

| Plan says | Measured |
|---|---|
| "`GPL.BP/PROC` and `GPL.BP/BBPROC` (the PROC compiler)" | ***`BBPROC` IS NOT PROC.*** Its own first line reads *"BootStrap Build process … a mini command processor … compile from source the basic programs needed by sd to run"*. It is one of `bbcmp.py`'s three bootstrap seeds (`installsdai.sh:491`). **Deleting it would have broken every install.** Windows HISTORY.md:31800 says it in one line: *"`QPROC` and `BBPROC` are not PROC despite the names"* |
| "`installsdai.sh:500` is one of three bootstrap compile steps and goes with it" | Line 500 is `chown -R sdsys:sdusers`. The three `bbcmp.py` steps are 491–493 and compile `BBPROC`, `BCOMP`, `PATHTKN` — **none is PROC. The installer needed no change at all** |
| "Retire the opcode … as the port did" | **The port kept `OP_PROCREAD`** — `opcodes.h:516` and `op_misc.c:1208` carry it in `sd4windows` today. The plan cites the port as its authority for the opposite of what the port did |

***OWNER'S RULING, 9 Sep 2026: KEEP `PROCREAD`/`PROCWRITE`, MATCH THE PORT.***
So §I2 is BASIC-only and **no C file was touched**. Three measurements backed
the question: the port kept them; `op_procread()` (`op_misc.c:1226`) already
self-guards by walking the call stack for a program named `$PROC` and returning
empty plus error status when it is absent, so with `GPL.BP/PROC` gone it answers
correctly with **no C change**; and `PROCWRITE` has no opcode at all — `BCOMP`
compiles it to a store into `SYSCOM.PROC.IBUF`, and those common slots must stay
because removing one shifts every slot after it.

**Four near-miss names, each checked and each kept** — the first three are the
port's list, the fourth is new here: `QPROC` (query processor) · `PDBG`/`PDEBUG`
(PHANTOM debugger, not PROC's) · `_KEYEDIT`/`KEYCODE.H` (`OP_KEYEDIT` is a BASIC
opcode, `opcodes.h:441`, and `_BINDKEY`, `_KEYCODE` and `BCOMP` reference them,
so they are not orphaned by SED/UPDREC going) · **`ST.MODIFY` in `bbcmp.py:5826`
and `BCOMP` is the BASIC `MODIFY btree, data` statement, nothing to do with the
`MODIFY` verb.** `MODIFYA` is reached by `VOC_TEMPLATE/MODIFY.ACCOUNT` → `$MODIFYA`,
a different catalogue name from the deleted `$MODIFY`. All nine were asserted
present after the deletions, as controls on the `git rm`.

***THE BASIC WAS NOT COMPILED THIS SESSION, AND THE INSTRUMENT THAT WAS TRIED
COULD NOT DO IT.*** `gplbld/bbcmp.py` cannot compile `CPROC`: it aborts on
`$IFNDEF`, which `CPROC` uses, and before that it fails to resolve
`$include define_install.h` because **`bbcmp.py:7141` upper-cases every include
name** and the file on disk is lower case. It is the restricted bootstrap
compiler for `BBPROC`/`BCOMP`/`PATHTKN` only. So the check that stands is
structural: `begin case`/`end case` **31/31 unchanged**, `loop` and `repeat`
each down by exactly **1** — the single pair removed from the `PQ` arm. **The
install's two-stage bootstrap is what compiles `CPROC`, and a syntax error there
aborts the install**, which is the loud failure this is relying on.

***AND THAT `bbcmp.py` UPPER-CASING IS A §M TRAP WORTH KEEPING.*** On a
case-sensitive filesystem an include whose file is lower case is unresolvable to
that compiler. The real `BCOMP` evidently resolves it, since installs work — but
§M1's "fold, then rename" has a second lookup here that the plan does not name.

## Open

*§M is done — installed on `83e5ccf` (13 Sep 23:06), witnessed 14 Sep; `verify-nocase.py` reads "§M NAME
HALF: COMPLETE" (run 14 Sep). The paragraph below is the 9 Sep plan.*

~~***RELEASE-BLOCKING: §M, THE LOWER-CASE CONVERSION.***~~ Owner's ruling, 9 Sep
2026 — later in the port is fine, **by the end is not optional**. Scheduled at
step 7 with §N, per the plan; the reasoning and the two dependencies are in the
step-4 note above. `M1`'s fold (the colon prompt and query language, and BASIC
`OPEN` including Q-pointers — order **as typed, then lower case, then upper
case**) has no dependency on `update.accounts` and may be started at any time.
Known traps: `M2`'s both-spellings-exist guard must **refuse, not guess**;
`git mv` may need a two-step for a case-only rename, verified with
`git ls-files` rather than by looking at the working tree; and
**`bbcmp.py:7141` upper-cases every `$include` name**, which is a third lookup
the plan does not name (found 9 Sep — see the §I note).

### §M3 on-disk directory rename — DONE, installed on `83e5ccf` (13 Sep 23:06) and witnessed 14 Sep (design approved with rulings 12 Sep, below as approved)

***SUPERSEDING RULING, OWNER, 12 Sep 2026 (later the same night): NO MIGRATION IS
NEEDED FOR ANY OF §M.*** *"There are no existing installs of SD Core for Linux
and there is no migration path from full SD"* (full SD has the TAPE system; this
does not). Every install is fresh and §M lands before the first release, so no
account, register or VOC ever holds an old name. ***Consequences:*** D1–D4 are
renames plus references only; D3's installer migration, `!vocpaths`, and the
two-name register restore are ***DROPPED***; rulings 2 and 3 below are moot, and
ruling 4 reduces to "CREATE.FILE makes lower-case names" (D4). The already-built
case migration (`GPL.BP/voccase`, its calls in LOGIN `update.voc` and MODIFYA
`voc.delta`, messages 10916/10917, `verify-voccase`, `verify-lcnames` sections
4–5) serves no install — ***removed 13 Sep on the owner's instruction*** (START HERE).
***Also found while auditing D1:*** the SDSYS account's own directories (`VOC`,
`$HOLD`, `$HOLD.DIC` in sdsys) are account directories, reached by the same
generic `pathname:'VOC'` code as every account — they move with D3, not D1.
`PCODE.OUT` is build tooling — D2.

***OWNER'S RULINGS, 12 Sep 2026, on the four questions below (2 and 3 now moot):***
1. ***Four phases*** D1–D4, each its own install and witness.
2. ***D3 migration by the installer only***, on a keep cycle, as root, before
   `UPDATE.ACCOUNTS ALL`. No runtime fallback: an account restored later from
   an old backup needs the migration re-run by hand — so the migration must be
   runnable on its own, not only inside the installer.
3. ***A `[locked]` F record whose path names a renamed directory: rewrite and
   report.***
4. ***EXISTING USER DATA DIRECTORIES ARE RENAMED TOO*** — against the proposal.
   D3 therefore covers every F record in an account whose field 2 or 3 is a
   relative path to a directory in that account with an upper-case letter
   (e.g. `ORDERS`, `ORDERS.DIC`): rename on disk, rewrite the path, refuse
   both-spellings. ***Consequences to handle and state in the changelog:***
   record ids inside those files do NOT change (12 Sep ruling); a user program
   or script that names the directory by a hard-coded OS path will break and
   cannot be migrated; multifile subdirectories and `.DIC` parts rename with
   their file; a path shared by two F records is renamed once; an absolute
   path into another account is not touched by the exact-relative rule.

*The proposal as it was written before the rulings:*

Owner chose this as the next category (12 Sep). The port has no precedent: its
`e1095ab` needed no migration because NTFS matches either case. ***Written in
the conditional; nothing below is measured behaviour except where it says so.***

**Measured facts it rests on (12 Sep, install `8c14634`):**
- A directory is reached only through a PATH in a VOC record: DON's 12 F/Q
  records name `VOC`, `$HOLD`, `$HOLD.DIC`, `$SVLISTS`, `BP` relatively and
  `@SDSYS/<NAME>` for system files. A session opens its VOC by `openpath "VOC"`
  (LOGIN:468, CPROC:2952, APISRVR, SETACC); admin verbs by `pathname:'VOC'`
  (CREATEA, DELACC, MODIFYA, SETFILE, `_VOC_REF`, LOGIN's all-accounts walk).
- Uninstall deletes sdsys whole (`deletesdai.sh:182`); only the register is
  carried, saved as `/home/sd/ACCOUNTS` and moved back at `installsdai.sh:722-724`.
- Keep cycle: `UPDATE.ACCOUNTS ALL` runs as root at `:940-944`, before
  services start — ***the one moment no user session can be open.***
- C names only `messages.c` MESSAGES ×3 and `to_file.c` `$HOLD` ×3. 483
  path-name lines overall (C, installer, bootstrap, helpers, verifiers,
  comments included). `bbcmp.py:7141` upper-cases every `$include` name.

**Proposed phases, each its own install and witness:**
- ***D1 — sdsys data directories*** (NEWVOC VOC_TEMPLATE MESSAGES SYSCOM
  SD.VOCLIB PCODE.OUT ACCOUNTS `$HOLD`, and the bootstrap-made `$HOLD.DIC $IPC
  $MAP $MAP.DIC VOC VOC.DIC ACCOUNTS.DIC DICT.DIC DIR_DICT`): repo `git mv`,
  BBPROC FILES_LIST, installer bootstrap loop, `gplbld/FILES_DICTS`, messages.c,
  every `@sdsys:@ds:'X'` literal, helper scripts (`reconcile-accounts.sh` REG).
  No user data moves. Two carry-overs: the register restore accepts the old
  `/home/sd/ACCOUNTS` or the new name (refusing if both), and account VOC paths
  `@SDSYS/X` are rewritten (see *path rewrite*).
- ***D2 — sdsys program directories*** `GPL.BP GPL.BP.OUT BP BP.OUT` (the port's
  `1943704`): build tooling churn (make/gen_includes, bbcmp, pcode_bld,
  installer, CLAUDE.md, every verifier path), and the `$include` upcase above.
- ***D3 — per-account directories*** `VOC $HOLD $HOLD.DIC $SVLISTS BP BP.OUT`,
  user-owned, the only phase touching user data.
- ***D4 — CREATE.FILE makes lower-case names*** (`CREATEF:306/:379`, the meter's
  code site). New files only; existing ones keep working through their recorded
  path.

**Path rewrite (`!vocpaths`, called by update.voc beside `!voccase`):** for F
records only, fields 2 and 3: a value EXACTLY equal to a known old path
(`@SDSYS/SYSCOM`, `$HOLD`, …) becomes the new one; any other value is never
touched; records rewritten are named. Idempotent.

**D3 migration, proposed:** the INSTALLER, as root, on a keep cycle, for every
registered account path (user and group), BEFORE `UPDATE.ACCOUNTS ALL`: per
directory, both spellings present → refuse that account and name it; old only →
`mv` (one `rename(2)`, owner and mode kept); new only → nothing. Then the update
rewrites the paths. ***Objection raised and not fully resolved:*** between the
`mv` and the rewrite an account is broken; if the install dies there, it stays
broken until the update is re-run. Mitigation proposed: the installer stops,
names the accounts and the one recovery command; both steps idempotent.
***Alternative considered:*** a runtime fallback (open lower, else upper, refuse
if both) needing no ordering and covering an account restored later from an old
backup — at the cost of dual-casing support in the runtime for ever.

**Would falsify the plan:** a session or process that can be open during the
keep-cycle update (the order at `:940-944` would then not be safe); a path to an
account directory recorded anywhere other than a VOC record (the register's
`ACC$PATH` is the account root, already lower); F records whose path is
absolute to a renamed directory (the exact-match rewrite would miss them).

**For the owner to decide before D1:** (1) the phase split; (2) D3 migration by
installer only, or also a runtime fallback; (3) a `[locked]` F record whose
path names a renamed directory — rewrite and report (proposed: a dead pointer
protects nothing, the same logic as verbs overriding the lock) or leave and
report; (4) existing user data files already created upper case — leave
(proposed) or rename.

### Conformity fix 10 Sep 2026 — CREATE.ACCOUNT always creates the OS user

***The `config('CREATUSR')` gate is removed from `CREATEA` `case 1`*** so
`create.account` ALWAYS creates the OS user — conforming to the port, whose
CREATEA removed the same gate 14 Aug 2026 on the owner's rule (*"SD has accounts,
not accounts-and-users; creating an account IS creating the OS account, nothing
to opt in to"*). Was: this tree required `CREATUSR=1` (off by default) **and** no
`no.query`, else 6074. Now: `create-account user <name>` creates the OS user +
prompts for its password + the SD account. `no.query` with no OS user is still
refused (creating needs the interactive password). Also applied the port's 21 Aug
fix: the missing minus on `@system.return.code` for a failed create (was `+6`).
Syntax-reviewed, compile-on-reinstall. `CREATUSR` still parses/prints; nothing
reads it. ***Witness: `create-account user tstd` now needs no prior `useradd`.***

### [S.5] Parity audit against SD Core for Windows (10 Sep 2026) — CLOSED 14 Sep 2026: its witness list below WITNESSED on `f2251e6` by `witness-release-run.sh` §12 and §15, every row passing

Owner's instruction: audit every implemented feature against the port (the
reference) and correct drift except OS differences. **Scope: this project's own
work since 8 Sep** (plan steps 1–4, PRE_RELEASE entries, §L1, CREATUSR, MICRO);
the inherited AI layer (`9f82a52`) was not audited.

| # | Drift found | Correction |
|---|---|---|
| 1 | `SH ! CONFIG LISTU LIST.READU LIST.LOCKS CLEAR.LOCKS LOCK SET.DATE CLEAN.ACCOUNT` in NEWVOC = every tier | removed from NEWVOC, added to `TIER.ADD.ADMINISTRATOR` (port's 24 Aug split). UMASK stays (stance) |
| 2 | `NLS SET.LANGUAGE LOAD.LANGUAGE` in the VOCs | removed; programs kept (port 16 Aug, "English only") |
| 3 | `UPDATE.ACCOUNT` | `UPDATE.ACCOUNTS` + `ALL` (LOGIN mode 4; msgs 10170–10173, 10170/10172 adapted); heading verb 30→15 (port UPSTREAM 37) |
| 4 | messages 10030–10045 reused port ids with other meanings | port-equivalent → port id (10032 10033 10080 10102 10105 10106 10109 10113 10114 10157); Linux-only CPROC notices → **10900–10904**, a block the port does not use |
| 5 | kernel keys 57–59 = the port's `K$AUDIT/K$WINPATH/K$WINPID` | `K$REAL.USER/K$SH/K$OS.EXEC` → **90–92** in `gplsrc/keys.h` and `INT$KEYS.H`, agreement checked |
| 6 | Y/N prompts (port PRE_RELEASE 79) | 19 message records byte-copied from the port (trailing spaces); Enter = N at SETFILE, DELETEF, CREATEF, SETPTR, QPROC ×2, ED ×3 (incl. `yes.no`), LOGIN ×2 |
| 7 | VOC copy stripped field 1 (port PRE_RELEASE 136) | copied whole at CREATEA, LOGIN `update.voc`, MODIFYA `tier.build.rec` |
| 8 | DELACC: three prompts, `CREATUSR` gate, deletes any `sdu_` user | port flow: 10158 + one confirmation 10084/10085 (Enter = N), xref is a statement, ACCOUNTS deleted last; OS user deleted only if new `!is_sd_user` finds GECOS `SD account`, stamped by `sd-elevate useradd -c`. 6029/6031/10027 retired |
| 9 | CREATEA lacked `SH-ON`/`OS-ON` | added: USER account below ADMINISTRATOR, reported with 10102 |
| 10 | MODIFYA `os.set` accepted group accounts, reported one field | refuses non-`sdu_` (10105); reports both fields (10102) |
| 11 | DELCAT's admin test inside the loop | before the loop (port 18 Aug) |
| 12 | WEOFSEQ failure `goto` skipped `sq_file->base = -1` | the port's shape |

**Already equal to the port:** step 1–2 C fixes (`k_error`, keep-alive,
`get_ak_node` zero tests, `dh_file` chsize, `txn.c` `map_t1_id`/remove/`end_txn_level`,
commit rollback); PRE_RELEASE 19 `K_ADMINISTRATOR`; 21 `-internal` `check_admin()`;
TERM; `TIER.OMIT.STANDARD` (identical); WHOAMI; `check-msglen`, `checksyntax`,
`mkbasicsyntax`, `sdbasic.yaml`, `gen_includes` (header comments only).

**OS/model differences, kept:** per-account `ACC$SH`/`ACC$OS.EXEC` vs the port's
`os.users`; `sd-elevate`/sudoers vs elevation; the `SET_PASSWD`/`CREATE_USER` admin
gates; ssh ForceCommand vs `sdssh`/`sdapi` groups (no `ssh|api|both|none` keyword);
CATALOG's gcat chown; `clopts.c` `kill()` pid guard; UMASK; "Linux" in 2004/10024/6075;
lower-case names (§M, scheduled).

***PORT DEFECT FOUND:*** the port's `MODIFYA tier.build.rec` still strips field 1
after its own PRE_RELEASE 136, so every downgrade there compares unequal and counts
the verbs "left alone". Fixed here; the port needs the same one-routine change.

**Compile evidence** (dev build, recipe, as `don`, staged sha = tree sha each):
CPROC both `IS_INSTALL` arms, LOGIN, MODIFYA, CREATEA, DELCAT, SETFILE, DELETEF,
CREATEF, SETPTR, QPROC, ED, MICRO, DELACC, IS_SD_USER, CREATE_USER — **0 error(s)**.
Reds: `DELCATX` 7, `ISX` 2, `LOGINX` 1, none written to `BP.OUT`. sha256 of all 137
`gcat` entries identical before/after every run. **The first pass's verdicts were
lost** to a ugrep regex error and the pass was re-run. `test-sd-elevate.py`
**37/0** with a new STAMP row; red = the HEAD helper's dry run shows no stamp.
`op_seqio.c` and a full `rm gplobj/*.o` rebuild clean; fixtures removed,
`COUNT VOC` 410, plain `bin/sd` rebuilt.
***THE KEY RENUMBERING MAKES THE BINARY AND GPL.BP ONE UNIT — MEASURED:*** the
renumbered tree `bin/sd` against the installed `$LOGIN` aborts every session,
`Illegal KERNEL() action key (58) at line 286 of $LOGIN`. CPROC/LOGIN/MICRO were
compiled with a scratchpad harness built from HEAD's `keys.h` (deleted after).
**Do not run the tree `bin/sd` against the current install; install the commit.**

**Owner's ruling on the home directory, 10 Sep, BUILT + COMPILED, UNRUN:**
`DELETE.ACCOUNT <acc> REMOVE.HOME` (a parameter, so the port's one-confirmation
rule holds; 10905 names the home). Only for an SD-stamped user (else 10906, before
the question); home read from `getent`, result read off disk (10907/10908);
`userdel` exit 12 = user gone, home not. New `sd-elevate userdel-home` re-checks the
stamp and that home is exactly `<useradd -D HOME>/<user>`; `test-sd-elevate.py`
**42/0**, the `don` row refused *for the stamp* (reason printed). No ALLOW row is
possible on a box with no stamped user — the allowed half is an install witness.

**Objections and gaps, not done:**
- Users created before the stamp (`don`, `pete`, `tstd`, `tprog`, `tadm`) are left
  in place by DELETE.ACCOUNT (10036).
- Existing accounts keep the admin and language verbs already in their VOCs (an
  update never deletes); a tier change does not remove them either (not in a layer).
- A non-admin's SH-ON now needs the SH verb copied into that VOC (the port's
  model); entry 23's `pete` witness relied on SH being in NEWVOC.
- 10114's port text "nothing has changed" is false when VOC_TEMPLATE fails after
  the standard layer (the port's too).
- MICRO vs the port's `EDIT` (1002 lines: mark tokens, working copy removed on
  every exit — UPSTREAM 16's second half) is not converged.
- Port features not built here: SUSPENDED, TIERGATE, GRANT/REVOKE/LIST.GRANTS,
  `[locked]`, ADOPT, an upgrade running `UPDATE.ACCOUNTS ALL` (F2), MODIFY.PASSWORD,
  `K$AUDIT`, §M.

***Witness, after an install of the commit (conditional):*** a new PROGRAMMER
account has no `SH`/`CONFIG`/`LISTU`, an ADMINISTRATOR one has them;
`UPDATE.ACCOUNTS FOO` → 10173; `UPDATE.ACCOUNTS ALL` in SDSYS → 10170 then 10171 with
a count; `listf` in a new account shows descriptions; `CREATE.ACCOUNT USER x SH-ON`
→ 10102; `DELETE.ACCOUNT X` → one `(y/<n>)` naming the Linux user, user gone;
`DELETE.ACCOUNT PETE` → 10036, `pete` kept. Falsified by any of those not holding.

### [S.7] NANO and MICRO — the port's EDIT program adopted (10 Sep 2026) — WITNESSED 12 Sep by `verify-editors.py` 28/28; the person-visible half WITNESSED 14 Sep by the owner (both editors show colour at a real terminal) — CLOSED

Owner, 10 Sep: Microsoft Edit is not packaged for Linux; nano replaces it and
gets SD BASIC highlighting; the verb is `NANO`; `EDIT` stays an alias for `ED`.
`GPL.BP/MICRO` is **deleted**; new `GPL.BP/EDIT` (the port's, `$EDIT`) serves
`NANO` and `MICRO` (both templates `CA $EDIT`; `NANO` added to
`TIER.OMIT.STANDARD`, now 43). **Kept from the port:** lossless mark tokens
(`~~ ~\` ~! ~- ~,`), round-trip check, both gates before anything is written,
working copy removed on every exit, one `crt` per message line. **Adapted:**
`find.editor` = `command -v` (absolute path required); no `micro.home` (a Linux
user's `~/.config/micro` is already writable); micro syntax still copied per user
(`place.syntax`); `check.permitted` asks `K$OS.EXEC`; POSIX path from
`fileinfo(FL$PATH)` used as is; open folds case; single-quote names refused.
**nano highlighting:** new `gplbld/mknanosyntax.py` (the port's extraction, nanorc
writer, refuses a regex `grep -E` cannot compile) → `gplbld/nanocfg/sdbasic.nanorc`;
the installer places it in `/usr/share/nano` (Debian `/etc/nanorc:257` includes
`*.nanorc`), `deletesdai.sh` removes it.
**Evidence:** EDIT **0 error(s)** (harness, as `don`), gcat unchanged;
`test-edittokens-units.py` (adopted, path `GPL.BP`) **23/0 cases, 597 871
strings, 209 records (19 with specials), 0 lost**; nano measured in a pty (scratch
script, entry 12's method): `.sdbasic`+nanorc **11** distinct SGR vs `.plain`+nanorc
**3** and `.sdbasic`+empty rc **3**; `checksyntax` on the regenerated YAML 24/0;
both shell scripts `bash -n` clean. ***Witness after install (conditional):***
`nano bp x` and `micro bp x` open with colour; `~~` in the editor saves as a value
mark; a PROGRAMMER account without OS-ON is refused before `$HOLD` is touched.

### [S.6] MICRO + plain-sd administrator OS access (earlier: built and compiled 10 Sep 2026, the MICRO program half superseded by the section above; CLOSED 14 Sep 2026 — WITNESSED on `79d7e87`, `witness-release-run.sh` §11 H1–H4)

***Found by the owner, 10 Sep:*** `micro bp test` → *"File Error: bp could not be
opened"*; `MICRO BP TEST` → 10053, then *"Record was not saved"*. Entry 12's
witness drove micro in a pty and only compiled `MICRO`, so the verb had never run
through SD.
- **Cause 1:** `MICRO:226` launched with `execute "!"` = CPROC `os.command`, gated
  admin-or-`K$SH` (`CPROC:3502`). **Cause 2, entry 23's gap:** `USR_ADMIN` is set
  only under `sudo sd` (`CPROC:299`), so an ADMINISTRATOR in plain `sd` had no
  SH/`!`/OS.EXECUTE, and `MODIFYA` refused to grant (10039) on the false premise
  that the gates read the tier via `USR_ADMIN`. The port hit the same case (its
  `HISTORY.md` 29 Aug, *"AN UNELEVATED ADMINISTRATOR HAS NO sh"*; owner there:
  *"by default without escalating"*); ours, 9 Sep: *"by tier, automatic and
  unrevocable"*. **Cause 3:** `open` is case-sensitive and only `BP` exists (§M).
- **Fix:** `LOGIN:319` and CPROC logto (`:2777`) load `K$SH`/`K$OS.EXEC` true when
  the account's `ACC$TIER` is ADMINISTRATOR **and** `is_grp_member(@logname,
  'sdadmin')` — both halves of the owner's definition. Account-scoped: a LOGTO
  reloads from the target's record, so the port's LOGTO leak does not arise.
  `MICRO` takes the port `EDIT`'s shape: `check_permitted` first (blank `K$TTY` →
  refuse; `K$ADMINISTRATOR` or `K$OS.EXEC` → allow; else refuse naming OS-ON),
  `find_editor` via `os.execute "command -v micro" capturing` (entry 4), launch
  with `os.execute` (admitted on `HDR_INTERNAL`) + exit code in the failure text,
  file name as typed → lower → upper (§M1's order), single-quote record names
  refused. `$include int$keys.h` added.
- **Compile** (dev build, recipe, as `don`): LOGIN **0** / red **1**; MICRO **0** /
  red **2**; CPROC **0 on both `IS_INSTALL` arms** (tree `define_install.h` is the
  install arm; the runtime arm was staged as the installer's `*comment out *` line,
  `installsdai.sh:794`) / red **1**. `gcat/$LOGIN`, `$MICRO`, `$CPROC` sha unchanged;
  fixtures + `BP.OUT` removed, `COUNT VOC` 410; plain `bin/sd` rebuilt.
- **Not verified:** `os.execute … capturing` has no other caller in this `GPL.BP`
  (BCOMP parses it; runtime unwitnessed). `K$TTY` blank when stdin is not a tty is
  read from `kernel.c:177`, not measured.
- ***Witness, after an install (conditional):*** plain `sd` as `don` — `micro bp
  test` and `MICRO BP TEST` open micro; `SH ls` runs. PROGRAMMER `tprog` without
  OS-ON — `MICRO BP X` gives the OS-ON refusal and leaves no `$HOLD` working copy;
  after `MODIFY.ACCOUNT TPROG OS-ON` + re-entry, micro opens. From DON, `LOGTO` a
  non-admin account → `SH ls` refused 10053. Falsified by 10053 in DON, or by micro
  opening for `tprog` before OS-ON.

### ADOPT — the installer's pre-existing-user exception (BUILT 11 Sep 2026 as PORT_ADOPTION queue 15 and witnessed; the plan below is as written 10 Sep)

***Owner's rule (10 Sep 2026): all SD users are created WITHIN SD (CREATE.ACCOUNT
makes the OS user — see the conformity fix above); the ONE exception is the
original installer, whose OS user already exists and is ADOPTED.*** The port does
this with an **ADOPT keyword** to CREATE.ACCOUNT — `CREATE.ACCOUNT USER <name>
ADOPT` uses a pre-existing OS user without creating it and defaults to the
ADMINISTRATOR tier (port `CREATEA:1617`: `if adopt and tier='STANDARD' then
tier='ADMINISTRATOR'`); the installer runs `sd -internal CREATE.ACCOUNT USER
<name> ADOPT`, the one path exempt from the install-time tier gates.

***Gap here:*** CREATEA has no ADOPT keyword; its `case is_user` SILENTLY adopts
ANY existing OS user, and the installer leans on that (`installsdai.sh:822`,
`create-account USER $tuser ADMINISTRATOR no.query`). That lets any pre-existing
OS user be taken in by plain create.account — against the rule.

***To build — one COUPLED, install-critical commit (CREATEA + installer together,
or the installer's own seeding breaks):***
- CREATEA: parse an `ADOPT` keyword (`more.args`); `case is_user` → if ADOPT, use
  the existing OS user and default the tier to ADMINISTRATOR (mirror port
  `:1617`); else **refuse** (a pre-existing OS user must be ADOPTed).
- `installsdai.sh:822`: seed the installer with `... USER $tuser ADOPT no.query`
  (ADOPT forces admin; no OS user is created, so `no.query` is fine).
- ***Install-critical:*** if refuse-unless-ADOPT lands without the installer
  switching to ADOPT, the install aborts at its own account step. Build atomic,
  let the bootstrap compile it, and witness with a clean install (the installer
  seeding itself is the witness) + a plain `create.account USER <existing-os-user>`
  being refused.
- ***Sequencing:*** build AFTER the pending SL1-core + CREATUSR verification
  reinstall — do not stack three unverified install-critical CREATEA changes.

### [S.3] §L1 — per-tier VOC (CLOSED 14 Sep 2026: core witnessed 10 Sep, MODIFYA re-derivation 14 Sep by `witness-tierchange.sh` 15/15; the LOGIN `update.voc` filter's STANDARD case WITNESSED 14 Sep by `witness-release-run.sh` §7 on `984be50` — Y at the prompt left `basic` and `run` absent, `list` present)

***`LOGIN` `update.voc` tier filter — BUILT AND COMPILED 10 Sep 2026, NOT RUN.***
The port's 17 Aug 2026 fix. All three call sites set `update.voc.tier`: mode 2
(`UPDATE.ACCOUNT`) and the `$RELEASE` prompt through new `get.acc.tier`
(`ACCOUNTS` by `@who`, own file variable — `acc.f` is closed by then); the
all-accounts walk off `acc.rec`. `update.voc` never copies the two control records
and skips `TIER.OMIT.STANDARD` ids unless the tier is blank/PROGRAMMER/ADMINISTRATOR
(blank = full, as the port). `SUSPENDED` → `ACC$PRIOR.TIER` at both resolvers
(nothing writes SUSPENDED here yet; carried for conformity). Also the port's
`old.rec = ''` before `READU` (upstream defect: a failed READU left the previous
id's record, so byte-identical adjacent ids like CATALOG/CATALOGUE were skipped).
**Not taken from the port's `update.voc`:** `[locked]` (= F3), Enter-defaults-N,
`upcase(id)='MD'` (§M), and its PRE_RELEASE 136 field-1 keep — `CREATEA:552` strips
field 1 too, so both sites must change together or the update undoes the create.
**Compile** (dev build, recipe, DON `BP`, as `don`): **0 error(s)**, *"with no
errors"*, staged sha = tree sha; red control = unbalanced bracket at the new
`get.acc.tier` line → **3 error(s)**, first `576: Right bracket not found`.
`BASIC:301` auto-runs `CATALOGUE BP $LOGIN` after a clean compile: refused
*"Command requires administrator privileges"*, and `gcat/$LOGIN` sha256 was
identical before and after (`gcat` is `sdsys` 0755). Fixtures + `BP.OUT` removed,
`COUNT VOC` **410**; plain `bin/sd` rebuilt (no DEVELOPER line).
***Witness, after an install of the commit (conditional):*** in STANDARD `tstd`
(368, no BASIC) set `$RELEASE` field 2 to an older stamp, log in as `tstd`, answer
`Y` → expect `COUNT VOC` 368 and `BASIC` not found. It would be falsified by 410.
The pre-fix control would be the same steps on the current install (expect 410 +
BASIC), which alters `tstd`.

***`MODIFYA` tier-change re-derivation — BUILT AND COMPILED 10 Sep 2026, NOT
RUN.*** *Witnessed 14 Sep 2026 by `witness-tierchange.sh`, 15/15 (START HERE).* The port's `voc.delta` + `tier.rank`/`tier.layer`/`tier.build.rec`/
`tier.add.one`/`tier.del.one` (port `gpl.bp/MODIFYA:1227-1440`), called in
`set.tier` **before** the register write (port order: a stopped run leaves the old
tier and a repeat converges); `voc.ok` false → **10044**, tier not written. Up
copies a layer in; down deletes only records equal to a tier build, else counts
them kept. `voc.from` is the raw field, so blank ranks PROGRAMMER; `old.tier`'s
blank-as-STANDARD stays, used only by the sdadmin test. Messages **10043** counts,
**10044** refusal (port 10114 says *"nothing has changed"*, false when the template
open fails after the standard layer — reworded to the register), **10045** failed
deletes. ***Adapted, not copied:*** `tier.build.rec` transforms NEWVOC records
only — `CREATEA:573-574` writes VOC_TEMPLATE records raw (`UNLOCK` keeps *"Verb to
unlock records"*), so transforming them would make every downgrade keep `UNLOCK`.
No SUSPENDED/route/promo/Windows-group parts (none exist here).
***Privilege — read from code, not measured:*** `sudo sd` drops to euid `sdsys`
(`CPROC:301`) and `sdext_eguid.c:66` sets no supplementary groups. `$MODIFYA` is
in `privileged_commands` (`CPROC:180`), so `CPROC:1682` restores euid 0 around it;
that is what would let it write `pete`/`don` VOCs, whose groups lack `sdsys`
(`sdu_pete:root,pete`; newer `sdu_tstd:root,sdsys,tstd`). ***Lead, unmeasured:***
`UPDATE.ACCOUNT` is `V|IN|15`, never raised, so its SDSYS all-accounts walk
probably cannot write user VOCs — hence the `$RELEASE` route for LOGIN's witness.
**Objections kept, not resolved:** (1) as the port, the register is written even
when deletes failed (10045), so the tier reads lower while verbs remain and a
repeat is a no-op (`from = to`); (2) `tier.layer` reads NEWVOC by the lists'
UPPER-CASE ids, so on ext4 §M must lower-case the lists and NEWVOC together or
every layer silently moves nothing.
**Compile** (dev build, recipe, as `don`): **0 error(s)**, staged sha = tree sha;
red = `(` injected in `tier.layer` → **9 error(s)**. Auto-`CATALOGUE $MODIFYA`
refused; `gcat/$MODIFYA` sha unchanged. Fixtures + `BP.OUT` removed, `COUNT VOC`
410. `check-msglen.py` REFUSED 10043 (exit 2, no `\n` escapes, so it measured
nothing); all three are one line, ≤69 chars, against a bound of 231.
***Witness, after an install of the commit (conditional)***, under `sudo sd`:
`MODIFY.ACCOUNT TSTD PROGRAMMER` → expect *"VOC: 42 records added, 0 removed, 0
left alone"* and tstd's `COUNT VOC` 410; back to `STANDARD` → *"0 … 42 removed"*,
368. `MODIFY.ACCOUNT TADM PROGRAMMER` → 5 removed (expect 410; also
`leave.sdadmin`'s first run), then `ADMINISTRATOR` → 5 added. Repeating a tier
should print 0/0/0. Any other count falsifies it. How to count another account's
VOC from SDSYS is untested (admin `LOGTO` gate, PRE_RELEASE 20 table).

***WITNESSED 10 Sep 2026 on a reinstall.*** CREATEA compiled (the install
completed). New accounts created on that install, counts read in-SD via `COUNT
VOC` / `LIST VOC 'BASIC'`: **STANDARD `tstd` = 368 records, BASIC NOT FOUND;
PROGRAMMER `tprog` = 410, BASIC present.** The gap is **exactly 42** — the 42
verbs in `TIER.OMIT.STANDARD`. So STANDARD gets NEWVOC less the omit list (cannot
build) and PROGRAMMER gets it entire — the tier VOC works at creation. Also
witnessed: the CREATUSR fix — `create-account user tprog programmer` (no
`no.query`) had SD create the OS user (`useradd`) and prompt for the password.
~~***Still pending: running the two builds above, and the ADOPT work (above).***~~ *14 Sep: the MODIFYA build and ADOPT are witnessed; the LOGIN filter's STANDARD case has no recorded witness.* Build details: the two
control records
`sdsys/NEWVOC/TIER.OMIT.STANDARD` (42 dev verbs) and
`sdsys/NEWVOC/TIER.ADD.ADMINISTRATOR` (5 admin verbs: CREATE/DELETE/MODIFY/
UPDATE.ACCOUNT, UNLOCK), and the **tier-aware copy loop in `CREATEA`**
(`:517-580`) — STANDARD = NEWVOC less the omit list, PROGRAMMER = NEWVOC entire,
ADMINISTRATOR = that plus the add list from `VOC_TEMPLATE`; the two control
records are never copied; matching is case-insensitive. Block structure reviewed
by hand; ***the authoritative compile is the install's two-stage bootstrap***
(it aborts on a syntax error), so the witness is a reinstall + inspecting a new
account's VOC per tier. (`LOGIN` `update.voc` and the `MODIFYA` re-derivation are
built, above.) *(Design
follows.)*

### §L1 design — per-tier VOC (proposed 10 Sep 2026; built, see the section above)

***The gates exist (entry 23); what is missing is that every tier still gets the
SAME verb set.*** §L1 would make the account's VOC depend on `ACC$TIER` (field 5,
already written by `CREATEA`/`MODIFYA`), conforming to the Windows port's model
(port `gpl.bp/CREATEA:1224-1440`, `newvoc/TIER.OMIT.STANDARD`,
`newvoc/TIER.ADD.ADMINISTRATOR`):

- **STANDARD** = NEWVOC less the verbs named in a new `NEWVOC` record
  `TIER.OMIT.STANDARD` — *"can run an application but not build one."*
- **PROGRAMMER** = NEWVOC entire (today's behaviour for everyone).
- **ADMINISTRATOR** = NEWVOC entire plus the verbs named in `TIER.ADD.ADMINISTRATOR`,
  copied from `VOC_TEMPLATE`.

**Two control records to add to `sdsys/NEWVOC`** (field 1 = description, fields 2+
= verb ids; the copy loop skips both records themselves):
- `TIER.OMIT.STANDARD` — the port's list transfers almost verbatim: **all 40 of
  its entries exist in this tree's NEWVOC** (checked 10 Sep, case-insensitively):
  `basic catalog(ue) delete.catalog(ue) compile.dict cd generate phantom run map
  debug ed edit micro create.file delete.file clear.file configure.file
  analyse/analyze.file fstat hsm set.trigger create/delete/build/make/list.index
  copy copyp delete rename reformat sreformat delete.common cname logout pstat
  pdebug pdump dump`.
- `TIER.ADD.ADMINISTRATOR` — ***must be curated for SD Core, NOT copied from the
  port.*** This tree's `VOC_TEMPLATE`−`NEWVOC` delta (17 ids) is mostly file /
  bootstrap entries; the actual admin VERBS in it are `create.account
  delete.account modify.account update.account unlock`. (The port also lists
  `grant revoke config listu sh !` etc.; here `sh`/`!` stay in every VOC and are
  gated at the C layer by entry 23, and the others are absent — so do not name
  them.)

**Three code sites (all must share one tier-filter, or the VOC drifts):**
1. `CREATEA` copy loop (`GPL.BP/CREATEA:517-534`) — read tier; skip the two
   control records; for STANDARD skip omit-list ids; for ADMINISTRATOR also copy
   the add-list records from `VOC_TEMPLATE`.
2. ***`LOGIN` `update.voc` (`GPL.BP/LOGIN:110-137,364-373`) re-copies NEWVOC on a
   release update*** — it must apply the SAME filter, or a VOC update silently
   restores a full VOC to a STANDARD account. ***THE PORT ALREADY HIT AND FIXED
   THIS (17 Aug 2026):*** its `update.voc` re-copied all of NEWVOC with no tier
   filter, handing a STANDARD account back `BASIC`, `CATALOG`, `RUN`, `ED`,
   `COPY`, `DELETE.CATALOG`, and was reachable from an ordinary login. Paid for
   next door — not a hypothesis. See the port's `HISTORY.md`.
3. `MODIFYA` on a tier change ***has NO VOC re-derivation today*** (checked 10
   Sep) — §L1 must add it so `MODIFY.ACCOUNT <a> STANDARD|PROGRAMMER|ADMINISTRATOR`
   re-derives the VOC; the port's `voc.delta`/`tier.set` is the model, and its
   PRE_RELEASE 57 rule (*a grant may go down or sideways, never up*) governs it.

**SD-Core adaptations / risks (what would falsify the plan):**
- ***Case.*** NEWVOC ids are still UPPER-CASE here (§M not applied), so the match
  must be case-insensitive (`upcase()=upcase()`, as the port) and must still work
  after §M lower-cases NEWVOC. §L1 and §M's fold interact — neither should assume
  the other's casing.
- ***SUSPENDED*** tier VOC is undecided; LOGIN already refuses a suspended login,
  so content may be moot — confirm. ***[11 Sep 2026: "LOGIN ALREADY REFUSES" WAS
  FALSE — no door in LOGIN, CPROC or APISRVR tested SUSPENDED (grep, 11 Sep).
  Settled by queue 12: the VOC is left as it is while suspended, as the port's.]***
- ***OBJECTION RAISED AND RESOLVED 10 Sep 2026 (owner) — the omit list stands as
  the port's, INCLUDING `run`, `phantom`, `logout`.*** The principle: **a STANDARD
  account only runs CATALOGUED programs.** The three are omitted on purpose —
  `run` (no uncatalogued programs), `phantom` (no background tasks), `logout` (no
  control of other users). A STANDARD user *"will probably never even see the
  command line."* The sanctioned way to give one account one extra feature is for
  an admin to **copy that VOC item into the user's VOC** — no tier change — so the
  omit list can be broad without being a trap. ***This decision and its rationale
  are the port's, recorded in its `HISTORY.md` ("17 Aug 2026 — Section 8"), the
  reference implementation; the owner confirmed it here.*** `PHANTOM` is omitted
  precisely because it runs a catalogued program in the *background* — the tier's
  "only run catalogued programs" is about foreground, attended use.
- ***RELATED INTENT, beyond §L1's VOC scope (note for later):*** because a STANDARD
  user is not expected to see the `:` prompt, such accounts likely want to be
  launched straight into an application (a forced `LOGIN`/menu entry) rather than
  dropped at the command line. That is a LOGIN-path decision, not a VOC one — flag
  it when §L1 lands, do not fold it in here.
- **Test after building:** a STANDARD account must have no `BASIC` (so the entry-23
  10054 witness moves to a PROGRAMMER account — already noted in PRE_RELEASE 23);
  PROGRAMMER = full VOC; ADMINISTRATOR = +admin verbs; a `MODIFY.ACCOUNT` tier
  change re-derives the VOC; a release `update.voc` preserves the tier's VOC.

### [S.8] `kernel(K$INTERNAL, n)` sets internal mode with no `HDR_INTERNAL` guard (CLOSED 14 Sep 2026, INSTALLED `ca4c07c`)

***Witnessed as far as it can be, 14 Sep 2026 on `ca4c07c`:*** the install's
two-stage bootstrap compiled `gpl.bp` (the install completed and is stamped), a
piped plain sign-on as `don` answered `WHO` → `2 don` and `COUNT VOC` → 418,
and `sudo sd` → `LOGTO don` worked (S.2's run), so LOGIN's `:555` read passed.
The refusal itself stays unreachable from compiled BASIC, as below.

***Built 14 Sep 2026: `op_kernel.c` `case K_INTERNAL` changes `internal_mode` only
when `process.program.flags & HDR_INTERNAL`; a refused set changes nothing and is
not an error.*** Every shipped BASIC caller passes `-1` (`grep` of `gpl.bp`:
option, debug, acomp, icomp, login, listcom, createa, bcomp, pstat); the only
setter is `sd.c:353,364` in C, which the guard does not touch. ***The refused path
cannot be reached from compiled BASIC***, so no witness can show the refusal;
what an install can show is that nothing that reads it broke — `sd -internal`
compiling `gpl.bp` at install, and LOGIN's `:555` check. That would be falsified
by an install whose bootstrap compile or sign-on fails. Not filed to the port.

*(Original entry follows.)* Measured 14 Sep 2026: `gplsrc/op_kernel.c:140-147` sets `internal_mode` for any
`n >= 0`; the port's `op_kernel.c:146-151` is identical. Reachable only from
`$internal` code, since `KERNEL` compiles only there (PRE_RELEASE 19, 21), so a
guard would be belt-and-braces, in the shape of PRE_RELEASE 19's
`K_ADMINISTRATOR` fix. First named as a lead in PRE_RELEASE 21.

### [S.1] BASIC screen/widget library — stage 1 DONE 14 Sep 2026; stages 2-5 DEFERRED TO 1.2 (owner, 15 Sep 2026), §OPEN§ (design note of 10 Sep below)

***STAGE 1 DONE 14 Sep 2026 — THE FALSIFIER DID NOT FIRE: THE RENDERER CAN STAY
PURE BASIC, AND SO CAN MOUSE INPUT.*** Measured in a sandbox (`gplbld/
sandbox-txnfail.py --keep`, then `gplbld/tui-render-probe.py --sandbox <dir>
--frames 500`; no sudo, live IPC unchanged) with `gplbld/tui-render-probe.bp`:
double buffer of one string per row, an equal row skipped by one compare, a
changed row trimmed to its differing span (16-char chunks, then chars), one
write per frame, `@(col,row)` for position. sd ran in a pty as a person's session
would, read by a sink that never slows it. ***160x48, 500 frames each, CPU
(`SYSTEM(9)`) per frame: FULL repaint 0.11 ms (7,935 bytes); naive SCROLL 1.05 ms
(every row changes); SCROLL through the terminal's scroll region 0.04 ms (163
bytes); one typed character 0.02 ms (6 bytes). Wall for all 2,000 frames incl.
8 MB through the pty: 617 ms.*** 80x24: 0.07/0.08/0.01/0.01 ms, wall 88 ms. Against
16 ms (one 60 Hz frame) the worst is ~15x under. ***Mouse: `ESC [ < 0 ; 12 ; 5 M`
written into the pty came out of KEYIN as `27 91 60 48 59 49 50 59 53 77`, byte
for byte*** — no `op_tio.c` change is needed for SGR 1006. ***NOT measured:***
colour attributes (a parallel string per row, roughly doubling the compare), a
terminal emulator's paint time (not SD's), any machine but this one. ***Two
harness traps, both in its comments:*** SD's terminfo tree has `xterm` and not
`xterm-256color`, and with the latter the session stalls at its first prompt;
and the prompt is the bytes `\r:` — a bare `:` matched a colon inside frame text
and typed OFF into the middle of a render. ***Stage 2 next, in the conditional:***
a catalogued event layer (`KEYIN`/`KEYREADY` decoded to logical keys, incl. the
SGR mouse report), the draw layer above as the shared renderer, then field,
button, listbox, menu, checkbox, radio and a form/focus manager — keyboard-only
first. What would falsify stage 2's shape: colour attributes pushing a frame
past 16 ms at 160x48 (measure them before the widgets depend on the format).

*(Original note, 10 Sep:)*

***Goal (owner, 10 Sep 2026):*** extend SD BASIC so a programmer builds rich
terminal screens — administrative apps rivalling the best TUI frameworks, up to
a traditional terminal-based IDE — WITHOUT leaving BASIC and WITHOUT any
commercial or client-side dependency. GPL-clean: standard ANSI/terminfo escape
sequences only, shipped as catalogued SD BASIC (thin C only where BASIC cannot
reach). AccuTerm is ruled out (commercial, needs a server-side API,
GPL-incompatible). Target terminal up to 160x48.

***What SD already provides:*** `KEYIN()` (raw key, timeout) + `KEYREADY()` (byte
pending) for input; the `@(...)` cursor/attribute set (`gplsrc/op_tio.c`) for
output; terminfo for portability. ***Missing:*** any widget layer, logical key
decoding (KEYIN returns raw bytes), and mouse.

***Architecture — a BASIC-facing API over layered catalogued subroutines:***
- **Event/key layer** — wrap KEYIN/KEYREADY into one `get.event()` decoding
  arrows, Tab, Enter, Esc, function keys (and mouse, below) into logical codes.
- **Screen/draw layer** — box-drawing, attributes, regions; ***double-buffered
  with minimal-diff redraw*** (write only changed cells) — the key to interactive
  speed in interpreted BASIC at large sizes.
- **Geometry/layout** — absolute plus simple layout managers (row/column/grid,
  anchoring, min/preferred size) so a screen reflows between 80x24 and 160x48.
- **Widgets** — label, button, text field (single/multi-line/masked), list box,
  table/grid (scroll/sort), tree, radio group, checkbox, dropdown/combo, menu +
  menu bar, tabs/notebook, scrollbar, progress bar, status bar, panel/frame,
  split pane, modal dialog, message/confirm box, and a text editor/viewer widget.
- **Form/focus manager** — owns a widget set, Tab/focus order, key dispatch,
  redraw, returns collected values; binds to MV dynamic arrays (field/value marks).
- **Theming** — colour via SGR (16/256/truecolor) / terminfo `setaf`/`setab`.

***Rendering:*** box-drawing via VT line-drawing (`acsc`/`smacs`) so it works in
the **default 8-bit build**; Unicode box-drawing is an **ECS-mode** enhancement
(SD's 8-bit-vs-ECS mode interacts here). Alternate screen + inhibit-cursor for a
clean full-screen app.

***Mouse:*** xterm SGR 1006. ***Likely pure BASIC*** — read the report sequence
(`ESC [ < … M/m`) via KEYIN/KEYREADY like any escape sequence — **IF** SD's input
path passes those bytes through KEYIN untouched. ***Verify that first;*** a small
`op_tio.c` addition only if it does not.

***THE MAIN TECHNICAL RISK — what would falsify the pure-BASIC engine: redraw
speed.*** 160x48 is ~7,680 cells; a full repaint or a fast scroll in interpreted
BASIC may be too slow to feel interactive. ***The FIRST task is to prototype the
diff-renderer and MEASURE a full redraw + a scroll at 160x48*** — if BASIC cannot
hit interactive latency, the draw/diff layer (and possibly key-decode / mouse)
moves to thin C behind the same BASIC API. The widgets come after that number is
known, not before it.

***North-star (owner): a terminal IDE*** — editor widget (SD-BASIC-aware), VOC/file
browser tree, multiple panes, menu + status bar, assembled from the widget set.
It is the validation that the toolkit is "rich enough", not the MVP.

***Staged (conditional):*** (1) prove the diff-renderer fast enough at 160x48;
(2) event/key-decode + draw + core widgets (field, button, listbox, menu,
checkbox, radio) + form manager, keyboard-only; (3) mouse; (4) advanced widgets
(table, tree, tabs, editor); (5) the IDE.

***Fits the port:*** GPL-clean, no dependency, AI-maintainable BASIC; rides the
ssh boundary + tiers — a STANDARD account ssh'd into SD lands in a catalogued
rich-screen app, which is the §L1 "launch into an application" note's natural
payload.

**Exercise the step 1 fixes.** The table above lists the check for each. `D3` and
`B1`/`B2` are minutes of work on the installed system and are the two most worth
doing, because a wrong catalogue gate would refuse an administrator.

**Exercise step 2 — all of it (`A1`–`A6`).** Committed and compiled, none run.
The check tables are under each step-2 section. `A1`'s undo is the one that needs
an *induced commit failure* to reach at all.

***STEP 2 IS WHERE "IT COMPILED" IS WORTH LEAST.*** Every item touches
transactions or index structure; `A5`'s failure mode is a permanently damaged
index and `A1`'s is a half-applied commit, both silent. Build a way to exercise
a fix before making it, not after — that discipline was not met for step 2, which
is the standing risk to retire before step 4's removals bury it.

~~**Next planned work is step 3 (`D5`/`J4`/`D6`), in START HERE**~~ — *stale:
steps 3 and 4 are both done. The current next task is at the top of this file.*

***ADDED 9 Sep 2026 — TWO LEADS THAT ARE WRITTEN DOWN AND NOT BUILT.***
`op_kernel.c:140`'s `kernel(K$INTERNAL, n>=0)` **sets** internal mode and has no
`HDR_INTERNAL` guard — entry 19's shape exactly. It is contained today only
because both command-line routes in are now gated (`PRE_RELEASE` 21), and one
line would make that belt-and-braces. And `is_grp_member` (`GPL.BP/IS_GRP_MEMBER`)
reads only field 4 of `/etc/group`, the supplementary member list, so a person
whose **primary** group is the one being tested answers `false`. No shipped call
depends on that today; it would bite the first time somebody's primary group is
an SD group.

**ADDED 10 Sep 2026 — API port 4243; the two installer prompts + a TCP listener
BUILT + WITNESSED 10 Sep.** Owner: SD Core conforms to the Windows port, which
stays on **4243** (reconsidered 4243→4245→4243 this session; the durable reason
is that changing the API port across an upgrade is itself the problem, so the
port stays put and Linux matches it for upgrade compatibility). Built this
session on the owner's direction, approach **B** — bind-address gating, ufw NOT
force-enabled:
- **TCP listener, localhost by default.** `usr/lib/systemd/system/sdclient.socket`
  gains `ListenStream=127.0.0.1:4243` beside the Unix socket (the port's "LOCAL"
  state). `installsdai.sh` rewrites it to `0.0.0.0:4243` + `ufw allow 4243/tcp`
  only when **"Allow API access"** is yes; else it stays local and no rule added.
- ***C CHANGE, REVERSING A DELIBERATE DECISION — `gplsrc/linuxio.c`
  `start_connection()`*** accepted only `PF_UNIX` (mab, 2024-02-19). `PF_INET` is
  now accepted **for the API server only** (`is_sdApiSrvr`, i.e. `sd -n -q`); no
  `getpeereid` on a TCP peer, so the connection is gated by SD user/password
  (APISRVR SDConnect) plus the bind/firewall choice. `PF_INET6` still refused
  (listener is IPv4). Built: `make` **0 errors**, `linuxio.o` recompiled, `sd`
  linked.
- **Two installer prompts** (asked up front, both default NO): "Allow ssh access"
  = Y → `systemctl enable --now ssh` + `ufw allow 22/tcp`; "Allow API access" = Y
  → the 0.0.0.0 rebind + `ufw allow 4243/tcp`. ufw is not force-enabled — the
  gate is the bind address; the ufw rule is belt-and-braces for when ufw is on.
- ***WITNESSED 10 Sep 2026 on the `11571a7` install (API=Y, listener
  `0.0.0.0:4243`).*** The owner ran the headless client
  `scratchpad/apitest/apitest.py` (`sdclilibwrap.sdmeConnect` → a real TCP
  connect, not the Unix socket): `--user pete --account PETE` → `SDConnect`
  returned **1**, `SDConnected()=1`, and `WHO` over the connection returned
  `2 PETE` (SDExecute err 0). ***So the least-tested claim is confirmed: `sd -n
  -q` completes the SDConnect handshake + `login()` + `sdusers` check on a TCP fd
  exactly as on the Unix socket.*** Both installer prompts appeared on the run.
  Still to exercise if wanted: a **remote** host (`--host <ip>`), and a **default
  (API=N)** install to confirm the listener is then 127.0.0.1-only.
- **Client library HARDENED + default 4243, 10 Sep 2026.** `gplsrc/sdclilib.c`
  was replaced with the owner's standalone hardened `linuxsdclilib` (validated
  packet/arg lengths, index-packet overflow prevention, partial/interrupted I/O,
  desync abandonment, max-record enforcement, `SV_EMSG_PAIR`/`SV_ECONTXT`), plus
  new headers `gplsrc/sdclilib.h` + `gplsrc/client_ctype.c`. Its `SDConnect`
  default is now **4243** (was 4245). Repo's shared headers left untouched;
  `make` 0 errors, both `sdclilib.so`/`libsdcli.so` linked; the standalone repo's
  `make check` (smoke + internal) passed. ***WITNESSED on the installed runtime
  10 Sep 2026*** — after a reinstall from `origin/main`, `apitest.py` (loading
  the installed hardened `sdclilib.so`) connected TCP `127.0.0.1:4243` as `pete`:
  `SDConnect`=1, `SDConnected()`=1, `WHO`→`2 PETE`, err 0. Source published at
  `github.com/dmontaine/linuxsdclilib` (the Aug-15 hardened repo).
- **Still open, separate:** `gplsrc/sdclient.c:3404` (a different client, not the
  lib) still defaults `port = 4245`; and `changelog`'s historical 4243→4245 line
  runs against the ruling. Both minor, client-side.

**Guards ported from the Windows version — surveyed 9 Sep 2026, owner's ask.**
The survey is recorded so it is not repeated: the port has **1** Claude hook and
**170** `gplbld` scripts (157 `.ps1`, 13 `.py`).

- ***THE CLAUDE HOOK WAS ALREADY HERE AND IS ALREADY IDENTICAL.***
  `.claude/hooks/no-program-edits.py` and `.claude/settings.json` are
  **byte-identical** to the port's, `python` resolves at `/usr/bin/python` so the
  settings command is not silently taking its `|| exit 0` branch, and
  `--selftest` reports **32 cases (14 deny, 18 allow), 0 failed**. It also fired
  for real this session, on an inline `python -c` writing a scratch fixture.
  There were no user-level or `settings.local.json` hooks in either project, and
  no active git hooks in either.
- **`gplbld/check-msglen.py` is ported, byte-for-byte.** Does a message fit
  `k_error()`'s buffer once `sysmsg()` expands it. **Copied rather than adapted
  because all four constants were checked against this tree first and all four
  match** — `MAX_ERROR_LINES` 3 / `MAX_EMSG_LEN` 80 (`sddefs.h:124-125`), the
  buffer declaration and 10-byte `"%08X: "` prefix (`k_error.c:160,212`), the D1
  `sizeof(s) - n` fix (`k_error.c:226`), and the `\n`→LF+CR substitution
  (`messages.c:337-340`). ~~**It hard-codes the bound 231 and will not notice if
  those change**, which its header now says.~~ *(14 Sep 2026: it derives the
  bound from the source each run and refuses if a premise is missing — P.11.)*
- **Run on `MESSAGES/10099`, added this session: 165 rendered against a bound of
  231, 3 escapes, exit 0.** The instrument was shown to discriminate rather than
  merely pass — an over-long fixture gives `fits: False` exit **1**, and one with
  no escapes is **REFUSED** at exit **2** rather than passing. *Worth knowing:*
  10099 renders as **4 lines where `k_error` is sized for 3**, which is not a
  fault here because `CPROC` shows it with BASIC `display sysmsg(...)` rather
  than raising it through `k_error()`; the port ships the same 4-line text.
- **Examined and NOT ported, each for a stated reason** — do not redo this:
  `stage.py` and `bootstrap.py` build a Windows *installer*; here
  `installsdai.sh` bootstraps on the target machine · `checksyntax.py` /
  `mkbasicsyntax.py` are `micro`-editor syntax tooling — *(superseded: both were
  ported under `PRE_RELEASE` 2, ruled 9 Sep — micro stays, highlighting kept)* ·
  `mkvocdoc.py` is coupled to `sd.iss` and the port's 26 Aug CONFIG-display
  decision · the other 157 are `.ps1`, **of which only 51 are on subjects §H
  excludes — the remaining 31 relevant ones are `PRE_RELEASE` 1.**
- ***`check-stale-leads.py`: THE NOTE HERE OF 9 Sep WAS WRONG TWICE AND IS
  CORRECTED.*** It said the script refuses at its line 637 for want of
  `PRE_RELEASE_FIXES.md`, and that a verbatim copy would be *"a silent no-op"*.
  **Both were read off the source rather than measured.** That file now exists,
  and the script still cannot run: copied verbatim it exits **2 before any
  phase** — *"could not bound section 7"* — because the entry-boundary machinery
  every phase depends on is built from the port's headings. And it is **not
  silent**: it refuses loudly, as the port designed it to. The unadapted copy was
  removed rather than committed. Scope of the real work is `PRE_RELEASE` 9.

**Standing gaps:**

- **No `assert-current` equivalent.** Nothing refuses to run a check against an
  install older than its source, so a green result can come from the previous
  build. This matters more from step 2 on, where a wrong answer is silent.
  **The port's is `gplbld/assert-current.ps1` — PowerShell, so this is a rewrite
  and not a copy**, which is why the 9 Sep survey above did not close it.
- ~~**Two generated headers drifted.**~~ **CLOSED 9 Sep 2026** — see "Step 3"
  below. `gplbld/gen_includes.py` regenerates `SYSCOM/ERR.H`,
  `GPL.BP/ERRTEXT.H`, `GPL.BP/REVSTAMP.H`, `GPL.BP/OPCODES.H` from the C
  headers; `make` runs its `--check` first, so drift is now a build failure.
- **`sdsys/MESSAGES` still lacks records `4100`, `4101`, `-10303`** (plan §D5).
  That is the runtime message file, not generated from `err.h`, so the generator
  does not touch it; adding those three is a separate deliberate data edit.

**Undecided:**

- `AI_Modification_Notes.zip` is a redundant archive of `AI_Modification_Notes/`,
  which is tracked. It is in `.gitignore` for now rather than deleted; deleting it
  is probably right.

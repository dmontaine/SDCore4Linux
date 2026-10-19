#!/bin/bash
#
# regress.sh - run the sandbox suites, one fresh build each, and say which passed.  No install, no sudo.
#
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh                     all of them, one after another, about 50 minutes
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --jobs 6            all of them, six at a time
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --snapshot --jobs 6 --free   the same, on a copy of the tree (edit meanwhile)
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --skip ced          all but the pseudo-terminal one
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --only coll,try     just those
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --tree DIR          the suites of the sd64 tree DIR, in that tree
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --free              then the gplbld/test-*.py free checks too
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --list              print the suites and stop
#   /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress.sh --changed --snapshot --jobs 8   THE RUN TO USE: only the suites the changed
#                                                                       files need (gplbld/regress-map.txt), and the free checks; --since REF for a range
#
# Exit 0 every suite passed, 1 a suite failed (or gave no verdict), 2 something could not be run (an unknown suite,
# a sandbox already holding the sandbox shared memory keys, a suite that said CANNOT RUN).  No sudo.
#
# WHAT IT COUNTS AS A PASS.  A suite passes only when it exits 0 AND its own last line says "N passed, M failed" with
# M = 0 and N > 0.  A suite that printed no such line, exited non-zero, or passed no rows FAILS: "nothing went wrong"
# is not a verdict (CLAUDE.md, an instrument shows what it DID).  Every suite's whole output is kept in the log
# directory, which is printed, and the [FAIL] rows of a failed suite are shown.
#
# WHY A SNAPSHOT.  Each suite builds its sandbox from the tree it lives in, so editing a kernel source while the run
# is going voids the suites still to come.  --snapshot makes a copy of the tree, builds it, runs the suites in the
# copy and removes it afterwards, so the live tree is free to edit.  By hand, the same is:
#   git ls-files -z --cached --others --exclude-standard sdb_ai | rsync -a --from0 --files-from=- ./ COPY/
#   cp sdb_ai/sd64/gplsrc/sdext_python_inc.h COPY/sdb_ai/sd64/gplsrc/      (git ignores it; the build needs it)
#   cp installsdcore.sh deletesdcore.sh PROJECT_STATUS.md PRE_RELEASE_FIXES.md PORT_ADOPTION.md COPY/   (the --free checks read them)
#   (cd COPY/sdb_ai/sd64 && make)                                           (SERIAL: make -j races sdtic and terminfo)
#   COPY/sdb_ai/sd64/gplbld/regress.sh --jobs 6 --tree COPY/sdb_ai/sd64
#
# WHY SOME CAN RUN AT ONCE.  A sandbox is built with its own pair of shared memory keys (sddefs.h, patched into the
# sandbox's copy: gplbld/sandbox-txnfail.py).  The pair is 0x53434c91/92 for the keyset 0, and each further keyset
# is 0x20 higher: --jobs N starts N workers, worker k exports SDBOX_KEYSET=k, and the workers take the suites from
# one queue, the longest first (the order of ALL_SUITES below).  Nothing else is shared: each suite has its own
# directory and its own run-tagged names.  The run refuses to start while any of the N pairs is held (an earlier
# sandbox, or one of your own on the same keys).  Each sandbox leaves ~14,000 files in /tmp (1M inodes there) and is
# removed as soon as its suite ends, so N workers hold about N times that at a time.
#
# START-HISTORY:
# 12 Oct 26 dm  New.  The list and the loop had lived in a scratchpad script that was lost between sessions; the
#               timing (11.8 minutes for 26 suites, 15 s of each being the sandbox build) is from the run of 12 Oct.
# 12 Oct 26 dm  lock-b6 added (the 27th suite, 49 s; the 27 together took 14 minutes).
# 12 Oct 26 dm  file-b8 added (the 28th suite, about 80 s).
# 12 Oct 26 dm  lang-a15 added (the 29th suite).
# 12 Oct 26 dm  fix-b10 added (the 30th suite).
# 12 Oct 26 dm  sed-menu (SED's menu bar and the screen library's widgets, 81 rows) and screen (the SCREEN statement
#               through user programs) added (the 31st and 32nd suites); both on the branch sed-screenlib.
# 13 Oct 26 dm  gates added (S.63, the per-account OS-access gates): the 31st suite on Dev, the 33rd with the two above.
# 13 Oct 26 dm  syntax added (SED's syntax colour, 22 rows): the 34th on the branch.
# 13 Oct 26 dm  dbgui added (the debugger's full-screen display on the library, 16 rows): the 35th.
# 13 Oct 26 dm  sed-edit added (SED's undo and redo and its mouse, 71 rows): the 36th.
# 14 Oct 26 dm  ide added (the IDE, gpl.bp/ide, 52 rows): the 37th.
# 14 Oct 26 dm  edbug added (ED's L, the debugger's matrix elements and common blocks, 13 rows): the 38th.
# 14 Oct 26 dm  openzero added ($MODE OPEN.FAIL.ZERO.FVAR, 7 rows): the 39th.
# 14 Oct 26 dm  pickrn added ($MODE PICK.READNEXT, 5 rows): the 40th.
# 14 Oct 26 dm  mlmask added (OPTION PICK.ML.CONV.MASK, 11 rows): the 41st.
# 14 Oct 26 dm  chained added (OPTION CHAINED.SELECT, 6 rows): the 42nd.
# 14 Oct 26 dm  execlist added ($MODE EXECUTE.CLEARLIST, 5 rows): the 43rd.
# 14 Oct 26 dm  partial added ($MODE PARTIAL.EXPRESSIONS, 7 rows): the 44th.
# 14 Oct 26 dm  the A-1 / A-3 / A-4 batch: classas (INHERITS AS and empty method brackets, 8 rows), stdfil (the default
#               file variable, 17), wdthenelse (WRITE.DELETE.THEN.ELSE, 17), bpv (the X breakpoint control and @BPV, 6),
#               numexp (NUMERIC.EXPONENT, 27), forcereload (FORCE.RELOAD, 7), footpause (QUERY.FOOTER.PAUSE, 7),
#               pgheading (PAGINATE.ON.HEADING, 9) and mfilepath (INHERIT.MFILE.PATH, 8): the 45th to 53rd.
# 14 Oct 26 dm  --jobs N: a keyset per worker (SDBOX_KEYSET, sandbox-txnfail.py) and a queue.  The serial run was 50
#               minutes, 13 of them the sandbox builds; ALL_SUITES is now in the order of the times measured in the
#               run of 14 Oct (screen 613 s, ide 351, ced about 230, sed-menu 188, sed-edit 139, the rest under 100).
# 14 Oct 26 dm  --snapshot: the copy, its build and its removal are the script's own (the recipe above had been run by
#               hand each time).  Measured 14 Oct on a snapshot of the tree: 53 of 53 suites with --jobs 6 in 647 s,
#               screen (619 s) being the longest piece; the 38 free checks read installsdcore.sh and three documents
#               outside sdb_ai, which the old recipe did not copy (4 of 38 "failed" for that on the first run).
# 14 Oct 26 dm  listu-a5 (the user table: LISTU and !LISTU show the account, LISTU DETAIL, SYSTEM(1056), HSM counters,
#               PSTAT's wait time; 37 rows, about 80 s) and cmd-a9 (SHOW.LIST, .C-, LPTR and NO.PAGE on a catalogued name,
#               the command stack's account, CATALOG LOCAL's overwrite question, two ED fixes; 50 rows, 18 s): the 54th and 55th suites.
# 14 Oct 26 dm  lang-b45 (COMPARE's I, PRECISION INHERIT, INMAT() after MATBUILD / MATWRITE, the ~= operator; 31 rows, 18 s): the 56th.
# 14 Oct 26 dm  idx-nocase (CREATE.INDEX / MAKE.INDEX NO.CASE and BUILD.INDEX folding its keys; 10 rows) and trans-b43
#               (TRANS / RTRANS / XLATE on a file that will not open follow the X, V, C code; 15 rows): the 57th and 58th.
# 14 Oct 26 dm  csv-b5 (CSV.MODE mode, delim: the modes, the delimiter, SYSTEM(1043) / (1046), calls, EXECUTE, WRITECSV; 27 rows): the 59th.
# 14 Oct 26 dm  locate-b5 (the BY string of LOCATE takes C and N, the letters in any order; 15 rows): the 60th.
# 14 Oct 26 dm  noecho (INPUT, INPUT @ and INPUTFIELD take NO.ECHO; 17 rows): the 61st.
# 14 Oct 26 dm  flushdh (FLUSH.DH.CACHE, LOCAL, NO.WAIT: timed beside a napping process and one waiting at an INPUT; 9 rows, about 25 s): the 62nd.
# 14 Oct 26 dm  stacklist (EXECUTE ... STACKLIST keeps list 0, its remove pointer included, and puts it back; 11 rows): the 63rd.
# 14 Oct 26 dm  inputif (INPUTIF and INPUTIF @ on a pseudo-terminal: nothing waiting, type-ahead, the DATA queue; 10 rows): the 64th.
# 14 Oct 26 dm  inputraw (INPUT var, length RAW: exactly length characters, no interpretation of newline or erase; the length is required; 6 rows): the 65th.
# 14 Oct 26 dm  inputfill (INPUT var, length, fill and INPUT @ with a fill: the field painted with fill 1, fill 2 when done, the cursor
#               with a third; on a pty; 18 rows): the 66th.
# 14 Oct 26 dm  inputtrap (INPUTNULL and INPUTTRAP GOTO / GOSUB with INPUT @ and INPUTFIELD: the labels, a character past the end, the
#               GOSUB return, THEN / ELSE, scope, cancel, INPUTNULL's precedence; on a pty; 21 rows): the 67th.
# 14 Oct 26 dm  sselectv (SSELECTV file TO listvar {RIGHT.ALIGNED} {DESCENDING}: a sorted select into a select list variable; 12 rows): the 68th.
# 14 Oct 26 dm  epoch (EPOCH(), MVDATE(), MVTIME(), MVDATE.TIME(), MVEPOCH() in both forms, worked out from zoneinfo under UTC, Kathmandu and Los Angeles; 135 rows): the 69th.
# 14 Oct 26 dm  txnstatus (STATUS() after END TRANSACTION: 0 committed, 1021 rolled back, by ROLLBACK, by falling through, in a conditional and nested; 13 rows): the 70th.
# 14 Oct 26 dm  opensock (OPEN.SOCKET's timeout, against a listener whose accept queue is full; 8 rows): the 71st.
# 14 Oct 26 dm  dbgwatch (the debugger's WATCH var op value: every operator and word form, strings, MATCHES, UNWATCH, re-arming, refusals; 24 rows): the 76th.
# 14 Oct 26 dm  audit-b9b (the bug-fix audit, second sitting: !SORT of a select list variable - red 7 of 10 on the old !sort - a matrix redimensioned 400 times, a derived class, a read trigger catalogued LOCAL, a K entry over a V entry for a LOCAL catalogue item - red on the old cproc; 15 rows): the 77th.
# 15 Oct 26 dm  option-q17 (QM4 gaps bundle Q-17: the options GIT, DIR.DTM, KEEP.OLD.OBJECT, NO.PHANTOM.NOTIFY, SPOOL.COMMAND and ASSOC.ALL, each off then on; 29 rows): the 78th.
# 15 Oct 26 dm  mode-q16 (QM4 gaps bundle Q-16, the $MODE options: CHANGE.NO.OVERLAP, COUNT.OVERLAP, INDEX.OVERLAP, PICK.CONVERT, CONDITIONAL.STATEMENTS, TRAP.UNUSED.MAIN, PICK.SELECT, EXPLICIT, DEFAULT.UNASS.ARGS and default argument values; every mode has its control; 95 rows): the 79th.
# 15 Oct 26 dm  func-q1 (QM4 gaps bundle Q-1, the functions behind the one opcode XFUN: CEIL FLOOR ROUNDUP ROUNDDOWN IS.* LEFT RIGHT LAST LASTS NV NS TRIMWS MATCHESS MATCHFIELDS, the CASING statement, ARG.PRESENT (Q-7), BOOL IS.NULL NUMERIC REUSING (Q-6); the manual's own examples; 162 rows): the 80th.
# 15 Oct 26 dm  sys-q18 (QM4 gaps bundle Q-18, SYSTEM() keys 14, 19, 21, 45, 1048, 1049, 1067; each by a relation the program computes; 8 rows): the 81st.
# 15 Oct 26 dm  qproc-q20 (QM4 gaps bundle Q-20, the query processor keywords MEDIAN and RPT, each with the neighbouring keyword's figure as its control; 19 rows): the 82nd.
# 15 Oct 26 dm  list-q2 (QM4 gaps bundle Q-2, the select list statements FORMLISTV, GETLISTV, WRITELIST, MOVELIST and MOVELISTV, each read back with READNEXT; 29 rows): the 83rd.
# 15 Oct 26 dm  verbs-q8 (QM4 gaps bundle Q-8, the verb MOVE.LIST: what each list holds afterwards, KEEP, and what it refuses; 16 rows): the 84th.  LIST.PHANTOMS has five rows in listu-a5.
# 15 Oct 26 dm  inhibit-q8 (QM4 gaps bundle Q-8, the verb INHIBIT.LOGIN: the verb, an ordinary session refused and an administrator one not, a session already running untouched, the setter's phantom, a second ON refused, another administrator session switching it off, a killed setter ignored, the audit trail, and the S.50 backup hold of a killed session; 43 rows): the 85th.
# 15 Oct 26 dm  stmt-q3 (QM4 gaps, second sitting: DIGEST() against hashlib, SET.TIMEZONE / TIMEZONE against zoneinfo, KEEP.SELECT, FIND.FILE and FIND.PROGRAM against FILEINFO and !PROG_INFO, COMMAND.LOGGING, ANALYSE.INDEX, SET.MODE with the mode read from the disk, MATWRITECSV read back from the file, USPLIT with the sandbox restarted, SYSTEM(20); every feature with its off state or older behaviour as the control, then SELECT.SOCKET with a server, a client and the accepted connection in one session and SELECTINDEXV; 133 rows): the 86th.
# 15 Oct 26 dm  q4 (QM4 gaps, third sitting: BLOCK.PRINT / BLOCK.TERM against the pictures of the letters and the spooled job, FILE.STAT against FILEINFO, BSCAN / ROOT / KEY and SELECTLEFTV / SELECTRIGHTV on an index of known values, DISABLE.INDEX with the updates and the query checked, SWAPMARKS(), SYSTEM(1071) after OSREAD against STATUS, OPTION QUERY.MERGE.PRINT read from the print job, PHANTOM GROUP with SYSTEM(1073), the G in LISTU and the parent ending, @PSTAT read by PSTAT, SET.QUEUE / SP.ASSIGN against GETPU and the hold job, FSTAT.USER with counts of known operations and an idle session as the control; 115 rows): the 87th.
# 15 Oct 26 dm  qmclient (QM4 gaps bundle C-1, the QMClient API: a real local API session through the sandbox's sdclilib.so and a server process - SDRevision, SDGetVar, SDSystem, SDIndices, SDTrans, SDRTrans, each against a value got another way; and since the same day SDTxn and the non-durable nested COMMIT ($MODE NON.DURABLE.TXN, mode 4) with the durable program as the control, what reached the disk read by the next session; 50 rows): the 88th.
# 15 Oct 26 dm  qmclient grew to 148 rows (third QMClient sitting, with sequential files over the API and CREATING.SEQKEY as parts P and Q: SDEvaluate / SDEvalConv and SDIConv / SDOConv / SDIConvs / SDOConvs against values got another way, six sessions at once, a session waiting for input while another comes and goes, SDRecordlocked with a second session's lock, a killed server and a request to it with SIGPIPE at its default action, SDDcount and SDChange against SD's own DCOUNT() and CHANGE(), SDLogto, MASTER.LOGIN and LOGIN in order, the BASIC class's failed connect, and AUTOLOGOUT 1 with 70 s of idling against a session without it; it takes about 3 minutes).
# 15 Oct 26 dm  edseqkey (ED and SED take CREATING.SEQKEY in the place of a record id: ED through a pipe, SED on a pseudo-terminal; the id shown, the record and the counter read back from the disk by a BASIC probe, a directory file, a collection file and a read-only open refused, an ordinary id unchanged): the 89th.
# 15 Oct 26 dm  sdfixseq (the audit of the CREATING.SEQKEY counter: sdfix's H line for it, the writers of the header that keep it, a read-only write that does not use an id up, and a writer against an index being made and deleted): the 90th.
# 15 Oct 26 dm  fcontrol (the public FCONTROL(fvar, action {, qualifier}) with openQM's numbers, run by an ordinary program: the CREATING.SEQKEY counter, field access, FC$VALID.ID, FC$MINMOD, the refusals on a read only file and a directory file, FC$SYNC / FC$CRLF / an unknown action stopping the program with a message, and CONFIGURE.FILE NEXT through the renamed internal function): the 91st.
# 15 Oct 26 dm  selectv-mode ($MODE SELECTV, openQM 85: SELECT / SELECTV / SSELECTV with no TO and READNEXT with no FROM use the program's default select list variable; with a no-mode control for each, PICK.SELECT with it, a LOCAL SUBROUTINE and a CALLed one; 29 rows, red 23 of 29 on the old tree): the 92nd.
# 15 Oct 26 dm  listf-mult (LISTF / LISTFL / LISTFR, openQM 3 and 185: a line for each subfile of a multifile, WITH / WITHOUT TRIGGER, ENCRYPTION and REPLICATION; 23 rows, red 8 of 23 on the old tree, the WITHOUT rows being the ones that fail): the 93rd.
# 16 Oct 26 dm  q5 (QM4 gaps, 16 Oct sitting: the CLEANUP parameter with sdlnxd killing a session's row, PHANTOMS and PHANTOM USER n, kept user numbers skipped by sessions and phantoms, two kept blocks side by side; it starts the sandbox's sdlnxd itself, which the sandbox tool otherwise kills): the 90th.  Since the LOCK.TRACER rows it has 50 rows and runs about three minutes (measured in the 59-suite run of 16 Oct: 153 s).
# 16 Oct 26 dm  restricted (RESTRICTED var / SUBROUTINE / FUNCTION in a class module: the main program, an unrelated class and the child object refused, the child reaching its parent's restricted names, READONLY, the compile errors; 11 rows): the 91st.
# 16 Oct 26 dm  crlf (the line terminator modes of directory and sequential files, QM4 Fixes item 452: FCONTROL FC$CRLF and the VOC letters L C B X, READ and WRITE of a directory file in each mode against a whole-record reference, with records cut across the 31,744 byte chunk, READSEQ / WRITESEQ, image mode; the bytes on disk; 55 rows, red 50 of 55 on ac509e4) and dirtrig (triggers on directory files, QM4 Fixes item 177: SET.TRIGGER, the %header% file, every trigger mode in order, refusing and changing, what is not a record, WRITESEQ not calling it; 31 rows, 23 of the first 30 red on ac509e4): the 117th and 118th.
# 17 Oct 26 dm  sysexc (run time errors as SYS.* exceptions, exception groups, the rollback of a transaction begun inside a TRY clause, and SYS.PROGRAM.NO_PDEBUG: QM4 Fixes 354 and 513; 58 rows, red 49 of 58 on the tree before): the 119th.
# 17 Oct 26 dm  ltype (L-type dictionary records, links, in I-type expressions and queries: QM4 Fixes 7; links to links, to A, S and I items, a link's file expression, and what a wrong link says, and a link changed after an I-type was compiled; 32 rows, the first 27 red 19 of 27 on the tree before): the 120th.
# 17 Oct 26 dm  callfile (the Pick style CALL "file name": the program compiled into a VOC-named file, past the catalogue, no operating system path: QM4 Fixes 208; 18 rows, red 12 of 18 on 15e0f1c, the 6 passes being refusals the old code made too): the 121st.
# 17 Oct 26 dm  editgates (the edit gates voc.edit, bp.edit, dict.edit, S.64: every kind of change by an ordinary program, the verbs and editors that the kernel's own test lets through, the sequential routes, MODIFY.ACCOUNT, LOGTO, the upgrade walk, the manifest; 228 rows on a private SD, 139 of them red on the tree of a0a1ad6): the 122nd.
# 17 Oct 26 dm  net (the NET gate and the SDNet server definitions, S.65 slice 1: K$NET as a session holds it, LOGTO and OPTION STACKED.ACCOUNT, MODIFY.ACCOUNT NET-ON / NET-OFF, the manifest, and the SDSYS-only verbs set.server, list.servers and delete.server with the file netservers they keep - every invalid field refused with nothing written, replace asks, the limit of ten, an ordinary account refused; nothing opens a remote file yet; NOT YET RUN): the 123rd.
# 17 Oct 26 dm  netfile (the BASIC client class gpl.bp/sdclient against the Python fake API server, S.65 slice 3a: connect.keys, the login from the stored derived keys of set.netlogin - the pin checked before a byte is sent, the stored salt and count compared with the server's, a wrong ClientKey or ServerKey, the account - and the file requests the class makes, with the bytes it puts on the wire; connect(user, password) as the regression; a connection that closes or falls silent; a files-only login; record locks; no socket left open; an ordinary session runs a BASIC driver that obeys input lines; NOT YET RUN): the 124th.
# 18 Oct 26 dm  req29 added (API request 29, vb.open.sdnet, a real `sd -Q` server on pipes: with NETFILES bit 2 set it opened the file of an account the
#               caller may not LOGTO, a suspended one, one named by a path, one with the NET gate off, and under SDCLIENT=1; 16 rows, 5 red on the tree
#               before, the evidence the planted record read back from the disk).
# 19 Oct 26 dm  idedraw added (the owner's four IDE reports of 19 Oct: a click on the menu bar, what a choice writes to the terminal (the flash),
#               the pane named on the status line, the highlighted cursor cell; 32 rows on a private SD, 21 red on the tree before).
# 19 Oct 26 dm  eofkeys added (SED, the IDE and a user program's SCREEN WAIT ... TIMEOUT end when piped input ends; they spun at 100% CPU: the verifier's
#               F8 of the 140x42 branch; 16 rows on a private SD, 6 red on the tree before, each of the two fixes killed by exactly its own rows).
# 18 Oct 26 dm  ide-sed added (Part B of the 140x42 plan: Ctrl-E in the IDE hands the record to SED, SED's save returns with the new text, leaving
#               without saving returns unchanged, a changed buffer is saved first or the hand-over cancelled, the Go menu entry, End still ends a row,
#               a record locked by someone else opens read only; 26 rows on one pseudo-terminal).
# 18 Oct 26 dm  winsize, sed-small and ide-small added (the 140 by 42 terminal work: winsize is the default size of a session with no terminal and the
#               TERM answers, 42 rows; sed-small is SED refusing below 140 by 42, surviving a shrink and the cursor guard, 104 rows, pty-bound, about 4
#               minutes; ide-small is the same for the IDE, CED and the debugger's line-mode fallback, 154 rows, with mutants named in its header).
# 18 Oct 26 dm  qm4def added (two defects the QM4 evaluation noticed, reproduced and fixed: a user conversion code reaching a $ program, a print
#               unit's SPOOLER string run through system() by an ordinary account; 13 rows on a private SD, 4 of them red on the tree before the fix).
# 18 Oct 26 dm  shared (the shared account, S.66: a group account named shared whose files an account with the shared.read gate opens by NAME with no
#               LOGTO; shared.read ON when its register field is blank, shared.write OFF; record writes need shared.write, structure changes are SDSYS's
#               at a terminal, a shared dictionary needs dict.edit as well; the lookup rules, the audit line, list.shared, LOGTO into an account with the
#               gate off, compile, the gate words; written from the code, NEVER RUN when this line was added - see sandbox-shared.py): the 126th.
# 16 Oct 26 dm  --snapshot also copies deletesdcore.sh: test-newvocmods-units.py reads it, and in the snapshot it was missing, so the
#               free check answered CANNOT RUN and the run exited 1 (found in the audit of Fixes batch A; test-regress-units.py has the row).
# END-HISTORY

set -u

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TREE=$(dirname "$HERE")

# The suites, the longest first (measured 14 Oct 26), so that a queue shared by several workers ends together.
ALL_SUITES="screen ide ced sed-menu sed-edit sed-small ide-small ide-sed winsize syntax oq2 listu-a5 conf-b1 file-b8 lock-b6 dbgui footpause sys-b2 coll try qproc-a3 gates bcomp-a1 collfile fix-b10 edbug openzero pickrn mlmask chained execlist partial classas stdfil wdthenelse bpv numexp forcereload pgheading mfilepath dbgcoll akcase stmt-b5 func-b4 dict-a2 conv-b3 misc-a9 list-a7 input nocase callcase dictfold audit-b9 file-a8 option-a4 proc-a5 upgradenocase lang-a15 cmd-a9 lang-b45 idx-nocase trans-b43 csv-b5 locate-b5 noecho flushdh stacklist inputif inputraw inputfill inputtrap sselectv epoch txnstatus opensock dbgwatch audit-b9b option-q17 mode-q16 func-q1 sys-q18 qproc-q20 list-q2 verbs-q8 inhibit-q8 stmt-q3 q4 qmclient edseqkey sdfixseq fcontrol selectv-mode listf-mult q5 restricted dbgequ cll xml stacked prof qdefaults qproc-when vert-fmt vlist-a3 incsearch lockown sdaccts fixes-b12 dbgcase sortwide splitfull nameindex terminfo-ext resetall classinit sync getdev itypemode edext ospath crlf dirtrig sysexc ltype callfile editgates net netfile qm4def shared viewport crypt tools req29 eofkeys idedraw guide pack-examples"

ONLY=""
SKIP=""
FREE=0
SUITES_OFF=0
CHANGED=0
SINCE=""
LIST=0
LOGS=""
LIMIT=3000
JOBS=1
SNAPSHOT=0
SNAP=""

usage() {
  sed -n '2,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --tree) TREE=$(cd "$2" && pwd) || exit 2; shift 2 ;;
    --only) ONLY=$2; shift 2 ;;
    --skip) SKIP=$2; shift 2 ;;
    --free) FREE=1; shift ;;
    --no-suites) SUITES_OFF=1; shift ;;
    --changed) CHANGED=1; shift ;;
    --since) CHANGED=1; SINCE=$2; shift 2 ;;
    --list) LIST=1; shift ;;
    --logs) LOGS=$2; shift 2 ;;
    --limit) LIMIT=$2; shift 2 ;;
    --jobs) JOBS=$2; shift 2 ;;
    --snapshot) SNAPSHOT=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "regress: unknown argument '$1' (try --help)" >&2; exit 2 ;;
  esac
done

case "$JOBS" in
  [1-8]) ;;
  *) echo "regress: CANNOT RUN - --jobs must be 1 to 8 (there are eight keysets), not '$JOBS'" >&2; exit 2 ;;
esac

# --changed [--since REF]: the suites the changed files need, chosen by gplbld/regress-changed.py from gplbld/regress-map.txt.  Its
# report (every changed file, the rule that took it, what it selected) goes to the screen; a file no rule matches, or a change
# of nothing, stops the run (exit 2).  The free checks always run with it.  A change that needs no sandbox suite runs only those.
if [ $CHANGED -eq 1 ]; then
  if [ -n "$ONLY" ]; then echo "regress: --changed and --only are alternatives; give one" >&2; exit 2; fi
  [ -f "$TREE/gplbld/regress-changed.py" ] || { echo "regress: CANNOT RUN - $TREE/gplbld/regress-changed.py is not there" >&2; exit 2; }
  CHANGED_SUITES=$(python3 "$TREE/gplbld/regress-changed.py" ${SINCE:+--since "$SINCE"}) || exit 2
  FREE=1
  if [ -z "$CHANGED_SUITES" ]; then
    SUITES_OFF=1
    ONLY=""
  else
    ONLY=${CHANGED_SUITES// /,}
  fi
fi

if [ -n "$ONLY" ]; then SUITES=${ONLY//,/ }; elif [ $SUITES_OFF -eq 1 ]; then SUITES=""; else SUITES=$ALL_SUITES; fi
KEEP=""
for s in $SUITES; do
  skipped=0
  for k in ${SKIP//,/ }; do [ "$k" = "$s" ] && skipped=1; done
  [ $skipped -eq 0 ] && KEEP="$KEEP $s"
done
SUITES=${KEEP# }

# With more than one worker, a long suite that has parts of its own is cut into PIECES, <suite>~<part>+<part>, which run
# side by side: the piece's script is sandbox-<suite>.py and it is given --only=<part>,<part>.  The screen suite was the
# longest thing in the run (619 s of 647, 14 Oct 26) and its parts are independent (11 of them, 54 to 164 s each on a
# fresh build).  The pieces must cover the parts the suite runs by default: test-regress-units.py reads
# sandbox-screen.py and refuses a list that has drifted.  One worker runs the suite whole, as before.
declare -A PIECES
PIECES[screen]="dialogs mouse+resize forms+tabs memo+scroll+owned table+themes+events"
if [ "$JOBS" -gt 1 ]; then
  EXPANDED=""
  for s in $SUITES; do
    if [ -n "${PIECES[$s]:-}" ]; then
      for p in ${PIECES[$s]}; do EXPANDED="$EXPANDED $s~$p"; done
    else
      EXPANDED="$EXPANDED $s"
    fi
  done
  SUITES=${EXPANDED# }
fi

if [ $LIST -eq 1 ]; then
  for s in $SUITES; do echo "$s"; done
  exit 0
fi

if [ ! -d "$TREE/gplbld" ]; then
  echo "regress: CANNOT RUN - $TREE has no gplbld directory" >&2
  exit 2
fi

count=$(echo $SUITES | wc -w)
# No more workers than suites.
[ "$JOBS" -gt "$count" ] && [ "$count" -gt 0 ] && JOBS=$count

echo "regress: tree     $TREE"

# An unknown suite is a refusal, not a pass over nothing.
if [ $SUITES_OFF -eq 0 ]; then
  for s in $SUITES; do
    if [ ! -f "$TREE/gplbld/sandbox-${s%%~*}.py" ]; then
      echo "regress: CANNOT RUN - no suite '$s' ($TREE/gplbld/sandbox-${s%%~*}.py is not there)" >&2
      exit 2
    fi
  done
  if [ -z "$SUITES" ]; then
    echo "regress: CANNOT RUN - no suite is selected" >&2
    exit 2
  fi
  k=0
  while [ $k -lt "$JOBS" ]; do
    shm=$(printf '0x%08x' $((0x53434C91 + 0x20 * k)))
    sem=$(printf '0x%08x' $((0x53434C92 + 0x20 * k)))
    held=$(ipcs -m -s 2>/dev/null | grep -i -E "$shm|$sem" | head -2)
    if [ -n "$held" ]; then
      echo "regress: CANNOT RUN - a sandbox already holds the shared memory keys $shm/${sem#0x} (keyset $k of $JOBS):" >&2
      echo "$held" >&2
      echo "         stop it with  SDBOX_KEYSET=$k python3 $TREE/gplbld/sandbox-fromtree.py <its directory> stop  (or ipcrm -M $shm; ipcrm -S $sem if its directory is gone)" >&2
      exit 2
    fi
    k=$((k + 1))
  done
fi

RUN=$(mktemp -d "${TMPDIR:-/tmp}/sdregress.XXXXXX") || { echo "regress: CANNOT RUN - no scratch directory" >&2; exit 2; }
[ -n "$LOGS" ] || LOGS="$RUN/logs"
mkdir -p "$LOGS" || { echo "regress: CANNOT RUN - cannot make $LOGS" >&2; exit 2; }
CLAIMS="$RUN/claims"
mkdir -p "$CLAIMS"
echo "regress: logs     $LOGS"

WORKERS=""
trap 'for w in $WORKERS; do kill -TERM "$w" 2>/dev/null; done; wait; [ -n "$SNAP" ] && rm -rf "$SNAP"; echo "regress: interrupted" >&2; exit 2' INT TERM

# --snapshot: a copy of the tree, built, in which the suites run.  rsync gets the files git knows (tracked, and new
# ones that are not ignored); the build wants the one ignored header; the --free checks read four files at the top of
# the repository.  The copy is removed when the run ends.
if [ $SNAPSHOT -eq 1 ]; then
  command -v rsync >/dev/null 2>&1 || { echo "regress: CANNOT RUN - --snapshot needs rsync" >&2; exit 2; }
  REPO=$(git -C "$TREE" rev-parse --show-toplevel 2>/dev/null) || { echo "regress: CANNOT RUN - --snapshot needs $TREE inside a git work tree" >&2; exit 2; }
  if [ "$(cd "$TREE" && pwd -P)" != "$REPO/sdb_ai/sd64" ]; then
    echo "regress: CANNOT RUN - --snapshot wants the tree to be <repository>/sdb_ai/sd64, and it is $TREE (repository $REPO)" >&2
    exit 2
  fi
  SNAP="$RUN/snap"
  mkdir -p "$SNAP"
  (cd "$REPO" && git ls-files -z --cached --others --exclude-standard sdb_ai | rsync -a --from0 --files-from=- ./ "$SNAP"/) \
    || { echo "regress: CANNOT RUN - the copy of the tree failed" >&2; rm -rf "$SNAP"; exit 2; }
  if [ -f "$TREE/gplsrc/sdext_python_inc.h" ]; then
    mkdir -p "$SNAP/sdb_ai/sd64/gplsrc"
    cp "$TREE/gplsrc/sdext_python_inc.h" "$SNAP/sdb_ai/sd64/gplsrc/"
  else
    echo "regress: note - $TREE/gplsrc/sdext_python_inc.h is not there, so the build may fail" >&2
  fi
  for f in installsdcore.sh deletesdcore.sh PROJECT_STATUS.md PRE_RELEASE_FIXES.md PORT_ADOPTION.md; do
    [ -f "$REPO/$f" ] && cp "$REPO/$f" "$SNAP/$f"
  done
  if ! (cd "$SNAP/sdb_ai/sd64" && make > "$LOGS/snapshot-make.log" 2>&1); then
    echo "regress: CANNOT RUN - make failed in the snapshot (see $LOGS/snapshot-make.log)" >&2
    rm -rf "$SNAP"
    exit 2
  fi
  TREE="$SNAP/sdb_ai/sd64"
  echo "regress: snapshot $SNAP"
fi

declare -A IDX
i=0
for s in $SUITES; do i=$((i + 1)); IDX[$s]=$i; done

# --- one suite -----------------------------------------------------------------------------------------------------
# run_suite <suite> <keyset>: build and run it in a fresh directory, stop and remove that, print its line and write its
# verdict to $LOGS/<suite>.verdict (status, passed, seconds, why - tab separated), which the end of the run tallies.
W_DIR=""
W_KS=0
CHILD=""

run_suite() {
  local s=$1 ks=$2 log verdict passed failed why status t1 rc secs line rows only=""
  W_DIR="$RUN/sbx-$s"
  W_KS=$ks
  log="$LOGS/$s.out"
  # a piece: <suite>~<part>+<part> runs sandbox-<suite>.py --only=<part>,<part>
  case "$s" in *~*) only="--only=$(echo "${s#*~}" | tr '+' ',')" ;; esac
  t1=$(date +%s)
  timeout "$LIMIT" python3 "$TREE/gplbld/sandbox-${s%%~*}.py" "$W_DIR" --build $only > "$log" 2>&1 &
  CHILD=$!
  wait "$CHILD"
  rc=$?
  CHILD=""
  python3 "$TREE/gplbld/sandbox-fromtree.py" "$W_DIR" stop >/dev/null 2>&1
  rm -rf "${W_DIR:?}"
  W_DIR=""
  secs=$(( $(date +%s) - t1 ))

  # The suite's own last line: "sandbox-NAME: N passed, M failed" - and nothing else is taken as a verdict.
  verdict=$(grep -E '^sandbox-[A-Za-z0-9._-]+: [0-9]+ passed, [0-9]+ failed' "$log" | tail -1)
  passed=0
  failed=0
  if [ -n "$verdict" ]; then
    passed=$(echo "$verdict" | sed -E 's/^[^:]+: ([0-9]+) passed, ([0-9]+) failed.*/\1/')
    failed=$(echo "$verdict" | sed -E 's/^[^:]+: ([0-9]+) passed, ([0-9]+) failed.*/\2/')
  fi

  why=""
  if [ "$rc" -eq 2 ] || grep -q 'CANNOT RUN' "$log"; then
    status="NOT RUN"
    why=$(grep -m1 'CANNOT RUN' "$log" | cut -c1-110)
    [ -n "$why" ] || why="exit $rc"
  elif [ -z "$verdict" ]; then
    status="FAIL"
    why="no verdict line (exit $rc)"
  elif [ "$rc" -ne 0 ]; then
    status="FAIL"
    why="exit $rc"
  elif [ "$failed" -ne 0 ]; then
    status="FAIL"
    why="$failed failed"
  elif [ "$passed" -eq 0 ]; then
    status="FAIL"
    why="no row passed"
  else
    status="PASS"
  fi

  line=$(printf '[%2d/%d] %-20s %-8s %5s passed  %4d s  %s' "${IDX[$s]}" "$count" "$s" "$status" "$passed" "$secs" "$why")
  rows=""
  if [ "$status" = "FAIL" ]; then
    rows=$(grep -E '\[FAIL\]' "$log" | head -5 | cut -c1-200 | sed 's/^/         /')
  fi
  # One write, so that the lines of two workers do not mix.
  printf '%s\n' "$line${rows:+$'\n'$rows}"
  printf '%s\t%s\t%s\t%s\n' "$status" "$passed" "$secs" "$why" > "$LOGS/$s.verdict"
}

# A worker is a subshell with its own keyset: it takes the next suite nobody has claimed (mkdir is the claim, and is
# atomic) and runs it, until none is left.
worker_abort() {
  [ -n "$CHILD" ] && kill -TERM "$CHILD" 2>/dev/null
  if [ -n "$W_DIR" ]; then
    SDBOX_KEYSET=$W_KS python3 "$TREE/gplbld/sandbox-fromtree.py" "$W_DIR" stop >/dev/null 2>&1
    rm -rf "${W_DIR:?}"
  fi
  exit 2
}

worker() {
  local ks=$1 s
  export SDBOX_KEYSET=$ks
  trap worker_abort TERM
  for s in $SUITES; do
    mkdir "$CLAIMS/$s" 2>/dev/null || continue
    run_suite "$s" "$ks"
  done
  exit 0
}

total=0
passed_suites=0
failed_suites=0
notrun_suites=0
failed_list=""
notrun_list=""
T0=$(date +%s)

if [ $SUITES_OFF -eq 0 ]; then
  echo "regress: suites   $count:$(for s in $SUITES; do printf ' %s' "$s"; done)"
  echo "regress: each     python3 $TREE/gplbld/sandbox-<suite>.py <fresh directory> --build   ($JOBS worker$([ "$JOBS" -gt 1 ] && echo s), keysets 0-$((JOBS - 1)))"
  echo
  k=0
  while [ $k -lt "$JOBS" ]; do
    worker $k &
    WORKERS="$WORKERS $!"
    k=$((k + 1))
  done
  for w in $WORKERS; do wait "$w"; done

  # The tally, in the order of the list, from what each suite wrote - not from what the workers said.
  for s in $SUITES; do
    status=""
    if IFS=$'\t' read -r status passed secs why < "$LOGS/$s.verdict" 2>/dev/null && [ -n "$status" ]; then
      :
    else
      status="NOT RUN"; passed=0; secs=0; why="no verdict was written (the worker ended)"
      printf '[%2d/%d] %-20s %-8s %5s passed  %4d s  %s\n' "${IDX[$s]}" "$count" "$s" "$status" "$passed" "$secs" "$why"
    fi
    total=$((total + secs))
    case "$status" in
      PASS) passed_suites=$((passed_suites + 1)) ;;
      FAIL)
        failed_suites=$((failed_suites + 1))
        failed_list="$failed_list $s"
        ;;
      *)
        notrun_suites=$((notrun_suites + 1))
        notrun_list="$notrun_list $s"
        ;;
    esac
  done
fi
rm -rf "$CLAIMS"

free_failed=0
free_ran=0
if [ $FREE -eq 1 ]; then
  echo
  echo "regress: free checks  (gplbld/test-*.py, run from $TREE)"
  for t in "$TREE"/gplbld/test-*.py; do
    [ -f "$t" ] || continue
    free_ran=$((free_ran + 1))
    if ! (cd "$TREE" && timeout 180 python3 "$t" > "$LOGS/$(basename "$t").out" 2>&1); then
      free_failed=$((free_failed + 1))
      echo "         FAIL $(basename "$t")   (see $LOGS/$(basename "$t").out)"
    fi
  done
  [ "$free_ran" -gt 0 ] || { echo "         no test-*.py found"; free_failed=$((free_failed + 1)); }
  echo "regress: free checks  $free_ran run, $free_failed failed"
fi

echo
elapsed=$(( $(date +%s) - T0 ))
if [ $SUITES_OFF -eq 0 ]; then
  echo "regress: $count suites: $passed_suites passed, $failed_suites failed${failed_list:+ ($failed_list )}, $notrun_suites not run${notrun_list:+ ($notrun_list )}; $total s in the suites, $elapsed s in all${JOBS:+ ($JOBS worker$([ "$JOBS" -gt 1 ] && echo s))}"
fi

[ -n "$SNAP" ] && rm -rf "$SNAP"
rmdir "$RUN/logs" 2>/dev/null
if [ "$LOGS" != "$RUN/logs" ]; then rmdir "$RUN" 2>/dev/null; fi

if [ "$failed_suites" -gt 0 ] || [ "$free_failed" -gt 0 ]; then exit 1; fi
if [ "$notrun_suites" -gt 0 ]; then exit 2; fi
exit 0

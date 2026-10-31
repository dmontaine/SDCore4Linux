* CREATEACC.H
* Settings positions for !create_account (S.50).
*
* START-HISTORY:
* 01 Oct 26 dm Written for S.50, BACKUP.ACCOUNT / RESTORE.ACCOUNT.  SHARED WITH
*              SD CORE FOR WINDOWS BYTE FOR BYTE (agreed by mail, 2026-10-01T0025):
*              Linux writes this file and the Windows port copies it.  Change it
*              here first, and mail the change.
* 02 Oct 26 dm CA$REUSE.SD.USER is read by both ports (Windows reuses with a
*              new password - owner's ruling that day); comment only.
* 17 Oct 26 dm S.65 slice 1: CA$NET (35), Linux only, the NET gate (as CA$VOC.EDIT etc. of S.64).
* 17 Oct 26 dm S.65 slice 2c: CA$FILES (36), Linux only, membership of the group sdfiles.
* 18 Oct 26 dm S.66: CA$SHARED.READ.OFF (37) and CA$SHARED.WRITE (38), Linux only, the shared-account gates.  Windows ignores
*              the Linux block (31-40) and defines neither; the mail to the Windows agent is deferred (sequential order of 11 Oct).
* 18 Oct 26 dm S.65 write group: CA$FILESWRITE (39), Linux only, membership of the group sdfileswrite (needs CA$FILES).  Same block, same deferral.
* 26 Oct 26 dm S.75, home: CA$START (42) and CA$PINS (43), Linux only, where the new account starts and whether it may add programs of its own to its home screen.  The Linux block
*              ran past 40 on 23 Oct (CA$AI, 41) and is 31-50 here.  Same deferral: mail the Windows agent when the Linux side is stable.
* 28 Oct 26 dm S.88 plan 2.9 (D2): CA$RECOVERY (44), Linux only, whether a new user account's editors keep a recovery copy of unsaved text.  Same block, same deferral.
* END-HISTORY
*
* START-DESCRIPTION:
*
*    call !create_account(acc.type, acc.name, settings, err)
*
*    settings is a dynamic array with one setting per FIXED field position, so
*    either port can add a setting of its own without changing the signature.
*    A blank field takes the default.  A port ignores the other port's block.
*
*       1-8    shared
*       9-20   reserved for future shared settings
*       21-30  SD Core for Windows only
*       31-50  SD Core for Linux only
*
* END-DESCRIPTION
*
* START-CODE

$define CA$PATH            1     ;* OTHER: the account's pathname; blank = default parent
$define CA$DESC            2     ;* Description, written to ACCOUNTS field 2
$define CA$ROUTE.SSH       3     ;* 1 / 0; blank = on (the default for a USER account)
$define CA$ROUTE.API       4     ;* 1 / 0; blank = on
$define CA$MEMBERS         5     ;* GROUP: member user names, value-mark separated
$define CA$ATTACH          6     ;* 1 = attach an existing OS user (install only)
$define CA$NO.QUERY        7     ;* 1 = ask nothing (refused for a new USER: password)
$define CA$SUSPENDED       8     ;* 1 = create the account suspended

$define CA$OS.SH          21     ;* Windows only: os.users field 1
$define CA$OS.EXECUTE     22     ;* Windows only: os.users field 2

* READ BY BOTH PORTS (it sits in the Linux block because Linux added it first):
* 1 = an OS user that SD itself created may be taken over instead of refused.
* RESTORE.ACCOUNT sets it.  Linux: the user keeps its Linux password ($cred is
* separate and is not written).  Windows (owner's ruling, 2 Oct 2026): the
* user is reused WITH A NEW PASSWORD, which sets the Windows password and
* $cred together.
$define CA$REUSE.SD.USER  31

* Linux only (17 Oct 26, S.64, the edit gates): 1 = the new account starts with the gate on.  A blank or a 0 is off.
$define CA$VOC.EDIT       32     ;* ACC$VOC.EDIT  'yes'
$define CA$BP.EDIT        33     ;* ACC$BP.EDIT   'yes'
$define CA$DICT.EDIT      34     ;* ACC$DICT.EDIT 'yes'

* Linux only (17 Oct 26, S.65 slice 1, the NET gate for SDNet): 1 = the new account starts with the gate on.  A blank or a 0 is off.
* The gate takes effect for the remote-file slices that follow and does nothing yet.
$define CA$NET            35     ;* ACC$NET 'yes'
$define CA$FILES          36     ;* 1 = start in the group sdfiles, the SDNet files-only API route (Linux only; S.65 slice 2c)

* Linux only (18 Oct 26, S.66, the shared account).  Both are requests only when exactly 1; anything else leaves the default.
* CA$SHARED.READ.OFF is INVERTED because the delivered default of shared.read is ON (a blank register field means yes).
$define CA$SHARED.READ.OFF 37    ;* 1 = the new account starts with ACC$SHARED.READ 'no' (withdrawn)
$define CA$SHARED.WRITE    38    ;* 1 = the new account starts with ACC$SHARED.WRITE 'yes'

* Linux only (18 Oct 26, S.65 write group): 1 = also join the Linux group sdfileswrite, so a files-only login can change files on this server.  Needs CA$FILES.
$define CA$FILESWRITE      39    ;* 1 = start in the group sdfileswrite (with CA$FILES; S.65 write group)

* Linux only (21 Oct 26, S.73 item 3): 1 = also join the Linux group sdfilesadmin, so a files-only login may administer files on this server.  Needs CA$FILES and CA$FILESWRITE.
$define CA$FILESADMIN      40    ;* 1 = start in the group sdfilesadmin (with CA$FILES and CA$FILESWRITE; S.73 item 3)

* Linux only (23 Oct 26, S.69 step 2): 1 = also join the Linux group sdaiusers, the right to use the AI provider's API through the helper sd-ai.  Stands alone.
$define CA$AI              41    ;* 1 = start in the group sdaiusers (S.69 step 2)

* Linux only (26 Oct 26, S.75, the home screen).  CA$START is a request only when it is exactly menu or terminal (lower case): the new account's ACC$START is that word; anything else
* is refused before anything is made.  Blank leaves the account following the system default (SET.START.DEFAULT).  CA$PINS is a request only when exactly 1 (off unless named): the
* new account's ACC$PINS is 'yes', the person may add programs of their own to their home screen (MY.MENU); blank or 0 leaves it off.
$define CA$START           42    ;* menu / terminal; blank = follow the system default
$define CA$PINS            43    ;* 1 = the new account starts with ACC$PINS 'yes'

* Linux only (28 Oct 26, S.88 plan 2.9, D2): 1 = the new USER account starts with ACC$RECOVERY 'yes' (its editors keep a recovery copy of unsaved text).  Blank or 0 leaves it off.
*   Refused for a group or other account (11771).
$define CA$RECOVERY        44    ;* 1 = the new account starts with ACC$RECOVERY 'yes'

* Linux only (30 Oct 26, S.92, TAPE.IMPORT): the account is FILLED by a subroutine while its directory is still the sdsys user's, before the VOC and the files it made are handed to
*   the account's user.  CA$AFTER is the subroutine's name and only '!tape_fill' is accepted; CA$AFTER.ARG is one string handed to it.  Refused (11919) for an ATTACHed user, a reused user,
*   the shared account and any type but USER and GROUP, before anything is made, because a failed fill removes what THIS call made and nothing else.  The subroutine is called
*   call !tape_fill(pathname, arg, made, ferr)
*   and returns in made the pathnames (field-mark separated, every one inside pathname) of the files and directories it created, which are handed over one by one, and in ferr a message number
*   and its arguments as err has them, or blank.  A refusal removes the directory, the Linux user with its home and the groups this call made (11920), or says what stays (11921).
$define CA$AFTER           45    ;* '!tape_fill': fill the new account before it is handed over (S.92)
$define CA$AFTER.ARG       46    ;* the argument for that subroutine; its parts are value-mark separated here and arrive field-mark separated

* END-CODE

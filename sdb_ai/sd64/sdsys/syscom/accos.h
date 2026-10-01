* ACCOS.H
* SD Core for Linux's own commands for the S.50 per-OS helpers.
*
* START-HISTORY:
* 01 Oct 26 dm Written for S.50.  LINUX ONLY - the Windows port has no copy.
*              The two commands live here, once, so the helpers cannot drift
*              apart and so gplbld's sandbox can point them at stand-ins by
*              patching this one file in its own copy of the tree.
* END-HISTORY
*
* START-CODE

* The privileged helper, through the sdsys user's one sudoers grant.
$define ACCOS$ELEVATE      'sudo /usr/local/sbin/sd-elevate'

* The archive tool run without root (count of a staged tree, extract).
$define ACCOS$ARCHIVER     'python3 /usr/local/sbin/sd-accarchive'

* END-CODE

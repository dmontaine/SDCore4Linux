/* SD_SFTP.H
 * File transfer over the ssh login (RECEIVE / SEND): the transfer server inside sd.
 * Copyright (c) 2026 The SD Developers, All Rights Reserved.  GNU General Public License version 3 or later, as the rest of SD.
 *
 * START-HISTORY:
 * 15 Nov 26 dm  S.242 stage 3: new.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * SD_SFTP_SUBSYSTEM is the name gplbld/ssh-forcecommand.sh gives the sftp subsystem in the ordinary Match arm (its SFTP_CMD).
 * Nothing exists at that path.  sshd hands it to the arm's ForceCommand (sd) as SSH_ORIGINAL_COMMAND, and that exact string,
 * with no terminal and SSH_CONNECTION set, is how sd knows an sftp request from a login.  gplbld/test-sftp-units.py holds the
 * two spellings together.
 *
 * END-DESCRIPTION
 */

#ifndef SD_SFTP_H
#define SD_SFTP_H

#define SD_SFTP_SUBSYSTEM "/usr/local/sdsys/bin/sd-sftp"

/* The slot a session opens with RECEIVE or SEND (USER_ENTRY.xfer_dir) */
#define XFER_NONE 0
#define XFER_IN   1 /* RECEIVE: files come in, to <account>/xfer.in */
#define XFER_OUT  2 /* SEND: files go out, from <account>/xfer.out */

#define XFS_OVERWRITE 0x01 /* USER_ENTRY.xfer_flags: RECEIVE OVERWRITE, an incoming name may replace a file that is there */

void xfer_detect(int argc);                             /* sd.c main(), first: is this process an sftp request? */
void k_xfer(DESCRIPTOR* descr, DESCRIPTOR* result);     /* op_kernel.c: KERNEL(K$XFER, ...) */

#endif

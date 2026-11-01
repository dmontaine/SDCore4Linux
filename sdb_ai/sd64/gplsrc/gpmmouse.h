/* GPMMOUSE.H
 * The Linux console's mouse through the gpm daemon (gpmmouse.c, S.94, 31 Oct 26).
 * Copyright (c) 2026, SD Core for Linux.  This program is free software; you can redistribute
 * it and/or modify it under the terms of the GNU General Public License, version 3 or later.
 */

int gpm_enable(void);
void gpm_disable(void);
int gpm_fd(void);
int gpm_peek_report(char *buf);
void gpm_report_done(void);

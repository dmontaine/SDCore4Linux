#!/bin/sh
# sudo-stub.sh - a stand-in for sudo, copied by the sandbox harness (sandbox-tk-base.py, install_sudo_stub) into a private directory that is put FIRST in PATH, as a file called `sudo`
# (S.85, 28 Oct 2026).  With the real helper present on the host, `sudo /usr/local/sbin/sd-elevate ...` (gpl.bp/remoteapi, remotessh, settings_os through accos.h, acc_os_bakdir, acc_archive)
# makes sudo-rs ask the sandbox user for a password and the page waits on it.  This fails at once, as sudo-rs did when the helper was not there: the same two lines as
# .claude/fake-sudo-stub.sh (private; test-sudostub-units.py holds the two equal when that file is present), kept here because a --snapshot copy of the tree holds only sdb_ai.
echo "sudo: '$1': command not found" >&2
exit 1

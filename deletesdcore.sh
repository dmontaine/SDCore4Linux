#!/bin/bash
#
# SD bash delete script
#   (c) 2023-2026 Donald Montaine and Mark Buller
#   This software is released under the Blue Oak Model License
#   a copy can be found on the web here: https://blueoakcouncil.org/license/1.0.0
#
#   rev 2.0  Mar 15 2026 mab - echo -e to printf
#   - prior history suppressed
#
#   26 Oct 2026 dm - W.11 F11: the immutable attribute the installer puts on
#   bin (so that the sdsys user cannot replace the directory root runs
#   sd, sdlnxd and sdidx from) is lifted before the system directory is removed.
#
#   18 Oct 2026 dm - S.66: the group sdg_shared (the shared account's group)
#   is removed on a full DELETE and kept when the accounts are kept.
#
#   18 Oct 2026 dm - S.65 write group: the route group sdfileswrite goes with
#   sdfiles on a full DELETE and is kept when the accounts are kept.
#
#   21 Oct 2026 dm - S.73 item 3: so does the route group sdfilesadmin.
#
#   17 Oct 2026 dm - S.65 slice 2c: the route group sdfiles (the SDNet
#   files-only API route) is removed with sdssh and sdapi on a full DELETE and
#   kept when the accounts are kept.
#
#   09 Oct 2026 - the listing of the saved accounts after "sudo cp -r" is
#   "sudo ls": the copy is made by root and came out root:root 0750 on the Ubuntu
#   26.04 release VM (measured; why that mode was not established, a 027 umask
#   would do it), so the bare "ls" run as the
#   ordinary user failed with "Permission denied" and, under "set -e", ended the
#   whole delete after the accounts were saved and before anything was removed.
#   Found on the release VM; the listing is informational only.
#
#   15 Sep 2026 - the API's TLS server identity (/etc/sd-tls) is kept when the
#   accounts are kept, and removed only on a full DELETE.  A reinstall that
#   keeps your database now keeps the server's identity with it.
#
#   13 Sep 2026 - the account register is sdsys/accounts on disk (plan M3 D1),
#   so a kept register is saved as /home/sd/accounts, the name installsdcore.sh
#   restores.  An install from before the rename has sdsys/ACCOUNTS, which this
#   does not look for: no install needs carrying across (owner, 12-13 Sep) -
#   take the delete-accounts path instead.
#

# Modified by Composer AI - 2026/06/10.
# Enable strict mode and predictable word splitting for safer uninstall.
# set -e
# set -u
# set -o pipefail
# IFS=$'\n\t'
set -euo pipefail
IFS=$'\n\t'
# --------------------

# Define color codes as variables
# note 90–97 Set bright foreground color aixterm (not in standard)
# 91 - bright RED
# 92 - bright GREEN
# 93 - bright YELLOW
# for now stick with standard
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
#
NC='\033[0m' # No Color (reset)

sdsysdir="/usr/local/sdsys"
systemd_dir="/usr/lib/systemd/system"
acct_path="/home/sd"

if [[ $EUID -eq 0 ]]; then
    printf "%bThis script must NOT be run as root.%b\n" "$RED" "$NC" 1>&2
    # exit
    exit 1
fi
if [ -f "${sdsysdir}/bin/sd" ]; then
    echo
else
    printf "%bSD is not installed!\n" "$RED"
    printf "This script will not run.%b\n" "$NC"
    # exit
    exit 1
fi
#
clear
printf "%bREMOVE the SD Database Package\n" "$RED"
echo    "---------------------------------------"
printf "%b\n" "$YELLOW"
# Modified by Composer AI - 2026/06/10.
# Use read -r so backslashes in input are not interpreted.
# read -p "Continue? (y/N) " yn
read -r -p "Continue? (y/N) " yn
# --------------------
case $yn in
     [yY] ) echo;;
     [nN] ) exit 0;;
         *) exit 0 ;;
esac

echo
echo "If requested, enter your account password:"
# Modified by Composer AI - 2026/06/10.
# Refresh sudo credentials with sudo -v instead of sudo date.
# sudo date &>/dev/null
sudo -v
# --------------------

# Modified by Composer AI - 2026/06/10.
# Ensure /home/sd exists before account or configuration backups.
# (no mkdir here in original script)
sudo mkdir -p "$acct_path"
# --------------------

echo
printf "%bDo you want to save your existing accounts.\n" "$GREEN"
echo "WARNING: Entering 'N' will delete all your existing accounts."
echo         
printf "%b\n" "$YELLOW"
keep_accts='KEEP'
# Modified by Composer AI - 2026/06/10.
# read -p "Keep your existing accounts? (Y/n) " yn
read -r -p "Keep your existing accounts? (Y/n) " yn
# --------------------
case $yn in
    [yY] ) echo
           echo Accounts Directory Saved
           # Modified by Composer AI - 2026/06/10.
           # sudo cp -r /usr/local/sdsys/ACCOUNTS /home/sd
           # ls /home/sd/ACCOUNTS;;
           sudo cp -r "${sdsysdir}/accounts" "$acct_path"
           sudo ls "$acct_path/accounts";;
    [nN] ) echo
           # Modified by Composer AI - 2026/06/10.
           # read -p 'Enter "DELETE" to confirm deletion of Accounts ' keep_accts
           read -r -p 'Enter "DELETE" to confirm deletion of Accounts ' keep_accts
           # --------------------
           if [ "$keep_accts" = "DELETE" ]; then
               echo /home/sd Directory Deleted
               sudo rm -fr "$acct_path"
           else
               echo Accounts Directory Saved
               sudo cp -r "${sdsysdir}/accounts" "$acct_path"
               sudo ls "$acct_path/accounts"
           fi
           ;;
    *)     echo
           echo Accounts Directory Saved
           sudo cp -r "${sdsysdir}/accounts" "$acct_path"
           sudo ls "$acct_path/accounts";;
esac

echo
echo
printf "%bDo you want to save your existing SD configuration.\n" "$GREEN"
echo "WARNING: Entering 'N' will delete your current configuration."
echo        
printf "%b\n" "$YELLOW"
# Modified by Composer AI - 2026/06/10.
# Standardize prompt handling with read -r and [yY] matching.
# read -p "Keep your existing configuration? (Y/n) " yn
read -r -p "Keep your existing configuration? (Y/n) " yn
# --------------------
# 10 Sep 26  PRE_RELEASE 26 - /home/sd MUST BE A DIRECTORY FOR THE MOVE BELOW.
#            Answering DELETE to the accounts question removes /home/sd, and
#            "mv /etc/sd.conf /home/sd" then does not fail - it RENAMES the
#            file to /home/sd, because the destination directory is gone.  The
#            delete looks successful and the next install dies at
#            "mkdir -p /home/sd/user_accounts" with "Not a directory".  Both
#            were measured in a sandbox, 10 Sep 26.  Recreating the directory
#            here makes the saved config land where the installer looks for it
#            (/home/sd/sd.conf); when the accounts were kept, this is a no-op.
sudo mkdir -p "$acct_path"
conf_deleted=no
case $yn in
    [yY] ) echo
           sudo mv /etc/sd.conf "$acct_path"
           echo Configuration file saved;;
    [nN] ) echo
           conf_deleted=yes
           echo Configuration file will be deleted;;
     *)    echo
           sudo mv /etc/sd.conf "$acct_path"
           echo Configuration file saved;;
esac
printf "%b\n" "$NC"

# 14 Nov 26  THE API ACROSS AN UPGRADE (owner, 14 Nov 2026: "those questions should not be asked during an upgrade if the config file has been saved.  If
#            closed they stay closed, if open they stay open").  This script takes the API's firewall rule out and the installer writes the socket unit
#            fresh, local only.  So, when the configuration is kept, an API that listens for other computers (systemd's own answer for the socket, which
#            sees REMOTE.API's drop-in too) is noted in /home/sd/api-access.saved - the word open, root's, mode 600 - and the installer opens it again.
#            When the configuration is deleted, REMOTE.API's drop-in goes as well: it outlived every uninstall before, so a fresh install that said
#            "local" could listen for other computers.  ssh needs nothing: this script leaves sshd and port 22 alone.  test-install-keepaccess.sh runs it.
# API-SAVE-BEGIN
sudo rm -f "$acct_path/api-access.saved"
if [ "$conf_deleted" = no ]; then
    case " $(systemctl show -p Listen --value sdclient.socket 2>/dev/null | tr '\n' ' ' || true) " in
        *" 0.0.0.0:4247 "*|*" [::]:4247 "*|*" *:4247 "*)
            if echo open | sudo tee "$acct_path/api-access.saved" > /dev/null && sudo chmod 600 "$acct_path/api-access.saved"; then
                echo "Saved: API access from other computers is open, and the next install keeps it open."
            else
                echo "WARNING: could not note that API access is open; after the next install open it with:  remote.api on"
            fi ;;
    esac
elif sudo test -e /etc/systemd/system/sdclient.socket.d/sd-remote-api.conf; then
    sudo rm -f /etc/systemd/system/sdclient.socket.d/sd-remote-api.conf
    sudo rmdir /etc/systemd/system/sdclient.socket.d 2>/dev/null || true
    echo "Removed the API listener setting REMOTE.API wrote (/etc/systemd/system/sdclient.socket.d/sd-remote-api.conf)."
fi
# API-SAVE-END

# 19 Oct 26 dm - THE STORED SDNET LOGINS (SDNet audit K8e; owner, 19 Oct 2026: "if accounts OR config is deleted then sdnet credentials are deleted,
#            only if both are retained should the sdnet info be retained").  /var/lib/sd-net/<user> holds, for every user who ran set.netlogin, the
#            ClientKey and ServerKey of a remote server: as good as that server's password, and outside the account directory on purpose, so no
#            DELETE of an account reached it.  They are removed when the accounts were deleted (the DELETE answer) or the configuration was
#            deleted (the N answer), and kept only when BOTH were kept; either way the script says which.  test-delete-sdnet.sh runs this block.
# SDNET-LOGINS-BEGIN
if [ "$keep_accts" = "DELETE" ] || [ "$conf_deleted" = yes ]; then
    if sudo test -d /var/lib/sd-net; then
        sudo rm -rf /var/lib/sd-net
        echo "Removed /var/lib/sd-net (every user's stored SDNet logins), because the accounts or the configuration were deleted."
    fi
else
    if sudo test -d /var/lib/sd-net; then
        echo "Kept /var/lib/sd-net (the stored SDNet logins), because both the accounts and the configuration were kept."
    fi
fi
# SDNET-LOGINS-END

# Modified by Composer AI - 2026/06/10.
# Stop SD and systemd services before removing binaries and unit files.
# remove the /usr/sdsys directory
# sudo rm -fr /usr/local/sdsys
# ...
# cd /usr/lib/systemd/system
# stop services (was here, after rm)
sudo "${sdsysdir}/bin/sd" -stop 2>/dev/null || true
# 25 Oct 26 dm - the audit daemon's own unit (sd-lnxd.service) first, so that it is not restarted while SD is being taken down.  It has no [Install] section
#   (sd.service wants it), so there is nothing to disable.
sudo systemctl stop sd-lnxd.service 2>/dev/null || true
sudo systemctl stop sd.service sdclient.socket 2>/dev/null || true
sudo systemctl disable sd.service sdclient.socket 2>/dev/null || true
# 23 Oct 26 dm - S.69 step 2: and the AI helper's socket (the units are removed with the others below).
sudo systemctl stop sd-ai.socket 2>/dev/null || true
sudo systemctl disable sd-ai.socket 2>/dev/null || true
# --------------------

# 11 Sep 26 dm - PORT_ADOPTION 13.  THE AUDIT TRAIL IS APPEND-ONLY (chattr +a),
# and "rm -fr" cannot remove such a file: the removal below would stop part way
# and leave half an install.  So the attribute comes off first, after the
# services are stopped above so nothing is appending.  When the accounts are
# kept the trail is kept with them, in $acct_path, and installsdcore.sh puts it
# back - the Windows port's uninstaller keeps the trail with the database.
# Answering DELETE removes it with everything else.
for f in "$sdsysdir"/audit "$sdsysdir"/audit.*; do
    [ -f "$f" ] || continue
    sudo chattr -a "$f" 2>/dev/null || true
    if [ "$keep_accts" != "DELETE" ]; then
        sudo mv "$f" "$acct_path/"
        echo "Saved audit trail $(basename "$f")"
    fi
done

# 14 Sep 26 dm - W.4 SCRAM phase 2.  THE CREDENTIAL REGISTER GOES WITH THE
# ACCOUNTS, for the reason the audit trail does: $cred is every account's SD
# password (as SCRAM keys), and a keep cycle that dropped it would leave every
# account unreachable through the API until each password was set again.
# installsdcore.sh restores it sdsys:sdusers 0700 - the administrator's own
# (18 Sep 26, S.26; the group is sdusers, there is no sdsys group).  DELETE
# removes it.
if [ "$keep_accts" != "DELETE" ] && [ -d "$sdsysdir/\$cred" ]; then
    sudo rm -fr "$acct_path/\$cred"
    sudo cp -a "$sdsysdir/\$cred" "$acct_path/"
    echo "Saved the credential register (\$cred)"
fi

# 20 Sep 26 dm - S.40 (parity with the Windows port, owner's ruling).
# batch.jobs is the per-account allowlist for a command run from the sd
# command line (login's batch.permitted); it goes with the accounts for the
# same reason $cred does - a keep cycle that dropped it would silently widen
# every account back to "any command, unattended" until the list was rebuilt
# by hand.  installsdcore.sh restores it sdsys:sdusers 0750.  DELETE removes it.
if [ "$keep_accts" != "DELETE" ] && [ -d "$sdsysdir/batch.jobs" ]; then
    sudo rm -fr "$acct_path/batch.jobs"
    sudo cp -a "$sdsysdir/batch.jobs" "$acct_path/"
    echo "Saved the batch-job allowlist (batch.jobs)"
fi

# 16 Oct 26 dm - QM4 gap 501 (NEWVOC.MODS): optional site-local VOC additions
# and overrides applied by bbproc, CREATE.ACCOUNT and UPDATE.ACCOUNTS.  Saved
# across a keep cycle if the administrator created one; DELETE removes it.
if [ "$keep_accts" != "DELETE" ] && [ -d "$sdsysdir/newvoc.mods" ]; then
    sudo rm -fr "$acct_path/newvoc.mods"
    sudo cp -a "$sdsysdir/newvoc.mods" "$acct_path/"
    echo "Saved the local VOC modifications file (newvoc.mods)"
fi

# 03 Nov 26 dm - where a session starts (set.start.default writes start.default in the sdsys directory, which this script removes): kept across a
# keep cycle as start.default.saved, so the installer's question offers it as the answer and an upgrade does not quietly change it.  An install from
# before the home screen (no gpl.bp/tool_home: L1.1-3 and earlier) started every session at the prompt, so it is saved as terminal (owner, 3 Nov 2026:
# "for existing users where all installs go to the prompt by default ... that will be retained on upgrade").
# 14 Nov 26 dm  ALWAYS SAVED WHEN THE ACCOUNTS ARE KEPT (owner, 14 Nov 2026: "an upgrade from 1.1-3 will always be prompt, so the installer should
#            assume that if there is no setting").  The installer now reads NO saved setting as the prompt, so an install that HAS the home screen and
#            was left at it (no start.default: the default writes none) must say so, or its upgrade would go to the prompt.  The home screen is known
#            by its program: gpl.bp.out/tool_home, the compiled object a 2.0 install keeps (gpl.bp, the source, is no longer installed), or
#            gpl.bp/tool_home in an older dev install.  Anything else is an install from before the home screen: the prompt.
# START-SAVE-BEGIN
if [ "$keep_accts" != "DELETE" ]; then
    if sudo test -f "$sdsysdir/start.default"; then
        sudo cp "$sdsysdir/start.default" "$acct_path/start.default.saved"
        sudo chmod 644 "$acct_path/start.default.saved"
        echo "Saved where sessions start (start.default)"
    elif sudo test -e "$sdsysdir/gpl.bp.out/tool_home" || sudo test -e "$sdsysdir/gpl.bp/tool_home"; then
        echo menu | sudo tee "$acct_path/start.default.saved" > /dev/null
        sudo chmod 644 "$acct_path/start.default.saved"
        echo "Saved where sessions start: at the home screen"
    else
        echo terminal | sudo tee "$acct_path/start.default.saved" > /dev/null
        sudo chmod 644 "$acct_path/start.default.saved"
        echo "Saved where sessions start: at the prompt (this install is from before the home screen)"
    fi
fi
# START-SAVE-END

# 27 Oct 26 dm - S.87 (the VOC deletion list): the copies of the VOC records an update removed, which RESTORE.VOC puts back, are kept across a keep cycle like
# newvoc.mods; DELETE removes them with the accounts they came from.
if [ "$keep_accts" != "DELETE" ] && [ -d "$sdsysdir/voc_removed.saved" ]; then
    sudo rm -fr "$acct_path/voc_removed.saved"
    sudo cp -a "$sdsysdir/voc_removed.saved" "$acct_path/"
    echo "Saved the copies of removed VOC records (voc_removed.saved)"
fi

# 26 Oct 26 dm - W.11 F11.  The installer makes bin immutable (chattr +i) so that the sdsys user, who owns the system directory, cannot rename it away and put a bin of
# its own in its place; "rm -fr" cannot empty or remove an immutable directory, so the attribute comes off first, as the audit trail's does above.  A bin from before
# this change, or on a file system without attributes, has no such attribute: the command finds nothing to lift and is no harm.
sudo chattr -i "$sdsysdir/bin" 2>/dev/null || true

# remove the /usr/sdsys directory
sudo rm -fr "$sdsysdir"
echo
echo "Removed ${sdsysdir} directory."

# remove the symbolic link to sd in /usr/local/bin or /usr/bin
if [ -L "/usr/local/bin/sd" ]; then
    sudo rm /usr/local/bin/sd
    echo "Removed symbolic link /usr/local/bin/sd."
fi

# 02 Oct 26 - a leftover sd-full link, which a 2 Oct installer made and the 1 Oct ruling
# dropped; only a link, as sd is.
if [ -L "/usr/local/bin/sd-full" ]; then
    sudo rm /usr/local/bin/sd-full
    echo "Removed symbolic link /usr/local/bin/sd-full."
fi

if [ -L "/usr/bin/sd" ]; then
    sudo rm /usr/bin/sd
    echo "Removed symbolic link /usr/bin/sd."
fi

#remove config file
sudo rm -f /etc/sd.conf
# 26 Oct 26 dm - S.75 A6: set.config (sd-elevate conf-set) keeps the file as it was before its last change as /etc/sd.conf.bak; it goes with the file, whether the
# configuration was saved to /home/sd (the saved sd.conf is the current one, the .bak is only the generation before it) or deleted.
sudo rm -f /etc/sd.conf.bak
echo "Config file removed."

# 15 Sep 26 dm - S.19: the API's TLS server identity, kept beside sd.conf
# (gplsrc/linuxio.c api_tls_dir).  The relay makes a new one on the next
# install's first API connection.
#
# 15 Sep 26 dm - ***IT GOES WITH THE ACCOUNTS NOW, LIKE $cred ABOVE*** (owner's
# ruling that day: the identity persists for 1.1; client-side recognition is
# 1.2's mutual enrolment).  A keep cycle used to destroy the server's identity,
# so the next install came up with a NEW key while the accounts, passwords and
# audit trail were all the ones the machine had before.  Nothing notices today,
# because no client checks the key - but the moment one does, every upgrade
# would look exactly like an impostor, and a warning that fires on every routine
# upgrade is one people learn to click through.  So the decision is taken before
# the clients exist, not after.
#
# It is LEFT IN PLACE rather than saved and restored: unlike $cred it lives
# outside the sdsys tree, at /etc/sd-tls, and installsdcore.sh never touches it -
# the relay picks it up on the next first API connection.  DELETE removes it,
# which is the case where the machine is genuinely being wiped.
if [ "$keep_accts" = "DELETE" ]; then
    sudo rm -rf /etc/sd-tls
    echo "Removed /etc/sd-tls."
else
    if [ -d /etc/sd-tls ]; then
        echo "Kept the API's TLS server identity (/etc/sd-tls), as the accounts were kept."
    fi
fi

# 10 Sep 26 - nano's SD BASIC syntax file, which installs before 1.2-0 placed outside the
# SD tree (beside the microcfg copy) because nano reads /usr/share/nano/*.nanorc.  The NANO
# verb is gone (27 Oct 26), so no new install makes the file; this removes an old one.
sudo rm -f /usr/share/nano/sdbasic.nanorc
echo "Removed /usr/share/nano/sdbasic.nanorc."

# 02 Nov 2026 - S.105: the block that removed the /etc/nanorc include line (22 Sep
#   2026) is gone with Fedora.  Older installers wrote that line only on a
#   distribution whose nanorc does not glob /usr/share/nano as Debian's does
#   (Arch, Fedora, openSUSE), none of which this release supports; git keeps it.

# --------------------
# 02 Oct 26  THE API FIREWALL RULE (owner, 2 Oct 2026: the API port is 4247,
#            fixed).  The installer and REMOTE.API add "ufw allow 4247/tcp";
#            nothing removed it before, so an uninstall left the port open.
#            Our own rule goes.  A 4243 rule is only REPORTED: SD Core used 4243
#            until 2 Oct 2026, but it is also OpenQM's and ScarletDME's port,
#            so this script cannot know the rule is SD's and does not touch it.
if command -v ufw >/dev/null 2>&1; then
    if sudo ufw show added 2>/dev/null | grep -q -E '^ufw allow 4247/tcp$'; then
        sudo ufw delete allow 4247/tcp >/dev/null && echo "Removed the firewall rule for the SD API (ufw allow 4247/tcp)."
    fi
    if sudo ufw show added 2>/dev/null | grep -q -E '^ufw allow 4243/tcp$'; then
        echo "NOTE: a firewall rule 'ufw allow 4243/tcp' remains.  SD Core before 2 Oct 2026"
        echo "  used port 4243; if nothing else on this computer needs it, remove it with:"
        echo "      sudo ufw delete allow 4243/tcp"
    fi
fi
# 04 Oct 26  THE SAME FOR FIREWALLD (owner, 4 Oct 2026), which the installer and
#            REMOTE.API use where it is the firewall.  Read
#            from the saved configuration, as sd-elevate reads it: --permanent,
#            or firewall-offline-cmd while firewalld is stopped.
# 02 Nov 26  S.105: kept with Fedora gone - Debian and Ubuntu package firewalld,
#            and the installer chooses it by what is installed, not by distribution.
if command -v firewall-cmd >/dev/null 2>&1 || command -v firewall-offline-cmd >/dev/null 2>&1; then
    # Running is asked of systemd: "firewall-cmd --state" is refused by polkit to an
    # ordinary user, which would read a running firewalld as stopped.
    if systemctl is-active --quiet firewalld 2>/dev/null; then fwd_live=1; fwd_saved() { sudo firewall-cmd --permanent "$@"; }
    else fwd_live=0; fwd_saved() { sudo firewall-offline-cmd "$@"; }; fi
    # The EXACT entry, not --query-port: a zone with its own range (Fedora
    # Workstation's 1025-65535/tcp, measured 4 Oct 2026) answers yes for 4247, and removing 4247 then split that range
    # (measured, 4 Oct 2026) - a hole in a rule SD did not make.
    fwd_rule() { fwd_saved --list-ports 2>/dev/null | tr ' ' '\n' | grep -qx -- "$1"; }
    if fwd_rule 4247/tcp; then
        fwd_saved --remove-port=4247/tcp >/dev/null && echo "Removed the firewall rule for the SD API (firewalld port 4247/tcp)."
        if [ "$fwd_live" -eq 1 ]; then sudo firewall-cmd -q --reload; fi
    fi
    if fwd_rule 4243/tcp; then
        echo "NOTE: a firewalld rule for port 4243/tcp remains.  SD Core before 2 Oct 2026"
        echo "  used port 4243; if nothing else on this computer needs it, remove it with:"
        echo "      sudo firewall-cmd --permanent --remove-port=4243/tcp && sudo firewall-cmd --reload"
    fi
fi

# --------------------
# PRE_RELEASE 14 - the privileged helper and its sudoers drop-in.
#
# ORDER MATTERS: the drop-in goes FIRST.  It names the sdsys user, and a
# sudoers file referring to privileges that no longer belong on this machine
# is a dangling entry in the file that decides who may become root.  Removing
# the rule before anything it mentions means there is never a moment where
# one outlives the other.
sudo rm -f /etc/sudoers.d/sdcore
echo "Removed /etc/sudoers.d/sdcore."
sudo rm -f /usr/local/sbin/sd-elevate
echo "Removed /usr/local/sbin/sd-elevate."
# 01 Oct 26  S.50 - the account archive tool goes with the helper that runs it.
#            Backups already written are the administrator's files and stay.
sudo rm -f /usr/local/sbin/sd-accarchive
echo "Removed /usr/local/sbin/sd-accarchive."
# 23 Oct 26 dm - S.69 step 2: the AI helper, its client and the provider table (root-owned, with the program).  Its settings and keys are /var/lib/sd-ai, which is
#   removed only with the accounts, further down.
sudo rm -rf /usr/local/lib/sd-ai
echo "Removed /usr/local/lib/sd-ai."
# 12 Sep 26  PORT_ADOPTION 19.  The reconciler goes with the other helpers.
#            It removes account directories under --sweep, so leaving a
#            root-owned copy behind after an uninstall would leave a tool
#            pointed at a register that is no longer there.
sudo rm -f /usr/local/sbin/sd-reconcile-accounts
echo "Removed /usr/local/sbin/sd-reconcile-accounts."
#
# 10 Sep 26  PRE_RELEASE 13 - take SD's ssh-only block back out of sshd_config.
#            ALWAYS, regardless of the accounts question: the block is system
#            configuration, not account data.  --remove is run BEFORE the helper
#            is deleted, because --remove IS the helper; it validates the result
#            with sshd -t and reloads sshd, and leaves sshd_config untouched if
#            no SD block is present.  Non-fatal: a stale block matching a group
#            that is about to be removed is harmless (it just never matches), so
#            a removal hiccup must not abort the uninstall.
# 14 Nov 26  AN UPGRADE KEEPS SDSYS OVER SSH AS IT WAS (owner, 13 Nov 2026, Windows chat: "I don't believe an upgrade should shut something that is already
#            open").  Before the block goes, an OPEN sdsys arm is noted in /home/sd/sdsys-ssh.saved when the configuration is kept (the keep cycle an upgrade
#            is); the installer opens it again after its own --install and removes the note.  Root-owned, mode 600, holding the word open: the installer
#            believes nothing else.  A deleted configuration leaves no note, so a full uninstall still removes it.  test-delete-sdsysssh.sh runs this block.
# SDSYS-SSH-SAVE-BEGIN
sudo rm -f "$acct_path/sdsys-ssh.saved"
if [ "$conf_deleted" = no ] && [ -x /usr/local/sbin/ssh-forcecommand ]; then
    case "$(sudo /usr/local/sbin/ssh-forcecommand --sdsys-state 2>/dev/null || true)" in
        *sdsys-arm=open*)
            if echo open | sudo tee "$acct_path/sdsys-ssh.saved" > /dev/null && sudo chmod 600 "$acct_path/sdsys-ssh.saved"; then
                echo "Saved: sdsys over ssh is open, and the next install opens it again."
            else
                echo "WARNING: could not note that sdsys over ssh is open; after the next install open it with:  sudo /usr/local/sbin/sd-elevate sdsys-ssh on"
            fi ;;
    esac
fi
# SDSYS-SSH-SAVE-END
ssh_fences_out=1
if [ -x /usr/local/sbin/ssh-forcecommand ]; then
    if ! sudo /usr/local/sbin/ssh-forcecommand --remove; then
        ssh_fences_out=0
        echo "WARNING: could not remove the ssh block automatically; check /etc/ssh/sshd_config and /etc/pam.d/sshd."
    fi
    sudo rm -f /usr/local/sbin/ssh-forcecommand
    echo "Removed /usr/local/sbin/ssh-forcecommand."
fi
# 01 Nov 26 dm - S.95: --remove above took out BOTH fences, the sshd block first and the two PAM lines after it.  The secret and the recovery codes go always (they are SD's
#            and belong to nothing once the fence is out); the module goes only when the fences are known to be out, because a PAM line naming a missing module would fail
#            the sign-in of sdsys (the line is guarded to that user, nobody else's).  A reinstall starts with the sdsys ssh door shut.
# 02 Nov 26 dm - S.106: the authenticator code itself is gone from SD; these removals stay only for a machine an older dev install put it on.
sudo rm -rf /etc/sdcore/totp
# 02 Nov 26 dm - S.101: the published status of the code (enrolled, scope) goes with the code.  Found by the S.102 VM witness: a delete left
#            "enrolled yes", and the next install started out claiming a code that no longer existed.
sudo rm -f /etc/sdcore/totp.public
# 02 Nov 26 dm - S.102 stage 3: the jobs' timers are stopped and their units removed FIRST (a timer left behind would start a program that is gone),
#            then the definitions (stage 2), which are SD's and belong to nothing once SD is gone.
for jt in /etc/systemd/system/sdcore-job-*.timer; do
    [ -e "$jt" ] || continue
    sudo systemctl disable --now "$(basename "$jt")" >/dev/null 2>&1 || true
done
sudo rm -f /etc/systemd/system/sdcore-job-*.timer /etc/systemd/system/sdcore-job-*.service
sudo systemctl daemon-reload >/dev/null 2>&1 || true
sudo rm -rf /etc/sdcore/jobs.d
sudo rmdir /etc/sdcore 2>/dev/null || true
echo "Removed /etc/sdcore/totp and totp.public (the sdsys authenticator secret, recovery codes and status), the scheduled jobs' timers and units, and /etc/sdcore/jobs.d (their definitions)."
if [ "$ssh_fences_out" = 1 ]; then
    sudo rm -rf /usr/local/lib/sd
    echo "Removed /usr/local/lib/sd (SD's PAM module)."
else
    echo "Kept /usr/local/lib/sd: a PAM line may still name it (see the warning above)."
fi
# 10 Sep 26  PRE_RELEASE 25 - THE GROUP GOES ONLY IF THE ACCOUNTS GO.
#            This removal was unconditional, and it was a lock-out on a
#            keep-accounts upgrade.  18 Sep 26, the teardown: sdadmin and
#            sdapi are not created any more (the administrator is the sdsys OS
#            user; the API is open to every account except SDSYS), so these
#            lines now only tidy machines installed before the teardown, and
#            only when the accounts go too.  A keep-accounts cycle leaves the
#            legacy groups exactly as it found them.
# 20 Sep 26 dm - S.29 BRINGS sdssh AND sdapi BACK, so sdapi is no longer a
#   leftover to tidy: it and sdssh are where each account's remote routes are
#   recorded.  They go with the accounts and never without them - on a keep
#   cycle the memberships ARE the routes the accounts still have.  sdadmin
#   stays legacy: the teardown removed the administrator group for good.
if [ "$keep_accts" = "DELETE" ]; then
    if getent group sdadmin &>/dev/null; then
        sudo groupdel sdadmin || true
        echo "Removed legacy group sdadmin."
    fi
    # 17 Oct 26 dm - S.65 slice 2c: sdfiles (the SDNet files-only API route)
    #   goes with sdssh and sdapi, for their reason.
    # 18 Oct 26 dm - S.65 write group: and sdfileswrite, the right to change files over it.
    # 21 Oct 26 dm - S.73 item 3: and sdfilesadmin, the right to administer them.
    # 23 Oct 26 dm - S.69 step 2: and sdaiusers, the right to use the AI provider's API.
    for sd_route_group in sdssh sdapi sdfiles sdfileswrite sdfilesadmin sdaiusers; do
        if getent group "$sd_route_group" &>/dev/null; then
            sudo groupdel "$sd_route_group" || true
            echo "Removed group $sd_route_group (the accounts went with it)."
        fi
    done
    # 21 Oct 26 dm - AI integration slice 1 (owner's D6): and the OS user sdai, with its own group (userdel takes the group it made).
    if getent passwd sdai &>/dev/null; then
        sudo userdel sdai || true
        echo "Removed user sdai."
    fi
    if getent group sdai &>/dev/null; then
        sudo groupdel sdai || true
        echo "Removed group sdai."
    fi
    # 23 Oct 26 dm - S.69 step 2: and the helper's settings and provider keys.  Kept with the accounts otherwise: a key is typed once and must survive an upgrade.
    if [ -d /var/lib/sd-ai ]; then
        sudo rm -rf /var/lib/sd-ai
        echo "Removed /var/lib/sd-ai (the AI settings and keys)."
    fi
else
    echo "sd ACCOUNTS were saved, so the route groups sdssh, sdapi, sdfiles, sdfileswrite, sdfilesadmin and sdaiusers were kept."
    echo "The user sdai was kept with them, and /var/lib/sd-ai (the AI settings and keys)."
fi
# --------------------

# Modified by Composer AI - 2026/06/10.
# Remove unit files using full paths; do not cd into systemd directory.
# cd /usr/lib/systemd/system
# stop services
# sudo systemctl stop sd.service
# sudo systemctl stop sdclient.socket
# disable services
# sudo systemctl disable sd.service
# sudo systemctl disable sdclient.socket
# remove service files
# sudo rm /usr/lib/systemd/system/sd.service
# sudo rm /usr/lib/systemd/system/sdclient.socket
# sudo rm /usr/lib/systemd/system/sdclient@.service
sudo rm -f "${systemd_dir}/sd.service" \
           "${systemd_dir}/sd-lnxd.service" \
           "${systemd_dir}/sdclient.socket" \
           "${systemd_dir}/sdclient@.service" \
           "${systemd_dir}/sd-ai.socket" \
           "${systemd_dir}/sd-ai@.service"
# --------------------
echo "Removed systemd service files."

# remove sdsys user and sdusers group only if deleting ACCOUNTS

if [ "$keep_accts" = "DELETE" ]; then
    # Modified by Composer AI - 2026/06/10.
    # Remove sdsys user and sdusers group only; sdsys is a user not a group.
    # sudo userdel sdsys
    # sudo groupdel sdusers
    # echo "Removed sdusers group."
    # sudo groupdel sdsys
    # echo "Removed sdsys group."
    if id sdsys &>/dev/null; then
        sudo userdel sdsys
        echo "Removed sdsys user."
    fi
    # 02 Nov 26 dm - S.102: the installer's CRONDENY block put the line "sdsys" in /etc/cron.deny and /etc/at.deny; with the user gone, the line goes
    #            too (that line only; a deny file left empty by it was the installer's own and is removed).  Kept accounts keep the sdsys user, and its deny.
    for dny in /etc/cron.deny /etc/at.deny; do
        if sudo test -f "$dny" && sudo grep -qx 'sdsys' "$dny"; then
            sudo sed -i '/^sdsys$/d' "$dny"
            if ! sudo test -s "$dny"; then sudo rm -f "$dny"; fi
            echo "Removed sdsys from $dny."
        fi
    done
    if getent group sdusers &>/dev/null; then
        sudo groupdel sdusers
        echo "Removed sdusers group."
    fi
    # Modified by Composer AI - 2026/06/10.
    # Remove orphan sdsys group left when userdel ran without groupdel.
    if getent group sdsys &>/dev/null; then
        sudo groupdel sdsys || true
        echo "Removed orphan sdsys group."
    fi
    # --------------------
    # 18 Oct 26 dm - S.66: sdg_shared goes here, in the DELETE path ONLY.  The next install
    #   makes the shared account again, and its group is made by CREATE.ACCOUNT as root and
    #   sdsys only; a group that survives a delete keeps whatever members an earlier install
    #   or an administrator gave it, and the reinstall would silently admit them to the
    #   shared account (sdg_shared's members are who may sign on to it).  On a keep-accounts
    #   cycle the register and /home/sd/group_accounts/shared survive and the group must
    #   too, so it is not touched there.
    if getent group sdg_shared &>/dev/null; then
        sudo groupdel sdg_shared || true
        echo "Removed group sdg_shared."
    fi
    echo "Note: for complete clean up groups sdu_* and sdg_* may need to be manually removed"
else
    echo "sd ACCOUNTS were saved, therefore"
    echo "user sdsys and group sdusers not deleted"
    echo "The assumption is sd will be reinstalled"
fi


printf "%b\n" "$GREEN"
echo "----------------------------------------------------------------------"
# Modified by Composer AI - 2026/06/10.
# Correct script name in completion message.
# echo "The deletesd.sh script has completed."
echo "The deletesdcore.sh script has completed."
# --------------------
echo "Reboot to update user and group information and prior to sd reinstall."
echo "----------------------------------------------------------------------"
printf "%b\n" "$YELLOW"
# Modified by Composer AI - 2026/06/10.
# read -p "Restart computer now? (y/N) " yn
read -r -p "Restart computer now? (y/N) " yn
# --------------------
case $yn in
    [yY] ) sudo reboot;;
    [nN] ) echo;;
    * ) echo ;;
esac
printf "%b\n" "$NC"
exit 0

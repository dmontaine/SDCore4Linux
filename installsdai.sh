#!/bin/bash
#   SD bash install script
#   (c) 2023-2026 Donald Montaine and Mark Buller
#   This software is released under the Blue Oak Model License
#   a copy can be found on the web here: https://blueoakcouncil.org/license/1.0.0
#
#   rev 2.0  Mar 15 2026 mab - echo -e to printf, allow install from local repository
#   - prior history suppressed 
#
#   rev 2.1 Apr 27 2026 dsm - change git repository to codeberg.org
#
#   rev 2.1ai May 24 2026 dsm - modified script to test ai version
#
#   09 Sep 2026 - two questions removed and the source fixed.  The installer no
#   longer asks whether to keep the download, and no longer asks which
#   repository to use: it always clones the main branch from
#   github.com/dmontaine/SDCore4Linux and always deletes the download when it
#   finishes.  The <D>evelopment branch and <L>ocal repository options are gone
#   with the question.  Debian and Ubuntu only for now - the pacman, dnf and
#   zypper branches are removed and a non-Debian system is refused by name
#   rather than silently taking a branch that installs nothing; Arch, Fedora and
#   openSUSE are served by the upstream sdb64 installer until this one is
#   stable.
#
#   10 Sep 2026 - two changes on the owner's ruling of that day.  The
#   installing user is registered as an SD ADMINISTRATOR (the ADMINISTRATOR
#   keyword on create-account) instead of a STANDARD account, so a fresh
#   install has a registered administrator and CPROC's bootstrap arm is a
#   fallback rather than the way in.  And a caller who cannot sudo is refused
#   at the first sudo, in words, instead of failing part-way with sudo's own
#   error.  Both are PRE_RELEASE 24.

# Modified by Composer AI - 2026/06/10.
# Enable strict mode and predictable word splitting for safer installation.
# (no strict mode in original script)
set -euo pipefail
IFS=$'\n\t'
# --------------------

# all important url of repository, change this to use your own fork
#
# 09 Sep 26  Now GitHub, always the main branch, and no longer a choice.  The
#            repository moved to github.com/dmontaine/SDCore4Linux; codeberg is
#            where this came from and is not where it is maintained.
#            MIND THE CAPITALISATION - the lower-case form only works through a
#            redirect.
REPO_URL="https://github.com/dmontaine/SDCore4Linux"
REPO_BRANCH="main"
# define where we expect to find the package
# 09 Sep 26  THE DOWNLOAD GOES UNDER $HOME, NOT INTO WHATEVER DIRECTORY THE
#            SCRIPT WAS RUN FROM.  It used to be "$(pwd)/.sdb64tmp", so running
#            the installer from a clone of this repository dropped a 4 MB build
#            tree inside the project and made "git status" dirty - and a clean
#            git status is a working instrument here.  Absolute, so it does not
#            move when the script cd's into the build tree.
dflt_git_folder="${HOME}/.sdb64tmp"
#
# 09 Sep 26  THE CLONE'S SOURCE TREE IS ONE LEVEL DOWN, AND THIS IS THE TRAP.
#            The old codeberg repository WAS the source tree - its root held
#            sd64/ - so the installer built from the clone root.  SDCore4Linux
#            holds the installer at the root and the source under sdb_ai/, so
#            the clone gives <tmp>/sdb_ai/sd64.  Building from <tmp> would fail
#            the "not an sd install repo" check with nothing to explain it.
repo_src_subdir="sdb_ai"

#function to test git repo availability
repo_available() {
# Modified by Composer AI - 2026/06/10.
# Test repository reachability directly instead of inspecting $? after echo.
# Attempt to list remote references silently
#   git ls-remote -q "$REPO_URL" &>/dev/null
# Check the exit status of the previous command
#   if [ $? -eq 0 ]; then
  if git ls-remote -q "$REPO_URL" &>/dev/null; then
# --------------------
    echo "The Git repository at github.com is available."
    echo "Creating temporary source code repository."
    return 0
  else
    printf "%b\n" "$RED"
    echo "The SDCore4Linux repository is not available."
    echo "Verify your internet connection and then try again."
    printf "%b\n" "$NC"
    # exit
    exit 1
  fi
 
}

# Modified by Composer AI - 2026/06/10.
# Verify required host tools before package installation begins.
require_command() {
  if ! command -v "$1" &>/dev/null; then
    printf "%bRequired command not found: %s%b\n" "$RED" "$1" "$NC" 1>&2
    exit 1
  fi
}
# --------------------

# Modified by Composer AI - 2026/06/10.
# Auto-detect distribution from /etc/os-release when possible.
detect_distro() {
  is_arch=0
  is_debian=0
  is_fedora=0
  is_suse=0
  if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    case "${ID_LIKE:-}:${ID}:" in
      *arch:*|*:arch:*) is_arch=1 ;;
      *debian:*|*:debian:*|*:ubuntu:*) is_debian=1 ;;
      *fedora:*|*:fedora:*|*:rhel:*) is_fedora=1 ;;
      *suse:*|*:opensuse*|*:sles:*) is_suse=1 ;;
    esac
  fi
}
# --------------------
 
if [[ $EUID -eq 0 ]]; then
    echo "This script must NOT be run as root" 1>&2
    # exit
    exit 1
fi
if [ -f  "/usr/local/sdsys/bin/sd" ]; then
    echo "A version of sd is already installed."
    echo "Uninstall it before running this script."
    # exit
    exit 1
fi
#
tgroup=sdusers
tuser=$USER
cwd=$(pwd)
sdsysdir="/usr/local/sdsys"

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

# Modified by Composer AI - 2026/06/10.
# sd -start and sd -stop return non-zero when already in the target state.
# Helpers prevent set -e from aborting reinstall/bootstrap mid-install.
sd_install_stop() {
  sudo "${sdsysdir}/bin/sd" -stop 2>/dev/null || true
}

sd_install_start() {
  if sudo "${sdsysdir}/bin/sd" -start; then
    return 0
  fi
  printf "%b\n" "$YELLOW"
  echo "sd -start failed; stopping any running instance and retrying."
  printf "%b\n" "$NC"
  sd_install_stop
  sleep 1
  if sudo "${sdsysdir}/bin/sd" -start; then
    return 0
  fi
  printf "%b\n" "$RED"
  echo "Could not start SD server."
  printf "%b\n" "$NC"
  return 1
}
# --------------------

#
clear
printf "%bSD installer%b\n" "$RED" "$NC"
echo -----------------------
echo
echo "WARNING - This script installs a version of SD that has been modified by AI."
echo "          This is a very experimental version for testing code reviews and"
echo "          modifications to the c code  by Composer AI."
# Modified by Composer AI - 2026/06/10.
# Fix typo in warning text.
# echo "          Do no try to install in parallel with a standard SD installation."
echo "          Do not try to install in parallel with a standard SD installation."
# --------------------
echo "          DO NOT USE IN A PRODUCTION ENVIRONMENT!"
echo
printf "%bFor this install script to work you must have sudo installed\n" "$GREEN" 
printf "and be a member of the sudo group.  Also, systemd must be enabled.%b\n" "$NC"
echo
# Modified by Composer AI - 2026/06/10.
# Fix tested-distribution wording.
# echo "Installer tested on Fedora 4r, and Ubuntu 26.04."
echo "Installer tested on Linux Mint 22.3."
# --------------------
echo
# 09 Sep 26  Was "from the selected branch", plus a paragraph offering the local
#            repository.  There is no selection any more: main, from GitHub.
echo "This script will download the SD source code from the main branch at"
echo "${REPO_URL}, compile it and install SD."
echo
echo "The download is temporary and is removed when the install finishes."
echo
#
printf "%b\n" "$YELLOW"
# Modified by Composer AI - 2026/06/10.
# read -p "Continue? (y/N) " yn
read -r -p "Continue? (y/N) " yn
# --------------------
echo
case $yn in
    [yY] ) echo;;
    [nN] ) exit 0;;
    * ) exit 0 ;;
esac
#
# 09 Sep 26  The local-repository probe is gone with the <L> menu option it fed.
#
printf "%b\n" "$GREEN"
echo "If requested, enter your account password:"
printf "%b\n" "$YELLOW"
#
# Modified by Composer AI - 2026/06/10.
# Refresh sudo credentials with sudo -v instead of sudo date.
# sudo date &>/dev/null
# 10 Sep 26  A CALLER WHO CANNOT SUDO IS REFUSED HERE, IN WORDS, BEFORE
#            ANYTHING IS CHANGED.  This was a bare "sudo -v": the credential
#            check was already the right test, but the failure was sudo's own
#            error and a set -e abort - true, and it names nothing the person
#            can act on.  Owner's ruling, 10 Sep 26.  Every privileged step in
#            this script shells to sudo, so without this the install fails
#            part-way through, after it has begun changing the machine.
if ! sudo -v; then
    printf "%b\n" "$RED"
    echo "This installer needs sudo, and ${USER} cannot use it."
    echo "sudo is not installed, or ${USER} is not in the sudo group."
    printf "%b\n" "$NC"
    exit 1
fi
# --------------------
clear
echo
# 09 Sep 26  The "Save downloaded source to a directory under your home folder?"
#            question is gone.  The download is working material, not something
#            the user is left holding: it is always removed when the install
#            finishes.  Somebody who wants the source clones the repository.
# Modified by Composer AI - 2026/06/10.
# Quote path variables when removing the temporary clone directory.
# rm -fr $cwd/$dflt_git_folder
# 09 Sep 26  sudo, and for the same reason as the cleanup at the end of the
#            script: a previous run that got as far as "sudo make" left
#            root-owned gplobj/ and terminfo/ behind, and an ordinary rm cannot
#            remove those.
sudo rm -fr "${dflt_git_folder}"
# --------------------
printf "%b\n" "$NC"
#
# Ask for distribution type
# Modified by Composer AI - 2026/06/10.
# Try auto-detection first; fall back to the manual menu when unknown.
# is_arch=0
# is_debian=0
# is_fedora=0
# is_suse=0
# printf "%bChoose your distribution.\n" "$GREEN"
detect_distro
# 09 Sep 26  DEBIAN AND UBUNTU ONLY, DELIBERATELY AND TEMPORARILY.  Arch, Fedora
#            and openSUSE are served by the upstream sdb64 installer while this
#            one is stabilised; they come back once it is.  Refusing is the
#            point: silently running the Debian branch on Fedora would install
#            nothing and fail later, somewhere that does not name the cause.
if [ "$is_debian" -ne 1 ]; then
    printf "%b\n" "$RED"
    echo "This installer currently supports Debian and Ubuntu based"
    echo "distributions only."
    echo
    if [ "$is_arch" -eq 1 ] || [ "$is_fedora" -eq 1 ] || [ "$is_suse" -eq 1 ]; then
        echo "Detected an Arch, Fedora or openSUSE based distribution from"
        echo "/etc/os-release.  Support for it will return; for now use the"
        echo "upstream sdb64 installer on this system."
    else
        echo "Could not identify this distribution from /etc/os-release."
    fi
    printf "%b\n" "$NC"
    exit 1
fi
echo "Detected a Debian or Ubuntu based distribution from /etc/os-release."
#
# The manual a/d/f/s distribution menu is gone with the other three branches.
# Detection either recognises Debian/Ubuntu or the refusal above has already
# exited, so there is nothing left to ask.
#
# 09 Sep 26  The pacman, dnf and zypper branches are removed with the rest of
#            the multi-distribution support; only apt-get is left.  They return
#            with the distributions, not before, so that what comes back is
#            written against an installer that works rather than restored from
#            memory.
#
# NOTE the Arch branch also START-ed and ENABLE-d sshd, which no other branch
# did.  That asymmetry is deliberately not carried into the apt branch here:
# whether SD turns an ssh server on is a decision, not an install detail, and it
# is PRE_RELEASE 13.  On Debian and Ubuntu the openssh-server package starts its
# own service, so removing the Arch lines changes nothing on this platform.
if ! sudo apt-get -y install git build-essential micro lynx libbsd-dev libsodium-dev openssh-server python3-dev; then
    printf "%b\n" "$RED"
    echo "Package installation using apt-get failed.  Exiting script."
    echo "Verify your internet connection and then try again."
    printf "%b\n" "$NC"
    exit 1
fi
# run this along as only required on Ubuntu 26.04 and
# don't want to abort if not found on earlier distributions
sudo apt-get -y --ignore-missing install libcrypt-dev || true
#

# Modified by Composer AI - 2026/06/10.
# Confirm build tools are available after distribution packages are installed.
require_command git
require_command make
require_command python3
require_command python3-config
# --------------------

echo
# 09 Sep 26  The <M>ain / <D>evelopment / <L>ocal menu is gone.  There is one
#            source: the main branch at GitHub.  The development branch is not
#            something to hand an end user, and the local-repository option
#            installed whatever happened to be sitting in ./sdb_ai, which is not
#            a decision an installer should offer either.
echo "Installing the main branch from: ${REPO_URL}"
repo_available
git clone --branch "$REPO_BRANCH" --depth 1 "$REPO_URL" "$dflt_git_folder"

# 09 Sep 26 dm - PRE_RELEASE 8.  RECORD WHICH COMMIT THIS INSTALL IS, so that
# assert-current.py can answer exactly instead of guessing from timestamps.
# Without it the only available comparison is "is the install older than the
# commit", which is decisive in one direction and worthless in the other: a
# newer mtime says nothing about WHICH commit was built.
#
# Read here, from the clone, rather than later from anywhere else - this is the
# only moment the answer is known for certain, and --depth 1 means HEAD is the
# one commit there is.  Written to the installed tree further down, once
# $sdsysdir exists.
sdcore_commit=$(git -C "$dflt_git_folder" rev-parse HEAD 2>/dev/null || echo unknown)
echo "Installing commit ${sdcore_commit}"

# The source tree is one level down in this repository - see repo_src_subdir.
inst_folder="${dflt_git_folder}/${repo_src_subdir}"

if [ -d "${inst_folder}/sd64" ]; then
    echo "Installing from ${inst_folder}."
else
    printf "%b\n" "$RED"
    echo "The download did not contain ${repo_src_subdir}/sd64, aborting."
    echo "Looked in: ${inst_folder}"
    echo "This means the repository layout changed, not that your download failed."
    printf "%b\n" "$NC"
    exit 1
fi

#
# Modified by Composer AI - 2026/06/10.
# cd $cwd/$inst_folder
# 09 Sep 26  inst_folder is absolute now - see dflt_git_folder.
cd "${inst_folder}"
# --------------------
#
# rev 0.9.0 need python dev to build, did we get it?
# Modified by Composer AI - 2026/06/10.
# Write a stand-in Python header using standard include syntax.
# python3 --version
# if [ $? -eq 0 ]; then
#     PY_HDRS=$(python3-config --includes)
#     HDRS_STR="${PY_HDRS%% *}"
#     HDRS_STR="${HDRS_STR#-I}"
#     echo "path to include file: " $HDRS_STR
#     echo "#include <"$HDRS_STR"/Python.h>" > sd64/gplsrc/sdext_python_inc.h
# else
if python3 --version &>/dev/null; then
    if ! python3-config --includes &>/dev/null; then
      printf "%bPython development headers missing, Cannot build!%b\n" "$RED" "$NC"
      exit 1
    fi
    echo "Python development headers available."
    echo '#include <Python.h>' > sd64/gplsrc/sdext_python_inc.h
else
# --------------------
    printf "%bPython missing, Cannot build!%b\n" "$RED" "$NC"
    exit 1
fi

#
# Modified by Composer AI - 2026/06/10.
# cd $cwd/$inst_folder/sd64
cd "${inst_folder}/sd64"
# --------------------
#
# Modified by Composer AI - 2026/06/10.
# Force rebuild during install; local checkouts may otherwise report up to date.
# if sudo make; then
if sudo make -B; then
# --------------------
    echo "Successful Build."
else
    printf "%b\n" "$RED"
    echo "Could not build SD. Install terminated!"
    printf "%b\n" "$NC"
    exit 1
fi
if [ ! -x bin/sd ]; then
    printf "%b\n" "$RED"
    echo "Build reported success but bin/sd is missing or not executable."
    echo "Install terminated!"
    printf "%b\n" "$NC"
    exit 1
fi

#
# Create sd system user and group
# Modified by Composer AI - 2026/06/10.
# Create sdusers/sdsys only when absent so reinstall after deletesdai.sh succeeds.
# echo "Creating group: sdusers."
# sudo groupadd --system sdusers
# sudo usermod -a -G sdusers root
# echo "Creating user: sdsys."
# sudo useradd --system sdsys -G sdusers
# echo "Setting user: sdsys default group to sdusers."
# sudo usermod -g sdusers sdsys
if ! getent group sdusers &>/dev/null; then
  echo "Creating group: sdusers."
  sudo groupadd --system sdusers
else
  echo "Group sdusers already exists."
fi
sudo usermod -a -G sdusers root
# Modified by Composer AI - 2026/06/10.
# Use sdusers as primary group (-g). Remove orphan sdsys group when no user
# exists; incomplete uninstalls leave group sdsys and useradd then fails.
# if ! id sdsys &>/dev/null; then
#   echo "Creating user: sdsys."
#   sudo useradd --system sdsys -G sdusers
# else
#   echo "User sdsys already exists."
# fi
# echo "Setting user: sdsys default group to sdusers."
# sudo usermod -g sdusers sdsys
if ! id sdsys &>/dev/null; then
  echo "Creating user: sdsys."
  if getent group sdsys &>/dev/null; then
    echo "Removing orphan sdsys group (no sdsys user)."
    sudo groupdel sdsys || true
  fi
  if ! sudo useradd --system -g sdusers -G sdusers --no-create-home sdsys; then
    printf "%b\n" "$RED"
    echo "Failed to create sdsys user. Install terminated!"
    printf "%b\n" "$NC"
    exit 1
  fi
else
  echo "User sdsys already exists."
fi
echo "Setting user: sdsys primary group to sdusers."
sudo usermod -g sdusers -G sdusers sdsys
# --------------------
# PRE_RELEASE 14, the owner's ruling of 9 Sep 2026: SD ships a sudoers.d
# drop-in for a group SD owns.
#
# WHY.  SD's account verbs shell out to sudo (useradd, passwd, usermod,
# groupadd, groupdel, userdel, chmod g+s) from ten call sites in GPL.BP.  With
# no sudoers configuration those block on a PASSWORD PROMPT INSIDE an SD
# session, which is a hang rather than an error - measured 9 Sep 2026, when
# "sudo -n -v" on this machine answered "a password is required".
#
# The drop-in names ONE command, SD's own helper, which validates its
# arguments; see gplbld/sdcore.sudoers for why naming useradd/passwd/usermod
# directly would be root by another route.
if ! getent group sdadmin &>/dev/null; then
  echo "Creating group: sdadmin."
  sudo groupadd --system sdadmin
else
  echo "Group sdadmin already exists."
fi

# Root-owned, and deliberately NOT under /usr/local/sdsys: that tree is
# chown -R sdsys:sdusers'd further down, so a helper living there could be
# rewritten by anyone who reached the sdsys account - and the sudoers entry
# would then hand them root.
echo "Installing privileged helper: /usr/local/sbin/sd-elevate."
sudo mkdir -p /usr/local/sbin
sudo install -o root -g root -m 0755 gplbld/sd-elevate /usr/local/sbin/sd-elevate

# Validate BEFORE installing.  A malformed sudoers file can lock sudo out of
# the machine, so this is checked rather than trusted.
echo "Validating sudoers drop-in."
if ! sudo visudo -cf gplbld/sdcore.sudoers; then
  printf "%b\n" "$RED"
  echo "gplbld/sdcore.sudoers failed validation. Install terminated!"
  printf "%b\n" "$NC"
  exit 1
fi

# The drop-in is inert unless /etc/sudoers includes the directory, and an
# ignored file looks exactly like one that grants nothing.  Checked rather
# than assumed.  sudo 1.9.1+ writes @includedir, older writes #includedir.
if ! sudo grep -Eq '^[[:space:]]*[@#]includedir[[:space:]]+/etc/sudoers\.d' /etc/sudoers; then
  printf "%b\n" "$RED"
  echo "/etc/sudoers has no includedir for /etc/sudoers.d, so the drop-in would"
  echo "be ignored. Add '#includedir /etc/sudoers.d' using visudo, then re-run."
  echo "Install terminated!"
  printf "%b\n" "$NC"
  exit 1
fi

# The filename must carry no '.' or '~' - sudo skips those silently.
sudo install -o root -g root -m 0440 gplbld/sdcore.sudoers /etc/sudoers.d/sdcore
echo "Installed: /etc/sudoers.d/sdcore (members of sdadmin may run sd-elevate)."
# --------------------
#
sudo cp -R sdsys /usr/local
# Fool sd's vm into thinking gcat is populated
sudo touch /usr/local/sdsys/gcat/\$CPROC
# create errlog
sudo touch /usr/local/sdsys/errlog
#
# The TAPE and RESTORE subsystem was removed (plan I1, step 4 shrink). It was
# optional and copied in here at install time from tape/, which is gone; an
# install that declined the old prompt never had it and is unchanged.
#
# copy install template
sudo cp -R bin "$sdsysdir"
sudo cp -R gplsrc "$sdsysdir"
sudo cp -R gplobj "$sdsysdir"
# Modified by Composer AI - 2026/06/10.
# sudo mkdir $sdsysdir/gplbld
sudo mkdir -p "$sdsysdir/gplbld"
# --------------------
sudo cp -R gplbld/FILES_DICTS "$sdsysdir/gplbld/FILES_DICTS"
sudo cp -R terminfo "$sdsysdir"
#
# build program objects for bootstrap install
sudo python3 gplbld/bbcmp.py "$sdsysdir" GPL.BP/BBPROC GPL.BP.OUT/BBPROC
sudo python3 gplbld/bbcmp.py "$sdsysdir" GPL.BP/BCOMP GPL.BP.OUT/BCOMP
sudo python3 gplbld/bbcmp.py "$sdsysdir" GPL.BP/PATHTKN GPL.BP.OUT/PATHTKN
sudo python3 gplbld/pcode_bld.py

sudo cp Makefile "$sdsysdir"
sudo cp gpl.src "$sdsysdir"
sudo cp terminfo.src "$sdsysdir"

# 09 Sep 26 dm - PRE_RELEASE 12.  SHIP THE micro SYNTAX FILE.  It was generated
# and validated by entry 2 and then went nowhere, so the highlighting the owner
# asked to keep from the Windows port never reached a user.
#
# THIS ONLY PUTS IT IN THE INSTALLED TREE.  micro reads syntax files from a
# PER-USER directory (~/.config/micro/syntax) and stock micro has no
# system-wide path - measured, there is no /usr/share/micro - so an installer
# running as root cannot place it for everyone who will ever run SD.  GPL.BP's
# MICRO copies it into the caller's own config on first use; this is the master
# it copies FROM.  Before the chown below, so it lands sdsys:sdusers like the
# rest of the tree.
sudo cp -r gplbld/microcfg "$sdsysdir"
#
sudo chown -R sdsys:sdusers "$sdsysdir"
sudo chown root:root "$sdsysdir/ACCOUNTS/SDSYS"
sudo chmod 654 "$sdsysdir/ACCOUNTS/SDSYS"
sudo chown -R sdsys:sdusers "$sdsysdir/terminfo"

sudo cp sd.conf /etc/sd.conf
sudo chmod 644 /etc/sd.conf
sudo chmod -R 755 "$sdsysdir"
sudo chmod 775 "$sdsysdir/errlog"
sudo chmod -R 775 "$sdsysdir/prt"

# 09 Sep 26 dm - PRE_RELEASE 8.  THE INSTALL STAMP, read from the clone above.
# assert-current.py compares "commit" against the working tree's HEAD, which is
# the only exact way to ask whether a measurement is being taken against the
# source that produced it.  Without it the best available comparison is "is the
# install older than the commit" - decisive in one direction and worthless in
# the other, because a newer mtime says nothing about WHICH commit was built.
#
# ***WRITTEN HERE AND NOT EARLIER, DELIBERATELY.***  Both "chown -R
# sdsys:sdusers" and "chmod -R 755" run above; a stamp written before them
# would be swept into sdsys ownership and mode, and it must not be, because
# anything that can rewrite this file can lie about what is installed.
sudo tee "$sdsysdir/.sdcore-install" >/dev/null <<SDSTAMP
# Written by installsdai.sh.  Read by gplbld/assert-current.py.
commit=${sdcore_commit}
branch=${REPO_BRANCH}
origin=${REPO_URL}
installed=$(date '+%Y-%m-%d %H:%M:%S')
SDSTAMP
sudo chown root:root "$sdsysdir/.sdcore-install"
sudo chmod 644 "$sdsysdir/.sdcore-install"
#
#   Add $tuser to sdusers group
sudo usermod -aG sdusers "$tuser"
#
 # directories for sd accounts
ACCT_PATH=/home/sd
if [ ! -d "$ACCT_PATH" ]; then
   sudo mkdir -p "$ACCT_PATH"/user_accounts
   sudo mkdir "$ACCT_PATH"/group_accounts
fi  
#
# Modified by Composer AI - 2026/06/10.
# Reference deletesdai.sh by its actual script name.
# rev 0.9.3 always set ownership (these could get messed up if sdsys and sdusers group gets deleted during deletesd.sh script
# rev 0.9.3 always set ownership (these could get messed up if sdsys and sdusers group gets deleted during deletesdai.sh script
# --------------------
sudo chown sdsys:sdusers "$ACCT_PATH"
sudo chmod 775 "$ACCT_PATH"
sudo chown sdsys:sdusers "$ACCT_PATH"/group_accounts
sudo chmod 775 "$ACCT_PATH"/group_accounts
sudo chown sdsys:sdusers "$ACCT_PATH"/user_accounts
sudo chmod 775 "$ACCT_PATH"/user_accounts
#
# Modified by Composer AI - 2026/06/10.
# sudo ln -s $sdsysdir/bin/sd /usr/local/bin/sd
sudo ln -sf "$sdsysdir/bin/sd" /usr/local/bin/sd
# --------------------
#
# Install sd service for systemd
SYSTEMDPATH=/usr/lib/systemd/system
#
if [ -d  "$SYSTEMDPATH" ]; then
    if [ -f "$SYSTEMDPATH/sd.service" ]; then
        echo "SD systemd service is already installed."
    else
        echo "Installing sd.service for systemd."
        sudo cp usr/lib/systemd/system/* "$SYSTEMDPATH"
        sudo chown root:root "$SYSTEMDPATH/sd.service"
        sudo chown root:root "$SYSTEMDPATH/sdclient.socket"
        sudo chown root:root "$SYSTEMDPATH/sdclient@.service"
        sudo chmod 644 "$SYSTEMDPATH/sd.service"
        sudo chmod 644 "$SYSTEMDPATH/sdclient.socket"
        sudo chmod 644 "$SYSTEMDPATH/sdclient@.service"
    fi
fi
#
# Copy saved directories if they exist
if [ -d /home/sd/ACCOUNTS ]; then
    sudo rm -fr "$sdsysdir/ACCOUNTS"
    sudo mv /home/sd/ACCOUNTS "$sdsysdir"
    echo Restored ACCOUNTS directory
else
    echo No ACCOUNTS backup directory exists
fi
#
# Copy saved sd.conf file if it exists
if [ -f /home/sd/sd.conf ]; then
    sudo rm /etc/sd.conf
    sudo mv /home/sd/sd.conf /etc
    echo Restored sd.conf file
else
    echo No sd.conf backup file exists
fi
#
#   Start SD server
# Modified by Composer AI - 2026/06/10.
# Stop any running instance before bootstrap; sd -start fails if already up.
# echo "Starting SD server."
# sudo "$sdsysdir/bin/sd" -start
echo "Starting SD server."
sudo systemctl stop sd.service sdclient.socket 2>/dev/null || true
sd_install_stop
sleep 1
if ! sd_install_start; then
    echo "Install terminated!"
    exit 1
fi
# --------------------
echo
# Modified by Composer AI - 2026/06/10.
# Fix bootstrap spelling in user-facing messages.
# echo "Bootstap pass 1."
echo "Bootstrap pass 1."
# --------------------
# Modified by Composer AI - 2026/06/10.
# Abort install when bootstrap pass 1 fails (e.g. LOGIN compile error).
# sudo "$sdsysdir/bin/sd" -i
if ! sudo "$sdsysdir/bin/sd" -i; then
    printf "%b\n" "$RED"
    echo "Bootstrap pass 1 failed. Install terminated!"
    echo "Review compile errors above before re-running the installer."
    printf "%b\n" "$NC"
    exit 1
fi
# --------------------
#
# files added in pass1 need perm and owner setup
# Modified by Composer AI - 2026/06/10.
# Skip chmod/chown when bootstrap did not create expected directories.
# sudo chmod -R 755 "$sdsysdir/\$HOLD.DIC"
for bootstrap_dir in '$HOLD.DIC' '$IPC' '$MAP' '$MAP.DIC' VOC ACCOUNTS.DIC DICT.DIC DIR_DICT VOC.DIC; do
    if [ -d "${sdsysdir}/${bootstrap_dir}" ]; then
        if [ "${bootstrap_dir}" = '$IPC' ]; then
            sudo chmod -R 775 "${sdsysdir}/${bootstrap_dir}"
        else
            sudo chmod -R 755 "${sdsysdir}/${bootstrap_dir}"
        fi
        sudo chown -R sdsys:sdusers "${sdsysdir}/${bootstrap_dir}"
    fi
done
# --------------------
#
# echo "Bootstap pass 2."
echo "Bootstrap pass 2."
# Modified by Composer AI - 2026/06/10.
# sudo "$sdsysdir/bin/sd" -internal SECOND.COMPILE
if ! sudo "$sdsysdir/bin/sd" -internal SECOND.COMPILE; then
    printf "%b\n" "$RED"
    echo "Bootstrap pass 2 failed. Install terminated!"
    printf "%b\n" "$NC"
    exit 1
fi
# --------------------
#
# echo "Bootstap pass 3."
echo "Bootstrap pass 3."
if ! sudo "$sdsysdir/bin/sd" RUN GPL.BP WRITE_INSTALL_DICTS NO.PAGE; then
    printf "%b\n" "$RED"
    echo "Bootstrap pass 3 failed. Install terminated!"
    printf "%b\n" "$NC"
    exit 1
fi
#
echo "Compiling C and I type dictionaries."
if ! sudo "$sdsysdir/bin/sd" THIRD.COMPILE; then
    printf "%b\n" "$RED"
    echo "THIRD.COMPILE failed. Install terminated!"
    printf "%b\n" "$NC"
    exit 1
fi
#
echo "Compiling CPROC without IS_INSTALL defined."
sudo bash -c 'echo "*comment out * $define IS_INSTALL" > /usr/local/sdsys/GPL.BP/define_install.h'
if ! sudo bin/sd -internal BASIC GPL.BP CPROC; then
    printf "%b\n" "$RED"
    echo "CPROC recompile failed. Install terminated!"
    printf "%b\n" "$NC"
    exit 1
fi
sudo chmod -R 755 "$sdsysdir/gcat"
#
#  create a user account for the current user
echo
echo
# 10 Sep 26  THE INSTALLING USER IS REGISTERED AS AN SD ADMINISTRATOR.
#            This was "create-account USER $tuser no.query", which made a
#            STANDARD account with no tier and no sdadmin membership, so a
#            fresh install had NO registered administrator and CPROC's
#            bootstrap arm was the only way in.  Owner's ruling, 10 Sep 26:
#            the arm is a fallback, not the norm.  The ADMINISTRATOR keyword
#            is CREATEA's own path (PRE_RELEASE 18) - it writes ACC$TIER and
#            adds the person to sdadmin - so the installer duplicates neither
#            half.  The port seeds its first administrator the same way, by
#            ADOPT, which CREATEA also forces to ADMINISTRATOR.
#
#            AN EXISTING ACCOUNT IS NOT TOUCHED.  The directory test above
#            means an upgrade that saved its accounts keeps the tier it has,
#            so this seeds a fresh install rather than promoting anybody.
if [ ! -d "/home/sd/user_accounts/${tuser}" ]; then
    echo "Creating a user account for ${tuser} as an SD administrator."
    sudo bin/sd create-account USER "$tuser" ADMINISTRATOR no.query
fi
#
echo
echo Stopping sd
# Modified by Composer AI - 2026/06/10.
# Use sd_install_stop/start so already-stopped/started does not abort install.
# sudo "$sdsysdir/bin/sd" -stop
sd_install_stop
# --------------------
sleep 1
#
echo
echo Enabling services
sudo systemctl start sd.service
sudo systemctl start sdclient.socket
sudo systemctl enable sd.service
sudo systemctl enable sdclient.socket
#
sleep 1
sd_install_stop
sleep 1
sd_install_start || true
sleep 1
sd_install_stop
#
echo
echo Compiling terminfo database
sudo "${inst_folder}/sd64/bin/sdtic" -v "${inst_folder}/sd64/terminfo.src"
echo Terminfo compilation complete
sudo cp "${inst_folder}/sd64/terminfo.src" "$sdsysdir"
echo

# 09 Sep 26  The download is always removed.  There is no longer a saved-copy
#            branch, and no local-repository case to exempt.
# 09 Sep 26  ***sudo, AND THIS IS THE BUG THAT MADE THE FIRST GITHUB INSTALL
#            "FAIL" AFTER IT HAD ACTUALLY SUCCEEDED.***  installsdai.sh:359 runs
#            "sudo make -B", so gplobj/ and terminfo/ inside the download are
#            owned by root.  A plain "rm -fr" as the calling user cannot unlink
#            files inside a root-owned directory: it deletes everything else,
#            prints "Permission denied", and RETURNS 1 - which under
#            "set -euo pipefail" at line 28 aborts the script.  SD was already
#            installed and working by then; the run just ended on an error with
#            no message, leaving a stripped .sdb64tmp holding only those two
#            directories.  It was invisible before only because the <L>ocal
#            option left no download for this block to find.
if [ -d "${dflt_git_folder}" ]; then
    echo "Remove ${dflt_git_folder}"
    sudo rm -fr "${dflt_git_folder}"
fi
cd "$cwd"
#
# display end of script message
echo
echo ---------------------------------------------------------------
# Modified by Composer AI - 2026/06/10.
# Reset terminal colors correctly in completion banner.
# printf "%bThe SD server is installed.%b\n" "$RED" "$YELLOW"
printf "%bThe SD server is installed.%b\n" "$RED" "$NC"
# --------------------
echo "---------------------------"
echo
# 09 Sep 26  One outcome to report now: the download is always deleted.
printf "%bThe temporary source code directory used during the install%b\n" "$GREEN" "$NC"
echo "has been deleted."
echo
echo "The /home/sd directory has been created."
echo "User directories are created under /home/sd/user_accounts."
echo "Group directories are created under /home/sd/group_accounts."
echo "Accounts are only created using CREATE-ACCOUNT in SD."
echo
echo "Reboot to assure that group memberships are updated"
echo "and the APIsrvr Service is enabled."
#
echo
echo "After rebooting, open a terminal and enter \'sd\' "
echo "to connect to your sd home directory."
echo
echo "Note: In rare cases it requires two reboots for sd to autostart"
echo "      If it still does not start, kickstarting it one time will"
echo "      fix the problem. The kickstart command is:"
echo
echo "      sudo /usr/local/sdsys/bin/sd -start"
echo
echo
printf "%b----------------------------------------------------------------\n" "$NC" 
printf "%b\n" "$YELLOW"
# read -p "Restart Computer? (y/N) " yn
read -r -p "Restart Computer? (y/N) " yn
printf "%b\n" "$NC"
case $yn in
    [yY] ) sudo reboot;;
    [nN] ) echo;;
    * ) echo ;;
esac
exit 0

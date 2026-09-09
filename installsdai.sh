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

# Modified by Composer AI - 2026/06/10.
# Enable strict mode and predictable word splitting for safer installation.
# (no strict mode in original script)
set -euo pipefail
IFS=$'\n\t'
# --------------------

# all important url of repository, change this to use your own fork
REPO_URL="https://codeberg.org/stringdatabase/sdb_ai"  
# define where we expect to find the package
dflt_git_folder=".sdb64tmp"
dflt_local_folder="sdb_ai" 

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
    echo "The Git repository at codeberg.org is available."
    echo "Creating temporary source code repository."
    return 0
  else
    printf "%b\n" "$RED"
    echo "Sdb_ai repository is not available."
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
echo "This script will download the SD source code from the selected branch, compile and install SD."
printf "If a local repository is found in %s, an option is provided to install SD \nfrom the local repository.\n" "$dflt_local_folder"
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
# do we have a local repository?
#
if [ -d "$dflt_local_folder" ]; then
    LOCAL_REPO=1
else
    LOCAL_REPO=0
fi
#
printf "%b\n" "$GREEN"
echo "If requested, enter your account password:"
printf "%b\n" "$YELLOW"
#
# Modified by Composer AI - 2026/06/10.
# Refresh sudo credentials with sudo -v instead of sudo date.
# sudo date &>/dev/null
sudo -v
# --------------------
clear
echo
# Modified by Composer AI - 2026/06/10.
# Ask whether to preserve the git download under ~/sdscripts_ai_download_<datetime>.
SAVE_DOWNLOAD=0
SAVE_DOWNLOAD_DIR=""
printf "%b\n" "$YELLOW"
read -r -p "Save downloaded source to a directory under your home folder? (y/N) " yn
printf "%b\n" "$NC"
case $yn in
    [yY] ) SAVE_DOWNLOAD=1
           SAVE_DOWNLOAD_DIR="${HOME}/sdscripts_ai_download_$(date +%Y%m%d_%H%M%S)"
           echo "Download will be saved to: ${SAVE_DOWNLOAD_DIR}"
           ;;
    * )    SAVE_DOWNLOAD=0 ;;
esac
# --------------------
# Modified by Composer AI - 2026/06/10.
# Quote path variables when removing the temporary clone directory.
# rm -fr $cwd/$dflt_git_folder
rm -fr "${cwd}/${dflt_git_folder}"
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
distro_sum=$((is_arch + is_debian + is_fedora + is_suse))
if [ "$distro_sum" -eq 0 ]; then
printf "%bChoose your distribution.\n" "$GREEN"
echo
echo " Enter <A> if you are installing on an Arch based distribution." 
echo " Enter <D> if you are installing on a Debian or Ubuntu based distribution."
echo " Enter <F> if you are installing on a Fedora Based distribution."
echo " Enter <S> if you are installing on an openSuse Based distribution."
echo " Or press enter with no entry to exit the installer."
printf "%b\n" "$YELLOW"
# read -p "Continue? (a/d/f/s) " adfs
read -r -p "Continue? (a/d/f/s) " adfs
printf "%b\n" "$NC"
case $adfs in
    [aA] ) is_arch=1;;
    [dD] ) is_debian=1;;
    [fF] ) is_fedora=1;;
    [sS] ) is_suse=1;;
    * ) exit 0 ;;
esac
else
  echo "Detected distribution from /etc/os-release."
fi
# --------------------
#
# package installer is based on distro, clunky but easy to read
if [ $is_arch -eq 1 ]; then
    if ! sudo pacman -S git base-devel micro lynx libbsd libsodium openssh python; then
        printf "%b\n" "$RED"
        echo "Package installation using pacman failed.  Exiting script."
        echo "Verify your internet connection and then try again."
        printf "%b\n" "$NC"
        exit 1
    else   
        # Modified by Composer AI - 2026/06/10.
        # Try sshd.service first; fall back to sshd on Arch variants.
        # sudo systemctl start sshd
        # sudo systemctl enable sshd
        sudo systemctl start sshd.service 2>/dev/null || sudo systemctl start sshd
        sudo systemctl enable sshd.service 2>/dev/null || sudo systemctl enable sshd
        # --------------------
    fi
fi
#
if [ $is_debian -eq 1 ]; then
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
fi
#
if [ $is_fedora -eq 1 ]; then
    if ! sudo dnf -y install git make automake gcc gcc-c++ kernel-devel micro lynx libbsd-devel libsodium-devel openssh-server python3-devel; then
        printf "%b\n" "$RED"
        echo "Package installation using dnf failed.  Exiting script."
        echo "Verify your internet connection and then try again."
        printf "%b\n" "$NC"
        exit 1
    fi
fi
#
if [ $is_suse -eq 1 ]; then
    if ! sudo zypper --non-interactive install git make automake gcc gcc-c++ kernel-default-devel micro-editor lynx libbsd-devel libsodium-devel openssh python3-devel; then
        printf "%b\n" "$RED"
        echo "Package installation using zypper failed.  Exiting script."
        echo "Verify your internet connection and then try again."
        printf "%b\n" "$NC"
        exit 1
    fi
fi

# Modified by Composer AI - 2026/06/10.
# Confirm build tools are available after distribution packages are installed.
require_command git
require_command make
require_command python3
require_command python3-config
# --------------------

echo
echo "Select: "
echo "  <M>ain branch."
echo "  <D>evelopment branch."
if [ $LOCAL_REPO -eq 1 ]; then
    echo "  <L>ocal repository."
    # read -p "Select repository? (M/D/L) " mdl
    read -r -p "Select repository? (M/D/L) " mdl
else
    # read -p "Select repository? (M/D) " mdl
    read -r -p "Select repository? (M/D) " mdl
fi
printf "%b\n" "$NC"
#
# check that sdb64 repository is accessible
case $mdl in
    [mM] ) echo "Installing the main version at: $REPO_URL"
           inst_folder=$dflt_git_folder
           repo_available
           # git clone -b main $REPO_URL $inst_folder
           git clone -b main "$REPO_URL" "$inst_folder"
           ;;

    [dD] ) echo "Installing the development version at: $REPO_URL"
           inst_folder=$dflt_git_folder
           repo_available
           # git clone -b dev $REPO_URL $inst_folder
           git clone -b dev "$REPO_URL" "$inst_folder"
           ;;

    [lL] ) # Modified by Composer AI - 2026/06/10.
           # Reject local install when no local repository is present.
           # echo "Installing local repository found in $dflt_local_folder"
           # inst_folder=$dflt_local_folder
           if [ "$LOCAL_REPO" -ne 1 ] || [ ! -d "${dflt_local_folder}/sd64" ]; then
             echo "Local repository not available in ${dflt_local_folder}."
             exit 1
           fi
           echo "Installing local repository found in ${dflt_local_folder}"
           inst_folder=$dflt_local_folder
           # --------------------
           ;;
    * )    echo "No matching selection, exit."
           exit 1;;
esac

if [ -d "${inst_folder}/sd64" ]; then
    echo "Installing from ${inst_folder}."
else
    echo "${inst_folder} not found or not an sd install repo, aborting"
    exit 1
fi

#
# Modified by Composer AI - 2026/06/10.
# cd $cwd/$inst_folder
cd "${cwd}/${inst_folder}"
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
cd "${cwd}/${inst_folder}/sd64"
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
if [ ! -d "/home/sd/user_accounts/${tuser}" ]; then
    echo "Creating a user account for ${tuser}."
    sudo bin/sd create-account USER "$tuser" no.query
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
sudo "${cwd}/${inst_folder}/sd64/bin/sdtic" -v "${cwd}/${inst_folder}/sd64/terminfo.src"
echo Terminfo compilation complete
sudo cp "${cwd}/${inst_folder}/sd64/terminfo.src" "$sdsysdir"
echo

# Modified by Composer AI - 2026/06/10.
# Save or remove the temporary git clone; local-repo installs are not copied.
# if [ -d "${cwd}/${dflt_git_folder}" ]; then
#     echo "Remove ${cwd}/${dflt_git_folder}"
#     rm -fr "${cwd}/${dflt_git_folder}"
# fi
if [ -d "${cwd}/${dflt_git_folder}" ]; then
    if [ "$SAVE_DOWNLOAD" -eq 1 ] && [ "${inst_folder}" = "${dflt_git_folder}" ]; then
        if [ -e "${SAVE_DOWNLOAD_DIR}" ]; then
            printf "%b\n" "$RED"
            echo "Save directory already exists: ${SAVE_DOWNLOAD_DIR}"
            echo "Leaving temporary clone at ${cwd}/${dflt_git_folder}"
            printf "%b\n" "$NC"
        else
            echo "Saving download to ${SAVE_DOWNLOAD_DIR}"
            cp -a "${cwd}/${dflt_git_folder}" "${SAVE_DOWNLOAD_DIR}"
            rm -fr "${cwd}/${dflt_git_folder}"
        fi
    else
        echo "Remove ${cwd}/${dflt_git_folder}"
        rm -fr "${cwd}/${dflt_git_folder}"
    fi
fi
# --------------------
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
# Modified by Composer AI - 2026/06/10.
# Report whether the temporary git clone was saved or deleted.
# printf "%bThe temporary source code directory used during the install%b\n" "$GREEN" "$NC"
# echo "has been deleted."
if [ "$SAVE_DOWNLOAD" -eq 1 ] && [ -d "${SAVE_DOWNLOAD_DIR}" ]; then
    printf "%bThe temporary source code directory used during the install%b\n" "$GREEN" "$NC"
    echo "was saved to ${SAVE_DOWNLOAD_DIR}."
elif [ "${inst_folder}" = "${dflt_local_folder}" ]; then
    printf "%bThe local repository was used for installation; nothing was downloaded.%b\n" "$GREEN" "$NC"
else
    printf "%bThe temporary source code directory used during the install%b\n" "$GREEN" "$NC"
    echo "has been deleted."
fi
# --------------------
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

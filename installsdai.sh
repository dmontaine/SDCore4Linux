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

# all important url of repository, change this to use your own fork
REPO_URL="https://codeberg.org/stringdatabase/sdb_ai"  
# define where we expect to find the package
dflt_git_folder=".sdb64tmp"
dflt_local_folder="sdb_ai" 

#function to test git repo availability
repo_available() {
# Attempt to list remote references silently
  git ls-remote -q "$REPO_URL" &>/dev/null
# Check the exit status of the previous command
  if [ $? -eq 0 ]; then
    echo "The Git repository at codeberg.org is available."
    echo "Creating temporary source code repository."
    return 0
  else
    printf "%b\n" "$RED"
    echo "Sdb_ai repository is not available."
    echo "Verify your internet connection and then try again."
    printf "%b\n" "$NC"
    exit
  fi
 
}
 
if [[ $EUID -eq 0 ]]; then
    echo "This script must NOT be run as root" 1>&2
    exit
fi
if [ -f  "/usr/local/sdsys/bin/sd" ]; then
    echo "A version of sd is already installed."
    echo "Uninstall it before running this script."
    exit
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

#
clear
printf "%bSD installer%b\n" "$RED" "$NC"
echo -----------------------
echo
echo "WARNING - This script installs a version of SD that has been modified by AI."
echo "          This is a very experimental version for testing code reviews and"
echo "          modifications to the c code  by Claude AI."
echo "          Do no try to install in parallel with a standard SD installation."
echo "          DO NOT USE IN A PRODUCTION ENVIRONMENT!"
echo
printf "%bFor this install script to work you must have sudo installed\n" "$GREEN" 
printf "and be a member of the sudo group.  Also, systemd must be enabled.%b\n" "$NC"
echo
echo "Installer tested on Fedora 4r, and Ubuntu 26.04."
echo
echo "This script will download the SD source code from the selected branch, compile and install SD."
printf "If a local repository is found in %s, an option is provided to install SD \nfrom the local repository.\n" "$dflt_local_folder"
echo
#
printf "%b\n" "$YELLOW"
read -p "Continue? (y/N) " yn
echo
case $yn in
    [yY] ) echo;;
    [nN] ) exit;;
    * ) exit ;;
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
sudo date &>/dev/null
clear
echo
rm -fr $cwd/$dflt_git_folder
printf "%b\n" "$NC"
#
# Ask for distribution type
is_arch=0
is_debian=0
is_fedora=0
is_suse=0
printf "%bChoose your distribution.\n" "$GREEN"
echo
echo " Enter <A> if you are installing on an Arch based distribution." 
echo " Enter <D> if you are installing on a Debian or Ubuntu based distribution."
echo " Enter <F> if you are installing on a Fedora Based distribution."
echo " Enter <S> if you are installing on an openSuse Based distribution."
echo " Or press enter with no entry to exit the installer."
printf "%b\n" "$YELLOW"
read -p "Continue? (a/d/f/s) " adfs
printf "%b\n" "$NC"
case $adfs in
    [aA] ) is_arch=1;;
    [dD] ) is_debian=1;;
    [fF] ) is_fedora=1;;
    [sS] ) is_suse=1;;
    * ) exit ;;
esac
#
# package installer is based on distro, clunky but easy to read
if [ $is_arch -eq 1 ]; then
    sudo pacman -S git base-devel micro lynx libbsd libsodium openssh python
    if [ $? -ne 0 ]; then
        printf "%b\n" "$RED"
        echo "Package installation using pacman failed.  Exiting script."
        echo "Verify your internet connection and then try again."
        printf "%b\n" "$NC"
        exit
    else   
        sudo systemctl start sshd
        sudo systemctl enable sshd
    fi
fi
#
if [ $is_debian -eq 1 ]; then
    sudo apt-get -y install git build-essential micro lynx libbsd-dev libsodium-dev openssh-server python3-dev
    if [ $? -ne 0 ]; then
        printf "%b\n" "$RED"
        echo "Package installation using apt-get failed.  Exiting script."
        echo "Verify your internet connection and then try again."
        printf "%b\n" "$NC"
        exit
    fi
    # run this along as only required on Ubuntu 26.04 and
    # don't want to abort if not found on earlier distributions
    sudo apt-get -y --ignore-missing install libcrypt-dev
fi
#
if [ $is_fedora -eq 1 ]; then
    sudo dnf -y install git make automake gcc gcc-c++ kernel-devel micro lynx libbsd-devel libsodium-devel openssh-server python3-devel
    if [ $? -ne 0 ]; then
        printf "%b\n" "$RED"
        echo "Package installation using dnf failed.  Exiting script."
        echo "Verify your internet connection and then try again."
        printf "%b\n" "$NC"
        exit
    fi
fi
#
if [ $is_suse -eq 1 ]; then
    sudo zypper --non-interactive install git make automake gcc gcc-c++ kernel-default-devel micro-editor lynx libbsd-devel libsodium-devel openssh python3-devel
    if [ $? -ne 0 ]; then
        printf "%b\n" "$RED"
        echo "Package installation using zypper failed.  Exiting script."
        echo "Verify your internet connection and then try again."
        printf "%b\n" "$NC"
        exit
    fi
fi

echo
printf "%bInstalling from Codeberg repository $REPO_URL\n" "$YELLOW"
echo "Select: "
echo "  <M>ain branch."
echo "  <D>evelopment branch."
if [ $LOCAL_REPO -eq 1 ]; then
    echo "  <L>ocal repository."
    read -p "Select repository? (M/D/L) " mdl
else
    read -p "Select repository? (M/D) " mdl
fi
printf "%b\n" "$NC"
#
# check that sdb64 repository is accessible


case $mdl in
    [mM] ) echo "Installing the main version at: $REPO_URL"
           inst_folder=$dflt_git_folder
           repo_available
           git clone -b main $REPO_URL $inst_folder
           ;;

    [dD] ) echo "Installing the development version at: $REPO_URL"
           inst_folder=$dflt_git_folder
           repo_available
           git clone -b dev $REPO_URL $inst_folder
           ;;

    [lL] ) echo "Installing local repository found in $dflt_local_folder"
           inst_folder=$dflt_local_folder
           ;;
    * )    echo "No matching selection, exit."
           exit;;
esac

if [ -d "$inst_folder/sd64" ]; then
    echo "Installing from $inst_folder."
else
    echo "$inst_folder not found or not an sd install repo, aborting"
    exit
fi

#
cd $cwd/$inst_folder
#
# rev 0.9.0 need python dev to build, did we get it?
python3 --version
if [ $? -eq 0 ]; then
    # got it, what version and where are the include files?
    PY_HDRS=$(python3-config --includes)
    # remove the first "-I"
    # and get the first path (for some reason its output twice?
    HDRS_STR="${PY_HDRS%% *}"
    HDRS_STR="${HDRS_STR#-I}"
    #
    echo "path to include file: " $HDRS_STR
    # now create the include file we will use
    echo "#include <"$HDRS_STR"/Python.h>" > sd64/gplsrc/sdext_python_inc.h
else
    printf "%bPython missing, Cannot build!%b\n" "$RED" "$NC"
    exit
fi
#
cd $cwd/$inst_folder/sd64
#
sudo make
# rev 0.9.0 if make fails, abort install
if [ $? -eq 0 ]; then
    echo "Successful Build."
else
    printf "%b\n" "$RED"
    echo "Could not build SD. Install terminated!"
    printf "%b\n" "$NC"
    exit
fi
#
# Create sd system user and group
echo "Creating group: sdusers."
sudo groupadd --system sdusers
sudo usermod -a -G sdusers root
#
echo "Creating user: sdsys."
sudo useradd --system sdsys -G sdusers
echo "Setting user: sdsys default group to sdusers."
sudo usermod -g sdusers sdsys
#
sudo cp -R sdsys /usr/local
# Fool sd's vm into thinking gcat is populated
sudo touch /usr/local/sdsys/gcat/\$CPROC
# create errlog
sudo touch /usr/local/sdsys/errlog
#
# install TAPE and RESTORE system?
printf "%b\n" "$YELLOW"
read -p "Install TAPE and RESTORE subsystem? (y/N) " yn
printf "%b\n" "$NC"
case $yn in
    [yY] )  echo "Copying TAPE and RESTORE programs to GPL.BP."
            sudo cp tape/GPL.BP/* /usr/local/sdsys/GPL.BP
            echo "Copying TAPE and RESTORE verbs to VOC."
            sudo cp -R tape/VOC/* /usr/local/sdsys/VOC_TEMPLATE
            echo ;;
esac
#
# copy install template
sudo cp -R bin $sdsysdir
sudo cp -R gplsrc $sdsysdir
sudo cp -R gplobj $sdsysdir
sudo mkdir $sdsysdir/gplbld
sudo cp -R gplbld/FILES_DICTS $sdsysdir/gplbld/FILES_DICTS
sudo cp -R terminfo $sdsysdir
#
# build program objects for bootstrap install
sudo python3 gplbld/bbcmp.py $sdsysdir GPL.BP/BBPROC GPL.BP.OUT/BBPROC
sudo python3 gplbld/bbcmp.py $sdsysdir GPL.BP/BCOMP GPL.BP.OUT/BCOMP
sudo python3 gplbld/bbcmp.py $sdsysdir GPL.BP/PATHTKN GPL.BP.OUT/PATHTKN
sudo python3 gplbld/pcode_bld.py

sudo cp Makefile $sdsysdir
sudo cp gpl.src $sdsysdir
sudo cp terminfo.src $sdsysdir
#
sudo chown -R sdsys:sdusers $sdsysdir
sudo chown root:root $sdsysdir/ACCOUNTS/SDSYS
sudo chmod 654 $sdsysdir/ACCOUNTS/SDSYS
sudo chown -R sdsys:sdusers $sdsysdir/terminfo

sudo cp sd.conf /etc/sd.conf
sudo chmod 644 /etc/sd.conf
sudo chmod -R 755 $sdsysdir
sudo chmod 775 $sdsysdir/errlog
sudo chmod -R 775 $sdsysdir/prt
#
#   Add $tuser to sdusers group
sudo usermod -aG sdusers $tuser
#
 # directories for sd accounts
ACCT_PATH=/home/sd
if [ ! -d "$ACCT_PATH" ]; then
   sudo mkdir -p "$ACCT_PATH"/user_accounts
   sudo mkdir "$ACCT_PATH"/group_accounts
fi  
#
# rev 0.9.3 always set ownership (these could get messed up if sdsys and sdusers group gets deleted during deletesd.sh script   
sudo chown sdsys:sdusers "$ACCT_PATH"
sudo chmod 775 "$ACCT_PATH"
sudo chown sdsys:sdusers "$ACCT_PATH"/group_accounts
sudo chmod 775 "$ACCT_PATH"/group_accounts
sudo chown sdsys:sdusers "$ACCT_PATH"/user_accounts
sudo chmod 775 "$ACCT_PATH"/user_accounts
#
sudo ln -s $sdsysdir/bin/sd /usr/local/bin/sd
#
# Install sd service for systemd
SYSTEMDPATH=/usr/lib/systemd/system
#
if [ -d  "$SYSTEMDPATH" ]; then
    if [ -f "$SYSTEMDPATH/sd.service" ]; then
        echo "SD systemd service is already installed."
    else
        echo "Installing sd.service for systemd."
        sudo cp usr/lib/systemd/system/* $SYSTEMDPATH
        sudo chown root:root $SYSTEMDPATH/sd.service
        sudo chown root:root $SYSTEMDPATH/sdclient.socket
        sudo chown root:root $SYSTEMDPATH/sdclient@.service
        sudo chmod 644 $SYSTEMDPATH/sd.service
        sudo chmod 644 $SYSTEMDPATH/sdclient.socket
        sudo chmod 644 $SYSTEMDPATH/sdclient@.service
    fi
fi
#
# Copy saved directories if they exist
if [ -d /home/sd/ACCOUNTS ]; then
    sudo rm -fr $sdsysdir/ACCOUNTS
    sudo mv /home/sd/ACCOUNTS $sdsysdir
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
echo "Starting SD server."
sudo $sdsysdir/bin/sd -start
echo
echo "Bootstap pass 1."
sudo $sdsysdir/bin/sd -i
#
# files added in pass1 need perm and owner setup
sudo chmod -R 755 $sdsysdir/\$HOLD.DIC
sudo chmod -R 775 $sdsysdir/\$IPC
sudo chmod -R 755 $sdsysdir/\$MAP
sudo chmod -R 755 $sdsysdir/\$MAP.DIC
sudo chmod -R 755 $sdsysdir/VOC
sudo chmod -R 755 $sdsysdir/ACCOUNTS.DIC
sudo chmod -R 755 $sdsysdir/DICT.DIC
sudo chmod -R 755 $sdsysdir/DIR_DICT
sudo chmod -R 755 $sdsysdir/VOC.DIC
#
sudo chown -R sdsys:sdusers  $sdsysdir/\$HOLD.DIC
sudo chown -R sdsys:sdusers  $sdsysdir/\$IPC
sudo chown -R sdsys:sdusers  $sdsysdir/\$MAP
sudo chown -R sdsys:sdusers  $sdsysdir/\$MAP.DIC
sudo chown -R sdsys:sdusers  $sdsysdir/VOC
sudo chown -R sdsys:sdusers  $sdsysdir/ACCOUNTS.DIC
sudo chown -R sdsys:sdusers  $sdsysdir/DICT.DIC
sudo chown -R sdsys:sdusers  $sdsysdir/DIR_DICT
sudo chown -R sdsys:sdusers  $sdsysdir/VOC.DIC
#
echo "Bootstap pass 2."
sudo $sdsysdir/bin/sd -internal SECOND.COMPILE
#
echo "Bootstap pass 3."
sudo $sdsysdir/bin/sd RUN GPL.BP WRITE_INSTALL_DICTS NO.PAGE
#
echo "Compiling C and I type dictionaries."
sudo $sdsysdir/bin/sd THIRD.COMPILE
#
echo "Compiling CPROC without IS_INSTALL defined."
sudo bash -c 'echo "*comment out * $define IS_INSTALL" > /usr/local/sdsys/GPL.BP/define_install.h'
sudo bin/sd -internal BASIC GPL.BP CPROC
sudo chmod -R 755 $sdsysdir/gcat
#
#  create a user account for the current user
echo
echo
if [ ! -d /home/sd/user_accounts/$tuser ]; then
    echo "Creating a user account for" $tuser "."
    sudo bin/sd create-account USER $tuser no.query
fi
#
echo
echo Stopping sd
sudo $sdsysdir/bin/sd -stop
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
sudo $sdsysdir/bin/sd -stop
sleep 1
sudo $sdsysdir/bin/sd -start
sleep 1
sudo $sdsysdir/bin/sd -stop
#
echo
echo Compiling terminfo database
sudo $cwd/$inst_folder/sd64/bin/sdtic -v $cwd/$inst_folder/sd64/terminfo.src
echo Terminfo compilation complete
sudo cp $cwd/$inst_folder/sd64/terminfo.src $sdsysdir
echo

if [ -d "$cwd/$dflt_git_folder" ]; then
    echo "Remove $cwd/$dflt_git_folder"
    rm -fr $cwd/$dflt_git_folder
fi
cd $cwd
#
# display end of script message
echo
echo ---------------------------------------------------------------
printf "%bThe SD server is installed.%b\n" "$RED" "$YELLOW"
echo "---------------------------"
echo
printf "%bThe temporary source code directory used during the install\n" "$GREEN" 
echo "has been deleted."
echo
echo "The /home/sd directory has been created."
echo "User directories are created under /home/sd/user_accounts."
echo "Group directories are created under /home/sd/group_accounts."
echo "Accounts are only created using CREATE-ACCOUNT in SD."
echo
echo "Reboot to assure that group memberships are updated"
echo "and the APIsrvr Service is enabled."
echo "Note: In rare cases it requires two reboots for sd to autostart"
#
echo
echo "After rebooting, open a terminal and enter \'sd\' "
echo "to connect to your sd home directory."
echo
printf "%b----------------------------------------------------------------\n" "$NC" 
printf "%b\n" "$YELLOW"
read -p "Restart Computer? (y/N) " yn
printf "%b\n" "$NC"
case $yn in
    [yY] ) sudo reboot;;
    [nN] ) echo;;
    * ) echo ;;
esac
exit


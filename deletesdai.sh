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
           sudo cp -r "${sdsysdir}/ACCOUNTS" "$acct_path"
           ls "$acct_path/ACCOUNTS";;
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
               sudo cp -r "${sdsysdir}/ACCOUNTS" "$acct_path"
               ls "$acct_path/ACCOUNTS"
           fi
           ;;
    *)     echo
           echo Accounts Directory Saved
           sudo cp -r "${sdsysdir}/ACCOUNTS" "$acct_path"
           ls "$acct_path/ACCOUNTS";;
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
case $yn in
    [yY] ) echo
           sudo mv /etc/sd.conf "$acct_path"
           echo Configuration file saved;;
    [nN] ) echo
           echo Configuration file will be deleted;;
     *)    echo
           sudo mv /etc/sd.conf "$acct_path"
           echo Configuration file saved;;
esac
printf "%b\n" "$NC"

# Modified by Composer AI - 2026/06/10.
# Stop SD and systemd services before removing binaries and unit files.
# remove the /usr/sdsys directory
# sudo rm -fr /usr/local/sdsys
# ...
# cd /usr/lib/systemd/system
# stop services (was here, after rm)
sudo "${sdsysdir}/bin/sd" -stop 2>/dev/null || true
sudo systemctl stop sd.service sdclient.socket 2>/dev/null || true
sudo systemctl disable sd.service sdclient.socket 2>/dev/null || true
# --------------------

# remove the /usr/sdsys directory
sudo rm -fr "$sdsysdir"
echo
echo "Removed ${sdsysdir} directory."

# remove the symbolic link to sd in /usr/local/bin or /usr/bin
if [ -L "/usr/local/bin/sd" ]; then
    sudo rm /usr/local/bin/sd
    echo "Removed symbolic link /usr/local/bin/sd."
fi

if [ -L "/usr/bin/sd" ]; then
    sudo rm /usr/bin/sd
    echo "Removed symbolic link /usr/bin/sd."
fi

#remove config file
sudo rm -f /etc/sd.conf
echo "Config file removed."

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
           "${systemd_dir}/sdclient.socket" \
           "${systemd_dir}/sdclient@.service"
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
echo "The deletesdai.sh script has completed."
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

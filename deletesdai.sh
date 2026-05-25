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

if [[ $EUID -eq 0 ]]; then
    printf "%bThis script must NOT be run as root.%b\n" "$RED" "$NC" 1>&2
    exit
fi
if [ -f  "/usr/local/sdsys/bin/sd" ]; then
    echo
else
    printf "%bSD is not installed!\n" "$RED"
    printf "This script will not run.%b\n" "$NC"
    exit
fi
#
clear
printf "%bREMOVE the SD Database Package\n" "$RED"
echo    "---------------------------------------"
printf "%b\n" "$YELLOW"
read -p "Continue? (y/N) " yn
case $yn in
     [yY] ) echo;;
     [nN] ) exit;;
         *) exit ;;
esac

echo
echo "If requested, enter your account password:"
sudo date &>/dev/null

echo
printf "%bDo you want to save your existing accounts.\n" "$GREEN"
echo "WARNING: Entering 'N' will delete all your existing accounts."
echo         
printf "%b\n" "$YELLOW"
keep_accts='KEEP'
read -p "Keep your existing accounts? (Y/n) " yn
case $yn in
    [yY] ) echo
           echo Accounts Directory Saved
           sudo cp -r /usr/local/sdsys/ACCOUNTS /home/sd
           ls /home/sd/ACCOUNTS;;
    [nN] ) echo
           read -p 'Enter "DELETE" to confirm deletion of Accounts ' keep_accts
           if [ "$keep_accts" = "DELETE" ]; then
               echo /home/sd Directory Deleted
               sudo rm -fr /home/sd
           else
               echo Accounts Directory Saved
               sudo cp -r /usr/local/sdsys/ACCOUNTS /home/sd
               ls /home/sd/ACCOUNTS
           fi
           ;;
    *)     echo
           echo Accounts Directory Saved
           sudo cp -r /usr/local/sdsys/ACCOUNTS /home/sd
           ls /home/sd/ACCOUNTS;;
esac

echo
echo
printf "%bDo you want to save your existing SD configuration.\n" "$GREEN"
echo "WARNING: Entering 'N' will delete your current configuration."
echo        
printf "%b\n" "$YELLOW"
read -p "Keep your existing configuration? (Y/n) " yn
case $yn in
    [Yy] ) echo
           sudo mv /etc/sd.conf /home/sd
           echo Configuration file saved;;
    [nN] ) echo
           echo Configuration file will be deleted;;
     *)    echo
           sudo mv /etc/sd.conf /home/sd
           echo Configuration file saved;;
esac
printf "%b\n" "$NC"

# remove the /usr/sdsys directory
sudo rm -fr /usr/local/sdsys
echo
echo "Removed /usr/local/sdsys directory."

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
sudo rm /etc/sd.conf
echo "Config file removed."
#
cd /usr/lib/systemd/system

#stop services
sudo systemctl stop sd.service
sudo systemctl stop sdclient.socket

# disable services
sudo systemctl disable sd.service
sudo systemctl disable sdclient.socket

# remove service files
sudo rm /usr/lib/systemd/system/sd.service
sudo rm /usr/lib/systemd/system/sdclient.socket
sudo rm /usr/lib/systemd/system/sdclient@.service
echo "Removed systemd service files."

# remove sdsys and sdusers group only if deleting ACCOUNTS

if [ "$keep_accts" = "DELETE" ]; then
    sudo userdel sdsys
    sudo groupdel sdusers
    echo "Removed sdusers group."
	sudo groupdel sdsys
    echo "Removed sdsys group."
	echo "Note: for complete clean up groups sdu_* and sdg_* may need to be manually removed"
else
    echo "sd ACCOUNTS were saved, therefore"
	echo "user sdsys and group sdusers not deleted"
	echo "The assumption is sd will be reinstalled"
fi


printf "%b\n" "$GREEN"
echo "----------------------------------------------------------------------"
echo "The deletesd.sh script has completed."
echo "Reboot to update user and group information and prior to sd reinstall."
echo "----------------------------------------------------------------------"
printf "%b\n" "$YELLOW"
read -p "Restart computer now? (y/N) " yn
case $yn in
    [yY] ) sudo reboot;;
    [nN] ) echo;;
    * ) echo ;;
esac
printf "%b\n" "$NC"
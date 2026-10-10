# SD Core for Linux

SD, the multivalue String Database, for Linux — built to behave the same as
SD Core for Windows.

SD is a multivalue database in the Pr1me Information tradition, descended from
OpenQM and ScarletDME through [sdb64](https://codeberg.org/stringdatabase/sdb64).
SD Core for Linux starts from sdb64 and brings it into line with
[SD Core for Windows](https://github.com/dmontaine/SDCore4Windows): the same
account model, administration only from the SDSYS account, TLS 1.3 and SCRAM
login for the client API, the same message numbers, and embedded Python. Where
the two platforms must differ — the installer, file permissions, service
management — it uses the native Linux mechanism.

**Version L1.1-3, released 9 October 2026**, paired with SD Core for Windows W1.1-3.
L1.1-1 was released on 29 September 2026 and L1.1-0 (26 September 2026) was the
first release of SD Core for Linux.
See `sdb_ai/sd64/sdsys/changelog` for what each contains.

SD Core is English only: it has no support for other languages or locales.

## Requirements

- A 64-bit Linux with systemd: Debian, Ubuntu (and their derivatives) or Fedora.
  The installer refuses any other, including Arch, openSUSE, RHEL and RHEL's clones.
- A user who can use `sudo`.
- An internet connection: the installer installs the build packages, clones
  this repository and compiles SD. It checks first and stops, changing nothing,
  if the computer is offline.

## Installing

Download `installsdcore.sh` from this repository, make it executable and run it
as your ordinary user (it calls `sudo` itself):

```sh
chmod +x installsdcore.sh
./installsdcore.sh
```

It installs the required packages, clones the main branch of this repository,
builds SD, installs it under `/usr/local/sdsys`, registers the service, and
deletes the download when it finishes. The installing user is registered as an
SD administrator.

**From a USB stick.** A release zip can be unzipped on a USB stick and the
installer run from there. Run it with `bash`, because a stick formatted FAT,
exFAT or NTFS has no execute permission and `./installsdcore.sh` can fail on it:

```sh
bash /media/<you>/<stick>/installsdcore.sh
```

The stick carries only the installer and the documentation. The installer still
downloads SD and the build packages, so the computer must be online; if it is
not, the installer says so before it asks anything or changes anything. It
builds under your home directory and writes nothing to the stick.

`deletesdcore.sh` removes SD again.

**SD Core for Linux cannot be installed alongside another SD** (such as sdb64):
both use `/usr/local/sdsys`.

## Documentation

The installation guide, SD BASIC and TCL references, and the administrator's
guide are in the separate
[SDCore4LinuxDocs](https://github.com/dmontaine/SDCore4LinuxDocs) repository.

## Source

This repository contains no binaries; everything is built from source during
the install.

## Related repositories

- [SDCore4Windows](https://github.com/dmontaine/SDCore4Windows) — SD Core for
  Windows, the release this one conforms to.
- [SDCore4WindowsSolo](https://github.com/dmontaine/SDCore4WindowsSolo) — a
  single-user Windows edition.

## Licence

Most of SD is licensed under the GPL v3.0; the install and delete scripts are
licensed under the Blue Oak Model License 1.0.0. The header of each source file
says which applies; see `sdb_ai/LICENSE`.

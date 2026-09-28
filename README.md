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

**Version L1.1-0, in development — the first release of SD Core for Linux**,
numbered to pair with SD Core for Windows W1.1-0. See
`sdb_ai/sd64/sdsys/changelog` for what it contains.

## Requirements

- A 64-bit Linux with systemd. The installer detects Debian/Ubuntu, Fedora/RHEL,
  openSUSE and Arch-based distributions and refuses any other.
- A user who can use `sudo`.
- An internet connection: the installer installs the build packages, clones
  this repository and compiles SD.

## Installing

Download `installsdai.sh` from this repository, make it executable and run it
as your ordinary user (it calls `sudo` itself):

```sh
chmod +x installsdai.sh
./installsdai.sh
```

It installs the required packages, clones the main branch of this repository,
builds SD, installs it under `/usr/local/sdsys`, registers the service, and
deletes the download when it finishes. The installing user is registered as an
SD administrator.

`deletesdai.sh` removes SD again.

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

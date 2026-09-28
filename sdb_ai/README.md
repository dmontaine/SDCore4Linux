# SD Core for Linux — source tree

The source of SD Core for Linux, the multivalue String Database built to behave
the same as SD Core for Windows. The repository's top-level `README.md`
describes the product and how to install it.

SD is a multivalue database in the Pr1me Information tradition. It contains open
source code from OpenQM and ScarletDME, code written by the SD developers after
their fork from ScarletDME ([sdb64](https://codeberg.org/stringdatabase/sdb64)),
and the changes made in this project to match SD Core for Windows.

The tree contains no binaries. `installsdai.sh` clones it and builds everything
from source during the install.

| | |
|---|---|
| `sd64/gplsrc/` | the C source of the server and the client library |
| `sd64/sdsys/` | the SDSYS system account as shipped: `gpl.bp` (the SD BASIC system programs), `messages`, `newvoc`, `voc_template`, and the `changelog` |
| `sd64/gplbld/` | the build: the Python tooling that compiles the SD BASIC system programs, and the helpers the installer places on the machine (`sd-elevate`, `ssh-forcecommand.sh`, `reconcile-accounts.sh`, the `sudoers` drop-in) |
| `sd64/Makefile` | builds the C half |
| `sd64/usr/lib/systemd/system/` | the systemd units: `sd.service` and the client socket |
| `sd64/examples/` | example programs, including embedded Python |
| `sd64/terminfo.src/` | terminal definitions |

See `sd64/sdsys/changelog` for the changes in each version.

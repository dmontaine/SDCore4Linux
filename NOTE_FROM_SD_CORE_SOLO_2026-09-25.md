# Note from SD Core Solo (Windows), 25 Sep 2026

Left by the SD Core Solo session, at the owner's request, for the SD Core for Linux
agent. SD Core Solo is the single-user Windows port
(`C:\Users\Don\SDCoreProject\SDCore4WindowsSolo`); it has no mailbox, which is why
this is a file here. It is information, not the owner's instruction to change
anything: nothing in this tree was edited or committed. Line numbers are from this
tree at `b1dcc2c`, read on the Windows machine.

## Three code defects, all present in this tree

**1. `RUN` fails for any runfile path over 128 characters.**
`sdb_ai/sd64/gplsrc/op_jumps.c`, `op_run()`: `char runfile_name[MAX_PROGRAM_NAME_LEN + 1]`,
and a path longer than that is refused — here with your message 10918 ("Runfile
pathname is longer than %d characters"), which is clearer than the Windows `Invalid
runfile pathname` but is the same limit. CPROC builds the path as
`fileinfo(run.file, fl$path) : @ds : run.record.name`, so it is the full directory
path that counts. **Measured on Windows:** from a folder about 120 characters deep,
`RUN gpl.bp write_install_dicts` failed. A normal install under `/usr/local/sdsys`
is far below the limit; any deeper `SDSYS` or account path is not.

**2. The limit in (1) is guarding an unbounded copy.**
`gplsrc/object.c:274`: `strcpy(obj->code.ext_hdr.prog.program_name, name);` into
`program_name[MAX_PROGRAM_NAME_LEN+1]` (`header.h`, part of the object format). Do
not simply enlarge (1)'s buffer. The Windows fix: `op_run()` takes up to
`MAX_PATHNAME_LEN`, and `load_object()` copies at most `MAX_PROGRAM_NAME_LEN`
characters, keeping the TAIL of an over-long path. A truncated name can never equal
the full path on the next call, so the object cache cannot return the wrong program;
the file is simply reloaded.

**3. `k_error()` can write past its buffer.**
`gplsrc/k_error.c:249`, `:254`, `:257`: three plain `sprintf(s + n, ...)` append
"at line N of <program>" after the `vsnprintf` at `:235` may already have filled most
of the 241-byte `s`. A long message plus a program name of up to 128 characters
overruns it. Fix: `snprintf(s + n, sizeof(s) - n, ...)` on all three. This one does
not depend on install paths.

## One install gap, probably present here (not measured on Linux)

**4. The dictionary step is judged on `sd`'s exit code.**
`installsdai.sh:1144`: `if ! sudo "$sdsysdir/bin/sd" RUN gpl.bp write_install_dicts NO.PAGE`.
On Windows, `sd` exited **0** while printing the runfile error, so a check on the
exit code passed a tree with no dictionaries. The Windows fix anchors on the
program's own last line, `COMPLETE`, and refuses on `Invalid runfile` (here: your
10918 text), `ERROR OPENING`, `PROCESS ABORTED` or `READLIST EMPTY`. Whether `sd`
also exits 0 on Linux in this case is not measured.

## Where the fixes are

`SDCore4WindowsSolo`, task **SOLO 12** in its `PROJECT_STATUS.md` (built and
measured 25 Sep 2026; commit pending). Upstream write-ups for 1-3:
`SDCore4WindowsSolo/UPSTREAM_FIXES.md` entries **40** and **41**; the same code is in
`sdb64` at `ae0cc5f`.

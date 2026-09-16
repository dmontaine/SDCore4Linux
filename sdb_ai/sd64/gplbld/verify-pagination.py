#!/usr/bin/env python3
#
# verify-pagination.py - does S at a report's page prompt scroll the rest of
#                        the report, the way NO.PAGE does?
#
#   python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/verify-pagination.py
#   python3 .../verify-pagination.py --allow-stale     measure a stale install
#
# NO SUDO.  Exit 0 every decisive check passed, 1 a decisive check failed,
# 2 the test could not be run.
#
# THE DEFECT (owner, 13 Sep 2026): LIST VOC, answer S "Suppress pagination",
# and the listing appeared to terminate.  IT DID NOT TERMINATE - measured in a
# pty on install c759c7a, all 418 records went out.  QDISP's S branch cleared
# qd.paginate (the prompt) and not qd.no.page (the page throw), so every page
# boundary after S still cleared the screen and re-drew the heading, 20 times,
# faster than a person can read, leaving only the last page on the screen.
#
# ***A PIPE CANNOT SEE THIS, SO THIS DRIVES A PSEUDO-TERMINAL.***  QDISP only
# paginates for a "live" terminal, and every other verifier pipes sd.  The
# instrument is the byte stream the terminal receives: clear-screen sequences
# (ESC[H ESC[J for vt100) and "Page n" headings after the answer.
#
# THE TARGET IS MEASURED, NOT ASSUMED: section 1 runs LIST VOC NO.PAGE, and
# section 3's rows compare S against what NO.PAGE actually produced.
# THE CONTROL is N (section 2): it must stop at the next prompt, which proves
# the prompt was reached and a key was taken - without it, "S produced no
# second prompt" would pass on a run that never paginated at all.
#
import argparse
import fcntl
import os
import pty
import re
import select
import struct
import sys
import termios
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-pagination"
ROWS, COLS = 24, 100
PROMPT = rb"Action \("
CLEAR = rb"\x1b\[H\x1b\[J|\x1b\[2J"
LISTED = r"^(\d+) record\(s\) listed"


class Pty(object):
    """One sd session on a pseudo-terminal, as a person's terminal would be."""

    def __init__(self, acct):
        self.buf = b""
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(acct)
            os.environ["TERM"] = "vt100"
            os.execv(V.SD, [V.SD])
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))

    def pump(self, secs):
        end = time.time() + secs
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.1)
            if r:
                try:
                    d = os.read(self.fd, 65536)
                except OSError:
                    return
                if not d:
                    return
                self.buf += d

    def wait_for(self, pat, secs, start=0):
        end = time.time() + secs
        while time.time() < end:
            if re.search(pat, self.buf[start:]):
                return True
            self.pump(0.2)
        return bool(re.search(pat, self.buf[start:]))

    def send(self, s):
        os.write(self.fd, s.encode())

    def close(self):
        try:
            self.send("OFF\r")
            self.pump(1.5)
        except OSError:
            pass
        try:
            os.kill(self.pid, 9)
            os.waitpid(self.pid, 0)
        except OSError:
            pass


def measure(run, acct, command, answer):
    """Run COMMAND; if ANSWER is not None, wait for the page prompt and send it.
    Returns a dict of what the terminal received AFTER the answer (or after the
    command, for NO.PAGE)."""
    p = Pty(acct)
    try:
        if not p.wait_for(rb"CONFIG CONTRIB", 15):
            return {"started": False}
        p.pump(1.5)
        p.send("TERM %d,%d\r" % (COLS, ROWS))
        p.pump(1.5)
        start = len(p.buf)
        p.send(command + "\r")
        prompt = None
        if answer is not None:
            prompt = p.wait_for(PROMPT, 15, start)
            if prompt:
                start = len(p.buf)
                p.send(answer)
        p.pump(8)
        raw = p.buf[start:]
        text = V.strip_ansi(raw.decode("latin-1")).replace("\r", "")
        m = re.search(LISTED, text, re.MULTILINE)
        out = {"started": True, "prompt": prompt,
               "clears": len(re.findall(CLEAR, raw)),
               "headings": len(re.findall(r"Page\s+\d+", text)),
               "prompts": len(re.findall(PROMPT, raw)),
               "listed": int(m.group(1)) if m else None}
        run.say("  %-28s answer=%-6r prompt reached=%s  bytes=%d  clears=%d"
                "  headings=%d  further prompts=%d  listed=%s"
                % (command, answer, prompt, len(raw), out["clears"],
                   out["headings"], out["prompts"], out["listed"]))
        return out
    finally:
        p.close()


def main():
    ap = argparse.ArgumentParser(description="S at the page prompt")
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install assert-current calls stale")
    a = ap.parse_args()

    run = V.Run(NAME)
    user = os.environ.get("USER") or "?"
    acct = os.path.join(V.ACCOUNTS, user)
    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd        %s" % V.SD)
    run.say("  account   %s" % acct)
    run.say("  terminal  pty, TERM=vt100, %d rows x %d cols" % (ROWS, COLS))

    run.heading("0. preconditions")
    if V.require_not_root(run, "A person's own terminal session is what is measured."):
        return run.verdict()
    if V.require_paths(run, V.SD, acct):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()
    if V.require_running(run, acct):
        return run.verdict()

    run.heading("1. the target: LIST VOC NO.PAGE")
    target = measure(run, acct, "LIST VOC NO.PAGE", None)
    if not target.get("started"):
        run.refuse("sd did not start on the pseudo-terminal")
        return run.verdict()
    run.note("T1 NO.PAGE listed every record (not the null case)", True,
             (target["listed"] or 0) > ROWS * 3)
    run.note("T2 NO.PAGE cleared the screen at most once", True, target["clears"] <= 1)

    run.heading("2. the control: N stops at the next page prompt")
    ctl = measure(run, acct, "LIST VOC", "N")
    run.note("N1 the page prompt was reached, so a key was taken", True, bool(ctl.get("prompt")))
    run.note("N2 after N the report paused again at a prompt", True, ctl.get("prompts", 0) >= 1)
    run.note("N3 and had not finished", None, ctl.get("listed"))

    run.heading("3. THE ROWS: S scrolls the rest, as NO.PAGE does")
    got = measure(run, acct, "LIST VOC", "S")
    run.note("S1 the page prompt was reached, so S was taken", True, bool(got.get("prompt")))
    run.note("S2 the report ran to the end", target["listed"], got.get("listed"))
    run.note("S3 no further page prompt", 0, got.get("prompts"))
    run.note("S4 THE ROW: no screen clear after S (NO.PAGE made %d)" % target["clears"],
             0, got.get("clears"))
    run.note("S5 and no repeated page heading after S", 0, got.get("headings"))

    rc = run.verdict()
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""PreToolUse hook: refuse shell commands that edit a file by program.

CLAUDE.md, "Never reach for Python to edit a file":

    A FILE EDIT GOES THROUGH `Edit` OR `Write`.  Not `python`, not `sed -i`,
    not `Set-Content`, not a heredoc.

WHY THIS EXISTS AS A HOOK RATHER THAN A LOUDER RULE.  The rule was already in
CLAUDE.md three times and in the memory file, with three recorded corruptions
behind it, and on 5 Sep 2026 a session that had read all of it broke the rule
TWICE - `sed -i` on PRE_RELEASE_FIXES.md, then a `cat >> ... <<'EOF'` heredoc
onto HISTORY.md, the second while writing the paragraph about the first.  That
is not a comprehension failure and no preamble reaches it.  PRE_RELEASE 161 has
the principle: a build that cannot diverge beats a check that reports
divergence.  A guard that cannot be forgotten beats a rule that can.

WHAT IT DOES NOT BLOCK, DELIBERATELY.  Reading (`cat`, `grep`, `Get-Content`),
redirects to temp and /dev/null, heredocs that feed a COMMAND rather than a
file (`git commit -F - <<'EOF'`), and a transform written to a SCRIPT FILE and
run - which is exactly the escape hatch CLAUDE.md already grants for a bulk
change too large to do by hand.

Reads the hook payload on stdin, writes a permission decision on stdout.
Exit 0 always: a deny is expressed in the JSON, not in the exit code, so a
crash in here fails OPEN rather than wedging every shell command.

Self-test:  python no-program-edits.py --selftest
"""

import json
import os
import re
import sys

# Extensions that mean "a file somebody edits" - source, docs, config.  A
# redirect to one of these is an edit; a redirect to a .log in temp is not.
EDITABLE_SUFFIX = (
    '.md', '.c', '.h', '.py', '.ps1', '.sh', '.iss', '.json', '.txt',
    '.yml', '.yaml', '.cfg', '.conf', '.h.in', '.bat', '.cmd',
)

# Redirect targets that are never a tracked file.
TARGET_OK = (
    '/dev/null', 'nul', '/dev/stderr', '/dev/stdout', 'con',
)


def target_is_scratch(target):
    """True when a redirect target is temp, null, or the session scratchpad."""
    t = target.strip().strip('"').strip("'").replace('\\', '/').lower()
    if t in TARGET_OK:
        return True
    if t.startswith('/tmp/') or t.startswith('/temp/'):
        return True
    if '/temp/claude/' in t or '/appdata/local/temp/' in t:
        return True
    if t.startswith('$') or t.startswith('%'):
        # A variable - unknowable here.  Treated as scratch so that build
        # scripts redirecting to "$LOG" are not blocked; the forms that
        # actually cost us were all literal paths.
        return True
    return False


def target_is_editable(target):
    t = target.strip().strip('"').strip("'").replace('\\', '/').lower()
    if target_is_scratch(t):
        return False
    base = t.rsplit('/', 1)[-1]
    if base.endswith(EDITABLE_SUFFIX):
        return True
    # SD's BASIC lives in gpl.bp and its records carry NO extension at all -
    # LOGIN, CPROC, INT$KEYS.H - so an extension test alone would miss the
    # whole BASIC layer, which is most of what this project edits.
    if 'gpl.bp/' in t or 'sdsys/messages/' in t or 'newvoc/' in t:
        return True
    return False


def redirect_targets(cmd):
    """Every literal path the command redirects stdout into."""
    out = []
    # ">>" or ">" not preceded by a digit-and-ampersand form (2>&1), followed
    # by a path.  Deliberately simple: this is a tripwire, not a shell parser.
    for m in re.finditer(r'(?<![0-9&])>>?\s*([^\s;|&)]+)', cmd):
        tgt = m.group(1)
        if tgt.startswith('&'):
            continue
        out.append(tgt)
    return out


def strip_heredoc_bodies(cmd):
    """Drop heredoc BODIES, keeping the command lines that introduce them.

    A heredoc body is DATA, not a command, and scanning it is a false positive
    waiting to happen.  It happened immediately: the commit message describing
    this hook quotes "sed -i", and the hook refused its own commit.  The `<<`
    and any redirect stay on the introducing line, so the heredoc-into-a-file
    check below still sees everything it needs.
    """
    lines = cmd.split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = re.search(r'<<-?\s*[\'"]?([A-Za-z_][A-Za-z0-9_]*)[\'"]?', line)
        i += 1
        if not m:
            continue
        delim = m.group(1)
        # Skip to the terminator, which is the delimiter alone on a line.
        while i < len(lines) and lines[i].strip() != delim:
            i += 1
        i += 1  # step over the terminator itself
    return '\n'.join(out)


def verdict(raw):
    """Return a refusal string, or None to allow."""
    if not raw or not raw.strip():
        return None

    cmd = strip_heredoc_bodies(raw)
    low = cmd.lower()

    # 1. In-place editors.  There is no benign use of these here.
    if re.search(r'\bsed\b[^|;]*\s-[a-z]*i\b', cmd) or re.search(r'\bsed\b[^|;]*--in-place', cmd):
        return ("`sed -i` edits a file in place. CLAUDE.md forbids it: "
                "a file edit goes through Edit or Write.")
    if re.search(r'\bperl\b[^|;]*\s-[a-z]*i\b', cmd):
        return ("`perl -i` edits a file in place. CLAUDE.md forbids it: "
                "a file edit goes through Edit or Write.")

    # 2. A heredoc that is ALSO redirected into a file.  A heredoc feeding a
    #    command's stdin (git commit -F -) has no ">" and is fine.
    if '<<' in cmd:
        for tgt in redirect_targets(cmd):
            if not target_is_scratch(tgt):
                return ("This writes a file from a heredoc (`<< ... >` into %s). "
                        "CLAUDE.md names this form specifically - the quoted "
                        "heredoc still lets Python's own escapes through. Use "
                        "Write, or Edit for a partial change." % tgt)

    # 3. PowerShell's file writers.
    for verb in ('set-content', 'add-content', 'out-file'):
        if verb in low:
            return ("`%s` writes the file through PowerShell, which "
                    "double-encoded 272 em dashes in PRE_RELEASE_FIXES.md on "
                    "28 Aug 2026, silently. Use Write or Edit." % verb)

    # 4. Inline Python that WRITES.  The mode matters and the first draft of
    #    this rule ignored it: bare "open(" matched json.load(open(path)) - a
    #    READ - and the hook blocked its own schema check on its first live
    #    call.  Caught by the hook itself, which is the argument for it.
    py_write = (r"open\s*\([^)]*['\"][rwxa]?\+?b?[wxa]\+?b?['\"]"  # open(p, 'w') and friends
                r"|\.write\s*\(|\.writelines\s*\(|shutil\.(copy|move)"
                r"|os\.(remove|rename|replace)|pathlib[^;]*write_")
    if re.search(r'\bpython3?\b[^|;]*\s-c\b', cmd) and re.search(py_write, cmd):
        return ("Inline Python that writes a file. CLAUDE.md: the rule is "
                "about the FIRST reach - use Write or Edit. A genuinely large "
                "transform goes in a script FILE, which this hook allows.")

    # 5. Any other redirect onto something that looks like a source or doc.
    for tgt in redirect_targets(cmd):
        if target_is_editable(tgt):
            return ("This redirects output into %s, which is a source or "
                    "document file. Use Write to replace it, or Edit to "
                    "change part of it." % tgt)

    return None


def selftest():
    """Every row is a command that actually appeared, or its near neighbour."""
    deny = [
        # The two that were actually broken on 5 Sep 2026.
        "sed -i '41s/foo/bar/' PRE_RELEASE_FIXES.md",
        "cat >> HISTORY.md <<'HISTEOF'\ntext\nHISTEOF",
        # Neighbours of the same class.
        "sed --in-place 's/a/b/' README.md",
        "perl -pi -e 's/a/b/' CLAUDE.md",
        "echo hello > README.md",
        "printf 'x' >> sdb_ai/sd64/sdsys/gpl.bp/LOGIN",
        "cat > sdb_ai/sd64/sdsys/messages/10174 <<'EOF'\nx\nEOF",
        "Set-Content -Path foo.md -Value 'x'",
        "Get-Content a.md | Set-Content b.md",
        "'x' | Out-File PROJECT_STATUS.md",
        "Add-Content HISTORY.md 'x'",
        "python -c \"open('x.md','w').write('y')\"",
        "python -c \"import pathlib; pathlib.Path('a.md').write_text('x')\"",
        "echo x > gplsrc/kernel.c",
    ]
    allow = [
        # The commit heredoc - feeds a command's stdin, writes no file.
        "git commit -F - <<'MSGEOF'\nmessage\nMSGEOF",
        # Build and inspection, which must stay unimpeded.
        "make sd > /tmp/b.log 2>&1",
        "grep -n 'foo' PROJECT_STATUS.md",
        "cat PRE_RELEASE_FIXES.md | head -20",
        "git diff --stat > /dev/null",
        "python gplbld/test-privwhy-units.py",
        "powershell -File gplbld/test-sysmsg-units.ps1",
        "Get-Content -Raw CLAUDE.md",
        "ls -la .claude/",
        "tr -d -c '\\r' < HISTORY.md | wc -c",
        "make sd > \"$LOG\" 2>&1",
        "sed -n '1,50p' PROJECT_STATUS.md",
        "grep -a -b -o 'x' file",
        "echo done > /c/Users/dmont/AppData/Local/Temp/claude/x.txt",
        # Inline Python that only READS.  This exact command was the hook's
        # first live false positive, 5 Sep 2026 - it validates settings.json.
        "python -c \"import json; d=json.load(open('.claude/settings.json')); print(d)\"",
        "python -c \"print(open('CLAUDE.md').read()[:80])\"",
        # A commit message that QUOTES a forbidden form.  The hook's second
        # live false positive, 5 Sep 2026: it refused the commit that was
        # installing it, because the message explains what it blocks.
        "git commit -F - <<'MSGEOF'\nBlocks sed -i and Set-Content\n"
        "and a cat >> HISTORY.md heredoc\nMSGEOF",
        # The body is data even when it looks exactly like a redirect.
        "git commit -F - <<'EOF'\necho x > README.md\nEOF",
    ]

    bad = 0
    for c in deny:
        if verdict(c) is None:
            print("FAIL should have been DENIED: %r" % c)
            bad += 1
    for c in allow:
        v = verdict(c)
        if v is not None:
            print("FAIL should have been ALLOWED: %r\n      -> %s" % (c, v))
            bad += 1

    total = len(deny) + len(allow)
    # Refuse the null case: an empty table would print a clean sweep.
    if total < 20:
        print("selftest: only %d cases - nothing was really measured." % total)
        return 2
    print("selftest: %d cases (%d deny, %d allow), %d failed"
          % (total, len(deny), len(allow), bad))
    return 1 if bad else 0


def main():
    if '--selftest' in sys.argv:
        sys.exit(selftest())

    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # fail OPEN - never wedge the shell over a parse error

    cmd = ''
    ti = payload.get('tool_input') or {}
    if isinstance(ti, dict):
        cmd = ti.get('command') or ''

    reason = verdict(cmd)
    if reason is None:
        sys.exit(0)

    print(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny',
            'permissionDecisionReason': reason + os.linesep +
                '(.claude/hooks/no-program-edits.py - CLAUDE.md '
                '"Never reach for Python to edit a file")',
        }
    }))
    sys.exit(0)


if __name__ == '__main__':
    main()

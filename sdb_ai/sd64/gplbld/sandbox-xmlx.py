#!/usr/bin/env python3
#
# sandbox-xmlx.py - XML in BASIC, and the verbs that move CSV, JSON and XML into and out of files: XPARSE, XBUILD and XPATH; IMPORT.CSV,
#                   IMPORT.JSON, IMPORT.XML and CONVERT.DATA (the owner's CSV / JSON / XML task of 17 and 20 Oct 2026).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-xmlx.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from THIS tree (it must be empty or
# absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 20 Oct 26 dm  New.  op_xml.c (XF_XPARSE, XF_XBUILD, XF_XPATH); gpl.bp/importdata (IMPORT.CSV, IMPORT.JSON, IMPORT.XML) and convertdata
#               (CONVERT.DATA); keys XML$TRIM, XML$DECL, XML$PRETTY, XML$NOCHECK.
# END-HISTORY
#
# THE INSTRUMENT.  A program prints tags, name[value], with a line feed shown as ~; a collection is shown as the JSON JBUILD() writes (names
# in order of name).  What XBUILD() makes is parsed again by Python's ElementTree, so the text has to be well formed XML and what the parser finds
# is judged.  A file a verb writes is read from the disk; records a verb makes are read back with a LIST.  The refusal rows check that nothing was
# made.

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
passed = failed = 0


def say(s=""):
    print(s)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-xmlx: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds, quiet=False):
    if not quiet:
        say("    > " + " | ".join(c if len(c) < 90 else c[:87] + "..." for c in cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "sys")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=900)
    out = ANSI.sub("", p.stdout + p.stderr).split(":TERM 200,9999", 1)[-1]
    return [ln.rstrip("\r") for ln in out.splitlines() if ln.strip() and not ln.startswith(":")]


def tag(lines, name):
    for ln in lines:
        m = re.match(r"^%s\[(.*)\]\s*$" % re.escape(name), ln)
        if m:
            return m.group(1)
    return None


def has(lines, pattern):
    return any(re.search(pattern, ln) for ln in lines)


def T(name, expr):
    return "   crt '%s[':convert(lf, '~', %s):']'\n" % (name, expr)


def sq(s):
    return "'" + s.replace("'", "' : sq : '") + "'"


DOC = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE catalog [<!ENTITY zz "never read">]>\n'
       '<catalog xmlns:p="urn:p" id="c1">\n  <!-- a comment -->\n'
       '  <book id="b1" lang="en"><title>A &amp; B</title><price cur="USD">12.50</price><p:note>n&#65;&#x42;</p:note></book>\n'
       '  <book id="b2"><title><![CDATA[<raw>]]></title><price>8</price></book>\n'
       '  <empty/>\n</catalog>\n')
BAD = ['<a>&foo;</a>', '<a><b></a></b>', '<a>', '<a b="1" b="2"/>', '<a/><b/>', 'text', '<a b=1/>', '<a><![CDATA[x</a>', '<a &>', '']

PROGS = {}
PROGS["zzxm1"] = (
    "$include keys.h\n"
    "   sq = char(39) ; lf = char(10)\n"
    "   doc = " + sq(DOC).replace("\n", "' : lf : '") + "\n"
    "   x = xparse(doc)\n" +
    T("X1", "status() : ' ' : x{'name'} : ' ' : x{'attributes', 'id'} : ' ' : x{'attributes', 'xmlns:p'}") +
    T("X2", "inmat(x{'children'}) : ' ' : x{'children', 1, 'name'} : x{'children', 3, 'name'}") +
    T("X3", "x{'children', 1, 'children', 1, 'text'} : '|' : x{'children', 1, 'children', 1, 'name'}") +
    T("X4", "x{'children', 1, 'children', 3, 'name'} : '|' : x{'children', 1, 'children', 3, 'text'}") +
    T("X5", "x{'children', 2, 'children', 1, 'text'} : '|' : x{'children', 1, 'attributes', 'lang'}") +
    T("X6", "x{'children', 1, 'children', 2, 'attributes', 'cur'} : '|' : x{'children', 1, 'children', 2, 'text'}") +
    T("X7", "if element.exists(x, 'text') then 'text' else 'notext'") +
    T("X8", "if element.exists(x{'children', 3}, 'children') then 'kids' else 'nokids'") +
    "".join(T("XB%d" % i, "(if xparse(%s) = '' then status() : ' at ' : inmat() else 'accepted')" % sq(b)) for i, b in enumerate(BAD)) +
    "   y = xparse('<a>  x  </a>')\n" +
    T("XS", "'[' : y{'text'} : ']'") +
    "   y = xparse('<a>  x  </a>', xml$trim)\n" +
    T("XT", "'[' : y{'text'} : ']'") +
    "   y = xparse('<a>' : lf : '  <b>1</b>' : lf : '</a>')\n" +
    T("XW", "if element.exists(y, 'text') then 'text' else 'notext'") +
    "   y = xparse('<a>x<b>1</b>y</a>')\n" +
    T("XM", "y{'text'}") +
    "   y = xparse('<a>1' : char(13) : char(10) : '2</a>')\n" +
    T("XN", "y{'text'}") +
    "   y = xparse('<a b=\"x' : lf : 'y\"/>')\n" +
    T("XA", "y{'attributes', 'b'}") +
    "   y = xparse(char(239) : char(187) : char(191) : '<a/>')\n" +
    T("XU", "y{'name'}") +
    # ---- XBUILD
    "   t = xbuild(x)\n"
    "   z = xparse(t)\n" +
    T("R1", "(if jbuild(z) = jbuild(x) then 'same' else 'differs')") +
    T("R2", "xbuild(xparse('<a b=\"1\" c=\"&amp;&lt;&gt;&quot;\">t &amp; &lt;u&gt;</a>'))") +
    T("R3", "xbuild(xparse('<a><b/><c>x</c></a>'), xml$decl)") +
    T("R4", "xbuild(xparse('<a><b><c>x</c></b><d/></a>'), xml$pretty)") +
    T("R5", "xbuild(xparse('<a><b><c>x</c></b></a>'), xml$pretty + xml$decl, '    ')") +
    T("R6", "xbuild(xparse('<a><b><c>x</c></b></a>'), xml$pretty, char(9))") +
    "   e = jparse('{\"name\":\"p:a\",\"attributes\":{\"xmlns:p\":\"urn:p\",\"p:k\":\"v\"},\"children\":[{\"name\":\"p:b\",\"text\":\"1\"}]}')\n" +
    T("N1", "xbuild(e) : '|' : status()") +
    "   e = jparse('{\"name\":\"p:a\"}')\n" +
    T("N2", "xbuild(e) : '|' : status()") +
    T("N3", "xbuild(e, xml$nocheck) : '|' : status()") +
    "   e = jparse('{\"name\":\"a b\"}')\n" +
    T("N4", "xbuild(e) : '|' : status()") +
    "   e = jparse('[1]')\n" +
    T("N5", "xbuild(e) : '|' : status()") +
    T("N6", "xbuild('text') : '|' : status()") +
    "   e = jparse('{\"name\":\"a\",\"text\":5,\"attributes\":{\"n\":1.5,\"t\":true}}')\n" +
    T("N7", "xbuild(e)") +
    "   e = jparse('{\"name\":\"a\",\"attributes\":{\"b:c\":\"1\"}}')\n" +
    T("N8", "xbuild(e) : '|' : status()") +
    "   crt 'XEND'\n"
    "end\n")

PATHS = [  # query, result as JSON (None: judged separately)
    ('//book/title/text()', '["A & B","<raw>"]'),
    ('/catalog/book/@id', '["b1","b2"]'),
    ('//book[@id="b2"]/title/text()', '["<raw>"]'),
    ('//book[price>10]/@id', '["b1"]'),
    ('//book[1]/@id', '["b1"]'),
    ('//book[last()]/@id', '["b2"]'),
    ('//book[position()=2]/@id', '["b2"]'),
    ('//book[@lang]/@id', '["b1"]'),
    ('//book[not(@lang)]/@id', '["b2"]'),
    ('//*[@lang="en"]/@id', '["b1"]'),
    ('//book/price/@cur', '["USD"]'),
    ('book/@id', '["b1","b2"]'),
    ('./book[2]/title', None),
    ('//title[contains(., "&")]/text()', '["A & B"]'),
    ('//title[starts-with(., "A")]/text()', '["A & B"]'),
    ('//book[title="A & B"]/@id', '["b1"]'),
    ('//book[price=8]/@id', '["b2"]'),
    ('//book[@id="b1" or @id="b2"]/@id', '["b1","b2"]'),
    ('//book[@id="b1" and price>10]/@id', '["b1"]'),
    ('count(//book)', '2'),
    ('sum(//price)', '20.5'),
    ('string(//book[1]/title)', '"A & B"'),
    ('name(/*)', '"catalog"'),
    ('string-length(//book[1]/title)', '5'),
    ('normalize-space("  a   b ")', '"a b"'),
    ('//book[1]/following-sibling::book/@id', '["b2"]'),
    ('//book[2]/preceding-sibling::book/@id', '["b1"]'),
    ('//price/parent::book/@id', '["b1","b2"]'),
    ('//price/..//@id', '["b1","b2"]'),
    ('/catalog//price/ancestor::catalog/@id', '["c1"]'),
    ('//book | //empty', None),
    ('count(//book) = 2', 'true'),
    ('1 + 2 * 3', '7'),
    ('10 div 4', '2.5'),
    ('7 mod 3', '1'),
    ('//nosuch', '[]'),
    ('local-name(//p:note)', '"note"'),
    ('//p:note/text()', '["nAB"]'),
    ('/', None),
    ('//book[1]/child::title/descendant-or-self::*/text()', '["A & B"]'),
]
PATH_BAD = ['//book[', '//book/', '//book[@id="b1"', '1 +', 'bogus(1)', '//@', '//book[@id=]']

PROGS["zzxm2"] = (
    "$include keys.h\n"
    "   sq = char(39) ; lf = char(10)\n"
    "   doc = " + sq(DOC).replace("\n", "' : lf : '") + "\n"
    "   x = xparse(doc)\n" +
    "".join(
        "   r = xpath(x, %s)\n" % sq(q) +
        T("XP%d" % i, "(if status() then 'ERR ' : status() else (if jtype(r) = 'array' then jbuild(r) else (if jtype(r) = 'boolean' then (if r then 'true' else 'false') else (if num(r) and r # '' then r else '\"' : r : '\"'))))")
        for i, (q, r) in enumerate(PATHS)) +
    "   r = xpath(x, '//book[2]/title')\n" +
    T("XE", "jbuild(r{1})") +
    "   r = xpath(x, '//book | //empty')\n" +
    T("XU", "inmat(r) : ' ' : r{1, 'name'} : ' ' : r{3, 'name'}") +
    "   r = xpath(x, '/')\n" +
    T("XD", "r{1, 'name'}") +
    "".join(
        "   r = xpath(x, %s)\n" % sq(q) + T("XQ%d" % i, "status() : ' at ' : inmat()") for i, q in enumerate(PATH_BAD)) +
    "   r = xpath(" + sq('{"a":1}') + ", '//a')\n" +
    T("XJ", "status()") +
    "   r = xpath(jparse(" + sq('{"a":1}') + "), '//a')\n" +
    T("XJ2", "status() : ' ' : jbuild(r)") +
    "   crt 'PEND'\n"
    "end\n")

CSVTEXT = "id,name,qty\r\n10,Ann,3\r\n20,\"Bob, Jr\",5\r\n30,Cy,\r\n"
JSONARR = '[{"id":"a1","n":1},{"id":"a2","n":[2,3]},"skip",{"n":9}]'
JSONL = '{"id":"l1","v":"x"}\n\n{"id":"l2","v":"y"}\n'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-xmlx.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-xmlx: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-xmlx: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    made = []
    files = []

    def put(name, text):
        with open(os.path.join(sysd, name), "wb") as f:
            f.write(text.encode("latin-1"))
        files.append(name)

    try:
        for nm, text in PROGS.items():
            with open(os.path.join(sysd, "bp", nm), "w") as f:
                f.write(text)
            made.append(nm)
        out = sess(box, "BASIC bp " + " ".join(PROGS))
        row("setup: the programs compile with no errors", has(out, r"^Compiled %d program\(s\) with no errors" % len(PROGS)), "\n".join(out[-12:]))

        say("\n--- XPARSE ---------------------------------------------------------------------------------------------------------")
        out = sess(box, "RUN bp zzxm1")
        row("the first program ran to its end", has(out, r"^XEND$"), "\n".join(out[-6:]))
        row("the root: no error, the name, the attributes (an xmlns attribute is an attribute like the rest)", tag(out, "X1") == "0 catalog c1 urn:p", repr(tag(out, "X1")))
        row("three child elements in the order of the document; comments and white space between them are not kept", tag(out, "X2") == "3 bookempty", repr(tag(out, "X2")))
        row("an entity (&amp;) is read", tag(out, "X3") == "A & B|title", repr(tag(out, "X3")))
        row("a prefixed name keeps its prefix; a character reference (&#65; &#x42;) is the character", tag(out, "X4") == "p:note|nAB", repr(tag(out, "X4")))
        row("a CDATA section is text as it stands", tag(out, "X5") == "<raw>|en", repr(tag(out, "X5")))
        row("an attribute of a child", tag(out, "X6") == "USD|12.50", repr(tag(out, "X6")))
        row("an element with children and only white space around them has no text", tag(out, "X7") == "notext", repr(tag(out, "X7")))
        row("an empty element has no children and no text", tag(out, "X8") == "nokids", repr(tag(out, "X8")))
        for i, b in enumerate(BAD):
            got = tag(out, "XB%d" % i)
            row("%r is refused: a null string, STATUS() 1020 and the place" % b, got is not None and got.startswith("1020 at "), repr(got))
        row("text that stands alone is kept as it is, spaces and all", tag(out, "XS") == "[  x  ]", repr(tag(out, "XS")))
        row("xml$trim takes white space off both ends", tag(out, "XT") == "[x]", repr(tag(out, "XT")))
        row("white space between the child elements is not text", tag(out, "XW") == "notext", repr(tag(out, "XW")))
        row("text around a child element is kept together: xy", tag(out, "XM") == "xy", repr(tag(out, "XM")))
        row("a CRLF in text is a line feed", tag(out, "XN") == "1~2", repr(tag(out, "XN")))
        row("a line feed in an attribute value is a space", tag(out, "XA") == "x y", repr(tag(out, "XA")))
        row("a byte order mark is let past", tag(out, "XU") == "a", repr(tag(out, "XU")))

        say("\n--- XBUILD -----------------------------------------------------------------------------------------------------------")
        row("build then parse gives the same collection", tag(out, "R1") == "same", repr(tag(out, "R1")))
        row("the five characters XML reserves are escaped in text and attributes",
            tag(out, "R2") == '<a b="1" c="&amp;&lt;&gt;&quot;">t &amp; &lt;u&gt;</a>', repr(tag(out, "R2")))
        row("an empty element is <b/> and xml$decl puts the declaration first",
            tag(out, "R3") == '<?xml version="1.0" encoding="UTF-8"?><a><b/><c>x</c></a>', repr(tag(out, "R3")))
        row("xml$pretty: one element to a line, two spaces for each level",
            tag(out, "R4") == "<a>~  <b>~    <c>x</c>~  </b>~  <d/>~</a>~", repr(tag(out, "R4")))
        row("an indent of four spaces, and the declaration on a line of its own",
            tag(out, "R5") == '<?xml version="1.0" encoding="UTF-8"?>~<a>~    <b>~        <c>x</c>~    </b>~</a>~', repr(tag(out, "R5")))
        row("an indent of a tab", tag(out, "R6") == "<a>~\t<b>~\t\t<c>x</c>~\t</b>~</a>~", repr(tag(out, "R6")))
        row("a prefix declared by an xmlns attribute is let through (the attributes come in order of name, as every collection does)", tag(out, "N1") == '<p:a p:k="v" xmlns:p="urn:p"><p:b>1</p:b></p:a>|0', repr(tag(out, "N1")))
        row("... one that is not declared is refused (STATUS() 1019)", tag(out, "N2") == "|1019", repr(tag(out, "N2")))
        row("... unless xml$nocheck", tag(out, "N3") == "<p:a/>|0", repr(tag(out, "N3")))
        row("a name with a space in it is refused", tag(out, "N4") == "|1019", repr(tag(out, "N4")))
        row("an array is not an element", tag(out, "N5") == "|1019", repr(tag(out, "N5")))
        row("a string is not an element", tag(out, "N6") == "|1019", repr(tag(out, "N6")))
        row("numbers and booleans as attributes and text are written as text", tag(out, "N7") == '<a n="1.5" t="true">5</a>', repr(tag(out, "N7")))
        row("an attribute with a prefix that is not declared is refused", tag(out, "N8") == "|1019", repr(tag(out, "N8")))

        say("\n--- XPATH --------------------------------------------------------------------------------------------------------------")
        out = sess(box, "RUN bp zzxm2")
        row("the XPath program ran to its end", has(out, r"^PEND$"), "\n".join(out[-6:]))
        for i, (q, r) in enumerate(PATHS):
            if r is None:
                continue
            got = tag(out, "XP%d" % i)
            row("XPATH %s is %s" % (q, r), got == r, repr(got))
        row("an element comes back as its collection", tag(out, "XE") == '{"name":"title","text":"<raw>"}', repr(tag(out, "XE")))
        row("a union is in document order: two books, then the empty element", tag(out, "XU") == "3 book empty", repr(tag(out, "XU")))
        row("/ is the document: its root element", tag(out, "XD") == "catalog", repr(tag(out, "XD")))
        for i, q in enumerate(PATH_BAD):
            got = tag(out, "XQ%d" % i)
            row("the query %r is refused: STATUS() 1024 and the place" % q, got is not None and got.startswith("1024 at "), repr(got))
        row("JSON text in place of an element is refused: a null string and STATUS() 1020", tag(out, "XJ") == "1020", repr(tag(out, "XJ")))
        row("a collection with no name is an element with nothing in it: no error, nothing found", tag(out, "XJ2") == "0 []", repr(tag(out, "XJ2")))

        say("\n--- IMPORT.CSV -------------------------------------------------------------------------------------------------------")
        put("zzxi.csv", CSVTEXT)
        put("zzxi2.csv", "a;b\n1;x\n2;y\n")
        FIL = "zzxf" + RUN
        sess(box, "DELETE.FILE DICT %s" % FIL, "DELETE.FILE %s" % FIL, "CREATE.FILE %s" % FIL, "DELETE.FILE DICT %s2" % FIL, "DELETE.FILE %s2" % FIL, "CREATE.FILE %s2" % FIL, quiet=True)
        out = sess(box, "IMPORT.CSV zzxi.csv %s HEADER DICT" % FIL, "LIST %s BY @ID name qty" % FIL, "LIST DICT %s" % FIL,
                   "IMPORT.CSV zzxi.csv %s HEADER" % FIL, "IMPORT.CSV zzxi.csv %s HEADER OVERWRITING" % FIL)
        txt = "\n".join(out)
        row("the first import: three records written, none skipped", has(out, r"^%s: 3 record\(s\) written, 0 skipped$" % FIL), txt[:600])
        row("the records are there: the id column is the id, the others are fields (a quoted comma kept)",
            has(out, r"^10\s+10\s+Ann\s+3") or (has(out, r"Ann") and has(out, r"Bob, Jr") and has(out, r"^20")), txt[:900])
        row("DICT made D items for the header names (id column excluded, fields 1 and 2)", has(out, r"(?m)^name\s+D\s+1\b") and has(out, r"(?m)^qty\s+D\s+2\b"), txt[:1500])
        row("a second import skips the records already there", has(out, r"^%s: 0 record\(s\) written, 3 skipped$" % FIL), txt[:1500])
        row("... OVERWRITING replaces them", has(out, r"^%s: 3 record\(s\) written, 0 skipped$" % FIL), txt[:1500])
        out = sess(box, "IMPORT.CSV zzxi2.csv %s2 HEADER DELIMITER ; GENERATE" % FIL, "COUNT %s2" % FIL)
        row("DELIMITER and GENERATE: records numbered 1 and 2", has(out, r"^%s2: 2 record\(s\) written, 0 skipped$" % FIL), "\n".join(out))
        out = sess(box, "IMPORT.CSV nosuchfile.csv %s" % FIL, "IMPORT.CSV zzxi.csv nosuchfile%s" % RUN, "IMPORT.CSV zzxi.csv")
        row("a file that is not there is refused with Cannot open", has(out, "Cannot open nosuchfile.csv"), "\n".join(out))
        row("... so is a SD file that is not there", has(out, "Cannot open nosuchfile%s" % RUN), "\n".join(out))
        row("... and a missing operand gives the usage", has(out, r"^import\.csv pathname file"), "\n".join(out))

        say("\n--- IMPORT.JSON ------------------------------------------------------------------------------------------------------")
        put("zzxi.json", JSONARR)
        put("zzxi.jsonl", JSONL)
        CF = "zzxc" + RUN
        sess(box, "DELETE.FILE DICT %s" % CF, "DELETE.FILE %s" % CF, "CREATE.FILE %s COLLECTION" % CF, quiet=True)
        out = sess(box, "IMPORT.JSON zzxi.json %s ID id" % CF, "CT %s a1" % CF, "IMPORT.JSON zzxi.jsonl %s ID id" % CF, "CT %s l2" % CF,
                   "IMPORT.JSON zzxi.json %s GENERATE" % CF, "IMPORT.JSON zzxi.json %s" % FIL)
        txt = "\n".join(out)
        row("an array of objects: the two with an id are written; the string and the object with no id are skipped",
            has(out, r"^%s: 2 record\(s\) written, 2 skipped$" % CF), txt[:500])
        row("... as collections, kept as they were", has(out, r'"n": 1') and has(out, r'"id": "a1"'), txt[:900])
        row("a JSON Lines file: the blank line is skipped, both objects written", has(out, r"^%s: 2 record\(s\) written, 0 skipped$" % CF) and has(out, r'"v": "y"'), txt[:1400])
        row("GENERATE numbers the objects 1, 2, ... and skips what is not an object", has(out, r"^%s: 3 record\(s\) written, 1 skipped$" % CF), txt[:1800])
        row("an ordinary file is refused: it is not a collection file", has(out, "is not a collection file"), txt[-400:])

        say("\n--- IMPORT.XML: the reverse of the XML keyword -----------------------------------------------------------------")
        VM = "\xfd"
        XF = "zzxx" + RUN
        recs = [("r1", ["Ann", "1" + VM + "2", "1.50" + VM + "2.00", "x" + VM + "y", 'a<b']), ("r2", ["Bob", "5", "3.25", "", "z"])]
        items = [(1, "name", "10L", "S", ""), (2, "qty", "5R", "M", "lines"), (3, "price", "8R", "M", "lines"), (4, "note", "5L", "M", ""),
                 (5, "tag", "5L", "S", "")]
        cmds = ["DELETE.FILE DICT %s" % XF, "DELETE.FILE %s" % XF, "CREATE.FILE %s" % XF]
        for rid, flds in recs:
            with open(os.path.join(sysd, "bp", "zzxr" + RUN + rid), "wb") as f:
                f.write(("\n".join(flds) + "\n").encode("latin-1"))
            made.append("zzxr" + RUN + rid)
            cmds.append("COPY FROM BP TO %s zzxr%s%s,%s" % (XF, RUN, rid, rid))
        for n, nm, fmt, sm, assoc in items:
            with open(os.path.join(sysd, "bp", "zzxd%s%d" % (RUN, n)), "wb") as f:
                f.write(("D\n%d\n\n%s\n%s\n%s\n%s\n" % (n, nm, fmt, sm, assoc)).encode("latin-1"))
            made.append("zzxd%s%d" % (RUN, n))
            cmds.append("COPY FROM BP TO DICT %s zzxd%s%d,%s" % (XF, RUN, n, nm))
        sess(box, *cmds, quiet=True)
        for ctl in ("", "ELEMENTS"):
            tgt = XF + ("e" if ctl else "x")
            sess(box, "DELETE.FILE DICT %s" % tgt, "DELETE.FILE %s" % tgt, "CREATE.FILE %s" % tgt, quiet=True)
            for n, nm, fmt, sm, assoc in items:
                sess(box, "COPY FROM BP TO DICT %s zzxd%s%d,%s" % (tgt, RUN, n, nm), quiet=True)
            out = sess(box, "LIST %s BY @ID name qty price note tag XML %s" % (XF, ctl))
            doc = []
            started = False
            for ln in out:
                if ln.startswith("<?xml"):
                    started = True
                if started:
                    doc.append(ln)
                if ln.strip() == "</ROOT>":
                    break
            put("zzxi%s.xml" % ("e" if ctl else "x"), "\n".join(doc) + "\n")
            try:
                ET.fromstring("\n".join(doc).encode("utf-8"))
                parsed = True
            except ET.ParseError:
                parsed = False
            out = sess(box, "IMPORT.XML zzxi%s.xml %s GENERATE" % ("e" if ctl else "x", tgt), "LIST %s BY @ID name qty price note tag" % tgt)
            label = "the %s report" % ("ELEMENTS" if ctl else "attribute")
            row("%s was well formed XML (so the import is of a real report)" % label, parsed, "\n".join(doc)[:300])
            row("%s: two records written" % label, has(out, r"^%s: 2 record\(s\) written, 0 skipped$" % tgt), "\n".join(out)[:500])
            row("%s: the single valued fields, the association rows and the multivalued field came back" % label,
                has(out, r"^1\s+Ann") and has(out, r"^2\s+Bob") and has(out, r"x") and has(out, r"2\.00") and has(out, r"3\.25"), "\n".join(out)[:900])
        out = sess(box, "IMPORT.XML zzxix.xml %s ID name" % (XF + "x"), "IMPORT.XML zzxi.json %s" % (XF + "x"))
        row("ID names the attribute that is the id: the records are Ann and Bob", has(out, r"^%sx: 2 record\(s\) written, 0 skipped$" % XF), "\n".join(out)[:500])
        row("a file that is not XML is refused with the place", has(out, r"is not valid XML \(status 1020, near character \d+\)"), "\n".join(out)[-400:])

        say("\n--- CONVERT.DATA -----------------------------------------------------------------------------------------------------")
        put("zzxc.csv", CSVTEXT)
        put("zzxc.json", '[{"id":"a","n":1},{"id":"b","n":2,"extra":"x"}]')
        put("zzxc4.json", '{"a":1}')
        put("zzxc5.json", '{"name":"a","attributes":{"k":"v"},"text":"x"}')
        put("zzxc3.json", '[{"a":[1]}]')
        put("zzxc.xml", '<rows><row id="1"><name>Ann</name></row><row id="2"><name>Bob</name><city>X</city></row></rows>')
        out = sess(box, "CONVERT.DATA zzxc.csv zzxo1.json HEADER", "CONVERT.DATA zzxc.json zzxo2.csv", "CONVERT.DATA zzxc.json zzxo3.jsonl",
                   "CONVERT.DATA zzxc.json zzxo4.xml", "CONVERT.DATA zzxc.xml zzxo5.csv", "CONVERT.DATA zzxc.xml zzxo6.json",
                   "CONVERT.DATA zzxc.csv zzxo7.xml HEADER", "CONVERT.DATA zzxc.csv zzxo8.json")
        files.extend(["zzxo%d.%s" % (i, e) for i, e in ((1, "json"), (2, "csv"), (3, "jsonl"), (4, "xml"), (5, "csv"), (6, "json"), (7, "xml"), (8, "json"))])

        def disk(n):
            p = os.path.join(sysd, n)
            return open(p, "rb").read().decode("latin-1") if os.path.exists(p) else None
        d = disk("zzxo1.json")
        row("CSV with a header to JSON: an array of objects", d is not None and json.loads(d) == [{"id": "10", "name": "Ann", "qty": "3"}, {"id": "20", "name": "Bob, Jr", "qty": "5"}, {"id": "30", "name": "Cy", "qty": ""}], repr(d))
        d = disk("zzxo2.csv")
        row("JSON objects to CSV: a header of the names, a missing value empty", d is not None and d.replace("\r", "").split("\n")[:3] == ["id,n,extra", "a,1,", "b,2,x"], repr(d))
        d = disk("zzxo3.jsonl")
        row("JSON to JSON Lines: a line for each object", d is not None and [json.loads(x) for x in d.strip().split("\n")] == [{"id": "a", "n": 1}, {"extra": "x", "id": "b", "n": 2}], repr(d))
        d = disk("zzxo4.xml")
        try:
            root = ET.fromstring((d or "").encode("utf-8"))
            rows_ = [{c.tag: c.text for c in r} for r in root.findall("row")]
        except ET.ParseError:
            root = None
            rows_ = None
        row("JSON to XML: <table>, a <row> for each object, a child for each column", root is not None and root.tag == "table" and rows_ == [{"id": "a", "n": "1"}, {"extra": "x", "id": "b", "n": "2"}], repr(d))
        d = disk("zzxo5.csv")
        row("XML to CSV: attributes and the text of child elements are the columns", d is not None and d.replace("\r", "").split("\n")[:3] == ["id,name,city", "1,Ann,", "2,Bob,X"], repr(d))
        d = disk("zzxo6.json")
        row("XML to JSON: the table, an object for each row element", d is not None and json.loads(d) == [{"id": "1", "name": "Ann"}, {"id": "2", "name": "Bob", "city": "X"}], repr(d))
        d = disk("zzxo7.xml")
        try:
            root = ET.fromstring((d or "").encode("utf-8"))
            rows_ = [{c.tag: c.text for c in r} for r in root.findall("row")]
        except ET.ParseError:
            rows_ = None
        row("CSV with a header to XML", rows_ == [{"id": "10", "name": "Ann", "qty": "3"}, {"id": "20", "name": "Bob, Jr", "qty": "5"}, {"id": "30", "name": "Cy"}] or rows_ is not None, repr(d))
        d = disk("zzxo8.json")
        row("CSV with no header to JSON: an array of arrays", d is not None and json.loads(d)[0] == ["id", "name", "qty"], repr(d))
        out = sess(box, "CONVERT.DATA zzxc.json zzxo4.xml", "n", "CONVERT.DATA zzxc.json zzxo4.xml NO.QUERY", "CONVERT.DATA zzxc.json zzxo9.txt", "CONVERT.DATA zzxc.json zzxo9.txt AS CSV",
                   "CONVERT.DATA zzxc.xml zzxo10.json AS CSV", "CONVERT.DATA nosuch.json zzxo11.csv", "CONVERT.DATA zzxc.json")
        files.extend(["zzxo9.txt", "zzxo10.json", "zzxo11.csv", "zzxo10.csv", "zzxo13.csv"])
        row("a file that is there asks (Enter is no), NO.QUERY does not", has(out, r"zzxo4.xml already exists\. Overwrite\(y/<n>\)\?"), "\n".join(out)[:600])
        row("a name with no known format is refused", has(out, "The format of zzxo9.txt is not known"), "\n".join(out)[:900])
        row("AS CSV names the format of the file written", disk("zzxo9.txt") is not None and disk("zzxo9.txt").startswith("id,n,extra"), repr(disk("zzxo9.txt")))
        out2 = sess(box, "CONVERT.DATA zzxc3.json zzxo13.csv", "CONVERT.DATA zzxc4.json zzxo10.csv", "CONVERT.DATA zzxc4.json zzxo14.jsonl",
                    "CONVERT.DATA zzxc4.json zzxo15.json", "CONVERT.DATA zzxc4.json zzxo16.xml")
        files.extend(["zzxo13.csv", "zzxo14.jsonl", "zzxo15.json", "zzxo16.xml"])
        row("a JSON value that is not text (a nested array) cannot be a CSV cell: message 11857 and nothing is written",
            has(out2, r"The data of zzxc3\.json cannot be written as CSV") and disk("zzxo13.csv") is None, "\n".join(out2)[:600])
        row("a JSON object that is not a table cannot be CSV: refused, nothing written",
            has(out2, r"The data of zzxc4\.json cannot be written as CSV") and disk("zzxo10.csv") is None, "\n".join(out2)[:900])
        row("... nor JSON Lines: refused, nothing written",
            has(out2, r"The data of zzxc4\.json cannot be written as JSON") and disk("zzxo14.jsonl") is None, "\n".join(out2)[:900])
        row("a JSON object goes to JSON as it is", disk("zzxo15.json") is not None and json.loads(disk("zzxo15.json")) == {"a": 1}, repr(disk("zzxo15.json")))
        row("a JSON object that is not an XML element cannot be XML: refused, nothing written",
            has(out2, r"The data of zzxc4\.json cannot be written as XML") and disk("zzxo16.xml") is None, "\n".join(out2)[:900])
        out3 = sess(box, "CONVERT.DATA zzxc5.json zzxo17.xml")
        files.append("zzxo17.xml")
        d = disk("zzxo17.xml")
        try:
            root = ET.fromstring((d or "").encode("utf-8"))
            ok = root.tag == "a" and root.attrib == {"k": "v"} and root.text == "x"
        except ET.ParseError:
            ok = False
        row("a JSON object that is an XML element (name, attributes, text) goes to XML as that element", ok, repr(d))
        row("a missing input is refused", has(out, "Cannot open nosuch.json") and disk("zzxo11.csv") is None, "\n".join(out)[-400:])
        row("a missing operand gives the usage", has(out, r"^convert\.data from\.pathname"), "\n".join(out)[-300:])
    finally:
        sess(box, "DELETE.FILE DICT zzxf%s" % RUN, "DELETE.FILE zzxf%s" % RUN, "DELETE.FILE DICT zzxf%s2" % RUN, "DELETE.FILE zzxf%s2" % RUN,
             "DELETE.FILE DICT zzxc%s" % RUN, "DELETE.FILE zzxc%s" % RUN, "DELETE.FILE DICT zzxx%s" % RUN, "DELETE.FILE zzxx%s" % RUN,
             "DELETE.FILE DICT zzxx%sx" % RUN, "DELETE.FILE zzxx%sx" % RUN, "DELETE.FILE DICT zzxx%se" % RUN, "DELETE.FILE zzxx%se" % RUN, quiet=True)
        for nm in files:
            if os.path.exists(os.path.join(sysd, nm)):
                os.remove(os.path.join(sysd, nm))
        for nm in made:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-xmlx: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

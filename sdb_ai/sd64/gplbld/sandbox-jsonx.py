#!/usr/bin/env python3
#
# sandbox-jsonx.py - JSON beyond JPARSE and JBUILD: JMERGE (RFC 7396), JPATCH (RFC 6902), JPATH (JSONPath), JVALIDATE (JSON Schema), the indent
#                    of JBUILD, READJSON and WRITEJSON (JSON Lines), and the JSON and JSON.LINES query keywords (the owner's CSV / JSON / XML
#                    task of 17 and 20 Oct 2026).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-jsonx.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from THIS tree (it must be empty or
# absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 20 Oct 26 dm  New.  op_json.c (XF_JMERGE ... XF_JVALIDATE), op_coll.c (CF_JBUILDI), bcomp (READJSON, WRITEJSON, the third operand of JBUILD),
#               readjsonrow, writejsonrow, qproc (the JSON and JSON.LINES keywords), keywords 237 and 238.
# END-HISTORY
#
# THE INSTRUMENT.  A program prints its results in tags, name[value], anchored to the start of a line; a collection is shown as the JSON JBUILD()
# writes (names in order of name).  The expectations are the examples of the RFCs and of the JSON Schema documentation where there are
# any.  A report is read from the session and given to Python's json module, so its text has to be JSON and what the module finds is judged.
# What a program writes to a file is read back from the disk.  The controls are the JBUILD() forms that existed before and an ordinary report.

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
FIL = "zzjf" + RUN
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
    say("sandbox-jsonx: CANNOT RUN - " + msg)
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
    return "   crt '%s[':%s:']'\n" % (name, expr)


def sq(s):
    """A BASIC string for text that holds quotes: built from char(39)."""
    return "'" + s.replace("'", "' : sq : '") + "'"


PROGS = {}

BOOKS = ('{"store":{"book":[{"category":"reference","author":"Nigel Rees","title":"Sayings of the Century","price":8.95},'
         '{"category":"fiction","author":"Evelyn Waugh","title":"Sword of Honour","price":12.99},'
         '{"category":"fiction","author":"Herman Melville","title":"Moby Dick","isbn":"0-553-21311-3","price":8.99},'
         '{"category":"fiction","author":"J. R. R. Tolkien","title":"The Lord of the Rings","isbn":"0-395-19395-8","price":22.99}],'
         '"bicycle":{"color":"red","price":399}}}')

# ---- merge ---------------------------------------------------------------------------------------------------------------------------
MERGE = [  # RFC 7396 appendix A: target, patch, result
    ('{"a":"b"}', '{"a":"c"}', '{"a":"c"}'),
    ('{"a":"b"}', '{"b":"c"}', '{"a":"b","b":"c"}'),
    ('{"a":"b"}', '{"a":null}', '{}'),
    ('{"a":"b","b":"c"}', '{"a":null}', '{"b":"c"}'),
    ('{"a":["b"]}', '{"a":"c"}', '{"a":"c"}'),
    ('{"a":"c"}', '{"a":["b"]}', '{"a":["b"]}'),
    ('{"a":{"b":"c"}}', '{"a":{"b":"d","c":null}}', '{"a":{"b":"d"}}'),
    ('{"a":[{"b":"c"}]}', '{"a":[1]}', '{"a":[1]}'),
    ('["a","b"]', '["c","d"]', '["c","d"]'),
    ('{"a":"b"}', '["c"]', '["c"]'),
    ('{"e":null}', '{"a":1}', '{"a":1,"e":null}'),
    ('[1,2]', '{"a":"b","c":null}', '{"a":"b"}'),
    ('{}', '{"a":{"bb":{"ccc":null}}}', '{"a":{"bb":{}}}'),
]
PATCH = [  # RFC 6902 appendix A: document, operations, result (None: the patch fails, at the operation number)
    ('{"foo":"bar"}', '[{"op":"add","path":"/baz","value":"qux"}]', '{"baz":"qux","foo":"bar"}', None),
    ('{"foo":["bar","baz"]}', '[{"op":"add","path":"/foo/1","value":"qux"}]', '{"foo":["bar","qux","baz"]}', None),
    ('{"baz":"qux","foo":"bar"}', '[{"op":"remove","path":"/baz"}]', '{"foo":"bar"}', None),
    ('{"foo":["bar","qux","baz"]}', '[{"op":"remove","path":"/foo/1"}]', '{"foo":["bar","baz"]}', None),
    ('{"baz":"qux","foo":"bar"}', '[{"op":"replace","path":"/baz","value":"boo"}]', '{"baz":"boo","foo":"bar"}', None),
    ('{"foo":{"bar":"baz","waldo":"fred"},"qux":{"corge":"grault"}}', '[{"op":"move","from":"/foo/waldo","path":"/qux/thud"}]',
     '{"foo":{"bar":"baz"},"qux":{"corge":"grault","thud":"fred"}}', None),
    ('{"foo":["all","grass","cows","eat"]}', '[{"op":"move","from":"/foo/1","path":"/foo/3"}]', '{"foo":["all","cows","eat","grass"]}', None),
    ('{"baz":"qux","foo":["a",2,"c"]}', '[{"op":"test","path":"/baz","value":"qux"},{"op":"test","path":"/foo/1","value":2}]',
     '{"baz":"qux","foo":["a",2,"c"]}', None),
    ('{"baz":"qux"}', '[{"op":"test","path":"/baz","value":"bar"}]', None, 1),
    ('{"foo":"bar"}', '[{"op":"add","path":"/child","value":{"grandchild":{}}}]', '{"child":{"grandchild":{}},"foo":"bar"}', None),
    ('{"foo":"bar"}', '[{"op":"add","path":"/baz/bat","value":"qux"}]', None, 1),
    ('{"/":9,"~1":10}', '[{"op":"test","path":"/~01","value":10}]', '{"/":9,"~1":10}', None),
    ('{"foo":["bar"]}', '[{"op":"add","path":"/foo/-","value":["abc","def"]}]', '{"foo":["bar",["abc","def"]]}', None),
    ('{"foo":{"bar":1},"x":2}', '[{"op":"copy","from":"/foo","path":"/y"}]', '{"foo":{"bar":1},"x":2,"y":{"bar":1}}', None),
    ('{"a":1}', '[{"op":"add","path":"/b","value":2},{"op":"remove","path":"/zzz"},{"op":"add","path":"/c","value":3}]', None, 2),
    ('{"a":1}', '[{"op":"frobnicate","path":"/a"}]', None, 1),
    ('{"a":[1,2]}', '[{"op":"add","path":"/a/3","value":9}]', None, 1),
    ('{"a":1}', '[{"op":"replace","path":"","value":[1,2]}]', '[1,2]', None),
]
PATH = [  # JSONPath over BOOKS: query, the result as JSON (None: judged separately)
    ('$.store.book[*].author', '["Nigel Rees","Evelyn Waugh","Herman Melville","J. R. R. Tolkien"]'),
    ('$..author', '["Nigel Rees","Evelyn Waugh","Herman Melville","J. R. R. Tolkien"]'),
    ('$.store.bicycle.color', '["red"]'),
    ("$['store']['bicycle']['color']", '["red"]'),
    ('$..book[2].title', '["Moby Dick"]'),
    ('$..book[-1].title', '["The Lord of the Rings"]'),
    ('$..book[0,1].price', '[8.95,12.99]'),
    ('$..book[:2].price', '[8.95,12.99]'),
    ('$..book[1:3].price', '[12.99,8.99]'),
    ('$..book[::2].price', '[8.95,8.99]'),
    ('$..book[::-1].price', '[22.99,8.99,12.99,8.95]'),
    ('$..book[?@.isbn].title', '["Moby Dick","The Lord of the Rings"]'),
    ('$..book[?@.price<10].title', '["Sayings of the Century","Moby Dick"]'),
    ("$..book[?@.category=='fiction' && @.price>10].title", '["Sword of Honour","The Lord of the Rings"]'),
    ("$..book[?@.category=='reference' || @.price>20].author", '["Nigel Rees","J. R. R. Tolkien"]'),
    ("$..book[?!(@.isbn)].title", '["Sayings of the Century","Sword of Honour"]'),
    ('$..book[?length(@.title) > 15].title', '["Sayings of the Century","The Lord of the Rings"]'),
    ('$..book[?match(@.author, ".*Waugh")].title', '["Sword of Honour"]'),
    ('$..book[?search(@.title, "Ring")].title', '["The Lord of the Rings"]'),
    ('$.store.book[?@.price == 8.95].title', '["Sayings of the Century"]'),
    ('$.store.book.length', '[]'),
    ('$.nosuch', '[]'),
    ('$', None),
]
PATH_BAD = ['store.book', '$.store.[', "$..book[?@.price<]", '$[', '$.store.book[?@.price ??]']

SCHEMA = ('{"type":"object","required":["name","age"],"properties":{"name":{"type":"string","minLength":1},'
          '"age":{"type":"integer","minimum":0,"maximum":150},"tags":{"type":"array","items":{"type":"string"},"uniqueItems":true},'
          '"email":{"type":"string","pattern":"^[^@]+@[^@]+$"}},"additionalProperties":false}')
VALID = [  # instance, schema, expected list of (path, keyword)
    ('{"name":"Ann","age":30,"tags":["a","b"],"email":"a@b.c"}', SCHEMA, []),
    ('{"name":"","age":-1,"tags":["a","a"],"zip":1}', SCHEMA,
     [("/age", "minimum"), ("/name", "minLength"), ("/tags", "uniqueItems"), ("/zip", "additionalProperties")]),
    ('{"name":"Ann"}', SCHEMA, [("", "required")]),
    ('{"name":"Ann","age":1.5}', SCHEMA, [("/age", "type")]),
    ('{"name":"Ann","age":1,"email":"nope"}', SCHEMA, [("/email", "pattern")]),
    ('{"name":"Ann","age":1,"tags":[1]}', SCHEMA, [("/tags/0", "type")]),
    ('{"a":5}', '{"properties":{"a":{"enum":[1,2,3]}}}', [("/a", "enum")]),
    ('{"a":2}', '{"properties":{"a":{"enum":[1,2,3]}}}', []),
    ('[1,2,3]', '{"prefixItems":[{"type":"integer"},{"type":"string"}],"items":{"type":"integer"}}', [("/1", "type")]),
    ('{"a":1}', '{"properties":{"a":{"const":2}}}', [("/a", "const")]),
    ('{"a":5}', '{"properties":{"a":{"oneOf":[{"type":"integer"},{"minimum":3}]}}}', [("/a", "oneOf")]),
    ('{"a":"x"}', '{"properties":{"a":{"anyOf":[{"type":"integer"},{"minLength":3}]}}}', [("/a", "anyOf")]),
    ('{"a":"x"}', '{"properties":{"a":{"not":{"type":"string"}}}}', [("/a", "not")]),
    ('{"p":1,"q":2}', '{"if":{"required":["p"]},"then":{"required":["z"]},"else":{"required":["y"]}}', [("", "required")]),
    ('{"a":{"b":"x"}}', '{"$defs":{"s":{"type":"integer"}},"properties":{"a":{"properties":{"b":{"$ref":"#/$defs/s"}}}}}', [("/a/b", "type")]),
    ('[1,"a"]', '{"contains":{"type":"boolean"}}', [("", "contains")]),
    ('{"a":1}', '{"dependentRequired":{"a":["b"]}}', [("", "dependentRequired")]),
    ('{"a":7}', '{"properties":{"a":{"multipleOf":2}}}', [("/a", "multipleOf")]),
    ('{"a":8}', '{"properties":{"a":{"multipleOf":2}}}', []),
    ('{"a":null}', '{"properties":{"a":{"type":["string","null"]}}}', []),
    ('{"a":null}', '{"properties":{"a":{"type":"string"}}}', [("/a", "type")]),
    ('{"a":1}', '{"properties":{"a":false}}', [("/a", "false")]),
    ('{"a":1}', '{"properties":{"a":true}}', []),
]

PROGS["zzjx1"] = (
    "$include keys.h\n"
    "   sq = char(39)\n"
    "   lf = char(10)\n" +
    "".join(
        "   m = jmerge(jparse(%s), jparse(%s))\n" % (sq(t), sq(p)) + T("MG%d" % i, "jbuild(m)")
        for i, (t, p, r) in enumerate(MERGE)) +
    "   c = jparse('{\"a\":1,\"b\":{\"x\":1}}')\n"
    "   m = jmerge(c, '{\"a\":null,\"b\":{\"y\":2}}')\n" +
    T("MGO", "jbuild(c)") + T("MGT", "jbuild(m)") +
    "   m = jmerge(c, 'not json')\n" + T("MGB", "m : '|' : status()") +
    "".join(
        "   p = jpatch(jparse(%s), jparse(%s))\n" % (sq(d), sq(o)) +
        T("PT%d" % i, "(if status() then 'FAIL ' : status() : ' at ' : inmat() else jbuild(p))")
        for i, (d, o, r, f) in enumerate(PATCH)) +
    "   c = jparse('{\"a\":[1,2,3]}')\n"
    "   p = jpatch(c, '[{\"op\":\"remove\",\"path\":\"/a/0\"}]')\n" +
    T("PTO", "jbuild(c)") + T("PTT", "jbuild(p)") +
    "   books = jparse(" + sq(BOOKS) + ")\n" +
    "".join(T("JP%d" % i, "jbuild(jpath(books, %s))" % sq(q)) for i, (q, r) in enumerate(PATH) if r is not None) +
    "   pr = jpath(books, '$..price')\n" +
    T("JPC", "inmat(pr)") +
    T("JPS", "jbuild(jpath(" + sq('{"a":[1,2,3]}') + ", '$.a[1:]'))") +
    "".join(
        "   x = jpath(books, %s)\n" % sq(q) + T("JB%d" % i, "(if status() then status() : ' at ' : inmat() else 'accepted')")
        for i, q in enumerate(PATH_BAD)) +
    "".join(
        "   e = jvalidate(jparse(%s), jparse(%s))\n" % (sq(i), sq(s)) +
        "   n = inmat(e)\n"
        "   l = ''\n"
        "   for k = 1 to n\n"
        "      l := e{k, 'path'} : ':' : e{k, 'keyword'} : ' '\n"
        "   next k\n" +
        T("JV%d" % j, "n : ' ' : l")
        for j, (i, s, x) in enumerate(VALID)) +
    "   e = jvalidate(jparse('{\"a\":1}'), jparse('{\"properties\":{\"a\":{\"type\":\"string\"}}}'))\n" +
    T("JVM", "e{1, 'message'}") +
    "   vt = jvalidate('[1,2]', '{\"maxItems\":1}')\n" +
    T("JVT", "inmat(vt)") +
    "   vs = jvalidate('7', '{\"multipleOf\":2}')\n" +
    T("JVS", "vs : '|' : status()") +
    "   crt 'JEND'\n"
    "end\n")

PROGS["zzjx2"] = (
    "$include keys.h\n"
    "   c = jparse('{\"a\":[1,{\"b\":2}],\"c\":\"x\"}')\n" +
    T("I0", "jbuild(c, jb$pretty)") +
    T("I4", "jbuild(c, jb$pretty, '    ')") +
    T("IT", "convert(char(9), '>', jbuild(c, jb$pretty, char(9)))") +
    T("IF", "jbuild(c, 0, '   ')") +
    T("IB", "jbuild(c, jb$pretty, 'xy')") +
    T("IC", "jbuild(c)") +
    T("IE", "jbuild(c, jb$pretty, '')") +
    "   crt 'IEND'\n"
    "end\n")

PROGS["zzjx3"] = (
    "$include keys.h\n"
    "   lf = char(10)\n"
    "   openseq 'zzjx3.jsonl' to f then null else create f else stop 'nocreate'\n"
    "   weofseq f\n"
    "   c = jparse('{\"id\":1,\"s\":\"a' : lf : 'b\"}')\n"
    "   writejson c to f else stop 'w1'\n"
    "   c = jparse('[1,2]')\n"
    "   writejson c to f else stop 'w2'\n"
    "   writeseq '' to f else stop 'blank'\n"
    "   c = jparse('{\"id\":2}')\n"
    "   writejson c to f else stop 'w3'\n"
    "   writeseq '{bad' to f else stop 'bad'\n"
    "   c = jparse('{\"id\":3}')\n"
    "   writejson c to f else stop 'w4'\n"
    "   weofseq f ; close f\n"
    "   openseq 'zzjx3.jsonl' to f else stop 'noopen'\n"
    "   readjson a from f else stop 'r1'\n" +
    T("RA", "a{'id'} : ' ' : convert(lf, '~', a{'s'})") +
    "   readjson b from f else stop 'r2'\n" +
    T("RB", "jtype(b) : ' ' : b{2}") +
    "   readjson d from f else stop 'r3'\n" +
    T("RD", "d{'id'}") +
    "   readjson e from f then crt 'RE then' else crt 'RE else ' : status()\n"
    "   readjson g from f else stop 'r5'\n" +
    T("RG", "g{'id'}") +
    "   readjson h from f then crt 'RH then' else crt 'RH else ' : status()\n"
    "   close f\n"
    "   x = jparse('[1]')\n"
    "   openseq 'zzjx3b.jsonl' to f then null else create f else stop 'nocreate'\n"
    "   weofseq f\n"
    "   fv = 5\n"
    "   writejson fv to f then crt 'WS then' else crt 'WS else ' : status()\n"
    "   close f\n"
    "   crt 'REND'\n"
    "end\n")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-jsonx.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-jsonx: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-jsonx: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    made = []
    try:
        for nm, text in PROGS.items():
            with open(os.path.join(sysd, "bp", nm), "w") as f:
                f.write(text)
            made.append(nm)
        out = sess(box, "BASIC bp " + " ".join(PROGS))
        row("setup: the programs compile with no errors", has(out, r"^Compiled %d program\(s\) with no errors" % len(PROGS)), "\n".join(out[-12:]))

        say("\n--- JMERGE: RFC 7396 appendix A ------------------------------------------------------------------------------------")
        out = sess(box, "RUN bp zzjx1")
        row("the first program ran to its end", has(out, r"^JEND$"), "\n".join(out[-6:]))
        for i, (t, p, r) in enumerate(MERGE):
            got = tag(out, "MG%d" % i)
            row("merge %s with %s gives %s" % (t, p, r), got is not None and json.loads(got or "null") == json.loads(r) and got == json.dumps(json.loads(r), separators=(",", ":"), sort_keys=True), repr(got))
        row("the target is not changed", tag(out, "MGO") == '{"a":1,"b":{"x":1}}', repr(tag(out, "MGO")))
        row("... the copy is merged: a gone, b.y added", tag(out, "MGT") == '{"b":{"x":1,"y":2}}', repr(tag(out, "MGT")))
        row("a patch that is not JSON gives a null string and STATUS() 1020", tag(out, "MGB") == "|1020", repr(tag(out, "MGB")))

        say("\n--- JPATCH: RFC 6902 appendix A ------------------------------------------------------------------------------------")
        for i, (d, o, r, f) in enumerate(PATCH):
            got = tag(out, "PT%d" % i)
            if r is not None:
                row("patch %s with %s gives %s" % (d, o, r), got is not None and not got.startswith("FAIL") and json.loads(got) == json.loads(r), repr(got))
            else:
                row("patch %s with %s fails at operation %d (STATUS() 1023, INMAT() the number)" % (d, o, f), got == "FAIL 1023 at %d" % f, repr(got))
        row("JPATCH changes a copy: the document is as it was", tag(out, "PTO") == '{"a":[1,2,3]}' and tag(out, "PTT") == '{"a":[2,3]}',
            "%r %r" % (tag(out, "PTO"), tag(out, "PTT")))

        say("\n--- JPATH: the bookstore of RFC 9535 ----------------------------------------------------------------------------")
        for i, (q, r) in enumerate(PATH):
            if r is None:
                continue
            got = tag(out, "JP%d" % i)
            row("JPATH %s is %s" % (q, r), got == r, repr(got))
        row("$..price finds five prices (the bicycle's and the four books')", tag(out, "JPC") == "5", repr(tag(out, "JPC")))
        row("a slice from 1 to the end", tag(out, "JPS") == "[2,3]", repr(tag(out, "JPS")))
        for i, q in enumerate(PATH_BAD):
            got = tag(out, "JB%d" % i)
            row("the query %r is refused: STATUS() 1024 and the place" % q, got is not None and got.startswith("1024 at "), repr(got))

        say("\n--- JVALIDATE: JSON Schema ---------------------------------------------------------------------------------------")
        for j, (inst, sch, exp) in enumerate(VALID):
            got = tag(out, "JV%d" % j)
            if exp is None:
                row("%s against %s is valid" % (inst, sch[:50]), got is not None and got.startswith("0 "), repr(got))
                continue
            want = "%d %s" % (len(exp), "".join("%s:%s " % e for e in sorted(exp)))
            gotn = None
            if got is not None:
                parts = got.split(" ", 1)
                items = sorted(p for p in (parts[1].split(" ") if len(parts) > 1 else []) if p)
                gotn = "%s %s" % (parts[0], "".join(p + " " for p in items))
            row("%s against %s: %s" % (inst, sch[:60] + ("..." if len(sch) > 60 else ""), exp if exp else "valid"), gotn == want, "have %r want %r" % (got, want))
        row("an error has a message", tag(out, "JVM") not in (None, ""), repr(tag(out, "JVM")))
        row("JSON text is taken in place of a collection", tag(out, "JVT") == "1", repr(tag(out, "JVT")))
        row("a document that is not an object or an array (a JSON scalar) is refused: a null string and STATUS() 1020", tag(out, "JVS") == "|1020", repr(tag(out, "JVS")))

        say("\n--- JBUILD with an indent ----------------------------------------------------------------------------------------------")
        out = sess(box, "RUN bp zzjx2")
        row("the second program ran to its end", has(out, r"^IEND$"), "\n".join(out[-6:]))
        # the layout comes out on several lines: take it from the raw output
        raw = "\n".join(out)
        row("CONTROL: jb$pretty with no indent is two spaces for each level", '\n  "a": [\n    1,\n    {\n      "b": 2\n    }\n  ],\n  "c": "x"\n}' in raw.replace("I0[", "\n"),
            raw[:400])
        row("an indent of four spaces", '\n    "a": [\n        1,\n        {\n            "b": 2\n        }\n    ],\n    "c": "x"\n}' in raw, raw[:600])
        row("an indent of a tab", '>"a": [' in raw.replace("\n", "") and ">>1," in raw.replace("\n", ""), raw[:600])
        row("an indent given with no jb$pretty is the pretty layout (naming an indent asks for it)", 'IF[{\n   "a": [' in raw, raw[:700])
        row("an indent that is not white space is two spaces", 'IB[{\n  "a": [' in raw, raw[:900])
        row("a null indent is two spaces", 'IE[{\n  "a": [' in raw, raw[:900])
        row("CONTROL: no mode is the compact text", tag(out, "IC") == '{"a":[1,{"b":2}],"c":"x"}', repr(tag(out, "IC")))

        say("\n--- READJSON and WRITEJSON: JSON Lines -----------------------------------------------------------------------------")
        out = sess(box, "RUN bp zzjx3")
        row("the program ran to its end", has(out, r"^REND$"), "\n".join(out[-6:]))
        d = open(os.path.join(sysd, "zzjx3.jsonl"), "rb").read().decode("latin-1") if os.path.exists(os.path.join(sysd, "zzjx3.jsonl")) else None
        want_lines = ['{"id":1,"s":"a\\nb"}', '[1,2]', '', '{"id":2}', '{bad', '{"id":3}']
        row("WRITEJSON wrote one compact line for each, a line feed in a string as \\n", d is not None and d.split("\n")[:6] == want_lines, repr(d))
        row("READJSON reads the first, the \\n back as a line feed", tag(out, "RA") == "1 a~b", repr(tag(out, "RA")))
        row("... an array too, skipping the blank line after it is next", tag(out, "RB") == "array 2", repr(tag(out, "RB")))
        row("... the blank line is skipped", tag(out, "RD") == "2", repr(tag(out, "RD")))
        row("a line that is not JSON takes ELSE, STATUS() 1020", has(out, r"^RE else 1020$"), "\n".join(out))
        row("... and the line after it is read next", tag(out, "RG") == "3", repr(tag(out, "RG")))
        row("at the end of the file ELSE with STATUS() 3006", has(out, r"^RH else 3006$"), "\n".join(out))
        row("WRITEJSON of a value that is not a collection takes ELSE with STATUS() 1020 and writes nothing", has(out, r"^WS else 1020$"), "\n".join(out))

        say("\n--- the JSON and JSON.LINES keywords ----------------------------------------------------------------------------")
        VM = "\xfd"
        recs = [("r1", ["Ann", "1" + VM + "2", "1.50" + VM + "2.00", "x" + VM + "y", 'say "hi"']), ("r2", ["Bob", "5", "3.25", "", "z"]),
                ("r3", ["", "", "", "", ""])]
        items = [(1, "name", "10L", "S", ""), (2, "qty", "5R", "M", "lines"), (3, "price", "8R", "M", "lines"), (4, "note", "5L", "M", ""),
                 (5, "tag", "5L", "S", "")]
        cmds = ["DELETE.FILE DICT %s" % FIL, "DELETE.FILE %s" % FIL, "CREATE.FILE %s" % FIL]
        for rid, flds in recs:
            with open(os.path.join(sysd, "bp", "zzjr" + RUN + rid), "wb") as f:
                f.write(("\n".join(flds) + "\n").encode("latin-1"))
            made.append("zzjr" + RUN + rid)
            cmds.append("COPY FROM BP TO %s zzjr%s%s,%s" % (FIL, RUN, rid, rid))
        for n, nm, fmt, sm, assoc in items:
            with open(os.path.join(sysd, "bp", "zzjd%s%d" % (RUN, n)), "wb") as f:
                f.write(("D\n%d\n\n%s\n%s\n%s\n%s\n" % (n, nm, fmt, sm, assoc)).encode("latin-1"))
            made.append("zzjd%s%d" % (RUN, n))
            cmds.append("COPY FROM BP TO DICT %s zzjd%s%d,%s" % (FIL, RUN, n, nm))
        sess(box, *cmds, quiet=True)
        c1 = "LIST %s BY @ID name qty price note tag JSON" % FIL
        c2 = "LIST %s BY @ID name qty price note tag JSON.LINES" % FIL
        c3 = "LIST %s BY @ID name qty XML JSON" % FIL
        c4 = "LIST %s BY @ID name ELEMENTS JSON" % FIL
        c5 = "LIST %s BY @ID name" % FIL
        out = sess(box, c1, c2, c3, c4, c5)
        txt = "\n".join(out)
        m = re.search(r"(?m)^\[\n(.*?)^\]$", txt, re.S)
        try:
            doc = json.loads("[" + m.group(1) + "]") if m else None
        except ValueError as e:
            doc = None
            say("      not JSON: %s" % e)
        row("JSON: the text between [ and ] is JSON, one object for each record", doc is not None and len(doc) == 3, txt[:300])
        if doc:
            a = doc[0]
            row("a single valued field is a member, as text (the double quote escaped)", a.get("name") == "Ann" and a.get("tag") == 'say "hi"', repr(a))
            row("an association is an array of row objects, named for the association", a.get("lines") == [{"qty": "1", "price": "1.50"}, {"qty": "2", "price": "2.00"}], repr(a))
            row("a multivalued field in no association is an array", a.get("note") == ["x", "y"], repr(a))
            row("a field with no value is left out: Bob has no note", "note" not in doc[1] and doc[1].get("lines") == [{"qty": "5", "price": "3.25"}], repr(doc[1]))
            row("nothing is a number: 007-style text would stay text, so qty is \"5\"", doc[1]["lines"][0]["qty"] == "5", repr(doc[1]))
        lines = [ln for ln in out if ln.startswith("{")]
        row("JSON.LINES: three lines of JSON, no brackets, one object each", len(lines) >= 3 and all(json.loads(x) is not None for x in lines[-3:]) and "\n[\n" not in txt.split(c2)[-1].split(c3)[0],
            "\n".join(lines))
        row("JSON with XML (or DELIMITER, CSV) is refused as a repeated report kind", has(out, "Multiple use of DELIMITER or CSV options"), txt[-400:])
        row("JSON with an XML option (ELEMENTS) is refused", has(out, "need the xml keyword"), txt[-400:])
        row("CONTROL: an ordinary report is still a report", has(out, r"^r1\s+Ann") or has(out, r"r1\s+Ann"), txt[-300:])
    finally:
        sess(box, "DELETE.FILE DICT %s" % FIL, "DELETE.FILE %s" % FIL, quiet=True)
        for nm in ("zzjx3.jsonl", "zzjx3b.jsonl"):
            if os.path.exists(os.path.join(sysd, nm)):
                os.remove(os.path.join(sysd, nm))
        for nm in made:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-jsonx: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

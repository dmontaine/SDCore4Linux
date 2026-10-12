#!/usr/bin/env python3
#
# sandbox-coll.py - 1.2-0 data collections (openQM "Data Collections").  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-coll.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from
# THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 13 Oct 26 dm  Written for the first slice: COLLECTION(), c{path} get / set / DEL, ELEMENT.EXISTS(), ENUMERATE().
# END-HISTORY
#
# THE INSTRUMENT IS THE VALUE A BASIC PROGRAM PRINTED between brackets (marks shown as F V S).  A row whose program
# is meant to stop with a run time error is read from the whole output instead.  Each feature has a CONTROL row on
# the line before it where there is an existing feature to compare it with.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0

C = "c = collection()\n   "

# (label, BASIC statements one per line leaving the value in x, wanted)   wanted starting with "ERR:" is a text the
# output must hold because the program must stop with a run time error.
CASES = [
    ("CONTROL: a dynamic array field is still read with angle brackets", "a = 'p':@fm:'q'\n   x = a<2>", "q"),
    ("CONTROL: and an ordinary variable still takes a substring", "a = 'hello'\n   x = a[2,3]", "ell"),
    ("COLLECTION() makes a collection that an element can be put in and read from",
     C + "c{'name'} = 'Acme'\n   x = c{'name'}", "Acme"),
    ("a number stays a number", C + "c{'n'} = 5\n   x = c{'n'} + 2", "7"),
    ("a value holding field marks comes back whole",
     C + "c{'v'} = 'a':@fm:'b'\n   x = change(c{'v'}, @fm, 'F')", "aFb"),
    ("setting a name again replaces it", C + "c{'k'} = 'one'\n   c{'k'} = 'two'\n   x = c{'k'}", "two"),
    ("an element that is not there is a null string and STATUS() is ER$NOT.FOUND",
     C + "x = c{'nope'}\n   x = '[':x:'][':status():']'", "[][1004]"),
    ("a name is case sensitive", C + "c{'Name'} = 'upper'\n   x = '[':c{'name'}:']'", "[]"),
    ("ELEMENT.EXISTS() says 1 for a present element", C + "c{'a'} = 1\n   x = element.exists(c, 'a')", "1"),
    ("ELEMENT.EXISTS() says 0 for an absent one", C + "c{'a'} = 1\n   x = element.exists(c, 'b')", "0"),
    ("DEL removes an element", C + "c{'a'} = 1\n   del c{'a'}\n   x = element.exists(c, 'a')", "0"),
    ("DEL of an absent element leaves STATUS() at ER$NOT.FOUND and does nothing else",
     C + "c{'a'} = 1\n   del c{'b'}\n   x = status():'|':element.exists(c, 'a')", "1004|1"),
    ("ENUMERATE() gives the names sorted, left aligned and case sensitive (capitals first)",
     C + "c{'b'} = 1\n   c{'a'} = 1\n   c{'C'} = 1\n   x = change(enumerate(c), @fm, '|')", "C|a|b"),
    ("ENUMERATE() of an empty collection is null", C + "x = '[':enumerate(c):']'", "[]"),
    ("ENUMERATE() lists only the level it is given",
     C + "c{'a/b'} = 1\n   c{'z'} = 1\n   x = change(enumerate(c), @fm, '|')", "a|z"),
    ("{'a','b'}, {'a'}{'b'} and {'a/b'} are the same element",
     C + "c{'a','b'} = 'v'\n   x = c{'a'}{'b'}:'|':c{'a/b'}:'|':c{'a','b'}", "v|v|v"),
    ("the path may be mixed: {'a/b','c'} and {'a'}{'b/c'}",
     C + "c{'a/b','c'} = 'w'\n   x = c{'a'}{'b/c'}:'|':c{'a/b/c'}", "w|w"),
    ("a path made of variables", C + "p = 'a':'/':'b'\n   c{p} = 'q'\n   k = 'a'\n   x = c{k}{'b'}", "q"),
    ("elements missing along the way are made", C + "c{'x/y/z'} = 'deep'\n   x = c{'x'}{'y'}{'z'}", "deep"),
    ("an intermediate level is a collection that can be enumerated",
     C + "c{'x/y/z'} = 'deep'\n   t = c{'x'}\n   x = change(enumerate(t), @fm, '|')", "y"),
    ("DEL of a level removes everything below it",
     C + "c{'x/y/z'} = 'deep'\n   del c{'x'}\n   x = element.exists(c, 'x/y/z'):element.exists(c, 'x')", "00"),
    ("assigning a collection variable makes another reference to the same collection",
     C + "d = c\n   d{'k'} = 'v'\n   x = c{'k'}", "v"),
    ("COLLECTION(c) makes an independent copy",
     C + "c{'k'} = 'one'\n   d = collection(c)\n   d{'k'} = 'two'\n   d{'new'} = 1\n   x = c{'k'}:'|':element.exists(c, 'new')", "one|0"),
    ("a copy is deep: a collection inside is copied too",
     C + "c{'in/k'} = 'one'\n   d = collection(c)\n   d{'in/k'} = 'two'\n   x = c{'in/k'}", "one"),
    ("a collection can be an element of another, and shares",
     C + "d = collection()\n   c{'sub'} = d\n   d{'k'} = 'v'\n   x = c{'sub'}{'k'}", "v"),
    ("a name that is a number is a name in an ordinary collection", C + "c{'7'} = 'seven'\n   c{7} = 'again'\n   x = c{'7'}", "again"),
    ("a value read back from a collection can be changed without changing the collection",
     C + "c{'s'} = 'abc'\n   v = c{'s'}\n   v := 'def'\n   x = c{'s'}", "abc"),
    ("a collection held in a dimensioned array element",
     "dim t(2)\n   t(1) = collection()\n   t(1){'k'} = 'v'\n   x = t(1){'k'}", "v"),
    ("3000 elements go in sorted and come out again (the table grows and shrinks)",
     C + "for i = 1 to 3000\n   c{'k':i} = i\n   next i\n   x = dcount(enumerate(c), @fm)\n"
     "   for i = 1 to 3000 step 2\n   del c{'k':i}\n   next i\n   x := '|':dcount(enumerate(c), @fm):'|':c{'k2998'}:'|':element.exists(c, 'k2999')\n"
     "   for i = 2 to 3000 step 2\n   del c{'k':i}\n   next i\n   x := '|':dcount(enumerate(c), @fm)", "3000|1500|2998|0|0"),
    ("a collection copied again and again, and dropped, leaves the original whole",
     C + "c{'a/b/c'} = 'deep'\n   for i = 1 to 2000\n   d = collection(c)\n   d{'a/b/x'} = i\n   next i\n   x = c{'a/b/c'}:'|':d{'a/b/x'}:'|':element.exists(c, 'a/b/x')", "deep|2000|0"),
    # ---- arrays -----------------------------------------------------------------------------------------------
    ("MAT() makes an empty array that INMAT() counts", C + "c{'a'} = mat()\n   x = inmat(c{'a'})", "0"),
    ("elements go on the end of an array by position", C + "c{'a'} = mat()\n   c{'a',1} = 'x'\n   c{'a',2} = 'y'\n   x = inmat(c{'a'}):'|':c{'a',1}:c{'a',2}", "2|xy"),
    ("a negative position appends", C + "c{'a'} = mat()\n   c{'a',-1} = 'p'\n   c{'a',-1} = 'q'\n   x = inmat(c{'a'}):'|':c{'a',2}", "2|q"),
    ("the {name}{n} form reaches the same element", C + "c{'a'} = mat()\n   c{'a'}{1} = 'x'\n   x = c{'a',1}:c{'a'}{1}:c{'a/1'}", "xxx"),
    ("a position past the end is not found", C + "c{'a'} = mat()\n   c{'a',1} = 'x'\n   x = '[':c{'a',2}:']':status()", "[]1004"),
    ("ENUMERATE() of an array is its positions", C + "c{'a'} = mat()\n   c{'a',1} = 'x'\n   c{'a',2} = 'y'\n   x = change(enumerate(c{'a'}), @fm, '|')", "1|2"),
    ("MAT(matrix) copies a dimensioned matrix",
     "dim t(3)\n   t(1) = 'a'\n   t(2) = 'b'\n   t(3) = 'c'\n" + "   " + C + "c{'k'} = mat(t)\n   x = inmat(c{'k'}):'|':c{'k',1}:c{'k',3}", "3|ac"),
    ("MAT(matrix, max) stops at max elements",
     "dim t(3)\n   t(1) = 'a'\n   t(2) = 'b'\n   t(3) = 'c'\n" + "   " + C + "c{'k'} = mat(t, 2)\n   x = inmat(c{'k'}):'|':c{'k',2}", "2|b"),
    ("MAT(matrix) of two dimensions goes row by row",
     "dim m(2,2)\n   m(1,1) = 1\n   m(1,2) = 2\n   m(2,1) = 3\n   m(2,2) = 4\n" + "   " + C + "c{'k'} = mat(m)\n   x = c{'k',1}:c{'k',2}:c{'k',3}:c{'k',4}", "1234"),
    ("an unassigned matrix element is a null string",
     "dim t(2)\n   t(1) = 'a'\n" + "   " + C + "c{'k'} = mat(t)\n   x = inmat(c{'k'}):'|':c{'k',1}:'[':c{'k',2}:']'", "2|a[]"),
    ("the copy is not the matrix: changing it leaves the matrix alone",
     "dim t(1)\n   t(1) = 'a'\n" + "   " + C + "c{'k'} = mat(t)\n   c{'k',1} = 'b'\n   x = t(1)", "a"),
    ("MAT x = MAT c{path} copies an array into a matrix",
     C + "c{'k'} = mat()\n   c{'k',1} = 'x'\n   c{'k',2} = 'y'\n   dim n(3)\n   mat n = mat c{'k'}\n   x = n(1):n(2)", "xy"),
    ("...and leaves the rest of the matrix as it was",
     C + "c{'k'} = mat()\n   c{'k',1} = 'x'\n   dim n(3)\n   n(3) = 'z'\n   mat n = mat c{'k'}\n   x = n(1):n(3)", "xz"),
    ("...and stops when the matrix is the shorter",
     C + "c{'k'} = mat()\n   c{'k',1} = 'x'\n   c{'k',2} = 'y'\n   c{'k',3} = 'w'\n   dim n(2)\n   mat n = mat c{'k'}\n   x = n(1):n(2)", "xy"),
    ("DEL of an array element renumbers the rest",
     C + "c{'k'} = mat()\n   c{'k',1} = 'a'\n   c{'k',2} = 'b'\n   c{'k',3} = 'c'\n   del c{'k',2}\n   x = inmat(c{'k'}):'|':c{'k',1}:c{'k',2}", "2|ac"),
    ("DEL c{name}{n} does the same",
     C + "c{'k'} = mat()\n   c{'k',1} = 'a'\n   c{'k',2} = 'b'\n   del c{'k'}{1}\n   x = inmat(c{'k'}):'|':c{'k',1}", "1|b"),
    ("INS value AS opens a gap in an array",
     C + "c{'k'} = mat()\n   c{'k',1} = 'a'\n   c{'k',2} = 'c'\n   ins 'b' as c{'k',2}\n   x = inmat(c{'k'}):'|':c{'k',1}:c{'k',2}:c{'k',3}", "3|abc"),
    ("INS at the first position pushes everything up",
     C + "c{'k'} = mat()\n   c{'k',1} = 'b'\n   ins 'a' as c{'k'}{1}\n   x = c{'k',1}:c{'k',2}", "ab"),
    ("INS one past the end, and with a negative position, appends",
     C + "c{'k'} = mat()\n   ins 'a' as c{'k',1}\n   ins 'b' as c{'k',2}\n   ins 'c' as c{'k',-1}\n   x = c{'k',1}:c{'k',2}:c{'k',3}", "abc"),
    ("INS in a collection that is not an array puts the element in", C + "ins 'v' as c{'n'}\n   x = c{'n'}", "v"),
    ("INS MAT() AS puts in an empty array", C + "ins mat() as c{'list'}\n   c{'list',1} = 'x'\n   x = inmat(c{'list'}):'|':c{'list',1}", "1|x"),
    ("INS MAT(matrix) AS puts in a copy of a matrix",
     "dim t(2)\n   t(1) = 'p'\n   t(2) = 'q'\n" + "   " + C + "ins mat(t) as c{'list'}\n   x = inmat(c{'list'}):'|':c{'list',2}", "2|q"),
    ("INMAT() of a variable holding an array", C + "c{'k'} = mat()\n   c{'k',1} = 'x'\n   t = c{'k'}\n   x = inmat(t)", "1"),
    ("INMAT() of an element that is not there is 0", C + "x = inmat(c{'nope'})", "0"),
    ("a collection is an element of an array, and an array of an array",
     C + "c{'g'} = mat()\n   c{'g',1} = mat()\n   c{'g',1,1} = 'deep'\n   c{'g',2} = collection()\n   c{'g',2}{'n'} = 'obj'\n   x = c{'g',1,1}:'|':c{'g',2,'n'}:'|':inmat(c{'g'})", "deep|obj|2"),
    ("COLLECTION(c) copies the arrays inside as well",
     C + "c{'k'} = mat()\n   c{'k',1} = 'one'\n   d = collection(c)\n   d{'k',1} = 'two'\n   d{'k',-1} = 'more'\n   x = c{'k',1}:'|':inmat(c{'k'}):'|':inmat(d{'k'})", "one|1|2"),
    ("an array assigned to a second name is the same array",
     C + "c{'k'} = mat()\n   t = c{'k'}\n   t{1} = 'via t'\n   x = c{'k',1}", "via t"),
    # ---- asterisk paths ---------------------------------------------------------------------------------------
    ("c{'k/*'} gives the elements of an array as values",
     C + "c{'k'} = mat()\n   c{'k',1} = 'a'\n   c{'k',2} = 'b'\n   c{'k',3} = 'c'\n   x = change(c{'k/*'}, @vm, '|')", "a|b|c"),
    ("c{'d/*/p'} gives one value from each element",
     C + "c{'d'} = mat()\n   c{'d',1} = collection()\n   c{'d',1}{'p'} = 'A'\n   c{'d',2} = collection()\n   c{'d',2}{'p'} = 'B'\n   x = change(c{'d/*/p'}, @vm, '|')", "A|B"),
    ("an element without the item leaves its place empty",
     C + "c{'d'} = mat()\n   c{'d',1} = collection()\n   c{'d',1}{'p'} = 'A'\n   c{'d',2} = collection()\n   c{'d',3} = collection()\n   c{'d',3}{'p'} = 'C'\n   x = change(c{'d/*/p'}, @vm, '|')", "A||C"),
    ("two asterisks give subvalues within values",
     C + "c{'d'} = mat()\n   c{'d',1} = collection()\n   c{'d',1}{'s'} = mat()\n   c{'d',1}{'s',1} = '1a'\n   c{'d',1}{'s',2} = '1b'\n"
     "   c{'d',2} = collection()\n   c{'d',2}{'s'} = mat()\n   c{'d',2}{'s',1} = '2a'\n   x = change(change(c{'d/*/s/*'}, @vm, 'V'), @svm, 'S')", "1aS1bV2a"),
    ("an asterisk path through something that is not an array is null", C + "c{'o/p'} = 'v'\n   x = '[':c{'o/*'}:']'", "[]"),
    ("ERR: an asterisk cannot be used to set", C + "c{'a'} = mat()\n   c{'a/*'} = 'x'", "ERR:Invalid data collection element name"),
    ("ERR: three asterisks are too many", C + "x = c{'a/*/*/*'}", "ERR:Invalid data collection element name"),
    ("ERR: elements may not be left undefined in an array", C + "c{'k'} = mat()\n   c{'k',1} = 'a'\n   c{'k',5} = 'e'", "ERR:Invalid data collection element name"),
    ("ERR: INS may not leave a gap either", C + "c{'k'} = mat()\n   ins 'q' as c{'k',9}", "ERR:Invalid data collection element name"),
    ("ERR: MAT x = MAT c{path} of something that is not an array",
     C + "c{'o'} = 'v'\n   dim n(2)\n   mat n = mat c{'o'}", "ERR:not a data collection"),
    ("ERR: MAT x = MAT c{path} of a collection that is not an array",
     C + "c{'o/p'} = 'v'\n   dim n(2)\n   mat n = mat c{'o'}", "ERR:not an array"),
    ("ERR: a name cannot be used as a position in an array",
     C + "c{'k'} = mat()\n   c{'k',1} = 'a'\n   c{'k','abc'} = 'b'", "ERR:Invalid data collection element name"),
    ("ERR: MAT(x) of something that is not a matrix", "t = 5\n   c = collection()\n   c{'k'} = mat(t)", "ERR:imensioned matrix"),
    # ---- JSON: JPARSE() and JBUILD() ------------------------------------------------------------------------
    ("JPARSE() reads an object into a collection and STATUS() is 0",
     "c = jparse('{\"name\":\"Acme\",\"n\":5}')\n   x = c{'name'}:'|':c{'n'} + 1:'|':status()", "Acme|6|0"),
    ("nested objects and arrays are reached by path",
     "c = jparse('{\"a\":{\"b\":[10,20,{\"z\":\"deep\"}]}}')\n   x = c{'a/b/1'}:'|':c{'a/b/3/z'}:'|':inmat(c{'a/b'})", "10|deep|3"),
    ("a JSON array at the top is an array", "c = jparse('[1,\"two\",[3]]')\n   x = inmat(c):'|':c{2}:'|':c{3,1}", "3|two|3"),
    ("true and false read back as 1 and 0, null as a null string",
     "c = jparse('{\"t\":true,\"f\":false,\"n\":null}')\n   x = c{'t'}:'|':c{'f'}:'|':'[':c{'n'}:']'", "1|0|[]"),
    ("numbers: integers, fractions, exponents, big ones",
     "c = jparse('{\"f\":1.5,\"big\":12345678901,\"neg\":-3,\"e\":1e2}')\n   x = c{'f'} * 2:'|':c{'neg'} - 1:'|':c{'e'}:'|':c{'big'}", "3|-4|100|12345678901"),
    ("whitespace, and all five marks, between elements are ignored",
     "c = jparse('{':@fm:' \"a\" ':@vm:':':@svm:' 1 ':@tm:'}')\n   x = c{'a'}:'|':status()", "1|0"),
    ("a later name replaces an earlier one", "c = jparse('{\"a\":1,\"a\":2}')\n   x = c{'a'}:'|':inmat(c)", "2|1"),
    ("single quotes are accepted for names and strings", "c = jparse(\"{'a':'b'}\")\n   x = c{'a'}", "b"),
    ("escapes: quote, backslash, slash, newline, tab",
     "c = jparse('{\"s\":\"q\\\"b\\\\s\\/n\\nt\\t\"}')\n   x = change(change(c{'s'}, char(10), 'N'), char(9), 'T')", "q\"b\\s/nNtT"),
    ("\\u00e9 is the byte E9 and \\u20ac is three bytes of UTF-8",
     "c = jparse('{\"a\":\"\\u00e9\",\"b\":\"\\u20ac\"}')\n   x = seq(c{'a'}):'|':len(c{'a'}):'|':seq(c{'b'}[1,1]):'|':len(c{'b'})", "233|1|226|3"),
    ("a surrogate pair is one four byte character",
     "c = jparse('{\"a\":\"\\ud83d\\ude00\"}')\n   x = len(c{'a'}):'|':seq(c{'a'}[1,1])", "4|240"),
    ("a name without quotes is refused unless JP$UNQUOTED.NAME is set",
     "c = jparse('{a:1}')\n   x = status():'|':'[':c:']'", "1020|[]"),
    ("...and with it set is accepted", "c = jparse('{a:1,b2:2}', 2)\n   x = c{'a'}:c{'b2'}:'|':status()", "12|0"),
    ("JP$NULL reads a null as a null string, not as null",
     "c = jparse('{\"n\":null}', 1)\n   x = jbuild(c)", "{\"n\":\"\"}"),
    ("an error gives a null string, STATUS() 1020 and INMAT() the character position",
     "c = jparse('{\"a\" 1}')\n   x = '[':c:']':status():'|':inmat()", "[]1020|6"),
    ("text after the value is an error, at the first character of it", "c = jparse('{\"a\":1} x')\n   x = status():'|':inmat()", "1020|9"),
    ("a value that is not an object or array is refused", "c = jparse('5')\n   x = status():'|':inmat()", "1020|1"),
    ("an empty string is refused", "c = jparse('')\n   x = status()", "1020"),
    ("a half-finished value is refused", "c = jparse('{\"a\":[1,2')\n   x = status()", "1020"),
    ("a trailing comma is refused", "c = jparse('[1,2,]')\n   x = status()", "1020"),
    ("01 is not a JSON number", "c = jparse('[01]')\n   x = status()", "1020"),
    ("600 levels of nesting are refused, not run into", "c = jparse(str('[', 600):str(']', 600))\n   x = status()", "1020"),
    ("JBUILD() writes a collection compactly, names in order",
     C + "c{'b'} = 2\n   c{'a'} = 'x'\n   x = jbuild(c):'|':status()", "{\"a\":\"x\",\"b\":2}|0"),
    ("arrays and nested collections", C + "c{'l'} = mat()\n   c{'l',1} = 1\n   c{'l',2} = 'two'\n   c{'o/p'} = 3\n   x = jbuild(c)", "{\"l\":[1,\"two\"],\"o\":{\"p\":3}}"),
    ("an array at the top", "c = mat()\n   x = jbuild(c)", "[]"),
    ("quote, backslash and control characters are escaped",
     C + "c{'s'} = 'q\"b\\':char(9):'t':char(10):'n'\n   x = jbuild(c)", "{\"s\":\"q\\\"b\\\\\\tt\\nn\"}"),
    ("marks and 8 bit characters are written as \\u00XX",
     C + "c{'m'} = 'a':@fm:'b':@vm:'c':char(233)\n   x = jbuild(c)", "{\"m\":\"a\\u00feb\\u00fdc\\u00e9\"}"),
    ("...and come back as the same bytes",
     C + "s = 'a':@fm:'b':@vm:'c':@svm:'d':char(233)\n   c{'m'} = s\n   d = jparse(jbuild(c))\n   x = (d{'m'} = s)", "1"),
    ("a float is written so it reads back the same",
     C + "c{'f'} = 0.1 + 0.2\n   d = jparse(jbuild(c))\n   x = (d{'f'} = c{'f'})", "1"),
    ("true, false and null survive a parse and a build",
     "s = '{\"e\":\"\",\"f\":false,\"n\":null,\"t\":true}'\n   x = (jbuild(jparse(s)) = s)", "1"),
    ("a whole document survives a parse and a build",
     "s = '{\"a\":[1,2.5,{\"b\":[true,null,\"x\"]}],\"c\":{\"d\":\"e\"},\"z\":[]}'\n   x = (jbuild(jparse(s)) = s)", "1"),
    ("a string that is a number is quoted unless JB$NUM", C + "c{'n'} = '42'\n   x = jbuild(c):'|':jbuild(c, 4)", "{\"n\":\"42\"}|{\"n\":42}"),
    ("JB$NUM leaves what is not a JSON number in quotes",
     C + "c{'a'} = '007'\n   c{'b'} = '1.5e3'\n   c{'c'} = '+5'\n   c{'d'} = ''\n   x = jbuild(c, 4)", "{\"a\":\"007\",\"b\":1.5e3,\"c\":\"+5\",\"d\":\"\"}"),
    ("JB$NULL writes an empty string as null", C + "c{'e'} = ''\n   x = jbuild(c):'|':jbuild(c, 2)", "{\"e\":\"\"}|{\"e\":null}"),
    ("names in single quotes, or with none", C + "c{'a'} = 'x'\n   x = jbuild(c, 8):'|':jbuild(c, 16)", "{'a':\"x\"}|{a:\"x\"}"),
    ("values in single quotes, or with none", C + "c{'a'} = \"it's\"\n   x = jbuild(c, 32):'|':jbuild(c, 64)", "{\"a\":'it\\'s'}|{\"a\":it's}"),
    ("the modes add: names and values both single quoted", C + "c{'a'} = 'x'\n   x = jbuild(c, 8 + 32)", "{'a':'x'}"),
    ("a file variable has no JSON form: a null string and STATUS() 1019",
     C + "open 'voc' to f else stop 'no voc'\n   c{'f'} = f\n   x = '[':jbuild(c):']':status()", "[]1019"),
    ("...unless JB$INVALID asks for a null", C + "open 'voc' to f else stop 'no voc'\n   c{'f'} = f\n   x = jbuild(c, 1):'|':status()", "{\"f\":null}|0"),
    ("a collection that contains itself cannot be built", C + "c{'me'} = c\n   x = '[':jbuild(c):']':status()", "[]1019"),
    ("the modes have names in keys.h",
     "$include keys.h\n   x = jp$null:'|':jp$unquoted.name:'|':jb$invalid:'|':jb$null:'|':jb$num:'|':jb$squote.name:'|':jb$noquote.name:'|':jb$squote.value:'|':jb$noquote.value", "1|2|1|2|4|8|16|32|64"),
    ("the error codes have names in err.h", "$include err.h\n   x = er$build.error:'|':er$parse.error", "1019|1020"),
    ("ERR: JBUILD() of something that is not a collection", "x = jbuild('abc')", "ERR:not a data collection"),
    # ---- JSON booleans and nulls --------------------------------------------------------------------------------
    ("JBOOLEAN() and JNULL() put true, false and null into a collection",
     C + "c{'t'} = jboolean(1)\n   c{'f'} = jboolean(0)\n   c{'n'} = jnull()\n   x = jbuild(c)", "{\"f\":false,\"n\":null,\"t\":true}"),
    ("a boolean is the number 1 or 0 and a null reads as a null string",
     C + "c{'t'} = jboolean(1)\n   c{'f'} = jboolean(0)\n   c{'n'} = jnull()\n   x = c{'t'} + 0:'|':c{'f'} + 0:'|':'[':c{'n'}:']'", "1|0|[]"),
    ("JBOOLEAN() is true for any other number, text and false for 0, null, 0 and false in any case",
     "x = jboolean(7) + 0:jboolean(0) + 0:jboolean('') + 0:jboolean('0') + 0:jboolean('FaLsE') + 0:jboolean('no') + 0:jboolean('abc') + 0", "1000011"),
    ("JTYPE() names the kind of a value",
     C + "c{'t'} = jboolean(1)\n   c{'n'} = jnull()\n   c{'s'} = 'text'\n   c{'i'} = 5\n   c{'o/p'} = 1\n   c{'a'} = mat()\n"
     "   x = jtype(c{'t'}):'|':jtype(c{'n'}):'|':jtype(c{'s'}):'|':jtype(c{'i'}):'|':jtype(c{'o'}):'|':jtype(c{'a'})", "boolean|null|string|number|collection|array"),
    ("JTYPE() of plain values", "x = jtype(5):'|':jtype(2.5):'|':jtype('5'):'|':jtype(''):'|':jtype(jnull()):'|':jtype(jboolean(1))", "number|number|string|string|null|boolean"),
    ("a boolean in a variable is still a boolean when stored",
     C + "v = jboolean(1)\n   c{'x'} = v\n   w = jnull()\n   c{'y'} = w\n   x = jbuild(c)", "{\"x\":true,\"y\":null}"),
    ("but arithmetic on a boolean gives an ordinary number",
     C + "v = jboolean(1) + 1\n   c{'x'} = v\n   x = jbuild(c):'|':jtype(v)", "{\"x\":2}|number"),
    ("a boolean or null read from a collection keeps its kind through a copy of the collection",
     C + "c{'t'} = jboolean(1)\n   c{'n'} = jnull()\n   d = collection(c)\n   x = jbuild(d)", "{\"n\":null,\"t\":true}"),
    ("and into another collection",
     "c = jparse('{\"t\":true,\"f\":false,\"n\":null}')\n   d = collection()\n   d{'t2'} = c{'t'}\n   d{'f2'} = c{'f'}\n   d{'n2'} = c{'n'}\n   x = jbuild(d)", "{\"f2\":false,\"n2\":null,\"t2\":true}"),
    ("JP$NULL makes a null an ordinary empty string", "c = jparse('{\"n\":null}', 1)\n   x = jtype(c{'n'})", "string"),
    ("and without it a parsed null is a null", "c = jparse('{\"n\":null,\"t\":true}')\n   x = jtype(c{'n'}):'|':jtype(c{'t'})", "null|boolean"),
    ("a null is an empty string to everything else", "x = '[':jnull():']':len(jnull()):(jnull() = '')", "[]01"),
    ("booleans and nulls survive MAT and MAT()",
     C + "c{'a'} = mat()\n   c{'a',1} = jboolean(1)\n   c{'a',2} = jnull()\n   dim n(2)\n   mat n = mat c{'a'}\n   d = collection()\n   d{'b'} = mat(n)\n   x = jbuild(d):'|':jtype(n(1)):'|':jtype(n(2))", "{\"b\":[true,null]}|boolean|null"),
    # ---- += -= *= /= := on an element --------------------------------------------------------------------------
    ("+= on an element that is not there starts from nothing", C + "c{'n'} += 5\n   x = c{'n'}", "5"),
    ("+= -= *= /= on an element",
     C + "c{'n'} = 10\n   c{'n'} += 5\n   x = c{'n'}\n   c{'n'} -= 3\n   x := '|':c{'n'}\n   c{'n'} *= 2\n   x := '|':c{'n'}\n   c{'n'} /= 4\n   x := '|':c{'n'}", "15|12|24|6"),
    (":= on an element joins on the end", C + "c{'s'} := 'ab'\n   c{'s'} := 'cd'\n   x = c{'s'}", "abcd"),
    ("the new value is worked out before it is stored, so the right side can read the element",
     C + "c{'n'} = 4\n   c{'n'} += c{'n'} * 2\n   x = c{'n'}", "12"),
    ("an operator on an array element", C + "c{'a'} = mat()\n   c{'a',1} = 1\n   c{'a',1} += 4\n   c{'a',2} := 'x'\n   x = c{'a',1}:'|':c{'a',2}", "5|x"),
    ("an operator along a path that is not there makes the levels", C + "c{'x/y'} += 1\n   x = c{'x'}{'y'}", "1"),
    ("an operator on a boolean gives an ordinary number", C + "c{'t'} = jboolean(1)\n   c{'t'} += 1\n   x = jbuild(c)", "{\"t\":2}"),
    (":= with a null string leaves the element as it was",
     C + "c{'s'} = 'a'\n   c{'s'} := ''\n   x = c{'s'}", "a"),
    # ---- HU conversion ------------------------------------------------------------------------------------------
    ("OCONV(,'HU') escapes a URL as the openQM page shows it",
     "x = oconv('http://domain.com/hello?a=b', 'HU')", "http%3a%2f%2fdomain.com%2fhello%3fa%3db"),
    ("ICONV(,'HU') undoes it", "x = iconv('http%3a%2f%2fdomain.com%2fhello%3fa%3db', 'HU')", "http://domain.com/hello?a=b"),
    ("letters, digits and - . _ ~ are left alone, a space is %20", "x = oconv('Az09-._~ ', 'HU')", "Az09-._~%20"),
    ("a mark is escaped too", "x = oconv('a':@fm:'b', 'HU')", "a%feb"),
    ("a % that is not followed by two hex digits, and a +, are left as they are",
     "x = iconv('%41%4A+%zz%4', 'HU')", "AJ+%zz%4"),
    ("a null string stays null", "x = '[':oconv('', 'HU'):']':'[':iconv('', 'HU'):']'", "[][]"),
    ("a name made with HU keeps its slashes out of the path",
     C + "k = oconv('a/b', 'HU')\n   c{k} = 'v'\n   x = c{k}:'|':element.exists(c, 'a/b'):'|':enumerate(c):'|':iconv(enumerate(c), 'HU')", "v|0|a%2fb|a/b"),
    ("an unknown conversion after H leaves the data and sets STATUS() 2", "x = oconv('a', 'HUX'):'|':status()", "a|2"),
    # ---- collections and subroutines ----------------------------------------------------------------------------
    ("a collection passed to a subroutine is the caller's own", C + "call zzcsub1(c)\n   x = c{'k'}", "set by sub"),
    ("a subroutine can make a collection and hand it back through an argument", "call zzcsub2(r)\n   x = r{'a'}:'|':jtype(r)", "1|collection"),
    ("calling a subroutine again and again with collections of its own is safe",
     "for i = 1 to 300\n   call zzcsub3(i, t)\n   next i\n   x = t", "300"),
    ("ERR: a variable that is not a collection cannot take an element", "n = 5\n   n{'a'} = 1", "ERR:not a data collection"),
    ("ERR: nor can one be read from it", "n = 5\n   x = n{'a'}", "ERR:not a data collection"),
    ("ERR: an element cannot be added below a value that is not a collection",
     C + "c{'a'} = 1\n   c{'a/b'} = 2", "ERR:passes through a value that is not a collection"),
    ("ERR: an empty name is refused", C + "c{''} = 1", "ERR:Invalid data collection element name"),
    ("ERR: so is an empty part of a path", C + "c{'a//b'} = 1", "ERR:Invalid data collection element name"),
    ("ERR: a missing right curly bracket is a compile error", C + "x = c{'a'", "ERR:Right curly bracket"),
]


# Subroutines the cases above call.  Each is written, compiled and catalogued LOCAL before the cases run.
SUBS = {
    "zzcsub1": "   subroutine zzcsub1(c)\n   c{'k'} = 'set by sub'\n   return\nend\n",
    "zzcsub2": "   subroutine zzcsub2(out)\n   out = collection()\n   out{'a'} = 1\n   return\nend\n",
    "zzcsub3": "   subroutine zzcsub3(n, out)\n   local = collection()\n   local{'v'} = n\n   local{'big/deep/er'} = n\n   out = local{'v'}\n   return\nend\n",
}


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
    say("sandbox-coll: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > %d commands" % len(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, timeout=900)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-coll.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-coll: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-coll: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    cmds, names = [], []
    for sub, src in SUBS.items():
        names.append(sub)
        with open(os.path.join(sysd, "bp", sub), "w") as f:
            f.write(src)
        cmds += ["BASIC bp %s" % sub, "CATALOG bp %s LOCAL" % sub]
    for i, (_, body, _w) in enumerate(CASES):
        nm = "zzco%02d" % i
        names.append(nm)
        with open(os.path.join(sysd, "bp", nm), "w") as f:
            f.write("   x = ''\n   " + "".join("%s\n   " % ln for ln in body.split("\n")) + "crt 'C%02d[':x:']'\nend\n" % i)
        cmds += ["BASIC bp %s" % nm, "RUN bp %s" % nm]
    cmds += ["DELETE.CATALOG %s LOCAL" % sub for sub in SUBS]
    try:
        out = sess(box, *cmds)
        try:
            with open(os.path.join(box, "coll.last.out"), "w") as f:   # for finding out why a row failed
                f.write(out)
        except OSError:
            pass
        say("\n--- collections -------------------------------------------------------------")
        starts = {}
        for m in re.finditer(r"(?m)^:BASIC bp zzco(\d{2,})\s*$", out):
            starts[int(m.group(1))] = m.start()
        for i, (label, _body, want) in enumerate(CASES):
            if i not in starts:
                row(label, False, "its compile was never seen in the output")
                continue
            later = [s for k, s in starts.items() if s > starts[i]]
            seg = out[starts[i]:(min(later) if later else len(out))]
            if want.startswith("ERR:"):
                text = want[4:]
                row("%s: wanted the text %r" % (label, text), text in seg and not re.search(r"(?m)^C%02d\[" % i, seg),
                    "output: %s" % seg[-300:])
            else:
                m = re.search(r"(?m)^C%02d\[(.*)\]\s*$" % i, seg)
                got = m.group(1) if m else None
                row("%s: wanted %r" % (label, want), got == want, "got %r  %s" % (got, seg[-200:]) if not m else "got %r" % got)
    finally:
        for nm in names:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-coll: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

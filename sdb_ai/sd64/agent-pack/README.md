# agent-pack: what an AI agent needs to work in SD Core for Linux

S.69 rows 1 and 1b of the AI plan. Documents, a generator and free and sandbox checks. **Nothing here is installed, compiled into SD or shipped by the installer** (it reads `sdsys`, `bin`, `gplsrc`, `gplobj`, `terminfo` and a few `gplbld` files; this directory is none of those), and nothing here calls a model, holds a key, opens a gate or changes ssh.

| path | what | made by |
|---|---|---|
| `guide/sd-basic-guide.md` | the SD BASIC dialect guide: language, system, walls, 20+ worked programs | by hand; every block compiled and run by `gplbld/sandbox-guide.py` |
| `pack/` | the generated knowledge pack: one chunk per TCL verb, query keyword, VOC type, dictionary type and conversion, BASIC statement, function, `$mode`, option, message, account word, setting and key group, with the source and line of each | `mkpack.py`; guarded by `gplbld/test-pack-units.py` |
| `core-start.md` | the "start here" text embedded in the pack's core | by hand |
| `skill/sd-core/` | a Claude Code skill: `SKILL.md` by hand, `references/` (the guide and the pack) generated | `mkpack.py --write` |
| `templates/` | a CLAUDE.md template for a project that lives in an SD account; an `.mcp.json` shape that does NOT work yet | by hand |
| `recipe/agent-account.md` | the zero-code recipe: give the agent its own OS user and SD account so the operating system is the wall | by hand |
| `PACKAGING.md` | the packaging facts verified from the official pages | by hand |

Regenerate after a change to a verb, a message, a bcomp table, a docs section the pack quotes, the shipped dictionaries, the guide or the stamp:

```
python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/agent-pack/mkpack.py --write
python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-pack-units.py
```

The generator takes the tree and the docs checkout as arguments (`--tree DIR --docs DIR --out DIR --skill DIR --product NAME`) so that SD Core Solo for Linux can run it on its own tree and its own docs. It reads the docs repository by absolute path (`/home/don/Projects/SDCore4LinuxDocs`) and exits 2, saying so, when the checkout is missing.

Line numbers in `src=path:line#hash` are locators that may lag after an edit elsewhere in the same file; the hash of the cited line is the identity and is what the check holds.

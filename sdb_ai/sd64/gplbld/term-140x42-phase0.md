# Terminal 140x42, phase 0: what the tree does today (measured 18 Oct 2026)

Tree: Dev `1adf913`, plain `make`, a sandbox built by `sandbox-fromtree.py` (keyset 2). Pseudo-terminal runs use
`ptydrive.py` and `termscreen.py`, the window size set before SD starts, `TERM xterm`, `LC_ALL=C`. Nothing here is a
change; the numbers are what the unchanged tree printed.

## The display size SD starts with

| session | `@crtwide x @crthigh` | where it comes from |
|---|---|---|
| pty 80x24, 100x30, 140x42, 200x60 | the window | `linuxio.c read_window_size()` at start and at every SIGWINCH; `kernel(K$WINSIZE)` answers `w<VM>h` |
| no tty (pipe), any `TERM` (xterm, linux, vt100, dumb) | 120x36 | `init_console()` 120/36, then LOGIN: `LINES`/`COLUMNS` from the environment, else terminfo `lines`/`cols`, else `DEFAULT.DEPTH/WIDTH` |
| no tty, `COLUMNS=90 LINES=33` | 90x33 | LOGIN, the environment |
| `TERM DEFAULT`, on a pty of any size or on a pipe | 120x36 | `term` uses `DEFAULT.WIDTH/DEPTH` (`int$keys.h`) |
| phantom, API server, socket before LOGIN | 120 wide, `lines_per_page` 37 | `op_tio.c tio_init()` only: `init_console()` is not run for these |

`tio_init` says 37 and `init_console` 36. 37 is the text of the original Ladybridge source (the Windows tree has it too,
`op_tio.c:3250`) and nothing in either tree's record says why. It is reachable only by a connection that never runs
`init_console()`, and LOGIN's `setpu` replaces it for any interactive socket session. Phase 1 keeps the relation (+1).

## TERM w,h and the sign-on answer: no ceiling exists

`TERM 200,9999`, `300,70`, `255,255`, `256,256`, `1000,500` and `32767,32767` were typed on a pipe session and on pty
sessions of the four sizes; `@crtwide`, `@crthigh` and the print unit's width and length (`getpu(PU$WIDTH/PU$LENGTH,-1)`)
all read back exactly what was typed. `TERM 19,9` and `TERM 33000,50` are refused by the verb's own range check
(messages 6850/6851: width 20-32767, depth 10-32767). The only limits in the path are those and the floor LOGIN and
`read_window_size()` apply (MIN.WIDTH 20, MIN.DEPTH 10). `sandbox-fromtree.py sess` types `TERM 200,9999` as its first
line. The ceiling the plan says was seen in a sandbox could not be reproduced on any path tried, and a search of
`gplsrc` for assignments to the display's width and lines per page (`linuxio.c`, `op_tio.c`) and of `login`/`term` finds
no upper bound beyond the range check. Nothing to remove.

Note: `TERM w,h` does not change `K$WINSIZE` (the tty's own answer) and holds until the next SIGWINCH.

## What each program does at four window sizes

| program | 80x24 | 100x30 | 140x42 | 200x60 |
|---|---|---|---|---|
| `SED file id` | refused: message 11197, "at least 120 columns by 36 lines; this one is 80 by 24" | refused (100 by 30) | drawn 120x36, upper left; bar row 1, file line row 35, status row 36; rest of the window blank | same as 140x42 |
| `IDE` | drawn for the window (whole window used, tree column a little narrower) | same | same | same |
| `IDE` below 60x16 | refused: message 11198 at 59x20, 60x15, 40x12, 30x10 | | | |
| `CED coll id` | drawn for the window | same | same | same; no refusal found down to 30x10 |
| debugger (`DEBUG` in a program compiled `DEBUGGING`) | full screen, window sized: title row 1, source, command line on the last row | same | same | same |
| `SCREEN OPEN CLEAR` user program | library draws in the window; a cell outside it is dropped, not wrapped | same | text at column 130 row 41 shown | same |
| `SCREEN OPEN CLEAR MINSIZE 140,42` | ELSE taken, screen not taken (program printed its own line) | ELSE | opens | opens |

## How each reads keys and draws

| program | keys | drawing | sizes read |
|---|---|---|---|
| SED (`gpl.bp/sed`, 10431 lines) | its own `getch` (`keyin()`; `getch` at 4918, three direct `keyin()` at 5199, 5216, 5286, the Esc timing at 4774); mouse decoded in SED | 28 lines holding `@(` (about 25 `display`/`crt` cursor or clear sites, the rest attribute reads); menu bar and message boxes through `$sl_menu`, `$sl_msgbox`; colour runs `$sl_sgr`; syntax `$sl_syntax` | once at 316-325 (`K$WINSIZE` against `SED.COLS 120` / `SED.ROWS 36`), never again |
| IDE (`gpl.bp/ide`, 1192 lines) | the library: `screen wait` (150), `screen menubar`, `screen msgbox`, `screen ask` -> `$sl_key`, which returns `resize` | the library; two `display @(-1)` clears only (190, 996) | `$sl_scr('get')` after `screen open`; MINW 60, MINH 16 (55-56) refuse at 84-89 |
| CED (`ced`, `ced_edit`, `ced_sub`) | `screen key` (ced_edit 117) | the library; no direct `@()` | `@crtwide`/`@crthigh` at ced_edit 83-84 |
| debugger (`gpl.bp/debug`, 2050 lines) | its own `keycode()` loop (800-830, `get.input`) | 9 direct `@(` sites; the full-screen display through `$sl_put`; `full.screen` set at 700-702 from `K$WINSIZE` and terminfo `smcup`/`rmcup` | `@crtwide`/`@crthigh` at 61-62, 671-676, 1130 |
| `SCREEN OPEN` programs | `screen key`/`screen wait` | the library's virtual screen | `!screen_open` tests `MINSIZE` against `@crtwide/@crthigh` (51-52) |

So one guard in `$sl_key` serves IDE, CED and user screen programs; SED and the debugger each need their own, in
`getch` and `keycode` respectively.

## Where 120 and 36 are written (the edit list, checked against the tree)

- `gplsrc/linuxio.c:341-342` (`init_console`), and the comment at 94-100.
- `gplsrc/op_tio.c:3330` (`tio_init`, 37 x 120).
- `sdsys/gpl.bp/int$keys.h:41,44` (`DEFAULT.WIDTH`, `DEFAULT.DEPTH`), used by `login` (200, 205) and `term` (173-174).
- `sdsys/gpl.bp/term` header (33) and the 8 Sep note (169); `login` comment (194).
- `terminfo.src`: 44 lines with `cols#120` (40 with `lines#36`, three with no `lines`, `ms-vt100` with `lines#25`); five
  `cols#132` entries also say `lines#36`.
- `sdsys/messages/11197` (SED's refusal, tied to `SED.COLS`/`SED.ROWS` at `sed:320-321`); no other message carries 120 or 36.
- Not touched by phase 1: `SED.COLS/ROWS`, message 11197, IDE `MINW/MINH`; they belong to the SED and refusal phases.

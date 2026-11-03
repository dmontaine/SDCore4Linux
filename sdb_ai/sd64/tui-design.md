# SD Core TUI design - the full-screen pages, as built

Written 2 Nov 2026 (S.88 step p7A), after the page conversions, so that it says what the tree DOES, not what was planned.
It is the authority for the common rules of SD's full-screen apps: a page that breaks one of them is a defect, or an exception
listed in section 7 with its reason. Where an older design note (`screenlib-design.md`, the planning notes) disagrees, this
document wins.

Every rule has a tag:

- **BUILT** - in the tree today; the evidence column names the check that holds it.
- **PLANNED** - not built. The evidence column names a `marker:`, a piece of source text that does not occur in `sdsys/gpl.bp`
  today. When the feature is built the marker appears, `gplbld/test-tuidesign-units.py` fails, and the row must be moved to BUILT
  in the same commit.
- **DROPPED** - decided against, or retired; it must not come back without the owner's word.
- **EXCEPTION** - an app or a key that is allowed to differ, and why.
- **OPEN** - a known difference put to the owner and not yet decided; the row says what holds until he answers.

A suite named in the evidence column that has not been run says so ("WRITTEN, NOT RUN"). The free check that holds this document
against the tree is `gplbld/test-tuidesign-units.py` (no install, no sd; `--selftest` runs its mutants).

## 1. The frame

| Id | Rule | Tag | Evidence |
|----|------|-----|----------|
| F1 | Every full-screen app is laid out for 140 columns by 43 rows at least (`TK.MINW 140`, `TK.MINH 43` in `tk.h`; the IDE's `LAYW = 140`, `LAYH = 43`). A bigger window is used whole; a smaller one is refused at the start, and if it shrinks while the app runs the keyboard is held until it is big enough again. | BUILT | test-tuidesign-units.py T1, test-tklayout-units.py |
| F2 | A session whose terminal gives no size answer gets 140 by 43 (`DEFAULT_WIDTH 140`, `DEFAULT_DEPTH 43` in `gplsrc/tio.h`, `DEFAULT.DEPTH` in `int$keys.h`): exactly F1's floor, so the pages open in it (the owner, 2 Nov 2026: "Change to 43"; it was 42 and every page refused such a session). | BUILT | test-tuidesign-units.py T8 |
| F3 | Row 0 is the menu bar; under it the body; the last three rows are the status line, a border and the function-key row. The right end of row 0 names the app and the audience ("administrator" or name@account), written by `$tk_frame` after the bar. | BUILT | test-tkbase-units.py, sandbox-home.py U9b |
| F4 | A page opens and closes the screen through `$tk_open` and `$tk_close`, and draws its frame through `$tk_frame` on every pass of its loop. An administrator page asks for the administrator in `$tk_open` (audience `admin`) before it reads anything. | BUILT | test-tuidesign-units.py T2 |
| F5 | A page's panes are declared to the layout service (`$tk_layout 'declare'`) at their 140 by 43 sizes; a resize is `$tk_layout 'refresh'` and the page is laid out again from the rectangles it gives. | BUILT | test-tklayout-units.py, test-l2-home-units.py |
| F6 | Two or more boxes that can take the focus are marked by `$tk_frame` (the page names them in `ctx<TK.C.FOCI>`); Tab and Shift-Tab move the focus between them on every such page (the owner's "Tab panes", 2 Nov 2026; tool.test had only Enter and Esc until 3 Nov 2026). | BUILT | test-focusmarks-units.py (Tab panes), sandbox-tool-test.py tab |

## 2. Keys and the menu bar

| Id | Rule | Tag | Evidence |
|----|------|-----|----------|
| K1 | The page's key table (`$tk_keys`, `tk.h` TK.K.*) is the one registry: the function-key row (`$tk_fkeys`), F1's list of keys (`$tk_help 'box'`, through the named common `/tkreg/` that `$tk_frame` fills) and the menu bar are all made from it, so they cannot disagree. A key may be bound but kept off the function-key row (TK.K.ROW 0). | BUILT | test-tk-keys-units.py |
| K2 | The menu bar is `$tk_menubar`: drawn on row 0 before `$tk_frame`, opened by F10, by Alt and a title's letter, by a click on row 0, and by Esc (K4). Its menus are File first and Help last. **It runs nothing**: an entry returns the key its action is bound to and the page's own case for that key does the work, with the page's own gates. | BUILT | test-tk-keys-units.py (samehandler), test-tuidesign-units.py T3 |
| K3 | Every action on the bar has a key, so the bar has something to replay. An action that cannot be used now is given a reason (`$tk_keys 'why'`): its entry is dimmed and cannot be chosen, and its key is out of use. | BUILT | test-tk-keys-units.py, test-home-units.py H82 |
| K4 | **The Esc rule.** Esc first closes what the page holds open (a filter, a sub-view, the output pane, a sub-menu page): the page tells the bar so (`busy`). Otherwise Esc opens the bar, on the first menu whose first entry is not Quit, so Esc then Enter never leaves a page. | BUILT | test-tk-keys-units.py (ESC_LEDGER), sandbox-home.py U9g |
| K5 | F1 is help on every page (`$tk_help 'box'` with the page's own record of `helptext`, which names its documentation page); Ctrl-Q quits. | BUILT | test-tuidesign-units.py T4, test-help-units.py |
| K6 | F6 reaches the AI line on every page (the owner's ruling of 1 Nov 2026): `$tk_aipage` adds the F6 row and the AI > Ask the AI entry when the AI is usable for the account, and the page's own case for F6 gives the line the focus. Without the AI nothing is added and nothing is drawn. | BUILT | test-tuidesign-units.py T5, test-aipage-units.py |
| K7 | F2 finds an action on every page that has the bar (the owner's "F2 finder", 2 Nov 2026): `$tk_menubar` opens `$sl_palette` on the bar's own menus, every entry as "Menu > Entry" with its key, typing narrows the list, Enter chooses. It answers exactly as the bar does (the action's key, replayed through the page's own case); an entry that cannot be used now says why in a box and is never answered. No page binds F2 (a page that did would win in its pane). | BUILT | test-tk-keys-units.py (finder, reserved), sandbox-tool-query.py q14 |
| K8 | A context menu on every page that has the bar: a right click anywhere opens it at the pointer, Shift-F10 in the middle. It lists the entries of the bar's menus (not File and Help) whose action the pane with the focus uses, dimmed when not usable now, then "Find an action..." (F2). It answers as the bar does. The Menu key is not decoded (a terminal sends it as a key SD does not name), so Shift-F10 is the keyboard's way. | BUILT | test-tk-keys-units.py (finder, reserved), sandbox-tool-query.py q14 |
| K9 | F11 is bound by no page. F10 is the bar's and is not a page's own row (only the test app E2 binds either). | BUILT | test-tk-keys-units.py (reserved), test-tuidesign-units.py T3 |

## 3. Boxes, forms and panes

| Id | Rule | Tag | Evidence |
|----|------|-----|----------|
| W1 | A command a page runs is shown first in a confirm box (`$tk_confirm`): Run and Cancel, **Cancel the default**, so Enter alone never runs anything; a destructive act or a gate that reaches beyond SD also asks for a name to be typed. The page then runs the same sentence with `$tk_run`. | BUILT | test-tuidesign-units.py T6, test-help-units.py |
| W2 | A labelled form is `$tk_form` (open, run, say, close): the page validates, the form does not. | BUILT | test-tkout-units.py O7-O10 |
| W3 | A file or a record is picked with `$tk_pickrec` (read only: it opens for reading, takes no lock, writes nothing). Its mode `list` picks from a list the page gives (the home screen's type-to-find of a tile). | BUILT | test-tkout-units.py O6, test-slpick-units.py, sandbox-home.py U9j-U9n |
| W4 | Results, refusals and command output go to the output pane `$tk_out` (Ctrl-O), whose history is kept in memory for one open of the page and never written. | BUILT | test-tkout-units.py O1-O5 |
| W5 | Message boxes and questions are the library's (`SCREEN MSGBOX`, `$tk_confirm`); a box puts back what was under it. | BUILT | sandbox-tk-widgets.py (WRITTEN, NOT RUN) |

## 4. The theme

| Id | Rule | Tag | Evidence |
|----|------|-----|----------|
| T1 | The library draws with styles; a theme says how each looks. The codes are `SL.CODES` in `sl.h`; the roles are error `f`, warning `U`, success `V`, readonly `W`, busy `X`, focus `Y`, and every theme gives each a look (mono with flags only). | BUILT | test-themeroles-units.py; sandbox-themeroles.py (WRITTEN, NOT RUN) |
| T2 | The site's theme is `SCREENTHEME` in `sd.conf` (shipped `blue`); the installer adds `SCREENTHEME=blue` to a restored `sd.conf` that has no such line. A program that asks for no theme, with a blank or unknown name, gets `mono`. | BUILT | test-themeroles-units.py R6-R7, test-install-screentheme.sh |
| T3 | A page offers no theme choice of its own; Keys (tool.keys) shows the next theme the terminal can show. | BUILT | test-themeroles-units.py R5 |

## 5. Pages on the frame

Every `tool_*` program of `sdsys/gpl.bp` is a page and is listed here; the check fails on a page that is missing or one listed that
is not there. "Rules" says which of sections 1-4 it follows: `all`, or the exception in section 7.

| Program | Verb | Audience | Rules |
|---------|------|----------|-------|
| `tool_accounts` | tool.accounts | administrator | all |
| `tool_ai` | tool.ai | administrator | all |
| `tool_audit` | tool.audit | administrator | all |
| `tool_backups` | tool.backups | administrator | all |
| `tool_bulk` | tool.bulk | everyone | all |
| `tool_catalog` | tool.catalog | everyone | all |
| `tool_config` | tool.config | administrator | all |
| `tool_dict` | tool.dict | everyone | all |
| `tool_entries` | tool.entries | administrator | all |
| `tool_files` | tool.files | everyone | all |
| `tool_gates` | tool.gates | administrator | all |
| `tool_home` | home | everyone | E6 |
| `tool_jobs` | tool.jobs | administrator | all |
| `tool_keys` | tool.keys | everyone | E1 |
| `tool_menus` | tool.menus | administrator | all |
| `tool_mygates` | tool.gates (an account holder's) | everyone | all |
| `tool_query` | tool.query | everyone | all |
| `tool_remote` | tool.remote | administrator | all |
| `tool_sessions` | tool.sessions | administrator | all |
| `tool_test` | tool.test | everyone | all |
| `tool_tktest` | tktest (no VOC entry) | test only | E2 |
| `tool_viewers` | tool.viewers | administrator | all |
| `tool_voc` | tool.voc | everyone | all |

## 6. Dropped

| Id | Rule | Tag | Evidence |
|----|------|-----|----------|
| D1 | The master-file copies page (`tool_masters`) is retired with the copies; Master files is `tool.entries`. | DROPPED | test-tuidesign-units.py T7 (no `tool_masters` in gpl.bp) |
| D2 | A page building its own `SCREEN MENUBAR` array (the home screen did until 2 Nov 2026). Only the registry's pilot `tool_tktest` still does. | DROPPED | test-tuidesign-units.py T3 |

## 7. Exceptions

| Id | App | What differs | Why | Tag |
|----|-----|--------------|-----|-----|
| E1 | `tool_keys` | No menu bar, no Esc rule, no F1. | It exists to show every key, Esc, F10 and Alt and a letter included, before acting on any (the owner's answer 18, 29 Oct 2026). | EXCEPTION |
| E2 | `tool_tktest` | A throw-away test app of the registry; its own `SCREEN MENUBAR`, F2, F6, F10 and F11. | It is not a verb of the product and goes with the tests (the owner's answer 18). | EXCEPTION |
| E3 | the debugger (`debug`) | Its own chrome and keys (F2 is abort, as it has been since 2004); on a terminal with no alternate screen it takes the main screen, and on one it cannot draw on it falls back to line mode. | Its command loop predates the toolkit and its keys are users' habit. | EXCEPTION |
| E4 | SED and CED (`sed`, `ced`, `ced_core`) | Their own key maps (SED's multivalue keys, CED's openQM keys); only their look follows the theme. | Frozen except look (the owner, 28 Oct 2026). | EXCEPTION |
| E5 | the IDE (`ide`) | Its menus come from messages 11225-11230, 11590 and 11654: File, Go, Search, Build, View, Tools, AI, Help (there is no Edit menu); F6 is its next pane; it has no F2 finder and no context menu (its menus are not made from a key table). Tools opens the development pages (Files, Dictionary, Vocabulary, Queries, Bulk update, Programs, Tests), each through the IDE's terminal hand-over as Run is, and the IDE comes back after Return. | Its panes are not decided (S.99); the menus are messages so they can be checked for mnemonics. | EXCEPTION |
| E6 | `tool_home` (the home screen) | Its AI line is `$tk_ai` itself (it takes the hint row; F6 and AI > Ask the AI give it the focus) and not `$tk_aipage`; Ctrl-Q signs out after asking (it has no quit); Backspace also goes back one sub-menu page; on the top page Esc then Enter reaches File > Sign out, whose box defaults to Cancel. | It is the place a session starts and ends; its line predates `$tk_aipage` and offers tiles, not keys. | EXCEPTION |

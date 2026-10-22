* TK.H
* The full-screen toolkit's shared base (S.75, plan .claude/plan-fullscreen-toolkit.md): the layout and the two tables every app uses.
* Copyright (c) 2026, SD Core for Linux.  This program is free software; you can redistribute
* it and/or modify it under the terms of the GNU General Public License, version 3 or later.
*
* START-HISTORY:
* 22 Oct 26 dm  New (TK-0.1: the frame, the key table and the function-key row).
* END-HISTORY
*
* THE MINIMUM WINDOW is 140 columns by 43 lines (the owner's ruling of 20 Oct 2026).  The 43rd line is the function-key row, outside the window below its border.
*
* THE FOOT OF THE SCREEN, counted from the last row of the layout (the layout is the window when it is bigger than the minimum, the minimum when it is smaller):
*      row H-1   the function keys      (YKEYS)
*      row H-2   the border             (YBORD)
*      row H-3   the status line        (YSTAT)   [pane]  message
*   and row 0 is the menu bar, whose right end holds the app's name and the audience (an app that has a menu draws the menu first).
*
* THE CONTEXT ctx is one dynamic array made by $tk_open and given to every other routine:
$define TK.MINW        140
$define TK.MINH        43
$define TK.C.W         1       ;* the layout's width: the window's, or TK.MINW when it is smaller
$define TK.C.H         2       ;* the layout's height
$define TK.C.UTF8      3       ;* 1 when the terminal says UTF-8 (the screen was opened with line drawing)
$define TK.C.TRAP      4       ;* the break setting before the app took it, for $tk_close to give back
$define TK.C.APP       5       ;* the app's name, for the right end of row 0
$define TK.C.AUD       6       ;* the audience as the person reads it: "administrator", or "name@account"
$define TK.C.YSTAT     7       ;* the row of the status line
$define TK.C.YBORD     8       ;* the row of the border
$define TK.C.YKEYS     9       ;* the row of the function keys
*
* THE KEY TABLE is one dynamic array, a key to a field; the values of a field are:
$define TK.K.KEY       1       ;* the key as $sl_key names it: f1, tab, ctrl-q ...
$define TK.K.LABEL     2       ;* what the function-key row says it does: help, sort ...
$define TK.K.ACT       3       ;* the action id the app acts on
$define TK.K.PANES     4       ;* sub-values: the panes that use the key; null is every pane
$define TK.K.ON        5       ;* 0 takes the key out of the row (and of the action lookup); null or 1 leaves it in

#!/usr/bin/env python3
#
# termscreen.py - a small VT100 screen, so a test can read what a full-screen SD program DREW rather than the
# stream of bytes it wrote.  No dependencies.
#
#   from termscreen import Screen
#   s = Screen(100, 20)
#   s.feed(output_text)
#   s.lines()          the rows now on the screen, trailing spaces removed
#   s.before_clear     the rows as they were just before the LAST clear of the whole screen - which, for a
#                      program that clears the screen as it exits, is the program's last screen
#   s.reverse(row)     the text drawn in reverse video on that row (the selected line of a menu)
#
# It understands what SD's terminfo entries for the xterm type send: cursor positioning (CSI r;c H), clear
# screen (CSI 2 J), erase in line and display, cursor moves, delete / insert character, the attribute switch
# (only reverse video is kept), carriage return, newline (with scrolling), backspace and tab.  Everything else
# (modes, colours, the keypad switch) is read and ignored.  START-HISTORY:
# 12 Oct 26 dm  New, for sandbox-ced.py.
# END-HISTORY

import re

CSI = re.compile(r"\x1b\[([0-9;?]*)([ -/]*)([@-~])")


class Screen:
    def __init__(self, cols=100, rows=24):
        self.cols = cols
        self.rows = rows
        self.grid = [[" "] * cols for _ in range(rows)]
        self.rev = [[False] * cols for _ in range(rows)]
        self.r = 0
        self.c = 0
        self.reverse_on = 0            # the current style: bit 1 reverse, bit 2 underline (the grid keeps it per cell)
        self.cursor_visible = True
        self.before_clear = None
        self.clears = 0

    def _blank_row(self):
        return [" "] * self.cols, [False] * self.cols

    def _scroll(self):
        self.grid.pop(0)
        self.rev.pop(0)
        g, v = self._blank_row()
        self.grid.append(g)
        self.rev.append(v)

    def _put(self, ch):
        if self.c >= self.cols:
            self.c = 0
            self._newline()
        self.grid[self.r][self.c] = ch
        self.rev[self.r][self.c] = self.reverse_on
        self.c += 1

    def _newline(self):
        if self.r == self.rows - 1:
            self._scroll()
        else:
            self.r += 1

    def lines(self):
        return ["".join(row).rstrip() for row in self.grid]

    def reverse(self, row):
        return "".join(ch for ch, v in zip(self.grid[row], self.rev[row]) if v & 1).strip()

    def underline(self, row):
        """The text drawn underlined on that row."""
        return "".join(ch for ch, v in zip(self.grid[row], self.rev[row]) if v & 2).strip()

    def attrs(self, row):
        """One code per cell of the row, as the screen library names them: n normal, r reverse, u underline, x both."""
        return "".join("nrux"[v & 3] for v in self.rev[row])

    def _csi(self, params, final):
        nums = [int(p) if p.isdigit() else None for p in params.split(";")] if params and not params.startswith("?") else []
        n1 = nums[0] if nums and nums[0] is not None else None
        if params.startswith("?"):
            if params == "?25" and final in "lh":
                self.cursor_visible = (final == "h")
            return   # the other modes (keypad, margins): not drawing
        if final in "Hf":
            row = (nums[0] if len(nums) > 0 and nums[0] else 1) - 1
            col = (nums[1] if len(nums) > 1 and nums[1] else 1) - 1
            self.r = min(max(row, 0), self.rows - 1)
            self.c = min(max(col, 0), self.cols - 1)
        elif final == "J":
            mode = n1 if n1 is not None else 0
            if mode == 2:
                self.before_clear = self.lines()
                self.clears += 1
                for i in range(self.rows):
                    self.grid[i], self.rev[i] = self._blank_row()
            elif mode == 0:
                for j in range(self.c, self.cols):
                    self.grid[self.r][j] = " "
                    self.rev[self.r][j] = False
                for i in range(self.r + 1, self.rows):
                    self.grid[i], self.rev[i] = self._blank_row()
        elif final == "K":
            mode = n1 if n1 is not None else 0
            lo, hi = (self.c, self.cols) if mode == 0 else ((0, self.c + 1) if mode == 1 else (0, self.cols))
            for j in range(lo, hi):
                self.grid[self.r][j] = " "
                self.rev[self.r][j] = False
        elif final == "A":
            self.r = max(self.r - (n1 or 1), 0)
        elif final == "B":
            self.r = min(self.r + (n1 or 1), self.rows - 1)
        elif final == "C":
            self.c = min(self.c + (n1 or 1), self.cols - 1)
        elif final == "D":
            self.c = max(self.c - (n1 or 1), 0)
        elif final == "G":
            self.c = min(max((n1 or 1) - 1, 0), self.cols - 1)
        elif final == "d":
            self.r = min(max((n1 or 1) - 1, 0), self.rows - 1)
        elif final == "P":
            k = n1 or 1
            row, rv = self.grid[self.r], self.rev[self.r]
            del row[self.c:self.c + k]
            del rv[self.c:self.c + k]
            row.extend([" "] * (self.cols - len(row)))
            rv.extend([False] * (self.cols - len(rv)))
        elif final == "@":
            k = n1 or 1
            row, rv = self.grid[self.r], self.rev[self.r]
            row[self.c:self.c] = [" "] * k
            rv[self.c:self.c] = [False] * k
            del row[self.cols:]
            del rv[self.cols:]
        elif final == "m":
            codes = [x for x in params.split(";")] if params else ["0"]
            for code in codes:
                if code in ("", "0"):
                    self.reverse_on = 0
                elif code == "27":
                    self.reverse_on &= ~1
                elif code == "7":
                    self.reverse_on |= 1
                elif code == "24":
                    self.reverse_on &= ~2
                elif code == "4":
                    self.reverse_on |= 2

    def feed(self, text):
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == "\x1b":
                m = CSI.match(text, i)
                if m:
                    self._csi(m.group(1), m.group(3))
                    i = m.end()
                    continue
                # ESC 7 / 8 (save / restore cursor), ESC = and ESC > (keypad), ESC ( B and the like
                if i + 1 < n and text[i + 1] in "()":
                    i += 3
                else:
                    i += 2
                continue
            if ch == "\r":
                self.c = 0
            elif ch == "\n":
                self._newline()
            elif ch == "\b":
                self.c = max(self.c - 1, 0)
            elif ch == "\t":
                self.c = min((self.c // 8 + 1) * 8, self.cols - 1)
            elif ch == "\x07" or ch == "\x0e" or ch == "\x0f":
                pass
            elif ch < " ":
                pass
            else:
                self._put(ch)
            i += 1


if __name__ == "__main__":
    s = Screen(20, 4)
    s.feed("\x1b[H\x1b[2Jhello\x1b[2;3Hxy\x1b[7mREV\x1b[27m\x1b[3;1Hz\x1b[Kq")
    assert s.lines() == ["hello", "  xyREV", "zq", ""], s.lines()
    assert s.reverse(1) == "REV", s.reverse(1)
    s.feed("\x1b[2J")
    assert s.before_clear == ["hello", "  xyREV", "zq", ""], s.before_clear
    # underline, both together, the style kept per cell, and the cursor state
    s.feed("\x1b[H\x1b[4mUL\x1b[24m\x1b[7mRV\x1b[4mBO\x1b[m..")
    assert s.underline(0) == "ULBO" and s.reverse(0) == "RVBO", (s.underline(0), s.reverse(0))
    assert s.attrs(0)[:8] == "uurrxxnn", s.attrs(0)[:8]
    assert s.cursor_visible
    s.feed("\x1b[?25l")
    assert not s.cursor_visible
    s.feed("\x1b[?25h")
    assert s.cursor_visible
    print("termscreen: self-test passed")

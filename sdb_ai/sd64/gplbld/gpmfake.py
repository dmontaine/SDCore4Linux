#!/usr/bin/env python3
"""gpmfake.py - a stand-in for the gpm daemon, for the tests of gplsrc/gpmmouse.c (sandbox-gpm.py).  No install, no sudo, no console.

  FakeGpm(path)       listens on a Unix stream socket at `path` (a directory of its own, mode 700) as /dev/gpmctl does
  .wait_client(t)     the first client's Gpm_Connect record as a dict, or None
  .event(...)         send one Gpm_Event record to the client (the 28-byte layout of gpm.h 1.20.7, checked against a live daemon on a Debian 13 console)
  .raw(bytes)         send bytes as they are (a short or odd record)
  .drop()             close the client's connection, as a daemon that is stopped does

START-HISTORY:
31 Oct 26 dm  New (S.94).  The layout was read from gpm.h and taken from a live daemon (.claude/vmtools/console-gpmprobe.py).
END-HISTORY
"""
import os
import socket
import struct
import threading
import time

CONNECT = struct.Struct("<HHHHii")                # eventMask defaultMask minMod maxMod pid vc                              (16 bytes)
EVENT = struct.Struct("<BBHhhhhiiihh")            # buttons modifiers vc | dx dy x y | type clicks margin | wdx wdy          (28 bytes)

# gpm.h
MOVE, DRAG, DOWN, UP, SINGLE, MFLAG = 1, 2, 4, 8, 16, 128
B_RIGHT, B_MIDDLE, B_LEFT = 1, 2, 4
MOD_SHIFT, MOD_ALTGR, MOD_CTRL, MOD_ALT = 1, 2, 4, 8


class FakeGpm:
    def __init__(self, path):
        self.path = path
        d = os.path.dirname(path)
        os.makedirs(d, mode=0o700, exist_ok=True)
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        self.srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.srv.bind(path)
        self.srv.listen(4)
        self.srv.settimeout(0.5)
        self.conn = None
        self.connect = None
        self.connections = 0
        self.stop = False
        self.t = threading.Thread(target=self._accept, daemon=True)
        self.t.start()

    def _accept(self):
        while not self.stop:
            try:
                c, _ = self.srv.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            data = b""
            c.settimeout(3.0)
            try:
                while len(data) < CONNECT.size:
                    more = c.recv(CONNECT.size - len(data))
                    if not more:
                        break
                    data += more
            except OSError:
                pass
            if len(data) == CONNECT.size:
                em, dm, mn, mx, pid, vc = CONNECT.unpack(data)
                self.connect = dict(eventMask=em, defaultMask=dm, minMod=mn, maxMod=mx, pid=pid, vc=vc)
                self.conn = c
                self.connections += 1
            else:
                c.close()

    def wait_client(self, secs=10.0):
        end = time.time() + secs
        while time.time() < end:
            if self.conn is not None:
                return self.connect
            time.sleep(0.05)
        return None

    def event(self, typ, x, y, buttons=0, mods=0, dx=0, dy=0, wdx=0, wdy=0, vc=1, clicks=0, margin=0):
        self.raw(EVENT.pack(buttons, mods, vc, dx, dy, x, y, typ, clicks, margin, wdx, wdy))

    def raw(self, data):
        self.conn.sendall(data)

    def closed_by_client(self, secs=3.0):
        """True when the client has closed its end (a read gives end of file)"""
        if self.conn is None:
            return False
        end = time.time() + secs
        self.conn.settimeout(0.2)
        while time.time() < end:
            try:
                if self.conn.recv(64) == b"":
                    return True
            except socket.timeout:
                continue
            except OSError:
                return True
        return False

    def drop(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except OSError:
                pass
            self.conn = None

    def close(self):
        self.stop = True
        self.drop()
        try:
            self.srv.close()
        except OSError:
            pass
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

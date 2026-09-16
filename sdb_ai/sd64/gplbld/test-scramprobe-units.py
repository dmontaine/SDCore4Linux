#!/usr/bin/env python3
"""test-scramprobe-units.py - free check over gplbld/scram-probe.py.

Adopted 15 Sep 2026 from the Windows port's test of the same name (its
RELEASE_1.1 42), under the owner's rule that Linux follows the Windows port's
decisions; its open/write rows are left out, because this probe has no
--open/--write.

  python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/test-scramprobe-units.py

No sudo, no install, no sd.  scram-probe.py drives the server's TLS+SCRAM login
directly, and its own SCRAM arithmetic has to be right, or a real red would be
blamed on the server.  This checks the parts that need no server:

  1. RFC 7677 section 3 vector: scram_compute() produces exactly the published
     ClientProof and server signature.
  2. libssl loads, and every OpenSSL symbol the Tls class declares resolves
     against it (the ABI is right).
  3. the mode and precondition decisions: no password -> exit 2, commands
     without --account -> exit 2, --no-tls to a dead port is never a pass, two
     modes at once are refused before anything connects.
  4. the wire line's three answers.

Controls: a wrong password must change the proof (the vector is not vacuous), a
mutated c= must change it too, and the wire search must FIND a password that is
there.

Exit 0 all passed, 1 a check failed, 2 could not run (the probe is missing, or
fewer checks ran than expected - the null case, refused).
"""

import base64
import importlib.util
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "scram-probe.py")

checks = 0
fails = 0


def check(cond, msg):
    global checks, fails
    checks += 1
    if cond:
        print("  [PASS] " + msg)
    else:
        fails += 1
        print("  [FAIL] " + msg)


def load_probe():
    spec = importlib.util.spec_from_file_location("scram_probe", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rfc7677_vector(mod):
    # RFC 7677 section 3: user "user", password "pencil".
    cnonce = "rOprNGfwEbeRWgbNEkqO"
    nonce = "rOprNGfwEbeRWgbNEkqO%hvYDpWUa2RaTCAfuxFIlj)hNlF$k0"
    salt = base64.b64decode("W22ZaJ0SNY7soEsUEjb6gQ==")
    iterations = 4096
    cfirst_bare = "n=user,r=" + cnonce
    sfirst = "r=%s,s=W22ZaJ0SNY7soEsUEjb6gQ==,i=4096" % nonce
    cfinal_bare = "c=biws,r=" + nonce
    want_proof = "dHzbZapWIk4jUhN+Ute9ytag9zjfMHgsqmmiz7AndVQ="
    want_v = "v=6rriTRBi23WpRR/wtup+mMhUZUn/dB5nLTJRsjl95G4="

    proof, expected_v = mod.scram_compute("pencil", salt, iterations,
                                          cfirst_bare, sfirst, cfinal_bare)
    proof_b64 = base64.b64encode(proof).decode("ascii")
    check(proof_b64 == want_proof, "RFC 7677 ClientProof (got %s)" % proof_b64)
    check(expected_v == want_v, "RFC 7677 server signature (got %s)" % expected_v)

    wrong, _ = mod.scram_compute("Pencil", salt, iterations, cfirst_bare,
                                 sfirst, cfinal_bare)
    check(base64.b64encode(wrong).decode("ascii") != want_proof,
          "control: a wrong password changes the proof")
    mutated, _ = mod.scram_compute("pencil", salt, iterations, cfirst_bare,
                                   sfirst, "c=bi7s,r=" + nonce)
    check(mutated != proof, "control: a mutated c= changes the proof")


def test_libssl(mod):
    try:
        name, lib = mod.Tls._load()
    except Exception as e:  # reported through the row, not a traceback
        check(False, "libssl could not be loaded: %s" % e)
        return
    check(lib is not None, "libssl loaded: %s" % name)
    symbols = ["TLS_client_method", "SSL_CTX_new", "SSL_CTX_ctrl",
               "SSL_CTX_set_verify", "SSL_new", "SSL_set_fd", "SSL_connect",
               "SSL_get_error", "SSL_read", "SSL_write", "SSL_get_version",
               "SSL_export_keying_material", "SSL_shutdown", "SSL_free",
               "SSL_CTX_free"]
    missing = [s for s in symbols if not hasattr(lib, s)]
    check(not missing, "all %d OpenSSL symbols resolve%s"
          % (len(symbols), "" if not missing else " (missing %s)" % missing))


def run_probe(args, env_extra=None):
    env = dict(os.environ)
    env.pop("SD_SCRAM_PASSWORD", None)
    if env_extra:
        env.update(env_extra)
    cmd = [sys.executable, PROBE] + args
    print("    > %s" % " ".join(cmd[1:]))
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
    return p.returncode, p.stdout + p.stderr


def test_modes():
    rc, out = run_probe(["--user", "x"])
    check(rc == 2 and "SD_SCRAM_PASSWORD is not set" in out,
          "no password -> exit 2 (got %d)" % rc)
    rc, out = run_probe(["--user", "x", "WHO"], {"SD_SCRAM_PASSWORD": "p"})
    check(rc == 2 and "commands need --account" in out,
          "commands without --account -> exit 2 (got %d)" % rc)
    # --no-tls to a port nothing listens on: cannot connect (2) or no ACK (1),
    # never the ACK and never a pass.
    rc, out = run_probe(["--user", "x", "--no-tls", "--port", "4"],
                        {"SD_SCRAM_PASSWORD": "p"})
    check(rc in (1, 2) and "PLAINTEXT: ACK RECEIVED" not in out,
          "--no-tls to a dead port is not a pass (got %d)" % rc)
    # Two modes at once: argparse refuses before connecting.  A probe that
    # silently picked one would report the wrong refusal.
    rc, out = run_probe(["--user", "x", "--replay", "--legacy"],
                        {"SD_SCRAM_PASSWORD": "p"})
    check(rc == 2 and "not allowed with" in out,
          "two modes at once -> exit 2 (got %d)" % rc)


def test_wire(mod):
    check(mod.wire_verdict(bytearray(), "secret").endswith("NOT CHECKED - nothing was sent"),
          "wire: nothing sent is NOT CHECKED, never 'absent' (the null case)")
    scram_like = bytearray(b"p=tls-exporter,,n=zz,r=abc")
    check("absent from the 26 plaintext" in mod.wire_verdict(scram_like, "secret"),
          "wire: SCRAM bytes -> password absent")
    legacy = bytearray(struct.pack("<h", 6) + b"secret")
    check("FOUND IN" in mod.wire_verdict(legacy, "secret"),
          "control: the wire search FINDS a password that is there")


def main():
    print("test-scramprobe-units")
    print("  probe    : %s" % PROBE)
    print("  python   : %s" % sys.executable)
    if not os.path.exists(PROBE):
        print("REFUSING - scram-probe.py not found at %s" % PROBE)
        return 2
    mod = load_probe()
    test_rfc7677_vector(mod)
    test_libssl(mod)
    test_modes()
    test_wire(mod)
    print("\ntest-scramprobe-units: %d checks, %d passed, %d failed"
          % (checks, checks - fails, fails))
    # The null case: vector 4, libssl 2, modes 4, wire 3.
    if checks < 13:
        print("REFUSING - fewer checks ran than expected (%d of 13)" % checks)
        return 2
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

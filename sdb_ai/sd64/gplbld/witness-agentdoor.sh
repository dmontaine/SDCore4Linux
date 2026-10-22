#!/bin/bash
#
# witness-agentdoor.sh - the agent arm of the ssh block under a REAL sshd (AI integration slice 1, S.69, the owner's D5 of 21 Oct 2026).
#
#   sudo bash /var/tmp/witness-agentdoor.sh /var/tmp/ssh-forcecommand.sh
#
# Run as root on a Linux machine with OpenSSH (the Debian 13 clone VM, and Fedora).  It needs NO SD install: it writes the block with the generator under test
# into a SCRATCH sshd_config, starts a PRIVATE sshd on 127.0.0.1:2299 with its own host key, and makes five throw-away users.  The machine's own sshd, its
# sshd_config and any SD install are not touched.  It removes everything it made, and says what it removed.
#
# WHAT IT ASKS sshd, never our own string: for each kind of user, `sshd -T -C user=...` (the effective forcecommand and allowtcpforwarding the REAL sshd
# derives from the groups the user is really in), and then a REAL ssh login whose command is `echo SHOULD-NOT-RUN` (it must not run: the forced command's
# stub prints what it was given in SSH_ORIGINAL_COMMAND and nothing else).
#
#   agentw  in sdagent                      -> the agent door, no forwarding
#   mixw    in sdagent AND sdusers AND sdssh -> the agent door (the arm is first)
#   plainw  in sdusers and sdssh            -> sd
#   norw    in sdusers only                  -> the refusal
#   nonw    in none of them                  -> no forced command at all
#
# INSTRUMENT RULES: it prints the sshd version, the config, every command it runs and what sshd said; a row passes only on the wording of the positive outcome
# and a refusal path is checked for its own wording too; it stops (exit 2) if sshd cannot be found, if the private sshd does not come up, or if sshd -T prints
# nothing for a user (a probe that asked nothing must not pass).  Exit 0 all rows passed, 1 a row failed, 2 it could not run.
set -u

GEN=${1:-}
[ -n "$GEN" ] && [ -f "$GEN" ] || { echo "witness-agentdoor: usage: $0 PATH-TO-ssh-forcecommand.sh" >&2; exit 2; }
[ "$(id -u)" = 0 ] || { echo "witness-agentdoor: CANNOT RUN - needs root (it makes users and starts an sshd)" >&2; exit 2; }
SSHD=$(command -v sshd || ls /usr/sbin/sshd 2>/dev/null)
[ -n "$SSHD" ] && [ -x "$SSHD" ] || { echo "witness-agentdoor: CANNOT RUN - no sshd found" >&2; exit 2; }
command -v ssh >/dev/null && command -v ssh-keygen >/dev/null || { echo "witness-agentdoor: CANNOT RUN - no ssh client" >&2; exit 2; }

W=/var/tmp/agentdoor-w
PORT=2299
PASSED=0
FAILED=0
MADE_GROUPS=""
MADE_USERS=""
pass() { PASSED=$((PASSED + 1)); echo "  [PASS] $1"; }
fail() { FAILED=$((FAILED + 1)); echo "  [FAIL] $1${2:+   <- $2}"; }

cleanup() {
  echo "--- cleanup"
  [ -f "$W/sshd.pid" ] && kill "$(cat "$W/sshd.pid")" 2>/dev/null && echo "stopped the private sshd"
  for u in $MADE_USERS; do userdel -r "$u" >/dev/null 2>&1 && echo "removed user $u"; done
  for g in $MADE_GROUPS; do groupdel "$g" >/dev/null 2>&1 && echo "removed group $g"; done
  rm -rf "$W" && echo "removed $W"
}
trap cleanup EXIT

echo "witness-agentdoor: $($SSHD -V 2>&1 | head -1)  sshd=$SSHD  generator=$GEN"
rm -rf "$W"; mkdir -p "$W"; chmod 755 "$W"

# groups: sdusers, sdssh, sdagent (made only if missing, removed only if made here)
for g in sdusers sdssh sdagent; do
  if getent group "$g" >/dev/null; then echo "group $g exists (left alone)"; else groupadd --system "$g" && MADE_GROUPS="$MADE_GROUPS $g" && echo "made group $g"; fi
done
mkuser() { # name groups...
  local n=$1; shift
  useradd -m -s /bin/bash -p '*' "$n" && MADE_USERS="$MADE_USERS $n"
  for g in "$@"; do usermod -aG "$g" "$n"; done
  echo "made user $n ($(id -nG "$n"))"
}
mkuser agentw sdagent
mkuser mixw sdagent sdusers sdssh
mkuser plainw sdusers sdssh
mkuser norw sdusers
mkuser nonw

# the stubs the arms point at
cat > "$W/sd-stub" <<'EOF'
#!/bin/bash
echo "SD-STUB user=$(id -un)"
EOF
cat > "$W/sd-mcp-stub" <<'EOF'
#!/bin/bash
echo "AGENT-DOOR user=$(id -un) orig=${SSH_ORIGINAL_COMMAND:-}"
EOF
chmod 755 "$W/sd-stub" "$W/sd-mcp-stub"
cp "$GEN" "$W/ssh-forcecommand" && chmod 755 "$W/ssh-forcecommand"
MSGS=$W/messages; mkdir -p "$MSGS"; echo "ssh refused for %1: no SD ssh route (witness stand-in for message 10074)" > "$MSGS/10074"

ssh-keygen -q -t ed25519 -N '' -f "$W/hostkey"
ssh-keygen -q -t ed25519 -N '' -f "$W/clientkey"
for u in agentw mixw plainw norw nonw; do
  h=$(getent passwd "$u" | cut -d: -f6)
  install -d -m 700 -o "$u" -g "$u" "$h/.ssh"
  install -m 600 -o "$u" -g "$u" "$W/clientkey.pub" "$h/.ssh/authorized_keys"
done

CFG=$W/sshd_config
cat > "$CFG" <<EOF
Port $PORT
ListenAddress 127.0.0.1
HostKey $W/hostkey
PidFile $W/sshd.pid
UsePAM no
PasswordAuthentication no
PubkeyAuthentication yes
StrictModes no
AuthorizedKeysFile %h/.ssh/authorized_keys
LogLevel ERROR
EOF
echo "--- writing the block with the generator under test"
SD_SSHD_CONFIG=$CFG SD_SSHD_BIN=$SSHD SD_SSH_FORCECOMMAND=$W/sd-stub SD_SSH_REFUSE_BIN=$W/ssh-forcecommand SD_SSH_MCP_BIN=$W/sd-mcp-stub SD_MESSAGE_DIR=$MSGS \
  bash "$GEN" --install > "$W/install.out" 2>&1
RC=$?
tail -4 "$W/install.out"
if [ $RC -eq 0 ] && grep -q 'Match Group sdagent,!sdsys' "$CFG"; then pass "the generator wrote the block with the agent arm into the scratch sshd_config"; else fail "the generator did not write the agent arm" "exit $RC"; exit 2; fi
echo "--- the block as written:"; sed -n '/BEGIN SD/,/END SD/p' "$CFG" | sed 's/^/    /'

echo "--- what the REAL sshd derives (sshd -T -C), per user"
eff() { # user key -> value
  "$SSHD" -T -f "$CFG" -C "user=$1,host=localhost,addr=127.0.0.1" 2>"$W/T.err" | awk -v k="$2" '$1 == k { $1 = ""; sub(/^ /, ""); print; exit }'
}
chk() { # user key expected description
  local got; got=$(eff "$1" "$2")
  if [ -z "$(eff "$1" port)" ]; then echo "witness-agentdoor: CANNOT RUN - sshd -T printed nothing for $1: $(cat "$W/T.err")" >&2; exit 2; fi
  if [ "$got" = "$3" ]; then pass "$4"; else fail "$4" "got '$got', wanted '$3'"; fi
}
chk agentw forcecommand "$W/sd-mcp-stub" "agentw (sdagent): sshd's forcecommand is the agent door"
chk agentw allowtcpforwarding "no" "agentw: tcp forwarding is no"
chk agentw allowagentforwarding "no" "agentw: agent forwarding is no"
chk agentw permittunnel "no" "agentw: tunnels are no"
chk agentw allowstreamlocalforwarding "no" "agentw: stream-local forwarding is no"
chk mixw forcecommand "$W/sd-mcp-stub" "mixw (sdagent AND sdusers AND sdssh): the agent door wins, not sd (the arm is first)"
chk plainw forcecommand "$W/sd-stub" "plainw (sdusers, sdssh): still forced into sd"
chk norw forcecommand "$W/ssh-forcecommand --refuse" "norw (sdusers, no sdssh): still the refusal"
chk nonw forcecommand "none" "nonw (in no SD group): no forced command, as before"

echo "--- real logins (the command is 'echo SHOULD-NOT-RUN'; a forced command must never run it)"
"$SSHD" -f "$CFG" || { echo "witness-agentdoor: CANNOT RUN - the private sshd did not start" >&2; exit 2; }
sleep 1
[ -f "$W/sshd.pid" ] || { echo "witness-agentdoor: CANNOT RUN - no pid file, the private sshd is not up" >&2; exit 2; }
login() { ssh -p $PORT -i "$W/clientkey" -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes -o ConnectTimeout=10 -o LogLevel=ERROR "$1@127.0.0.1" 'echo SHOULD-NOT-RUN' 2>&1; }
out=$(login agentw); echo "    agentw -> $out"
if [ "$out" = "AGENT-DOOR user=agentw orig=echo SHOULD-NOT-RUN" ]; then pass "agentw reaches the agent door, and the command it typed arrived only in SSH_ORIGINAL_COMMAND"; else fail "agentw login" "$out"; fi
out=$(login mixw); echo "    mixw -> $out"
if [ "$out" = "AGENT-DOOR user=mixw orig=echo SHOULD-NOT-RUN" ]; then pass "mixw (also an SD user) reaches the agent door, not sd"; else fail "mixw login" "$out"; fi
out=$(login plainw); echo "    plainw -> $out"
if [ "$out" = "SD-STUB user=plainw" ]; then pass "plainw reaches sd as before, and its command did not run"; else fail "plainw login" "$out"; fi
out=$(login norw); rc=$?; echo "    norw -> $out   (ssh exit $rc)"
# the refusal runs under sshd without this script's environment, so it prints the installed message 10074 when there is one and its own fallback line when not:
# the row judges the OUTCOME - the user is named, neither door is reached, the command did not run, and ssh failed.
if [ "$rc" -ne 0 ] && echo "$out" | grep -q 'norw' && ! echo "$out" | grep -qE 'SD-STUB|AGENT-DOOR|^SHOULD-NOT-RUN$'; then pass "norw is refused, naming the user, reaches neither door, and ssh fails"; else fail "norw login" "exit $rc: $out"; fi
out=$(login nonw); echo "    nonw -> $out"
if [ "$out" = "SHOULD-NOT-RUN" ]; then pass "nonw (no SD group) runs its own command, as before: the block does not touch other users"; else fail "nonw login" "$out"; fi

echo
echo "witness-agentdoor: $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ]

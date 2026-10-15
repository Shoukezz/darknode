"""Reference solutions — proof every mission is solvable inside its CPU budget.

These live ONLY in the test suite, never in the shipped game. The game shows
three-level hints but never a full solution.
"""

SOLUTIONS = {
    1: 'submit("ONLINE")\n',
    2: 'submit(7 * 13 + 5)\n',
    3: 'submit(f"OMNI-{42:04d}")\n',
    4: 'submit("GRANT" if 7 >= 5 and not False else "DENY")\n',
    5: """
total = 0
for n in range(1, 101):
    if n % 2 == 0:
        total += n
submit(total)
""",
    6: """
open_ports = []
for line in cat("scan.txt").splitlines():
    parts = line.split()
    if parts[2] == "open":
        open_ports.append(int(parts[1]))
submit(sorted(open_ports))
""",
    7: """
scan(); connect("relay"); scan()
for b in range(10):
    if 14 + 2 * b == 20:
        pin = f"7{b}{b}7"
        if crack("gw-01", pin):
            connect("gw-01")
            submit(cat("operator.txt"))
""",
    8: """
counts = {}
for line in cat("events.log").splitlines():
    name = line.split()[0].split("=")[1]
    counts[name] = counts.get(name, 0) + 1
submit(max(counts, key=counts.get))
""",
    9: """
a = set(cat("sensor-a.txt").split())
b = set(cat("sensor-b.txt").split())
submit(sorted(a & b))
""",
    10: """
def valid(badge):
    return sum(int(c) for c in badge) % 7 == 0
count = 0
for badge in cat("badges.txt").splitlines():
    if valid(badge):
        count += 1
submit(count)
""",
    11: """
record = cat("record.txt")
for field in record.split(";"):
    key, _, val = field.partition(":")
    if key.strip() == "NAME":
        submit(val.strip())
""",
    12: 'submit(cat("cipher0.txt")[::-1])\n',
    13: """
a, b = 1, 1
for _ in range(18):
    a, b = b, a + b
submit(b)
""",
    14: """
nums = [int(x) for x in cat("nums.txt").split()]
submit(sorted(n * n for n in nums if n % 2 == 1))
""",
    15: """
rows = []
for line in cat("targets.txt").splitlines():
    name, score = line.split()
    rows.append((name, int(score)))
rows.sort(key=lambda r: (-r[1], r[0]))
submit([name for name, _ in rows])
""",
    16: """
target = 61803 * 2 + 7
lo, hi = 0, size() - 1
while lo <= hi:
    mid = (lo + hi) // 2
    v = at(mid)
    if v == target:
        submit(mid)
        break
    elif v < target:
        lo = mid + 1
    else:
        hi = mid - 1
""",
    17: """
seen = {"home"}
queue = ["home"]
while queue:
    host = queue.pop(0)
    for nxt in scan(host):
        if nxt not in seen:
            seen.add(nxt)
            queue.append(nxt)
submit(sorted(seen))
""",
    18: """
def dfs(host, path):
    if host == "vault":
        return path
    for nxt in scan(host):
        if nxt not in path:
            found = dfs(nxt, path + [nxt])
            if found:
                return found
    return None
submit(dfs("home", ["home"]))
""",
    19: """
import heapq
best = {"home": 0}
pq = [(0, "home")]
while pq:
    cost, host = heapq.heappop(pq)
    if cost > best.get(host, 1e9):
        continue
    for nxt, w in links(host):
        if cost + w < best.get(nxt, 1e9):
            best[nxt] = cost + w
            heapq.heappush(pq, (cost + w, nxt))
submit(best["core"])
""",
    20: """
scan()
connect("archive")
msg = cat("msg.enc")
for shift in range(26):
    text = "".join(
        chr((ord(c) - 65 - shift) % 26 + 65) if "A" <= c <= "Z" else c
        for c in msg
    )
    if text.startswith("OMNIGRID"):
        submit(text)
        break
""",
    21: """
scan()
connect("archive")
key = cat("key.txt").split()[-1]
msg = cat("msg.vig")
out = []
j = 0
for c in msg:
    if "A" <= c <= "Z":
        k = ord(key[j % len(key)]) - 65
        out.append(chr((ord(c) - 65 - k) % 26 + 65))
        j += 1
    else:
        out.append(c)
submit("".join(out))
""",
    22: """
import base64
scan()
connect("relay")
key = cat("key.txt").split()[-1].encode()
raw = base64.b64decode(cat("msg.b64"))
out = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
submit(out.decode())
""",
    23: """
import base64
def h(s):
    v = 0
    for c in s:
        v = (v * 31 + ord(c)) % 100003
    return v
target = int(cat("shadow.txt").split(":")[1])
words = base64.b64decode(cat("wordlist.b64")).decode().split()
for w in words:
    if h(w) == target:
        submit(w)
        break
""",
    24: """
counts = {}
for line in cat("access.log").splitlines():
    ip, method, path, status = line.split()
    if status == "403":
        counts[ip] = counts.get(ip, 0) + 1
submit(max(counts, key=counts.get))
""",
    25: """
import itertools
scan()
connect("junction")
scan()
for combo in itertools.combinations(range(1, 10), 5):
    if sum(combo) == 17:
        pin = "".join(str(d) for d in combo)
        if crack("mainframe", pin):
            break
connect("mainframe")
key = cat("key.txt").split()[-1]
msg = cat("payload.vig")
out = []
j = 0
for c in msg:
    if "A" <= c <= "Z":
        k = ord(key[j % len(key)]) - 65
        out.append(chr((ord(c) - 65 - k) % 26 + 65))
        j += 1
    else:
        out.append(c)
submit("".join(out))
""",
}

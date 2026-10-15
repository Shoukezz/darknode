# DarkNode

A hacking-simulator game where you write **Python scripts** to breach a fictional network.

You sit at a terminal on the host `home`. Each mission drops you into a made-up network of
hosts, locked gateways and encrypted files. You can't click your way through: you write a
Python script that scans, cracks and decrypts, and the game runs it under a limited CPU
budget. Clumsy code runs out of cycles; clever code gets in.

> Everything in DarkNode is fictional. The "network" is a graph inside the game, and no real
> systems are touched.

```
darknode> run 1
['relay-a', 'relay-b']
-- cycles used: 88/5000
ACCESS GRANTED: network mapped: 10 hosts
```

## Quick start

Requires Python 3.10+. No dependencies.

```bash
git clone https://github.com/Shoukezz/darknode.git
cd darknode
python -m darknode
```

Or install it as a command:

```bash
pip install -e .
darknode
```

## How to play

```
darknode> missions        # list missions
darknode> brief 1         # read the briefing
darknode> new 1           # create scripts/mission1.py from a template
                          # ...edit the script in your editor...
darknode> run 1           # run it against the mission
```

Inside your script you can call:

| Function | What it does |
|---|---|
| `whoami()` | current host |
| `scan(host=None)` | hosts linked to `host` (default: current host) |
| `connect(host)` | move to an unlocked host you've discovered |
| `hint(host)` | password hint of a locked host |
| `crack(host, password)` | `True` if the password is right; unlocks the host |
| `ls()` / `cat(name)` | list and read files on the current host |
| `submit(answer)` | send your answer |

Allowed imports: `math`, `string`, `itertools`, `collections`, `functools`, `heapq`, `base64`.

## Missions

| # | Mission | What you practice |
|---|---|---|
| 1 | First Contact | graph traversal (BFS/DFS), lists, loops |
| 2 | Weak PIN | turning hints into a search space, avoiding brute force |
| 3 | Intercepted | string processing, the Caesar cipher |

## How it works

```
darknode/
  network.py   # the fictional network: nodes, links, locked hosts
  game.py      # GameSession: the API player scripts call
  sandbox.py   # runs player code with limited builtins and a CPU-cycle budget
  missions.py  # mission networks, briefings and answer checks
  runner.py    # plays a script against a mission
  terminal.py  # the interactive shell
```

The sandbox compiles the player's script, runs it with a reduced set of builtins and an
import allow-list, and counts every executed line through `sys.settrace`. When the count
passes the mission's budget, the run stops with "out of CPU cycles".

The sandbox is a **game mechanic, not a security boundary**: it keeps honest scripts inside
the game rules but is not meant to contain hostile code.

## Tests

```bash
python -m unittest
```

The test suite includes a reference solution for every mission, which proves each one is
solvable within its CPU budget.

## Roadmap

- [x] Core engine, sandbox, 3 missions, terminal
- [ ] More missions: password dictionaries, XOR, shortest paths, firewalls
- [ ] Save progress, credits and unlockable commands
- [ ] Full-screen terminal UI

## License

MIT

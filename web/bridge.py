"""Bridge between the browser page and the DarkNode engine (runs inside Pyodide)."""

import json

from darknode.game import API_HELP
from darknode.missions import MISSIONS, get_mission
from darknode.runner import play


def missions_json() -> str:
    return json.dumps({
        "api": API_HELP,
        "missions": [
            {
                "id": m.id,
                "title": m.title,
                "briefing": m.briefing,
                "template": m.template,
                "max_cycles": m.max_cycles,
            }
            for m in MISSIONS
        ],
    })


def _map(session) -> dict:
    net = session.network
    known = sorted(session.discovered)
    nodes = []
    for host in known:
        node = net.node(host)
        if node.password is None:
            state = "open"
        elif node.cracked:
            state = "cracked"
        else:
            state = "locked"
        nodes.append({"host": host, "state": state, "current": host == session.current})
    links = []
    for host in known:
        for nxt in net.neighbors(host):
            if nxt in session.discovered and host < nxt:
                links.append([host, nxt])
    return {"nodes": nodes, "links": links, "total": len(net.hosts())}


def run_json(mission_id: int, source: str) -> str:
    mission = get_mission(int(mission_id))
    result = play(mission, source, "mission.py")
    return json.dumps({
        "success": result.success,
        "message": result.message,
        "output": result.run.output,
        "cycles": result.run.cycles,
        "max_cycles": mission.max_cycles,
        "map": _map(result.session) if result.session else None,
    })

"""Bridge between the browser page and the DarkNode engine (runs inside Pyodide).

The page holds the save file as a JSON string and passes it in and out; all game
rules (credits, stars, shop, achievements, unlocks) live in the Python engine, so
the browser and terminal behave identically.
"""

import json

from darknode import i18n, progress
from darknode.content import ACT_ORDER, ACTS, unlocked_missions
from darknode.missions import MISSIONS, get_mission
from darknode.runner import play
from darknode.sandbox_gen import generate
from darknode.save import SaveData
from darknode.shop import SHOP, SHOP_ORDER


def _strings(lang: str) -> dict:
    """The whole UI string table plus the api help, for one language."""
    data = i18n.load(lang)
    return {
        "ui": data.get("ui", {}),
        "api_help": data.get("api_help", ""),
        "act": data.get("act", {}),
        "achievement": data.get("achievement", {}),
        "shop_items": data.get("shop_items", {}),
        "sandbox": data.get("sandbox", {}),
        "meta": data.get("meta", {}),
    }


def catalog(lang: str = "en") -> str:
    """Everything the page needs to render, in ``lang``."""
    missions = []
    for m in MISSIONS:
        missions.append({
            "id": m.id,
            "act": m.act,
            "concept": m.concept,
            "title": i18n.t(f"mission.{m.id}.title", lang),
            "briefing": i18n.t(f"mission.{m.id}.briefing", lang),
            "conceptHelp": i18n.t(f"mission.{m.id}.concept", lang),
            "hints": i18n.get(f"mission.{m.id}.hints", lang) or [],
            "template": i18n.t(f"mission.{m.id}.template", lang),
            "max_cycles": m.max_cycles,
            "reward": m.reward,
        })
    acts = [{"id": a,
             "name": i18n.t(f"act.{a}.name", lang),
             "blurb": i18n.t(f"act.{a}.blurb", lang),
             "missions": ACTS[a]} for a in ACT_ORDER]
    shop = [{"id": i, "cost": SHOP[i].cost,
             "name": i18n.t(f"shop_items.{i}.name", lang),
             "desc": i18n.t(f"shop_items.{i}.desc", lang)} for i in SHOP_ORDER]
    return json.dumps({
        "languages": [{"id": k, "name": v} for k, v in i18n.LANGUAGE_NAMES.items()],
        "missions": missions,
        "acts": acts,
        "shop": shop,
        "strings": _strings(lang),
    }, ensure_ascii=False)


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


def _result_payload(mission, result, lang) -> dict:
    return {
        "success": result.success,
        "message": i18n.t(result.message_key, lang, **result.params),
        "output": result.run.output,
        "cycles": result.run.cycles,
        "max_cycles": mission.max_cycles,
        "stars": result.stars,
        "cycle_bonus": result.cycle_bonus,
        "error_type": result.run.error_type,
        "map": _map(result.session) if result.session else None,
    }


def run_json(mission_id: int, source: str, save_json: str = "", lang: str = "en") -> str:
    data = SaveData.from_json(save_json) if save_json else SaveData()
    mission = get_mission(int(mission_id))
    result = play(mission, source, "mission.py", data.unlocked)
    payload = _result_payload(mission, result, lang)
    summary = progress.award(data, mission, result)
    payload["award"] = {
        "awarded": summary.get("awarded", 0),
        "bonus": summary.get("bonus", 0),
        "credits": summary.get("credits", data.credits),
        "new_achievements": summary.get("new_achievements", []),
    }
    payload["save"] = data.to_dict()
    payload["unlocked_missions"] = sorted(unlocked_missions({int(k) for k in data.completed}))
    payload["sandbox_unlocked"] = progress.sandbox_unlocked(data)
    return json.dumps(payload, ensure_ascii=False)


def sandbox_json(seed: int, source: str, save_json: str = "", lang: str = "en") -> str:
    data = SaveData.from_json(save_json) if save_json else SaveData()
    mission = generate(int(seed))
    result = play(mission, source, "sandbox.py", data.unlocked)
    payload = _result_payload(mission, result, lang)
    payload["save"] = data.to_dict()
    return json.dumps(payload, ensure_ascii=False)


def buy_json(item_id: str, save_json: str = "", lang: str = "en") -> str:
    data = SaveData.from_json(save_json) if save_json else SaveData()
    result = progress.buy(data, item_id)
    result["save"] = data.to_dict()
    return json.dumps(result, ensure_ascii=False)


def validate_save(save_json: str) -> str:
    """Return a cleaned save dict, or {"ok": false} if the text is not a save."""
    try:
        data = SaveData.from_json(save_json)
    except (ValueError, TypeError):
        return json.dumps({"ok": False})
    return json.dumps({"ok": True, "save": data.to_dict()}, ensure_ascii=False)

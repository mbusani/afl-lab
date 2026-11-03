"""Build one AFL season's match results from the Squiggle API (https://api.squiggle.com.au).

Usage: python3 data/build_afl_games.py afl 2026   (competition, season)
Writes games_<comp>_<year>.csv, games_<comp>_<year>.json and conversion_<comp>_<year>.json next to this file.
Data: Squiggle (Max Barry), https://squiggle.com.au. Standard library only."""
import csv, datetime, json, os, pathlib, sys, urllib.request

UA_BASE = "football-analytics-lab (https://github.com/mbusani/football-analytics-lab)"
KEYS = ["id", "year", "round", "roundname", "date", "venue", "home", "away",
        "home_goals", "home_behinds", "home_score", "home_shots",
        "away_goals", "away_behinds", "away_score", "away_shots", "is_final"]
OUT = pathlib.Path(__file__).parent


def user_agent(env=os.environ):
    contact = env.get("SQUIGGLE_CONTACT", "").strip()
    if "@" not in contact:
        raise SystemExit("Set SQUIGGLE_CONTACT to a contact email; Squiggle's API requires one in the User-Agent.")
    return f"{UA_BASE} - {contact}"


def fetch_games(year):
    req = urllib.request.Request(f"https://api.squiggle.com.au/?q=games;year={int(year)}",
                                 headers={"User-Agent": user_agent()})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["games"]


def to_rows(games):
    rows = []
    for g in games:
        if g.get("complete") != 100:
            continue
        for side in ("h", "a"):
            if g[f"{side}score"] != 6 * g[f"{side}goals"] + g[f"{side}behinds"]:
                raise ValueError(f"score mismatch in game {g['id']} ({side})")
        rows.append({
            "id": g["id"], "year": g["year"], "round": g["round"],
            "roundname": g.get("roundname") or f"Round {g['round']}",
            "date": g["date"], "venue": g["venue"], "home": g["hteam"], "away": g["ateam"],
            "home_goals": g["hgoals"], "home_behinds": g["hbehinds"], "home_score": g["hscore"],
            "home_shots": g["hgoals"] + g["hbehinds"],
            "away_goals": g["agoals"], "away_behinds": g["abehinds"], "away_score": g["ascore"],
            "away_shots": g["agoals"] + g["abehinds"], "is_final": g["is_final"],
        })
    return sorted(rows, key=lambda r: (r["date"], r["id"]))


def league_conversion(rows):
    teams = {}
    for r in rows:
        for side in ("home", "away"):
            t = teams.setdefault(r[side], {"goals": 0, "shots": 0})
            t["goals"] += r[f"{side}_goals"]; t["shots"] += r[f"{side}_shots"]
    for t in teams.values():
        t["p"] = round(t["goals"] / t["shots"], 4) if t["shots"] else None
    goals = sum(t["goals"] for t in teams.values())
    shots = sum(t["shots"] for t in teams.values())
    return {"year": rows[0]["year"] if rows else None, "goals": goals, "behinds": shots - goals,
            "shots": shots, "p": round(goals / shots, 4) if shots else None, "teams": dict(sorted(teams.items()))}


SOURCES = {"afl": fetch_games}  # aflw, alm, alw: added by follow-up plans after the Task 6 data spike


def main(comp, year):
    if comp not in SOURCES:
        raise SystemExit(f"unsupported competition {comp!r}; supported: {', '.join(SOURCES)}")
    rows = to_rows(SOURCES[comp](year))
    if not rows:
        raise SystemExit(f"no completed matches for {comp} {year}; nothing written")
    conversion = league_conversion(rows)  # compute before writing so a failure leaves no partial files
    with open(OUT / f"games_{comp}_{year}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=KEYS); w.writeheader(); w.writerows(rows)
    meta = {"source": "Squiggle API", "fetched": datetime.date.today().isoformat(), "rows": rows}
    (OUT / f"games_{comp}_{year}.json").write_text(json.dumps(meta, indent=1))
    (OUT / f"conversion_{comp}_{year}.json").write_text(json.dumps(conversion, indent=1))
    print(f"{len(rows)} completed matches written for {comp} {year}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "afl", int(sys.argv[2]) if len(sys.argv) > 2 else 2026)

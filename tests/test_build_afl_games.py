import importlib.util, pathlib, re, pytest

spec = importlib.util.spec_from_file_location(
    "build", pathlib.Path(__file__).parents[1] / "data" / "build_afl_games.py")
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)

def game(**kw):
    g = dict(id=1, year=2026, round=1, roundname="Round 1", date="2026-03-12 19:30:00",
             venue="Optus Stadium", hteam="West Coast", ateam="Fremantle",
             hgoals=12, hbehinds=10, hscore=82, agoals=14, abehinds=8, ascore=92,
             complete=100, is_final=0)
    g.update(kw); return g

def test_drops_incomplete_and_sorts_by_date():
    rows = build.to_rows([game(id=2, date="2026-03-20 19:30:00"), game(id=3, complete=60), game(id=1)])
    assert [r["id"] for r in rows] == [1, 2]

def test_shots_are_goals_plus_behinds():
    r = build.to_rows([game()])[0]
    assert (r["home_shots"], r["away_shots"]) == (22, 22)
    assert (r["home"], r["away"]) == ("West Coast", "Fremantle")

def test_score_mismatch_raises():
    with pytest.raises(ValueError):
        build.to_rows([game(hscore=83)])

def test_missing_roundname_falls_back():
    g = game(); del g["roundname"]
    assert build.to_rows([g])[0]["roundname"] == "Round 1"

def test_user_agent_needs_contact_email():
    with pytest.raises(SystemExit):
        build.user_agent({})
    assert build.user_agent({"SQUIGGLE_CONTACT": "a@b.co"}).endswith(" - a@b.co")

def test_committed_data_has_no_contact_details():
    data = pathlib.Path(__file__).parents[1] / "data"
    for f in data.glob("*.*"):
        if f.suffix in {".json", ".csv"}:
            text = f.read_text()
            assert "SQUIGGLE_CONTACT" not in text, f.name
            assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text), f"email-like text in {f.name}"

def test_league_conversion():
    rows = build.to_rows([game(), game(id=2, hgoals=10, hbehinds=10, hscore=70)])
    c = build.league_conversion(rows)
    assert c["goals"] == 12 + 14 + 10 + 14 and c["shots"] == 22 + 22 + 20 + 22
    assert c["p"] == round(50 / 86, 4)
    assert c["teams"]["West Coast"]["shots"] == 42

def test_league_conversion_empty_has_no_p():
    c = build.league_conversion([])
    assert c["p"] is None and c["shots"] == 0

def test_main_with_no_completed_games_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path)
    monkeypatch.setitem(build.SOURCES, "afl", lambda year: [])
    with pytest.raises(SystemExit):
        build.main("afl", 2026)
    assert list(tmp_path.iterdir()) == []

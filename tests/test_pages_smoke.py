"""Browser smoke tests for the site. Serves the repo locally and drives Chromium via Playwright.
The calculator tests always run; the season-table tests need data/deserved_afl_2026.json
(build it with `SQUIGGLE_CONTACT=<email> npm run build:afl`) and are skipped until it exists."""
import functools, http.server, pathlib, threading, pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parents[1]
DATA = ROOT / "data" / "deserved_afl_2026.json"
MODEL = "/models/deserved-to-win/"


@pytest.fixture(scope="module")
def base():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    handler.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 375, "height": 800})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.errors = errors
        yield pg
        b.close()


def test_calculator_numbers(base, page):
    page.goto(base + MODEL)
    page.fill("#p", "0.53")
    page.fill("#home-shots", "25")
    page.fill("#away-shots", "20")
    page.dispatch_event("#away-shots", "input")
    assert page.text_content("#home-prob").strip() == "82.7%"
    assert page.text_content("#draw-prob").strip() == "6.6%"
    assert page.text_content("#away-prob").strip() == "10.7%"
    assert page.text_content("#home-exp").strip() == "91.3"
    assert page.text_content("#away-exp").strip() == "73.0"
    assert page.errors == []


def test_stepper_buttons(base, page):
    page.goto(base + MODEL)
    page.fill("#home-shots", "22"); page.fill("#away-shots", "22"); page.dispatch_event("#away-shots", "input")
    page.click('button[data-step="home-shots"][data-d="1"]')
    assert page.input_value("#home-shots") == "23"
    page.click('button[data-step="away-shots"][data-d="-1"]')
    assert page.input_value("#away-shots") == "21"


def test_pages_fit_phone_width(base, page):
    for path in ("/", MODEL):
        page.goto(base + path)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), path


def test_waiting_message_without_data(base, page):
    if DATA.exists():
        pytest.skip("season data present")
    page.goto(base + MODEL)
    assert "npm run build:afl" in page.text_content("#upsets-box")


def test_season_tables(base, page):
    if not DATA.exists():
        pytest.skip("data/deserved_afl_2026.json not built yet: run SQUIGGLE_CONTACT=<email> npm run build:afl")
    page.goto(base + MODEL)
    page.wait_for_selector("#upsets tbody tr")
    assert page.locator("#upsets tbody tr").count() == 10
    assert page.locator("#ladder tbody tr").count() == 18
    assert page.locator("#calibration tbody tr").count() >= 1
    assert "Brier score" in page.text_content("#brier")
    assert "correlation" in page.text_content("#persistence")


def test_photos_load_with_alt_and_credit(base, page):
    for path, want in (("/", 2), (MODEL, 1)):
        page.goto(base + path)
        figs = page.locator("figure.photo")
        assert figs.count() == want, path
        for i in range(want):
            fig = figs.nth(i)
            img = fig.locator("img")
            img.scroll_into_view_if_needed()
            page.wait_for_function("el => el.complete && el.naturalWidth > 0", arg=img.element_handle())
            assert img.get_attribute("alt"), path
            assert "commons.wikimedia.org" in fig.locator("figcaption a").first.get_attribute("href"), path


def test_home_cards_and_map(base, page):
    page.goto(base + "/")
    assert page.locator("#stops .stop").count() == 3
    assert page.locator("#stops-dev .stop").count() == 3
    assert "In development" in page.text_content("#stops-dev")
    assert page.locator("#map a.map-node").count() == 6
    assert page.locator("#map a.map-node.dev").count() == 3
    assert page.locator("nav.top a.lnk").count() == 7
    assert page.errors == []


def test_home_ball_route_uses_live_sections_only(base, page):
    page.goto(base + "/")
    route = page.get_attribute("#map .map-pass", "d")
    live = page.evaluate("""() => [...document.querySelectorAll('#map a.map-node:not(.dev) circle')]
        .map(c => c.getAttribute('cx') + ' ' + c.getAttribute('cy'))""")
    assert len(live) == 3
    assert route == "M" + " L".join(live) + " Z"
    assert page.get_attribute("#map animateMotion", "path") == route


def test_home_has_no_night_styled_text_outside_hero(base, page):
    page.goto(base + "/")
    assert page.locator(".hero nav.top .brand").count() == 1
    assert page.locator(".hero .eyebrow").count() == 1
    assert page.locator(".hero .lede").count() == 1
    outside = ".brand, .eyebrow, .lede, nav.top"
    assert page.evaluate("s => [...document.querySelectorAll(s)].filter(e => !e.closest('.hero')).length", outside) == 0


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_home_focus_ring_is_lamp_on_night_surfaces(base, page, scheme):
    """Tabs to a real link in the hero, the SVG map and the footer, and reads the ring the browser would draw."""
    page.emulate_media(color_scheme=scheme)
    page.goto(base + "/")
    lamp = page.evaluate("""() => { const d = document.createElement('i'); d.style.color = getComputedStyle(document.documentElement).getPropertyValue('--lamp');
        document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; }""")
    seen = {}
    rings = []
    for _ in range(60):
        page.keyboard.press("Tab")
        ring = page.evaluate("""() => { const a = document.activeElement; if (!a.matches(':focus-visible')) return null;
            const area = a.closest('#map') ? 'map' : a.closest('.hero') ? 'hero' : a.closest('footer') ? 'footer' : null;
            const s = getComputedStyle(a); return area && {area, style: s.outlineStyle, colour: s.outlineColor, width: s.outlineWidth}; }""")
        if ring:
            seen[ring["area"]] = ring
            rings.append(ring)
    page.emulate_media(color_scheme="light")
    assert set(seen) == {"hero", "map", "footer"}
    for ring in rings:
        assert (ring["style"], ring["colour"], ring["width"]) == ("solid", lamp, "3px"), ring


def test_home_example_board_lines_up_with_the_page(base, page):
    """A <figure> has a default side margin, which would inset the board and squeeze it on a phone."""
    page.set_viewport_size({"width": 375, "height": 800})
    page.set_viewport_size({"width": 375, "height": 800})
    page.goto(base + "/")
    board = page.locator("#example figure.board").bounding_box()
    photo = page.locator("#example figure.photo").bounding_box()
    assert board["x"] == photo["x"]
    assert board["width"] == photo["width"]


def test_home_coming_next_label_clears_its_cards(base, page):
    page.goto(base + "/")
    label = page.locator(".coming .label").bounding_box()
    cards = page.locator("#stops-dev").bounding_box()
    assert cards["y"] - (label["y"] + label["height"]) >= 8


def test_home_ball_sits_still_with_reduced_motion(base, page):
    page.emulate_media(reduced_motion="reduce")
    try:
        page.goto(base + "/")
        page.wait_for_selector("#map .map-ball")
        assert page.locator("#map animateMotion").count() == 0
    finally:
        page.emulate_media(reduced_motion="no-preference")
    page.goto(base + "/")
    assert page.locator("#map animateMotion").count() == 1


def test_night_surface_links_stay_lamp_or_chalk_on_hover_in_light_mode(base, page):
    """a:hover would otherwise turn night-surface links the dark-amber accent (about 2.7:1 on night)."""
    page.emulate_media(color_scheme="light")
    page.goto(base + "/")
    lamp = page.evaluate("""() => { const d = document.createElement('i'); d.style.color = getComputedStyle(document.documentElement).getPropertyValue('--lamp');
        document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; }""")
    def colour(sel):
        return page.evaluate("s => getComputedStyle(document.querySelector(s)).color", sel)
    try:
        for sel in ("footer a", "nav.top a.brand"):
            page.hover(sel)
            assert colour(sel) == lamp, sel
        page.hover("footer a")
        assert page.evaluate("s => getComputedStyle(document.querySelector(s)).textDecorationColor", "footer a") == lamp
    finally:
        page.mouse.move(0, 0)

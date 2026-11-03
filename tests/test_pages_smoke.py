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
            assert "commons.wikimedia.org" in fig.locator("figcaption a").get_attribute("href"), path

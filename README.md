# AFL Lab

Australian football explained with models you can try, check and validate with. By Mark Busani, Perth.

## What's here

| Path | What it is |
|---|---|
| `index.html` | Landing page |
| `models/deserved-to-win/` | Model 01: "Did they deserve to win?" (scoring-shots calculator, 2026 season analysis, report card) |
| `assets/scoring-shots.js` | The model: pure functions shared by the page and the season build |
| `assets/site.css` | Site styles |
| `data/build_afl_games.py` | Builds a season's match results from the [Squiggle API](https://api.squiggle.com.au) |
| `scripts/build-deserved.mjs` | Runs the model over the season and writes `data/deserved_afl_2026.json` |
| `tests/` | Node and pytest tests, including browser smoke tests |

## Build the 2026 data

Squiggle asks for a contact email in the User-Agent. It's read from an environment variable and never saved:

```bash
SQUIGGLE_CONTACT=you@example.com npm run build:afl
```

Then run the tests again before committing the files in `data/`.

## Test

```bash
npm test                          # model and season analysis (Node 22, no dependencies)
python3 -m pytest tests           # data build and browser smoke tests (needs pytest and playwright)
```

## View locally

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000.

## Credits

Match scores: Squiggle API by Max Barry. Code: MIT.

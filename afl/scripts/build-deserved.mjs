/* Runs the scoring-shots model over a season and writes afl/data/deserved_<comp>_<year>.json.
   Usage: node afl/scripts/build-deserved.mjs [comp] [year]   (default: afl 2026) */
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { winProbability, matchLuck } from "../assets/scoring-shots.js";

const r4 = (x) => Math.round(x * 1e4) / 1e4;

const r4n = (x) => (x === null || x === undefined ? x : r4(x));

/* Rounds the report numbers to 4 dp for writing; null stays null. Exported functions stay full precision. */
export function roundOutput(out) {
  return {
    ...out,
    ladder: out.ladder.map((t) => ({ ...t, expected_wins: r4n(t.expected_wins), luck: r4n(t.luck), conversion: r4n(t.conversion) })),
    calibration: {
      ...out.calibration, brier: r4n(out.calibration.brier),
      bins: out.calibration.bins.map((b) => ({ ...b, fav_expected: r4n(b.fav_expected), fav_points: r4n(b.fav_points) })),
    },
    persistence: {
      ...out.persistence,
      teams: out.persistence.teams.map((t) => ({ ...t, first: r4n(t.first), second: r4n(t.second) })),
      correlation: r4n(out.persistence.correlation),
    },
  };
}

export function pearson(xs, ys) {
  const n = xs.length, mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) {
    sxy += (xs[i] - mx) * (ys[i] - my); sxx += (xs[i] - mx) ** 2; syy += (ys[i] - my) ** 2;
  }
  return sxx && syy ? sxy / Math.sqrt(sxx * syy) : null;
}

/* Does goalkicking accuracy carry over? Each team's conversion in rounds <= split vs after it
   (home-and-away only). A high correlation suggests skill; near zero suggests luck. */
export function conversionByHalf(rows, split = 12) {
  const t = new Map();
  const get = (name) => t.get(name) || t.set(name, { g1: 0, s1: 0, g2: 0, s2: 0 }).get(name);
  for (const r of rows) {
    if (r.is_final) continue;
    const k = r.round <= split ? 1 : 2;
    for (const side of ["home", "away"]) {
      const x = get(r[side]);
      x[`g${k}`] += r[`${side}_goals`]; x[`s${k}`] += r[`${side}_shots`];
    }
  }
  const teams = [...t].filter(([, x]) => x.s1 && x.s2)
    .map(([team, x]) => ({ team, first: x.g1 / x.s1, second: x.g2 / x.s2 }));
  return { split_round: split, teams, correlation: pearson(teams.map((x) => x.first), teams.map((x) => x.second)) };
}

export function calibration(matches) {
  const bins = [0.5, 0.6, 0.7, 0.8, 0.9].map((lo) => ({ lo, hi: r4(lo + 0.1), n: 0, fav_points: 0, fav_expected: 0 }));
  let sq = 0;
  for (const m of matches) {
    const e = m.home_win_prob + m.draw_prob / 2;
    const actual = m.home_score > m.away_score ? 1 : m.home_score === m.away_score ? 0.5 : 0;
    sq += (e - actual) ** 2;
    const homeFav = e >= 0.5, f = homeFav ? e : 1 - e;
    const b = bins[Math.min(4, Math.floor((f - 0.5) * 10 + 1e-9))];
    b.n++; b.fav_expected += f; b.fav_points += homeFav ? actual : 1 - actual;
  }
  return { brier: matches.length ? sq / matches.length : null, bins };
}

export function analyseSeason(rows, p) {
  const teams = new Map();
  const team = (name) => {
    if (!teams.has(name)) teams.set(name, { team: name, played: 0, wins: 0, expected_wins: 0, goals: 0, shots: 0 });
    return teams.get(name);
  };
  let right = 0, counted = 0;
  const matches = rows.map((r) => {
    const w = winProbability({ homeShots: r.home_shots, awayShots: r.away_shots, p });
    const luck = matchLuck({ homeShots: r.home_shots, awayShots: r.away_shots,
      homeScore: r.home_score, awayScore: r.away_score, p });
    const hWin = r.home_score > r.away_score ? 1 : r.home_score === r.away_score ? 0.5 : 0;
    const hExp = w.home + w.draw / 2;
    const h = team(r.home), a = team(r.away);
    h.played++; a.played++;
    h.wins += hWin; a.wins += 1 - hWin;
    h.expected_wins += hExp; a.expected_wins += 1 - hExp;
    h.goals += r.home_goals; h.shots += r.home_shots; a.goals += r.away_goals; a.shots += r.away_shots;
    if (hWin !== 0.5 && r.home_shots !== r.away_shots) {
      counted++;
      if ((hWin === 1) === (w.home > w.away)) right++;
    }
    return {
      id: r.id, round: r.round, roundname: r.roundname, date: r.date, venue: r.venue,
      home: r.home, away: r.away, home_shots: r.home_shots, away_shots: r.away_shots,
      home_score: r.home_score, away_score: r.away_score,
      home_win_prob: r4(w.home), draw_prob: r4(w.draw), away_win_prob: r4(w.away),
      home_expected: r4(w.homeExpected), away_expected: r4(w.awayExpected),
      winner_win_prob: hWin === 0.5 ? null : r4(hWin === 1 ? w.home : w.away),
      home_luck: r4(luck.home),
    };
  });
  const upsets = matches.filter((m) => m.winner_win_prob !== null)
    .sort((x, y) => x.winner_win_prob - y.winner_win_prob).slice(0, 10);
  const ladder = [...teams.values()]
    .map(({ goals, shots, ...t }) => ({ ...t, conversion: shots ? goals / shots : null, luck: t.wins - t.expected_wins }))
    .sort((x, y) => y.luck - x.luck);
  return {
    p, matches, upsets, ladder, calibration: calibration(matches), persistence: conversionByHalf(rows, 12),
    summary: { matches: counted, model_right: right,
      model_right_pct: counted ? r4(right / counted) : null },
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const comp = process.argv[2] || "afl";
  const year = process.argv[3] || "2026";
  const dataDir = join(dirname(fileURLToPath(import.meta.url)), "..", "data");
  const read = (name) => {
    const f = join(dataDir, `${name}_${comp}_${year}.json`);
    try { return JSON.parse(readFileSync(f, "utf8")); } catch (e) {
      if (e.code !== "ENOENT") throw e;
      console.error(`missing afl/data/${name}_${comp}_${year}.json: run SQUIGGLE_CONTACT=<email> npm run build:afl first`);
      process.exit(1);
    }
  };
  const games = read("games"), conv = read("conversion");
  const out = roundOutput(analyseSeason(games.rows, conv.p));
  out.source = games.source; out.fetched = games.fetched; out.comp = comp; out.year = Number(year);
  writeFileSync(join(dataDir, `deserved_${comp}_${year}.json`), JSON.stringify(out, null, 1));
  console.log(`${out.matches.length} matches; model right ${out.summary.model_right}/${out.summary.matches}`);
}

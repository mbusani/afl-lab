import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { analyseSeason, calibration, pearson, conversionByHalf, roundOutput } from "../scripts/build-deserved.mjs";

// goals follow from score = shots + 5 x goals
const row = (id, home, away, hs, as, hsc, asc, round = 1) => ({
  id, round, roundname: `Round ${round}`, date: `2026-03-1${id} 19:30:00`, venue: "V",
  home, away, home_shots: hs, away_shots: as, home_score: hsc, away_score: asc,
  home_goals: (hsc - hs) / 5, away_goals: (asc - as) / 5,
});
// A out-shoots B 30-15 but loses (an upset); C beats A as expected; B v C is a straight win for B on more shots
const rows = [
  row(1, "A", "B", 30, 15, 60, 65),
  row(2, "C", "A", 28, 20, 108, 70),
  row(3, "B", "C", 25, 18, 100, 78),
];

test("upsets are ordered by the winner's model chance, lowest first", () => {
  const s = analyseSeason(rows, 0.53);
  assert.equal(s.upsets[0].id, 1);
  assert.ok(s.upsets[0].winner_win_prob < s.upsets[1].winner_win_prob);
});

test("ladder luck is wins minus expected wins and sums to zero", () => {
  const s = analyseSeason(rows, 0.53);
  let total = 0;
  for (const t of s.ladder) {
    assert.ok(Math.abs(t.luck - (t.wins - t.expected_wins)) < 1e-9);
    total += t.luck;
  }
  assert.ok(Math.abs(total) < 1e-9);
  assert.equal(s.ladder[0].team, "B"); // won a game it was expected to lose
});

test("calibration bins favourites and computes the Brier score", () => {
  // m1: home expected 0.75 (favourite home, 0.75 -> bin 0.7), home won (actual 1)
  // m2: home expected 0.15 (favourite away, 0.85 -> bin 0.8), home won (an upset, actual 1)
  const c = calibration([
    { home_win_prob: 0.7, draw_prob: 0.1, away_win_prob: 0.2, home_score: 90, away_score: 80 },
    { home_win_prob: 0.1, draw_prob: 0.1, away_win_prob: 0.8, home_score: 90, away_score: 80 },
  ]);
  assert.ok(Math.abs(c.brier - ((0.75 - 1) ** 2 + (0.15 - 1) ** 2) / 2) < 1e-9);
  const b7 = c.bins.find((b) => b.lo === 0.7), b8 = c.bins.find((b) => b.lo === 0.8);
  assert.deepEqual([b7.n, b7.fav_points], [1, 1]);
  assert.deepEqual([b8.n, b8.fav_points], [1, 0]);
  assert.equal(c.bins.reduce((n, b) => n + b.n, 0), 2);
});

test("ladder carries each team's own conversion rate", () => {
  const s = analyseSeason(rows, 0.53);
  const a = s.ladder.find((t) => t.team === "A");
  assert.equal(a.conversion, (6 + 10) / (30 + 20)); // A: 6 goals from 30, then 10 from 20
});

test("pearson correlation", () => {
  assert.ok(Math.abs(pearson([1, 2, 3], [2, 4, 6]) - 1) < 1e-12);
  assert.ok(Math.abs(pearson([1, 2, 3], [3, 2, 1]) + 1) < 1e-12);
  assert.equal(pearson([1, 1, 1], [1, 2, 3]), null); // no variation
});

test("conversionByHalf splits at the round and skips finals", () => {
  const r = [
    row(1, "X", "Y", 10, 10, 30, 35, 1),   // X 4/10, Y 5/10
    row(2, "X", "Y", 20, 20, 65, 75, 13),  // X 9/20, Y 11/20
    { ...row(3, "X", "Y", 10, 10, 60, 10, 25), is_final: 1 },
  ];
  const h = conversionByHalf(r, 12);
  const x = h.teams.find((t) => t.team === "X");
  assert.deepEqual([x.first, x.second], [0.4, 0.45]);
  assert.equal(h.split_round, 12);
  assert.ok(Math.abs(h.correlation - 1) < 1e-12);
});

test("summary counts how often the side with more expected wins won", () => {
  const s = analyseSeason(rows, 0.53);
  assert.equal(s.summary.matches, 3);
  assert.equal(s.summary.model_right, 2);
});

test("equal-shot, non-drawn matches are exact 50/50s and are excluded from the summary", () => {
  const withTie = [...rows, row(4, "A", "B", 22, 22, 100, 90)];
  const s = analyseSeason(withTie, 0.53);
  assert.equal(s.summary.matches, 3);
  assert.equal(s.summary.model_right, 2);
});

test("conversionByHalf puts round 12 in the first half and round 13 in the second", () => {
  const r = [
    row(1, "X", "Y", 10, 10, 30, 35, 12),  // first half: X 4/10, Y 5/10
    row(2, "X", "Y", 20, 20, 65, 75, 13),  // second half: X 9/20, Y 11/20
  ];
  const x = conversionByHalf(r, 12).teams.find((t) => t.team === "X");
  assert.deepEqual([x.first, x.second], [0.4, 0.45]);
});

test("roundOutput rounds to 4 dp and keeps null as null", () => {
  const o = roundOutput({
    calibration: { brier: 0.123456789, bins: [{ lo: 0.5, n: 2, fav_expected: 1.23456789, fav_points: 1.00004 }] },
    persistence: { split_round: 12, teams: [{ team: "X", first: 0.123456, second: 2 / 3 }], correlation: null },
    ladder: [{ team: "X", expected_wins: 1.23456789, luck: -0.00004, conversion: null }],
  });
  assert.equal(o.calibration.brier, 0.1235);
  assert.deepEqual([o.calibration.bins[0].fav_expected, o.calibration.bins[0].fav_points], [1.2346, 1]);
  assert.deepEqual([o.persistence.teams[0].first, o.persistence.teams[0].second], [0.1235, 0.6667]);
  assert.equal(o.persistence.correlation, null);
  assert.equal(o.ladder[0].conversion, null);
  assert.equal(o.ladder[0].expected_wins, 1.2346);
  assert.equal(roundOutput({ calibration: { brier: null, bins: [] }, persistence: { teams: [], correlation: 0.55555 }, ladder: [] }).calibration.brier, null);
});

test("a missing input file prints one clear line and exits 1", () => {
  const script = fileURLToPath(new URL("../scripts/build-deserved.mjs", import.meta.url));
  const r = spawnSync(process.execPath, [script, "zz", "1900"], { encoding: "utf8" });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /missing/);
  assert.doesNotMatch(r.stderr, /at .*node:/);
});

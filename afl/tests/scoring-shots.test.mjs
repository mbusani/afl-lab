import { test } from "node:test";
import assert from "node:assert/strict";
import {
  binomialPmf, expectedScore, winProbability, scoreDistribution, matchLuck,
} from "../assets/scoring-shots.js";

const r4 = (x) => Math.round(x * 1e4) / 1e4;

test("binomialPmf sums to 1 and matches a hand case", () => {
  assert.deepEqual(binomialPmf(2, 0.5), [0.25, 0.5, 0.25]);
  const s = binomialPmf(30, 0.53).reduce((a, b) => a + b, 0);
  assert.ok(Math.abs(s - 1) < 1e-9);
});

test("expectedScore is S(1 + 5p)", () => {
  assert.equal(expectedScore(20, 0.5), 70);
  assert.equal(expectedScore(0, 0.53), 0);
});

test("2 v 2 shots at p = 0.5 (hand-checked)", () => {
  const w = winProbability({ homeShots: 2, awayShots: 2, p: 0.5 });
  assert.equal(w.home, 0.3125);
  assert.equal(w.draw, 0.375);
  assert.equal(w.away, 0.3125);
});

test("25 v 20 shots at p = 0.53", () => {
  const w = winProbability({ homeShots: 25, awayShots: 20, p: 0.53 });
  assert.equal(r4(w.home), 0.8266);
  assert.equal(r4(w.draw), 0.0661);
  assert.equal(r4(w.away), 0.1074);
  assert.equal(r4(w.homeExpected), r4(25 * 3.65));
});

test("probabilities sum to 1 and equal shots are symmetric", () => {
  for (const [h, a] of [[0, 0], [1, 0], [30, 30], [12, 31]]) {
    const w = winProbability({ homeShots: h, awayShots: a, p: 0.53 });
    assert.ok(Math.abs(w.home + w.draw + w.away - 1) < 1e-9);
  }
  const eq = winProbability({ homeShots: 30, awayShots: 30, p: 0.53 });
  assert.ok(Math.abs(eq.home - eq.away) < 1e-12);
  assert.equal(winProbability({ homeShots: 1, awayShots: 0, p: 0.53 }).home, 1);
  assert.equal(winProbability({ homeShots: 0, awayShots: 0, p: 0.53 }).draw, 1);
});

test("scoreDistribution lists S + 5g with binomial probabilities", () => {
  assert.deepEqual(scoreDistribution(2, 0.5), [
    { score: 2, prob: 0.25 }, { score: 7, prob: 0.5 }, { score: 12, prob: 0.25 },
  ]);
});

test("matchLuck is actual minus expected points, and zero-sum", () => {
  const l = matchLuck({ homeShots: 2, awayShots: 2, homeScore: 12, awayScore: 7, p: 0.5 });
  // expected home points = 0.3125 + 0.375/2 = 0.5, actual = 1
  assert.equal(l.home, 0.5);
  assert.equal(l.away, -0.5);
});

test("invalid input throws RangeError", () => {
  assert.throws(() => winProbability({ homeShots: -1, awayShots: 2, p: 0.5 }), RangeError);
  assert.throws(() => winProbability({ homeShots: 2.5, awayShots: 2, p: 0.5 }), RangeError);
  assert.throws(() => winProbability({ homeShots: 2, awayShots: 2, p: 0 }), RangeError);
  assert.throws(() => winProbability({ homeShots: 2, awayShots: 2, p: 1 }), RangeError);
});

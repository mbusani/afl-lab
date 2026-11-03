/* AFL scoring-shots model: "Did they deserve to win?"
   Each scoring shot is a goal (6) with probability p, otherwise a behind (1).
   A team with S shots and G goals scores S + 5G. G ~ Binomial(S, p).
   Pure functions, no DOM: shared by the model page and afl/scripts/build-deserved.mjs. */

function check(shots, p) {
  for (const s of shots) {
    if (!Number.isInteger(s) || s < 0) throw new RangeError(`shots must be a whole number >= 0, got ${s}`);
  }
  if (!(p > 0 && p < 1)) throw new RangeError(`p must be between 0 and 1 (exclusive), got ${p}`);
}

export function binomialPmf(n, p) {
  check([n], p);
  const out = new Array(n + 1);
  out[0] = Math.pow(1 - p, n);
  for (let k = 1; k <= n; k++) out[k] = out[k - 1] * ((n - k + 1) / k) * (p / (1 - p));
  return out;
}

export function expectedScore(shots, p) {
  check([shots], p);
  return shots * (1 + 5 * p);
}

export function scoreDistribution(shots, p) {
  return binomialPmf(shots, p).map((prob, g) => ({ score: shots + 5 * g, prob }));
}

export function winProbability({ homeShots, awayShots, p }) {
  check([homeShots, awayShots], p);
  const h = binomialPmf(homeShots, p);
  const a = binomialPmf(awayShots, p);
  let home = 0, draw = 0, away = 0;
  for (let i = 0; i < h.length; i++) {
    const hs = homeShots + 5 * i;
    for (let j = 0; j < a.length; j++) {
      const as = awayShots + 5 * j;
      const q = h[i] * a[j];
      if (hs > as) home += q; else if (hs === as) draw += q; else away += q;
    }
  }
  return {
    home, draw, away,
    homeExpected: expectedScore(homeShots, p),
    awayExpected: expectedScore(awayShots, p),
  };
}

export function matchLuck({ homeShots, awayShots, homeScore, awayScore, p }) {
  const w = winProbability({ homeShots, awayShots, p });
  const actual = homeScore > awayScore ? 1 : homeScore === awayScore ? 0.5 : 0;
  const expected = w.home + w.draw / 2;
  return { home: actual - expected, away: (1 - actual) - (1 - expected) };
}

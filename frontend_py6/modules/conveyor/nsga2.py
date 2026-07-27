"""
modules/conveyor/nsga2.py — NSGA-II for Phase 1 (geometry)
═══════════════════════════════════════════════════════════════════════════
Non-dominated Sorting Genetic Algorithm II, applied to the screw conveyor
Auto-Optimiser's geometry phase only.

Why only Phase 1
────────────────
Screw conveyor design is largely a CATALOGUE problem — standard shafts, a
finite gearbox and bearing list — and a grid sweep over real catalogue
entries guarantees every candidate is a buildable, orderable part. A GA
working on continuous variables and snapping to the nearest stocked part
afterwards can converge on combinations that do not exist.

Phase 1 is the exception: N (speed) and pitch ratio are genuinely
continuous, and the four goals (efficiency / energy / cost / life) trade
off against each other most sharply here. Phases 2-3 stay on the
catalogue-driven grid sweep.

Diameter is handled as an INTEGER INDEX into the standard-diameter list
rather than as a continuous variable that gets rounded. That removes the
catalogue-snapping problem for the one Phase-1 variable that has it: every
genome maps to a real diameter by construction, so no candidate can be
produced that is not orderable.

What this buys over weighted-sum
────────────────────────────────
The existing scorer collapses the selected goals into one scalar by equal
weighting. A design that is best-in-class on cost and life but mediocre on
energy loses to an all-round average design, and never appears in the top
five. NSGA-II returns the Pareto front instead: the set of designs where
improving any objective requires giving up another. Nothing on that front
is dominated, so the trade-off is the engineer's to make rather than the
weighting's.

Constraint handling
───────────────────
Deb's constrained-domination, not a penalty term:
  * a feasible solution always dominates an infeasible one
  * between two infeasible solutions, the smaller total violation wins
  * between two feasible solutions, ordinary Pareto dominance applies
This keeps infeasible designs in the population early (they carry useful
genes) without ever letting one outrank a feasible design.

Evaluation cost
───────────────
Every evaluation is an HTTP call to the backend. Genomes are cached by
their rounded decision vector, so re-evaluating an unchanged individual is
free — which matters because elitist survival carries parents forward
unchanged every generation.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

# Standard diameters (m) — the catalogue. Index into this, never interpolate.
STD_DIAMETERS: list[float] = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60]

N_BOUNDS = (20.0, 120.0)     # RPM
PR_BOUNDS = (0.75, 1.25)     # pitch / diameter

#: Objective extractors. Each returns a value to MINIMISE, so goals that are
#: "higher is better" are negated here rather than in the algorithm.
OBJECTIVES: dict[str, Callable[[dict], float]] = {
    "efficiency": lambda r: -((r.get("eff", {}) or {}).get("score", 0) or 0),
    "energy":     lambda r: (r.get("eff", {}) or {}).get("kWh_t", 9) or 9,
    "cost":       lambda r: (r.get("cost", {}) or {}).get("total", 99999) or 99999,
    "life":       lambda r: -((r.get("wear", {}) or {}).get("life_h", 0) or 0),
}


@dataclass
class Individual:
    d_idx: int
    N: float
    pr: float
    objectives: list[float] = field(default_factory=list)
    violation: float = 0.0
    result: Optional[dict] = None
    rank: int = 0
    crowding: float = 0.0

    @property
    def D(self) -> float:
        return STD_DIAMETERS[self.d_idx]

    @property
    def feasible(self) -> bool:
        return self.violation <= 0.0

    def key(self) -> tuple:
        """Cache key — rounded so trivially different genomes reuse a result."""
        return (self.d_idx, round(self.N, 1), round(self.pr, 3))


def constraint_violation(r: dict) -> float:
    """
    Total constraint violation, 0.0 when fully feasible.

    Counts the same five checks the grid sweep's _is_feasible() uses. A
    count rather than a magnitude, because the backend returns booleans for
    these rather than margins — a magnitude-based violation would need the
    engine to expose how far past each limit a design sits.
    """
    if not r or r.get("error"):
        return 5.0
    checks = [
        (r.get("cap", {}) or {}).get("ok"),
        (r.get("tor", {}) or {}).get("shOk"),
        r.get("deflection_ok"),
        (r.get("gbx_r", {}) or {}).get("tOk"),
        (r.get("brg_r", {}) or {}).get("ok"),
    ]
    return float(sum(1 for c in checks if not c))


def dominates(a: Individual, b: Individual) -> bool:
    """Deb's constrained-domination operator."""
    if a.feasible and not b.feasible:
        return True
    if b.feasible and not a.feasible:
        return False
    if not a.feasible and not b.feasible:
        return a.violation < b.violation
    better_anywhere = False
    for x, y in zip(a.objectives, b.objectives):
        if x > y:
            return False
        if x < y:
            better_anywhere = True
    return better_anywhere


def fast_non_dominated_sort(pop: Sequence[Individual]) -> list[list[Individual]]:
    """Partition into Pareto fronts; sets .rank on every individual."""
    fronts: list[list[Individual]] = [[]]
    dominated: dict[int, list[Individual]] = {}
    n_dominating: dict[int, int] = {}

    for p in pop:
        dominated[id(p)] = []
        n_dominating[id(p)] = 0
        for q in pop:
            if p is q:
                continue
            if dominates(p, q):
                dominated[id(p)].append(q)
            elif dominates(q, p):
                n_dominating[id(p)] += 1
        if n_dominating[id(p)] == 0:
            p.rank = 0
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        nxt: list[Individual] = []
        for p in fronts[i]:
            for q in dominated[id(p)]:
                n_dominating[id(q)] -= 1
                if n_dominating[id(q)] == 0:
                    q.rank = i + 1
                    nxt.append(q)
        i += 1
        fronts.append(nxt)
    return [f for f in fronts if f]


def crowding_distance(front: list[Individual]) -> None:
    """Assign crowding distance within one front — preserves front diversity
    so the returned Pareto set spreads across the trade-off rather than
    clustering in one corner."""
    n = len(front)
    if n == 0:
        return
    for ind in front:
        ind.crowding = 0.0
    n_obj = len(front[0].objectives)
    for m in range(n_obj):
        front.sort(key=lambda ind: ind.objectives[m])
        front[0].crowding = math.inf
        front[-1].crowding = math.inf
        lo, hi = front[0].objectives[m], front[-1].objectives[m]
        span = hi - lo
        if span <= 0:
            continue
        for i in range(1, n - 1):
            front[i].crowding += (
                front[i + 1].objectives[m] - front[i - 1].objectives[m]
            ) / span


def _tournament(pop: Sequence[Individual], rng: random.Random) -> Individual:
    """Binary tournament on the crowded-comparison operator."""
    a, b = rng.choice(pop), rng.choice(pop)
    if a.rank != b.rank:
        return a if a.rank < b.rank else b
    return a if a.crowding > b.crowding else b


def _sbx(x1: float, x2: float, lo: float, hi: float,
         rng: random.Random, eta: float = 15.0) -> tuple[float, float]:
    """Simulated binary crossover for a continuous gene."""
    if abs(x1 - x2) < 1e-12:
        return x1, x2
    u = rng.random()
    beta = (2 * u) ** (1 / (eta + 1)) if u <= 0.5 else (1 / (2 * (1 - u))) ** (1 / (eta + 1))
    c1 = 0.5 * ((1 + beta) * x1 + (1 - beta) * x2)
    c2 = 0.5 * ((1 - beta) * x1 + (1 + beta) * x2)
    return min(max(c1, lo), hi), min(max(c2, lo), hi)


def _poly_mutate(x: float, lo: float, hi: float,
                 rng: random.Random, eta: float = 20.0) -> float:
    """Polynomial mutation for a continuous gene."""
    if hi <= lo:
        return x
    u = rng.random()
    delta = ((2 * u) ** (1 / (eta + 1)) - 1) if u < 0.5 else (1 - (2 * (1 - u)) ** (1 / (eta + 1)))
    return min(max(x + delta * (hi - lo), lo), hi)


def optimise(
    evaluate: Callable[[float, float, float], dict],
    goals: Sequence[str],
    pop_size: int = 24,
    generations: int = 12,
    seed: int = 12345,
    progress: Optional[Callable[[int, int], bool]] = None,
) -> tuple[list[Individual], list[Individual]]:
    """
    Run NSGA-II over Phase 1 geometry.

    evaluate(D, N, P) -> backend design result dict.
    goals            -> subset of OBJECTIVES keys; these become the axes.
    progress(done,total) -> return False to abort.

    Returns (pareto_front, all_evaluated).

    Deterministic by default: the RNG is seeded, so the same inputs give the
    same front. An optimiser that suggests different geometry on each run
    for identical inputs is very hard for an engineer to trust or review.

    Budget is pop_size × generations evaluations before caching — 24 × 12 =
    288, deliberately close to the grid sweep's 320 so the two methods can
    be compared at equal cost.
    """
    rng = random.Random(seed)
    objs = [g for g in goals if g in OBJECTIVES] or ["efficiency"]
    cache: dict[tuple, Individual] = {}
    evaluated: list[Individual] = []
    budget = pop_size * generations
    done = 0

    def evaluate_ind(ind: Individual) -> bool:
        """Fill in objectives/violation. False if the caller aborted."""
        nonlocal done
        hit = cache.get(ind.key())
        if hit is not None:
            ind.objectives = list(hit.objectives)
            ind.violation = hit.violation
            ind.result = hit.result
            return True
        P = min(ind.D * ind.pr, 1.5)
        r = evaluate(ind.D, ind.N, P)
        done += 1
        ind.result = r
        ind.violation = constraint_violation(r)
        ind.objectives = [OBJECTIVES[g](r) for g in objs]
        cache[ind.key()] = ind
        evaluated.append(ind)
        if progress is not None and not progress(done, budget):
            return False
        return True

    # ── initial population ────────────────────────────────────────────────
    # Seeded with an even spread across the diameter catalogue rather than
    # pure random, so no diameter band is missing from generation 0 — a GA
    # cannot recover a diameter that never entered the gene pool except by
    # mutation, and the catalogue is small enough to cover outright.
    pop: list[Individual] = []
    for i in range(pop_size):
        d_idx = i % len(STD_DIAMETERS)
        pop.append(Individual(
            d_idx=d_idx,
            N=rng.uniform(*N_BOUNDS),
            pr=rng.uniform(*PR_BOUNDS),
        ))
    for ind in pop:
        if not evaluate_ind(ind):
            return _finish(pop, evaluated)

    fronts = fast_non_dominated_sort(pop)
    for f in fronts:
        crowding_distance(f)

    # ── generations ───────────────────────────────────────────────────────
    for _ in range(generations - 1):
        offspring: list[Individual] = []
        while len(offspring) < pop_size:
            p1, p2 = _tournament(pop, rng), _tournament(pop, rng)
            n1, n2 = _sbx(p1.N, p2.N, *N_BOUNDS, rng=rng)
            r1, r2 = _sbx(p1.pr, p2.pr, *PR_BOUNDS, rng=rng)
            # Diameter: discrete uniform crossover, then occasional
            # neighbour-step mutation. Interpolating an index and rounding
            # would bias toward the middle of the catalogue.
            d1, d2 = (p1.d_idx, p2.d_idx) if rng.random() < 0.5 else (p2.d_idx, p1.d_idx)
            for d, N, pr in ((d1, n1, r1), (d2, n2, r2)):
                if rng.random() < 0.25:
                    d = min(max(d + rng.choice((-1, 1)), 0), len(STD_DIAMETERS) - 1)
                offspring.append(Individual(
                    d_idx=d,
                    N=_poly_mutate(N, *N_BOUNDS, rng=rng),
                    pr=_poly_mutate(pr, *PR_BOUNDS, rng=rng),
                ))
        offspring = offspring[:pop_size]
        for ind in offspring:
            if not evaluate_ind(ind):
                return _finish(pop + offspring, evaluated)

        # Elitist survival: parents + offspring, truncated by rank then
        # crowding. Guarantees the best front never degrades between
        # generations.
        merged = pop + offspring
        fronts = fast_non_dominated_sort(merged)
        new_pop: list[Individual] = []
        for f in fronts:
            crowding_distance(f)
            if len(new_pop) + len(f) <= pop_size:
                new_pop.extend(f)
            else:
                f.sort(key=lambda i: i.crowding, reverse=True)
                new_pop.extend(f[:pop_size - len(new_pop)])
                break
        pop = new_pop

    return _finish(pop, evaluated)


def _finish(pop: Sequence[Individual],
            evaluated: list[Individual]) -> tuple[list[Individual], list[Individual]]:
    """Pareto front of the FEASIBLE evaluated set, plus everything seen.

    The front is taken over all feasible individuals ever evaluated, not
    just the final population — a good design discovered in generation 3
    and later crowded out is still a valid answer to show the engineer.
    """
    feasible = [i for i in evaluated if i.feasible]
    if not feasible:
        return [], evaluated
    fronts = fast_non_dominated_sort(feasible)
    front = fronts[0] if fronts else []
    crowding_distance(front)
    front.sort(key=lambda i: (i.objectives[0], -i.crowding))
    return front, evaluated
# satellite_floer.bordered

The algebra half of the satellite computation. Given a type-A structure for a pattern and a
type-D structure for a companion, it pairs them:

```
CFA^-(P, S^1 x D^2)   [x]   CFDhat(S^3 - nu(K))   =   gCFK^-(P(K))
```

**No Heegaard diagrams anywhere in here.** The only thing this half reads from upstream is
a CSV of discs, whose first four columns — source, target, power of `U`, chord word — *are*
the type-A structure. Where those discs came from is not its business.

Part of the `satellite-floer` package. No dependencies. Python 3.9+.

```bash
satellite-floer knots                            # the knot catalogue
satellite-floer cfd trefoil -o trefoil.csv       # CFDhat of the complement
satellite-floer cfa Q121-discs.csv               # a disc table, as a CFA^-
satellite-floer box Q121-discs.csv trefoil       # gCFK^- of the satellite
satellite-floer box cfa.csv cfd.csv -o out.csv   # ... both sides from files
satellite-floer check out.csv                    # d^2, and the rank at U = 1
python3 -m unittest discover -s tests          # from the repository root
```

```python
from satellite_floer.bordered import box, cfd, read_cfa

pattern   = read_cfa(open("Q121-discs.csv").read())
companion = cfd("trefoil")
satellite = box(pattern, companion)

satellite.is_a_complex()             # d^2 = 0
satellite.homology_rank_at_U1()      # 1, for anything that really is a knot complex
```

## Everything is over F_2 and F_2[U]

So there are no signs anywhere, and there is nothing to get wrong about them. Everything is
basis-dependent and concrete: a `CFA^-` is a graph, a `CFDhat` is a graph, a chain complex is
a graph. Two arrows that agree in every field cancel.

We do **not** check the `A_infinity` relations, or that a type-D structure really is one.
What is checked is `d^2 = 0`, the type-D relation, and all of the bookkeeping below.

## The torus algebra

`A(T^2)` has eight nonzero elements: two idempotents and six Reeb chords, the chords being the
intervals in the four points where the alpha arcs meet the boundary circle.

```
rho_1 = [1,2]    rho_2 = [2,3]    rho_3 = [3,4]
rho_12 = [1,3]   rho_23 = [2,4]   rho_123 = [1,4]
```

The two alpha arcs end at `{1,3}` and `{2,4}`, and those are the two idempotents. So a chord
`[i,j]` runs from the idempotent owning `i` to the one owning `j`, and that one sentence
generates the whole table — `rho_1, rho_3 : iota_0 -> iota_1`, `rho_2 : iota_1 -> iota_0`,
`rho_12 : iota_0 -> iota_0`, `rho_23 : iota_1 -> iota_1`, `rho_123 : iota_0 -> iota_1`.
Multiplication is concatenation, `[i,j][j,k] = [i,k]`, and everything else is zero.

**Idempotents are inferred, never declared.** Every chord pins the idempotent at each of its
ends, and an arrow with no chord forces its two ends to agree, so the arrows alone determine
the splitting except for a generator nothing touches. That is why nothing here has heard of
the `x_`/`y_` naming the diagrams upstream happen to use — it is a last-resort hint and a file
whose arrows say otherwise wins.

Read the other way, it is a fact about the diagrams: `y` generators must be `iota_0` and `x`
generators `iota_1`, because that is the only assignment under which every disc's chord word
composes from its source to its target. 0 violations in 903 discs.

**A word is a sequence, not a product.** `m_3(x, rho_1, rho_2)` and `m_2(x, rho_12)` are
different operations, and in the box tensor the first wants a two-arrow path in the type-D
structure and the second a one-arrow path. Note that `(rho_2, rho_1)` is a perfectly legal
argument list — the idempotents meet — even though `rho_2 . rho_1` is zero in the algebra; it
occurs in the disc tables.

## CFDhat from a knot complex

`knots.cfd("trefoil")` goes through `CFK^-`. A `CFK^-` here is a chain complex over `F_2[U]`
together with an Alexander grading, and the grading is exactly what makes it a knot complex.
In `CFK^infinity` coordinates `x` sits at `(0, A(x))` and `U^k x` at `(-k, A(x) - k)`, so a
term `x -> U^k y`:

| | |
|---|---|
| `k = 0` | preserves `i`, drops `j`: a **vertical** arrow, of length `A(x) - A(y)` |
| `k > 0` | drops `i` by `k`, preserves `j`: a **horizontal** arrow of length `k`, and `A(y) = A(x) + k` — horizontal arrows *raise* the Alexander grading |

Levine's Proposition 2.4 asks for a basis in which each family of arrows is a set of disjoint
pairs. Each pairing leaves exactly one generator over, `xi_0` vertically and `eta_0`
horizontally, and `tau(K) = A(xi_0) = -A(eta_0)`. Both are computed and cross-checked; a basis
that is not simplified is refused rather than mangled.

With `d b = a + U c` this makes the trefoil the **right-handed** one, `tau = +1`.

Then Theorem 2.6 builds the type-D structure. The `iota_0` part is the `CFK^-` basis itself;
the `iota_1` part is one chain of new generators per arrow, plus the unstable chain:

```
vertical arrow  xi_{2j-1} -> xi_{2j}  of length k, contributing k generators:
    xi_{2j} -D123-> kappa_1 -D23-> ... -D23-> kappa_k <-D1- xi_{2j-1}

horizontal arrow  eta_{2j-1} -> eta_{2j}  of length l, contributing l:
    eta_{2j-1} -D3-> lambda_1 -D23-> ... -D23-> lambda_l -D2-> eta_{2j}

the unstable chain, s = 2|tau| generators:
    tau > 0:   eta_0 -D3->   mu_1 -D23-> ... -D23-> mu_s <-D1- xi_0
    tau == 0:  xi_0 -D12-> eta_0
    tau < 0:   xi_0 -D123-> mu_1 -D23-> ... -D23-> mu_s -D2-> eta_0
```

For the unknot `n = 0`, so `xi_0` and `eta_0` are the same single generator and the `tau = 0`
case is a **self-loop labelled `rho_12`** — necessarily `rho_12` and not `rho_23`, because the
lone generator is in `iota_0` and `rho_12` is the only chord that runs `iota_0` to `iota_0`.

### The Alexander grading, when you do not give one

`infer_alexander` recovers it from the arrows, and three facts do it. Horizontal arrows pin
differences exactly. The multiset of vertical lengths equals the multiset of horizontal
lengths, by the symmetry of `CFK^infinity` under exchanging `i` and `j`, so the unknown
vertical lengths are a permutation of known numbers. And the multiset of gradings is symmetric
about 0, which fixes the remaining shifts absolutely. If that leaves more than one answer it
raises rather than guessing, and an explicit `# alexander:` line always wins.

So `d b = a + U c` is enough to say "trefoil" and get `A = (-1, 0, 1)` and `tau = 1` back.

## The box tensor

```
generators    x (x) eta, for x in the CFA and eta in the CFD in the SAME idempotent
differential  d(x (x) eta) = sum over operations  x -U^k, (a_1..a_n)-> y  of the CFA,
              and over paths  eta -a_1-> ... -a_n-> zeta  of the CFD spelling that same
              sequence, of  U^k . (y (x) zeta)
```

The `n = 0` term is the CFA's own `m_1` against the empty path, which ends where it started.

**Why it terminates.** A CFA that came from a Heegaard diagram has finitely many operations,
so its words have a longest length, and only paths of exactly that many arrows are ever
enumerated. The type-D side need not be bounded — the unknot's is a single generator with a
`rho_12` self-loop, and it is fine.

**What it is, in graph terms.** With single letters on both sides this would be the tensor
(Kronecker, categorical) product of edge-labelled graphs: keep a pair of edges when the labels
agree. With words on the type-A side it is the product construction for automata — the CFA is
a transducer reading chord words and emitting powers of `U`, the CFD is an NFA over the same
alphabet, and this is their composition. Chop each CFA word into a path through fresh
intermediate states and it is the plain tensor product again.

## What is checked, and what is not

Every satellite complex this produces is checked two ways: `d^2 = 0`, and the homology at
`U = 1` has total rank **exactly 1**. Setting `U = 1` kills every `F_2[U]`-torsion summand, so
what survives is the rank of the free part, and for anything that really is a knot complex
that is 1. It is cheap and it catches almost anything gone wrong.

Not written, and wanted — in the order that unblocks the most:

- **A partial box tensor.** Name one well-chosen generator of the `CFDhat` and one part of the
  `CFA`, tensor only those, argue that the result is a direct *summand* of the whole thing,
  and find the `F_2[U]` in there. This is where the project is heading: it is also how you
  elide most of a companion's `CFDhat` and still say something about `gCFK^-`.
- **Homology over `F_2[U]`, which may turn out to be unnecessary.** The reason to want Smith
  normal form over the PID was to separate the free part from the torsion. If a summand can be
  computed on its own, it is enough to compute that summand and see that the `F_2[U]` lives in
  it — no PID machinery at all. The rank at `U = 1` stays as the cheap global check either way.
- **Reducing a type-D structure.** `CFDhat` from a knot complex is already reduced, so the box
  tensor refuses arrows with an idempotent coefficient rather than mishandling them — an
  unreduced structure need not even be bounded.
- **Bases that are not simultaneously simplified.** We check that a given basis is both
  vertically and horizontally simplified and refuse otherwise; every knot in the catalogue
  is. Handling one that is only half simplified means carrying the change of basis
  `xi_p = sum a_{p,q} eta_q` explicitly. There is reportedly a theorem relating the two
  distinguished generators that would help — see `CLAUDE.md`, where the exact statement is
  flagged as needing to be pinned down first.
- **The `A_infinity` relations**, and checking that a type-D structure really is one.

## The formats

Three CSVs, specified in `docs/formats.md`: `bordered-cfa 1`, `bordered-cfd 1`, and
`bordered-complex 1` (which with an `# alexander:` line is a `CFK^-`). `read_cfa` also accepts
a `heegaard-discs 1` file, because the disc format's first four columns are the CFA format and
the other two are provenance.

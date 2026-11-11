# File formats

These five CSV formats are the whole coupling between the three jobs: building a
diagram, finding its discs, and the algebra. Each is a CSV: one header row, no quoting
(no field ever contains a comma), and metadata above it as `# key: value` lines, which
`pandas.read_csv(f, comment='#')` ignores. The first `#` line with no colon is the format
name and version.

Generator names are opaque strings without commas or spaces. A **chord word** is Reeb chords
concatenated with no separator, each spelled `P` + digits: `P1 P2 P3 P12 P23 P123`. The `P`
delimits, so `P1P23` and `P123` are different strings and the tokenisation is unambiguous.
The empty word is the empty field. Words are in **path order, never reversed**.

### `heegaard-diagram 1` — a bordered Heegaard diagram

```
# heegaard-diagram 1
# name: twin-rainbow
# x-generators: 8
# y-generators: 5
# basepoint: z corner
# basepoint: w arc 1
side_a,index_a,side_b,index_b,family
bottom,0,bottom,3,rainbow
left,4,bottom,4,left-bottom
```

Combinatorics only. One row per arc of beta; an endpoint names the **edge** (`bottom` `top`
`left` `right`) and the index along it, because bottom and top are the same alpha curve but
different sides of the fundamental domain. `family` is a label for the human. Where an arc is
*drawn* is a rendering decision made later and nothing depends on it.

### `heegaard-discs 1` — the discs a diagram bounds

```
# heegaard-discs 1
# diagram: twin-rainbow
# x-generators: 8
# y-generators: 5
# reeb-convention: composed
# count: 25
source,target,U,chords,arcs,path
y_0,x_7,0,P1,-1,N W
x_0,x_3,1,,1,E
```

`arcs` and `path` are provenance: which run of beta the disc is, and how it closed up along
the alpha curves. They are enough to rebuild the disc's polygon exactly, which is what lets a
disc table drawn by one implementation be redrawn by the other. **The algebra never reads
them.**

### `bordered-cfa 1` — a type-A structure

```
# bordered-cfa 1
# name: twin-rainbow
# iota0: y_0,y_1,y_2,y_3,y_4
# iota1: x_0,x_1,x_2,x_3,x_4,x_5,x_6,x_7
# count: 25
source,target,U,chords
y_0,x_7,0,P1
x_0,x_3,1,
```

**The first four columns of `heegaard-discs 1`, and nothing else** — so a disc CSV *is* a CFA
CSV with two extra columns, and `satellite_floer.bordered` reads either. One row is one operation
`m_{n+1}(source, a_1, ..., a_n) = U^k target` where the chord word is `a_1...a_n`; the empty
word is `m_1 = d`. Rows are counted **mod 2**: two rows agreeing in all four columns cancel.

The idempotent lines are the one thing a disc CSV does not carry explicitly. `satellite_floer.bordered` infers
them from the arrows (every chord pins the idempotents at its two ends, and an empty word
forces them equal), and only falls back to the `x_`/`y_` convention for a generator that no
arrow touches.

### `bordered-cfd 1` — a type-D structure

```
# bordered-cfd 1
# name: trefoil
# tau: 1
# iota0: a,b,c
# iota1: kappa_1_1,lambda_1_1,mu_1,mu_2
# count: 7
source,target,chord
a,kappa_1_1,P123
a,mu_1,P3
b,kappa_1_1,P1
...
```

Exactly one chord per arrow. `delta^1(source) = rho ⊗ target`, and the arrows out of one
generator are summed. An empty chord field would be an idempotent coefficient; the format
allows it, `CFDhat` from a knot complex never produces one, and the box tensor rejects it
(see the TODO — reduction is not written).

### `bordered-complex 1` — a chain complex over `F_2[U]`, and `CFK^-`

```
# bordered-complex 1
# name: trefoil
# generators: a,b,c
# alexander: a=-1,b=0,c=1
# count: 2
source,target,U
b,a,0
b,c,1
```

`d(source) = U^k target`, summed, mod 2. `# generators:` is needed because a generator can
have no arrows at either end. With an `# alexander:` line the complex is a **`CFK^-`** — the
grading is exactly the extra data that turns a chain complex into a knot complex, and it is
what the vertical/horizontal split and `tau` are read off. Without it, it is just a complex,
which is what the box tensor outputs.

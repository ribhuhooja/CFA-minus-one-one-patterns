"""Build the general-diagram report: H(r,s) from Chen form to finished diagram.

    python3 report.py            # writes out/general-diagrams.html

Everything in the page is computed here and now -- the checks are run, not quoted.
"""

from __future__ import annotations

import html
import os

from heegaard import Q, build, diagram_from_csv, diagram_to_csv
from heegaard.chen import (H, chen_form, cut_height, is_connected, main_region_winding,
                           recut, rotate_ccw, sigma)
from heegaard.format import discs_to_csv
from heegaard.layout import stroked
from heegaard.render import render_chen, render_diagram
from heegaard.solver import enumerate_discs

CELL = 380


def q_parameters(i, m, n):
    return 1 + 2 * i * m - m, n + 3 * m - 2 * m * n + 4 * i * m * n - 4 * i * m - 2


def arc_set(d):
    return sorted(tuple(sorted(((a.a.side, a.a.index), (a.b.side, a.b.index)))) for a in d.arcs)


def disc_rows(d):
    return discs_to_csv(enumerate_discs(d), d).splitlines()[6:]


def figure(svg: str, caption: str) -> str:
    return (f'<figure>{svg}<figcaption>{html.escape(caption)}</figcaption></figure>')


def worked(r: int, s: int, note: str = "") -> str:
    """One example, all the way through: Chen form, shift, turn, and back from the CSV."""
    form = chen_form(r, s)
    middle, hits = recut(form)
    turned = rotate_ccw(middle, name=f"H({r},{s})")
    final = H(r, s)
    csv = diagram_to_csv(final)
    again = diagram_from_csv(csv)

    same = arc_set(again) == arc_set(final)
    discs = len(enumerate_discs(final))
    pictures = "".join([
        figure(render_chen(form, cut=True, cell=CELL,
                           caption=f"H({r},{s}) Chen form, and where the region slides to"),
               "1. The Chen form on the annulus. The two red edges are one curve, mu, glued; "
               "beta never touches the dashed edges, so there are no generators on that curve "
               f"yet. The dashed red line is the new cut, through z. It meets beta in "
               f"{len(hits)} places, numbered along it -- these become the new generators."),
        figure(render_diagram(middle, cell=CELL,
                              caption=f"H({r},{s}) in the shifted region"),
               "2. The same picture in the shifted fundamental region, with z now at a "
               f"corner. The {form.M} points on mu are unmoved and only renumbered; the "
               f"{len(hits)} new ones sit on the horizontal curve."),
        figure(render_diagram(turned, cell=CELL, caption=f"H({r},{s}) turned"),
               "3. Turned a quarter turn, which puts z in the top left corner and exchanges "
               "the two curves: the points on mu are now the x generators."),
        figure(render_diagram(again, cell=CELL, caption=f"H({r},{s}) read back from its CSV"),
               "4. Written out as a CSV and read back as a diagram, with no memory of how it "
               f"was made. Same arcs as the diagram above: {same}."),
    ])
    facts = (f"<tr><td>sigma(r,s)</td><td>{sigma(r, s)}</td>"
             f"<td>main region winding, walked: {main_region_winding(r, s)}</td></tr>"
             f"<tr><td>dependent arcs D</td><td>{form.D}</td>"
             f"<td>{'|sigma|, sloping back' if sigma(r, s) < 0 else 'sigma + 2, turned round with two extra rainbows'}</td></tr>"
             f"<tr><td>points on mu</td><td>{form.M}</td><td>2|r| + s + D</td></tr>"
             f"<tr><td>cut height</td><td>{cut_height(form)}</td><td>the height of z</td></tr>"
             f"<tr><td>new generators</td><td>{len(hits)}</td><td>2|r| - 1 = {2 * abs(r) - 1}</td></tr>"
             f"<tr><td>finished diagram</td><td>{final.x_count} x, {final.y_count} y, "
             f"{len(final.arcs)} arcs</td><td>{discs} discs; drawn as strokes: "
             f"{stroked(final)}</td></tr>")
    return f"""
<section class="example">
  <h3>H({r}, {s}){' &mdash; ' + html.escape(note) if note else ''}</h3>
  <table class="facts">{facts}</table>
  <div class="grid">{pictures}</div>
  <details><summary>the CSV it writes</summary><pre>{html.escape(csv)}</pre></details>
</section>"""


def checks() -> str:
    rows, ok, bad = [], 0, 0
    for i in range(1, 5):
        for m in range(2, 5):
            for n in range(2, 5):
                r, s = q_parameters(i, m, n)
                match = arc_set(H(r, s)) == arc_set(Q(i, m, n))
                ok, bad = (ok + 1, bad) if match else (ok, bad + 1)
                rows.append(f"<tr><td>Q({i},{m},{n})</td><td>H({r},{s})</td>"
                            f"<td>{abs(sigma(r, s))}</td><td>{m + n - 2}</td>"
                            f"<td class='{'yes' if match else 'no'}'>{match}</td></tr>")

    sample = [(1, 2, 2), (2, 2, 2), (1, 3, 2), (2, 3, 3), (1, 4, 4)]
    disc_match = all(disc_rows(H(*q_parameters(*p))) == disc_rows(Q(*p)) for p in sample)
    tw, h31 = build("twin-rainbow"), H(3, 1)
    formula = all(sigma(r, s) == -main_region_winding(r, s)
                  for r in range(2, 12) for s in range(1, 21))

    return f"""
<section>
  <h2>The checks</h2>
  <p><b>sigma is the winding of the main region.</b> The closed form
  <code>1 - sum_(j=1)^(2r+s-1) (-1)^floor(j(2r-1)/(2r+s))</code> agrees with walking the main
  region from one loose end to the other and counting, on all 200 pairs with
  <code>2 &le; r &le; 11</code> and <code>1 &le; s &le; 20</code>: <b class="{'yes' if formula else 'no'}">{formula}</b>.</p>

  <p><b>The twin-rainbow is Q(1,2,1).</b> Those parameters give
  <code>(r,s) = {q_parameters(1, 2, 1)}</code>. Same arcs as the hand-drawn diagram:
  <b class="{'yes' if arc_set(tw) == arc_set(h31) else 'no'}">{arc_set(tw) == arc_set(h31)}</b>;
  same discs, all {len(enumerate_discs(h31))} of them:
  <b class="{'yes' if disc_rows(tw) == disc_rows(h31) else 'no'}">{disc_rows(tw) == disc_rows(h31)}</b>.</p>

  <p><b>Q(i,m,n) is H(1+2im-m, n+3m-2mn+4imn-4im-2)</b> &mdash; {ok} matched, {bad} did not.
  Disc tables identical too, on {len(sample)} of them:
  <b class="{'yes' if disc_match else 'no'}">{disc_match}</b>.</p>
  <table class="wide"><thead><tr><th>Q</th><th>H</th><th>|sigma|</th><th>m+n-2</th>
  <th>same arcs</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
</section>"""


def gallery(title: str, blurb: str, entries) -> str:
    cards = []
    for label, diagram in entries:
        cards.append(figure(render_diagram(diagram, cell=330, caption=label),
                            f"{label}: {diagram.x_count} x, {diagram.y_count} y, "
                            f"{len(diagram.arcs)} arcs"))
    return (f'<section><h2>{html.escape(title)}</h2><p>{blurb}</p>'
            f'<div class="grid">{"".join(cards)}</div></section>')


def build_report() -> str:
    examples = "".join([
        worked(3, 1, "= Q(1,2,1), the twin-rainbow"),
        worked(3, 6, "= Q(1,2,2)"),
        worked(4, 2, "= Q(1,3,1)"),
        worked(5, 4, "sigma > 0, so the dependent region turns round"),
        worked(-3, 6, "r < 0, the picture upside down"),
    ])
    n1 = gallery(
        "n = 1",
        "The family with <code>n = 1</code>, which the old Q constructor refused. "
        "Nothing about H(r,s) minds: <code>s</code> comes out small and the dependent "
        "region is short.",
        [(f"Q({i},{m},1) = H{q_parameters(i, m, 1)}", H(*q_parameters(i, m, 1)))
         for i, m in [(1, 2), (1, 3), (1, 4), (1, 5), (2, 2), (2, 3), (3, 2), (3, 3)]])
    return TEMPLATE.format(checks=checks(), examples=examples, gallery=n1)


TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<title>H(r, s): general bordered Heegaard diagrams</title>
<style>
 :root {{ color-scheme: light; }}
 body {{ font: 15px/1.6 ui-sans-serif, system-ui, sans-serif; color: #1d1a17;
        background: #fbfaf8; margin: 0 auto; max-width: 1180px; padding: 32px 24px 80px; }}
 h1 {{ font-size: 28px; margin: 0 0 4px; }}
 h2 {{ font-size: 20px; margin: 44px 0 10px; border-bottom: 1px solid #e5e0d8;
       padding-bottom: 6px; }}
 h3 {{ font-size: 17px; margin: 34px 0 8px; }}
 p {{ max-width: 78ch; }}
 code {{ font-family: ui-monospace, Menlo, monospace; font-size: 0.92em;
         background: #f2efe9; padding: 1px 4px; border-radius: 3px; }}
 .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr));
          gap: 18px; margin: 14px 0; }}
 figure {{ margin: 0; background: #fff; border: 1px solid #e5e0d8; border-radius: 6px;
           padding: 10px; }}
 figure svg {{ width: 100%; height: auto; display: block; }}
 figcaption {{ font-size: 12.5px; color: #6b645d; margin-top: 8px; }}
 table {{ border-collapse: collapse; font-size: 13.5px; margin: 10px 0; }}
 td, th {{ border: 1px solid #e5e0d8; padding: 3px 9px; text-align: left; }}
 th {{ background: #f2efe9; }}
 .facts td:first-child {{ color: #6b645d; }}
 .wide {{ font-size: 12.5px; }}
 .yes {{ color: #2a7d4f; }} .no {{ color: #b3261e; font-weight: 700; }}
 pre {{ background: #f7f5f1; border: 1px solid #e5e0d8; border-radius: 5px; padding: 10px;
        overflow-x: auto; font-size: 12px; }}
 details {{ margin-top: 10px; }} summary {{ cursor: pointer; color: #6b645d; font-size: 13px; }}
 .lede {{ color: #6b645d; margin-top: 0; }}
</style>
<h1>H(r, s)</h1>
<p class="lede">General bordered Heegaard diagrams, built in Chen form and re-cut.</p>

<p>Two integers make one of these: <code>r &ne; 0</code> and <code>s &gt; 0</code>, with beta a
single closed curve exactly when <code>gcd(2|r|-1, s+1) = 1</code>.</p>

<p>The <b>Chen form</b> lives on the torus cut along one curve only, the up-down one
<code>mu</code>, so it is an annulus. Every arc runs between its two boundary circles or turns
back to the one it came from, and nothing crosses the left-right curve at all &mdash; so the
picture has no generators on that curve yet. Writing <code>M = 2|r| + s + D</code> for the
number of points on each boundary, the arcs are, for <code>r &gt; 0</code>:</p>
<table>
<tr><td>right rainbows</td><td><code>right(j) &mdash; right(2r-1-j)</code></td>
    <td><code>j = 0 .. r-1</code></td><td>z inside the innermost</td></tr>
<tr><td>main strands</td><td><code>left(1+k) &mdash; right(2r+k)</code></td>
    <td><code>k = 0 .. s-1</code></td><td>slope <code>2r-1</code></td></tr>
<tr><td>left rainbows</td><td><code>left(s+1+j) &mdash; left(2r+s-j)</code></td>
    <td><code>j = 0 .. r-1</code></td><td>w inside the innermost</td></tr>
<tr><td>dependent</td><td>see below</td><td><code>D</code> of them</td>
    <td>closes the curve up</td></tr>
</table>

<p>The main region is everything but the last family. It is a single path from
<code>left(0)</code> to <code>right(2r+s)</code>, and the winding it picks up on the way is
<code>-sigma(r,s)</code>. The dependent arcs close that path and cancel the winding down to the
&plusmn;1 a bordered diagram needs. When <code>sigma &lt; 0</code> that takes
<code>D = |sigma|</code> strands sloping back by one. When <code>sigma &gt; 0</code> they would
have to slope the other way, and a strand cannot simply be turned round &mdash; so the region
gains a small rainbow at each end to turn the curve about, with <code>sigma</code> strands
between them, and <code>D = sigma + 2</code>. For <code>r &lt; 0</code> the whole picture is
upside down.</p>

<p>The <b>re-cut</b> is where the other generators come from. <code>z</code> sits inside the
innermost rainbow around it, and the fundamental region is slid until <code>z</code> is at a
corner &mdash; so the new horizontal cut runs at exactly that height. It meets beta in
<code>2|r|-1</code> places, and those become the new generators. Sliding does not disturb the
points on <code>mu</code>; it only renumbers them.</p>

<p>This is done with real geometry rather than by counting. <em>How many</em> crossings there
are can be read off, but <em>the order they come in along the cut</em> cannot &mdash; that is a
fact about where the arcs actually run, and it is what fixes the diagram. So the annulus is
drawn, the cut is a line across it, and the crossings are sorted by where they fall.</p>

{checks}

<h2>Worked examples</h2>
<p>Each one goes all the way through: the Chen form, the shifted fundamental region, the
quarter turn that puts <code>z</code> in the top left corner, and the diagram read back from
the CSV with no memory of how it was made.</p>
{examples}

{gallery}
</body>
"""


if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    path = os.path.join("out", "general-diagrams.html")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(build_report())
    print(f"wrote {path} ({os.path.getsize(path) / 1024:.0f} KB)")

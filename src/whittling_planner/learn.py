"""The knife cuts a whittler uses, what each is good for, and which cuts each
design and each step of a plan calls for."""

import re
from dataclasses import dataclass

from whittling_planner.designs import DESIGNS, EYES, LEVELS, Design


@dataclass(frozen=True)
class Cut:
    key: str
    name: str
    aka: str  # other names you'll see in books and videos
    level: str  # one of HOW_HARD
    good_for: str  # one line: what it's for
    how: tuple[str, ...]
    watch: tuple[str, ...]  # what goes wrong, and how to avoid it


HOW_HARD = ("Easy", "Takes practice", "Tricky")

CUTS: dict[str, Cut] = {
    c.key: c
    for c in [
        Cut(
            "straightaway", "Straightaway cut", "rough cut, push-away cut", "Easy",
            "Taking off a lot of wood fast: roughing out the outlines and knocking off corners.",
            (
                "Hold the knife in your fist, edge facing away from you.",
                "Hold the piece in your other hand, behind and out of the way of the blade.",
                "Push the blade along the wood at a shallow angle, so it lifts a long shaving.",
            ),
            (
                "It's the least controlled cut. Stop well short of your pencil line and finish with push or pull cuts.",
                "Shallow bites. A deep bite levers the wood apart and the split can run past your line.",
                "Brace your arms against your body and cut with a short, firm stroke, not a swing.",
            ),
        ),
        Cut(
            "pull", "Pull cut", "paring cut, draw cut, potato-peeler cut", "Easy",
            "Controlled shavings: rounding edges, shaping heads and bodies, cleaning up toward a line.",
            (
                "Hold the piece and the knife in the same hand, edge toward you.",
                "Rest that hand's thumb on the wood, below and past where the cut will end.",
                "Close your fingers toward your thumb, as if peeling a potato. The blade stops before it reaches the thumb.",
            ),
            (
                "The blade moves toward your thumb. Keep the thumb out of the line of the cut, or wear a thumb guard "
                "or a wrap of tape.",
                "Short strokes. The power comes from closing your hand, not from your arm.",
            ),
        ),
        Cut(
            "push", "Thumb push cut", "reinforced push cut, thumb-assist", "Easy",
            "Small, exact cuts with power behind them: rounding small curves, taking down high spots, and end grain.",
            (
                "Hold the knife with the edge facing away from you.",
                "Put the thumb of your other hand on the back of the blade.",
                "Push with that thumb while the knife hand steers. The blade moves only a short way, under full control.",
            ),
            (
                "The knife hand guides and the other thumb pushes. Pushing hard with the knife hand turns it into a "
                "straightaway cut, with none of the control.",
                "Ideal for end grain: slice across it at an angle, a thin layer at a time.",
            ),
        ),
        Cut(
            "stop", "Stop cut", "stop-and-relief cut", "Easy",
            "Inside corners, and anywhere one part meets another: under a chin or a bill, a hat brim, between legs. "
            "It stops a shaving or a split from running past the line.",
            (
                "Cut straight down into the wood along the line, rocking the blade, as deep as you want the corner.",
                "From the waste side, slice at an angle toward the bottom of that cut (the relief cut).",
                "The chip pops out where the cuts meet. Repeat, a little deeper each time.",
            ),
            (
                "Never pry a chip that won't come out. Cut the stop cut deeper and slice again.",
                "A stop cut along the grain can split the wood like a wedge, so press lightly there.",
                "Always slice toward the stop cut, never past it.",
            ),
        ),
        Cut(
            "vcut", "V-cut", "V-notch, V-groove", "Takes practice",
            "Lines and grooves: wing outlines, feathers, fur, mouths, beard lines, a turtle's shell, the gap between "
            "two legs.",
            (
                "Draw the line in pencil.",
                "Cut along one side of it at about 45°, angled under the line.",
                "Cut along the other side at the same angle, so the two cuts meet at the bottom. The V-shaped chip "
                "lifts out.",
            ),
            (
                "If the two cuts don't meet at the bottom, the chip tears out. Recut both sides, don't pull the chip.",
                "On a curved line the grain changes direction partway along, so turn the piece and cut from the "
                "other end where it starts to tear.",
                "Two shallow Vs look better than one deep one.",
            ),
        ),
        Cut(
            "scoop", "Scoop cut", "spoon cut, rolling cut", "Tricky",
            "Hollows and inside curves: under a chin, a dished face, under a mushroom cap, under a belly.",
            (
                "Start a pull or push cut at the rim of the hollow.",
                "Roll your wrist as you cut, so the blade dips down into the hollow and comes back up, like scooping "
                "ice cream.",
                "Slice the blade sideways as it goes, using its length rather than pushing straight.",
            ),
            (
                "The second half of a scoop runs uphill against the grain and tears. Scoop from both rims toward the "
                "bottom of the hollow, and stop there.",
                "A deep hollow is easier with a hook knife.",
            ),
        ),
        Cut(
            "lever", "Lever cut", "thumb pivot cut", "Takes practice",
            "Tight spots where a long stroke won't fit: around ears, into notches, cleaning out between legs.",
            (
                "Hold the knife edge-away and press the thumb of your knife hand on the wood, near the cut.",
                "Swing the blade around that thumb in a short arc, like closing a pair of scissors.",
                "Use the knife tip and take tiny bites.",
            ),
            (
                "The pivot thumb sits behind the blade, never in front of it.",
                "Work tight spots from both sides; reaching in from one side snaps thin parts.",
            ),
        ),
        Cut(
            "chip", "Triangle chip", "stab cut, eye chip", "Takes practice",
            "Eyes on a rustic figure, nostrils, and small decorative notches.",
            (
                "Draw a small triangle and mark its middle.",
                "Press the knife tip in along the three lines from the middle out to the corners: deepest in the "
                "middle, shallow at the corners.",
                "Slice along each side of the triangle, angled down toward the middle. The chip comes out as a "
                "little pyramid.",
            ),
            (
                "These are tiny cuts, so the tip must be sharp. A blunt tip crushes the wood instead of cutting it.",
                "Make both eyes the same size: cut one, then match the other to it.",
            ),
        ),
        Cut(
            "facet", "Flat-plane cut", "facet cut", "Takes practice",
            "The rustic look: each surface is one crisp, flat cut that's left showing.",
            (
                "Choose where the facet starts and ends.",
                "Take it off in one long, confident pull or straightaway cut, with the blade flat to the new face.",
                "Leave it. Each facet stays as the knife left it, so its corners stay sharp.",
            ),
            (
                "Going back over a facet makes it bumpy. If it isn't right, make the next facet beside it instead.",
                "A dull knife leaves a fuzzy face; a sharp one leaves it shiny. Strop before the final facets.",
            ),
        ),
        Cut(
            "saw", "Saw cut", "kerf cuts", "Easy",
            "Optional, if you have a coping saw or a small pull saw: taking off big waste fast, especially across "
            "the grain and from a 4 × 2 × 2 block.",
            (
                "Clamp the block, or hold it firmly on a bench hook.",
                "Saw in from the edge, stopping about 1/16 in outside your pencil line. Several cuts side by side "
                "break up a big piece of waste.",
                "Knock the waste out between the cuts with the knife, then carve down to the line.",
            ),
            (
                "Never saw right up to the line. The saw wanders, and the last 1/16 in is the knife's job.",
            ),
        ),
    ]
}

# "I want to…" → the cuts for it
USES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Take off a lot of wood fast", ("straightaway", "saw")),
    ("Round off an edge or shape a curve", ("pull", "push")),
    ("Get right down to a pencil line", ("push", "pull")),
    ("Carve into an inside corner without splitting past it", ("stop",)),
    ("Cut a line or a groove: wings, fur, a mouth", ("vcut",)),
    ("Hollow out a dip: under a chin, a dished face", ("scoop",)),
    ("Work in a tight spot, around ears or between legs", ("lever",)),
    ("Make an eye or a small notch", ("chip",)),
    ("Leave crisp, flat knife facets (the rustic style)", ("facet",)),
    ("Carve end grain, the hard ends of the fibers", ("push",)),
)

# a progression through the designs, each adding something new
PATH: tuple[tuple[str, str], ...] = (
    ("penguin", "All smooth, outward curves. Learn to round with pull and push cuts, always cutting downhill."),
    ("duck-rustic", "Flat-plane cuts that stay crisp, and a triangle chip for each eye."),
    ("gnome", "Stop cuts under the hat brim, and V-cuts down the beard."),
    ("duck-decoy", "A first scoop cut, behind the head, and V-cut wings."),
    ("owl", "Scooping the dished face from both sides, and lever cuts between the ear tufts."),
    ("bear-standing", "Stop cuts and scoops in the tight gaps between the arms, legs and body."),
    ("cat-sitting", "Thin ears and narrow gaps: everything at once."),
)

# words in plan steps that link to a cut, or to a topic on the Learn page
TERMS: tuple[tuple[str, str], ...] = (
    (r"straightaway cuts?", "straightaway"),
    (r"pull cuts?", "pull"),
    (r"push cuts?", "push"),
    (r"stop cuts?", "stop"),
    (r"V-cuts?", "vcut"),
    (r"scoop cuts?", "scoop"),
    (r"lever cuts?", "lever"),
    (r"triangle(?:-shaped)? chips?", "chip"),
    (r"flat planes?", "facet"),
    (r"coping saw|saw cuts?", "saw"),
    (r"downhill", "grain"),
    (r"short grain", "grain"),
    (r"end grain", "grain"),
)
_FINISH_TERMS = [(re.compile(p, re.I), k) for p, k in TERMS if k in CUTS] + [(re.compile(r"\bhollow", re.I), "scoop")]

# the cuts for each kind of step
PROFILE_CUTS = (
    ("straightaway", "the bulk of the waste, in shallow bites"),
    ("stop", "inside corners of the outline"),
    ("push", "the last 1/16 in, down to the line"),
    ("saw", "optional: big waste, stopping 1/16 in outside the line"),
)
ROUND_CUTS = (
    ("straightaway", "the long corners, early on"),
    ("pull", "rounding, with control"),
    ("push", "small curves and end grain"),
)
RUSTIC_ROUND_CUTS = (
    ("facet", "each corner becomes one flat facet"),
    ("push", "small facets and end grain"),
)


def cuts_in(texts) -> list[tuple[str, str]]:
    """The cuts that steps like "Wings: a V-cut along each side" mention, with
    what each is for (the part before the colon)."""
    out = []
    for text in texts:
        label = text.split(":", 1)[0].lower() if ":" in text[:30] else ""
        for pattern, key in _FINISH_TERMS:
            if pattern.search(text) and (key, label) not in out:
                out.append((key, label))
    return out


def design_cuts(d: Design) -> list[tuple[str, str]]:
    """Every cut a design calls for beyond the roughing out, with where: its
    detail cuts, then what its own finishing touches mention."""
    out = {}
    for key, where in d.cuts:
        out.setdefault(key, []).append(where)
    for key, label in cuts_in(t for t in d.touches if t != EYES):
        out.setdefault(key, []).append(f"{label}, when finishing" if label else "when finishing")
    return [(key, "; ".join(wheres)) for key, wheres in out.items()]


def cut_json(key: str, where: str = "") -> dict:
    c = CUTS[key]
    return {"key": key, "name": c.name, "level": c.level, "good_for": c.good_for, "where": where}


def learn_json() -> dict:
    by_cut: dict[str, list[dict]] = {k: [] for k in CUTS}
    for d in DESIGNS.values():
        for key, where in design_cuts(d):
            by_cut[key].append({"key": d.key, "name": d.name, "level": d.level, "where": where})
    for designs in by_cut.values():
        designs.sort(key=lambda x: LEVELS.index(x["level"]))
    seen: set[str] = set()
    path = []
    for key, why in PATH:
        d = DESIGNS[key]
        cuts = [k for k, _ in design_cuts(d)]
        path.append({"key": key, "name": d.name, "level": d.level, "why": why,
                     "cuts": [{"key": k, "name": CUTS[k].name, "new": k not in seen} for k in cuts]})
        seen.update(cuts)
    return {
        "levels": HOW_HARD,
        "cuts": [{"key": c.key, "name": c.name, "aka": c.aka, "level": c.level, "good_for": c.good_for,
                  "how": c.how, "watch": c.watch, "designs": by_cut[c.key]} for c in CUTS.values()],
        "uses": [{"want": want, "cuts": [{"key": k, "name": CUTS[k].name} for k in keys]} for want, keys in USES],
        "path": path,
        "terms": [{"pattern": p, "anchor": a} for p, a in TERMS],
    }

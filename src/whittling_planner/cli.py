"""Terminal entry point.

    whittling-planner designs
    whittling-planner plan duck-decoy --block 2x1x1
    whittling-planner plan gnome --block 3x1.5x1.5 --straight
"""

import argparse

from whittling_planner.designs import BLOCKS, DESIGNS
from whittling_planner.grain import AXIS_WORDS
from whittling_planner.plan import compute, to_json


def main() -> None:
    parser = argparse.ArgumentParser(prog="whittling-planner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("designs", help="list the built-in designs")

    p_plan = sub.add_parser("plan", help="print a staged carving plan, with the measurements to mark out")
    p_plan.add_argument("design", choices=list(DESIGNS))
    p_plan.add_argument("--block", help=f"a stock block ({', '.join(BLOCKS)}) or your own, LxWxH in inches "
                                        "(default: the block the design was made for)")
    p_plan.add_argument("--straight", action="store_true", help="never turn the figure at an angle in the block")
    p_plan.add_argument("--grain", choices=list("xyz"), help="grain direction (default: along the block's length)")

    args = parser.parse_args()
    if args.cmd == "designs":
        for d in DESIGNS.values():
            print(f"{d.key:14s} {d.name:16s} {d.level:13s} {d.style:8s} made for {', '.join(d.blocks)}")
    elif args.cmd == "plan":
        print_plan(args)


def print_plan(args) -> None:
    block = args.block or DESIGNS[args.design].blocks[0]
    dims = BLOCKS.get(block) or tuple(float(v) for v in block.lower().split("x"))
    plan = to_json(compute(args.design, tuple(v * 25.4 for v in dims), grain=args.grain, angled=not args.straight))

    print(f"{plan['design']['name']}: {plan['block_label']} block, finished size {plan['figure_label']}")
    g = plan["grain"]
    for axis in "xyz":
        n = g["weak_parts"][axis]
        tag = " (this block)" if axis == g["selected"] else ""
        print(f"  grain {AXIS_WORDS[axis]}{tag}: {f'{n} weak spot(s)' if n else 'no weak spots'}")
    for i, s in enumerate(plan["stages"], 1):
        removed = f"  [removes {s['removed_pct']:.0f}% of the block]" if "removed_pct" in s else ""
        print(f"\n{i}. {s['title']}{removed}")
        for step in s["steps"]:
            print(f"   - {step}")
        for m in s["marks"]:
            print(f"\n   {m['title']}: {m['station_head'].lower()} → {m['across_head'].lower()} (inches)")
            for row in m["rows"]:
                print(f"     {row['at']:>16s}   {row['marks']}")
            for tip in m["tips"]:
                print(f"     point {tip['label']}: {tip['text']}")


if __name__ == "__main__":
    main()

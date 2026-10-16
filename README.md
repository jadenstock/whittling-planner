# whittling-planner

Pick a block of wood and a design. The planner tells you how to set the block down, how to mark it out with a pencil, ruler and square, and what to carve away at each step, shown in 3D. It finishes with the eyes, texture and an oil or wax finish.

It's CAM (the software that plans CNC cuts) adapted for a person with a knife.

## Run

```sh
uv run whittling-planner-web                          # web app on http://127.0.0.1:8003
uv run whittling-planner designs                      # list the designs
uv run whittling-planner plan duck-decoy              # the plan and the measurements, in the terminal
uv run whittling-planner plan gnome --block 3x1.5x1.5 # your own block, in inches
uv run pytest
```

## What it does

- **Blocks:** four stock basswood blocks: 2 × 1 × 1, 4 × 1 × 1, 4 × 2 × 2 and 2 × 2 × 1 in. You can also enter your own size. Carving blocks are sold with the grain along their longest side.
- **Designs:** 19 designs (`designs.py`). Duck, cat and bear each come in several styles, and there are beginner-friendly extras: gnome, penguin, owl, toadstool, whale, turtle, frog and dachshund. Each design is drawn to fill the block it was made for. The *rustic* ones are built from flat facets, like Scandinavian flat-plane carving, so the knife cuts stay visible. Every design marked Beginner is checked to have no short-grain weak spots.
- **Explore page:** a gallery of every design, filtered by block, style and level. It shows each design inside each block.
- **Placement** (`placement.py`): any design goes in any block. The planner tries every way of setting the block down, and turns the figure up to 45° when that makes it at least 8% bigger. It keeps the grain running along a direction the design can take. Example: a dachshund turned 30° in a 2 × 2 × 1 block comes out 15% bigger than one set square on.
- **Marking out instead of printing** (`marks.py`): pencil lines go around the block at every 1/8 or 1/4 in ("stations"). For each outline, a table gives the measurements on each station, and lettered points cover the tips that fall between stations. A drawing of the face shows it all. The 3D view draws the same pencil lines on the block, and on each later step it outlines where the cut starts.
- **Stages:** prepare and mark the block; cut the profile outlines, the one that removes the most wood first (the side profile wins near-ties); round off the corners; carve the details; then finishing touches.
- **Grain check:** for each grain direction, it finds thin parts whose fibers are short and never reach the thick body (short grain) and highlights them on the model.

## How it works

Each design is a signed distance function, sampled on a voxel grid of about 100³ cells shaped to the block.

- Seen along an axis, the figure's outline is the minimum of its field along that axis. Pushing that outline straight through the block gives the shape a profile cut leaves.
- Each stage intersects the previous one with more extruded outlines (an elementwise max of fields). The result is the "visual hull" from 3, then 9, directions; the last stage is the figure itself.
- How much to remove at a point is the next stage's field, sampled at that point of the current stage's surface.
- The marking tables come from sampling each outline along the station lines. The lettered points are local extremes of the outline's contour.
- Grain check (`grain.py`): a morphological opening finds thin parts. A thin part is weak if, along the grain, its fibers are shorter than 15 mm and never reach the thick body.

## Next ideas

- Load your own STL model.
- Check your progress: photograph the piece against a plain background and compare its outline with the plan's.
- Show which way to cut each surface (downhill with the grain).
- Flag hollows a knife can't reach.

## Prior art

- *Sculpting by Numbers* (Rivers, Adams & Durand, SIGGRAPH Asia 2012) projected a "remove material here" map onto the piece while people sculpted.
- *FreeD* (Amit Zoran, MIT Media Lab) is a handheld milling tool that tracks its position and won't cut outside the model.

Neither targets whittling or handles grain.

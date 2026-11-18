# Episode 1 secret pushwall locations

Coordinates are zero based, with x increasing east and y increasing south.
These are the pushwall marker tiles in the stock level packages.

| Floor | Count | Wall tiles (x, y) |
| --- | ---: | --- |
| E1L1 | 5 | (10, 13), (30, 22), (18, 49), (17, 50), (13, 53) |
| E1L2 | 4 | (19, 12), (42, 27), (36, 32), (37, 61) |
| E1L3 | 10 | (12, 1), (39, 2), (2, 4), (11, 12), (29, 12), (43, 45), (10, 58), (37, 60), (4, 61), (7, 61) |
| E1L4 | 7 | (1, 5), (37, 8), (12, 10), (44, 11), (58, 24), (30, 45), (25, 53) |
| E1L5 | 5 | (50, 8), (48, 37), (2, 43), (39, 46), (44, 59) |
| E1L6 | 4 | (27, 4), (27, 12), (30, 13), (55, 22) |
| E1L7 | 2 | (1, 3), (40, 11) |
| E1L8 | 13 | (39, 8), (41, 11), (49, 15), (13, 28), (10, 29), (16, 29), (7, 30), (4, 31), (11, 32), (3, 33), (8, 33), (5, 34), (1, 50) |
| E1L9 | 2 | (36, 14), (25, 32) |
| E1L10 | 15 | (54, 2), (3, 6), (16, 6), (61, 7), (33, 16), (33, 17), (57, 19), (1, 25), (38, 30), (37, 31), (43, 32), (41, 42), (44, 46), (28, 49), (59, 52) |

The marked test wall is E1L1 (10, 13). The fixture starts one tile south
at (10, 14), facing north. In the fixture, press **Up Arrow** to push the wall
and **W** to walk into the opening.

For the test wall, use the south side and face north. The stock corridor has
open floor at (10, 12) and (10, 11) behind the wall, so this setup can exercise
both tile crossings. The table identifies map markers. It does not establish
a playtested route or push direction for every other secret.

On E1L1, the stock map has open standing tiles and an open first destination
from the following sides. Face the listed wall from the standing tile. An
actor can still block the destination at runtime.

| Wall | Standing tiles |
| --- | --- |
| (10, 13) | South (10, 14) or north (10, 12) |
| (30, 22) | West (29, 22) or east (31, 22) |
| (18, 49) | South (18, 50) or north (18, 48) |
| (17, 50) | West (16, 50) or east (18, 50) |
| (13, 53) | South (13, 54) or north (13, 52) |

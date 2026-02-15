# Object & Gripper Parameter Reference

All grasp-specific tuning knobs now live in [`config/object_gripper_params.yaml`](../config/object_gripper_params.yaml). Editing this single file lets you swap targets or retune the gripper without hunting through scripts.

## Editing Workflow

1. Stop any running Isaac Sim session.
2. Update the YAML file (keep indentation, use meters for distances).
3. Rerun your data collection or inference script – the parameters load on startup.
4. If you edit cube dimensions, rerun `python convert_orange1_to_cube.py` so the USD mesh matches the new spec.

## Parameter Groups

### Object Geometry & Spawn (`object`)
| Key | Description | Typical Range |
| --- | --- | --- |
| `count` | Number of spawn instances for the target object. Scripts currently expect `1`. | `1` |
| `models` / `usd_paths` | Asset names and USD paths that SceneFactory loads. Update if you introduce a new mesh. | existing asset IDs |
| `mass` | Kilograms applied when spawning the rigid body. | `0.05 – 0.3` kg |
| `target_width_m` | Optional explicit grasp width (meters). Overrides the inferred size when computing gripper closure. | leave blank to auto infer |
| `shape_type` | Declares the geometry family (`cube`, `sphere`, `cylinder`, `box`, ...). Enables shape-aware width calculation. | `cube` |
| `shape_dimensions.*` | Shape-specific measurements (e.g., `edge_length_m`, `radius_m`, `diameter_m`). Only the fields relevant to the declared shape are read. | match your CAD spec |
| `generation.*` | Workspace sampling box and exclusion zones used by `RandomPositionGenerator`. Expand/shrink to reposition drops. | within reachable workspace |
| `physics.radius` / `physics.height` | Cylindrical proxy dimensions (meters) shared by collision checks and placement. | radius `0.015 – 0.04` m |
| `physics.min_distance` | Minimum allowed spacing between spawned objects (meters). | `0.04 – 0.08` |
| `cube_conversion.half_extent_m` | Half-extent for the cube mesh. Total cube width = `half_extent * 2`. | `0.015 – 0.03` m |

### Placement Guards (`placement`)
| Key | Description | Tips |
| --- | --- | --- |
| `safety_distances.*` | Margins applied by `SmartPlacementManager` to avoid robot, edges, and plate. | Increase when cubes get larger. |
| `placement_limits.*` | Hard clamp on how far the smart placement solver will search along X/Y. | Keep within IK reach (~0.35 m). |
| `object_sizes.*` | Bounding sizes for different object categories. Keep `orange` in sync with your target geometry. | radius/height in meters |

### Gripper Hardware (`gripper_joint` & `gripper_controller`)
| Key | Description |
| --- | --- |
| `joint_name` | Joint inside the URDF to command. Only change if your URDF labels differ. |
| `open_position_rad` / `closed_position_rad` | Absolute joint angles (radians) used by `SingleJawGripper`. Shrink the open angle if additional clearance is needed. |
| `gripper_controller.step_size` | Increment applied while manually jogging the gripper (keyboard control, gradual closes). |

### Gripper Profile (`gripper_profile`)
| Key | Description |
| --- | --- |
| `max_opening_m` / `min_opening_m` | Physical jaw gap at fully open/closed. Determines how object width maps to openness percent. |
| `safety_clearance_m` | Positive values subtract from the object width (tightening the gap); set negative if you need extra air between jaws. |
| `percent_band` | Overrides `grasping.percent_band` to define the allowed randomization around the computed close percent. |

### Motion & Timing (`state_machine_control`)
| Subsection | Highlights |
| --- | --- |
| `grasping.*` | Set `auto_percent_from_object: true` (default) to derive the close percent from object size. `percent_band` defines the spread around the computed target. |
| `movement_speeds.*` | Cartesian step sizes (meters per physics step). Increase carefully—too fast breaks IK. |
| `positions.*` | All height/offset targets (approach, lift, transport, release) and the `initial_position`. Raise these when using taller props. |
| `timing.*` | Frame budgets for posture adjust, descent, lift checks, and release duration. Also feeds the lift success polling interval. |

### Grasp Detection (`grasp_detection`)
Same fields the old config exposed (distance thresholds, smart detector toggles, plate placement margins). Tune here when the detector falsely labels grasps or placements.

### Raycasting (`raycasting`)
Controls the debug rays that gate the descent:
- `ray_length_m`: total ray length in meters.
- `red/green/purple.origin_offset_local`: offsets (meters) from the wrist/gripper frames before casting.
- `direction_local`: unit vectors in each local frame.

Adjust offsets if you switch to a wider gripper so the green ray still enters the object’s body.

## Practical Examples

- **Make the gripper close further**: Leave `auto_percent_from_object` enabled and reduce `object.target_width_m` (or tweak the shape dimensions such as `edge_length_m` / `radius_m`), or tighten `gripper_profile.safety_clearance_m`. For manual overrides, adjust `close_angle_percent_*` directly.
- **Support a larger cube**: Increase `object.physics.radius/height`, bump `cube_conversion.half_extent_m`, widen the spawn `generation` ranges, raise `placement.safety_distances`, and tweak `positions.*` heights so the approach and lift clear the taller object.
- **Slow the descent**: Reduce `movement_speeds.descend_step_m` and optionally increase `timing.max_descend_steps` to keep the overall timeout reasonable.

Keep this document nearby while iterating—every knob in the grasp pipeline now has a single, discoverable home.

# Manual Teleoperation Quickstart

This guide explains how to launch Isaac Sim with the SO-101 scene in free-teleop mode and how to steer the arm with the keyboard. Use it whenever you want to sanity-check the workspace, tune IK limits, or gather manual demonstrations.

## 1. Launch the Manual Controller

```bash
conda activate isaac
cd /home/windowsuser/so101-autogen
python scripts/data_collection_manual.py
```

What the script does:

1. Boots Isaac Sim with visualization enabled (non-headless).
2. Loads the standard SO-101 scene, including the oranges, plate, and cameras.
3. Spawns the keyboard jogger so you can move the IK target directly without the grasping state machine.

> **Tip:** Keep the Isaac window focused while jogging so the Kit app receives keyboard events.

## 2. Default Keyboard Map

| Key | Action | Notes |
| --- | --- | --- |
| `W` / `S` | Move end-effector +X / −X (forward/back) | Clamped to the safe band configured in `manual_control.workspace_limits`. |
| `A` / `D` | Move end-effector +Y / −Y (left/right) | Same workspace clamping. |
| `E` / `F` | Move end-effector +Z / −Z (up/down) | Uses the vertical step size below. |
| `O` / `P` | Incrementally open / close the gripper | Applies `gripper_step_rad`. Consider remapping if Kit shortcuts conflict. |
| `SPACE` | Snap back to the initial hover pose | Uses `state_machine_control.positions.initial_position`. |
| `R` | Reset spawned objects and reopen the gripper | Calls `SceneManager.reset_scene()` then returns home. |
| `TAB` | Cycle active camera | Requires the camera controller to load successfully. |
| `Z` / `X` / `C` | Slow / Normal / Fast jog speeds | Multiplies the base step size by the configured multipliers. |
| `H` | Print the control cheat sheet | Useful after remapping keys. |
| `Q` | Quit manual mode | Gracefully tears down Isaac Sim. |

Jogging updates appear in the console every ~1.2 s (configurable), showing the current target pose and speed mode, so you always know where the IK solver is headed.

## 3. Tuning Step Sizes and Workspace Limits

All manual-teleop parameters live in `config/object_gripper_params.yaml` under the `manual_control` block:

```yaml
manual_control:
  step_sizes:
    linear_step_m: 0.008      # Base X/Y increment
    vertical_step_m: 0.006    # Base Z increment
    gripper_step_rad: 0.04    # Delta applied per O/P tap
    slow_multiplier: 0.25     # Applied when pressing Z
    fast_multiplier: 2.0      # Applied when pressing C
  workspace_limits:
    x: [0.19, 0.33]
    y: [-0.18, 0.18]
    z: [0.15, 0.36]
  status_interval_s: 1.2
```

- **Workspace limits**: Keep these aligned with ranges that the IK solver can actually reach. The current values mirror the constrained spawn region so we no longer hit Lula failures while jogging.
- **Step sizes**: Lower them for fine manipulation or increase them for faster sweeps. Remember the speed multipliers scale these base values.
- **Gripper delta**: `gripper_step_rad` maps directly to radians of joint motion per key press. Use a smaller number for precise finger positioning.

After editing the YAML, restart `scripts/data_collection_manual.py` so the new values load.

## 4. Troubleshooting

- **IK failure pop-ups**: If you manage to hit a hard limit, the controller automatically snaps back to the safe hover pose. Reduce the workspace range or step size if failures become frequent.
- **“Cannot parent prim” warnings**: Kit reserves some keys (e.g., `P`). If the notification spam is distracting, rebind the open/close keys in `ManualTeleopController._on_keyboard_event()` and update the table above.
- **Camera switching not working**: Ensure the camera controller module loads; otherwise `TAB` will log a warning but the rest of the teleop flow keeps running.

With this setup you can validate grasp poses manually, inspect joint limits, or record qualitative feedback before tweaking the automated pipeline.

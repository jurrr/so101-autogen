# -*- coding: utf-8 -*-
"""Manual teleoperation entry point for SO-101 in Isaac Sim."""
import logging
import os
import sys
import time
import weakref
from typing import Dict, Optional

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger("manual_teleop")


class ManualControlStateProxy:
    """Lightweight wrapper that exposes the gripper controller to the IK loop."""

    def __init__(self, gripper_controller, ik_controller):
        self.gripper_controller = gripper_controller
        self._ik_controller = ik_controller
        self._safe_target = ik_controller.get_target_position()

    def handle_ik_failure(self):
        logger.error("IK failure in manual mode. Returning to the safe target pose.")
        self._ik_controller.set_target_position(self._safe_target)
        self._ik_controller.move_to_initial_position()


class ManualTeleopController:
    """Keyboard-driven Cartesian jogger for the SO-101 end-effector."""

    def __init__(
        self,
        ik_controller,
        gripper_controller,
        scene_manager=None,
        camera_controller=None,
        manual_config: Optional[Dict] = None,
    ):
        manual_config = manual_config or {}
        step_cfg = manual_config.get("step_sizes", {})
        workspace_cfg = manual_config.get("workspace_limits", {})

        self.ik_controller = ik_controller
        self.gripper_controller = gripper_controller
        self.scene_manager = scene_manager
        self.camera_controller = camera_controller

        self.linear_step = float(step_cfg.get("linear_step_m", 0.01))
        self.vertical_step = float(step_cfg.get("vertical_step_m", 0.008))
        self.gripper_step = float(step_cfg.get("gripper_step_rad", 0.04))
        self.slow_multiplier = float(step_cfg.get("slow_multiplier", 0.25))
        self.fast_multiplier = float(step_cfg.get("fast_multiplier", 4.0))
        self.speed_mode = "normal"
        self.status_interval = float(manual_config.get("status_interval_s", 2.0))
        self.workspace_margin = float(manual_config.get("workspace_margin_m", 0.015))
        self.workspace_limits = self._normalize_workspace(workspace_cfg)
        self._effective_limits = self._shrink_workspace(self.workspace_limits, self.workspace_margin)

        self.exit_requested = False
        self._last_status = time.time()
        self._initial_target = self.ik_controller.get_target_position()
        self._limit_notified = {"x": False, "y": False, "z": False}

        self._keyboard = None
        self._keyboard_sub = None
        self._input = None
        self._appwindow = None

        self._subscribe_keyboard()
        self._print_control_help()

    def _normalize_workspace(self, workspace_cfg):
        default_limits = {
            "x": (0.19, 0.33),
            "y": (-0.18, 0.18),
            "z": (0.15, 0.36),
        }
        if not workspace_cfg:
            return default_limits

        limits = {}
        for axis in ("x", "y", "z"):
            axis_limits = workspace_cfg.get(axis)
            if isinstance(axis_limits, (list, tuple)) and len(axis_limits) == 2:
                limits[axis] = (float(axis_limits[0]), float(axis_limits[1]))
            else:
                limits[axis] = default_limits[axis]
        return limits

    def _shrink_workspace(self, limits, margin):
        if margin <= 0.0:
            return limits

        effective = {}
        for axis, (low, high) in limits.items():
            low_val = float(low)
            high_val = float(high)
            span = high_val - low_val
            if span <= 0:
                effective[axis] = (low_val, high_val)
                continue
            shrink = min(margin, max(0.0, span / 2.0 - 1e-4))
            effective[axis] = (low_val + shrink, high_val - shrink)
        return effective

    def _subscribe_keyboard(self):
        try:
            import carb.input
            import omni.appwindow

            self._appwindow = omni.appwindow.get_default_app_window()
            self._input = carb.input.acquire_input_interface()
            self._keyboard = self._appwindow.get_keyboard()
            self._keyboard_sub = self._input.subscribe_to_keyboard_events(
                self._keyboard,
                lambda event, *args, obj=weakref.proxy(self): obj._on_keyboard_event(event, *args),
            )
            logger.info("Manual teleop keyboard listener initialized.")
        except Exception as exc:
            logger.error("Failed to initialize keyboard listener: %s", exc)
            raise

    def _current_speed_multiplier(self) -> float:
        if self.speed_mode == "slow":
            return self.slow_multiplier
        if self.speed_mode == "fast":
            return self.fast_multiplier
        return 1.0

    def _xy_step(self) -> float:
        return self.linear_step * self._current_speed_multiplier()

    def _z_step(self) -> float:
        return self.vertical_step * self._current_speed_multiplier()

    def _set_speed_mode(self, mode: str):
        if mode not in {"slow", "normal", "fast"}:
            return
        if self.speed_mode == mode:
            return
        self.speed_mode = mode
        print(f"🚀 Speed mode: {self.speed_mode}")

    def _apply_motion(self, dx: float, dy: float, dz: float):
        delta = np.array([dx, dy, dz])
        if np.allclose(delta, 0.0):
            return

        current = self.ik_controller.get_target_position()
        desired = current + delta
        updated = desired.copy()
        clamped_axes = []
        for idx, axis in enumerate(("x", "y", "z")):
            limits = self._effective_limits.get(axis, self.workspace_limits[axis])
            before = updated[idx]
            updated[idx] = np.clip(before, *limits)
            if not np.isclose(updated[idx], before):
                clamped_axes.append(axis)

        if np.allclose(updated, current):
            self._notify_axis_limits(clamped_axes)
            return

        self.ik_controller.set_target_position(updated)
        self._last_status = 0  # force immediate status print
        self._notify_axis_limits(clamped_axes)

    def _notify_axis_limits(self, clamped_axes):
        if not clamped_axes and not any(self._limit_notified.values()):
            return

        for axis in ("x", "y", "z"):
            if axis in clamped_axes:
                if not self._limit_notified[axis]:
                    low, high = self._effective_limits[axis]
                    print(f"⚠️ {axis.upper()} axis limit reached ({low:.3f} m to {high:.3f} m).")
                    self._limit_notified[axis] = True
            else:
                self._limit_notified[axis] = False

    def _nudge_gripper(self, direction: float):
        delta = direction * self.gripper_step
        target = self.gripper_controller.get_target_position()
        low = min(self.gripper_controller.open_pos, self.gripper_controller.closed_pos)
        high = max(self.gripper_controller.open_pos, self.gripper_controller.closed_pos)
        updated = np.clip(target + delta, low, high)
        self.gripper_controller.set_target_position(updated)
        self.gripper_controller.current_gripper_position = updated
        openness = self.gripper_controller.get_openness_percentage() * 100.0
        print(f"🤏 Gripper target: {updated:.3f} rad ({openness:.1f}% open)")

    def _move_to_initial_target(self):
        self.ik_controller.set_target_position(self._initial_target)
        self.ik_controller.move_to_initial_position()
        print("🎯 Returned to initial Cartesian target.")

    def _reset_scene(self):
        if self.scene_manager:
            self.scene_manager.reset_scene()
            print("🔄 Scene objects reset.")
        self.gripper_controller.open_gripper()
        self._move_to_initial_target()

    def _switch_camera(self):
        if self.camera_controller:
            try:
                self.camera_controller.switch_camera()
                print("📷 Switched manual camera view.")
            except Exception as exc:
                print(f"⚠️ Failed to switch camera: {exc}")

    def _print_control_help(self):
        print("\n🎛️ Manual Teleoperation Controls:")
        print("   Arrow Up / Arrow Down : Move along +X / -X (toward / away from table)")
        print("   Arrow Left / Arrow Right : Move along +Y / -Y (left / right)")
        print("   Page Up / Page Down : Move along +Z / -Z (up / down)")
        print("   - (open) / + (close) : Control gripper")
        print("   SPACE  : Snap arm back to the initial pose")
        print("   R      : Reset scene objects and reopen gripper")
        print("   TAB    : Cycle camera views")
        print("   Z / X / C : Slow / normal / fast jogging speed")
        print("   H      : Reprint this cheat sheet")
        print("   Q      : Quit manual teleop mode")

    def _on_keyboard_event(self, event, *args, **kwargs):
        import carb.input

        if event.type != carb.input.KeyboardEventType.KEY_PRESS:
            return True

        key_name = event.input.name.upper()

        if key_name in {"UP", "ARROW_UP"}:
            self._apply_motion(self._xy_step(), 0.0, 0.0)
        elif key_name in {"DOWN", "ARROW_DOWN"}:
            self._apply_motion(-self._xy_step(), 0.0, 0.0)
        elif key_name in {"LEFT", "ARROW_LEFT"}:
            self._apply_motion(0.0, self._xy_step(), 0.0)
        elif key_name in {"RIGHT", "ARROW_RIGHT"}:
            self._apply_motion(0.0, -self._xy_step(), 0.0)
        elif key_name in {"PAGEUP", "PAGE_UP"}:
            self._apply_motion(0.0, 0.0, self._z_step())
        elif key_name in {"PAGEDOWN", "PAGE_DOWN"}:
            self._apply_motion(0.0, 0.0, -self._z_step())
        elif key_name in {"MINUS", "SUBTRACT", "KP_SUBTRACT", "NUMPAD_SUBTRACT"}:
            self._nudge_gripper(+1.0)
        elif key_name in {"EQUALS", "PLUS", "ADD", "KP_ADD", "NUMPAD_ADD"}:
            self._nudge_gripper(-1.0)
        elif key_name == "SPACE":
            self._move_to_initial_target()
        elif key_name == "R":
            self._reset_scene()
        elif key_name == "TAB":
            self._switch_camera()
        elif key_name == "Z":
            self._set_speed_mode("slow")
        elif key_name == "X":
            self._set_speed_mode("normal")
        elif key_name == "C":
            self._set_speed_mode("fast")
        elif key_name == "H":
            self._print_control_help()
        elif key_name == "Q":
            self.exit_requested = True
            print("👋 Exit requested (Q).")

        return True

    def tick(self):
        now = time.time()
        if now - self._last_status >= self.status_interval:
            pos = self.ik_controller.get_target_position()
            print(
                f"🎯 Target: x={pos[0]:.3f} m, y={pos[1]:.3f} m, z={pos[2]:.3f} m | speed={self.speed_mode}"
            )
            self._last_status = now

    def cleanup(self):
        if self._input and self._keyboard_sub:
            try:
                self._input.unsubscribe_to_keyboard_events(self._keyboard, self._keyboard_sub)
            except Exception as exc:
                logger.warning("Failed to unsubscribe keyboard listener: %s", exc)
        self._keyboard_sub = None
        logger.info("Manual teleop controller cleaned up.")


def _load_object_configs():
    from src.utils.config_utils import load_scene_config, load_object_gripper_config

    scene_config = load_scene_config(PROJECT_ROOT)
    object_gripper_config = {}
    if scene_config:
        object_gripper_config = scene_config.get("object_gripper", {}) or {}
    if not object_gripper_config:
        object_gripper_config = load_object_gripper_config(PROJECT_ROOT) or {}
    return scene_config, object_gripper_config


def main():
    print("🚀 SO-101 Manual Teleoperation Mode")
    print("This script loads the standard scene and lets you jog the arm manually.")

    scene_config, object_gripper_config = _load_object_configs()

    from src.utils.logger import setup_logging

    setup_logging()
    logger.info("Starting manual teleop setup.")

    from src.config.config_loader import ConfigLoader
    from src.core.simulation_manager import SimulationManager
    from src.utils.extension_loader import ExtensionLoader

    config_loader = ConfigLoader()
    config = config_loader.get_config()

    sim_manager = SimulationManager(headless=False)
    sim_manager.start_simulation()
    ExtensionLoader.load_all()

    from src.core.world_setup import WorldSetup
    from src.robot import get_ik_controller, get_gripper_controller
    from src.scene.scene_manager import SceneManager
    from src.utils.scene_factory import SceneFactory

    world_setup = WorldSetup(config, object_gripper_config=object_gripper_config)
    world = world_setup.create_world()
    world_setup.setup_environment()
    world_setup.add_follow_target_task()

    scene_factory = SceneFactory(PROJECT_ROOT, world)
    scene_objects, orange_positions, plate_center = scene_factory.create_orange_plate_scene(scene_config)

    world.reset()
    print("⏳ Stabilizing scene...")
    for step in range(60):
        world.step(render=True)
        if step % 20 == 0:
            print(f"   Warmup step {step + 1}/60")

    orange_reset_positions = {}
    if len(orange_positions) >= 1:
        orange_reset_positions["orange1_object"] = orange_positions[0].tolist()
    if len(orange_positions) >= 2:
        orange_reset_positions["orange2_object"] = orange_positions[1].tolist()
    if len(orange_positions) >= 3:
        orange_reset_positions["orange3_object"] = orange_positions[2].tolist()
    orange_reset_positions["plate_object"] = plate_center

    scene_manager = SceneManager(scene_config, world)
    scene_manager.register_scene_objects(scene_objects)
    scene_manager.set_orange_reset_positions(orange_reset_positions)

    task = world.get_task("so101_follow_target")
    task_params = task.get_params()
    robot_name = task_params["robot_name"]["value"]
    robot = world.scene.get_object(robot_name)
    if robot is None:
        raise RuntimeError(f"Robot '{robot_name}' not found in the scene.")

    IKController = get_ik_controller()
    ik_controller = IKController(robot, config, PROJECT_ROOT)

    GripperController = get_gripper_controller()
    open_pos = robot.gripper._joint_opened_position
    closed_pos = robot.gripper._joint_closed_position
    gripper_controller = GripperController(
        open_pos,
        closed_pos,
        controller_config=object_gripper_config.get("gripper_controller", {}),
    )
    gripper_controller.open_gripper()

    try:
        from src.camera import get_multi_camera_controller_from_ref

        MultiCameraController = get_multi_camera_controller_from_ref()
        camera_controller = MultiCameraController(config=scene_config)
        print("📷 Camera controller ready. Use TAB to cycle views.")
    except Exception as exc:
        camera_controller = None
        print(f"⚠️ Camera controller unavailable: {exc}")

    manual_config = object_gripper_config.get("manual_control", {})
    state_proxy = ManualControlStateProxy(gripper_controller, ik_controller)
    teleop_controller = ManualTeleopController(
        ik_controller=ik_controller,
        gripper_controller=gripper_controller,
        scene_manager=scene_manager,
        camera_controller=camera_controller,
        manual_config=manual_config,
    )

    try:
        print("🎮 Manual teleop ready. Use the keyboard to move the arm.")
        while sim_manager.is_running() and not teleop_controller.exit_requested:
            world.step(render=True)
            teleop_controller.tick()
            ik_controller.execute_control(robot, state_proxy)
    except KeyboardInterrupt:
        print("\n⌨️ Keyboard interrupt received. Closing manual teleop...")
    finally:
        teleop_controller.cleanup()
        sim_manager.close()
        print("✅ Isaac Sim shut down.")


if __name__ == "__main__":
    main()

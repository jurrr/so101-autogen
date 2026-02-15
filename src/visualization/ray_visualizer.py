# -*- coding: utf-8 -*-
"""
Ray Visualizer - Responsible for calculating and drawing rays.
Ray calculation logic is ported from the reference script interactive_ik_isaaclab_fixed_cameras.py.
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

class RayVisualizer:
    """
    Ray Visualizer - Responsible for calculating the position and direction of three rays, and for drawing them.
    """
    def __init__(self, draw_interface, config=None):
        """
        Initializes the Ray Visualizer.

        Args:
            draw_interface: An instance of Isaac Sim's _debug_draw interface.
        """
        self.draw = draw_interface
        self._config = config or {}
        self.ray_length = self._config.get('ray_length_m', 0.5)
        self._red_ray = self._build_ray_settings(
            'red', default_direction=[0.0, -1.0, 0.0], default_offset=[0.0, -0.08, 0.0]
        )
        self._green_ray = self._build_ray_settings(
            'green', default_direction=[-1.0, 0.0, 0.0], default_offset=[0.0, 0.0, -0.02]
        )
        self._purple_ray = self._build_ray_settings(
            'purple', default_direction=[0.0, 0.0, 1.0], default_offset=[0.0, 0.0, 0.0]
        )
        logger.info("🌈 Ray visualizer initialized.")

    def _build_ray_settings(self, key, default_direction, default_offset):
        ray_cfg = self._config.get(key, {})
        direction = np.array(ray_cfg.get('direction_local', default_direction))
        offset = np.array(ray_cfg.get('origin_offset_local', default_offset))
        return {"direction": direction, "offset": offset}

    def calculate_rays(self, ee_pos, ee_rot, gripper_pos, gripper_rot):
        """
        Calculates the start point, direction, and end point for the three rays.
        
        Args:
            ee_pos: End-effector position (wrist_link).
            ee_rot: End-effector rotation matrix (wrist_link).
            gripper_pos: Gripper position (gripper_frame_link).
            gripper_rot: Gripper rotation matrix (gripper_frame_link).
            
        Returns:
            dict: A dictionary containing information about the three rays.
        """
        try:
            # Red ray: Down from wrist_link (local negative Y-axis)
            ray_direction_red = ee_rot @ self._red_ray["direction"]
            offset_world_red = ee_rot @ self._red_ray["offset"]
            ray_origin_red = ee_pos + offset_world_red
            ray_end_point_red = ray_origin_red + ray_direction_red * self.ray_length

            # Green ray: Left from gripper (local negative X-axis)
            ray_direction_green = gripper_rot @ self._green_ray["direction"]
            offset_world_green = gripper_rot @ self._green_ray["offset"]
            ray_origin_green = gripper_pos + offset_world_green
            ray_end_point_green = ray_origin_green + ray_direction_green * self.ray_length

            # Purple ray: Up from gripper (local positive Z-axis)
            offset_world_purple = gripper_rot @ self._purple_ray["offset"]
            ray_origin_purple = gripper_pos + offset_world_purple
            ray_direction_purple = gripper_rot @ self._purple_ray["direction"]
            ray_end_point_purple = ray_origin_purple + ray_direction_purple * self.ray_length

            rays_info = {
                "red_ray": {
                    "origin": ray_origin_red,
                    "dir": ray_direction_red,
                    "end": ray_end_point_red,
                    "color": (1.0, 0.0, 0.0, 1.0),  # Red
                    "size": 2.0
                },
                "green_ray": {
                    "origin": ray_origin_green,
                    "dir": ray_direction_green,
                    "end": ray_end_point_green,
                    "color": (0.0, 1.0, 0.0, 1.0),  # Green
                    "size": 2.0
                },
                "purple_ray": {
                    "origin": ray_origin_purple,
                    "dir": ray_direction_purple,
                    "end": ray_end_point_purple,
                    "color": (1.0, 0.0, 1.0, 1.0),  # Purple
                    "size": 2.0
                }
            }
            
            return rays_info
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate rays: {e}")
            return {}

    def get_rays_for_drawing(self, rays_info, is_enabled=True):
        """     
        Gets the data for drawing the rays.
        
        Args:
            rays_info: A dictionary containing ray information.
            is_enabled: Whether visualization is enabled.
            
        Returns:
            tuple: (list of start points, list of end points, list of colors, list of sizes)
        """
        if not is_enabled or not rays_info:
            return [], [], [], []
        
        ray_starts = []
        ray_ends = []
        ray_colors = []
        ray_sizes = []
        
        for ray_name, ray_data in rays_info.items():
            ray_starts.append(ray_data["origin"])
            ray_ends.append(ray_data["end"])
            ray_colors.append(ray_data["color"])
            ray_sizes.append(ray_data["size"])
        
        return ray_starts, ray_ends, ray_colors, ray_sizes

    def draw_rays(self, rays_info, is_enabled=True):
        """
        Draws the rays.
        
        Args:
            rays_info: A dictionary containing ray information.
            is_enabled: Whether visualization is enabled.
        """
        if not is_enabled or not rays_info:
            return
        
        ray_starts, ray_ends, ray_colors, ray_sizes = self.get_rays_for_drawing(rays_info, is_enabled)
        
        if ray_starts:
            self.draw.draw_lines(ray_starts, ray_ends, ray_colors, ray_sizes)


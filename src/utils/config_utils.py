# -*- coding: utf-8 -*-
"""
Configuration Utilities Module
Provides functions for loading and processing configuration parameters, extracted from the main script.
"""

import os
import copy
import yaml


class ConfigManager:
    """Configuration Manager"""
    
    def __init__(self, project_root):
        """Initializes the ConfigManager.
        
        Args:
            project_root (str): The root path of the project.
        """
        self.project_root = project_root
        self.config_path = os.path.join(project_root, "config", "scene_config.yaml")
        self.object_gripper_config_path = os.path.join(project_root, "config", "object_gripper_params.yaml")
        self.object_gripper_config = None
    
    def load_scene_config(self):
        """Loads the scene configuration file.
        
        Returns:
            dict: A dictionary with the scene configuration, or None if the file does not exist.
        """
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print(f"✅ Scene configuration file loaded: {self.config_path}")
            self.object_gripper_config = load_object_gripper_config(self.object_gripper_config_path)
            if self.object_gripper_config:
                merge_object_gripper_config(config, self.object_gripper_config)
            return config
        else:
            print(f"⚠️ Configuration file not found: {self.config_path}")
            return None
    
    def get_config_with_defaults(self, config, key_path, default_value):
        """Safely retrieves a value from a nested configuration, using a default if not found.
        
        Args:
            config (dict): The configuration dictionary.
            key_path (str): The path to the key, using dot notation (e.g., "scene.plate.position").
            default_value: The default value to return if the key is not found.
            
        Returns:
            The configuration value or the default value.
        """
        keys = key_path.split('.')
        current = config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                print(f"⚠️ Configuration path '{key_path}' not found. Using default value: {default_value}")
                return default_value
        
        return current
    
    def get_plate_config(self, config):
        """Gets the plate configuration parameters.
        
        Args:
            config (dict): The scene configuration.
            
        Returns:
            dict: The plate configuration parameters.
        """
        return {
            "position": self.get_config_with_defaults(config, "scene.plate.position", [0.28, 0.0, 0.1]),
            "radius": self.get_config_with_defaults(config, "scene.plate.virtual_config.radius", 0.1),
            "height": self.get_config_with_defaults(config, "scene.plate.virtual_config.height", 0.02),
            "scale": self.get_config_with_defaults(config, "scene.plate.scale", 1.0)
        }
    
    def get_orange_config(self, config):
        """Gets the orange configuration parameters.
        
        Args:
            config (dict): The scene configuration.
            
        Returns:
            dict: The orange configuration parameters.
        """
        # Prefer the dedicated object/gripper configuration if it exists
        if self.object_gripper_config:
            object_cfg = self.object_gripper_config.get('object', {})
            generation_cfg = object_cfg.get('generation', {})
            physics_cfg = object_cfg.get('physics', {})
            return {
                "count": object_cfg.get('count', 1),
                "mass": object_cfg.get('mass', physics_cfg.get('mass', 0.15)),
                "models": object_cfg.get('models', ["Orange001"]),
                "usd_paths": object_cfg.get('usd_paths', ["assets/objects/Orange001/Orange001.usd"]),
                "x_range": generation_cfg.get('x_range', [0.1, 0.2]),
                "y_range": generation_cfg.get('y_range', [0.03, 0.23]),
                "z_drop_height": generation_cfg.get('z_drop_height', 0.1),
                "orange_radius": physics_cfg.get('radius', 0.025),
                "min_distance": physics_cfg.get('min_distance', 0.06),
                "max_attempts": generation_cfg.get('max_attempts', 50)
            }

        orange_generation = self.get_config_with_defaults(config, "scene.oranges.generation", {})

        return {
            "count": self.get_config_with_defaults(config, "scene.oranges.count", 1),
            "mass": self.get_config_with_defaults(config, "scene.oranges.physics.mass", 0.15),
            "models": self.get_config_with_defaults(config, "scene.oranges.models", 
                ["Orange001"]),
            "usd_paths": self.get_config_with_defaults(config, "scene.oranges.usd_paths", [
                "assets/objects/Orange001/Orange001.usd"
            ]),
            "x_range": orange_generation.get("x_range", [0.1, 0.2]),
            "y_range": orange_generation.get("y_range", [0.03, 0.23]),
            "z_drop_height": orange_generation.get("z_drop_height", 0.1),
            "orange_radius": orange_generation.get("orange_radius", 0.025),
            "min_distance": orange_generation.get("min_distance", 0.06),
            "max_attempts": orange_generation.get("max_attempts", 50)
        }
    
    def get_target_configs(self, config):
        """Gets the target configuration parameters.
        
        Args:
            config (dict): The scene configuration.
            
        Returns:
            dict: The target configuration parameters.
        """
        return self.get_config_with_defaults(config, "target_configs", {
            "/World/orange1": {
                "name": "orange1_object",
                "draw_aabb": True,
                "aabb_color": (1.0, 1.0, 0.0, 0.5),
                "draw_obb": True,
                "obb_color": (0.0, 1.0, 1.0, 1.0),
            }
        })


# Compatibility functions to maintain the same interface as the main script.
def load_scene_config(project_root):
    """Compatibility function."""
    config_manager = ConfigManager(project_root)
    return config_manager.load_scene_config()


def get_config_with_defaults(config, key_path, default_value):
    """Compatibility function."""
    config_manager = ConfigManager("")  # Empty project root, only used for method access.
    return config_manager.get_config_with_defaults(config, key_path, default_value)


def load_object_gripper_config(config_path_or_project_root):
    """Loads the consolidated object/gripper parameter file."""
    path = config_path_or_project_root
    if os.path.isdir(config_path_or_project_root):
        path = os.path.join(config_path_or_project_root, "config", "object_gripper_params.yaml")
    if not os.path.exists(path):
        print(f"⚠️ Object/gripper configuration not found: {path}")
        return None
    with open(path, 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    print(f"✅ Object/gripper configuration loaded: {path}")
    return data


def merge_object_gripper_config(scene_config, object_gripper_config):
    """Injects object/gripper parameters into the legacy scene config structure."""
    if not scene_config or not object_gripper_config:
        return scene_config

    scene_config['object_gripper'] = object_gripper_config

    scene_section = scene_config.setdefault('scene', {})
    oranges_section = scene_section.setdefault('oranges', {})

    object_cfg = object_gripper_config.get('object', {})
    if object_cfg:
        for key in ['count', 'mass', 'models', 'usd_paths']:
            if key in object_cfg:
                oranges_section[key] = object_cfg[key]
        if 'generation' in object_cfg:
            oranges_section['generation'] = copy.deepcopy(object_cfg['generation'])
        if 'physics' in object_cfg:
            oranges_section['physics'] = copy.deepcopy(object_cfg['physics'])

    placement_cfg = object_gripper_config.get('placement')
    if placement_cfg:
        placement_section = scene_config.setdefault('placement', {})
        _deep_update(placement_section, placement_cfg)

    if 'state_machine_control' in object_gripper_config:
        scene_config['state_machine_control'] = copy.deepcopy(object_gripper_config['state_machine_control'])

    if 'grasp_detection' in object_gripper_config:
        scene_config['grasp_detection'] = copy.deepcopy(object_gripper_config['grasp_detection'])

    if 'gripper_joint' in object_gripper_config:
        scene_config['gripper_joint'] = copy.deepcopy(object_gripper_config['gripper_joint'])

    if 'gripper_controller' in object_gripper_config:
        scene_config['gripper_controller'] = copy.deepcopy(object_gripper_config['gripper_controller'])

    if 'raycasting' in object_gripper_config:
        scene_config['raycasting'] = copy.deepcopy(object_gripper_config['raycasting'])

    return scene_config


def _deep_update(target, updates):
    """Recursively updates a nested dictionary."""
    for key, value in updates.items():
        if isinstance(value, dict):
            node = target.setdefault(key, {})
            if isinstance(node, dict):
                _deep_update(node, value)
            else:
                target[key] = copy.deepcopy(value)
        else:
            target[key] = copy.deepcopy(value)

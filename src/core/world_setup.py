# -*- coding: utf-8 -*-
"""
World Setup Manager
Handles the initialization of the Isaac Sim World, environment setup,
and the creation of simulation tasks.
"""

import numpy as np
from typing import Dict, Any
import logging

# Isaac Sim imports
from isaacsim.core.api import World
from isaacsim.core.prims import RigidPrim
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.core.utils.types import ArticulationAction
# Use a local copy of the FollowTarget task
from src.core.follow_target import FollowTarget
import omni.physx
from omni.isaac.core.utils.prims import create_prim

import omni.usd
from pxr import Sdf, Gf, UsdGeom

class WorldSetup:
    """
    World Setup Manager
    Responsible for creating the Isaac Sim world, adding tasks, and setting up the environment.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the WorldSetup manager.
        
        Args:
            config: The configuration dictionary.
        """
        self.config = config
        self.world = None
        self.task = None
        
        # Get parameters from config
        sim_config = config.get('simulation', {})
        self.stage_units = sim_config.get('stage_units_in_meters', 1.0)
        
        robot_config = config.get('robot', {})
        self.target_position = np.array(robot_config.get('target_position', [0.3, 0.0, 0.15]))
        
        task_config = config.get('task', {})
        self.task_name = task_config.get('name', 'so101_follow_target')
    
    def create_world(self) -> World:
        """
        Creates the Isaac Sim world.
        """
        try:
            self.world = World(stage_units_in_meters=self.stage_units)
            
            print(f"✅ World created (stage_units_in_meters: {self.stage_units}).")
            return self.world
            
        except Exception as e:
            print(f"❌ Failed to create World: {e}")
            raise
    
    def setup_environment(self):
        """
        Sets up the environment by adding lighting and a ground plane.
        """
        try:
            # Get environment configuration
            env_config = self.config.get('scene', {}).get('environment', {})
            
            # 1. Add a dome light
            light_config = env_config.get('lighting', {}).get('dome_light', {})
            light_prim_path = light_config.get('path', '/World/defaultLight')
            
            create_prim(prim_path=light_prim_path, prim_type="DomeLight")
            
            stage = omni.usd.get_context().get_stage()
            light_prim = stage.GetPrimAtPath(light_prim_path)
            
            # Set light parameters
            intensity = light_config.get('intensity', 3000.0)
            color = light_config.get('color', [0.75, 0.75, 0.75])
            
            light_prim.CreateAttribute("intensity", Sdf.ValueTypeNames.Float).Set(intensity)
            light_prim.CreateAttribute("color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
            
            print(f"✅ Dome light added: intensity={intensity}, color={color}.")
            
            # 2. Add a ground plane and IMMEDIATELY override it
            if env_config.get('ground_plane', True):
                self.world.scene.add_default_ground_plane()
                print("✅ Default ground plane added.")
                
                # IMMEDIATELY create our own white surface to replace grid
                print("🎨 IMMEDIATELY creating custom white surface to override grid...")
                self._create_custom_white_surface_override()
                    
            else:
                print("⚪ Ground plane disabled.")
            
            # 3. Disable visual grid if requested
            if env_config.get('disable_grid', False):
                self._disable_visual_grid()
                print("🚫 Visual grid disabled.")
                
            # 4. Apply aggressive white tabletop setup if table styling is configured
            table_styling = env_config.get('table_styling', {})
            if table_styling:
                # Try our advanced white table setup
                self._apply_advanced_white_table_setup(table_styling)
                # Also try the original method as backup
                self._apply_white_material_to_ground_plane(table_styling)
            
        except Exception as e:
            print(f"❌ Failed to set up environment: {e}")
            raise
    
    def add_follow_target_task(self):
        """
        Adds the FollowTarget task to the world.
        """
        try:
            self.task = FollowTarget(name=self.task_name, target_position=self.target_position)
            
            self.world.add_task(self.task)
            
            print(f"✅ FollowTarget task added: name={self.task_name}, target_position={self.target_position}.")
            return self.task
            
        except Exception as e:
            print(f"❌ Failed to add FollowTarget task: {e}")
            raise
    
    def reset_world(self):
        """
        Resets the world.
        """
        try:
            if self.world is not None:
                self.world.reset()
                print("✅ World has been reset.")
            else:
                print("⚠️ World not created, cannot reset.")
                
        except Exception as e:
            print(f"❌ Failed to reset World: {e}")
            raise
    
    def get_world(self) -> World:
        """Gets the World object."""
        return self.world
    
    def get_task(self):
        """Gets the task object."""
        return self.task
    
    def get_robot(self):
        """
        Gets the robot object from the world scene.
        """
        try:
            if self.task is None:
                print("⚠️ Task not created, cannot get robot.")
                return None
            
            task_params = self.task.get_params()
            robot_name = task_params["robot_name"]["value"]
            robot = self.world.scene.get_object(robot_name)
            
            print(f"✅ Robot object '{robot_name}' acquired.")
            return robot
            
        except Exception as e:
            print(f"❌ Failed to acquire robot object: {e}")
            return None
    
    def play_world(self):
        """
        Starts the simulation.
        """
        try:
            if self.world is not None:
                self.world.play()
                print("✅ Simulation started.")
            else:
                print("⚠️ World not created, cannot start simulation.")
                
        except Exception as e:
            print(f"❌ Failed to set up environment: {e}")
            raise
    
    def _disable_visual_grid(self):
        """
        Disable the visual grid overlay in Isaac Sim.
        This removes the grid lines from the viewport.
        """
        try:
            import carb
            import omni.kit.viewport.utility
            
            # Method 1: Try to disable grid via viewport settings
            try:
                viewport_api = omni.kit.viewport.utility.get_active_viewport()
                if viewport_api:
                    # Disable grid display
                    viewport_api.scene_view.displayOptions.showGrid = False
                    print("🚫 Disabled grid via viewport API")
                    return
            except Exception as e:
                print(f"⚠️ Viewport grid disable method 1 failed: {e}")
            
            # Method 2: Try to disable via carb settings
            try:
                settings = carb.settings.get_settings()
                settings.set_bool("/app/viewport/grid/enabled", False)
                settings.set_bool("/app/viewport/displayOptions/showGrid", False)
                print("🚫 Disabled grid via carb settings")
                return
            except Exception as e:
                print(f"⚠️ Viewport grid disable method 2 failed: {e}")
            
            # Method 3: Try to hide grid prim directly
            try:
                import omni.usd
                stage = omni.usd.get_context().get_stage()
                
                # Common grid prim paths
                grid_paths = [
                    "/World/grid",
                    "/World/Grid", 
                    "/Environment/grid",
                    "/defaultGroundPlane"
                ]
                
                for grid_path in grid_paths:
                    grid_prim = stage.GetPrimAtPath(grid_path)
                    if grid_prim.IsValid():
                        grid_prim.SetActive(False)
                        print(f"🚫 Disabled grid prim at {grid_path}")
                        return
                        
            except Exception as e:
                print(f"⚠️ Grid prim disable failed: {e}")
            
            print("⚠️ Could not disable grid - all methods failed")
            
        except ImportError as e:
            print(f"⚠️ Grid disable imports not available: {e}")
        except Exception as e:
            print(f"⚠️ Unexpected error disabling grid: {e}")
    
    def _apply_white_material_to_ground_plane(self, table_styling):
        """
        Apply white material to the ground plane to override grid pattern.
        
        Args:
            table_styling (dict): Table styling configuration with color, roughness, metallic
        """
        try:
            import omni.usd
            from pxr import UsdShade, Sdf, Gf
            
            stage = omni.usd.get_context().get_stage()
            if not stage:
                print("⚠️ USD stage not available for material application")
                return
                
            # Try to find the ground plane
            ground_plane_paths = [
                "/World/defaultGroundPlane",
                "/defaultGroundPlane", 
                "/World/GroundPlane",
                "/GroundPlane"
            ]
            
            ground_prim = None
            ground_path = None
            for path in ground_plane_paths:
                prim = stage.GetPrimAtPath(path)
                if prim.IsValid():
                    ground_prim = prim
                    ground_path = path
                    break
                    
            if not ground_prim:
                print("⚠️ Ground plane prim not found for white material application")
                return
                
            print(f"🎨 Applying white material to ground plane at {ground_path}")
            
            # Create material
            material_path = "/World/Materials/WhiteTable"
            material_prim = UsdShade.Material.Define(stage, material_path)
            
            # Create shader
            shader_path = f"{material_path}/Shader"
            shader = UsdShade.Shader.Define(stage, shader_path)
            shader.CreateIdAttr("UsdPreviewSurface")
            
            # Set material properties
            color = table_styling.get('color', [1.0, 1.0, 1.0])
            roughness = table_styling.get('roughness', 0.2)
            metallic = table_styling.get('metallic', 0.0)
            
            shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
            shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
            shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
            
            # Connect shader to material
            material_prim.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
            
            # Apply material to ground plane
            UsdShade.MaterialBindingAPI(ground_prim).Bind(material_prim.GetPrim())
            
            print(f"✅ White material applied to ground plane with color {color}")
            
        except ImportError:
            print("⚠️ USD libraries not available for white material application")
        except Exception as e:
            print(f"❌ Failed to apply white material to ground plane: {e}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")
            print("   This will be applied later when scene factory runs")
    
    def _apply_advanced_white_table_setup(self, table_styling):
        """
        Apply advanced white table setup with multiple methods to ensure clean white surface.
        """
        try:
            import omni.usd
            import carb
            from pxr import UsdShade, Sdf, Gf
            
            print("🎨 Applying advanced white table setup...")
            
            stage = omni.usd.get_context().get_stage()
            if not stage:
                print("⚠️ USD stage not available for advanced white table setup")
                return
                
            # Method 1: Aggressive grid disabling
            try:
                settings = carb.settings.get_settings()
                grid_settings = [
                    "/app/viewport/grid/enabled",
                    "/app/viewport/displayOptions/showGrid", 
                    "/app/viewport/grid/visible",
                    "/app/viewport/displayOptions/gridEnabled",
                    "/persistent/app/viewport/displayOptions/showGrid",
                    "/app/renderer/displayOptions/showGrid"
                ]
                
                for setting in grid_settings:
                    try:
                        settings.set_bool(setting, False)
                        print(f"   🚫 Disabled grid setting: {setting}")
                    except:
                        pass  # Some settings might not exist
                        
            except Exception as e:
                print(f"⚠️ Advanced grid disable failed: {e}")
            
            # Method 2: Hide all grid prims
            grid_paths = [
                "/World/grid", "/World/Grid", "/World/ground_grid",
                "/Environment/grid", "/Environment/Grid", "/Render/grid"
            ]
            
            for grid_path in grid_paths:
                try:
                    grid_prim = stage.GetPrimAtPath(grid_path)
                    if grid_prim.IsValid():
                        grid_prim.SetActive(False)
                        print(f"   🚫 Disabled grid prim: {grid_path}")
                except:
                    pass
                    
            print("✅ Advanced white table setup applied")
            
        except ImportError:
            print("⚠️ Advanced white table libraries not available")
        except Exception as e:
            print(f"❌ Advanced white table setup failed: {e}")

    def _apply_immediate_white_setup(self):
        """
        Apply immediate white ground plane setup right after ground plane creation.
        This combines all methods to ensure a clean white surface.
        """
        print("🎨 IMMEDIATE WHITE SETUP: Removing grid and applying white material...")
        
        # Step 1: Immediate grid disabling
        self._disable_grid_immediately()
        
        # Step 2: Apply white material
        table_styling = {
            'color': [1.0, 1.0, 1.0],
            'roughness': 0.1,
            'metallic': 0.0
        }
        self._apply_white_material_to_ground_plane(table_styling)
        
        # Step 3: Force grid removal from viewport
        self._force_viewport_grid_removal()
        
    def _disable_grid_immediately(self):
        """Immediately disable grid using all available methods."""
        try:
            import carb
            
            print("🚫 IMMEDIATE: Disabling all grid settings...")
            settings = carb.settings.get_settings()
            
            # Comprehensive grid setting disabling
            grid_settings = [
                "/app/viewport/grid/enabled",
                "/app/viewport/displayOptions/showGrid",
                "/app/viewport/grid/visible", 
                "/app/viewport/displayOptions/gridEnabled",
                "/persistent/app/viewport/displayOptions/showGrid",
                "/app/renderer/displayOptions/showGrid",
                "/app/stage/displayOptions/showGrid",
                "/app/omni/kit/viewport/displayOptions/showGrid"
            ]
            
            for setting in grid_settings:
                try:
                    settings.set_bool(setting, False)
                    print(f"   ✅ Disabled: {setting}")
                except Exception:
                    pass  # Some settings might not exist
                    
        except Exception as e:
            print(f"⚠️ Immediate grid disable failed: {e}")
            
    def _force_viewport_grid_removal(self):
        """Force remove grid from viewport using multiple methods."""
        try:
            import omni.kit.viewport.utility
            
            print("🚫 FORCE: Removing viewport grid...")
            
            # Method 1: Active viewport
            try:
                viewport = omni.kit.viewport.utility.get_active_viewport()
                if viewport and hasattr(viewport, 'scene_view'):
                    if hasattr(viewport.scene_view, 'displayOptions'):
                        viewport.scene_view.displayOptions.showGrid = False
                        print("   ✅ Forced grid off via active viewport")
            except Exception as e:
                print(f"   ⚠️ Active viewport method failed: {e}")
                
            # Method 2: All viewports
            try:
                # Get all viewport windows and disable grid
                viewport_names = ["Viewport", "Viewport Next"]
                for name in viewport_names:
                    try:
                        vp = omni.kit.viewport.utility.get_viewport_from_window_name(name)
                        if vp and hasattr(vp, 'scene_view'):
                            if hasattr(vp.scene_view, 'displayOptions'):
                                vp.scene_view.displayOptions.showGrid = False
                                print(f"   ✅ Forced grid off via {name}")
                    except:
                        pass
            except Exception as e:
                print(f"   ⚠️ Multi-viewport method failed: {e}")
                
        except Exception as e:
            print(f"⚠️ Force viewport grid removal failed: {e}")

    def _create_custom_white_surface_override(self):
        """
        Create a large white surface that completely covers and overrides the grid.
        This is placed slightly above the default ground plane to hide it completely.
        """
        try:
            import omni.usd
            from pxr import UsdGeom, UsdShade, Sdf, Gf
            from omni.isaac.core.utils.prims import create_prim
            
            print("🎨 Creating custom white surface override...")
            
            stage = omni.usd.get_context().get_stage()
            if not stage:
                print("   ❌ No USD stage available")
                return False
                
            # Create a large white plane that covers the entire workspace
            white_surface_path = "/World/CustomWhiteSurface"
            
            # Remove if exists
            if stage.GetPrimAtPath(white_surface_path).IsValid():
                stage.RemovePrim(white_surface_path)
                
            # Create plane geometry
            plane_geom = UsdGeom.Mesh.Define(stage, white_surface_path)
            
            # Create a 20x20 meter white plane (much larger than workspace)
            size = 10.0  # 10 meter radius = 20x20 total
            points = [
                (-size, -size, 0.001),  # Slightly above ground (1mm)
                (size, -size, 0.001),
                (size, size, 0.001), 
                (-size, size, 0.001)
            ]
            
            face_vertex_counts = [4]
            face_vertex_indices = [0, 1, 2, 3]
            normals = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)]
            
            # Set geometry attributes
            plane_geom.GetPointsAttr().Set(points)
            plane_geom.GetFaceVertexCountsAttr().Set(face_vertex_counts)
            plane_geom.GetFaceVertexIndicesAttr().Set(face_vertex_indices)
            plane_geom.GetNormalsAttr().Set(normals)
            
            print(f"   ✅ Created large white surface geometry at {white_surface_path}")
            
            # Create pure white material
            material_path = "/World/Materials/CustomWhiteSurface"
            if stage.GetPrimAtPath(material_path).IsValid():
                stage.RemovePrim(material_path)
                
            material = UsdShade.Material.Define(stage, material_path)
            
            # Create shader with maximum whiteness
            shader_path = f"{material_path}/WhiteShader"
            shader = UsdShade.Shader.Define(stage, shader_path)
            shader.CreateIdAttr("UsdPreviewSurface")
            
            # Ultra-white settings
            shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(1.0, 1.0, 1.0))
            shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.1, 0.1, 0.1))  # Slight glow
            shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.0)   # Mirror smooth
            shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)    # Non-metallic
            shader.CreateInput("specular", Sdf.ValueTypeNames.Float).Set(0.5)    # Some reflection
            shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(1.0)     # Fully opaque
            
            # Connect shader to material
            material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
            
            # Apply material to the plane
            plane_prim = plane_geom.GetPrim()
            UsdShade.MaterialBindingAPI(plane_prim).Bind(material.GetPrim())
            
            print(f"   ✅ Applied ultra-white material to custom surface")
            
            # Also disable the original ground plane grid
            self._hide_original_ground_plane_grid(stage)
            
            print("   🏆 CUSTOM WHITE SURFACE OVERRIDE COMPLETE!")
            return True
            
        except Exception as e:
            print(f"   ❌ Custom white surface creation failed: {e}")
            import traceback
            print(f"   Error details: {traceback.format_exc()}")
            return False
            
    def _hide_original_ground_plane_grid(self, stage):
        """Hide or modify the original ground plane to remove its grid pattern."""
        try:
            from pxr import UsdShade, Sdf, Gf
            
            # Try to find and modify the original ground plane
            ground_paths = ["/World/defaultGroundPlane", "/defaultGroundPlane"]
            
            for ground_path in ground_paths:
                ground_prim = stage.GetPrimAtPath(ground_path)
                if ground_prim.IsValid():
                    print(f"   🎭 Hiding/modifying original ground plane at {ground_path}")
                    
                    # Method 1: Make it invisible
                    try:
                        from pxr import UsdGeom
                        imageable = UsdGeom.Imageable(ground_prim)
                        imageable.MakeInvisible()
                        print(f"   ✅ Made original ground plane invisible")
                    except:
                        pass
                        
                    # Method 2: Apply white material over it too
                    try:
                        white_material_path = "/World/Materials/GroundOverride"
                        if stage.GetPrimAtPath(white_material_path).IsValid():
                            stage.RemovePrim(white_material_path)
                            
                        override_material = UsdShade.Material.Define(stage, white_material_path)
                        override_shader_path = f"{white_material_path}/Shader"
                        override_shader = UsdShade.Shader.Define(stage, override_shader_path)
                        override_shader.CreateIdAttr("UsdPreviewSurface")
                        
                        override_shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(1.0, 1.0, 1.0))
                        override_material.CreateSurfaceOutput().ConnectToSource(override_shader.ConnectableAPI(), "surface")
                        UsdShade.MaterialBindingAPI(ground_prim).Bind(override_material.GetPrim())
                        
                        print(f"   ✅ Applied override white material to original ground")
                    except Exception as e:
                        print(f"   ⚠️ Override material failed: {e}")
                        
        except Exception as e:
            print(f"   ⚠️ Hide original ground plane failed: {e}")

    def step_world(self, render: bool = True):
        """
        Executes a single simulation step.
        """
        if self.world is not None:
            self.world.step(render=render)
        else:
            print("⚠️ World not created, cannot execute simulation step.")
    
    def is_playing(self) -> bool:
        """Checks if the simulation is playing."""
        if self.world is not None:
            return self.world.is_playing()
        return False

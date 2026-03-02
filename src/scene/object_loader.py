# -*- coding: utf-8 -*-
"""
Object Loader - Manages the loading of objects into the scene.

"""

import os
import numpy as np
from typing import Dict, Any, List, Optional
import logging

# Isaac Sim imports
from isaacsim.core.api import World
from isaacsim.core.prims import RigidPrim
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.core.prims import SingleRigidPrim

import omni.usd
from pxr import Sdf, Gf, UsdGeom

from .random_generator import RandomPositionGenerator

# Virtual plate object class for placement detection when the actual USD is unavailable.
class VirtualPlateObject:
    """A virtual plate object for placement detection when the actual USD is not available."""
    def __init__(self, position, radius=0.1, height=0.02):
        self.position = np.array(position)
        self.radius = radius
        self.height = height
        self.name = "virtual_plate_object"
        print(f"Virtual plate object initialized: Position {self.position.tolist()}, Radius {self.radius}m, Height {self.height}m")

    def get_world_pose(self):
        """Returns the position and an identity quaternion."""
        return self.position, np.array([1.0, 0.0, 0.0, 0.0])  # Position and identity quaternion

    def set_world_pose(self, position, orientation=np.array([1.0, 0.0, 0.0, 0.0])):
        """Sets the world pose - supports position reset."""
        self.position = np.array(position)
        print(f"Virtual plate position updated: [{self.position[0]:.4f}, {self.position[1]:.4f}, {self.position[2]:.4f}]")

    def get_linear_velocity(self):
        """Returns a zero velocity vector, indicating it is stationary."""
        return np.array([0.0, 0.0, 0.0])

class ObjectLoader:
    """
    Object Loader
    Loads oranges and the plate into the scene, following the methodology of the original main script.
    """
    
    def __init__(self, config: Dict[str, Any], project_root: str):
        """
        Initializes the ObjectLoader.
        
        Args:
            config: Scene configuration.
            project_root: The root path of the project.
        """
        self.config = config
        self.project_root = project_root
        
        # Orange configuration (styled to look like different candies)
        oranges_config = config.get('scene', {}).get('oranges', {})
        self.orange_models = oranges_config.get('models', ["Orange001"])
        self.orange_usd_paths = oranges_config.get('usd_paths', [
            "assets/objects/Orange001/Orange001.usd"
        ])
        self.orange_count = oranges_config.get('count', 1)
        
        # Candy type configurations
        self.candy_types = oranges_config.get('candy_types', {})
        default_mass = oranges_config.get('physics', {}).get('mass', 0.007)
        
        # Print candy types being loaded
        print(f"<l Candy types configured:")
        for model, candy_info in self.candy_types.items():
            print(f"   {model} -> {candy_info.get('name', 'Unknown')} (mass: {candy_info.get('mass', default_mass)}kg)")
        
        # Plate configuration (styled to look like yellow bowl)
        plate_config = config.get('scene', {}).get('plate', {})
        self.plate_usd_path = plate_config.get('usd_path', 'assets/objects/Plate/Plate.usd')
        self.plate_position = plate_config.get('position', [0.25, -0.15, 0.1])
        self.plate_scale = plate_config.get('scale', 1.0)
        self.use_virtual_plate = plate_config.get('use_virtual', True)
        self.virtual_plate_config = plate_config.get('virtual_config', {})
        
        # Bowl styling info
        self.bowl_styling = plate_config.get('bowl_styling', {})
        
        # Table styling info  
        env_config = config.get('scene', {}).get('environment', {})
        self.table_styling = env_config.get('table_styling', {})
        
        # Random position generator
        generation_config = oranges_config.get('generation', {})
        self.position_generator = RandomPositionGenerator(generation_config)
        
        # Store loaded objects
        self.orange_objects = {}
        self.orange_reset_positions = {}
        self.plate_object = None
        
        print(f" Object Loader initialized.")
        print(f"   Number of candy objects: {self.orange_count}")
        print(f"   Orange models (candy-styled): {self.orange_models}")
        print(f"   Plate position (yellow bowl): {self.plate_position}")
        print(f"   Using virtual plate: {self.use_virtual_plate}")
        if self.bowl_styling:
            print(f"   Bowl color: {self.bowl_styling.get('color', 'default')}")
        if self.table_styling:
            print(f"   Table color: {self.table_styling.get('color', 'default')}")
    
    def load_orange(self, world: World, usd_path: str, prim_path: str, position: List[float], name: str, model_name: str, mass: float = 0.007):
        """
        Loads a single orange into the scene (styled to look like specific candy type).
        
        Args:
            model_name: The model name (e.g., "Orange001") to determine candy type
        """
        full_usd_path = os.path.join(self.project_root, usd_path)
        
        if not os.path.exists(full_usd_path):
            print(f"L Orange USD file not found: {full_usd_path}")
            return None
            
        try:
            # Get candy type info for this model
            candy_info = self.candy_types.get(model_name, {})
            candy_name = candy_info.get('name', 'Unknown Candy')
            candy_mass = candy_info.get('mass', mass)
            candy_color = candy_info.get('color', [1.0, 0.5, 0.0])  # Default orange
            
            print(f"=' Loading {candy_name} USD: {full_usd_path}")
            
            # Step 1: Load the USD to the stage
            add_reference_to_stage(usd_path=full_usd_path, prim_path=prim_path)
            print(f" {candy_name} USD loaded to stage: {prim_path}")
            
            # Step 2: Add as a SingleRigidPrim
            orange = world.scene.add(
                SingleRigidPrim(
                    prim_path=prim_path,
                    name=name,
                    position=position,
                    mass=candy_mass
                )
            )
            
            # Step 3: Apply candy-specific material if possible
            if hasattr(self, '_apply_candy_material'):
                self._apply_candy_material(prim_path, candy_info)
            
            print(f" {candy_name} loaded successfully: {name} at position {position} with mass {candy_mass}kg")
            print(f"   Color: RGB{tuple(candy_color)}")
            
            return orange
            
        except Exception as e:
            print(f"L Failed to load {candy_name} {name}: {e}")
            import traceback
            print(f"Detailed error: {traceback.format_exc()}")
            return None
    
    def load_oranges(self, world: World) -> Dict[str, Any]:
        """
        Loads all candy objects (using orange USD files) into the scene.
        """
        try:
            print(f"� Loading {self.orange_count} candy objects...")
            
            # Generate random position for single candy object
            print(f"<� Generating 1 random position for candy object...")
            random_positions = self.position_generator.generate_random_orange_positions(1)
            
            # Only one candy position
            candy1_reset_pos = random_positions[0] if len(random_positions) > 0 else [0.2, 0.1, 0.1]
            
            positions = [candy1_reset_pos]
            
            # Print the single candy position
            model_name = self.orange_models[0]
            candy_info = self.candy_types.get(model_name, {})
            candy_name = candy_info.get('name', 'Candy 1')
            print(f"<l {candy_name} random position: [{positions[0][0]:.3f}, {positions[0][1]:.3f}, {positions[0][2]:.3f}]")
            
            # Load the single candy object
            orange_objects = {}
            orange_reset_positions = {}
            
            usd_path = self.orange_usd_paths[0]
            model_name = self.orange_models[0]
            prim_path = "/World/orange1"
            object_name = "orange1_object"
            position = positions[0]
            
            # Get candy-specific mass
            candy_info = self.candy_types.get(model_name, {})
            default_mass = 0.007  # Default candy mass
            candy_mass = candy_info.get('mass', default_mass)
            
            # Load using the helper function
            orange = self.load_orange(world, usd_path, prim_path, position, object_name, model_name, candy_mass)
            
            if orange is not None:
                orange_objects[object_name] = orange
                orange_reset_positions[object_name] = position
                candy_name = candy_info.get('name', 'Candy 1')
                print(f" {candy_name} loaded: {object_name}")
            self.orange_objects = orange_objects
            self.orange_reset_positions = orange_reset_positions
            
            return {
                'objects': orange_objects,
                'reset_positions': orange_reset_positions
            }
            
        except Exception as e:
            print(f"L Failed to load candy objects: {e}")
            import traceback
            print(f"Detailed error: {traceback.format_exc()}")
            return {'objects': {}, 'reset_positions': {}}
    
    def load_plate(self, world: World) -> Optional[Any]:
        """
        Loads the plate into the scene.
        """
        try:
            print("=� Loading the plate...")
            
            # Create a virtual plate object for placement detection.
            print("=' Creating a virtual plate object for placement detection...")
            
            # Use plate position from the configuration.
            virtual_config = self.virtual_plate_config
            plate_center = virtual_config.get('position', [0.25, -0.15, 0.005])
            plate_radius = virtual_config.get('radius', 0.1)
            plate_height = virtual_config.get('height', 0.02)
            
            plate_object = VirtualPlateObject(plate_center, plate_radius, plate_height)
            
            print(f" Virtual plate object created: Position {plate_center}, Radius {plate_radius}m, Height {plate_height}m")
            
            # If the actual plate USD file exists, attempt to load it.
            full_plate_usd_path = os.path.join(self.project_root, self.plate_usd_path)
            
            if os.path.exists(full_plate_usd_path):
                try:
                    print(f"=' Attempting to load actual plate USD: {full_plate_usd_path}")
                    
                    # Step 1: Load the USD to the stage.
                    add_reference_to_stage(usd_path=full_plate_usd_path, prim_path="/World/plate")
                    print(" Plate USD loaded to stage.")
                    
                    # Step 2: Set the scale.
                    stage = omni.usd.get_context().get_stage()
                    plate_prim = stage.GetPrimAtPath("/World/plate")
                    if plate_prim.IsValid():
                        xformable = UsdGeom.Xformable(plate_prim)
                        existing_ops = xformable.GetOrderedXformOps()
                        scale_op = None
                        for op in existing_ops:
                            if op.GetOpName() == "xformOp:scale":
                                scale_op = op
                                break
                        
                        if scale_op is None:
                            scale_op = xformable.AddScaleOp()
                        
                        scale_op.Set(Gf.Vec3f(self.plate_scale, self.plate_scale, self.plate_scale))
                        print(f" Plate scale set to: {self.plate_scale}")
                    
                    # Step 3: Add as a SingleRigidPrim.
                    actual_plate = world.scene.add(
                        SingleRigidPrim(
                            prim_path="/World/plate",
                            name="plate_object",
                            position=plate_center,  # Use the corrected position
                            mass=0.5
                        )
                    )
                    
                    # If the actual plate is loaded successfully, use it.
                    plate_object = actual_plate
                    
                    print(f" Actual plate loaded: Position {plate_center}, Scale {self.plate_scale}")
                    
                except Exception as e:
                    print(f"L Failed to load actual plate: {e}")
                    import traceback
                    print(f"Detailed error: {traceback.format_exc()}")
                    print("= Continuing with the virtual plate object.")
            else:
                print(f"� Plate USD file not found: {full_plate_usd_path}")
                print("= Using virtual plate object for placement detection.")
            
            self.plate_object = plate_object
            return plate_object
            
        except Exception as e:
            print(f"L Failed to load plate: {e}")
            import traceback
            print(f"Detailed error: {traceback.format_exc()}")
            return None
    
    def _apply_candy_material(self, prim_path: str, candy_info: Dict):
        """
        Applies candy-specific material to the loaded object.
        
        Args:
            prim_path: Path to the prim
            candy_info: Candy configuration dictionary
        """
        try:
            import omni.usd
            from pxr import Sdf, Gf, UsdShade
            
            stage = omni.usd.get_context().get_stage()
            prim = stage.GetPrimAtPath(prim_path)
            
            if not prim.IsValid():
                print(f"� Cannot apply material: Prim not found at {prim_path}")
                return
                
            candy_name = candy_info.get('name', 'Unknown')
            color = candy_info.get('color', [1.0, 0.5, 0.0])
            roughness = candy_info.get('roughness', 0.1)
            metallic = candy_info.get('metallic', 0.2)
            
            # Create material path
            material_name = f"{candy_name.replace(' ', '_')}_Material"
            material_prim_path = f"/World/Looks/{material_name}"
            
            # Create or get material
            looks_prim = stage.GetPrimAtPath("/World/Looks")
            if not looks_prim.IsValid():
                looks_prim = stage.DefinePrim("/World/Looks", "Scope")
                
            material_prim = stage.DefinePrim(material_prim_path, "Material")
            material = UsdShade.Material(material_prim)
            
            # Create shader
            shader_path = material_prim_path + "/Shader"
            shader_prim = stage.DefinePrim(shader_path, "Shader")
            shader = UsdShade.Shader(shader_prim)
            shader.CreateIdAttr("UsdPreviewSurface")
            
            # Set material properties
            diffuse_input = shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
            diffuse_input.Set(Gf.Vec3f(*color))
            
            roughness_input = shader.CreateInput("roughness", Sdf.ValueTypeNames.Float)
            roughness_input.Set(roughness)
            
            metallic_input = shader.CreateInput("metallic", Sdf.ValueTypeNames.Float)
            metallic_input.Set(metallic)
            
            # Connect shader to material
            material_surface = material.CreateSurfaceOutput()
            material_surface.ConnectToSource(shader.ConnectableAPI(), "surface")
            
            # Bind material to object
            UsdShade.MaterialBindingAPI(prim).Bind(material)
            
            print(f" Applied {candy_name} material to {prim_path}")
            
        except ImportError:
            print(f"� USD/Omniverse not available - skipping material application for {candy_info.get('name', 'candy')}")
        except Exception as e:
            print(f"L Failed to apply material for {candy_info.get('name', 'candy')}: {e}")

    def apply_all_materials(self):
        """
        Applies materials to all loaded objects (candies, bowl, table).
        """
        print("\n<� Applying candy and styling materials...")
        
        # Apply candy materials
        for object_name, orange_obj in self.orange_objects.items():
            if orange_obj and hasattr(orange_obj, 'prim_path'):
                # Determine which candy type this is
                object_index = int(object_name.replace('orange', '').replace('_object', '')) - 1
                if object_index < len(self.orange_models):
                    model_name = self.orange_models[object_index]
                    candy_info = self.candy_types.get(model_name, {})
                    if candy_info:
                        self._apply_candy_material(orange_obj.prim_path, candy_info)
        
        # Apply bowl material
        if self.plate_object and hasattr(self.plate_object, 'prim_path') and self.bowl_styling:
            self._apply_bowl_material(self.plate_object.prim_path)
        
        # Apply table material
        if self.table_styling:
            self._apply_table_material()
            
        print(" All materials applied!")

    def _apply_bowl_material(self, prim_path: str):
        """Applies yellow bowl material to plate."""
        bowl_info = {
            'name': 'Yellow Bowl',
            'color': self.bowl_styling.get('color', [1.0, 1.0, 0.0]),
            'roughness': self.bowl_styling.get('roughness', 0.2),
            'metallic': self.bowl_styling.get('metallic', 0.0)
        }
        self._apply_candy_material(prim_path, bowl_info)
        
    def _apply_table_material(self):
        """Applies white table material to ground plane."""
        try:
            import omni.usd
            stage = omni.usd.get_context().get_stage()
            ground_prim_path = "/World/defaultGroundPlane"
            
            table_info = {
                'name': 'White Table',
                'color': self.table_styling.get('color', [1.0, 1.0, 1.0]),
                'roughness': self.table_styling.get('roughness', 0.3),
                'metallic': self.table_styling.get('metallic', 0.0)
            }
            self._apply_candy_material(ground_prim_path, table_info)
        except Exception as e:
            print(f"L Failed to apply table material: {e}")

    def regenerate_orange_positions(self, world: World):
        """
        Regenerates random positions for the oranges.
        """
        if not self.orange_objects:
            print("� No orange objects to reposition.")
            return
        
        print("= Regenerating orange positions...")
        
        # Generate new orange positions.
        print("<� Generating new positions for the oranges.")
        new_positions = self.position_generator.generate_random_orange_positions(len(self.orange_objects))
        
        # Move oranges to their new positions.
        repositioned_count = 0
        for i, (name, orange_obj) in enumerate(self.orange_objects.items()):
            if i < len(new_positions) and orange_obj is not None:
                try:
                    new_pos = new_positions[i]
                    orange_obj.set_world_pose(
                        position=np.array(new_pos),
                        orientation=np.array([1.0, 0.0, 0.0, 0.0])
                    )
                    orange_obj.set_linear_velocity(np.array([0.0, 0.0, 0.0]))
                    orange_obj.set_angular_velocity(np.array([0.0, 0.0, 0.0]))
                    
                    # Update the reset position.
                    self.orange_reset_positions[name] = new_pos
                    
                    print(f"{name} moved to new random position: [{new_pos[0]:.3f}, {new_pos[1]:.3f}, {new_pos[2]:.3f}]")
                    repositioned_count += 1
                except Exception as e:
                    print(f"L Failed to update position for {name}: {e}")
        
        print(f"<� Random repositioning complete. Successfully moved {repositioned_count} oranges.")
    
    def get_orange_objects(self) -> Dict[str, Any]:
        """Gets the dictionary of orange objects."""
        return self.orange_objects
    
    def get_orange_reset_positions(self) -> Dict[str, List[float]]:
        """Gets the dictionary of orange reset positions."""
        return self.orange_reset_positions
    
    def get_plate_object(self) -> Any:
        """Gets the plate object."""
        return self.plate_object
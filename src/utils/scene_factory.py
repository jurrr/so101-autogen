# -*- coding: utf-8 -*-
"""
Scene Factory Module
Provides functionality for constructing scenes, extracted from the main script.
"""

import os
import numpy as np
from .config_utils import ConfigManager


class SceneFactory:
    """Scene Factory Class"""
    
    def __init__(self, project_root, world):
        """Initializes the SceneFactory.
        
        Args:
            project_root (str): The root path of the project.
            world: The Isaac Sim World object.
        """
        self.project_root = project_root
        self.world = world
        self.config_manager = ConfigManager(project_root)
    
    def create_orange_plate_scene(self, scene_config):
        """Creates the orange and plate scene.
        
        Args:
            scene_config (dict): The scene configuration.
            
        Returns:
            dict: A dictionary of scene objects.
        """
        print("\n Creating the orange and plate scene...")
        scene_objects = {}
        
        # Get configuration parameters
        plate_config = self.config_manager.get_plate_config(scene_config)
        orange_config = self.config_manager.get_orange_config(scene_config)
        
        # Extract parameters
        plate_position = plate_config["position"]
        plate_radius = plate_config["radius"]
        plate_height = plate_config["height"]
        orange_count = orange_config["count"]
        orange_mass = orange_config["mass"]
        orange_usd_paths = orange_config["usd_paths"]
        x_range = orange_config["x_range"]
        y_range = orange_config["y_range"]
        z_drop_height = orange_config["z_drop_height"]
        orange_radius = orange_config["orange_radius"]
        min_distance = orange_config["min_distance"]
        max_attempts = orange_config["max_attempts"]
        
        print(f"Configuration parameters loaded:")
        print(f"   Plate Position: {plate_position}")
        print(f"   Plate Radius: {plate_radius}m, Height: {plate_height}m")
        print(f"   Number of Oranges: {orange_count}, Mass: {orange_mass}kg")
        print(f"   Orange Generation Range: X{x_range}, Y{y_range}, Z={z_drop_height}")
        print(f"   Min Distance: {min_distance}m, Max Attempts: {max_attempts}")
        
        # Initialize the smart placement system
        from src.scene.smart_placement import SmartPlacement
        
        smart_placement = SmartPlacement(
            config_path="config/scene_config.yaml",
            plate_position=plate_position
        )
        
        # Set plate position
        print("Setting plate position...")
        plate_center = plate_position.copy()
        print(f"Using plate position from configuration file: {plate_center}")
        
        # Generate orange positions (avoiding the plate)
        print("Generating orange positions (avoiding the plate)...")
        smart_placement.clear_placement_history()
        plate_object_info = {
            "position": np.array(plate_center),
            "type": "plate", 
            "name": "plate_object"
        }
        smart_placement.placed_objects.append(plate_object_info)
        print(f"Plate avoidance zone: Position {plate_center}, Radius {smart_placement.object_sizes['plate']['radius']}m")
        
        # Generate orange positions
        orange_types = ["orange"] * orange_count
        orange_names = [f"orange{i+1}_object" for i in range(orange_count)]
        orange_positions = smart_placement.generate_safe_positions(orange_types, orange_names)
        
        # Combine all positions
        safe_positions = orange_positions + [np.array(plate_center)]
        print(f"Generated {len(orange_positions)} orange positions + 1 plate position.")
        
        # Load orange objects
        orange_objects_loaded = self._load_orange_objects(
            orange_count, orange_usd_paths, safe_positions, orange_mass, scene_config
        )
        
        # Add oranges to the scene objects dictionary
        for name, obj in orange_objects_loaded.items():
            scene_objects[name] = obj
        
        # Load the plate object
        plate_obj = self._load_plate_object(plate_center, plate_radius, plate_height)
        if plate_obj:
            scene_objects["plate_object"] = plate_obj
        
        # Apply candy materials and styling
        print("\nApplying candy materials and styling...")
        self._apply_candy_materials(scene_objects, scene_config)
        
        print(f"Orange and plate scene created: {len(scene_objects)} objects.")
        for name in scene_objects.keys():
            print(f"    - {name}")
        
        return scene_objects, orange_positions, plate_center
    
    def _load_orange_objects(self, orange_count, orange_usd_paths, safe_positions, orange_mass, scene_config):
        """Loads the orange objects with candy-specific masses.
        
        Args:
            orange_count (int): The number of oranges.
            orange_usd_paths (list): A list of paths to the orange USD files.
            safe_positions (list): A list of safe positions.
            orange_mass (float): The default mass of the oranges.
            scene_config (dict): Scene configuration containing candy types.
            
        Returns:
            dict: A dictionary of orange objects.
        """
        orange_objects_loaded = {}
        
        # Get candy type configurations
        oranges_config = scene_config.get('scene', {}).get('oranges', {})
        candy_types = oranges_config.get('candy_types', {})
        orange_models = oranges_config.get('models', ["Orange001", "Orange002", "Orange003"])
        
        for i in range(orange_count):
            if i < len(safe_positions) - 1:  # Subtract 1 because the last position is the plate
                usd_path = f"{self.project_root}/{orange_usd_paths[i]}" if i < len(orange_usd_paths) else f"{self.project_root}/{orange_usd_paths[0]}"
                prim_path = f"/World/orange{i+1}"
                scene_name = f"orange{i+1}_object"
                
                # Get candy-specific mass
                model_name = orange_models[i] if i < len(orange_models) else f"Orange00{i+1}"
                candy_info = candy_types.get(model_name, {})
                candy_mass = candy_info.get('mass', orange_mass)
                candy_name = candy_info.get('name', f'Candy {i+1}')
                
                orange_obj = self._load_single_orange(usd_path, prim_path, safe_positions[i].tolist(), scene_name, candy_mass)
                if orange_obj:
                    orange_objects_loaded[scene_name] = orange_obj
                    print(f"{candy_name} loaded successfully: Position {safe_positions[i].tolist()}, Mass {candy_mass}kg")
        
        return orange_objects_loaded
    
    def _load_single_orange(self, usd_path, prim_path, position, name, mass=0.15):
        """Loads a single orange.
        
        Args:
            usd_path (str): The path to the USD file.
            prim_path (str): The prim path.
            position (list): The position.
            name (str): The name of the object.
            mass (float): The mass.
            
        Returns:
            The orange object or None.
        """
        if not os.path.exists(usd_path):
            print(f"Orange USD file not found: {usd_path}")
            return None
            
        try:
            print(f"Loading orange USD: {os.path.basename(usd_path)}")
            
            # Step 1: Load the USD to the stage
            from isaacsim.core.utils.stage import add_reference_to_stage
            add_reference_to_stage(usd_path=usd_path, prim_path=prim_path)
            print(f"Orange USD loaded to stage: {prim_path}")
            
            # Step 2: Create a physics object using SingleRigidPrim
            from isaacsim.core.prims import SingleRigidPrim
            
            orange = self.world.scene.add(
                SingleRigidPrim(
                    prim_path=prim_path,
                    name=name,
                    position=position,
                    mass=mass
                )
            )
            
            print(f"Orange loaded: {name} at position {position} with mass {mass}kg")
            return orange
            
        except Exception as e:
            print(f"Failed to load orange {name}: {e}")
            return None
    
    def _load_plate_object(self, plate_center, plate_radius, plate_height):
        """Loads the plate object.
        
        Args:
            plate_center (list): The center position of the plate.
            plate_radius (float): The radius of the plate.
            plate_height (float): The height of the plate.
            
        Returns:
            The plate object or a virtual plate object.
        """
        print("Loading plate USD model...")
        print(f"Using plate position: {plate_center}")
        
        plate_usd_path = f"{self.project_root}/assets/objects/Plate/Plate.usd"
        
        if os.path.exists(plate_usd_path):
            try:
                print(f"Loading plate USD: {os.path.basename(plate_usd_path)}")
                from isaacsim.core.utils.stage import add_reference_to_stage
                add_reference_to_stage(usd_path=plate_usd_path, prim_path="/World/plate")
                print("Plate USD loaded to stage: /World/plate")
                
                # Create a physics object for the plate using SingleRigidPrim
                from isaacsim.core.prims import SingleRigidPrim
                plate = self.world.scene.add(
                    SingleRigidPrim(
                        prim_path="/World/plate",
                        name="plate_object",
                        position=plate_center,
                        mass=0.2  # 200g mass for the plate
                    )
                )
                print(f"Plate loaded: plate_object at position {plate_center} with mass 0.2kg")
                return plate
                
            except Exception as e:
                print(f"Failed to load plate: {e}")
                print("Using a virtual plate object as a fallback...")
        else:
            print(f"Plate USD file not found: {plate_usd_path}")
            print("Using a virtual plate object as a fallback...")
            
        # Create a virtual plate object
        return self._create_virtual_plate(plate_center, plate_radius, plate_height)
    
    def _create_virtual_plate(self, position, radius=0.1, height=0.02):
        """Creates a virtual plate object.
        
        Args:
            position (list): The position.
            radius (float): The radius.
            height (float): The height.
            
        Returns:
            A virtual plate object.
        """
        class VirtualPlateObject:
            def __init__(self, position, radius=0.1, height=0.02):
                self.position = np.array(position)
                self.radius = radius
                self.height = height
            
            def get_world_pose(self):
                return self.position, np.array([1, 0, 0, 0])  # Position and identity quaternion
            
            def set_world_pose(self, position, orientation=None):
                self.position = np.array(position)
                print(f"Virtual plate position updated: [{self.position[0]:.4f}, {self.position[1]:.4f}, {self.position[2]:.4f}]")
            
            def get_linear_velocity(self):
                return np.array([0, 0, 0])  # Stationary state
        
        virtual_plate = VirtualPlateObject(position, radius=radius, height=height)
        print(f"Virtual plate object created at position: {position}")
        return virtual_plate
    
    def _apply_candy_materials(self, scene_objects, scene_config):
        """
        Applies candy materials and styling to the loaded objects.
        
        Args:
            scene_objects (dict): Dictionary of loaded scene objects
            scene_config (dict): Scene configuration containing candy types and styling
        """
        try:
            print("Applying candy transformations...")
            
            # Check if Isaac Sim is ready for material operations
            try:
                import omni.usd
                stage = omni.usd.get_context().get_stage()
                stage_ready = stage is not None
                print(f"   🔧 Isaac Sim stage ready: {stage_ready}")
                if not stage_ready:
                    print("   ⚠️  USD stage not available - materials may not be applied")
            except ImportError:
                print("   ⚠️  USD libraries not loaded - this is expected during early initialization")
                print("   ℹ️  Materials will be applied when Isaac Sim is fully loaded")
            
            # Get candy type configurations
            oranges_config = scene_config.get('scene', {}).get('oranges', {})
            candy_types = oranges_config.get('candy_types', {})
            
            print(f"   Debug: Found candy types: {list(candy_types.keys())}")
            
            # Get styling configurations
            plate_config = scene_config.get('scene', {}).get('plate', {})
            bowl_styling = plate_config.get('bowl_styling', {})
            
            # Look for environment config in placement section (where it actually is)
            env_config = scene_config.get('placement', {}).get('environment', {})
            table_styling = env_config.get('table_styling', {})
            
            print(f"   Debug: Bowl styling: {bowl_styling}")
            print(f"   Debug: Table styling: {table_styling}")
            
            # Apply candy materials to orange objects
            orange_models = oranges_config.get('models', ["Orange001", "Orange002", "Orange003"])
            print(f"   Debug: Orange models: {orange_models}")
            
            materials_applied = 0
            materials_attempted = 0
            
            for object_name, obj in scene_objects.items():
                print(f"   Debug: Processing object {object_name}, has prim_path: {hasattr(obj, 'prim_path')}")
                
                if "orange" in object_name.lower() and hasattr(obj, 'prim_path'):
                    materials_attempted += 1
                    # Determine candy type based on object index
                    object_index = int(object_name.replace('orange', '').replace('_object', '')) - 1
                    if object_index < len(orange_models):
                        model_name = orange_models[object_index]
                        candy_info = candy_types.get(model_name, {})
                        candy_name = candy_info.get('name', f'Candy {object_index+1}')
                        
                        print(f"   🍬 Transforming {object_name} → {candy_name}")
                        print(f"       Prim path: {obj.prim_path}")
                        print(f"       Candy info: {candy_info}")
                        
                        if candy_info:  # Only apply if we have candy info
                            success = self._apply_material_to_object(obj.prim_path, candy_info, candy_name)
                            if success:
                                materials_applied += 1
                        else:
                            print(f"       ❌ No candy info found for {model_name}")
                
                elif "plate" in object_name.lower():
                    if hasattr(obj, 'prim_path') and bowl_styling:
                        materials_attempted += 1
                        bowl_info = {
                            'name': 'Yellow Bowl',
                            'color': bowl_styling.get('color', [1.0, 1.0, 0.0]),
                            'roughness': bowl_styling.get('roughness', 0.2),
                            'metallic': bowl_styling.get('metallic', 0.0)
                        }
                        print(f"   🥣 Transforming plate → Yellow Bowl")
                        print(f"       Prim path: {obj.prim_path}")
                        success = self._apply_material_to_object(obj.prim_path, bowl_info, "Yellow_Bowl")
                        if success:
                            materials_applied += 1
                    else:
                        print(f"   ℹ️  Plate object {object_name} - prim_path: {hasattr(obj, 'prim_path')}, bowl_styling: {bool(bowl_styling)}")
            
            # Apply table styling to ground
            if table_styling:
                materials_attempted += 1
                table_info = {
                    'name': 'White Table',
                    'color': table_styling.get('color', [1.0, 1.0, 1.0]),
                    'roughness': table_styling.get('roughness', 0.3),
                    'metallic': table_styling.get('metallic', 0.0)
                }
                print(f"   🪑 Transforming ground → White Table")
                success = self._apply_material_to_ground(table_info)
                if success:
                    materials_applied += 1
            
            print(f"🎨 Candy transformations completed!")
            print(f"   📊 Materials attempted: {materials_attempted}")
            print(f"   ✅ Materials successfully applied: {materials_applied}")
            print(f"   ❌ Materials failed: {materials_attempted - materials_applied}")
            
            if materials_applied == 0:
                print("🚨 WARNING: No materials were successfully applied!")
                print("   This could be because:")
                print("   - Isaac Sim is not fully loaded yet")
                print("   - USD stage is not ready")
                print("   - Object prim paths are incorrect")
                print("   - Material binding failed")
                print("   🔄 Try waiting a few seconds and running the script again")
            elif materials_applied < materials_attempted:
                print("⚠️  Some materials failed to apply - check the detailed error messages above")
            else:
                print("🎉 All materials applied successfully!")
                print("   If you don't see visual changes, try:")
                print("   - Pressing 'G' to cycle lighting modes in Isaac Sim")
                print("   - Rotating the viewport to refresh rendering")
                print("   - Checking that Lit mode is enabled (not Unlit)")
                print("   - For WHITE TABLE: Try orbiting camera to look down at ground plane")
                print("   - For WHITE TABLE: Check viewport lighting settings (may appear gray in some lighting)")
                print("   - Press the '4' key to switch to perspective view if in orthographic mode")
            
        except Exception as e:
            print(f"❌ Failed to apply some candy materials: {e}")
            print("   Objects will appear with default materials")
            import traceback
            print(f"   Error details: {traceback.format_exc()}")
    
    def _apply_material_to_object(self, prim_path, material_info, material_name):
        """
        Applies material to a specific object.
        
        Args:
            prim_path (str): Path to the object prim
            material_info (dict): Material configuration
            material_name (str): Name for the material
        """
        try:
            # Try to import USD modules - these are only available when Isaac Sim is running
            import omni.usd
            from pxr import Sdf, Gf, UsdShade
            
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                print(f"     ❌ No USD stage available - Isaac Sim may not be fully initialized")
                return
                
            prim = stage.GetPrimAtPath(prim_path)
            
            if not prim.IsValid():
                print(f"     ❌ Prim not found: {prim_path}")
                return
                
            color = material_info.get('color', [1.0, 0.5, 0.0])
            roughness = material_info.get('roughness', 0.1)
            metallic = material_info.get('metallic', 0.2)
            
            print(f"     🎨 Creating material for {material_name} with color {color}")
            
            # Create material path INSIDE the object (correct hierarchy)
            safe_name = material_name.replace(' ', '_').replace('-', '_')
            object_looks_path = f"{prim_path}/Looks"
            material_prim_path = f"{object_looks_path}/{safe_name}_Material"
            
            print(f"     📁 Material path: {material_prim_path}")
            
            # Create or get object's Looks scope
            looks_prim = stage.GetPrimAtPath(object_looks_path)
            if not looks_prim.IsValid():
                looks_prim = stage.DefinePrim(object_looks_path, "Scope")
                print(f"     ✅ Created Looks scope: {object_looks_path}")
            else:
                print(f"     ♻️  Using existing Looks scope: {object_looks_path}")
                
            # Remove existing material if it exists
            existing_material = stage.GetPrimAtPath(material_prim_path)
            if existing_material.IsValid():
                stage.RemovePrim(material_prim_path)
                print(f"     🗑️  Removed existing material: {material_prim_path}")
                
            material_prim = stage.DefinePrim(material_prim_path, "Material")
            material = UsdShade.Material(material_prim)
            
            # Create shader inside the object's material
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
            
            # Bind material to object (and its children)
            binding_api = UsdShade.MaterialBindingAPI.Apply(prim)
            binding_api.Bind(material)
            
            # Also try to bind to visual/mesh children if they exist
            materials_bound = self._bind_material_to_children(stage, prim_path, material)
            
            print(f"     ✅ Applied {material_name} material (RGB: {color}) to {prim_path}")
            print(f"     🔗 Material bindings: {materials_bound + 1} objects")
            
            return True
            
        except ImportError as e:
            print(f"     ❌ USD libraries not available for {material_name}: {e}")
            print(f"     ℹ️  This is expected if Isaac Sim is not fully loaded yet")
            return False
        except Exception as e:
            print(f"     ❌ Failed to apply {material_name} material: {e}")
            import traceback
            print(f"     📋 Error details: {traceback.format_exc()}")
            return False
    
    def _bind_material_to_children(self, stage, object_path, material):
        """
        Bind material to visual/mesh children of an object.
        
        Args:
            stage: USD stage
            object_path (str): Path to the parent object
            material: UsdShade.Material to bind
            
        Returns:
            int: Number of children the material was bound to
        """
        bound_count = 0
        try:
            from pxr import UsdShade
            
            # First try to find the actual model path within the object
            object_prim = stage.GetPrimAtPath(object_path)
            if not object_prim.IsValid():
                return bound_count
                
            # Look for the actual model (e.g., Orange001 inside orange1)
            model_paths = []
            for child in object_prim.GetChildren():
                child_path = str(child.GetPath())
                if any(name in child_path for name in ['Orange', 'Plate', 'Model', 'Mesh']):
                    model_paths.append(child_path)
                    print(f"       🔍 Found model path: {child_path}")
            
            # Common child paths where visuals might be
            visual_paths = []
            for model_path in model_paths:
                visual_paths.extend([
                    f"{model_path}/Visuals",
                    f"{model_path}/visuals", 
                    f"{model_path}/mesh",
                    f"{model_path}/Mesh",
                    f"{model_path}/Looks",
                    model_path  # The model itself
                ])
            
            # Also try direct paths from the object
            visual_paths.extend([
                f"{object_path}/Visuals",
                f"{object_path}/visuals", 
                f"{object_path}/mesh",
                f"{object_path}/Mesh"
            ])
            
            for visual_path in visual_paths:
                visual_prim = stage.GetPrimAtPath(visual_path)
                if visual_prim.IsValid():
                    try:
                        binding_api = UsdShade.MaterialBindingAPI.Apply(visual_prim)
                        binding_api.Bind(material)
                        bound_count += 1
                        print(f"       ✅ Material bound to: {visual_path}")
                    except Exception as e:
                        print(f"       ⚠️  Failed to bind to {visual_path}: {e}")
                        
                    # Also bind to any mesh children
                    for child_prim in visual_prim.GetChildren():
                        if child_prim.IsValid():
                            try:
                                binding_api = UsdShade.MaterialBindingAPI.Apply(child_prim)
                                binding_api.Bind(material)
                                bound_count += 1
                                print(f"       ✅ Material bound to child: {child_prim.GetPath()}")
                            except Exception as e:
                                print(f"       ⚠️  Failed to bind to child {child_prim.GetPath()}: {e}")
            
            return bound_count
            
        except Exception as e:
            print(f"       ❌ Error binding to children: {e}")
            return bound_count
    
    def _apply_material_to_ground(self, material_info):
        """
        Applies material to the ground plane.
        
        Args:
            material_info (dict): Material configuration for the ground
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import omni.usd
            stage = omni.usd.get_context().get_stage()
            ground_prim_path = "/World/defaultGroundPlane"
            
            ground_prim = stage.GetPrimAtPath(ground_prim_path)
            if ground_prim.IsValid():
                print(f"     🪑 Applying table material to: {ground_prim_path}")
                return self._apply_material_to_object(ground_prim_path, material_info, "White_Table")
            else:
                print(f"     ❌ Ground plane not found at: {ground_prim_path}")
                return False
                
        except ImportError as e:
            print(f"     ❌ USD libraries not available for table material: {e}")
            return False
        except Exception as e:
            print(f"     ❌ Failed to apply table material: {e}")
            return False


# Compatibility function to maintain the same interface as the main script.
def create_orange_plate_scene(project_root, world, scene_config):
    """Compatibility function."""
    factory = SceneFactory(project_root, world)
    return factory.create_orange_plate_scene(scene_config)

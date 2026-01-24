#!/usr/bin/env python3
"""
Convert Orange001 from sphere to cube.

This script modifies the Orange001.usd file to replace the sphere mesh
with a cube mesh, suitable for pick-and-place operations.

Usage:
    python convert_orange1_to_cube.py
    
Or run within Isaac Sim Python environment:
    /path/to/isaac-sim/python.sh convert_orange1_to_cube.py
"""

import os
import shutil
from pxr import Usd, UsdGeom, Gf, Vt

def backup_original(usd_path):
    """Create a backup of the original USD file."""
    backup_path = usd_path.replace('.usd', '_sphere_backup.usd')
    if not os.path.exists(backup_path):
        shutil.copy2(usd_path, backup_path)
        print(f"✅ Created backup: {backup_path}")
    else:
        print(f"ℹ️ Backup already exists: {backup_path}")
    return backup_path

def create_cube_mesh(stage, prim_path, size=0.05, width=None, depth=None, height=None, rotation_z_degrees=0):
    """
    Create a cube mesh at the specified prim path.
    
    Args:
        stage: USD stage
        prim_path: Path where the cube should be created
        size: Default size of the cube (half-extent) - used if width/depth/height not specified
        width: Width of the cube (X dimension, half-extent). If None, uses size
        depth: Depth of the cube (Y dimension, half-extent). If None, uses size
        height: Height of the cube (Z dimension, half-extent). If None, uses size
        rotation_z_degrees: DEPRECATED - rotation is now applied at the transform level, not vertices
    
    Returns:
        UsdGeom.Mesh: The created cube mesh
    """
    import math
    
    # Define cube dimensions (half-extents)
    # If custom dimensions provided, use them; otherwise use uniform size
    sx = width if width is not None else size   # X dimension (width)
    sy = depth if depth is not None else size   # Y dimension (depth)
    sz = height if height is not None else size # Z dimension (height)
    
    # Define cube vertices (8 corners) - NO rotation applied to vertices
    # Rotation is handled by USD transform operations instead
    points = [
        (-sx, -sy, -sz),  # 0: bottom-back-left
        ( sx, -sy, -sz),  # 1: bottom-back-right
        ( sx,  sy, -sz),  # 2: bottom-front-right
        (-sx,  sy, -sz),  # 3: bottom-front-left
        (-sx, -sy,  sz),  # 4: top-back-left
        ( sx, -sy,  sz),  # 5: top-back-right
        ( sx,  sy,  sz),  # 6: top-front-right
        (-sx,  sy,  sz),  # 7: top-front-left
    ]
    
    # Define faces (6 faces, each with 4 vertices)
    # Counter-clockwise winding order for outward-facing normals
    face_vertex_counts = [4, 4, 4, 4, 4, 4]
    face_vertex_indices = [
        # Bottom face (z = -s)
        0, 1, 2, 3,
        # Top face (z = +s)
        4, 7, 6, 5,
        # Back face (y = -s)
        0, 4, 5, 1,
        # Front face (y = +s)
        3, 2, 6, 7,
        # Left face (x = -s)
        0, 3, 7, 4,
        # Right face (x = +s)
        1, 5, 6, 2,
    ]
    
    # Create the mesh prim
    mesh = UsdGeom.Mesh.Define(stage, prim_path)
    
    # Set the mesh data
    mesh.GetPointsAttr().Set(points)
    mesh.GetFaceVertexCountsAttr().Set(face_vertex_counts)
    mesh.GetFaceVertexIndicesAttr().Set(face_vertex_indices)
    
    # Compute and set normals for smooth shading
    normals = [
        # Bottom face normals
        (0, 0, -1), (0, 0, -1), (0, 0, -1), (0, 0, -1),
        # Top face normals
        (0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1),
        # Back face normals
        (0, -1, 0), (0, -1, 0), (0, -1, 0), (0, -1, 0),
        # Front face normals
        (0, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0),
        # Left face normals
        (-1, 0, 0), (-1, 0, 0), (-1, 0, 0), (-1, 0, 0),
        # Right face normals
        (1, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0),
    ]
    mesh.GetNormalsAttr().Set(normals)
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
    
    # Set subdivision scheme to none (hard edges for cube)
    mesh.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)
    
    return mesh

def apply_orange_material(stage, mesh_prim_path):
    """
    Apply an orange material to the cube mesh.
    
    Args:
        stage: USD stage
        mesh_prim_path: Path to the mesh prim
    """
    try:
        from pxr import UsdShade, Sdf
        
        # Create a material at the root level
        material_path = "/World/Looks/OrangeMaterial"
        
        # Ensure Looks scope exists
        looks_scope = UsdGeom.Scope.Define(stage, "/World/Looks")
        
        # Create material
        material = UsdShade.Material.Define(stage, material_path)
        
        # Create a PBR shader
        shader_path = material_path + "/Shader"
        shader = UsdShade.Shader.Define(stage, shader_path)
        shader.CreateIdAttr("UsdPreviewSurface")
        
        # Set orange color (RGB: 1.0, 0.5, 0.0)
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set((1.0, 0.5, 0.0))
        
        # Set material properties for a glossy orange look
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.2)
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.1)
        shader.CreateInput("specular", Sdf.ValueTypeNames.Float).Set(0.5)
        
        # Connect shader to material surface
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        
        # Bind material to the mesh
        mesh_prim = stage.GetPrimAtPath(mesh_prim_path)
        if mesh_prim.IsValid():
            binding_api = UsdShade.MaterialBindingAPI.Apply(mesh_prim)
            binding_api.Bind(material)
            print(f"✅ Applied orange material to {mesh_prim_path}")
        else:
            print(f"⚠️ Mesh prim not found: {mesh_prim_path}")
            
    except Exception as e:
        print(f"⚠️ Failed to apply material: {e}")

def add_collision_properties(stage, mesh_prim_path):
    """
    Add collision and physics properties to the mesh.
    
    Args:
        stage: USD stage
        mesh_prim_path: Path to the mesh prim
    """
    try:
        from pxr import UsdPhysics
        
        mesh_prim = stage.GetPrimAtPath(mesh_prim_path)
        if not mesh_prim.IsValid():
            print(f"⚠️ Mesh prim not found: {mesh_prim_path}")
            return
        
        # Add collision API
        collision_api = UsdPhysics.CollisionAPI.Apply(mesh_prim)
        print(f"✅ Added CollisionAPI to {mesh_prim_path}")
        
        # Add mesh collision API for precise collision detection
        mesh_collision_api = UsdPhysics.MeshCollisionAPI.Apply(mesh_prim)
        mesh_collision_api.CreateApproximationAttr().Set("convexHull")
        print(f"✅ Added MeshCollisionAPI with convex hull approximation")
        
        # Optional: Add physics material for friction/restitution
        # This helps with realistic contact behavior
        try:
            physics_material = UsdPhysics.MaterialAPI.Apply(mesh_prim)
            
            # Set friction and restitution
            if hasattr(physics_material, 'CreateStaticFrictionAttr'):
                physics_material.CreateStaticFrictionAttr().Set(0.5)
                physics_material.CreateDynamicFrictionAttr().Set(0.4)
                physics_material.CreateRestitutionAttr().Set(0.1)
                print(f"✅ Added physics material properties (friction, restitution)")
        except Exception as mat_error:
            print(f"ℹ️ Could not add physics material: {mat_error}")
        
    except Exception as e:
        print(f"⚠️ Failed to add collision properties: {e}")

def convert_orange_to_cube(usd_path, cube_size=0.025, width=None, depth=None, height=None, rotation_z_degrees=0):
    """
    Convert Orange001 USD file from sphere to cube.
    
    Args:
        usd_path: Path to the Orange001.usd file
        cube_size: Half-extent of the cube (default, used if width/depth/height not specified)
        width: Width of the cube (X dimension, half-extent)
        depth: Depth of the cube (Y dimension, half-extent)
        height: Height of the cube (Z dimension, half-extent)
        rotation_z_degrees: Rotation around Z-axis in degrees
    """
    print(f"\n🔄 Converting {usd_path} to cube...")
    if rotation_z_degrees != 0:
        print(f"   Rotation: {rotation_z_degrees}° around Z-axis")
    
    # Backup the original file
    backup_path = backup_original(usd_path)
    
    # Open the USD stage
    stage = Usd.Stage.Open(usd_path)
    
    # Find all mesh prims (excluding materials/looks)
    print("\n📋 Analyzing USD structure...")
    geometry_prims = []
    material_prims = []
    
    for prim in stage.Traverse():
        prim_path = str(prim.GetPath())
        prim_type = prim.GetTypeName()
        
        # Skip materials and looks
        if "Looks" in prim_path or "Material" in prim_path:
            material_prims.append(prim)
            continue
            
        # Find geometry prims
        if prim_type == "Mesh":
            geometry_prims.append(prim)
            print(f"   Found mesh: {prim_path}")
        elif prim_type in ["Xform", "Scope"]:
            print(f"   Found {prim_type}: {prim_path}")
    
    if not geometry_prims:
        print("❌ No mesh geometry found in the USD file!")
        return False
    
    # Convert ALL mesh prims (both visual and collision meshes)
    print(f"\n🎯 Converting {len(geometry_prims)} mesh(es)...")
    
    for idx, original_mesh_prim in enumerate(geometry_prims):
        mesh_path = original_mesh_prim.GetPath()
        mesh_name = str(mesh_path).split('/')[-1]
        
        # Determine if this is visual or collision mesh
        is_collision = "Collision" in str(mesh_path)
        is_visual = "Visual" in str(mesh_path)
        mesh_type = "Collision" if is_collision else ("Visual" if is_visual else "Mesh")
        
        print(f"\n   [{idx+1}/{len(geometry_prims)}] {mesh_type} mesh: {mesh_path}")
        
        # Store material bindings if they exist
        material_binding = None
        try:
            from pxr import UsdShade
            # Try to get material binding
            material_api = UsdShade.MaterialBindingAPI(original_mesh_prim)
            if material_api:
                material_binding = material_api.GetDirectBinding()
                if material_binding:
                    print(f"      Found material binding: {material_binding.GetMaterialPath()}")
        except Exception as e:
            pass
        
        # Remove the old mesh
        stage.RemovePrim(mesh_path)
        print(f"      ✅ Removed original sphere mesh")
        
        # Create the new cube mesh at the same path
        cube_mesh = create_cube_mesh(stage, mesh_path, size=cube_size, width=width, depth=depth, height=height, rotation_z_degrees=rotation_z_degrees)
        
        # Apply rotation transform to the parent Xform (ALWAYS, to clear old rotation if needed)
        # This ensures the bounding box visualization also rotates
        # Find the parent Xform prim (Orange001 level)
        mesh_path_str = str(mesh_path)
        if "Orange001" in mesh_path_str:
            # Get the Orange001 Xform prim
            parent_path = None
            for part in ["/root/Orange001", "/Orange001"]:
                test_prim = stage.GetPrimAtPath(part)
                if test_prim.IsValid() and test_prim.GetTypeName() == "Xform":
                    parent_path = part
                    break
            
            if parent_path:
                parent_prim = stage.GetPrimAtPath(parent_path)
                xformable = UsdGeom.Xformable(parent_prim)
                
                # Check if rotateZ operation already exists
                existing_ops = xformable.GetOrderedXformOps()
                rotate_op = None
                
                for op in existing_ops:
                    if op.GetOpType() == UsdGeom.XformOp.TypeRotateZ:
                        rotate_op = op
                        break
                
                # If no existing rotateZ op, create one
                if rotate_op is None:
                    rotate_op = xformable.AddRotateZOp()
                
                # Set the rotation value (in degrees) - even if 0 to clear old values
                rotate_op.Set(rotation_z_degrees)
                
                print(f"      🔄 Set Z-rotation to {rotation_z_degrees}° on {parent_path}")
        
        # Calculate actual dimensions for display
        actual_width = (width if width is not None else cube_size) * 2 * 100  # Convert to cm
        actual_depth = (depth if depth is not None else cube_size) * 2 * 100
        actual_height = (height if height is not None else cube_size) * 2 * 100
        rotation_info = f" (rotated {rotation_z_degrees}°)" if rotation_z_degrees != 0 else ""
        print(f"      ✅ Created cube mesh: {actual_width:.1f}cm(W) x {actual_depth:.1f}cm(D) x {actual_height:.1f}cm(H){rotation_info}")
        
        # Apply orange material to visual meshes
        if is_visual or not is_collision:
            print(f"      🎨 Applying orange material...")
            apply_orange_material(stage, mesh_path)
        
        # Add collision properties to collision meshes
        if is_collision:
            print(f"      🔧 Adding collision properties...")
            add_collision_properties(stage, mesh_path)
    
    # Save the modified stage
    stage.GetRootLayer().Save()
    print(f"\n✅ Successfully converted {usd_path} to cube!")
    print(f"   Original sphere backed up to: {backup_path}")
    
    return True

def main():
    """Main entry point."""
    print("=" * 60)
    print("🔷 Orange001 Sphere to Cube Converter")
    print("=" * 60)
    
    # Get script directory first
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load configuration
    config_path = os.path.join(script_dir, "config/scene_config.yaml")
    print(f"\n📋 Loading configuration from: {config_path}")
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Get cube dimensions from config
        obj_geom = config.get('object_geometry', {})
        cube_config = obj_geom.get('cube', {})
        
        width = cube_config.get('width', 0.01)
        depth = cube_config.get('depth', 0.01)
        height = cube_config.get('height', 0.005)
        rotation_z = cube_config.get('rotation_z_degrees', 45)
        
        print(f"✅ Loaded cube dimensions from config:")
        print(f"   Width:  {width*2*100:.1f}cm (half-extent: {width*100:.1f}cm)")
        print(f"   Depth:  {depth*2*100:.1f}cm (half-extent: {depth*100:.1f}cm)")
        print(f"   Height: {height*2*100:.1f}cm (half-extent: {height*100:.1f}cm)")
        print(f"   Rotation: {rotation_z}°")
        
    except Exception as e:
        print(f"⚠️ Could not load config: {e}")
        print("Using default dimensions: 2cm x 2cm x 1cm")
        width = 0.01
        depth = 0.01
        height = 0.005
        rotation_z = 45
    
    # Path to the Orange001 USD file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    orange_usd_path = os.path.join(script_dir, "assets/objects/Orange001/Orange001.usd")
    
    # Check if the file exists
    if not os.path.exists(orange_usd_path):
        print(f"❌ Error: Orange001.usd not found at {orange_usd_path}")
        return 1
    
    print(f"\n📁 Input file: {orange_usd_path}")
    
    # Convert the orange to a cube with dimensions from config
    success = convert_orange_to_cube(
        orange_usd_path, 
        width=width,
        depth=depth,
        height=height,
        rotation_z_degrees=rotation_z
    )
    
    if success:
        print("\n" + "=" * 60)
        print("✨ Conversion complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Run your data collection script:")
        print("   python scripts/data_collection_automatic.py \\")
        print("     --total-success-episodes 5 \\")
        print("     --data-output ./datasets/custom_cube_v1_5.hdf5")
        print("\n2. The Orange001 object will now appear as a cube in the simulation")
        print("\n3. To restore the original sphere, copy the backup file:")
        print("   cp assets/objects/Orange001/Orange001_sphere_backup.usd \\")
        print("      assets/objects/Orange001/Orange001.usd")
        print("=" * 60)
        return 0
    else:
        print("\n❌ Conversion failed!")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())

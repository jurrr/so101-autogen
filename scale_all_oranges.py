from pxr import Usd, UsdGeom

# Scale all three orange USD files
orange_files = [
    "assets/objects/Orange001/Orange001.usd",
    "assets/objects/Orange002/Orange002.usd", 
    "assets/objects/Orange003/Orange003.usd"
]

def scale_orange_file(usd_path, scale_factor=(1,1,1)):
    stage = Usd.Stage.Open(usd_path)
    geometry_prims = []
    for prim in stage.Traverse():
        if prim.GetTypeName() in ["Mesh", "Xform", "Scope"] and "Looks" not in str(prim.GetPath()):
            geometry_prims.append(prim)
    orange_prim = geometry_prims[0]
    try:
        xformable = UsdGeom.Xformable(orange_prim)
        existing_ops = xformable.GetOrderedXformOps()
        scale_op = None
        for op in existing_ops:
            if op.GetOpName() == "xformOp:scale":
                scale_op = op
                break
        
        if scale_op is None:
            scale_op = xformable.AddScaleOp()
        scale_op.Set(scale_factor)
        stage.GetRootLayer().Save()
        return True
        
    except Exception as e:
        print(f"❌ Failed to scale {usd_path}: {e}")
        return False

scale_factor = (0.3,0.3,0.3)  # 30% of original size
for usd_file in orange_files:
    scale_orange_file(usd_file, scale_factor)
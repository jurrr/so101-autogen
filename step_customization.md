# Simulation Customization Steps

This document tracks the step-by-step customizations made to the so101-autogen simulation framework.

---

## Step 1: Remove 2 Oranges (Keep Only Orange001)

**Objective**: Simplify the simulation by reducing from 3 oranges to 1 orange, keeping only Orange001.

**Date**: November 20, 2025

### Changes Made

#### 1. Configuration Files

**File**: `config/scene_config.yaml`

- **Orange Count**: Changed from `count: 3` to `count: 1`
- **Models List**: Removed `Orange002` and `Orange003`, kept only `Orange001`
  ```yaml
  models: 
    - "Orange001"
  ```
- **USD Paths**: Removed paths to Orange002 and Orange003 USD files
  ```yaml
  usd_paths:
    - "assets/objects/Orange001/Orange001.usd"
  ```
- **Target Configs**: Removed `/World/orange2` and `/World/orange3` configurations
  - Only `/World/orange1` remains with its visualization settings

**Rationale**: The configuration file is the source of truth for scene setup. By updating it here, all components that read from the config will automatically use only 1 orange.

---

#### 2. Configuration Utilities

**File**: `src/utils/config_utils.py`

**Changes in `get_orange_config()` method**:
- Default count: Changed from `3` to `1`
- Default models list: Changed from `["Orange001", "Orange002", "Orange003"]` to `["Orange001"]`
- Default USD paths: Removed Orange002 and Orange003 paths

**Changes in `get_target_configs()` method**:
- Removed default configurations for `/World/orange2` and `/World/orange3`
- Only `/World/orange1` remains in defaults

**Rationale**: These defaults ensure backward compatibility if the config file is missing or incomplete.

---

#### 3. Scene Factory

**File**: `src/utils/scene_factory.py`

**Changes in `create_orange_plate_scene()` method**:
- **Orange types/names generation**: Changed from loop-based to direct assignment
  ```python
  # Before: orange_types = ["orange"] * orange_count
  # After:  orange_types = ["orange"]
  
  # Before: orange_names = [f"orange{i+1}_object" for i in range(orange_count)]
  # After:  orange_names = ["orange1_object"]
  ```

**Changes in `_load_orange_objects()` method**:
- **Removed for loop**: Changed from `for i in range(orange_count)` to direct loading of single orange
- **Simplified logic**: Removed conditional indexing logic
- **Direct assignment**: 
  ```python
  usd_path = f"{self.project_root}/{orange_usd_paths[0]}"
  prim_path = "/World/orange1"
  scene_name = "orange1_object"
  model_name = orange_models[0]
  ```

**Changes in `_apply_candy_materials()` method**:
- **Default models list**: Changed from `["Orange001", "Orange002", "Orange003"]` to `["Orange001"]`
- **Removed index-based logic**: Changed from extracting object index to always using first model
  ```python
  # Before: object_index = int(object_name.replace('orange', '').replace('_object', '')) - 1
  #         model_name = orange_models[object_index]
  # After:  model_name = orange_models[0]
  ```

**Rationale**: The scene factory orchestrates object creation. Removing loops simplifies the code flow and eliminates the possibility of accidentally creating multiple oranges.

---

#### 4. Object Loader

**File**: `src/scene/object_loader.py`

**Changes in `__init__()` method**:
- Default `orange_models`: Changed to `["Orange001"]`
- Default `orange_usd_paths`: Changed to single-element list
- Default `orange_count`: Changed to `1`

**Changes in `load_oranges()` method**:
- **Position generation**: Changed from `generate_random_orange_positions(self.orange_count)` to `generate_random_orange_positions(1)`
- **Removed multiple position variables**: Removed `candy2_reset_pos` and `candy3_reset_pos`
- **Simplified positions list**: `positions = [candy1_reset_pos]` (single element)
- **Removed position printing loop**: Replaced with direct print of single position
- **Removed object loading loop**: Changed from `for i in range(min(self.orange_count, len(self.orange_usd_paths)))` to direct loading:
  ```python
  usd_path = self.orange_usd_paths[0]
  model_name = self.orange_models[0]
  prim_path = "/World/orange1"
  object_name = "orange1_object"
  position = positions[0]
  ```

**Rationale**: The object loader is responsible for actually instantiating objects in the scene. Simplifying from a loop to direct loading removes complexity and potential bugs.

---

#### 5. Data Collection Automation

**File**: `scripts/data_collection_automatic.py`

**Changes in main automation loop**:
- **Removed orange enumeration**: Removed `num_oranges = len(scene_manager.get_oranges())`
- **Removed for loop**: Changed from `for i in range(num_oranges)` to direct targeting
- **Direct target assignment**: `target_index = 1` (always target orange1)
- **Simplified keyboard input**: Always simulate key press '1'
- **Updated comment**: Changed "inner loop" reference to "continue to next run"

**Before**:
```python
num_oranges = len(scene_manager.get_oranges())
for i in range(num_oranges):
    target_index = i + 1
    ...
```

**After**:
```python
# Only one orange now, always target orange1
target_index = 1
...
```

**Rationale**: The automation script drives the data collection. By removing the loop that iterates through multiple oranges, we ensure it always targets the single orange, simplifying the collection logic and reducing the chance of errors.

---

#### 6. Utility Scripts

**File**: `scale_all_oranges.py`

**Changes**:
- **Updated comment**: Changed from "Scale all three orange USD files" to "Scale only Orange001 USD file"
- **Orange files list**: Removed Orange002 and Orange003
  ```python
  orange_files = [
      "assets/objects/Orange001/Orange001.usd"
  ]
  ```

**Rationale**: This utility script scales orange models. Since we only have one orange now, it should only process that single file.

---

### Impact Analysis

Using `steps_overview.md` as a guide, here's how this change affects each step of the gripper simulation:

#### Step 1: Locate Orange (IDLE → APPROACH)
- **Before**: User/automation could select targets 1, 2, or 3
- **After**: Only target 1 (orange1) is available
- **Impact**: `start_grasp_sequence()` will only be called with target_key '1'
- **Verification**: `target_configs` dictionary now only contains `/World/orange1`

#### Step 2-7: Gripper Operations (APPROACH → RETURN_HOME)
- **No Change**: All gripper operations (position, grip, lift, transport, release, return) remain identical
- **Reason**: These operations work on whatever target was selected. Since we still have 1 target, the entire state machine flow remains unchanged.

#### Smart Placement Manager
- **Before**: Tracked positions of up to 3 oranges to avoid collisions
- **After**: Only tracks 1 orange position
- **Impact**: `_scan_existing_oranges()` in state machine will find only 1 orange
- **Benefit**: Reduced computational overhead, simpler placement logic

#### Data Collection
- **Before**: Each run collected data for 3 sequential grasps (one per orange)
- **After**: Each run collects data for 1 grasp
- **Impact**: To collect N successful episodes, automation needs N runs instead of N/3 runs
- **Benefit**: Clearer 1:1 relationship between runs and successful episodes

---

### Files Modified

1. `config/scene_config.yaml` - Main configuration
2. `src/utils/config_utils.py` - Configuration parsing defaults
3. `src/utils/scene_factory.py` - Scene creation logic
4. `src/scene/object_loader.py` - Object instantiation
5. `scripts/data_collection_automatic.py` - Automation loop
6. `scale_all_oranges.py` - Utility script

### Files NOT Modified (No Changes Needed)

Based on the analysis, the following components work correctly without modification:

- **State Machine** (`src/state_machine/simple_state_machine.py`): Works with any number of targets via the `target_configs` dictionary
- **Grasp Detector** (`src/robot/grasp_detector.py`): Operates on the selected target object regardless of how many exist
- **IK Controller** (`src/robot/ik_controller.py`): Computes kinematics for target positions, independent of object count
- **Smart Placement Manager** (`src/robot/smart_placement_manager.py`): Scans for existing objects dynamically
- **Random Generator** (`src/scene/random_generator.py`): Accepts `num_oranges` parameter, now called with 1

---

### Testing Checklist

To verify this customization works correctly:

- [ ] Configuration loads successfully with 1 orange
- [ ] Scene creates with only 1 orange visible
- [ ] Orange001 appears at a randomized position
- [ ] Pressing '1' starts the grasp sequence
- [ ] Pressing '2' or '3' does nothing (no target exists)
- [ ] Automation script successfully grasps the single orange
- [ ] Scene reset regenerates a new random position for the single orange
- [ ] Data collection records correct episode data for 1-orange runs

---

### Next Steps

This completes **Step 1: Remove 2 Oranges**. Future customization steps will build upon this simplified 1-orange foundation.

Potential next steps:
- Step 2: Modify object properties (size, mass, appearance)
- Step 3: Change target object type (replace orange with different object)
- Step 4: Adjust gripper behavior or state machine parameters
- Step 5: Modify placement/target locations

---

### Notes

- All changes maintain backward compatibility with the overall architecture
- The state machine flow remains identical - only the number of available targets changed
- Code is now simpler with fewer loops and conditionals
- Random position generation still provides variability for training data

# SO101 AutoGen Customization Guide

This comprehensive guide explains how to customize the automated data collection system for different tasks, objects, and environments in the SO101 robot simulation.

## Table of Contents
1. [Camera Setup Customization](#camera-setup-customization)
2. [Objects to Move (Currently Oranges)](#objects-to-move-customization)
3. [Target Object Customization (Currently Plate)](#target-object-customization)
4. [Reinforcement Learning & Reward System](#reinforcement-learning--reward-system)
5. [Scene Randomization](#scene-randomization)
6. [Quick Configuration Reference](#quick-configuration-reference)

---

## Camera Setup Customization

The camera system consists of a wrist camera (ego-centric view) and a front/external camera (third-person view).

### Camera Configuration Files
- **Main Config**: `config/scene_config.yaml` - Lines 102-119
- **Controller**: `src/camera/multi_camera_controller.py` - Lines 71-110

### Front Camera Positioning

The front camera position can be adjusted in `config/scene_config.yaml`:

```yaml
cameras:
  front_camera:
    position: [0.52, 0.0, 0.4]  # [X, Y, Z] in meters
    orientation: [0.65328, 0.2706, 0.2706, 0.65328]  # [w, x, y, z] quaternion
    focal_length: 28.7
    horizontal_aperture: 38.11
    vertical_aperture: 28.58
    clipping_range: [0.01, 50.0]
```

#### Position Adjustments:
- **Higher view**: Increase Z value (e.g., `0.6` for 20cm higher)
- **Lower view**: Decrease Z value (e.g., `0.2` for 20cm lower)  
- **Move right**: Increase X value (e.g., `0.7` for 18cm forward)
- **Move left**: Decrease X value (e.g., `0.3` for 22cm backward)
- **Move away from robot**: Increase Y value (e.g., `0.2` for 20cm away)
- **Move toward robot**: Decrease Y value (e.g., `-0.2` for 20cm toward)

#### Inference-Optimized Camera Position:
For better inference alignment, use a closer, slightly elevated view:

```yaml
cameras:
  front_camera:
    position: [0.35, -0.1, 0.45]  # Closer, slightly offset, higher
    orientation: [0.7071, 0.0, 0.0, 0.7071]  # Looking down at 45 degrees
    focal_length: 35.0  # Slightly longer focal length
```

### Wrist Camera Configuration

The wrist camera is OK as-is but can be adjusted:

```yaml
cameras:
  wrist_camera:
    position: [0.02, 0.2, 0.1]   # Relative to gripper link
    orientation: [0.93969, -0.34202, 0.0, 0.0]
```

To modify wrist camera angle or position, adjust these values in the config file.

---

## Objects to Move Customization

Currently uses orange USD files styled as different candy types. All customization happens in the config file and object loader.

### Configuration Files
- **Main Config**: `config/scene_config.yaml` - Lines 8-77
- **Object Loader**: `src/scene/object_loader.py` - Lines 41-120
- **Scene Factory**: `src/utils/scene_factory.py` - Material application and USD hierarchy management

### Adding New Objects

#### Step 1: Add USD Files
Place your custom USD files in the assets directory:
```
assets/objects/YourObject/
├── YourObject.usd
└── texture/
    ├── diffuse.png
    ├── normal.png
    └── roughness.png
```

#### Step 2: Update Configuration
Edit `config/scene_config.yaml`:

```yaml
scene:
  oranges:  # Rename this section to match your objects
    count: 3
    models: 
      - "CustomCube"
      - "CustomSphere" 
      - "CustomTool"
    usd_paths:
      - "assets/objects/CustomCube/CustomCube.usd"
      - "assets/objects/CustomSphere/CustomSphere.usd"
      - "assets/objects/CustomTool/CustomTool.usd"
    
    # Define object types with physics and visual properties
    candy_types:  # Rename to object_types
      CustomCube:
        name: "Metal Cube"
        color: [0.7, 0.7, 0.8]      # Metallic gray
        mass: 0.015                  # 15g - heavier object
        roughness: 0.05              # Very smooth
        metallic: 0.8                # High metallic
      CustomSphere:
        name: "Plastic Ball"  
        color: [1.0, 0.2, 0.2]       # Bright red
        mass: 0.003                  # 3g - lighter object
        roughness: 0.4               # Matte finish
        metallic: 0.0                # No metallic
      CustomTool:
        name: "Screwdriver"
        color: [0.2, 0.2, 0.8]       # Blue handle
        mass: 0.025                  # 25g - tool weight
        roughness: 0.3               # Semi-matte
        metallic: 0.1                # Slight metallic
```

#### Step 3: Material Application System

The system automatically applies materials to objects based on the configuration. Materials are created in the proper USD hierarchy (`/World/object_name/Looks/material_name`) and bound to object visuals.

**Material Application Features:**
- Automatic color, roughness, and metallic property application
- Proper USD hierarchy management (materials created in each object's Looks folder)
- Error handling for Isaac Sim runtime requirements
- Debugging output for material application status

**Troubleshooting Material Issues:**
If materials don't appear visually:
1. Check the terminal output for material application debug messages
2. Verify objects have proper visual children in the USD hierarchy
3. Ensure Isaac Sim runtime is active (materials require omni.usd modules)
4. Check USD Stage in Isaac Sim to confirm materials are in correct locations

**Debug Material Application:**
The system provides detailed debug output during scene creation:
```
Material application: orange_0 -> Orange001_material: SUCCESS/FAILED
Material creation: /World/orange_0/Looks/Orange001_material: SUCCESS/FAILED
Material binding: orange_0 visual children: SUCCESS/FAILED
```

### Object Physics Customization

Adjust physical properties for different object behaviors:

```yaml
# Default physics settings
physics:
  radius: 0.02              # Object collision radius
  height: 0.03              # Object height
  mass: 0.010               # Default mass in kg
  min_distance: 0.05        # Minimum distance between objects
```

### Object Generation Areas

Control where objects spawn:

```yaml
generation:
  # Base generation range
  x_range: [0.1, 0.35]       # X: 10cm to 35cm from robot
  y_range: [-0.25, 0.25]     # Y: -25cm to 25cm (left/right)
  z_drop_height: 0.05        # Z: 5cm height for dropping
  max_attempts: 50           # Maximum placement attempts
  
  # Define exclusion zones where objects cannot spawn
  exclusion_zones:
    - name: "robot_arm_zone"
      type: "rectangle"
      bounds:
        x: [-0.1, 0.1]       # Robot workspace
        y: [-0.05, 0.05]     
        z: [0.0, 0.05]
    - name: "target_zone"
      type: "circle"
      center_from: "plate_position"
      radius: 0.12           # 12cm radius around target
      z: [0.0, 0.2]
```

---

## Target Object Customization

Currently uses a plate where objects should be placed. The target defines success criteria.

### Configuration Files  
- **Main Config**: `config/scene_config.yaml` - Lines 79-96
- **Scene Manager**: `src/scene/scene_manager.py` - Lines 167-212
- **Pickup Assessor**: `src/visualization/pickup_assessor.py` - Used for success detection

### Target Object Configuration

Edit `config/scene_config.yaml`:

```yaml
scene:
  plate:  # Rename to match your target
    model: "Container"
    usd_path: "assets/objects/Container/Container.usd"
    position: [0.20, -0.10, 0.02]  # [X, Y, Z] target position
    scale: 1.0
    use_virtual: true  # Use virtual object for detection
    
    # Visual styling
    bowl_styling:
      color: [0.0, 1.0, 0.0]        # Green container
      roughness: 0.1                 # Glossy finish
      metallic: 0.2                  # Slight metallic
      
    # Virtual object for success detection
    virtual_config:
      radius: 0.15              # Success area radius (15cm)
      height: 0.05              # Container height (5cm)
      position: [0.20, -0.10, 0.005]  # Ground-level position
```

### Success Detection Customization

The success criteria are defined in the grasp detector configuration:

```yaml
# Grasp Detection Configuration
grasp_detection:
  # Placement success thresholds
  grasp_success_xy_threshold: 0.05      # 5cm XY tolerance
  grasp_success_z_threshold: 0.08       # 8cm Z tolerance
  placement_velocity_threshold: 0.08    # Object must be nearly still
  placement_stability_frames: 120       # Must be stable for 2 seconds
  plate_placement_margin: 0.025         # 2.5cm margin inside target
```

### Custom Target Types

Create different target types by modifying the virtual config:

```yaml
# Precision Task (small target)
virtual_config:
  radius: 0.05              # 5cm precision target
  height: 0.02
  position: [0.25, 0.0, 0.005]

# Large Collection Area  
virtual_config:
  radius: 0.20              # 20cm large target
  height: 0.10
  position: [0.15, -0.15, 0.005]

# Linear Target (tray/slot)
virtual_config:
  type: "rectangular"       # Override circular detection
  bounds:
    x: [0.15, 0.25]         # 10cm x 15cm rectangular target
    y: [-0.05, 0.10]
    z: [0.0, 0.05]
```

---

## Reinforcement Learning & Reward System

The reward system is managed by the state machine and placement detection systems.

### Configuration Files
- **State Machine**: `src/state_machine/simple_state_machine.py` - Lines 300-600
- **Grasp Detection**: `src/robot/grasp_detector.py` 
- **Smart Placement**: `src/robot/smart_placement_manager.py`

### Reward Function Customization

The reward system operates through state transitions and success detection. Key areas to modify:

#### 1. Task Success Criteria

In `src/state_machine/simple_state_machine.py`, modify the success detection:

```python
def _update_release_state(self):
    """Customize release success criteria"""
    if self.state_timer > 1:
        # Custom success evaluation
        placement_success = self._evaluate_custom_placement()
        
        if placement_success:
            print("✅ Custom task completed successfully.")
            # Additional custom scoring
            score = self._calculate_placement_quality()
            print(f"Placement quality score: {score:.2f}")
            self._transition_to_state(SimpleGraspingState.RETURN_HOME)
            return
            
def _evaluate_custom_placement(self):
    """Custom placement evaluation logic"""
    target_pos, _ = self.target_object.get_world_pose()
    target_center = np.array([0.20, -0.10, 0.02])  # Your target center
    
    # Distance-based scoring
    distance = np.linalg.norm(target_pos[:2] - target_center[:2])
    
    # Precision requirements
    if distance <= 0.03:  # Within 3cm = excellent
        return True
    elif distance <= 0.05:  # Within 5cm = good  
        return True
    else:
        return False

def _calculate_placement_quality(self):
    """Calculate 0-1 quality score"""
    target_pos, _ = self.target_object.get_world_pose()
    target_center = np.array([0.20, -0.10, 0.02])
    
    distance = np.linalg.norm(target_pos[:2] - target_center[:2])
    max_distance = 0.10  # 10cm = 0 score
    
    score = max(0.0, 1.0 - (distance / max_distance))
    return score
```

#### 2. Intermediate Rewards

Add progress-based rewards in the state machine:

```python
def _update_approach_state(self):
    """Reward getting closer to target"""
    if not self.is_moving:
        # Calculate approach quality
        current_pos = self.ik_controller.current_target_position
        target_pos, _ = self.target_object.get_world_pose()
        
        approach_distance = np.linalg.norm(current_pos[:2] - target_pos[:2])
        approach_score = max(0.0, 1.0 - approach_distance / 0.3)
        
        print(f"Approach score: {approach_score:.2f}")
        
        self._transition_to_state(SimpleGraspingState.DESCEND)

def _update_grasp_state(self):
    """Reward successful grasping"""
    # ... existing grasp logic ...
    
    if self.state_timer == self.grasp_duration_steps:
        # Evaluate grasp quality
        grasp_success = self.grasp_detector.check_grasp_success()
        if grasp_success:
            print("Grasp reward: +50 points")
            # Could save this score for training data
```

### Failure Penalties

Customize failure conditions and penalties:

```python
def _handle_task_failure(self, failure_reason):
    """Custom failure handling with different penalties"""
    failure_penalties = {
        "ik_failure": -10,
        "grasp_failure": -20, 
        "collision": -30,
        "timeout": -5,
        "placement_failure": -15
    }
    
    penalty = failure_penalties.get(failure_reason, -10)
    print(f"Task failed: {failure_reason}, penalty: {penalty}")
    
    # Could log this for training analysis
    self._log_failure_data(failure_reason, penalty)
    
    self._transition_to_state(SimpleGraspingState.FAILED)
```

### State Machine Speed Control

Control task timing and difficulty:

```yaml
state_machine_control:
  grasping:
    close_duration_s: 1.0          # Slower = easier grasping
    settle_duration_s: 0.5         # Time to stabilize
  movement_speeds:
    travel_horizontal_step_m: 0.005  # Faster movement
    descend_step_m: 0.0005          # Very slow descent = precision
    lift_step_m: 0.003              # Moderate lift speed
```

---

## Scene Randomization  

The system includes built-in randomization for robust learning.

### Configuration Files
- **Random Generator**: `src/scene/random_generator.py`
- **Scene Manager**: `src/scene/scene_manager.py` - Lines 150-200
- **Main Config**: `config/scene_config.yaml` - Lines 30-50

### Object Position Randomization

Current randomization settings:

```yaml
generation:
  # Randomization ranges
  x_range: [0.1, 0.35]       # 25cm range in X
  y_range: [-0.25, 0.25]     # 50cm range in Y  
  z_drop_height: 0.05        # Fixed drop height
  max_attempts: 50           # Retry limit
```

### Advanced Randomization Options

Add to `config/scene_config.yaml`:

```yaml
# Advanced randomization settings
randomization:
  # Object pose randomization
  position_noise: 0.02         # ±2cm position variation
  orientation_noise: 15.0      # ±15 degree rotation
  
  # Object property randomization  
  mass_variation: 0.2          # ±20% mass variation
  friction_variation: 0.3      # ±30% friction variation
  size_variation: 0.1          # ±10% size variation
  
  # Environment randomization
  lighting_variation: true
  table_color_variation: true
  
  # Target position randomization
  target_position_noise: 0.03  # ±3cm target variation
```

### Implementing Advanced Randomization

Modify `src/scene/random_generator.py`:

```python
class RandomPositionGenerator:
    def generate_randomized_scene(self):
        """Generate complete randomized scene"""
        
        # 1. Randomize object positions
        positions = self.generate_random_orange_positions(3)
        
        # 2. Randomize object properties  
        for i, pos in enumerate(positions):
            # Add position noise
            noise = np.random.uniform(-0.02, 0.02, 3)
            positions[i] = [pos[0] + noise[0], pos[1] + noise[1], pos[2]]
            
        # 3. Randomize target position
        base_target = np.array([0.20, -0.10, 0.02])
        target_noise = np.random.uniform(-0.03, 0.03, 2)
        randomized_target = [
            base_target[0] + target_noise[0],
            base_target[1] + target_noise[1], 
            base_target[2]
        ]
        
        # 4. Randomize lighting
        self._randomize_lighting()
        
        return positions, randomized_target
    
    def _randomize_lighting(self):
        """Randomize lighting conditions"""
        import omni.usd
        stage = omni.usd.get_context().get_stage()
        
        # Randomize ambient light intensity
        ambient_intensity = np.random.uniform(0.3, 0.8)
        
        # Randomize directional light angle  
        light_angle = np.random.uniform(-30, 30)
        
        # Apply lighting changes
        # Implementation depends on your lighting setup
```

### Randomization During Data Collection

The data collection script automatically resets and randomizes the scene:

```python
# In scripts/data_collection_automatic.py
def randomize_scene_for_episode():
    """Called before each episode"""
    
    # 1. Reset scene with new random positions
    keyboard_handler.simulate_key_press('r')
    
    # 2. Wait for randomization to complete
    for _ in range(60):  # 1 second at 60 FPS
        world.step(render=not headless)
        
    # 3. Apply additional randomization if configured
    if config.get('advanced_randomization', {}).get('enabled', False):
        scene_manager.apply_advanced_randomization()
```

---

## Quick Configuration Reference

### Common Customization Tasks

#### Change Objects from Oranges to Cubes:
1. Create cube USD files in `assets/objects/Cube/`
2. Update `config/scene_config.yaml` lines 8-20 with new paths
3. Modify object_types section lines 25-50

#### Move Target Location:
1. Edit `config/scene_config.yaml` line 82: `position: [X, Y, Z]`
2. Update virtual_config position line 94

#### Adjust Camera for Better Inference:
1. Edit `config/scene_config.yaml` lines 104-107: front camera position
2. Consider position `[0.4, -0.1, 0.5]` for elevated angled view

#### Make Task Easier/Harder:
```yaml
# Easier task
state_machine_control:
  movement_speeds:
    descend_step_m: 0.002        # Faster descent
grasp_detection:
  grasp_success_xy_threshold: 0.08  # Larger tolerance

# Harder task  
state_machine_control:
  movement_speeds:
    descend_step_m: 0.0005       # Slower, more precise
grasp_detection:
  grasp_success_xy_threshold: 0.03  # Tighter tolerance
```

#### Add More Randomization:
1. Expand `generation.exclusion_zones` in config
2. Add randomization parameters to config
3. Modify `src/scene/random_generator.py` with custom logic

### File Modification Priority

1. **Quick changes**: Edit `config/scene_config.yaml`
2. **Object behavior**: Modify `src/scene/object_loader.py`  
3. **Reward system**: Edit `src/state_machine/simple_state_machine.py`
4. **Success criteria**: Modify `src/robot/grasp_detector.py`
5. **Randomization**: Edit `src/scene/random_generator.py`

### Testing Your Changes

After making modifications:

1. Test with single episode:
```bash
python scripts/data_collection_automatic.py --total-success-episodes 1
```

2. Check visualization:
```bash
python scripts/hdf5_visualizer.py --hdf5_file ./datasets/test.hdf5
```

3. Validate with full collection:
```bash
python scripts/data_collection_automatic.py --total-success-episodes 10 --data-output ./datasets/custom_task.hdf5
```

Remember to backup your configuration before making changes, and test each modification incrementally to ensure the simulation remains stable.
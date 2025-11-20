# Gripper Simulation Steps Overview

This document provides a detailed breakdown of the steps executed by the robotic gripper during the automated pick-and-place simulation. Each step is orchestrated by the `SimpleGraspingStateMachine` and evaluated through various detection and control systems.

---

## State Machine Flow

The simulation follows a **linear state flow** without complex branching or recovery logic. The states are defined in `src/state_machine/grasp_states.py` and orchestrated by `src/state_machine/simple_state_machine.py`.

### Complete State Sequence

1. **IDLE** - Waiting for target selection
2. **APPROACH** - Move above the target
3. **POSTURE_ADJUST** - Align gripper vertically (currently skipped)
4. **DESCEND** - Lower to grasping height
5. **GRASP** - Close the gripper
6. **GRASP_SETTLE** - Wait for grasp to stabilize
7. **LIFT** - Lift the object
8. **RETREAT** - Move to a safe position
9. **TRANSPORT** - Transport to above the plate
10. **RELEASE** - Open gripper to release object
11. **RETURN_HOME** - Return to initial position
12. **SUCCESS** / **FAILED** - Terminal states

---

## Detailed Step Breakdown

### Step 1: Locate Orange (IDLE → APPROACH)

**Purpose**: Identify and select the target object to grasp.

#### Movement Orchestration
- **Trigger**: User or automation script selects a target object by key (1-9)
- **Method**: `start_grasp_sequence(target_key)` in `simple_state_machine.py`
- **Target Selection**: 
  - Reads target configuration from `target_configs` dictionary
  - Retrieves target object from scene using `scene_manager.get_prim(target_prim_path)`
  - Sets up grasp detector with target object: `grasp_detector.set_target_object()`

#### Evaluation
- **Validation**: Checks if target object exists in scene
- **Plate Setup**: 
  - Attempts to find real plate object in scene
  - Falls back to virtual plate at configured position if not found
  - Initializes `GraspDetector` with plate object for later placement detection
- **Success Criteria**: Target object successfully retrieved and detector initialized
- **Failure Handling**: Transitions to FAILED state if target not found

**Key Components**:
- `SimpleGraspingStateMachine.start_grasp_sequence()` (line ~208)
- `GraspDetector.set_target_object()` (line ~73 in `grasp_detector.py`)
- `scene_manager.get_prim()` for object retrieval

---

### Step 2: Position Gripper Above Orange (APPROACH)

**Purpose**: Move the gripper to a position directly above the target object.

#### Movement Orchestration
- **Entry Point**: `_start_approach()` (line ~473 in `simple_state_machine.py`)
- **Target Calculation**: 
  - Gets target object world position: `target_object.get_world_pose()`
  - Creates approach position at `[target_x, target_y, approach_height]`
  - `approach_height` typically 0.21m (configured in YAML)
- **Movement Type**: Smooth interpolated movement
  - Uses `_start_smooth_move()` with `travel_horizontal_speed`
  - Calculates duration based on distance and speed
  - Linear interpolation over calculated steps

#### IK Control
- **IK Solver**: `LulaKinematicsSolver` (in `ik_controller.py`)
  - Computes joint angles for target end-effector position
  - Uses warm start from current joint positions for efficiency
  - Frame name: "wrist_link"
- **Update Method**: `_update_smooth_move()` (line ~619)
  - Increments progress each frame
  - Interpolates between start and end positions
  - Updates IK target: `ik_controller.set_target_position(current_pos)`

#### Evaluation
- **Progress Tracking**: `move_progress` incremented by `1.0 / move_duration_steps` each frame
- **Completion Check**: `if not self.is_moving` in `_update_approach_state()` (line ~640)
- **Success Criteria**: Gripper reaches approach position (progress >= 1.0)
- **Transition**: Moves to POSTURE_ADJUST state (currently skips to DESCEND)

**Key Components**:
- `IKController.compute_ik()` - Solves inverse kinematics
- `_start_smooth_move()` - Initiates smooth movement
- `_update_smooth_move()` - Updates position each frame

---

### Step 3: Grip Orange (DESCEND → GRASP → GRASP_SETTLE)

This step is divided into three sub-states for precision and reliability.

#### 3a. DESCEND - Lower to Grasping Height

**Purpose**: Slowly descend until gripper is at optimal grasping position.

##### Movement Orchestration
- **Entry Point**: `_start_descend()` (line ~492)
- **Movement Type**: Frame-by-frame incremental descent
  - Step size: `descend_step_size` (typically 0.002m = 2mm per frame)
  - No smooth interpolation - direct position updates
- **Height Control**: 
  - Continuously updates Z-coordinate: `new_pos[2] -= descend_step_size`
  - Safety check: prevents descent below 0.01m (1cm from ground)

##### Evaluation
- **Method**: `_update_descend_state()` (line ~656)
- **Posture Checking**: 
  - Monitors gripper verticality via `pickup_assessor.check_pickup_posture_corrected()`
  - Uses wrist orientation to detect proper alignment
  - **Green state check**: Waits for optimal grasping orientation
- **Success Criteria**: Pickup assessor detects "green" (graspable) state
- **Failure Handling**: 
  - If reaches ground level (z < 0.01m): transitions to FAILED
  - Returns to initial position on failure
- **Status Logging**: Prints height every 30 frames (0.5 seconds)

**Key Components**:
- `PickupAssessor.check_pickup_posture_corrected()` - Detects graspable state
- Frame-by-frame position updates via IK controller

#### 3b. GRASP - Close Gripper Jaws

**Purpose**: Progressively close the gripper around the object.

##### Movement Orchestration
- **Entry Point**: `_start_grasp()` (line ~505)
- **Gripper Control**: Progressive closure via `GripperController`
  - Start position: `grasp_start_pos` (open position)
  - End position: `grasp_end_pos` (typically 65% closed)
  - Duration: `grasp_duration_steps` frames (typically 60 frames = 1 second)
- **Interpolation**: Linear interpolation between open and closed positions
  - `progress = state_timer / grasp_duration_steps`
  - `current_pos = (1 - progress) * start + progress * end`

##### Evaluation
- **Method**: `_update_grasp_state()` (line ~692)
- **Progress Tracking**: Monitors `state_timer` against `grasp_duration_steps`
- **Completion**: When `state_timer > grasp_duration_steps`
- **Transition**: Moves to GRASP_SETTLE for stabilization

**Key Components**:
- `GripperController.set_target_position()` - Controls gripper jaw position
- Progressive closure over configured duration

#### 3c. GRASP_SETTLE - Wait for Stabilization

**Purpose**: Allow physics to settle after gripper closure.

##### Movement Orchestration
- **Hold Period**: No movement, just waiting
- **Duration**: `grasp_settle_duration_steps` frames (typically 30-60 frames)
- **Purpose**: Ensures object is securely held before lifting

##### Evaluation
- **Method**: `_update_grasp_settle_state()` (line ~701)
- **Timer Check**: `if state_timer > grasp_settle_duration_steps`
- **Success Criteria**: Settle period completes
- **Transition**: Moves to LIFT state

---

### Step 4: Lift Orange (LIFT)

**Purpose**: Slowly lift the object while continuously verifying the grasp is successful.

#### Movement Orchestration
- **Entry Point**: `_start_lift()` (line ~514)
- **Movement Type**: Frame-by-frame incremental lift
  - Step size: `lift_step_size` (typically 0.005m = 5mm per frame)
  - Target height: `lift_height` (typically 0.16m)
- **Update Method**: `_update_lift_state()` (line ~709)
  - Increments Z-coordinate: `new_pos[2] += lift_step_size`
  - Caps at maximum lift height

#### Grasp Verification
- **Check Interval**: Every 30 frames (0.5 seconds)
  - `if state_timer % lift_check_interval == 0`
- **Detection Method**: `grasp_detector.check_grasp_success()`

##### Smart Grasp Detection System

The `GraspDetector` (in `src/robot/grasp_detector.py`) uses multiple verification methods:

**Method 1: Relative Distance Stability**
- Measures initial distance between object and gripper center
- Monitors distance change over time
- Success if change ≤ 5cm throughout lift
- Primary detection method when sufficient history available

**Method 2: Absolute Distance Check**
- XY distance threshold: 10cm (relaxed from 3cm)
- Z distance threshold: 15cm (relaxed from 3cm)
- Fallback method for early detection

**Method 3: Movement Ratio Analysis**
- Compares object movement to gripper movement
- Threshold: ratio ≥ 0.7 (object follows gripper 70%+)
- Ensures object is actually moving with gripper

**Method 4: Stability Variance**
- Monitors variance in XY distance over last 10 frames
- Success if variance < 1mm²
- Confirms stable grasp

**Combined Evaluation**:
```python
result = relative_distance_ok AND movement_ok AND stability_ok
```

#### Evaluation Criteria
- **Success**: 
  - Grasp check passes continuously
  - Reaches target lift height (`current_pos[2] >= lift_height`)
- **Failure Detection**:
  - If `grasp_detector.check_grasp_success()` returns False:
    - Immediately stops lift
    - Returns to initial position
    - Transitions to FAILED state
  - Timeout: 300 frames (5 seconds) without reaching height
- **Status Logging**: Prints height every 30 frames

**Key Components**:
- `GraspDetector.check_grasp_success()` - Multi-method grasp verification
- `GraspDetector.smart_grasp_detection()` - Advanced detection logic
- Continuous monitoring during entire lift phase

---

### Step 5: Move Gripper to Plate (RETREAT → TRANSPORT)

This step is divided into two sub-states for collision avoidance.

#### 5a. RETREAT - Move to Safe Position

**Purpose**: Move to an intermediate position to avoid collisions during transport.

##### Movement Orchestration
- **Entry Point**: `_on_enter_state(RETREAT)` triggers `_update_retreat_state()`
- **Safe Position Calculation**: `_calculate_safe_position()` (line ~169)
  - Formula: `safe_pos = target_pos + (2/7) * (origin - target_pos)`
  - Moves 2/7 of the way toward origin from object position
  - Maintains safe clearance from objects
- **Movement Type**: Smooth interpolated movement
  - Uses `_start_smooth_move()` with safe position as target
  - Speed: `travel_horizontal_speed`

##### Evaluation
- **Method**: `_update_retreat_state()` (line ~775)
- **Object Monitoring**: 
  - Checks grasp every 30 frames
  - If object lost: immediate failure and return to initial position
- **Completion**: When `not self.is_moving`
- **Success Criteria**: Reaches safe position without losing object
- **Transition**: Moves to TRANSPORT state

#### 5b. TRANSPORT - Move to Above Plate

**Purpose**: Transport object from safe position to directly above the plate.

##### Movement Orchestration
- **Entry Point**: `_start_transport()` (line ~524)
- **Target Calculation**:
  1. Attempts to get real plate position from `scene_manager.plate_position`
  2. Falls back to default configured position [0.28, -0.05, transport_height]
  3. Uses **Smart Placement Manager** for optimal placement position

##### Smart Placement System

The `SmartPlacementManager` (in `src/robot/smart_placement_manager.py`) provides intelligent placement:

**Placement Strategy**:
- Maintains record of all placed objects (`placed_objects` list)
- Generates candidate positions using "center_to_edge" strategy:
  - Starts from plate center
  - Creates concentric rings moving outward
  - Maximum attempts: 100 positions
- Validates each position:
  - Must be within effective plate radius (radius - safety_margin_edge)
  - Must maintain minimum distance from other objects (6cm)
  - Must be within IK reachable range:
    - X distance ≤ 30cm from base
    - Y distance ≤ 20cm from base

**Position Selection**:
```python
placement_position = placement_manager.calculate_placement_position(target_prim_name)
```

**Final Transport Position**:
- XY: From placement manager (collision-free position)
- Z: `release_height` (typically 0.05m = 5cm above plate)
- Stored in `_transport_final_position` for state caching

##### Movement Execution
- **Movement Type**: Smooth interpolated movement
  - From safe position to placement position
  - Speed: `travel_horizontal_speed`
- **Optimization**: Checks if already near target (distance < 1cm)
  - Skips movement if already positioned

##### Evaluation
- **Method**: `_update_transport_state()` (line ~784)
- **Object Monitoring**: 
  - Checks grasp every 30 frames during transport
  - If object lost: immediate failure
- **Status Logging**: 
  - Prints start/target positions on first frame
  - Logs transport progress
- **Completion**: When `not self.is_moving`
- **Success Criteria**: Reaches placement position with object still held
- **Transition**: Moves to RELEASE state

**Key Components**:
- `SmartPlacementManager.calculate_placement_position()` - Collision-free placement
- `_calculate_safe_position()` - Intermediate waypoint for collision avoidance
- Continuous grasp monitoring throughout transport

---

### Step 6: Lower Gripper and Release Orange (RELEASE)

**Purpose**: Open gripper to release object and verify successful placement.

#### Movement Orchestration
- **Entry Point**: `_start_release()` (line ~538)
- **Gripper Action**: 
  - Sets gripper to fully open position
  - `gripper_controller.target_gripper_position = open_pos`
  - No arm movement - only gripper opens
- **Arm Position**: Remains at `release_height` (5cm above plate surface)

#### Placement Verification

##### Detection Initialization
- **Start Point**: Frame 1 of RELEASE state
  - Calls `grasp_detector.start_placement_detection()`
  - Initializes placement monitoring system
- **Wait Period**: 60 frames (~1 second) before starting checks
  - Allows physics to settle after gripper opens

##### Placement Detection System

The `GraspDetector.check_object_placed_in_plate()` uses multi-criteria verification:

**Criteria 1: Position Check**
- Gets object position from `target_object.get_world_pose()`
- Retrieves plate AABB (Axis-Aligned Bounding Box):
  - Min bounds: `[plate_x - radius, plate_y - radius, plate_z]`
  - Max bounds: `[plate_x + radius, plate_y + radius, plate_z + height]`
- Applies placement margin (2.5cm) for safety
- **Position validation**:
  ```python
  x_ok = plate_bbox_min_x + margin <= object_x <= plate_bbox_max_x - margin
  y_ok = plate_bbox_min_y + margin <= object_y <= plate_bbox_max_y - margin
  z_ok = plate_bbox_min_z <= object_z <= plate_bbox_max_z + 0.02  # Z more lenient
  position_ok = x_ok AND y_ok  # Primary check is XY overlap
  ```

**Criteria 2: Velocity Stability**
- Gets object linear velocity: `target_object.get_linear_velocity()`
- Calculates speed: `np.linalg.norm(velocity)`
- Threshold: 0.08 m/s (8cm/s) - more lenient than initial 5cm/s
- **Velocity history tracking**:
  - Records last 10 velocity measurements
  - Requires 3 consecutive frames below threshold
- **Stability counter**:
  - Increments when velocity below threshold
  - Resets to 0 if velocity exceeds threshold
  - Must reach count ≥ 3 for success

**Combined Evaluation**:
```python
placement_success = position_ok AND (stability_counter >= 3)
```

##### Debug Logging (if enabled)
Prints every 10 frames during detection:
- Object position [x, y, z]
- Object speed (mm/s)
- Plate bounding box coordinates
- Position checks (X, Y, Z pass/fail)
- Stability counter value
- Final result

#### Placement Recording
- **On Success**: 
  - Records placement with `placement_manager.record_placement()`
  - Saves: object name, position, success=True
  - Used for future collision avoidance
  - Prints confirmation: "✅ Object successfully placed in the plate"

#### Evaluation
- **Method**: `_update_release_state()` (line ~836)
- **Continuous Checking**: Runs placement detection from frame 2 onward
- **Success Criteria**: 
  - Object within plate bounds (XY with margin)
  - Velocity below threshold for 3 consecutive frames
- **Timeout**: `release_duration_steps` frames (typically 360 = 6 seconds)
- **Failure Handling**:
  - If timeout: records failed placement, transitions to RETURN_HOME
  - Still attempts to return to initial position
- **Transition**: To RETURN_HOME state on success or timeout

**Key Components**:
- `GraspDetector.start_placement_detection()` - Initializes monitoring
- `GraspDetector.check_object_placed_in_plate()` - Multi-criteria verification
- `SmartPlacementManager.record_placement()` - Records for collision avoidance
- Position + velocity + stability combined evaluation

---

### Step 7: Return to Initial Position (RETURN_HOME)

**Purpose**: Return gripper to starting position for next task.

#### Movement Orchestration
- **Entry Point**: `_on_enter_state(RETURN_HOME)` triggers movement
- **Target Position**: `initial_position` (typically [0.25, 0.0, 0.25])
- **Movement Type**: Smooth interpolated movement
  - Uses `_start_smooth_move()` with initial position as target
  - Speed: `travel_horizontal_speed`
- **Gripper State**: Remains open (already opened during RELEASE)

#### Evaluation
- **Method**: `_update_return_home_state()` (line ~868)
- **Completion Check**: `if not self.is_moving`
- **Success Criteria**: Reaches initial position
- **Transition**: To SUCCESS state (task complete)

#### Terminal State Handling
- **SUCCESS State**:
  - Marks `last_attempt_successful = True`
  - Logs completion to data collection manager (if enabled)
  - Waits for scene reset or new task
- **FAILED State**:
  - Marks `last_attempt_successful = False`
  - Logs failed attempt
  - Prepares for retry or scene reset

**Key Components**:
- `_return_to_initial_position()` - Emergency return using direct joint positions
- `_update_return_home_state()` - Standard return via smooth movement
- Terminal state handlers for success/failure logging

---

## Movement Control Systems

### IK Controller (`src/robot/ik_controller.py`)

**Core Functionality**:
- **IK Solver**: `LulaKinematicsSolver`
  - Descriptor: `config/so101_descriptor.yaml`
  - URDF: `assets/robots/so101_physics_generated/so101_v1.urdf`
  - Target frame: "wrist_link"
- **Computation**: `compute_ik(target_position, current_joint_positions)`
  - Returns: `(joint_angles, success_flag)`
  - Uses warm start for efficiency
  - Throttles failure logging to avoid spam

**Position Control**:
- Maintains target position: `ik_target_position`
- Updates target: `set_target_position()`
- Retrieves current: `get_target_position()`
- Applies joint actions to robot each frame

**Posture Correction** (currently disabled):
- Can monitor gripper verticality
- Adjustable via `enable_posture_correction` flag
- Skipped in current implementation

### Gripper Controller (`src/robot/gripper_controller.py`)

**Progressive Control**:
- Open position: Typically 0.0
- Closed position: Configured in YAML (e.g., -0.65)
- Step size: 0.01 for incremental movement

**Control Methods**:
- `set_target_position()` - Direct position setting
- `open_gripper()` - Fully open
- `close_gripper(percentage)` - Partial or full closure
- Progressive movement via `update()` each frame

### Smooth Movement System

**Implementation** (in `SimpleGraspingStateMachine`):
```python
def _start_smooth_move(end_pos, speed):
    # Record start and end positions
    # Calculate duration based on distance and speed
    # Begin linear interpolation
    
def _update_smooth_move():
    # Increment progress
    # Interpolate current position
    # Update IK target
```

**Advantages**:
- Natural-looking movement
- Configurable speed per movement type
- Avoids sudden jumps in position
- Dynamic duration calculation based on distance

---

## Detection and Evaluation Systems

### Grasp Detector (`src/robot/grasp_detector.py`)

**Grasp Detection Methods**:

1. **Basic Distance Check**: Quick preliminary judgment
   - Gripper center to object distance
   - Thresholds: 3cm for initial checks

2. **Smart Grasp Detection**: Multi-criteria analysis
   - Relative distance stability (primary)
   - Absolute distance check (fallback)
   - Movement ratio analysis (object follows gripper)
   - Stability variance monitoring

3. **Placement Detection**: Multi-stage verification
   - Position within plate bounds (XY primary, Z secondary)
   - Velocity stability monitoring
   - Consecutive frame confirmation

**Configuration** (from `scene_config.yaml` → `grasp_detection` section):
- Check intervals, thresholds, stability frames
- Debug logging options
- Gripper jaw paths for position detection

### Pickup Assessor

**Posture Verification**:
- Monitors wrist orientation
- Detects "green" (graspable) state during descent
- Ensures proper gripper alignment before grasp

### Smart Placement Manager (`src/robot/smart_placement_manager.py`)

**Collision Avoidance**:
- Tracks all placed objects with position and radius
- Generates collision-free candidate positions
- Validates against safety margins and IK reachability

**Placement Strategy**:
- Center-to-edge: Starts at plate center, moves outward
- Concentric ring generation
- Maximum 100 placement attempts

**IK Reachability Validation**:
- X distance ≤ 30cm
- Y distance ≤ 20cm
- Ensures robot can physically reach position

---

## Configuration Parameters

Key parameters from `config/scene_config.yaml`:

### Movement Speeds
```yaml
travel_horizontal_speed: 0.01   # Horizontal movement speed (m/frame)
descend_step_size: 0.002        # Descent speed (m/frame)
lift_step_size: 0.005           # Lift speed (m/frame)
```

### Heights
```yaml
approach_height: 0.21           # Height above object for approach
lift_height: 0.16               # Target height for lift
transport_height: 0.25          # Safe transport height
release_height: 0.05            # Height for release (5cm above plate)
```

### Timing
```yaml
grasp_duration_steps: 60        # Gripper closure duration (frames)
grasp_settle_duration_steps: 30 # Settle wait time (frames)
release_duration_steps: 360     # Release timeout (6 seconds)
```

### Detection Thresholds
```yaml
grasp_detection:
  grasp_success_xy_threshold: 0.05      # 5cm
  grasp_success_z_threshold: 0.12       # 12cm
  grasp_movement_ratio_threshold: 0.7   # 70% following
  placement_velocity_threshold: 0.08    # 8cm/s
  placement_stability_frames: 120       # ~4 seconds
```

---

## Error Handling and Recovery

### IK Failure
- **Detection**: `success_flag` from `compute_ik()` is False
- **Action**: 
  - Immediate stop of current movement
  - Return to initial position via direct joint setting
  - Transition to FAILED state
  - Throttled logging to avoid spam (once per second)

### Grasp Failure
- **Detection**: `grasp_detector.check_grasp_success()` returns False during LIFT
- **Action**:
  - Immediate stop of lift
  - Print failure message
  - Return to initial position
  - Transition to FAILED state

### Object Lost During Transport
- **Detection**: Grasp check fails during TRANSPORT or RETREAT
- **Action**:
  - Immediate stop of movement
  - Return to initial position
  - Transition to FAILED state
  - No retry attempts

### Plate Movement Detection
- **Monitoring**: Records initial plate position at DESCEND state entry
- **Check**: Continuous monitoring during task execution
- **Threshold**: Movement > configured limit
- **Action**: 
  - Sets `hard_reset_required` flag
  - Triggers full scene reset
  - Prevents cascading failures

### Safety Limits
- **Ground Collision**: Prevents descent below 1cm from ground
- **Height Limits**: Caps lift at configured maximum
- **Timeout Protection**: 
  - LIFT timeout: 300 frames (5 seconds)
  - RELEASE timeout: 360 frames (6 seconds)

### Emergency Return
- **Method**: `_return_to_initial_position()`
- **Strategy**: 
  - Attempts direct joint position setting (bypasses IK)
  - Falls back to IK-based movement if direct setting fails
  - Opens gripper to release any held object
  - Used for all failure recovery

---

## Data Collection Integration

When `data_collection_manager` is provided:

### Episode Management
- **Episode ID**: Auto-incrementing counter
- **Start Event**: Triggered on APPROACH state entry
- **End Event**: Triggered on SUCCESS/FAILED terminal states

### Data Recording
- **Frame-by-frame**: 
  - Camera images (front + wrist views)
  - Robot joint positions
  - Gripper position
  - Target positions
  - State information
- **Format**: HDF5 with LeRobot-compatible structure
- **Frequency**: Every simulation frame (60 Hz)

### Success/Failure Logging
- Records episode outcome
- Links to specific object and task
- Enables success rate analysis

---

## Summary

The gripper simulation implements a **robust, multi-stage pick-and-place pipeline** with:

1. **Intelligent Movement**: IK-based control with smooth interpolation
2. **Multi-Criteria Detection**: Grasp and placement verification using multiple sensors
3. **Collision Avoidance**: Smart placement system for multi-object scenarios
4. **Comprehensive Error Handling**: Graceful recovery from common failure modes
5. **Data Collection Ready**: Integrated recording for ML training

The system prioritizes **reliability** and **reproducibility** over speed, making it ideal for generating high-quality synthetic training data for visuomotor policies.

# Explain Auto Data Collection

## Overview

The automatic data collection in this project uses **imitation learning** rather than reinforcement learning. The system collects demonstration data by running a pre-programmed robotic task where a robot arm picks up orange objects and places them in a bowl. The collected data is then used to train a diffusion policy model using the LeRobot framework.

## How Data Collection Works

### 1. Starting Positions

**Arm Position:**
- The robot arm starts at a **fixed home position** defined in the robot configuration
- Initial joint positions are consistent across all episodes
- Located at: `config/scene_config.yaml` under `robot.initial_joint_positions`

**Bowl Position:**
- **Fixed position** at `[0.275, -0.15, 0.02]` (27.5cm along X-axis, -15cm along Y-axis)
- Consistent across all episodes
- Defined in: `config/scene_config.yaml` under `placement.objects.plate.position`

**Orange Positions:**
- **Randomized within a defined area**
- Generation bounds: X: [0.2, 0.45], Y: [-0.25, 0.25], Z: 0.02
- Each episode spawns 3 oranges at random positions within these bounds
- Minimum distance between oranges: 3cm to prevent overlap
- **Could be varied** by modifying the bounds in `config/scene_config.yaml`

### 2. Success/Failure Detection

**Target Definition:**
The simulation defines success based on **proximity detection**:
```python
# In src/tasks/plate_task.py
def _is_orange_in_plate(self, orange_position, plate_position):
    distance = np.linalg.norm(orange_position[:2] - plate_position[:2])
    return distance < self.plate_radius
```

**Success Criteria:**
- An orange is considered "in the plate" when it's within the plate's radius
- The task tracks how many oranges are successfully placed
- Episode ends when all 3 oranges are in the plate OR maximum steps reached
- Success threshold can be adjusted in the task configuration

### 3. Pre-trained Behavior

**Why the simulation works well from start:**
The robot does NOT use a pre-trained model. Instead, it uses **scripted/programmed behavior**:

```python
# The robot follows pre-programmed motion sequences
def execute_pick_and_place(self):
    # 1. Move to orange position
    # 2. Lower arm to grasp height
    # 3. Close gripper
    # 4. Lift orange
    # 5. Move to plate position
    # 6. Lower and release
```

The "intelligence" comes from:
- **Computer vision** for object detection
- **Inverse kinematics** for motion planning  
- **Pre-programmed sequences** for pick-and-place operations
- **Physics simulation** ensuring realistic interactions

### 4. Learning Approach

**No Reinforcement Learning During Collection:**
- The data collection phase does NOT use reinforcement learning
- No model improvement during collection
- No checkpoints of improved models are saved during this phase
- The robot follows the same scripted behavior for all episodes

**Learning Happens Later:**
After data collection, the saved demonstrations are used to train a **diffusion policy** using imitation learning:
```bash
lerobot-train \
    --dataset.repo_id=jurrr/pickup_orange_10e \
    --policy.type=diffusion
```

### 5. Data Storage Strategy

**Only Successful Episodes Are Saved:**
```python
# In scripts/data_collection_automatic.py
if task_completed_successfully:
    episode_data = collect_episode_data()
    save_to_hdf5(episode_data, output_file)
    successful_episodes += 1
```

**What Gets Recorded:**
- **Camera observations** (RGB images from multiple viewpoints)
- **Robot joint states** (positions, velocities)
- **Gripper state** (open/closed)
- **Object poses** (orange and plate positions)
- **Action sequences** (commanded joint movements)

**Individual vs. Set Success:**
- The system tracks completion of **all 3 oranges as a set**
- Episodes are only saved when ALL 3 oranges are successfully placed
- Partial completions (1 or 2 oranges) are discarded
- This ensures high-quality demonstration data

## Execution Flow

1. **Episode Initialization:**
   - Reset robot to home position
   - Spawn 3 oranges at random locations
   - Place bowl at fixed position

2. **Scripted Execution:**
   - Detect orange positions using computer vision
   - Plan pick-and-place sequence for each orange
   - Execute motions using inverse kinematics

3. **Success Evaluation:**
   - Monitor orange positions relative to plate
   - Count successful placements
   - Determine episode completion

4. **Data Recording:**
   - If successful: Save complete episode data to HDF5
   - If failed: Discard episode and retry
   - Continue until target number of successful episodes collected

## Variability Options

**Can Be Varied:**
- Orange spawn positions (modify bounds in config)
- Orange colors/types (already has 3 variants)
- Bowl position (change plate coordinates)
- Camera angles (multiple camera configs available)
- Lighting conditions
- Physics parameters (friction, mass, etc.)

**Currently Fixed:**
- Robot starting position
- Bowl orientation
- Task sequence (always pick all oranges)
- Success criteria (proximity to plate)

This approach generates high-quality demonstration data that can then be used to train imitation learning models to perform the same task autonomously.
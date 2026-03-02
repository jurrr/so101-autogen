# To run the example from the original readme:

**Storage Setup: Datasets moved to large drive to prevent storage issues**
- Main drive (`/`): 124GB total - keep for code and OS
- Large drive (`/mnt`): 176GB total - used for datasets and model outputs  
- Symlink created: `./datasets` -> `/mnt/datasets`

## 0. Check available storage
```
# Monitor disk usage
df -h

# Check dataset sizes
ls -lh ./datasets/
du -sh /mnt/datasets/
du -sh /mnt/outputs/
```

## 1. activate isaac env 
```
conda activate isaac
```

## 2. run the automatic data collection 

**Note: Datasets are stored on the large drive (/mnt/datasets) to avoid storage issues**

```
python scripts/data_collection_automatic.py --total-success-episodes 100 --data-output ./datasets/custom_orange_v1_100.hdf5
```


## 3. optional: show the examples generated

```
python scripts/hdf5_visualizer.py --hdf5_file ./datasets/custom_orange_v1_100.hdf5
```

## 4. convert to lerobot format (v2.1 ➜ v3.0)

**Step 4a – Run the parallel converter (still emits v2.1)**

LeRobot 0.3.3 remains the most stable release for `parallel_converter.py`, so keep using it for the initial HDF5 → LeRobot export (13,315 frames across 29 episodes in this example).

```
pip install lerobot==0.3.3
```

Login to Hugging Face before pushing
```
huggingface-cli login

# Set environment variables to use large drive for cache and temporary files
export HF_HOME=/mnt/outputs/.cache/huggingface
export TMPDIR=/mnt/outputs/temp
mkdir -p $HF_HOME $TMPDIR

# Convert to v2.1 format (works with current task format)
python scripts/parallel_converter.py \
    --hdf5-root ./datasets \
    --hdf5-files custom_orange_v1_100.hdf5 \
    --repo-id jurrr/pickup_custom_orange_100e_v033 \
    --num-workers 4 \
    --python-executable /home/windowsuser/miniconda3/envs/isaac/bin/python \
    --push-to-hub
```

**Result:** Dataset `jurrr/pickup_custom_orange_100e_v033` with 13,315 individual frames ✅

For the wrist-camera datasets that ship with this repo, refresh the uploads with the exact commands requested by the Hub team:

```
python scripts/parallel_converter.py \
    --repo-id jurrr/custom-cube-frontwristcam-test5episodes-v0 \
    --robot-type so101_follower \
    --fps 30 \
    --hdf5-root /mnt/datasets \
    --hdf5-files custom_cube_frontwristcam_5.hdf5 \
    --task "grab object and place into plate" \
    --num-workers 2 \
    --push-to-hub

python scripts/parallel_converter.py \
    --repo-id jurrr/custom-cube-frontwristcam-50-v0 \
    --robot-type so101_follower \
    --fps 30 \
    --hdf5-root /mnt/datasets \
    --hdf5-files custom_cube_frontwristcam_50.hdf5 \
    --task "grab object and place into plate" \
    --num-workers 2 \
    --push-to-hub
```

**Step 4b – Upgrade every dataset to the mandatory v3.0 format**

Starting with LeRobot 0.4, datasets must expose the v3.0 layout. Run the official upgrader immediately after each `parallel_converter.py` push so that the Hub tag is in sync.

```
pip install "lerobot>=0.4.1"

# Generic command (set --root to the parent directory where datasets live)
python -m lerobot.datasets.v30.convert_dataset_v21_to_v30 \
    --repo-id <user>/<dataset_name> \
    --root /mnt/datasets \
    --push-to-hub true

# Project datasets
python -m lerobot.datasets.v30.convert_dataset_v21_to_v30 \
    --repo-id jurrr/custom-cube-frontwristcam-test5episodes-v0 \
    --root /mnt/datasets \
    --push-to-hub true

python -m lerobot.datasets.v30.convert_dataset_v21_to_v30 \
    --repo-id jurrr/custom-cube-frontwristcam-50-v0 \
    --root /mnt/datasets \
    --push-to-hub true
```

The script rewrites the dataset in-place (it will create `_old` and `_v30` folders during execution) and publishes the upgraded snapshot plus the `codebase_version=v3.0` tag automatically.

## 5. train smolvla model based on examples

**Important: Install LeRobot 0.4.1 in isaac environment for training (after conversion is complete)**

```
conda activate isaac
pip install lerobot==0.4.1
pip install transformers  # Ensure transformers is available in isaac env
```

**Note: Training must be run in the isaac conda environment**
- The isaac environment has all the necessary dependencies for Isaac Sim integration
- LeRobot 0.4.1 and transformers must be installed in the isaac environment 
- Flash-attn installation errors can be ignored (optional dependency)

First install FFmpeg and fix video codec compatibility

```
sudo apt update
sudo apt install ffmpeg
pip uninstall torchcodec -y
pip install torchcodec==0.2.1

# Fix numpy compatibility
pip install "numpy<2"
```

Train the model from scratch using the working v2.1 dataset (outputs saved to large drive to avoid storage issues)

```
# Ensure you're in the isaac environment
conda activate isaac

# Create output directory on large drive for model training
export LEROBOT_CACHE_DIR=/mnt/outputs

# ✅ SUCCESSFUL COMMAND - Tested and working in isaac environment:
export LEROBOT_CACHE_DIR=/mnt/outputs && lerobot-train \
    --batch_size=64 \
    --steps=100 \
    --dataset.repo_id=jurrr/pickup_custom_orange_100e_v033 \
    --dataset.video_backend=pyav \
    --policy.device=cuda \
    --policy.type=smolvla \
    --wandb.enable=false \
    --policy.repo_id=jurrr/pickup_custom_orange_100e_v033_policy_vlm \
    --save_freq=200 \
    --job_name=smolvla_custom_orange_100e_vlm \
    --output_dir=/mnt/outputs/smolvla_custom_oeange_100e_100_vlm
```

**Key Parameters:**
- `--dataset.video_backend=pyav`: Uses PyAV instead of TorchCodec (fixes video compatibility issues)
- `--policy.type=smolvla`: Uses Small VLA architecture instead of plain diffusion
- `--policy.vlm_model_name` (default): Uses HuggingFaceTB/SmolVLM2-500M-Video-Instruct for vision-language understanding
- **Environment**: Must run in `conda activate isaac` environment ✅
- Training on LeRobot 0.4.1 with modern SmolVLA policy
- Dataset: 13,315 frames from 29 episodes with proper frame-level structure
- Output: Trained policy uploaded to `jurrr/pickup_orange_100e_v033_policy_vlm`

## 6. Monitor and cleanup storage

```
# Check storage usage after training
df -h
du -sh /mnt/outputs/

# Clean up old model checkpoints if needed
rm -rf /mnt/outputs/old_experiment_name/

# Archive datasets after successful training
tar -czf /mnt/datasets_archive_$(date +%Y%m%d).tar.gz -C /mnt datasets/
```

## Summary: LeRobot Version Workflow

**The complete workflow uses two different LeRobot versions:**

1. **Data Conversion** (Step 4): Use `lerobot==0.3.3`
   - Converts HDF5 → LeRobot v2.1 format successfully
   - Task format compatibility issues resolved
   - Creates proper frame-level dataset structure

2. **Model Training** (Step 5): Use `lerobot==0.4.1` in isaac environment
   - **Critical**: Must run `conda activate isaac` before training
   - SmolVLA policy implementation (more efficient than diffusion)
   - Vision-Language Model integration for better scene understanding
   - Uses PyAV backend for video compatibility
   - Trains on the v2.1 dataset created in step 4

**Final Results:**
- ✅ Dataset: `jurrr/pickup_orange_100e_v033` (13,315 frames, 29 episodes)
- ✅ Trained Policy: `jurrr/pickup_orange_100e_v033_policy_vlm` (SmolVLA with VLM)



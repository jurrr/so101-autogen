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
python scripts/data_collection_automatic.py --total-success-episodes 10 --data-output ./datasets/auto_v1_10.hdf5
python scripts/data_collection_automatic.py --total-success-episodes 5 --data-output ./datasets/auto_v1_5.hdf5 
python scripts/data_collection_automatic.py --total-success-episodes 100 --data-output ./datasets/auto_v1_100.hdf5 
```


## 3. optional: show the examples generated

```
python scripts/hdf5_visualizer.py --hdf5_file ./datasets/auto_v1_10.hdf5
```

## 4. convert to lerobot format

Due to task=task parameter, the previous lerobot version is used! downgrade to 0.3.3

```
pip install lerobot==0.3.3
```

Login to huggingface to push to hub
```
huggingface-cli login

# Set environment variables to use large drive for cache and temporary files
export HF_HOME=/mnt/outputs/.cache/huggingface
export TMPDIR=/mnt/outputs/temp
mkdir -p $HF_HOME $TMPDIR

# Optimal settings for VM with 4 CPU cores and 27GB RAM:
# - Conservative: 2 workers (safe, slower)
# - Balanced: 4 workers (matches CPU cores, good balance)  
# - Aggressive: 6 workers (1.5x cores, higher memory usage)

python scripts/parallel_converter.py \
    --hdf5-root ./datasets \
    --hdf5-files auto_v1_100.hdf5 \
    --repo-id jurrr/pickup_orange_100e_v033 \
    --num-workers 4 \
    --python-executable /home/windowsuser/miniconda3/envs/isaac/bin/python \
    --push-to-hub
```

Cleanup of large datasets after creation
``` 
# Large datasets are now stored on /mnt drive (176GB available)
# Remove old/large datasets when needed:
rm /mnt/datasets/automatic_collection.hdf5
rm /mnt/datasets/auto_v1_1000.hdf5

# Or remove from symlinked path:
rm ./datasets/automatic_collection.hdf5
rm ./datasets/auto_v1_1000.hdf5

# Clean up conversion cache and temporary files after successful upload:
rm -rf /mnt/outputs/.cache/huggingface/lerobot/
rm -rf /mnt/outputs/temp/
``` 

## 5. train smolvla model based on examples

First install FFmpeg and fix video codec compatibility

```
sudo apt update
sudo apt install ffmpeg
pip uninstall torchcodec -y
pip install torchcodec==0.2.1

#Fix numpy compatibility
pip install "numpy<2"
```

Train the model from scratch (outputs saved to large drive to avoid storage issues)

```
# Create output directory on large drive for model training
export LEROBOT_CACHE_DIR=/mnt/outputs

lerobot-train \
    --batch_size=64 \
    --steps=1000 \
    --dataset.repo_id=jurrr/pickup_orange_10e \
    --policy.device=cuda \
    --policy.type=diffusion \
    --wandb.enable=false \
    --policy.repo_id=jurrr/pickup_orange_10e_policy \
    --save_freq=200 \
    --job_name=smolvla_10e_1k \
    --output_dir=/mnt/outputs/smolvla_10e_1k
```

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



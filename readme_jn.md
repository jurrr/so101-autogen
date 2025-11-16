conda activate isaac

python scripts/data_collection_automatic.py --total-success-episodes 10 --data-output ./datasets/auto_v1_10.hdf5

python scripts/hdf5_visualizer.py --hdf5_file ./datasets/auto_v1_10.hdf5

pip install lerobot==0.3.3

huggingface-cli login

python scripts/parallel_converter.py     --hdf5-root ./datasets     --hdf5-files auto_v1_10.hdf5     --repo-id jurrr/pickup_orange_10e     --num-workers 24     --python-executable /home/windowsuser/miniconda3/envs/isaac/bin/python --push-to-hub


# Install FFmpeg and fix video codec compatibility
sudo apt update
sudo apt install ffmpeg
pip uninstall torchcodec -y
pip install torchcodec==0.2.1

# Fix numpy compatibility
pip install "numpy<2"

# Train the model from scratch (using default 4 workers or auto-detect)
lerobot-train \
    --batch_size=64 \
    --steps=1000 \
    --dataset.repo_id=jurrr/pickup_orange_10e \
    --policy.device=cuda \
    --policy.type=diffusion \
    --wandb.enable=false \
    --policy.repo_id=jurrr/pickup_orange_10e_policy \
    --save_freq=200 \
    --job_name=smolvla_10e_1k
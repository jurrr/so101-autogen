#!/usr/bin/env python3

import argparse
import json
import shutil
from collections import OrderedDict
from pathlib import Path

import pandas as pd


def parse_rename_map(value: str) -> dict[str, str]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict) or not parsed:
        raise ValueError("rename-map must be a non-empty JSON object")
    for key, mapped in parsed.items():
        if not isinstance(key, str) or not isinstance(mapped, str) or not key or not mapped:
            raise ValueError("rename-map keys and values must be non-empty strings")
    return parsed


def replace_with_map(text: str, rename_map: dict[str, str]) -> str:
    updated = text
    for old_key in sorted(rename_map.keys(), key=len, reverse=True):
        updated = updated.replace(old_key, rename_map[old_key])
    return updated


def rename_dict_keys(obj, rename_map: dict[str, str]):
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            new_key = replace_with_map(key, rename_map)
            out[new_key] = rename_dict_keys(value, rename_map)
        return out
    if isinstance(obj, list):
        return [rename_dict_keys(item, rename_map) for item in obj]
    return obj


def rename_video_directories(dataset_dir: Path, rename_map: dict[str, str]) -> None:
    videos_root = dataset_dir / "videos"
    if not videos_root.exists():
        return

    for old_key, new_key in rename_map.items():
        old_dir = videos_root / old_key
        new_dir = videos_root / new_key

        if not old_dir.exists():
            continue

        if not new_dir.exists():
            old_dir.rename(new_dir)
            continue

        for item in old_dir.rglob("*"):
            if not item.is_file():
                continue
            relative = item.relative_to(old_dir)
            target = new_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise FileExistsError(f"Refusing to overwrite existing file: {target}")
            shutil.move(str(item), str(target))

        shutil.rmtree(old_dir)


def update_info_json(dataset_dir: Path, rename_map: dict[str, str], robot_type: str | None) -> str:
    info_path = dataset_dir / "meta" / "info.json"
    with info_path.open("r", encoding="utf-8") as handle:
        info = json.load(handle, object_pairs_hook=OrderedDict)

    features = info.get("features", {})
    if features:
        new_features = OrderedDict()
        for key, value in features.items():
            new_key = replace_with_map(key, rename_map)
            new_features[new_key] = rename_dict_keys(value, rename_map)
        info["features"] = new_features

    info = rename_dict_keys(info, rename_map)

    if robot_type:
        info["robot_type"] = robot_type

    with info_path.open("w", encoding="utf-8") as handle:
        json.dump(info, handle, indent=4)

    return info["codebase_version"]


def update_stats_json(dataset_dir: Path, rename_map: dict[str, str]) -> None:
    stats_path = dataset_dir / "meta" / "stats.json"
    if not stats_path.exists():
        return

    with stats_path.open("r", encoding="utf-8") as handle:
        stats = json.load(handle)

    stats = rename_dict_keys(stats, rename_map)

    with stats_path.open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=4)


def update_episodes_parquet(dataset_dir: Path, rename_map: dict[str, str]) -> None:
    episodes_root = dataset_dir / "meta" / "episodes"
    if not episodes_root.exists():
        return

    parquet_files = sorted(episodes_root.rglob("*.parquet"))
    for parquet_path in parquet_files:
        frame = pd.read_parquet(parquet_path)
        renamed_columns = {column: replace_with_map(column, rename_map) for column in frame.columns}
        frame = frame.rename(columns=renamed_columns)
        frame.to_parquet(parquet_path, index=False)


def normalize_one_dataset(dataset_dir: Path, rename_map: dict[str, str], robot_type: str | None) -> str:
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    rename_video_directories(dataset_dir, rename_map)
    codebase_version = update_info_json(dataset_dir, rename_map, robot_type)
    update_stats_json(dataset_dir, rename_map)
    update_episodes_parquet(dataset_dir, rename_map)
    return codebase_version


def ensure_dataset_available(root: Path, repo_id: str, download_missing: bool) -> Path:
    dataset_dir = root / repo_id
    if dataset_dir.exists():
        return dataset_dir

    if not download_missing:
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    from huggingface_hub import snapshot_download

    dataset_dir.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Local dataset missing. Downloading from Hub into: {dataset_dir}")
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        revision="main",
        local_dir=str(dataset_dir),
    )
    return dataset_dir


def upload_and_tag(repo_id: str, dataset_dir: Path, codebase_version: str) -> None:
    from huggingface_hub import HfApi, create_repo
    from huggingface_hub.utils import HfHubHTTPError

    create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
    api = HfApi()
    api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=str(dataset_dir),
        path_in_repo=".",
    )

    try:
        api.delete_tag(repo_id=repo_id, tag=codebase_version, repo_type="dataset")
    except HfHubHTTPError:
        pass
    api.create_tag(repo_id=repo_id, tag=codebase_version, revision="main", repo_type="dataset")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize LeRobot v3 dataset schema keys and optionally upload.")
    parser.add_argument("--repo-ids", nargs="+", required=True, help="Dataset repo ids, e.g. cmotions/custom-cube-frontwristcam-50-t3")
    parser.add_argument("--root", default="/mnt/datasets", help="Parent directory that contains <user>/<repo_name> dataset folders")
    parser.add_argument(
        "--rename-map",
        default='{"observation.images.front":"observation.images.top"}',
        help="JSON mapping of feature key renames",
    )
    parser.add_argument("--robot-type", default=None, help="Optional robot_type override for meta/info.json")
    parser.add_argument("--upload", action="store_true", help="Upload normalized dataset(s) to Hub and refresh codebase tag")
    parser.add_argument(
        "--download-missing",
        action="store_true",
        help="If local dataset folder is missing, download main revision from Hub into --root before normalization",
    )

    args = parser.parse_args()
    rename_map = parse_rename_map(args.rename_map)
    root = Path(args.root).expanduser().resolve()

    for repo_id in args.repo_ids:
        dataset_dir = ensure_dataset_available(root, repo_id, args.download_missing)
        print(f"Normalizing: {repo_id}")
        codebase_version = normalize_one_dataset(dataset_dir, rename_map, args.robot_type)
        print(f"  Updated local dataset at: {dataset_dir}")
        print(f"  codebase_version: {codebase_version}")

        if args.upload:
            upload_and_tag(repo_id, dataset_dir, codebase_version)
            print(f"  Uploaded and tagged: {repo_id}@{codebase_version}")


if __name__ == "__main__":
    main()

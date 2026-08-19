"""Upload the masked full-record release to its private R2 bucket.

The manifest is uploaded only after every referenced Parquet asset succeeds.
Run without ``--execute`` to validate the local release and print the plan.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "public" / "full-data"
DEFAULT_BUCKET = "freddie-mac-crt-disclosure-data"
WRANGLER = ("npx", "--yes", "wrangler@4.123.0")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument(
        "--profile",
        help="Optional named Wrangler auth profile; defaults to the active profile.",
    )
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def load_release(source: Path) -> tuple[dict[str, object], list[Path]]:
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    release = manifest.get("release")
    assets = manifest.get("assets")
    if not isinstance(release, str) or not release:
        raise ValueError("manifest release is missing")
    if not isinstance(assets, list) or not assets:
        raise ValueError("manifest assets are missing")

    paths: list[Path] = []
    for item in assets:
        if not isinstance(item, dict) or not isinstance(item.get("asset"), str):
            raise TypeError("manifest contains an invalid asset entry")
        path = source / item["asset"]
        expected_bytes = item.get("bytes")
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != expected_bytes:
            raise ValueError(f"size mismatch for {path.name}")
        paths.append(path)

    if len(paths) != manifest.get("partitions"):
        raise ValueError("partition count does not match manifest assets")
    return manifest, paths


def put_object(
    bucket: str,
    release: str,
    path: Path,
    content_type: str,
    profile: str | None,
    retries: int,
) -> str:
    target = f"{bucket}/{release}/{path.name}"
    profile_args = ("--profile", profile) if profile else ()
    command = (
        *WRANGLER,
        "r2",
        "object",
        "put",
        target,
        "--file",
        str(path),
        "--content-type",
        content_type,
        "--storage-class",
        "Standard",
        "--remote",
        *profile_args,
    )
    for attempt in range(retries + 1):
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if not result.returncode:
            return path.name
        if attempt < retries:
            time.sleep(2**attempt)
    detail = (result.stderr or result.stdout).strip()
    raise RuntimeError(f"upload failed for {path.name}: {detail}")


def main() -> int:
    args = parse_args()
    if args.workers < 1 or args.workers > 12:
        raise ValueError("workers must be between 1 and 12")
    if args.retries < 0 or args.retries > 5:
        raise ValueError("retries must be between 0 and 5")

    source = args.source.resolve()
    manifest, assets = load_release(source)
    release = str(manifest["release"])
    total_bytes = sum(path.stat().st_size for path in assets)
    print(
        f"validated {len(assets)} assets ({total_bytes:,} bytes) for "
        f"r2://{args.bucket}/{release}/"
    )
    if not args.execute:
        print("dry run complete; pass --execute to upload")
        return 0

    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                put_object,
                args.bucket,
                release,
                path,
                "application/vnd.apache.parquet",
                args.profile,
                args.retries,
            ): path
            for path in assets
        }
        for future in as_completed(futures):
            future.result()
            completed += 1
            if completed % 20 == 0 or completed == len(assets):
                print(f"uploaded {completed}/{len(assets)} assets", flush=True)

    put_object(
        args.bucket,
        release,
        source / "manifest.json",
        "application/json",
        args.profile,
        args.retries,
    )
    print("uploaded manifest.json last; release is complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import os
from pathlib import Path

# 必须在 import huggingface_hub 之前设置镜像
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from huggingface_hub import snapshot_download

PROJECT_ROOT = Path(__file__).resolve().parent
MODELS_DIR = PROJECT_ROOT / "models"

# 只下载运行所需文件，跳过 onnx/openvino 等大文件
IGNORE_PATTERNS = ["onnx/*", "openvino/*", "train_script.py"]

MODELS = [
    ("sentence-transformers/all-mpnet-base-v2", MODELS_DIR / "all-mpnet-base-v2"),
    ("sentence-transformers/all-MiniLM-L6-v2", MODELS_DIR / "all-MiniLM-L6-v2"),
]


def is_model_complete(model_dir: Path) -> bool:
    if not model_dir.exists():
        return False

    has_config = (model_dir / "config.json").exists()
    has_weights = (model_dir / "model.safetensors").exists() or (
        model_dir / "pytorch_model.bin"
    ).exists()
    has_tokenizer = (model_dir / "tokenizer.json").exists() or (
        model_dir / "vocab.txt"
    ).exists()

    return has_config and has_weights and has_tokenizer


def download_one(repo_id: str, local_dir: Path) -> None:
    print(f"\n开始下载 {repo_id} ...")
    print(f"保存到: {local_dir}")
    print(f"镜像: {os.environ.get('HF_ENDPOINT')}")

    local_dir.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=repo_id,
        local_dir=str(local_dir),
        ignore_patterns=IGNORE_PATTERNS,
    )

    if not is_model_complete(local_dir):
        raise RuntimeError(
            f"模型不完整: {local_dir}\n"
            "请检查网络/代理，或从 HuggingFace 网页手动下载必需文件后放到该目录。"
        )

    print(f"下载完成: {local_dir}")


def main() -> None:
    failed = []

    for repo_id, local_dir in MODELS:
        try:
            if is_model_complete(local_dir):
                print(f"\n已存在完整模型，跳过: {local_dir}")
                continue
            download_one(repo_id, local_dir)
        except Exception as exc:
            print(f"\n下载失败 {repo_id}: {exc}")
            failed.append(repo_id)

    if failed:
        print("\n以下模型下载失败:")
        for repo_id in failed:
            print(f"  - {repo_id}")
        print("\n可尝试:")
        print("  1. 配置代理后重试")
        print("  2. 浏览器从 https://hf-mirror.com 手动下载到 models/ 对应目录")
        raise SystemExit(1)

    print("\n全部模型就绪。")


if __name__ == "__main__":
    main()

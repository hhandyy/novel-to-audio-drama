import json
import os
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from . import CONFIG_DIR, NOVELS_DIR, VOICE_DIR

def load_config():
    with open(CONFIG_DIR, "r", encoding="utf-8") as f:
        return json.load(f)
        

def hex_to_wav(hex_str: str, output_path: Path):
    """将 hex 编码音频转为 WAV 文件"""
    try:
        audio_bytes = bytes.fromhex(hex_str)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
    except Exception as e:
        raise RuntimeError(f"Hex 转 WAV 失败: {e}")


def generate_voice_for_role(
    role: str,
    description: str,
    config: dict,
    voice_library_dir: Path,
    metadata_path: Path,
    preview_text: str = "人生就像海洋，只有意志坚强的人才能到达彼岸。"
) -> str:
    """
    调用 MiniMax API 生成音色，返回绝对路径
    """
    api_cfg = config["minimax"]["voice_design"]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_cfg['api_token']}"
    }
    payload = {
        "prompt": description,
        "preview_text": preview_text
    }

    response = requests.post(
        api_cfg["url"],
        json=payload,
        headers=headers,
        timeout=30
    )
    resp_json = response.json()

    if resp_json.get("base_resp", {}).get("status_code") != 0:
        msg = resp_json.get("base_resp", {}).get("status_msg", "Unknown error")
        raise RuntimeError(f"MiniMax API 错误: {msg}")

    hex_audio = resp_json["trial_audio"]
    voice_id = resp_json["voice_id"]

    # 仅用时间戳命名
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]  # 精确到微秒前6位，避免重复
    filename = f"{timestamp}.wav"
    wav_path = voice_library_dir / filename

    # 保存音频
    hex_to_wav(hex_audio, wav_path)

    # 安全更新 metadata（读-改-写）
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {}

    metadata[filename] = {
        "prompt": description,
        "role_hint": role,
        #"voice_id": voice_id,
        #"generated_at": timestamp
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return str(wav_path.resolve())


def sync_role_to_voice(novel_name: str, config_path: Optional[Path] = None):
    """
    为指定小说的角色生成缺失音色，并更新 role_to_voice.json
    可被 FastAPI 或 CLI 调用
    """
    config = load_config()

    voice_library_dir = VOICE_DIR
    voice_library_dir.mkdir(exist_ok=True)
    metadata_path = voice_library_dir / "metadata.json"

    novel_dir = NOVELS_DIR / novel_name
    characters_path = novel_dir / "characters.json"
    role_to_voice_path = novel_dir / "role_to_voice.json"

    if not characters_path.exists():
        raise FileNotFoundError(f"未找到 characters.json: {characters_path}")

    with open(characters_path, "r", encoding="utf-8") as f:
        characters = json.load(f)

    # 加载现有映射
    if role_to_voice_path.exists():
        with open(role_to_voice_path, "r", encoding="utf-8") as f:
            role_to_voice: Dict[str, str] = json.load(f)
    else:
        role_to_voice = {}

    updated = False
    for char in characters:
        role = char["role"]
        description = char["descript"]

        # 检查是否已存在且文件有效
        existing_path = role_to_voice.get(role)
        if existing_path and Path(existing_path).exists():
            print(f"✅ 角色 '{role}' 音色已存在，跳过")
            continue

        # 生成新音色
        try:
            wav_path = generate_voice_for_role(
                role=role,
                description=description,
                config=config,
                voice_library_dir=voice_library_dir,
                metadata_path=metadata_path
            )
            role_to_voice[role] = wav_path
            updated = True
            print(f"✨ 已为 '{role}' 生成音色: {wav_path}")
        except Exception as e:
            print(f"❌ 生成 '{role}' 音色失败: {e}")
            continue

    if updated:
        with open(role_to_voice_path, "w", encoding="utf-8") as f:
            json.dump(role_to_voice, f, ensure_ascii=False, indent=2)
        print(f"✅ role_to_voice.json 已更新: {role_to_voice_path}")
    else:
        print("ℹ️ 无新角色需要生成音色")

    return str(role_to_voice_path)


# ====== CLI 入口 ======
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="为小说角色生成并管理音色")
    parser.add_argument("--novel", required=True, help="小说名称")
    args = parser.parse_args()

    sync_role_to_voice(args.novel)
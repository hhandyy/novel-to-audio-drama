import json
import os
import tempfile
import subprocess
from pathlib import Path
from pydub import AudioSegment
from . import NOVELS_DIR

def generate_tts_audio(novel_name: str, chapter_id: str):
    """
    根据 script.json 和 role_to_voice.json 生成有声剧
    """
    INDEXTTS_PATH = os.environ.get("INDEXTTS_PATH", "/root/index-tts")
    B_DIR = Path(INDEXTTS_PATH)

    NOVEL_DIR = NOVELS_DIR / novel_name
    CHAPTER_DIR = NOVEL_DIR / "chapters" / chapter_id
    SEGMENTS_DIR = CHAPTER_DIR / "segments"

    SCRIPT_PATH = CHAPTER_DIR / "script.json"
    ROLE_MAP_PATH = NOVEL_DIR / "role_to_voice.json"

    for p, name in [(SCRIPT_PATH, "剧本"), (ROLE_MAP_PATH, "角色音色映射")]:
        if not p.exists():
            raise FileNotFoundError(f"{name}不存在: {p}")

    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        script_data = json.load(f)
    with open(ROLE_MAP_PATH, "r", encoding="utf-8") as f:
        role_map = json.load(f)

    task = {"lines": []}
    for i, line in enumerate(script_data["lines"]):
        role = line["role"]
        if role not in role_map:
            raise ValueError(f"角色 '{role}' 未定义")
        ref_audio_abs = (B_DIR / role_map[role]).resolve()
        if not ref_audio_abs.exists():
            raise FileNotFoundError(f"参考音频不存在: {ref_audio_abs}")
        task["lines"].append({
            "index": i,
            "text": line["text"],
            "ref_audio": str(ref_audio_abs),
            "output_wav": str(SEGMENTS_DIR / f"segment_{i:03d}.wav")
        })

    # 写入临时任务文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, dir=B_DIR, encoding='utf-8') as tmpf:
        json.dump(task, tmpf, ensure_ascii=False, indent=2)
        task_json_path = Path(tmpf.name)

    batch_script_content = f'''
import json, sys
sys.path.insert(0, ".")
from indextts.infer_v2 import IndexTTS2

with open(r"{task_json_path}", "r", encoding="utf-8") as f:
    task = json.load(f)

tts = IndexTTS2(
    cfg_path="checkpoints/config.yaml",
    model_dir="checkpoints",
    use_fp16=True,
    use_cuda_kernel=False,
    use_deepspeed=False
)

for item in task["lines"]:
    tts.infer(
        spk_audio_prompt=item["ref_audio"],
        text=item["text"],
        output_path=item["output_wav"],
        emo_alpha=0.3,
        use_emo_text=True,
        use_random=True,
        verbose=False
    )
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=B_DIR, encoding='utf-8') as tmpf:
        tmpf.write(batch_script_content)
        batch_script_path = Path(tmpf.name)

    try:
        print(f"🚀 开始生成音频...")
        subprocess.run(["uv", "run", batch_script_path.name], cwd=B_DIR, check=True)
    finally:
        task_json_path.unlink(missing_ok=True)
        batch_script_path.unlink(missing_ok=True)

    # 拼接音频
    combined = AudioSegment.empty()
    for i in range(len(script_data["lines"])):
        seg = AudioSegment.from_wav(SEGMENTS_DIR / f"segment_{i:03d}.wav")
        combined += seg + AudioSegment.silent(duration=500)
    final_output = SEGMENTS_DIR / "full_drama.wav"
    combined.export(final_output, format="wav")
    print(f"✅ 有声剧生成完成: {final_output}")
    return str(final_output)


# ====== CLI 入口 ======
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="生成小说章节的有声剧")
    parser.add_argument("--novel", required=True)
    parser.add_argument("--chapter", required=True)
    args = parser.parse_args()
    generate_tts_audio(args.novel, args.chapter)
# novel_init.py
import re
import json
from pathlib import Path
from charset_normalizer import from_path
from typing import List, Optional
from . import NOVELS_DIR,VOICE_DIR

def read_text_robustly(file_path: Path) -> str:
    """
    使用 charset-normalizer 自动检测编码并读取文本，
    自动处理非法字节（errors='replace'）
    """
    result = from_path(file_path).best()
    if result is None:
        raise RuntimeError(f"无法检测文件编码: {file_path}")
    return str(result)

def init_novel(
    novel_file: str,
    chapter_pattern: str = r"^[ \t\u3000]*(?:第)?[零一二三四五六七八九十百千\d]{1,10}[章话节]",
    novel_name: Optional[str] = None
):
    """
    初始化小说项目结构
    
    Args:
        novel_file: 小说全文文件路径（如 "凡人修仙传.txt"）
        chapter_pattern: 用于分割章节的正则表达式
        novel_name: 小说名（若未提供，则用文件名去掉后缀）
    """
    novel_path = Path(novel_file).resolve()
    if not novel_path.exists():
        raise FileNotFoundError(f"小说文件不存在: {novel_path}")

    # 确定小说名
    if novel_name is None:
        novel_name = novel_path.stem  # 去掉 .txt 后缀
    
    novel_dir = NOVELS_DIR  / novel_name
    novel_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir = novel_dir / "chapters"
    chapters_dir.mkdir(exist_ok=True)

    content = read_text_robustly(novel_path)
    raw_all_path = novel_dir / "raw_all.txt"
    raw_all_path.write_text(content, encoding="utf-8")
    print(f"已保存全文（UTF-8）到: {raw_all_path}")

    # === 按章节分割（保留标题行）===
    lines = content.splitlines()
    chapters: List[List[str]] = []
    current_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if re.search(chapter_pattern, stripped):
            if current_lines:
                chapters.append(current_lines)
                current_lines = []
            current_lines.append(stripped)  # 标题行作为章节第一行
        else:
            current_lines.append(stripped)

    if current_lines:
        chapters.append(current_lines)

    if not chapters:
        # 若无匹配，整本书作为第一章（保留所有非空行）
        chapters = [[line.strip() for line in lines if line.strip()]]

    # === 写入各章节 raw.txt ===
    for i, ch_lines in enumerate(chapters, start=1):  # 注意：不再解包 (title, lines)
        ch_dir = chapters_dir / f"ch_{i}"
        ch_dir.mkdir(exist_ok=True)
        (ch_dir / "raw.txt").write_text("\n".join(ch_lines), encoding="utf-8")
        print(f"📄 章节 {i}: {len(ch_lines)} 行")

    print(f"✅ 共创建 {len(chapters)} 个章节")

    # === 初始化 characters.json（默认含旁白）===
    characters_path = novel_dir / "characters.json"
    if not characters_path.exists():
        default_characters = [
            {
                "role": "旁白",
                "descript": "旁白，使用默认旁白音频。",
                "id": 1
            }
        ]
        with open(characters_path, "w", encoding="utf-8") as f:
            json.dump(default_characters, f, ensure_ascii=False, indent=2)
        print(f"📝 已初始化 characters.json: {characters_path}")
    else:
        print(f"ℹ️ characters.json 已存在，跳过初始化")

    # === 初始化 role_to_voice.json（默认包含旁白音色）===
    role_to_voice_path = novel_dir / "role_to_voice.json"
    if not role_to_voice_path.exists():
        # 注意：确保该 WAV 文件确实存在！
        default_mapping = {
            "旁白": str(VOICE_DIR / "默认旁白.wav")
        }
        with open(role_to_voice_path, "w", encoding="utf-8") as f:
            json.dump(default_mapping, f, ensure_ascii=False, indent=2)
        print(f"📝 已初始化 role_to_voice.json: {role_to_voice_path}")
    else:
        print(f"ℹ️ role_to_voice.json 已存在，跳过初始化")

    print(f"\n🎉 小说 [{novel_name}] 初始化完成！")
    print(f"📁 路径: {novel_dir}")
    return str(novel_dir)


# ====== CLI 入口 ======
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="初始化小说项目结构")
    parser.add_argument("--novel_file", help="小说全文文件路径（如 凡人修仙传.txt）")  # 改为位置参数
    parser.add_argument("--pattern", default=r"^[ \t\u3000]*(?:第)?[零一二三四五六七八九十百千\d]{1,10}[章话节]", 
                        help='章节分隔正则表达式（默认匹配 "第一章"、"100话" 等）')
    parser.add_argument("--name", help="小说名称（可选，默认取文件名）")
    args = parser.parse_args()

    init_novel(
        novel_file=args.novel_file,
        chapter_pattern=args.pattern,
        novel_name=args.name
    )
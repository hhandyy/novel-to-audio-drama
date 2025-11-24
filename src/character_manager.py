import json
import re
from pathlib import Path
from openai import OpenAI
from . import CONFIG_DIR, NOVELS_DIR

def load_config():
    with open(CONFIG_DIR, "r", encoding="utf-8") as f:
        return json.load(f)

def get_all_roles_from_script(novel_name: str, chapter_id: str):
    """从 script.json 提取所有角色名（去重，保留顺序）"""
    script_path = NOVELS_DIR / novel_name / "chapters" / chapter_id / "script.json"
    with open(script_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    roles = []
    seen = set()
    for line in data["lines"]:
        role = line["role"]
        if role not in seen:
            roles.append(role)
            seen.add(role)
    return roles

def generate_character_profile(novel_name: str, new_role: str, context_snippet: str = "") -> dict:
    """
    调用 LLM 为新角色生成性格档案
    """
    config = load_config()
    llm_cfg = config["llm"]["character_profile"]
    client = OpenAI(api_key=llm_cfg["api_key"], base_url=llm_cfg["base_url"])
    
    prompt = f"""请基于以下上下文，为小说《{novel_name}》中首次出现的角色“{new_role}”生成一份合理的人物档案。

上下文理论上包含对该角色的描写（可能是外貌、言行、他人评价、身份背景等）。请优先忠实复述或提炼原文信息；若原文信息有限，可结合常见修仙/玄幻/都市等类型设定进行合理推断，但不得凭空编造与上下文冲突的内容。

至少应明确该角色的性别（男/女/其他（雄/雌））和大致年龄段（如少年、青年、中年、老年，或具体岁数）。在此基础上，尽可能描述其性格特征、说话方式和身世背景——这些可以来自作者对其的直接描写，也可以从对话、行为、称谓、反应等侧面细节中合理具象化。

上下文参考：
{context_snippet}
请以纯 JSON 格式输出，仅包含一个对象，字段为：
"role"：角色名（即 "{new_role}"）
"descript"：一段自然语言描述，整合上述所有信息
不要包含任何额外字段、解释、注释或格式，只输出合法 JSON。
"""

    completion = client.chat.completions.create(
        model=llm_cfg["model"],
        messages=[{"role": "user", "content": prompt}],
        #temperature=0.5,
        max_tokens=5120
    )
    response = completion.choices[0].message.content

    # 提取 JSON
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response, re.IGNORECASE)
    json_str = match.group(1).strip() if match else response.strip()
    try:
        profile = json.loads(json_str)
    except json.JSONDecodeError:
        # 容错：尝试修复
        json_str = re.sub(r",\s*[}\]]", lambda m: m.group(0)[-1], json_str)
        json_str = json_str.replace("'", '"')
        profile = json.loads(json_str)

    # 确保必要字段
    for key in ["role", "descript"]:
        if key not in profile:
            profile[key] = None
    return profile

def manage_characters(novel_name: str, chapter_id: str):
    """
    主函数：更新小说的角色性格库
    """
    CHARACTERS_PATH = NOVELS_DIR / novel_name / "characters.json"

    # 加载现有角色库（若存在）
    if CHARACTERS_PATH.exists():
        with open(CHARACTERS_PATH, "r", encoding="utf-8") as f:
            characters = json.load(f)
        existing_roles = {char["role"] for char in characters}
        next_id = max((char.get("id", 0) for char in characters), default=0) + 1
    else:
        characters = []
        existing_roles = set()
        next_id = 1

    # 获取本章节所有角色（按首次出现顺序）
    all_roles = get_all_roles_from_script(novel_name, chapter_id)
    new_roles = [role for role in all_roles if role not in existing_roles]

    if not new_roles:
        print("✅ 无新角色，角色库无需更新")
        return str(CHARACTERS_PATH)

    print(f"🔍 发现 {len(new_roles)} 个新角色: {new_roles}")

    # 为每个新角色生成档案
    for role in new_roles:
        # 可选：提取该角色在 script.json 中的前几句作为上下文
        context_lines = []
        raw_txt_path = NOVELS_DIR / novel_name / "chapters" / chapter_id / "raw.txt"
        if not raw_txt_path.exists():
            raise FileNotFoundError(f"未找到原始小说文本: {raw_txt_path}")

        with open(raw_txt_path, "r", encoding="utf-8") as f:
            raw_text = f.read().strip()
        if not raw_text:
            raise ValueError(f"{raw_txt_path} 内容为空")

        profile = generate_character_profile(novel_name, role, raw_text)
        profile["id"] = next_id
        next_id += 1
        characters.append(profile)
        print(f"✨ 已生成角色档案: {role}")

    # 保存
    with open(CHARACTERS_PATH, "w", encoding="utf-8") as f:
        json.dump(characters, f, ensure_ascii=False, indent=2)

    print(f"✅ 角色库已更新: {CHARACTERS_PATH}")
    return str(CHARACTERS_PATH)


# CLI 入口
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="更新小说角色性格库")
    parser.add_argument("--novel", required=True)
    parser.add_argument("--chapter", required=True)
    args = parser.parse_args()
    manage_characters(args.novel, args.chapter)
import json
import re
from pathlib import Path
from openai import OpenAI
from . import CONFIG_DIR, NOVELS_DIR

def load_config():
    with open(CONFIG_DIR, "r", encoding="utf-8") as f:
        return json.load(f)

def convert_novel_to_script(novel_name: str, chapter_id: str):
    """
    将 novels/{novel}/chapters/{chapter}/raw.txt 转换为 script.json
    """
    RAW_TXT_PATH = NOVELS_DIR / novel_name / "chapters" / chapter_id / "raw.txt"
    SCRIPT_JSON_PATH = NOVELS_DIR / novel_name / "chapters" / chapter_id / "script.json"

    if not RAW_TXT_PATH.exists():
        raise FileNotFoundError(f"未找到原始小说文本: {RAW_TXT_PATH}")

    with open(RAW_TXT_PATH, "r", encoding="utf-8") as f:
        raw_text = f.read().strip()
    if not raw_text:
        raise ValueError(f"{RAW_TXT_PATH} 内容为空")

    # 加载 LLM 配置
    config = load_config()
    llm_cfg = config["llm"]["novel_to_script"]
    client = OpenAI(api_key=llm_cfg["api_key"], base_url=llm_cfg["base_url"])

    json_example = """
{
      "lines": [
        {
          "role": "旁白",
          "text": "傍晚时分，宗内。"
        },
        {
          "role": "旁白",
          "text": "老者徐徐说到："
        },
        {
          "role": "旁白",
          "text": "师弟，天南第一集会要开了。"
        },
        {
          "role": "韩立",
          "text": "待我将宝物收好。"
        },
        {
          "role": "旁白",
          "text": "韩立放下手中竹简，说道："
        },
        {
          "role": "韩立",
          "text": "那老狐狸也会去么？"
        },
        {
          "role": "银月",
          "text": "自是会去的，主人。"
        },
        {
          "role": "旁白",
          "text": "银月蹦跳地过来，拿起竹简放入包中。"
        },
    ]
}
"""
    PROMPT = f"""你是一位专业的有声书剧本改编师。请将以下小说片段转换为结构化的有声书剧本，严格遵循以下规则：

1. 输出必须是纯 JSON 格式，仅包含一个顶层对象，其字段为 "lines"，值为对象列表。
2. 每个对象包含两个字段："role"（角色名）和 "text"（该角色说出的完整台词或旁白叙述的完整语句）。

【角色命名原则】
3. "role" 字段**只能是以下两类之一**：
   - 具体的角色名字（如“韩立”“银月”“南宫婉”等），这些名字必须在当前或上下文片段中**明确出现过**；
   - “旁白”。
   不得使用任何泛指、身份描述或模糊称谓（如“老者”“青年”“黑衣人”“管家”“众人”“他”等）作为角色名。
4. 判断某句对话是否归属具体角色，需同时满足：
   a) 该角色的名字已在原文中出现（不一定在同一句）；
   b) 通过上下文、自称（如“本座”“小女子”）、对话对象称呼（如“韩兄”“银月姑娘”）或情节逻辑，能合理地确定说话人就是该具体角色。
   若满足，则 "role" 使用该具体名字。
5. 凡不满足第4条的情况（包括说话者为群体、临时角色、身份不明者，或虽有描写但无具体名字），其话语及引导语一律由“旁白”转述。
6. 严禁因“原文未写‘XXX说’”而将可合理归因于已知名字角色的台词转为旁白；也严禁为无名字角色虚构或保留模糊称谓。

【条目拆分规则】
7. 必须严格按语义单元与原文结构拆分条目：
   a. 原文每开始一个新段落（即出现换行），无论说话人是否变化，均需拆分为独立条目；
   b. 若单段内混合了角色对话与叙述性内容（如动作、神态、引导语如“说道”“惊呼”等），须将对话部分提取为对应角色台词，其余叙述内容作为“旁白”条目，拆分为多条，旁白转述与角色自述之间不能存在重复内容；
   c. 同一角色的多句台词，若中间插入了旁白或其他内容，即使语义连贯，也必须分别作为独立条目处理。

【内容过滤规则】
8. 若原文包含与正篇叙事无关的内容（如作者感言、章节备注、致谢、互动留言、广告等，通常出现在章末或独立段落），请完全忽略，不予处理。

请直接输出符合上述规则的 JSON，不要包含任何解释、注释或额外文本。

【One-Shot 示例参考】
输入原文：
傍晚时分，宗内。
老者徐徐说到：“师弟，天南第一集会要开了”。
“待我将宝物收好”，韩立放下手中竹简，说道：“那老狐狸也会去么？”
“自是会去的，主人”。银月蹦跳地过来，拿起竹简放入包中。

整理为：{json_example}

小说原文：
{raw_text}
""" 
    print("🧠 正在调用 LLM 转换小说为剧本...")
    completion = client.chat.completions.create(
        model=llm_cfg["model"],
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=4096
    )
    response_text = completion.choices[0].message.content

    # 解析 JSON
    def extract_json(text):
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
        json_str = match.group(1).strip() if match else text.strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = re.sub(r",\s*[}\]]", lambda m: m.group(0)[-1], json_str)
            json_str = json_str.replace("'", '"')
            return json.loads(json_str)

    result = extract_json(response_text)

    # 验证
    if not isinstance(result, dict) or not isinstance(result.get("lines"), list):
        raise ValueError("LLM 返回格式无效")

    for i, item in enumerate(result["lines"]):
        if not (isinstance(item, dict) and "role" in item and "text" in item):
            raise ValueError(f"第 {i+1} 行格式错误")

    # 保存
    with open(SCRIPT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 剧本已保存至: {SCRIPT_JSON_PATH}")
    return str(SCRIPT_JSON_PATH)


# ====== CLI 入口 ======
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="将小说 raw.txt 转换为剧本 script.json")
    parser.add_argument("--novel", required=True)
    parser.add_argument("--chapter", required=True)
    args = parser.parse_args()
    convert_novel_to_script(args.novel, args.chapter)
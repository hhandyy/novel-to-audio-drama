# AINovelCast-自动化有声小说生成器

## 简介
**从小说文本开始，一键自动化生成具有专业配音效果的多角色有声小说，告别传统单一音色或手动配置的繁琐流程。**

## 安装与配置

### 1. 准备
本地或服务器安装好index-tts，用于将文本转语音
项目地址：https://github.com/index-tts/index-tts.git

### 2. 下载依赖库
克隆本仓库：
```bash
git clone https://github.com/hhandyy/AINovelCast.git
cd AINovelCast
uv sync
```

### 3. 配置API密钥
在项目根目录下找到 `config.json` 文件，填写openai格式的大模型API密钥：
```json
{
  "llm": {
    "novel_to_script": { 
      "api_key": "",
      "base_url": "",
      "model": ""
    },
    "character_profile": {
      "api_key": "",
      "base_url": "",
      "model": ""
    }
  },
  "minimax": {
    "voice_design": {
      "url": "https://api.minimaxi.com/v1/voice_design",
      "api_token": "YOUR_MINIMAX_API_TOKEN_HERE"
    }
  }
}
```
novel_to_script用于调用大模型将文本转换为剧本 
character_profile调用大模型为新角色提供性格描写 
voice_design调用minmax的speech模型通过性格描写生成一段音色。 

### 4. 设置环境变量
为了使程序能够找到Index TTS的位置，请设置如下环境变量：
```bash
export INDEXTTS_PATH=/path/to/your/index-tts
```
注意：此路径应指向你本地安装了Index TTS的具体位置。

### 5. 启动Web界面
一切就绪后，可以通过Streamlit运行图形化界面：
```bash
uv run streamlit run web_ui.py
```
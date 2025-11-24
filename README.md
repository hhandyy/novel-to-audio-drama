# 小说转有声小说生成器

本项目旨在利用大模型技术将文字形式的小说转换成带有语音的有声书。通过一系列自动化步骤，从文本分析到最终音频合成，实现高质量的有声内容产出。

## 功能概述
- **初始化小说**：解析并存储小说章节。
- **剧本转换**：根据小说内容生成剧本。
- **角色管理**：识别并定义每个角色的性格特征。
- **音色同步**：基于角色性格设计相应的说话声音。
- **TTS音频生成**：利用TTS技术合成最终的有声书。

## 安装与配置

### 1. 准备
本地或服务器安装好index-tts，用于将文本转语音
项目地址：https://github.com/index-tts/index-tts.git

### 2. 下载依赖库
克隆本仓库：
```bash
git clone https://github.com/hhandyy/novel-to-audio-drama.git
cd novel-to-audio-drama
uv sync
```

### 3. 配置API密钥
在项目根目录下找到 `config.json` 文件，按填写相关服务的API密钥：
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
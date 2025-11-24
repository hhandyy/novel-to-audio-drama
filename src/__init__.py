# src/__init__.py
from pathlib import Path

# 项目根目录 = src 的父目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

#配置目录
CONFIG_DIR = PROJECT_ROOT / "config.json"

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
NOVELS_DIR = DATA_DIR / "novels"
UPLOAD_DIR = DATA_DIR / "upload"
VOICE_DIR = DATA_DIR / "people_voice"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
NOVELS_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
VOICE_DIR.mkdir(exist_ok=True)

from .novel_init import init_novel
from .novel_parser import convert_novel_to_script
from .character_manager import manage_characters
from .voice_manager import sync_role_to_voice
from .tts_generator import generate_tts_audio
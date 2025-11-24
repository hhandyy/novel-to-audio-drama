import streamlit as st
from pathlib import Path
import json
import re
from src import (
    init_novel,
    convert_novel_to_script,
    manage_characters,
    sync_role_to_voice,
    generate_tts_audio,
    NOVELS_DIR,
    VOICE_DIR
)

# 页面配置
st.set_page_config(page_title="Narrative AI - 有声小说生成器", layout="wide")
st.title("🎙️ Narrative AI - 有声小说生成器 (V1)")

# ========== 左侧边栏：小说 & 章节选择 ==========
with st.sidebar:
    st.header("📚 小说库")

    # 获取小说列表
    novels = sorted([d.name for d in NOVELS_DIR.iterdir() if d.is_dir()]) if NOVELS_DIR.exists() else []
    
    if novels:
        selected_novel = st.selectbox("选择小说", novels, key="sidebar_novel")
        novel_path = NOVELS_DIR / selected_novel
        chapters_dir = novel_path / "chapters"

        if chapters_dir.exists():
            # 获取章节并自然排序（ch_1, ch_2, ..., ch_10）
            raw_chapters = [d.name for d in chapters_dir.iterdir() if d.is_dir()]
            def natural_sort_key(s):
                return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]
            chapters = sorted(raw_chapters, key=natural_sort_key)
            
            selected_chapter = st.selectbox("选择章节", chapters, key="sidebar_chapter")
        else:
            selected_novel = None
            selected_chapter = None
            st.warning("无章节目录")
    else:
        selected_novel = None
        selected_chapter = None
        st.info("暂无小说")

# ========== 主区域：功能面板 ==========
tab1, tab2, tab3 = st.tabs(["📥 初始化小说", "⚙️ 生成章节音频", "🎭 自定义角色音色"])

# --- Tab 1: 上传小说 ---
with tab1:
    st.subheader("上传并初始化新小说")
    novel_file = st.file_uploader("选择小说文本文件 (.txt)", type=["txt"])
    original_name = None
    if novel_file is not None:
        original_name = Path(novel_file.name).stem
    novel_name = st.text_input("小说名称（默认上传文件名）", placeholder=original_name)
    chapter_pattern = st.text_input(
        "章节分隔正则",
        value=r"^[ \t\u3000]*(?:第)?[零一二三四五六七八九十百千\d]{1,10}[章话节]"
    )

    if st.button("初始化小说") and novel_file and novel_name and chapter_pattern:
        upload_path = Path("data/upload") / f"{novel_name}.txt"
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        with open(upload_path, "wb") as f:
            f.write(novel_file.getvalue())
        
        try:
            init_novel(
                novel_file=str(upload_path),
                chapter_pattern=chapter_pattern,
                novel_name=novel_name
            )
            st.success(f"✅ 小说 [{novel_name}] 初始化成功！")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 初始化失败: {str(e)}")

# --- Tab 2: 生成章节 ---
with tab2:
    if not selected_novel or not selected_chapter:
        st.info("请在左侧边栏选择小说和章节")
    else:
        st.subheader(f"处理章节：{selected_novel} / {selected_chapter}")
        ch_path = NOVELS_DIR / selected_novel / "chapters" / selected_chapter
        audio_file = ch_path / "full_drama.wav"
        audio_exists = audio_file.exists()

        if audio_exists:
            st.success("✅ 音频已生成")
            # 提供下载
            with open(audio_file, "rb") as f:
                default_name = f"{selected_novel}_{selected_chapter}.wav"
                st.download_button(
                    label="📥 下载音频",
                    data=f,
                    file_name=default_name,
                    mime="audio/wav"
                )
        else:
            st.warning("⏳ 音频尚未生成")

        if st.button("🚀 生成本章音频"):
            with st.spinner("正在处理中，请稍候..."):
                try:
                    convert_novel_to_script(selected_novel, selected_chapter)
                    manage_characters(selected_novel, selected_chapter)
                    sync_role_to_voice(selected_novel)
                    generate_tts_audio(selected_novel, selected_chapter)
                    st.success("🎉 生成完成！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 生成失败: {e}")

        # --- 批量操作区域 ---
        st.divider()
        st.subheader("📦 批量操作")

        if chapters_dir.exists():
            raw_chapters = [d.name for d in chapters_dir.iterdir() if d.is_dir()]
            def natural_sort_key(s):
                return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]
            all_chapters = sorted(raw_chapters, key=natural_sort_key)

            col1, col2 = st.columns(2)
            start_ch = col1.selectbox("起始章节", all_chapters, index=0, key="batch_start")
            end_ch = col2.selectbox("结束章节", all_chapters, index=min(len(all_chapters)-1, 5), key="batch_end")

            # 确保起止顺序合理
            start_idx = all_chapters.index(start_ch)
            end_idx = all_chapters.index(end_ch)
            if start_idx > end_idx:
                start_ch, end_ch = end_ch, start_ch
                start_idx, end_idx = end_idx, start_idx
            batch_chapters = all_chapters[start_idx:end_idx+1]

            st.write(f"将处理 {len(batch_chapters)} 章节: {start_ch} → {end_ch}")

            # 批量生成按钮
            if st.button("🔁 批量生成选中章节"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                for i, ch in enumerate(batch_chapters):
                    status_text.text(f"正在处理 {ch} ({i+1}/{len(batch_chapters)})...")
                    progress_bar.progress((i + 1) / len(batch_chapters))
                    try:
                        convert_novel_to_script(selected_novel, ch)
                        manage_characters(selected_novel, ch)
                        sync_role_to_voice(selected_novel)
                        generate_tts_audio(selected_novel, ch)
                    except Exception as e:
                        st.warning(f"⚠️ {ch} 生成失败: {e}")
                status_text.text("✅ 批量生成完成！")
                st.rerun()

            # 批量下载按钮
            existing_audio_files = []
            for ch in batch_chapters:
                audio_path = NOVELS_DIR / selected_novel / "chapters" / ch / "full_drama.wav"
                if audio_path.exists():
                    existing_audio_files.append((ch, audio_path))

            if existing_audio_files:
                if st.button("📥 批量下载已生成音频 (ZIP)"):
                    import zipfile
                    from io import BytesIO

                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        for ch, path in existing_audio_files:
                            arcname = f"{selected_novel}_{ch}.wav"
                            zf.write(path, arcname)
                    
                    st.download_button(
                        label="⬇️ 下载 ZIP 包",
                        data=zip_buffer.getvalue(),
                        file_name=f"{selected_novel}_ch_{start_ch}_to_{end_ch}.zip",
                        mime="application/zip"
                    )
            else:
                st.info("所选章节中暂无已生成的音频，无法批量下载。")

# --- Tab 3: 自定义音色 ---
with tab3:
    if not selected_novel:
        st.info("请在左侧边栏选择小说")
    else:
        st.subheader(f"为小说 [{selected_novel}] 设置角色音色")
        role_name = st.text_input("角色名称（如：韩立、银月）", placeholder="请输入角色名")
        uploaded_wav = st.file_uploader("上传该角色的参考音色 (.wav)", type=["wav"])

        if st.button("💾 保存音色") and role_name and uploaded_wav:
            # 保存音色文件
            voice_filename = f"{selected_novel}_{role_name}.wav"
            voice_save_path = VOICE_DIR / voice_filename
            with open(voice_save_path, "wb") as f:
                f.write(uploaded_wav.getvalue())

            # 更新角色映射
            role_to_voice_path = NOVELS_DIR / selected_novel / "role_to_voice.json"
            if role_to_voice_path.exists():
                with open(role_to_voice_path, encoding="utf-8") as f:
                    role_map = json.load(f)
            else:
                role_map = {}

            role_map[role_name] = voice_filename

            with open(role_to_voice_path, "w", encoding="utf-8") as f:
                json.dump(role_map, f, ensure_ascii=False, indent=2)

            st.success(f"✅ 角色 [{role_name}] 音色已绑定到 `{voice_filename}`")
# packaging_ai_app.py
import streamlit as st
import time
import requests
from io import BytesIO
import sqlite3
import json

# ----------------------------
# API Configuration
# ----------------------------
API_BASE_URL = "http://122.51.53.133:9060"
PROMPT_API_URL = f"{API_BASE_URL}/generate_prompt"
IMAGE_API_URL = f"{API_BASE_URL}/generate_image"

# ----------------------------
# API Call Functions
# ----------------------------
def call_generate_prompt_api(user_prompt):
    """Calls the backend to generate a detailed design plan."""
    try:
        response = requests.post(PROMPT_API_URL, json={"prompt": user_prompt}, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"无法连接到设计方案生成服务: {e}")
        return None

def call_generate_image_api(detailed_prompt):
    """Calls the backend to generate images from a detailed plan."""
    try:
        response = requests.post(IMAGE_API_URL, json={"prompt": detailed_prompt}, timeout=180)
        response.raise_for_status()
        data = response.json()
        # Extract URLs from the response dictionary
        return [data.get(f"image_url{i+1}") for i in range(4) if data.get(f"image_url{i+1}")]
    except requests.exceptions.RequestException as e:
        st.error(f"无法连接到图片生成服务: {e}")
        return None

# ----------------------------
# Database Setup
# ----------------------------
DB_FILE = "projects.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects
        (id INTEGER PRIMARY KEY, name TEXT NOT NULL, state_json TEXT NOT NULL)
    ''')
    conn.commit()
    conn.close()

def save_project(name, state):
    state_json = json.dumps(state)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO projects (name, state_json) VALUES (?, ?)", (name, state_json))
    conn.commit()
    conn.close()

def load_projects():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM projects ORDER BY id DESC")
    projects = c.fetchall()
    conn.close()
    return projects

def load_project_state(project_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT state_json FROM projects WHERE id = ?", (project_id,))
    result = c.fetchone()
    conn.close()
    return json.loads(result[0]) if result else None

def delete_project(project_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

init_db()

# ----------------------------
# Page Configuration & Helper Functions
# ----------------------------
st.set_page_config(page_title="包装设计AI助手", page_icon="🎨", layout="wide")

@st.cache_data(show_spinner=False)
def get_image_bytes(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BytesIO(response.content)
    except requests.exceptions.RequestException:
        return None

# ----------------------------
# Sidebar
# ----------------------------
with st.sidebar:
    st.title("🎨 包装设计AI助手")
    st.markdown("---")
    st.header("1. 基础参数")
    package_type = st.selectbox("包装样式:", ("纸盒 (Box)", "瓶子 (Bottle)", "袋子 (Pouch)"), key="package_type")
    package_style = st.selectbox("设计风格:", ("现代简约 (Minimalist)", "复古经典 (Vintage)", "潮流趣味 (Playful)", "高端奢华 (Luxury)", "自然环保 (Natural)"), key="package_style")
    
    st.markdown("---")
    st.header("2. 品牌身份 (可选)")
    brand_color = st.color_picker("品牌主色", "#6E42D0")
    uploaded_logo = st.file_uploader("上传Logo", type=["png", "jpg", "jpeg"])
    if uploaded_logo: st.image(uploaded_logo, caption="当前Logo", width=100)

    st.markdown("---")
    st.header("3. 高级设计控件 (可选)")
    key_elements = st.text_area("核心元素", placeholder="例如: 100% Organic, New Formula")
    excluded_elements = st.text_area("排除元素", placeholder="例如: 不要卡通形象, 不要红色")

    st.markdown("---")
    st.header("4. 项目管理")
    project_name = st.text_input("为当前项目命名", placeholder="例如：蜂蜜包装第一版")
    if st.button("保存当前项目", use_container_width=True):
        if project_name:
            state_to_save = {k: v for k, v in st.session_state.items() if k != 'uploaded_logo'}
            save_project(project_name, state_to_save)
            st.success(f"项目 '{project_name}' 已保存!")
            time.sleep(1); st.rerun()
        else:
            st.warning("请输入项目名称后再保存。")

    st.markdown("##### 已有项目")
    for proj_id, proj_name in load_projects():
        col1, col2, col3 = st.columns([3, 2, 2])
        col1.markdown(f"**{proj_name}**")
        if col2.button("加载", key=f"load_{proj_id}", use_container_width=True):
            st.session_state.clear(); st.session_state.update(load_project_state(proj_id))
            st.success(f"项目 '{proj_name}' 已加载!"); time.sleep(1); st.rerun()
        if col3.button("删除", key=f"delete_{proj_id}", use_container_width=True):
            delete_project(proj_id); st.rerun()
    
    st.markdown("---")
    if st.button("重新开始对话", use_container_width=True):
        st.session_state.clear(); st.rerun()

# ----------------------------
# Initialize Session State
# ----------------------------
if "messages" not in st.session_state: st.session_state.messages = []
if "selected_for_iteration" not in st.session_state: st.session_state.selected_for_iteration = None
if "original_prompt" not in st.session_state: st.session_state.original_prompt = ""

# ----------------------------
# Main Chat Interface
# ----------------------------
st.header("与AI助手沟通需求")

for i, message in enumerate(st.session_state.get("messages", [])):
    with st.chat_message(message["role"]):
        if isinstance(message["content"], str): st.markdown(message["content"])
        elif isinstance(message["content"], list):
            cols = st.columns(len(message["content"]))
            for img_index, col in enumerate(cols):
                with col:
                    image_url = message["content"][img_index]
                    st.image(image_url, use_column_width=True)
                    if i == len(st.session_state.messages) - 1:
                        btn_col1, btn_col2 = st.columns(2)
                        if btn_col1.button(f"优化方案 {img_index+1}", key=f"iterate_{i}_{img_index}", use_container_width=True):
                            st.session_state.selected_for_iteration = {"index": img_index, "url": image_url}; st.rerun()
                        image_bytes = get_image_bytes(image_url)
                        if image_bytes:
                            btn_col2.download_button(label="下载图片", data=image_bytes, file_name=f"design_{img_index+1}.png", mime="image/png", key=f"download_{i}_{img_index}", use_container_width=True)
                        else: btn_col2.caption("下载失败")

if st.session_state.selected_for_iteration:
    st.info(f"您已选择 **方案 {st.session_state.selected_for_iteration['index'] + 1}** 进行优化。请在下方输入您的修改意见。")
    st.image(st.session_state.selected_for_iteration['url'], width=200)

if prompt := st.chat_input("请描述您的设计需求或修改意见..."):
    is_iteration = st.session_state.selected_for_iteration is not None
    if is_iteration: st.session_state.messages.append({"role": "user", "content": f"（针对方案 {st.session_state.selected_for_iteration['index']+1}）{prompt}"})
    else: st.session_state.messages.append({"role": "user", "content": prompt})

    # --- Step 1: Call Prompt Generation API ---
    with st.chat_message("assistant"):
        with st.spinner("AI助手正在构思设计方案..."):
            # Construct a detailed user prompt from all controls
            full_user_prompt = f"为 {package_type} 设计一个 {package_style} 风格的包装。设计需求: {prompt}。"
            if key_elements: full_user_prompt += f" 必须包含这些元素: {key_elements}。"
            if excluded_elements: full_user_prompt += f" 不能包含这些元素: {excluded_elements}。"
            if brand_color: full_user_prompt += f" 品牌主色是 {brand_color}。"
            # In a real scenario, you would handle the logo data.
            if uploaded_logo: full_user_prompt += " (注意: 用户上传了Logo，请在设计中体现)。"
            if is_iteration: full_user_prompt = f"基于之前的设计进行修改。修改意见: {prompt}。原始需求: {st.session_state.original_prompt}"

            if not is_iteration: st.session_state.original_prompt = full_user_prompt
            
            prompt_api_response = call_generate_prompt_api(full_user_prompt)

        if prompt_api_response and 'plan_presentation' in prompt_api_response:
            detailed_plan = prompt_api_response['plan_presentation']
            design_rationale = prompt_api_response.get('rationale', '已为您生成详细的设计方案。')
            st.markdown(design_rationale)
            st.session_state.messages.append({"role": "assistant", "content": design_rationale})
        else:
            st.error("无法获取设计方案，请稍后重试。")
            detailed_plan = None # Stop execution if this step fails

    # --- Step 2: Call Image Generation API ---
    if detailed_plan:
        with st.chat_message("assistant"):
            with st.spinner("正在根据方案生成图片..."):
                image_urls = call_generate_image_api(detailed_plan)
            
            if image_urls:
                st.session_state.messages.append({"role": "assistant", "content": image_urls})
            else:
                st.error("图片生成失败，请检查后端服务或稍后重试。")
                st.session_state.messages.append({"role": "assistant", "content": "图片生成失败。"})

            st.session_state.selected_for_iteration = None
            st.rerun()

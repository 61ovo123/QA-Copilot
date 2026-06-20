import streamlit as st
import json
import pandas as pd
from io import BytesIO
from openai import OpenAI

st.set_page_config(
    page_title="QA Copilot",
    page_icon="▸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================
# Session State 初始化
# ==========================

if "cases" not in st.session_state:
    st.session_state.cases = None

if "pytest_code" not in st.session_state:
    st.session_state.pytest_code = None

if "collection" not in st.session_state:
    st.session_state.collection = None

if "history" not in st.session_state:
    st.session_state.history = []

# ==========================
# 设计系统：终端 / 代码编辑器风格
# ==========================
# 配色逻辑：黑底等宽字体还原测试工程师真实的终端/CI环境；
# 三个生成工具分别使用它们各自生态里的真实品牌色，
# 不是随手挑的渐变，是有依据的色彩系统。

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
    --bg: #eef3fb;
    --bg-panel: #ffffff;
    --bg-panel-alt: #f3f7fd;
    --border: #d3dfef;
    --border-bright: #a9c0e0;
    --text: #0d1b34;
    --text-dim: #3c5274;
    --text-faint: #6e84a8;
    --accent-testcases: #60a5fa;
    --accent-pytest: #2563eb;
    --accent-postman: #1e3a8a;
    --accent-cursor: #2563eb;
    --accent-fail: #dc2626;
}

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

.stApp {
    background: var(--bg);
    color: var(--text);
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* ---------- 窗口标题栏 ---------- */

.term-chrome {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px 8px 0 0;
    padding: 10px 16px;
    margin-bottom: 0;
}

.term-dot {
    width: 11px;
    height: 11px;
    border-radius: 50%;
    display: inline-block;
}

.term-dot.red { background: #f87171; }
.term-dot.yellow { background: #f4c430; }
.term-dot.green { background: #4ade80; }

.term-chrome-title {
    margin-left: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: var(--text-faint);
    letter-spacing: 0.02em;
}

.term-body {
    background: var(--bg-panel-alt);
    border: 1px solid var(--border);
    border-top: none;
    border-radius: 0 0 8px 8px;
    padding: 28px 32px 8px 32px;
    margin-bottom: 28px;
}

/* ---------- 标题：命令行提示符 ---------- */

.prompt-line {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.1rem;
    font-weight: 600;
    color: var(--text);
    margin: 0;
}

.prompt-line .sigil {
    color: var(--accent-cursor);
}

.cursor-blink {
    display: inline-block;
    width: 11px;
    height: 1.5rem;
    background: var(--accent-cursor);
    margin-left: 6px;
    vertical-align: -3px;
    animation: blink 1.1s steps(1) infinite;
}

@keyframes blink {
    0%, 49% { opacity: 1; }
    50%, 100% { opacity: 0; }
}

.prompt-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: var(--text-dim);
    margin-top: 6px;
    margin-bottom: 0;
}

/* ---------- 工具卡片 ---------- */

.tool-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-left: 3px solid var(--card-accent, var(--text-faint));
    border-radius: 4px;
    padding: 14px 16px;
    height: 100%;
}

.tool-card .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--card-accent, var(--text-faint));
    display: inline-block;
    margin-right: 8px;
}

.tool-card .label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--text);
}

.tool-card .desc {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: var(--text-dim);
    margin-top: 6px;
    margin-bottom: 0;
}

/* ---------- 文件 / 面板标签 ---------- */

.file-tab {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 7px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: var(--text-dim);
}

.panel-box {
    background: var(--bg-panel-alt);
    border: 1px solid var(--border);
    border-radius: 0 6px 6px 6px;
    padding: 18px 18px 6px 18px;
    margin-bottom: 18px;
}

/* ---------- Streamlit 组件重皮 ---------- */

section[data-testid="stSidebar"] {
    background: var(--bg-panel);
    border-right: 1px solid var(--border);
}

section[data-testid="stSidebar"] * {
    font-family: 'JetBrains Mono', monospace;
}

.stTextArea textarea {
    background: var(--bg-panel) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
}

.stTextArea textarea:focus {
    border-color: var(--accent-cursor) !important;
    box-shadow: 0 0 0 1px var(--accent-cursor) !important;
}

.stButton button, .stDownloadButton button {
    background: var(--bg-panel) !important;
    color: var(--text) !important;
    border: 1px solid var(--border-bright) !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em;
    transition: border-color 0.15s ease, color 0.15s ease;
}

.stButton button:hover, .stDownloadButton button:hover {
    border-color: var(--accent-cursor) !important;
    color: var(--accent-cursor) !important;
}

.stButton button p, .stDownloadButton button p {
    font-family: 'JetBrains Mono', monospace !important;
}

[data-testid="stMetric"] {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 10px 12px;
}

[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent-cursor);
}

[data-testid="stMetricLabel"] {
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-dim);
}

.stRadio label {
    font-family: 'JetBrains Mono', monospace !important;
}

div[data-testid="stExpander"] {
    background: var(--bg-panel);
    border: 1px solid var(--border) !important;
    border-radius: 4px;
}

.streamlit-expanderHeader, summary {
    font-family: 'JetBrains Mono', monospace !important;
    color: var(--text) !important;
}

.stAlert {
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
}

.stCodeBlock, pre {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
}

div[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 4px;
}

hr {
    border-color: var(--border) !important;
}

.section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: var(--text-faint);
    text-transform: uppercase;
    margin-bottom: 6px;
}

/* ---------- Tabs ---------- */

[data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid var(--border) !important;
    gap: 4px;
}

button[data-baseweb="tab"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.74rem !important;
    letter-spacing: 0.06em;
    color: var(--text-faint) !important;
    background: transparent !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--accent-cursor) !important;
}

[data-baseweb="tab-highlight"] {
    background-color: var(--accent-cursor) !important;
}

.stTabs [data-testid="stCaption"] {
    font-family: 'JetBrains Mono', monospace !important;
}

</style>
""", unsafe_allow_html=True)

# ==========================
# DeepSeek 客户端
# ==========================

try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    st.error(
        "未找到 DEEPSEEK_API_KEY。\n\n"
        "请在项目根目录创建 `.streamlit/secrets.toml` 文件，写入：\n\n"
        "```\nDEEPSEEK_API_KEY = \"你的key\"\n```"
    )
    st.stop()

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# ==========================
# 工具函数
# ==========================

def clean_json(text):

    text = text.strip()

    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    return text.strip()


def export_excel(cases):

    output = BytesIO()

    df = pd.DataFrame(cases)

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False
        )

    output.seek(0)

    return output


def generate_test_cases(req):

    prompt = f"""
你是一名高级软件测试工程师。

根据以下需求生成测试用例。

需求：

{req}

必须严格返回JSON数组。

禁止返回：
- markdown
- ```json
- 解释文字
- 分析过程

只能返回如下格式：

[
  {{
    "测试编号":"TC001",
    "测试场景":"正常登录",
    "预期结果":"登录成功"
  }},
  {{
    "测试编号":"TC002",
    "测试场景":"密码错误",
    "预期结果":"提示密码错误"
  }}
]
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ]
    )

    return response.choices[0].message.content


def generate_pytest(req):

    prompt = f"""
根据以下需求生成pytest自动化测试脚本。

需求：

{req}

只返回代码。
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ]
    )

    return response.choices[0].message.content


def generate_postman(req):

    prompt = f"""
根据以下需求生成Postman Collection v2.1。

需求：

{req}

只返回JSON。
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ]
    )

    return response.choices[0].message.content


# ==========================
# 侧边栏
# ==========================

with st.sidebar:

    st.markdown('<div class="section-label">QA COPILOT</div>', unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "History"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.metric(
        "history entries",
        len(st.session_state.history)
    )

    if st.button("clear history"):

        st.session_state.history = []
        st.session_state.cases = None
        st.session_state.pytest_code = None
        st.session_state.collection = None

        st.rerun()

# ==========================
# 主区域：Dashboard 页面
# ==========================

if page == "Dashboard":

    # ---- 窗口标题栏 + 命令行式标题 ----

    st.markdown("""
    <div class="term-chrome">
        <span class="term-dot red"></span>
        <span class="term-dot yellow"></span>
        <span class="term-dot green"></span>
        <span class="term-chrome-title">qa-copilot — zsh</span>
    </div>
    <div class="term-body">
        <p class="prompt-line"><span class="sigil">$</span> qa-copilot run --watch<span class="cursor-blink"></span></p>
        <p class="prompt-sub"># AI-native test artifact generator — test cases / pytest / postman</p>
    </div>
    """, unsafe_allow_html=True)

    # ---- 三个工具卡片，按各自生态的真实品牌色区分 ----

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("""
        <div class="tool-card" style="--card-accent:#60a5fa;">
            <span class="dot"></span><span class="label">TEST CASES</span>
            <p class="desc">结构化QA测试场景 → JSON</p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="tool-card" style="--card-accent:#2563eb;">
            <span class="dot"></span><span class="label">PYTEST</span>
            <p class="desc">自动化测试脚本 → .py</p>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <div class="tool-card" style="--card-accent:#1e3a8a;">
            <span class="dot"></span><span class="label">POSTMAN</span>
            <p class="desc">接口测试集合 → .json</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    left, right = st.columns([1, 2])

    with left:

        st.markdown('<div class="file-tab">📄 requirement.md</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-box">', unsafe_allow_html=True)

        requirement = st.text_area(
            "Requirement Description",
            height=220,
            label_visibility="collapsed",
            placeholder="# 在这里描述需求\n例如：\nPOST /login\n参数：username, password\n返回：token"
        )

        st.markdown('</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        # ==========================
        # 测试用例
        # ==========================

        with col1:

            if st.button("▸ Test Cases"):

                if not requirement.strip():

                    st.warning("请输入需求")

                else:

                    try:

                        with st.spinner("Generating Test Cases..."):

                            result = generate_test_cases(
                                requirement
                            )

                            with right:
                                st.markdown('<div class="section-label">AI原始返回内容</div>', unsafe_allow_html=True)
                                st.code(result)

                            result = clean_json(result)

                            try:

                                cases = json.loads(result)

                            except Exception:

                                with right:
                                    st.error("✗ AI返回的不是合法JSON")
                                    st.code(result)

                                st.stop()

                            with right:
                                st.success(f"✓ JSON解析成功 — 共 {len(cases)} 条用例")

                            st.session_state.cases = cases

                            st.session_state.history.append(
                                {
                                    "type":"Test Cases",
                                    "requirement":requirement,
                                    "data":cases
                                }
                            )

                    except Exception as e:

                        st.error(e)

        # ==========================
        # Pytest
        # ==========================

        with col2:

            if st.button("▸ Pytest"):

                if not requirement.strip():

                    st.warning("请输入需求")

                else:

                    try:

                        with st.spinner("Generating Pytest..."):

                            script = generate_pytest(
                                requirement
                            )

                            st.session_state.pytest_code = script

                            st.session_state.history.append(
                                {
                                    "type":"Pytest",
                                    "requirement":requirement,
                                    "data":script
                                }
                            )

                    except Exception as e:

                        st.error(e)

        # ==========================
        # Postman
        # ==========================

        with col3:

            if st.button("▸ Postman"):

                if not requirement.strip():

                    st.warning("请输入需求")

                else:

                    try:

                        with st.spinner("Generating Postman..."):

                            collection = generate_postman(
                                requirement
                            )

                            collection = clean_json(
                                collection
                            )

                            st.session_state.collection = collection

                            st.session_state.history.append(
                                {
                                    "type":"Postman",
                                    "requirement":requirement,
                                    "data":collection
                                }
                            )

                    except Exception as e:

                        st.error(e)

    # ==========================
    # 结果展示区
    # ==========================

    with right:

        st.markdown('<div class="file-tab">▸ output.log</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-box">', unsafe_allow_html=True)

        has_any_result = (
            st.session_state.cases
            or st.session_state.pytest_code
            or st.session_state.collection
        )

        if not has_any_result:
            st.markdown(
                '<p style="font-family:\'JetBrains Mono\',monospace;color:var(--text-faint);font-size:0.82rem;">'
                '# 等待生成结果 — 点击左侧按钮开始'
                '</p>',
                unsafe_allow_html=True
            )

        else:

            tab_cases, tab_pytest, tab_postman = st.tabs([
                "● TEST CASES" if st.session_state.cases else "TEST CASES",
                "● PYTEST" if st.session_state.pytest_code else "PYTEST",
                "● POSTMAN" if st.session_state.collection else "POSTMAN",
            ])

            # ---- Test Cases ----
            with tab_cases:

                if st.session_state.cases:

                    head_l, head_r = st.columns([4, 1])

                    with head_l:
                        st.markdown('<div class="section-label">TEST CASES</div>', unsafe_allow_html=True)

                    with head_r:
                        excel_file = export_excel(
                            st.session_state.cases
                        )
                        st.download_button(
                            "↓ .xlsx",
                            excel_file,
                            "test_cases.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                    df = pd.DataFrame(
                        st.session_state.cases
                    )

                    st.dataframe(
                        df,
                        use_container_width=True
                    )

                else:
                    st.caption("尚未生成 — 点击左侧 ▸ Test Cases")

            # ---- Pytest ----
            with tab_pytest:

                if st.session_state.pytest_code:

                    head_l, head_r = st.columns([4, 1])

                    with head_l:
                        st.markdown('<div class="section-label">PYTEST SCRIPT</div>', unsafe_allow_html=True)

                    with head_r:
                        st.download_button(
                            "↓ .py",
                            st.session_state.pytest_code,
                            "test_case.py",
                            use_container_width=True
                        )

                    st.code(
                        st.session_state.pytest_code,
                        language="python"
                    )

                else:
                    st.caption("尚未生成 — 点击左侧 ▸ Pytest")

            # ---- Postman Collection ----
            with tab_postman:

                if st.session_state.collection:

                    head_l, head_r = st.columns([4, 1])

                    with head_l:
                        st.markdown('<div class="section-label">POSTMAN COLLECTION</div>', unsafe_allow_html=True)

                    with head_r:
                        st.download_button(
                            "↓ .json",
                            st.session_state.collection,
                            "collection.json",
                            use_container_width=True
                        )

                    st.code(
                        st.session_state.collection,
                        language="json"
                    )

                else:
                    st.caption("尚未生成 — 点击左侧 ▸ Postman")

        st.markdown('</div>', unsafe_allow_html=True)

# ==========================
# 主区域：History 页面
# ==========================

elif page == "History":

    st.markdown("""
    <div class="term-chrome">
        <span class="term-dot red"></span>
        <span class="term-dot yellow"></span>
        <span class="term-dot green"></span>
        <span class="term-chrome-title">qa-copilot — history</span>
    </div>
    <div class="term-body">
        <p class="prompt-line"><span class="sigil">$</span> cat history.log<span class="cursor-blink"></span></p>
    </div>
    """, unsafe_allow_html=True)

    if len(st.session_state.history) == 0:

        st.markdown(
            '<p style="font-family:\'JetBrains Mono\',monospace;color:var(--text-faint);">'
            '# 暂无记录 — 生成内容后会显示在这里'
            '</p>',
            unsafe_allow_html=True
        )

    else:

        for i, item in enumerate(
            reversed(st.session_state.history)
        ):

            with st.expander(
                f"▸ {item['type']}  #{i+1}"
            ):

                st.write(item["requirement"])

                if item["type"] == "Test Cases":

                    st.dataframe(
                        pd.DataFrame(item["data"]),
                        use_container_width=True
                    )

                elif item["type"] == "Pytest":

                    st.code(
                        item["data"],
                        language="python"
                    )

                else:

                    st.code(
                        item["data"],
                        language="json"
                    )

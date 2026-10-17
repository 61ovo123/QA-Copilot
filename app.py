import streamlit as st
import streamlit.components.v1 as components
import json
import time
import pandas as pd
from io import BytesIO
from openai import OpenAI, RateLimitError, InternalServerError, APIConnectionError

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
# 设计系统：Notion / 飞书式文档风格
# ==========================
# 配色逻辑：白底 + 暖灰阶（Notion 经典 #37352f / #f7f7f5），
# 文档感排版、清爽留白；蓝色 #2383e2 作为唯一强调色，
# 三个生成工具用浅色品牌底色的图标区分，整体克制、易读。

st.markdown("""
<style>

/* 字体源：Google Fonts 国内镜像（loli.net）
   直连 fonts.googleapis.com 在国内会被墙，导致 Material Icons 字体
   加载失败、图标名（arrow_drop_down 等）以文字形式漏出 */
@import url('https://fonts.loli.net/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');
@import url('https://fonts.loli.net/icon?family=Material+Icons');
@import url('https://fonts.loli.net/icon?family=Material+Symbols+Outlined');

:root {
    /* Notion 暖灰阶文档配色 */
    --bg: #ffffff;
    --bg-sidebar: #f7f7f5;
    --bg-hover: #f1f1ef;
    --bg-panel: #ffffff;
    --bg-panel-alt: #fbfbfa;
    --border: #e9e9e7;
    --border-strong: #d9d9d6;
    --text: #37352f;
    --text-dim: #787774;
    --text-faint: #9b9a97;
    --accent: #2383e2;
    --accent-soft: #e7f3fb;
    --accent-fail: #d44c47;
    --shadow-card: 0 1px 3px rgba(15, 15, 15, 0.05), 0 4px 12px rgba(15, 15, 15, 0.04);
    /* UI 字体栈：跨平台系统字体（Windows 用 Segoe UI + 微软雅黑） */
    --font-ui: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
    /* 等宽字体栈：仅代码区域使用 */
    --font-mono: "JetBrains Mono", "SF Mono", "Cascadia Code", Consolas, Menlo, monospace;
}

html, body, [class*="css"] {
    font-family: var(--font-ui);
}

/* 恢复 Material Icons / Material Symbols 字体 —— 全局字体覆盖会导致
   Streamlit 内部图标（折叠按钮、expander 箭头等）变成文字。
   字体文件本身由上方 loli.net 镜像 @import 提供。 */
.material-icons, [class*="material-icons"], [class*="Material-Icons"],
[data-testid="stIconMaterial"] {
    font-family: "Material Icons" !important;
}
.material-symbols-outlined, [class*="material-symbols"] {
    font-family: "Material Symbols Outlined" !important;
}

/* Expander 头部排版：标题文字独占一行，箭头图标放在标题下一行
   DOM: summary(flex) > span(flex row) > [icon-span, title-div]
   改为纵向反向排列 = 标题在上、箭头在下 */
[data-testid="stExpander"] summary > span {
    flex-direction: column-reverse !important;
    align-items: flex-start !important;
    gap: 2px !important;
}

.stApp {
    background: var(--bg);
    color: var(--text);
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* ---------- 文档式页头 ---------- */

.hero {
    padding: 18px 4px 16px 4px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
}

.hero-row {
    display: flex;
    align-items: center;
    gap: 12px;
}

.hero-badge {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    background: var(--accent);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.hero-badge svg {
    width: 20px;
    height: 20px;
    display: block;
}

.hero-title {
    font-family: var(--font-ui);
    font-size: 1.9rem;
    font-weight: 700;
    color: var(--text);
    margin: 0;
    letter-spacing: -0.01em;
    line-height: 1.2;
}

.hero-sub {
    font-family: var(--font-ui);
    font-size: 0.9rem;
    color: var(--text-dim);
    margin-top: 8px;
    margin-bottom: 0;
}

/* ---------- 工具卡片 ---------- */

.tool-card {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    height: 100%;
    box-shadow: 0 1px 2px rgba(15, 15, 15, 0.04);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.tool-card:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-card);
}

.tool-icon {
    width: 30px;
    height: 30px;
    border-radius: 6px;
    background: var(--card-accent-bg, var(--bg-hover));
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.tool-icon svg {
    width: 16px;
    height: 16px;
    display: block;
}

.tool-card .label {
    font-family: var(--font-ui);
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1.3;
    margin-top: 1px;
}

.tool-card .desc {
    font-family: var(--font-ui);
    font-size: 0.78rem;
    color: var(--text-dim);
    margin-top: 3px;
    margin-bottom: 0;
}

/* ---------- 文件 / 面板标签 ---------- */

.file-tab {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-sidebar);
    border: 1px solid var(--border);
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 7px 14px;
    font-family: var(--font-ui);
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-dim);
}

.file-tab svg {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
}

.panel-box {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 0 8px 8px 8px;
    padding: 18px 18px 6px 18px;
    margin-bottom: 18px;
}

/* ---------- Streamlit 组件重皮 ---------- */

section[data-testid="stSidebar"] {
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
}

section[data-testid="stSidebar"] * {
    font-family: var(--font-ui);
}

.stTextArea textarea {
    background: var(--bg-panel) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: var(--font-ui) !important;
    font-size: 0.92rem !important;
    line-height: 1.6;
    transition: border-color 0.12s ease, box-shadow 0.12s ease;
}

.stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(35, 131, 226, 0.18) !important;
}

.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {
    background: var(--bg-panel) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: var(--font-ui) !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em;
    box-shadow: 0 1px 2px rgba(15, 15, 15, 0.05);
    transition: background 0.12s ease, border-color 0.12s ease;
}

.stButton button:hover, .stDownloadButton button:hover, [data-testid="stFormSubmitButton"] button:hover {
    background: var(--bg-hover) !important;
    border-color: var(--border-strong) !important;
    color: var(--text) !important;
}

.stButton button p, .stDownloadButton button p, [data-testid="stFormSubmitButton"] button p {
    font-family: var(--font-ui) !important;
}

/* ---------- 行内按钮等高对齐 ----------
   复制按钮(iframe)、下载按钮、普通按钮混排在一行时高度/垂直位置不一致,
   统一为 40px 高 */

.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {
    height: 40px !important;
}

/* 侧边栏 API Key 行:输入框统一 40px,与眼睛按钮(见下方 eye 按钮规则)等高 */
div.st-key-deepseek_api_key input {
    height: 40px !important;
}

[data-testid="stMetric"] {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
}

[data-testid="stMetricValue"] {
    font-family: var(--font-ui);
    color: var(--accent);
}

[data-testid="stMetricLabel"] {
    font-family: var(--font-ui);
    color: var(--text-dim);
}

.stRadio label {
    font-family: var(--font-ui) !important;
}

div[data-testid="stExpander"] {
    background: var(--bg-panel);
    border: 1px solid var(--border) !important;
    border-radius: 8px;
}

.streamlit-expanderHeader, summary {
    font-family: var(--font-ui) !important;
    color: var(--text) !important;
}

.stAlert {
    border-radius: 6px;
    font-family: var(--font-ui);
    font-size: 0.88rem;
}

[data-testid="stCodeBlock"], pre {
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
}

div[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 6px;
}

hr {
    border-color: var(--border) !important;
}

.section-label {
    font-family: var(--font-ui);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.1em;
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
    font-family: var(--font-ui) !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.02em;
    color: var(--text-dim) !important;
    background: transparent !important;
}

button[data-baseweb="tab"]:hover {
    color: var(--text) !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--accent) !important;
}

[data-baseweb="tab-highlight"] {
    background-color: var(--accent) !important;
}

.stTabs [data-testid="stCaption"] {
    font-family: var(--font-ui) !important;
}

/* ---------- API Key 输入框 ---------- */

/* 隐藏 Streamlit 自带的密码可见性切换按钮（它会渲染成 "visibility" 文字并与点号重叠） */
.stTextInput [data-baseweb="input"] button,
.stTextInput [data-testid="stTextInputVisibilityToggle"],
.stTextInput [aria-label*="password" i] {
    display: none !important;
}

/* 输入框不再为按钮预留右侧空间，避免点号被挤压 */
.stTextInput input[type="password"] {
    padding-right: 12px !important;
}

/* ---------- 眼睛切换按钮（Lucide eye / eye-off SVG） ---------- */
/* Streamlit 给每个 widget 容器加 st-key-{widget_key} 类，
   用 st-key-toggle_api_key_visibility 直接锁定眼睛按钮，无需脆弱的兄弟选择器。
   背景 SVG URL 由 Python 根据当前 show_api_key 状态动态注入。 */

div.st-key-toggle_api_key_visibility {
    margin-top: 0 !important;
    padding-top: 0 !important;
}

div.st-key-toggle_api_key_visibility button,
div.st-key-toggle_api_key_visibility button p {
    color: transparent !important;
    font-size: 0 !important;
}

div.st-key-toggle_api_key_visibility button {
    background-repeat: no-repeat !important;
    background-position: center !important;
    background-size: 18px 18px !important;
    padding: 0 !important;
    height: 40px !important;
    min-height: 40px !important;
    margin: 0 !important;
    cursor: pointer;
}

div.st-key-toggle_api_key_visibility button:hover {
    border-color: var(--accent) !important;
}

/* ---------- 侧边栏导航：Lucide 图标代替 emoji ---------- */

/* 导航项图标（Lucide SVG）—— 图标放在文字左边、选择圆点的右边
   DOM: stRadioGroup > div(wrapper) > label > div(content) > div(radio-dot) + div(stMarkdownContainer) > p(text)
   把 ::before 加在 <p> 上，让图标跟文字同行，且在选择圆点的右边。
   不再隐藏 radio 圆点（用户需要看到选中状态）。 */

[data-testid="stRadioGroup"] > div:nth-child(1) [data-testid="stMarkdownContainer"] p::before {
    content: "" !important;
    display: inline-block !important;
    vertical-align: middle !important;
    width: 18px;
    height: 18px;
    margin-right: 8px;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23787774' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><rect width='7' height='9' x='3' y='3' rx='1'/><rect width='7' height='5' x='14' y='3' rx='1'/><rect width='7' height='9' x='14' y='12' rx='1'/><rect width='7' height='5' x='3' y='16' rx='1'/></svg>");
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
}

[data-testid="stRadioGroup"] > div:nth-child(2) [data-testid="stMarkdownContainer"] p::before {
    content: "" !important;
    display: inline-block !important;
    vertical-align: middle !important;
    width: 18px;
    height: 18px;
    margin-right: 8px;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23787774' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8'/><path d='M3 3v5h5'/><path d='M12 7v5l4 2'/></svg>");
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
}

</style>
""", unsafe_allow_html=True)

# ==========================
# DeepSeek 客户端
# ==========================
# DeepSeek API Key 现在通过侧边栏输入（仅当前会话保存，不写入文件）。
# 若已配置 .streamlit/secrets.toml，会作为默认值自动填入输入框。
# 客户端实例化移到侧边栏之后（见下方）。

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


def call_deepseek(prompt):
    """调用 DeepSeek;对限流(429)和服务繁忙(5xx,如 503)自动重试 2 次,间隔 3s/6s;
    认证失败(401)等非临时性错误立即抛出"""

    last_err = None

    for attempt in range(3):

        try:

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

        except (RateLimitError, InternalServerError, APIConnectionError) as e:

            last_err = e

            if attempt < 2:
                time.sleep(3 * (attempt + 1))

    raise last_err


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

    return call_deepseek(prompt)


def generate_pytest(req):

    prompt = f"""
根据以下需求生成pytest自动化测试脚本。

需求：

{req}

只返回代码。
"""

    return call_deepseek(prompt)


def generate_postman(req):

    prompt = f"""
根据以下需求生成Postman Collection v2.1。

需求：

{req}

只返回JSON。
"""

    return call_deepseek(prompt)


def strip_code_fences(text):
    """去掉 AI 返回代码中可能包裹的 ```python ... ``` 围栏"""
    t = (text or "").strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1:]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip() + "\n"


def build_pytest_package(pytest_code):
    """打包可直接运行的 pytest 测试项目(返回 zip bytes)
    包含: tests/test_api.py / requirements.txt / pytest.ini / README.md"""
    import zipfile
    buf = BytesIO()
    readme = (
        "# Pytest 测试包 — QA Copilot 生成\n\n"
        "## 运行方法\n\n"
        "```bash\n"
        "pip install -r requirements.txt\n"
        "pytest\n"
        "```\n\n"
        "## 文件说明\n\n"
        "- `tests/test_api.py` — AI 生成的自动化测试脚本\n"
        "- `pytest.ini` — pytest 配置(测试目录为 tests/)\n"
        "- `requirements.txt` — 运行依赖\n\n"
        "运行前请确认脚本中的被测服务地址(BASE_URL 等)正确。\n"
    )
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("tests/test_api.py", strip_code_fences(pytest_code))
        zf.writestr("requirements.txt", "pytest>=8.0\nrequests>=2.31\n")
        zf.writestr("pytest.ini", "[pytest]\ntestpaths = tests\naddopts = -v\n")
        zf.writestr("README.md", readme)
    return buf.getvalue()


def push_to_postman(collection_json, api_key, workspace_id=None):
    """通过 Postman API 把 Collection 推送到指定 Workspace,返回响应 dict
    失败时抛出带 Postman 响应体的异常,便于定位(401=Key无效等)"""
    import urllib.request
    import urllib.error
    url = "https://api.getpostman.com/collections"
    if workspace_id:
        url += f"?workspace={workspace_id}"
    try:
        payload = json.loads(collection_json)
    except Exception:
        raise ValueError("Collection 不是合法 JSON,无法推送")
    # 补全 Postman API 必需字段,避免 400 校验失败
    info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
    info.setdefault("schema", "https://schema.getpostman.com/json/collection/v2.1.0/collection.json")
    if not info.get("name"):
        info["name"] = "QA Copilot Collection"
    payload["info"] = info
    payload.setdefault("item", [])
    body = json.dumps({"collection": payload}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("X-Api-Key", (api_key or "").strip())
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "ignore")[:300]
        except Exception:
            pass
        hint = {401: "API Key 无效", 403: "Key 权限不足", 404: "Workspace ID 不存在"}.get(e.code, "")
        raise RuntimeError(f"HTTP {e.code} {hint} {detail}".strip())


def postman_get(path, api_key):
    """调用 Postman API GET 请求,返回 dict"""
    import urllib.request
    import urllib.error
    req = urllib.request.Request(f"https://api.getpostman.com/{path}")
    req.add_header("X-Api-Key", (api_key or "").strip())
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:200]}")


def copy_button_component(text, label="复制 JSON"):
    """渲染一个点击后复制 text 到剪贴板的按钮(iframe 内自带手势,兼容各浏览器)"""
    import html as _html
    escaped = _html.escape(text)
    components.html(
        f"""
        <html>
        <body style="margin:0;padding:0;">
            <button id="cpybtn" onclick="doCopy()" style="
                width:100%;height:40px;box-sizing:border-box;padding:0 10px;
                font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
                font-size:0.85rem;font-weight:500;border:1px solid #e9e9e7;
                border-radius:6px;background:#ffffff;color:#37352f;
                box-shadow:0 1px 2px rgba(15,15,15,0.05);
                cursor:pointer;">{label}</button>
            <textarea id="cpytxt" style="position:absolute;left:-9999px;top:0;">{escaped}</textarea>
            <script>
            function doCopy() {{
                var t = document.getElementById("cpytxt");
                t.select();
                try {{ document.execCommand("copy"); }} catch (e) {{}}
                var b = document.getElementById("cpybtn");
                b.textContent = "已复制";
                setTimeout(function() {{ b.textContent = "{label}"; }}, 1500);
            }}
            </script>
        </body>
        </html>
        """,
        height=40,
    )


# ==========================
# 侧边栏
# ==========================

with st.sidebar:

    st.markdown('<div class="section-label">QA COPILOT</div>', unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        ["Dashboard", "History"],
        label_visibility="collapsed"
    )

    st.divider()

    # DeepSeek API Key 输入（仅当前会话保存，不写入文件）
    # 若已配置 .streamlit/secrets.toml，作为默认值填入
    if "deepseek_api_key" not in st.session_state:
        try:
            st.session_state.deepseek_api_key = st.secrets["DEEPSEEK_API_KEY"]
        except Exception:
            st.session_state.deepseek_api_key = ""

    # 显示/隐藏 API Key 的开关（默认隐藏）
    if "show_api_key" not in st.session_state:
        st.session_state.show_api_key = False

    st.markdown('<div class="section-label">你的 API Key</div>', unsafe_allow_html=True)
    # 眼睛图标 SVG（Lucide eye / eye-off）按当前状态动态注入 CSS
    # 注意：必须放在 columns 外面 —— 若放在眼睛按钮同一列里，
    # st.markdown 的空容器会多占 ~16px，把按钮顶下去造成与输入框错位
    # eye-state-hidden: 当前隐藏（点击会显示，显示 eye 图标）
    # eye-state-shown: 当前显示（点击会隐藏，显示 eye-off 图标）
    _eye_svg = (
        "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23787774' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0'/><circle cx='12' cy='12' r='3'/></svg>"
        if not st.session_state.show_api_key
        else "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23787774' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49'/><path d='M14.084 14.158a3 3 0 0 1-4.242-4.242'/><path d='M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143'/><path d='m2 2 20 20'/></svg>"
    )
    st.markdown(
        f'<style>div.st-key-toggle_api_key_visibility button {{ background-image: url("{_eye_svg}") !important; }}</style>',
        unsafe_allow_html=True
    )
    _key_col, _eye_col = st.columns([5, 1])
    with _key_col:
        st.text_input(
            "你的 API Key",
            type="password" if not st.session_state.show_api_key else "default",
            placeholder="sk-...",
            key="deepseek_api_key",
            label_visibility="collapsed",
            help="仅保存在当前会话，不写入文件"
        )
    with _eye_col:
        if st.button(" ", key="toggle_api_key_visibility", use_container_width=True, help="显示/隐藏 API Key"):
            st.session_state.show_api_key = not st.session_state.show_api_key
            st.rerun()

    # Postman 一键导入配置（可选）— 仅保存在当前会话，不写入文件
    with st.expander("Postman 一键导入（可选）"):
        st.text_input(
            "Postman API Key",
            type="password",
            key="postman_api_key",
            help="postman.com 右上角头像 → Settings → API Keys 生成"
        )
        st.text_input(
            "Workspace ID",
            key="postman_workspace_id",
            help="Postman 打开目标 Workspace，URL 中 /workspaces/ 后面那串；留空则推送到默认 Workspace"
        )
        _pkey_now = st.session_state.get("postman_api_key", "")
        _vbtn, _wbtn = st.columns(2)
        with _vbtn:
            if st.button("验证 Key", use_container_width=True, disabled=not _pkey_now.strip()):
                try:
                    _me = postman_get("me", _pkey_now)
                    _u = _me.get("user") or {}
                    st.success(f"✓ Key 有效（{_u.get('username') or _u.get('email') or 'OK'}）")
                except Exception as _e:
                    st.error(f"✗ {_e}")
        with _wbtn:
            if st.button("列出 Workspace", use_container_width=True, disabled=not _pkey_now.strip()):
                try:
                    _ws = postman_get("workspaces", _pkey_now).get("workspaces") or []
                    if _ws:
                        st.caption("点 id 代码块右上角的复制按钮，只会复制纯 id:")
                        for _w in _ws[:10]:
                            _wn, _wi = st.columns([1, 2])
                            with _wn:
                                st.caption(f"**{_w.get('name')}**")
                            with _wi:
                                st.code(_w.get("id", ""), language=None)
                    else:
                        st.caption("该账号下没有可见 Workspace")
                except Exception as _e:
                    st.error(f"✗ {_e}")

    st.metric(
        "历史记录",
        len(st.session_state.history)
    )

    if st.button("清空历史"):

        st.session_state.history = []
        st.session_state.cases = None
        st.session_state.pytest_code = None
        st.session_state.collection = None
        st.session_state.raw_cases = None
        st.session_state.cases_parse_error = None

        st.rerun()

# ==========================
# DeepSeek 客户端初始化
# ==========================

if not st.session_state.get("deepseek_api_key"):
    st.info("请在左侧栏填写你的 API Key 后开始使用。")
    st.stop()

client = OpenAI(
    api_key=st.session_state.deepseek_api_key.strip(),
    base_url="https://api.deepseek.com"
)

# ==========================
# 主区域：Dashboard 页面
# ==========================

if page == "Dashboard":

    # ---- 窗口标题栏 + 命令行式标题 ----

    st.markdown("""
    <div class="hero">
        <div class="hero-row">
            <span class="hero-badge"><svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='#ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/></svg></span>
            <h1 class="hero-title">QA Copilot</h1>
        </div>
        <p class="hero-sub">AI 原生测试工件生成器 — 测试用例 · Pytest · Postman，一键生成、导出、推送</p>
    </div>
    """, unsafe_allow_html=True)

    # ---- 三个工具卡片，浅色品牌图标区分 ----

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("""
        <div class="tool-card">
            <span class="tool-icon" style="background:#e7f3fb;">
                <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='#2383e2' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/></svg>
            </span>
            <div>
                <div class="label">Test Cases</div>
                <p class="desc">结构化 QA 测试场景 → JSON</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="tool-card">
            <span class="tool-icon" style="background:#edf3ec;">
                <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='#448361' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            </span>
            <div>
                <div class="label">Pytest</div>
                <p class="desc">自动化测试脚本 → .py</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <div class="tool-card">
            <span class="tool-icon" style="background:#faebdd;">
                <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='#d9730d' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
            </span>
            <div>
                <div class="label">Postman</div>
                <p class="desc">接口测试集合 → .json</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    left, right = st.columns([1, 2])

    with left:

        st.markdown('<div class="file-tab"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#787774" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>requirement.md</div>', unsafe_allow_html=True)
        # 需求输入 + 三个生成按钮放进 st.form:
        # text_area 有未提交文本时,直接点普通按钮会被「失焦提交」的 rerun 吞掉点击,
        # 表现为主区域毫无反应;form_submit_button 会一次性提交整个表单,不存在该问题
        st.markdown('<div class="panel-box">', unsafe_allow_html=True)

        with st.form("generator_form", border=False):

            requirement = st.text_area(
                "Requirement Description",
                height=220,
                label_visibility="collapsed",
                placeholder="# 在这里描述需求\n例如：\nPOST /login\n参数：username, password\n返回：token"
            )

            fcol1, fcol2, fcol3 = st.columns(3)

            with fcol1:
                gen_cases = st.form_submit_button("Test Cases", use_container_width=True)

            with fcol2:
                gen_pytest = st.form_submit_button("Pytest", use_container_width=True)

            with fcol3:
                gen_postman = st.form_submit_button("Postman", use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # 与上方按钮列对齐的逻辑列:spinner/警告/错误正好显示在对应按钮正下方
        col1, col2, col3 = st.columns(3)

        # ==========================
        # 测试用例
        # ==========================

        with col1:

            if gen_cases:

                if not requirement.strip():

                    st.warning("请输入需求")

                else:

                    try:

                        with st.spinner("Generating Test Cases..."):

                            result = generate_test_cases(
                                requirement
                            )

                            # 原始返回内容存入 session_state，在 TEST CASES tab 内展示
                            # （避免直接渲染到右栏顶部，把 tabs 导航挤到页面下方）
                            st.session_state.raw_cases = result

                            result = clean_json(result)

                            try:

                                cases = json.loads(result)

                            except Exception:

                                st.session_state.cases_parse_error = result
                                st.stop()

                            st.session_state.cases_parse_error = None
                            st.session_state.cases = cases
                            st.session_state.scroll_to = "cases"

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

            if gen_pytest:

                if not requirement.strip():

                    st.warning("请输入需求")

                else:

                    try:

                        with st.spinner("Generating Pytest..."):

                            script = generate_pytest(
                                requirement
                            )

                            st.session_state.pytest_code = script
                            st.session_state.scroll_to = "pytest"

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

            if gen_postman:

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
                            st.session_state.push_result = None
                            st.session_state.scroll_to = "postman"

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

        st.markdown('<div class="file-tab"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#787774" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>output.log</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-box">', unsafe_allow_html=True)

        has_any_result = (
            st.session_state.cases
            or st.session_state.pytest_code
            or st.session_state.collection
            or st.session_state.get("cases_parse_error")
        )

        if not has_any_result:
            st.markdown(
                '<p style="font-family:var(--font-ui);color:var(--text-faint);font-size:0.88rem;padding:6px 2px;">'
                '等待生成结果 — 点击左侧按钮开始'
                '</p>',
                unsafe_allow_html=True
            )

        else:

            tab_cases, tab_pytest, tab_postman = st.tabs([
                "● TEST CASES" if st.session_state.cases else "TEST CASES",
                "● PYTEST" if st.session_state.pytest_code else "PYTEST",
                "● POSTMAN" if st.session_state.collection else "POSTMAN",
            ])

            # 生成结果后自动切换到对应 tab 并滚动到结果区
            _scroll_target = st.session_state.get("scroll_to")
            if _scroll_target:
                _tab_label = {
                    "cases": "TEST CASES",
                    "pytest": "PYTEST",
                    "postman": "POSTMAN",
                }.get(_scroll_target, "")
                if _tab_label:
                    components.html(
                        f"""
                        <script>
                        setTimeout(function() {{
                            var doc = window.parent.document;
                            var tabs = doc.querySelectorAll('[role="tab"]');
                            for (var i = 0; i < tabs.length; i++) {{
                                if (tabs[i].textContent.includes('{_tab_label}')) {{
                                    tabs[i].click();
                                    tabs[i].scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                    break;
                                }}
                            }}
                        }}, 300);
                        </script>
                        """,
                        height=0,
                    )
                st.session_state.scroll_to = None

            # ---- Test Cases ----
            with tab_cases:

                if st.session_state.get("cases_parse_error"):

                    st.error("✗ AI返回的不是合法JSON")
                    with st.expander("AI原始返回内容"):
                        st.code(st.session_state.cases_parse_error)

                elif st.session_state.cases:

                    head_l, copy_col, head_r = st.columns([4, 1, 1])

                    with head_l:
                        st.markdown('<div class="section-label">TEST CASES</div>', unsafe_allow_html=True)

                    with copy_col:
                        copy_button_component(
                            json.dumps(st.session_state.cases, ensure_ascii=False, indent=2)
                        )

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

                    if st.session_state.get("raw_cases"):
                        with st.expander("AI原始返回内容"):
                            st.code(st.session_state.raw_cases)

                else:
                    st.caption("尚未生成 — 点击左侧 Test Cases")

            # ---- Pytest ----
            with tab_pytest:

                if st.session_state.pytest_code:

                    head_l, zip_col, head_r = st.columns([4, 1, 1])

                    with head_l:
                        st.markdown('<div class="section-label">PYTEST SCRIPT</div>', unsafe_allow_html=True)

                    with zip_col:
                        st.download_button(
                            "↓ 测试包 .zip",
                            build_pytest_package(st.session_state.pytest_code),
                            "pytest_project.zip",
                            mime="application/zip",
                            use_container_width=True
                        )

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
                    st.caption("尚未生成 — 点击左侧 Pytest")

            # ---- Postman Collection ----
            with tab_postman:

                if st.session_state.collection:

                    head_l, push_col, head_r = st.columns([4, 1, 1])

                    with head_l:
                        st.markdown('<div class="section-label">POSTMAN COLLECTION</div>', unsafe_allow_html=True)

                    with push_col:
                        _pkey = st.session_state.get("postman_api_key", "")
                        if st.button(
                            "↑ 推送到 Postman",
                            use_container_width=True,
                            disabled=not _pkey.strip(),
                            help="" if _pkey.strip() else "先在左侧栏「Postman 一键导入（可选）」中填入 Postman API Key"
                        ):
                            with st.spinner("推送中..."):
                                try:
                                    _res = push_to_postman(
                                        st.session_state.collection,
                                        _pkey,
                                        st.session_state.get("postman_workspace_id", "")
                                    )
                                    _uid = (_res.get("collection") or {}).get("uid", "OK")
                                    if st.session_state.get("postman_workspace_id", "").strip():
                                        st.session_state.push_result = (
                                            True,
                                            f"✓ 已推送到指定 Workspace（uid: {_uid}）。打开 Postman 对应 Workspace 刷新即可看到"
                                        )
                                    else:
                                        st.session_state.push_result = (
                                            True,
                                            f"✓ 已推送到 API Key 账号的默认 Workspace（uid: {_uid}）。你没填 Workspace ID — 在 Postman 左上角切到 My Workspace 查看；或在左侧栏「列出 Workspace」拿到目标 ID 填入后重推"
                                        )
                                except Exception as _e:
                                    st.session_state.push_result = (False, f"推送失败：{_e}")
                            st.rerun()

                    with head_r:
                        st.download_button(
                            "↓ collection.json",
                            st.session_state.collection,
                            "postman_collection.json",
                            mime="application/json",
                            use_container_width=True
                        )

                    _pr = st.session_state.get("push_result")
                    if _pr:
                        (st.success if _pr[0] else st.error)(_pr[1])

                    st.code(
                        st.session_state.collection,
                        language="json"
                    )

                    st.caption("导入方法：Postman → Import → 选择下载的 JSON 文件")

                else:
                    st.caption("尚未生成 — 点击左侧 Postman")

        st.markdown('</div>', unsafe_allow_html=True)

# ==========================
# 主区域：History 页面
# ==========================

elif page == "History":

    st.markdown("""
    <div class="hero">
        <div class="hero-row">
            <span class="hero-badge"><svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='#ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg></span>
            <h1 class="hero-title">History</h1>
        </div>
        <p class="hero-sub">生成记录 — 测试用例 · Pytest · Postman</p>
    </div>
    """, unsafe_allow_html=True)

    if len(st.session_state.history) == 0:

        st.markdown(
            '<p style="font-family:var(--font-ui);color:var(--text-faint);font-size:0.88rem;padding:6px 2px;">'
            '暂无记录 — 生成内容后会显示在这里'
            '</p>',
            unsafe_allow_html=True
        )

    else:

        for i, item in enumerate(
            reversed(st.session_state.history)
        ):

            with st.expander(
                f"{item['type']} · #{i+1}"
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

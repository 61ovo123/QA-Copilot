# QA Copilot

> AI-Native Software Testing Platform — 输入一段需求描述，自动生成测试用例、pytest 自动化脚本、Postman 接口测试集合。

基于 Streamlit + DeepSeek API 构建，面向软件测试场景，把"写测试用例 / 写自动化脚本 / 写接口测试集合"这三件重复劳动交给 AI，测试工程师只需要描述需求、审核结果、下载使用。

## 功能特性

- **测试用例生成**：输入需求描述，AI按结构化JSON格式生成测试用例（编号 / 场景 / 预期结果），表格展示，支持一键导出 Excel
- **Pytest 脚本生成**：根据需求自动生成可直接使用的 pytest 自动化测试脚本
- **Postman Collection 生成**：根据需求生成符合 Postman Collection v2.1 规范的接口测试集合，可直接导入 Postman
- **历史记录**：所有生成记录自动保存在当前会话中，可随时回看
- **结果区Tab切换**：三类生成结果分Tab展示，互不干扰，下载按钮固定在内容右上角

## 技术栈

| 模块 | 技术 |
|---|---|
| 前端/应用框架 | Streamlit |
| AI 能力 | DeepSeek API（通过 OpenAI SDK 兼容接口调用） |
| 数据处理 | pandas |
| Excel 导出 | openpyxl |

## 项目结构

```
.
├── app.py                          # 主程序
├── requirements.txt                # 依赖列表
├── .streamlit/
│   ├── config.toml                 # 界面主题配置（已包含，可直接使用）
│   └── secrets.toml.example        # API Key 配置模板（复制后改名使用）
└── .gitignore
```

## 快速开始

### 1. 克隆项目并安装依赖

```bash
git clone https://github.com/你的用户名/你的仓库名.git
cd 你的仓库名
pip install -r requirements.txt
```

建议在虚拟环境中安装：

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置 DeepSeek API Key

项目使用 Streamlit 的 `secrets.toml` 机制管理密钥，**不会**把密钥提交到 GitHub。

1. 前往 [DeepSeek 开放平台](https://platform.deepseek.com) 注册并获取 API Key
2. 复制模板文件并改名：

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

3. 打开 `.streamlit/secrets.toml`，填入你自己的 Key：

```toml
DEEPSEEK_API_KEY = "sk-你的真实key"
```

> `.streamlit/secrets.toml` 已经在 `.gitignore` 中被排除，不会被提交，放心填写真实密钥。

### 3. 运行项目

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。

## 使用说明

1. 在左侧 `requirement.md` 输入框中描述需求，例如：
   ```
   POST /login
   参数：username, password
   返回：token
   ```
2. 点击 `Test Cases` / `Pytest` / `Postman` 三个按钮中的任意一个，等待AI生成
3. 右侧 `output.log` 区域会按Tab展示生成结果，点击右上角下载按钮获取文件
4. 左侧导航栏切换到 `History` 可查看本次会话内的全部生成记录

## 注意事项

- AI生成的测试用例/脚本/接口集合建议人工复核后再用于正式测试流程，AI可能遗漏边界场景或生成不完全符合项目实际接口规范的内容
- `DEEPSEEK_API_KEY` 属于敏感信息，请勿在任何情况下提交到公开仓库
- 如需部署到 Streamlit Community Cloud，需在部署平台的 Secrets 管理界面单独配置 `DEEPSEEK_API_KEY`，本地的 `secrets.toml` 不会自动同步上去


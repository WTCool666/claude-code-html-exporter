# Claude Code HTML Exporter

![view](https://github.com/WTCool666/claude-code-html-exporter/blob/master/res/1.png)

将 Claude Code CLI 的会话记录（`.jsonl`）导出为美观的、自包含的终端风格 HTML 页面。支持离线浏览、搜索和分享。

### 功能特性

- **终端深色主题** — 模拟 xshell / Claude Code CLI 的视觉体验
- **Markdown 预渲染** — 标题、加粗、斜体、代码块、表格等在 Python 端完成渲染，无需联网加载 CDN
- **Diff 高亮** — 代码块中 `+`/`-` 行自动标记绿色/红色背景
- **侧边栏导航** — 左侧列出所有用户提问，点击直接跳转
- **全文搜索** — 所有匹配结果在正文中高亮显示，点击结果精确跳转，支持上一条/下一条
- **过滤开关** — 工具调用、工具结果、思考过程、时间戳可独立显示/隐藏
- **自动展开折叠** — 勾选时自动展开所有详情，取消勾选时折叠并隐藏
- **自包含 HTML** — 单个 `.html` 文件，无外部依赖，离线可用

### 使用方法

```bash
# 交互模式：列出所有会话，输入序号导出
python3 claude_session_html.py

# 直接指定会话文件
python3 claude_session_html.py ~/.claude/projects/.../abc123.jsonl

# 也可以传目录路径（自动查找 .jsonl）
python3 claude_session_html.py ~/.claude/projects/.../abc123

# 指定输出路径
python3 claude_session_html.py <会话路径> output.html

# 列出所有可用会话
python3 claude_session_html.py -l
```

### 原理

Claude Code 将会话记录存储在 `~/.claude/projects/` 目录下的 `.jsonl` 文件中。每行是一个 JSON 对象，代表一条消息、工具调用或元数据。本脚本：

1. 读取并解析 `.jsonl` 会话文件
2. 用 Python `markdown` 库将 Markdown 渲染为 HTML
3. 对代码块中的 diff 行添加颜色高亮
4. 生成包含内嵌 CSS 和 JavaScript 的完整 HTML 页面
5. 输出单个 `.html` 文件，任何浏览器都能打开

# 

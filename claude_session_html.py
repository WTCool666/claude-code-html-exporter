#!/usr/bin/env python3
"""
将 Claude Code 的 JSONL 会话文件导出为终端风格的 HTML 页面。
Markdown 在 Python 端预渲染，无需联网。

用法:
    python3 claude_session_html.py <session_path> [output.html]
    python3 claude_session_html.py -l                    # 列出所有会话
"""

import json
import sys
import os
import re
import html
import markdown
from pathlib import Path
from datetime import datetime

CLAUDE_DIR = Path.home() / ".claude" / "projects"

# ─── HTML 模板 ──────────────────────────────────────────────

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {
    --bg: #1e1e2e;
    --fg: #ffffff;
    --fg-dim: #9399b2;
    --fg-user: #a6e3a1;
    --fg-claude: #89b4fa;
    --fg-tool: #f9e2af;
    --fg-result: #ffffff;
    --fg-thinking: #ffffff;
    --border: #313244;
    --accent: #cba6f7;
    --scrollbar: #45475a;
    --scrollbar-hover: #585b70;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html { font-size: 16px; }
  body {
    background: var(--bg);
    color: var(--fg);
    font-family: 'Cascadia Code', 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
    line-height: 1.6;
    overflow: hidden;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  /* 主体区域：侧边栏 + 内容 */
  .main-wrap {
    flex: 1;
    display: flex;
    overflow: hidden;
  }
  /* 侧边栏 */
  .sidebar {
    width: 280px;
    min-width: 280px;
    background: #11111b;
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: width 0.2s, min-width 0.2s;
  }
  .sidebar.collapsed {
    width: 0;
    min-width: 0;
    border-right: none;
  }
  .sidebar-header {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }
  .sidebar-header span { color: var(--fg-dim); font-size: 0.85rem; font-weight: 600; }
  .sidebar-toggle {
    background: none; border: none; color: var(--fg-dim); cursor: pointer;
    font-size: 1.2rem; padding: 2px 6px; border-radius: 3px; font-family: inherit;
  }
  .sidebar-toggle:hover { color: var(--fg); background: var(--border); }
  .sidebar-list {
    flex: 1; overflow-y: auto; padding: 6px 0;
  }
  .sidebar-list::-webkit-scrollbar { width: 4px; }
  .sidebar-list::-webkit-scrollbar-thumb { background: var(--scrollbar); border-radius: 2px; }
  .nav-item {
    display: block;
    padding: 8px 14px;
    color: var(--fg-dim);
    font-size: 0.8rem;
    line-height: 1.4;
    cursor: pointer;
    border-left: 3px solid transparent;
    transition: all 0.15s;
    text-decoration: none;
    word-break: break-all;
  }
  .nav-item:hover {
    background: rgba(137, 180, 250, 0.08);
    color: var(--fg);
    border-left-color: var(--accent);
  }
  .nav-item.active {
    background: rgba(137, 180, 250, 0.12);
    color: var(--fg);
    border-left-color: var(--fg-claude);
  }
  .nav-item .nav-num {
    color: var(--fg-claude);
    font-weight: 700;
    margin-right: 6px;
    font-size: 0.75rem;
  }
  .nav-item .nav-time {
    color: var(--fg-dim);
    font-size: 0.7rem;
    opacity: 0.6;
  }
  /* 折叠按钮（侧边栏收起时显示） */
  .sidebar-expand {
    display: none;
    position: fixed;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    background: var(--border);
    color: var(--fg-dim);
    border: none;
    border-radius: 0 4px 4px 0;
    padding: 12px 6px;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.9rem;
    z-index: 10;
  }
  .sidebar-expand:hover { background: var(--scrollbar-hover); color: var(--fg); }
  .sidebar.collapsed ~ .content-wrap .sidebar-expand { display: block; }
  /* 内容区 */
  .content-wrap {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    position: relative;
  }
  .titlebar {
    background: #11111b;
    border-bottom: 1px solid var(--border);
    padding: 10px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }
  .titlebar-dots { display: flex; gap: 6px; }
  .titlebar-dots span { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
  .titlebar-dots .red { background: #f38ba8; }
  .titlebar-dots .yellow { background: #f9e2af; }
  .titlebar-dots .green { background: #a6e3a1; }
  .titlebar-info { color: var(--fg-dim); font-size: 0.85rem; }
  .titlebar-info strong { color: var(--fg); font-weight: 600; }
  .toolbar {
    background: #181825;
    border-bottom: 1px solid var(--border);
    padding: 6px 20px;
    display: flex;
    gap: 12px;
    align-items: center;
    flex-shrink: 0;
  }
  .toolbar label { color: var(--fg-dim); font-size: 0.8rem; cursor: pointer; display: flex; align-items: center; gap: 4px; }
  .toolbar label:hover { color: var(--fg); }
  .toolbar input[type="checkbox"] { accent-color: var(--accent); cursor: pointer; }
  .toolbar .nav-info { margin-left: auto; color: var(--fg-dim); font-size: 0.8rem; }
  .toolbar button {
    background: var(--border); color: var(--fg); border: none; border-radius: 4px;
    padding: 4px 10px; cursor: pointer; font-family: inherit; font-size: 0.8rem;
  }
  .toolbar button:hover { background: var(--scrollbar-hover); }
  .chat-area {
    flex: 1; overflow-y: auto; padding: 16px 20px; scroll-behavior: smooth;
  }
  .chat-area::-webkit-scrollbar { width: 8px; }
  .chat-area::-webkit-scrollbar-track { background: transparent; }
  .chat-area::-webkit-scrollbar-thumb { background: var(--scrollbar); border-radius: 4px; }
  .chat-area::-webkit-scrollbar-thumb:hover { background: var(--scrollbar-hover); }
  .msg-block { margin-bottom: 16px; }
  .msg-timestamp { color: var(--fg-dim); font-size: 0.75rem; margin-bottom: 2px; opacity: 0.7; }
  .msg-user {
    color: var(--fg-user); white-space: pre-wrap; word-break: break-word; font-size: 1.05rem;
    padding: 8px 12px; background: rgba(166, 227, 161, 0.06);
    border-left: 3px solid var(--fg-user); border-radius: 0 6px 6px 0;
  }
  .msg-user .prompt-symbol { color: var(--fg-user); opacity: 0.7; margin-right: 4px; }
  .msg-claude { color: var(--fg); padding: 4px 0; }
  .msg-tool {
    color: var(--fg-tool); font-size: 0.95rem; padding: 6px 12px;
    background: rgba(249, 226, 175, 0.04); border-left: 2px solid rgba(249, 226, 175, 0.3);
    border-radius: 0 4px 4px 0; margin: 4px 0;
  }
  .msg-tool .tool-name { color: var(--fg-tool); font-weight: 600; }
  .msg-tool .tool-cmd { color: var(--fg); white-space: pre-wrap; margin-top: 4px; font-size: 0.82rem; }
  .msg-tool .tool-file { color: var(--accent); }
  .msg-tool .tool-desc { color: var(--fg-dim); font-style: italic; }
  .msg-result { color: var(--fg-result); font-size: 0.92rem; margin: 2px 0; }
  .msg-result summary { cursor: pointer; color: var(--fg-dim); font-size: 0.88rem; padding: 2px 0; user-select: none; }
  .msg-result summary:hover { color: var(--fg); }
  .msg-result .result-content {
    color: var(--fg-result); white-space: pre-wrap; word-break: break-all;
    background: rgba(0,0,0,0.2); padding: 8px 10px; border-radius: 4px;
    max-height: 400px; overflow-y: auto; font-size: 0.88rem; line-height: 1.5;
  }
  .msg-result .result-content::-webkit-scrollbar { width: 6px; }
  .msg-result .result-content::-webkit-scrollbar-thumb { background: var(--scrollbar); border-radius: 3px; }
  .msg-thinking { color: var(--fg-thinking); font-size: 0.92rem; margin: 2px 0; }
  .msg-thinking summary { cursor: pointer; color: var(--fg-dim); font-size: 0.88rem; font-style: italic; padding: 2px 0; user-select: none; }
  .msg-thinking summary:hover { color: var(--fg-result); }
  .msg-thinking .thinking-content {
    color: var(--fg-thinking); white-space: pre-wrap; padding: 6px 10px;
    border-left: 2px solid var(--fg-thinking); font-size: 0.88rem; line-height: 1.5;
  }
  .highlight { background: rgba(249, 226, 175, 0.3); border-radius: 2px; padding: 0 2px; }
  .search-panel {
    display: none; background: #181825; border-top: 1px solid var(--border);
    flex-direction: column; flex-shrink: 0; max-height: 50vh;
  }
  .search-panel.active { display: flex; }
  .search-row {
    display: flex; align-items: center; gap: 8px; padding: 8px 16px; flex-shrink: 0;
  }
  .search-row input {
    flex: 1; background: var(--bg); border: 1px solid var(--border); color: var(--fg);
    padding: 6px 10px; border-radius: 4px; font-family: inherit; font-size: 0.88rem; outline: none;
  }
  .search-row input:focus { border-color: var(--accent); }
  .search-row .search-info { color: var(--fg-dim); font-size: 0.8rem; white-space: nowrap; }
  .search-row button {
    background: var(--border); color: var(--fg); border: none; border-radius: 4px;
    padding: 4px 10px; cursor: pointer; font-family: inherit; font-size: 0.78rem;
  }
  .search-row button:hover { background: var(--scrollbar-hover); }
  .search-results {
    overflow-y: auto; border-top: 1px solid var(--border); flex: 1;
  }
  .search-results::-webkit-scrollbar { width: 6px; }
  .search-results::-webkit-scrollbar-thumb { background: var(--scrollbar); border-radius: 3px; }
  .sr-item {
    padding: 6px 16px; cursor: pointer; border-bottom: 1px solid rgba(49,50,68,0.5);
    font-size: 0.82rem; line-height: 1.5; color: var(--fg-dim);
  }
  .sr-item:hover { background: rgba(137, 180, 250, 0.08); color: var(--fg); }
  .sr-item .sr-ctx { word-break: break-all; }
  .sr-item mark { background: rgba(249, 226, 175, 0.35); color: var(--fg); border-radius: 2px; padding: 0 2px; }
  .sr-item .sr-loc { color: var(--fg-dim); font-size: 0.72rem; opacity: 0.6; margin-top: 2px; }
  /* Markdown 渲染样式 */
  .md-body { font-size: 1.05rem; line-height: 1.8; color: #ffffff; }
  .md-body h1, .md-body h2, .md-body h3, .md-body h4, .md-body h5, .md-body h6 {
    color: var(--fg-claude); margin: 18px 0 10px 0; font-weight: 700; line-height: 1.3;
  }
  .md-body h1 { font-size: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
  .md-body h2 { font-size: 1.3rem; border-bottom: 1px solid var(--border); padding-bottom: 4px; }
  .md-body h3 { font-size: 1.15rem; }
  .md-body p { margin: 8px 0; color: #ffffff; }
  .md-body strong { color: #ffffff; font-weight: 700; }
  .md-body em { color: #ffffff; font-style: italic; }
  .md-body a { color: var(--accent); text-decoration: underline; }
  .md-body ul, .md-body ol { margin: 8px 0; padding-left: 26px; }
  .md-body li { margin: 4px 0; color: #ffffff; }
  .md-body code {
    background: rgba(0,0,0,0.3); color: #a6e3a1; padding: 2px 6px; border-radius: 3px; font-size: 0.9em;
  }
  .md-body pre {
    background: #11111b; border: 1px solid var(--border); border-radius: 6px;
    margin: 10px 0; overflow-x: auto; font-size: 0.88em; line-height: 1.5;
  }
  .md-body pre code {
    background: none; color: var(--fg); padding: 12px 16px; font-size: 1em;
    display: block; white-space: pre;
  }
  .md-body pre code .diff-add {
    background: rgba(166, 227, 161, 0.18); color: #a6e3a1; display: block;
    margin: 0 -16px; padding: 0 16px;
  }
  .md-body pre code .diff-del {
    background: rgba(243, 139, 168, 0.18); color: #f38ba8; display: block;
    margin: 0 -16px; padding: 0 16px;
  }
  .md-body blockquote {
    border-left: 3px solid var(--accent); margin: 8px 0; padding: 4px 12px;
    color: var(--fg-dim); background: rgba(203,166,247,0.05);
  }
  .md-body hr { border: none; border-top: 1px solid var(--border); margin: 16px 0; }
  .md-body table { border-collapse: collapse; margin: 8px 0; width: 100%; }
  .md-body th, .md-body td { border: 1px solid var(--border); padding: 6px 10px; text-align: left; }
  .md-body th { background: rgba(0,0,0,0.3); color: var(--fg-claude); }
  .md-body img { max-width: 100%; border-radius: 6px; }
  .highlight { background: rgba(249, 226, 175, 0.3); border-radius: 2px; padding: 0 2px; }
  .highlight-current { background: rgba(249, 226, 175, 0.7); outline: 2px solid #f9e2af; border-radius: 2px; }
</style>
</head>
<body>

<div class="titlebar">
  <div class="titlebar-dots">
    <span class="red"></span>
    <span class="yellow"></span>
    <span class="green"></span>
  </div>
  <div class="titlebar-info">
    <strong>Claude Code</strong> &nbsp;&middot;&nbsp; {session_info} &nbsp;&middot;&nbsp; {turn_count} 轮对话 &nbsp;&middot;&nbsp; {msg_count} 条消息
  </div>
</div>

<div class="toolbar">
  <label><input type="checkbox" id="chk-tool" checked> 工具调用</label>
  <label><input type="checkbox" id="chk-result" checked> 工具结果</label>
  <label><input type="checkbox" id="chk-thinking" checked> 思考过程</label>
  <label><input type="checkbox" id="chk-timestamp" checked> 时间戳</label>
  <div class="nav-info">
    <button onclick="toggleSearch()">搜索</button>
    <button onclick="document.getElementById('chat').scrollTop=0">顶部</button>
    <button onclick="document.getElementById('chat').scrollTop=99999999">底部</button>
  </div>
</div>

<div class="main-wrap">
  <div class="sidebar" id="sidebar">
    <div class="sidebar-header">
      <span>对话导航</span>
      <button class="sidebar-toggle" onclick="toggleSidebar()" title="收起侧边栏">&larr;</button>
    </div>
    <div class="sidebar-list" id="nav-list">
{nav_items}
    </div>
  </div>
  <div class="content-wrap">
    <button class="sidebar-expand" onclick="toggleSidebar()">&#9654;</button>
    <div class="search-panel" id="search-panel">
      <div class="search-row">
        <input type="text" id="search-input" placeholder="搜索对话内容...">
        <span class="search-info" id="search-info"></span>
        <button onclick="searchPrev()">上一条</button>
        <button onclick="searchNext()">下一条</button>
        <button onclick="closeSearch()">关闭</button>
      </div>
      <div class="search-results" id="search-results"></div>
    </div>
    <div class="chat-area" id="chat">
{chat_content}
    </div>
  </div>
</div>

<script>
(function() {
  var map = {
    'chk-tool': 'msg-tool',
    'chk-result': 'msg-result',
    'chk-thinking': 'msg-thinking',
    'chk-timestamp': 'msg-timestamp'
  };
  for (var id in map) {
    (function(checkboxId, cls) {
      document.getElementById(checkboxId).addEventListener('change', function() {
        var show = this.checked;
        var els = document.querySelectorAll('.' + cls);
        for (var i = 0; i < els.length; i++) {
          if (show) {
            els[i].style.display = '';
            if (els[i].tagName === 'DETAILS') els[i].setAttribute('open', '');
          } else {
            if (els[i].tagName === 'DETAILS') els[i].removeAttribute('open');
            els[i].style.display = 'none';
          }
        }
      });
    })(id, map[id]);
  }
})();

var searchMatches = [];
var searchIdx = -1;
var searchTimer = null;
var currentQuery = '';

document.getElementById('search-input').addEventListener('input', function() {
  clearTimeout(searchTimer);
  var q = this.value;
  searchTimer = setTimeout(function() { doSearch(q); }, 300);
});

function toggleSearch() {
  var panel = document.getElementById('search-panel');
  panel.classList.toggle('active');
  if (panel.classList.contains('active')) document.getElementById('search-input').focus();
}

function closeSearch() {
  document.getElementById('search-panel').classList.remove('active');
  clearAllHighlights();
  searchMatches = [];
  searchIdx = -1;
  currentQuery = '';
  document.getElementById('search-results').innerHTML = '';
  document.getElementById('search-info').textContent = '';
  document.getElementById('search-input').value = '';
}

function clearAllHighlights() {
  document.getElementById('chat').querySelectorAll('.highlight, .highlight-current').forEach(function(el) {
    var text = document.createTextNode(el.textContent);
    el.parentNode.replaceChild(text, el);
  });
  // 合并相邻文本节点
  document.getElementById('chat').normalize();
}

function doSearch(query) {
  clearAllHighlights();
  searchMatches = [];
  searchIdx = -1;
  currentQuery = query;
  var resultsEl = document.getElementById('search-results');
  var info = document.getElementById('search-info');
  resultsEl.innerHTML = '';
  if (!query || query.length < 2) { info.textContent = query ? '至少输入2个字符' : ''; return; }

  var qLow = query.toLowerCase();
  var chat = document.getElementById('chat');
  var blocks = chat.querySelectorAll('.msg-block');
  var listHtml = '';

  for (var b = 0; b < blocks.length; b++) {
    var block = blocks[b];
    var blockId = block.id || '';
    // 在 block 的文本节点中高亮所有匹配
    var matchSpans = highlightAll(block, query);
    // 生成搜索结果列表（用匹配的 span 信息）
    var text = block.textContent;
    var pos = 0;
    while (true) {
      var idx = text.toLowerCase().indexOf(qLow, pos);
      if (idx < 0) break;
      var start = Math.max(0, idx - 30);
      var end = Math.min(text.length, idx + query.length + 30);
      var ctx = text.substring(start, end).replace(/[\\r\\n]/g, ' ');
      var mi = idx - start;
      var turnLabel = blockId ? blockId.replace('turn-', '#') : '';
      var li = searchMatches.length;
      listHtml += '<div class="sr-item" data-idx="' + li + '">';
      listHtml += '<div class="sr-ctx">' + escHtml(ctx.substring(0, mi)) + '<mark>' + escHtml(ctx.substring(mi, mi + query.length)) + '</mark>' + escHtml(ctx.substring(mi + query.length)) + '</div>';
      listHtml += '<div class="sr-loc">' + escHtml(turnLabel) + '</div>';
      listHtml += '</div>';
      searchMatches.push({ blockId: blockId, charOffset: idx });
      pos = idx + 1;
    }
  }

  resultsEl.innerHTML = listHtml;
  info.textContent = searchMatches.length > 0 ? searchMatches.length + ' 处匹配' : '无匹配';

  resultsEl.querySelectorAll('.sr-item').forEach(function(item, i) {
    item.addEventListener('click', function() { searchIdx = i; jumpToMatch(i); });
  });
}

function highlightAll(root, query) {
  var qLow = query.toLowerCase();
  var qLen = query.length;
  var spans = [];
  var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
  var nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);

  for (var n = 0; n < nodes.length; n++) {
    var node = nodes[n];
    var text = node.textContent;
    var pos = 0;
    var parts = [];
    var last = 0;
    var hasMatch = false;
    while (true) {
      var found = text.toLowerCase().indexOf(qLow, pos);
      if (found < 0) break;
      hasMatch = true;
      if (found > last) parts.push(document.createTextNode(text.substring(last, found)));
      var span = document.createElement('span');
      span.className = 'highlight';
      span.textContent = text.substring(found, found + qLen);
      parts.push(span);
      spans.push(span);
      last = found + qLen;
      pos = last;
    }
    if (hasMatch) {
      if (last < text.length) parts.push(document.createTextNode(text.substring(last)));
      var frag = document.createDocumentFragment();
      for (var p = 0; p < parts.length; p++) frag.appendChild(parts[p]);
      node.parentNode.replaceChild(frag, node);
    }
  }
  return spans;
}

function escHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function searchNext() {
  if (!searchMatches.length) return;
  searchIdx = (searchIdx + 1) % searchMatches.length;
  jumpToMatch(searchIdx);
}

function searchPrev() {
  if (!searchMatches.length) return;
  searchIdx = (searchIdx - 1 + searchMatches.length) % searchMatches.length;
  jumpToMatch(searchIdx);
}

function jumpToMatch(idx) {
  // 清除之前的当前高亮，恢复为普通高亮
  var prev = document.querySelector('.highlight-current');
  if (prev) prev.className = 'highlight';

  var items = document.querySelectorAll('.sr-item');
  items.forEach(function(it, i) { it.style.background = i === idx ? 'rgba(137, 180, 250, 0.15)' : ''; });

  var match = searchMatches[idx];
  if (!match) return;
  var block = document.getElementById(match.blockId);
  if (!block) return;

  // 找到 block 中第 N 个 highlight span 设为 current
  var allHl = block.querySelectorAll('.highlight');
  // 计算这个匹配在 block 中是第几个（按 charOffset 匹配）
  var qLow = currentQuery.toLowerCase();
  var count = 0;
  var targetCount = 0;
  var text = block.textContent;
  var p = 0;
  while (true) {
    var fi = text.toLowerCase().indexOf(qLow, p);
    if (fi < 0) break;
    if (Math.abs(fi - match.charOffset) < 5) { targetCount = count; break; }
    count++;
    p = fi + 1;
  }
  if (allHl[targetCount]) {
    allHl[targetCount].className = 'highlight-current';
    allHl[targetCount].scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else if (block) {
    block.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  if (items[idx]) items[idx].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  document.getElementById('search-info').textContent = (idx + 1) + '/' + searchMatches.length;
}

document.addEventListener('keydown', function(e) {
  if (e.key === '/' && !e.ctrlKey && document.activeElement.tagName !== 'INPUT') { e.preventDefault(); toggleSearch(); }
  if (e.key === 'Escape') closeSearch();
  // Enter 下一条, Shift+Enter 上一条
  if (document.activeElement === document.getElementById('search-input')) {
    if (e.key === 'Enter') { e.preventDefault(); e.shiftKey ? searchPrev() : searchNext(); }
  }
});

/* 侧边栏收起/展开 */
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

/* 点击导航跳转 */
document.getElementById('nav-list').addEventListener('click', function(e) {
  var item = e.target.closest('.nav-item');
  if (!item) return;
  var targetId = item.getAttribute('data-target');
  var target = document.getElementById(targetId);
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    // 高亮
    document.querySelectorAll('.nav-item').forEach(function(n) { n.classList.remove('active'); });
    item.classList.add('active');
  }
});

/* 滚动时自动高亮当前导航项 */
var chatEl = document.getElementById('chat');
chatEl.addEventListener('scroll', function() {
  var blocks = document.querySelectorAll('.msg-block[id]');
  var navItems = document.querySelectorAll('.nav-item');
  if (!blocks.length) return;
  var scrollTop = chatEl.scrollTop;
  var current = null;
  for (var i = blocks.length - 1; i >= 0; i--) {
    if (blocks[i].offsetTop - chatEl.offsetTop <= scrollTop + 40) {
      current = blocks[i].id;
      break;
    }
  }
  navItems.forEach(function(n) {
    n.classList.toggle('active', n.getAttribute('data-target') === current);
  });
});
</script>
</body>
</html>'''


def get_all_sessions():
    sessions = []
    for jsonl in CLAUDE_DIR.rglob("*.jsonl"):
        stat = jsonl.stat()
        sessions.append((jsonl, stat.st_mtime, stat.st_size))
    sessions.sort(key=lambda x: x[1], reverse=True)
    return sessions


def list_sessions():
    sessions = get_all_sessions()
    if not sessions:
        print("没有找到任何会话文件。")
        return
    print(f"{'序号':<5} {'大小':>8} {'最后修改时间':<22} {'文件路径'}")
    print("-" * 100)
    for i, (path, mtime, size) in enumerate(sessions, 1):
        mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        if size > 1024 * 1024:
            size_str = f"{size / 1024 / 1024:.1f}MB"
        elif size > 1024:
            size_str = f"{size / 1024:.1f}KB"
        else:
            size_str = f"{size}B"
        print(f"{i:<5} {size_str:>8} {mtime_str:<22} {path}")


def h(text):
    return html.escape(str(text))


def render_markdown(text):
    """Markdown -> HTML，并添加 diff 高亮"""
    rendered = markdown.markdown(text, extensions=['fenced_code', 'tables'])

    # diff 高亮：对 <pre><code>...</code></pre> 块内的 +行/-行 加颜色
    def diff_replacer(m):
        prefix = m.group(1)
        code_content = m.group(2)
        lines = code_content.split('\n')
        result = []
        for line in lines:
            if line.startswith('+') and len(line) > 1:
                result.append(f'<span class="diff-add">{line}</span>')
            elif line.startswith('-') and len(line) > 1:
                result.append(f'<span class="diff-del">{line}</span>')
            else:
                result.append(line)
        return prefix + '\n'.join(result) + '</code></pre>'

    rendered = re.sub(
        r'(<pre><code[^>]*>)(.*?)(</code></pre>)',
        diff_replacer, rendered, flags=re.DOTALL
    )
    return rendered


def format_tool_use_block(block):
    name = block.get("name", "unknown_tool")
    tool_input = block.get("input", {})
    parts = [f'<span class="tool-name">&tridot; {h(name)}</span>']

    if name == "Bash":
        cmd = tool_input.get("command", "")
        desc = tool_input.get("description", "")
        parts.append(f'<div class="tool-cmd">{h(cmd)}</div>')
        if desc:
            parts.append(f'<div class="tool-desc">{h(desc)}</div>')
    elif name in ("Read", "Write", "Edit"):
        filepath = tool_input.get("file_path", "")
        parts.append(f' <span class="tool-file">{h(filepath)}</span>')
        if name == "Edit":
            old = tool_input.get("old_string", "")
            new = tool_input.get("new_string", "")
            old_lines = '\n'.join(f'<span style="color:#f38ba8">- {h(line)}</span>' for line in old.split('\n'))
            new_lines = '\n'.join(f'<span style="color:#a6e3a1">+ {h(line)}</span>' for line in new.split('\n'))
            parts.append(f'<div class="tool-cmd">{old_lines}</div>')
            parts.append(f'<div class="tool-cmd">{new_lines}</div>')
        elif name == "Write":
            content = tool_input.get("content", "")
            content_lines = '\n'.join(h(line) for line in content.split('\n'))
            parts.append(f'<div class="tool-cmd">{content_lines}</div>')
    elif name == "WebSearch":
        query = tool_input.get("query", "")
        parts.append(f' 搜索: <span class="tool-file">{h(query)}</span>')
    else:
        for key, val in tool_input.items():
            val_str = str(val)
            parts.append(f'<div class="tool-desc">{h(key)}: {h(val_str)}</div>')
    return '<div class="msg-tool">' + "".join(parts) + '</div>'


def format_tool_result_block(block):
    content = block.get("content", "")
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
            else:
                parts.append(str(c))
        content = "\n".join(parts)
    if not content.strip():
        return ""
    if len(content) > 5000:
        content = content[:5000] + f"\n... (共 {len(content)} 字符)"
    return (f'<details class="msg-result"><summary>&tridot; 工具返回结果</summary>'
            f'<div class="result-content">{h(content)}</div></details>')


def format_thinking_block(block):
    thinking = block.get("thinking", "")
    if not thinking.strip():
        return ""
    if len(thinking) > 3000:
        thinking = thinking[:3000] + f"\n... (共 {len(thinking)} 字符)"
    return (f'<details class="msg-thinking"><summary>&tridot; 思考过程</summary>'
            f'<div class="thinking-content">{h(thinking)}</div></details>')


def export_session(jsonl_path, output_path=None):
    jsonl_path = Path(jsonl_path)
    if jsonl_path.is_dir():
        jsonl_path = jsonl_path.with_suffix(".jsonl")
    elif jsonl_path.suffix != ".jsonl":
        jsonl_path = jsonl_path.with_suffix(".jsonl")
    if not jsonl_path.exists():
        print(f"错误: 文件不存在 {jsonl_path}")
        sys.exit(1)
    if output_path is None:
        output_path = jsonl_path.with_suffix(".html")

    with open(jsonl_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    messages = []
    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg_type = obj.get("type", "")
        if msg_type in ("user", "assistant"):
            msg = obj.get("message", {})
            messages.append({
                "type": msg_type,
                "role": msg.get("role", msg_type),
                "content": msg.get("content", ""),
                "timestamp": obj.get("timestamp", ""),
            })

    html_parts = []
    nav_parts = []
    turn_number = 0
    block_counter = 0
    msg_count = 0

    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        timestamp = msg.get("timestamp", "")
        ts_str = ""
        ts_short = ""
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                ts_short = dt.strftime("%H:%M")
            except Exception:
                ts_str = timestamp[:19]
                ts_short = ts_str[11:16] if len(ts_str) >= 16 else ""

        if role == "user":
            if isinstance(content, str) and content.strip():
                turn_number += 1
                block_counter += 1
                msg_count += 1
                block_id = f"turn-{turn_number}"
                html_parts.append(f'<div class="msg-block" id="{block_id}">')
                html_parts.append(f'<div class="msg-timestamp">{h(ts_str)}</div>')
                html_parts.append(f'<div class="msg-user"><span class="prompt-symbol">&#10095;</span> {h(content)}</div>')
                html_parts.append('</div>')
                summary = content.strip().replace('\n', ' ')[:50]
                nav_parts.append(f'<div class="nav-item" data-target="{block_id}"><span class="nav-num">#{turn_number}</span><span class="nav-time">{h(ts_short)}</span> {h(summary)}</div>')
            elif isinstance(content, list):
                has_text = False
                user_text = ""
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text" and block.get("text", "").strip():
                            if not has_text:
                                turn_number += 1
                                block_id = f"turn-{turn_number}"
                                html_parts.append(f'<div class="msg-block" id="{block_id}">')
                                html_parts.append(f'<div class="msg-timestamp">{h(ts_str)}</div>')
                                user_text = block["text"]
                                html_parts.append(f'<div class="msg-user"><span class="prompt-symbol">&#10095;</span> {h(block["text"])}</div>')
                                has_text = True
                                msg_count += 1
                            else:
                                html_parts.append(f'<div class="msg-user">{h(block["text"])}</div>')
                        elif block.get("type") == "tool_result":
                            result_html = format_tool_result_block(block)
                            if result_html:
                                html_parts.append(result_html)
                                msg_count += 1
                if has_text:
                    html_parts.append('</div>')
                    summary = user_text.strip().replace('\n', ' ')[:50]
                    nav_parts.append(f'<div class="nav-item" data-target="{block_id}"><span class="nav-num">#{turn_number}</span><span class="nav-time">{h(ts_short)}</span> {h(summary)}</div>')

        elif role == "assistant":
            if isinstance(content, list):
                claude_parts = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    block_type = block.get("type", "")
                    if block_type == "text":
                        text = block.get("text", "")
                        if text.strip():
                            rendered = render_markdown(text)
                            claude_parts.append(f'<div class="msg-claude"><div class="md-body">{rendered}</div></div>')
                            msg_count += 1
                    elif block_type == "thinking":
                        thinking_html = format_thinking_block(block)
                        if thinking_html:
                            claude_parts.append(thinking_html)
                            msg_count += 1
                    elif block_type == "tool_use":
                        tool_html = format_tool_use_block(block)
                        claude_parts.append(tool_html)
                        msg_count += 1
                if claude_parts:
                    block_counter += 1
                    html_parts.append(f'<div class="msg-block" id="msg-{block_counter}">')
                    html_parts.append(f'<div class="msg-timestamp">{h(ts_str)}</div>')
                    html_parts.extend(claude_parts)
                    html_parts.append('</div>')
            elif isinstance(content, str) and content.strip():
                block_counter += 1
                rendered = render_markdown(content)
                html_parts.append(f'<div class="msg-block" id="msg-{block_counter}">')
                html_parts.append(f'<div class="msg-timestamp">{h(ts_str)}</div>')
                html_parts.append(f'<div class="msg-claude"><div class="md-body">{rendered}</div></div>')
                html_parts.append('</div>')
                msg_count += 1

    chat_content = "\n".join(html_parts)
    nav_content = "\n".join(nav_parts)
    session_info = f"{jsonl_path.stem[:8]}... · {ts_str[:10] if ts_str else 'unknown'}"

    final_html = HTML_TEMPLATE
    final_html = final_html.replace("{title}", f"Claude Code 会话 — {ts_str[:10] if ts_str else ''}")
    final_html = final_html.replace("{chat_content}", chat_content)
    final_html = final_html.replace("{nav_items}", nav_content)
    final_html = final_html.replace("{session_info}", session_info)
    final_html = final_html.replace("{turn_count}", str(turn_number))
    final_html = final_html.replace("{msg_count}", str(msg_count))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    size_str = f"{len(final_html) / 1024:.1f}KB"
    print(f"导出完成: {output_path}")
    print(f"文件大小: {size_str} | {turn_number} 轮对话 | {msg_count} 条消息")


def interactive_mode():
    sessions = get_all_sessions()
    if not sessions:
        print("没有找到任何会话文件。")
        return
    list_sessions()
    print()
    try:
        choice = input("请输入序号选择要导出的会话 (直接回车退出): ").strip()
        if not choice:
            return
        idx = int(choice) - 1
        if 0 <= idx < len(sessions):
            path = sessions[idx][0]
            print(f"\n选择的会话: {path}")
            export_session(path)
        else:
            print("无效的序号。")
    except (ValueError, KeyboardInterrupt):
        print()


def main():
    if len(sys.argv) < 2:
        interactive_mode()
        return
    jsonl_path = sys.argv[1]
    if jsonl_path in ("-l", "--list"):
        list_sessions()
        return
    output_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else None
    export_session(jsonl_path, output_path)


if __name__ == "__main__":
    main()

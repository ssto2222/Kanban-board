'use strict';

let logsData  = [];
let logsReady = false;

// ── Entry point ───────────────────────────────────────────────────────────────

function initLogs() {
  if (!logsReady) {
    logsReady = true;
    bindLogsEvents();
  }
  fetchLogs();
}

// ── Events ────────────────────────────────────────────────────────────────────

function bindLogsEvents() {
  document.getElementById('logs-filter-action').addEventListener('change', renderLogs);
  document.getElementById('logs-filter-user').addEventListener('input',   renderLogs);
  document.getElementById('logs-refresh').addEventListener('click', fetchLogs);
}

// ── API ───────────────────────────────────────────────────────────────────────

async function fetchLogs() {
  const btn = document.getElementById('logs-refresh');
  if (btn) btn.disabled = true;
  try {
    const res = await fetch('/api/logs');
    if (res.status === 401) {
      document.getElementById('logs-empty').textContent = 'ログインが必要です';
      document.getElementById('logs-empty').style.display = 'block';
      document.getElementById('logs-list').innerHTML = '';
      return;
    }
    logsData = await res.json();
    renderLogs();
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── Render ────────────────────────────────────────────────────────────────────

const ACTION_META = {
  login:         { icon: '🔑', label: 'ログイン' },
  logout:        { icon: '👋', label: 'ログアウト' },
  task_create:   { icon: '➕', label: 'タスク作成' },
  task_update:   { icon: '✏️',  label: 'タスク更新' },
  task_move:     { icon: '📦', label: 'カード移動' },
  task_delete:   { icon: '🗑',  label: 'タスク削除' },
  task_reassign: { icon: '🔀', label: '担当者振り替え' },
  lift_create:   { icon: '➕', label: '高所作業車追加' },
  lift_update:   { icon: '✏️',  label: '高所作業車更新' },
  lift_move:     { icon: '🏗',  label: '高所作業車移動' },
  lift_delete:   { icon: '🗑',  label: '高所作業車削除' },
};

function renderLogs() {
  const filterAction = document.getElementById('logs-filter-action').value;
  const filterUser   = document.getElementById('logs-filter-user').value.trim().toLowerCase();

  const filtered = logsData.filter(l => {
    if (filterAction && l.action !== filterAction) return false;
    if (filterUser) {
      const name = (l.display_name + ' ' + l.username).toLowerCase();
      if (!name.includes(filterUser)) return false;
    }
    return true;
  });

  const list  = document.getElementById('logs-list');
  const empty = document.getElementById('logs-empty');
  document.getElementById('logs-count').textContent = filtered.length;

  if (!filtered.length) {
    list.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';
  list.innerHTML = '';
  for (const log of filtered) {
    list.appendChild(buildLogRow(log));
  }
}

function buildLogRow(log) {
  const meta = ACTION_META[log.action] || { icon: '📝', label: log.action };
  const row  = document.createElement('div');
  row.className = 'log-row';

  const ts    = new Date(log.ts);
  const tsStr = ts.toLocaleString('ja-JP', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    timeZone: 'Asia/Tokyo',
  });

  row.innerHTML = `
    <span class="log-ts">${tsStr}</span>
    <span class="log-actor">${logEsc(log.display_name || log.username || '匿名')}</span>
    <span class="log-action"><span class="log-icon">${meta.icon}</span>${meta.label}</span>
    <span class="log-detail">${logEsc(log.detail)}</span>
  `;
  return row;
}

function logEsc(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

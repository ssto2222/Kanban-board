'use strict';

// 寒色→暖色の4段階（赤・オレンジは期限切れ警告色として予約済みのため除外）
const STICKY_COLORS = [
  '#118AB2', // 寒色: ブルー
  '#4CC9F0', // 寒色寄り: ライトブルー
  '#06D6A0', // 暖色寄り: ティール
  '#FFD166', // 暖色: イエロー（デフォルト）
];

const COL_META = {
  todo: { label: '📋 待機中', bg: '#0f3460' },
  wip:  { label: '⚡ 進行中', bg: '#533483' },
  done: { label: '✅ 完了',   bg: '#1a6b3c' },
};

let tasks = [];
let draggedId = null;
let editingTask = null;
let currentView = 'kanban';

// ── 初期化 ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  buildSwatches('swatches', 'task-color');
  buildSwatches('nt-swatches', 'nt-color');
  bindEvents();
  loadTasks();
});

function buildSwatches(containerId, inputId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  // スウォッチをまとめるラッパー
  const wrapper = document.createElement('div');
  wrapper.className = 'color-swatches';
  for (const c of STICKY_COLORS) {
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = c;
    sw.title = c;
    sw.addEventListener('click', () => {
      document.getElementById(inputId).value = c;
    });
    wrapper.appendChild(sw);
  }
  container.appendChild(wrapper);
}

function bindEvents() {
  // ナビゲーション
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
  });

  // モーダルボタン
  document.getElementById('btn-cancel').addEventListener('click', closeModal);
  document.getElementById('btn-save').addEventListener('click', saveTask);
  document.getElementById('btn-delete').addEventListener('click', deleteTask);

  // モーダル背景クリックで閉じる
  document.getElementById('overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('overlay')) closeModal();
  });

  // キーボードショートカット
  document.addEventListener('keydown', (e) => {
    const overlay = document.getElementById('overlay');
    if (overlay.style.display !== 'flex') return;
    if (e.key === 'Escape') closeModal();
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') saveTask();
  });

  // 検索
  document.getElementById('search').addEventListener('input', () => {
    if (currentView === 'kanban') renderKanban();
    else if (currentView === 'assignee') renderAssignee();
  });

  // ドロップゾーン
  for (const col of ['todo', 'wip', 'done']) {
    const el = document.getElementById(`col-${col}`);
    el.addEventListener('dragover', (e) => {
      e.preventDefault();
      el.classList.add('highlight');
    });
    el.addEventListener('dragleave', (e) => {
      if (!el.contains(e.relatedTarget)) el.classList.remove('highlight');
    });
    el.addEventListener('drop', (e) => handleDrop(e, col));
  }

  // タイムラインコントロール
  document.querySelectorAll('input[name="tl-group"]').forEach(r => {
    r.addEventListener('change', renderTimeline);
  });
  document.getElementById('tl-span').addEventListener('change', renderTimeline);

  // 新規タスクフォーム
  document.getElementById('nt-is-milestone').addEventListener('change', toggleMilestone);
  document.getElementById('nt-assignee-select').addEventListener('change', () => {
    const val = document.getElementById('nt-assignee-select').value;
    if (val) document.getElementById('nt-assignee').value = val;
  });
  document.getElementById('nt-submit').addEventListener('click', submitNewTask);
}

// ── ビュー切り替え ────────────────────────────────────────────────────────────

function switchView(view) {
  currentView = view;

  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === view);
  });
  document.querySelectorAll('.view').forEach(v => {
    v.classList.toggle('active', v.id === `view-${view}`);
  });

  if (view === 'kanban')    renderKanban();
  else if (view === 'assignee')  renderAssignee();
  else if (view === 'timeline')  renderTimeline();
  else if (view === 'new_task')  initNewTaskForm();
}

// ── API ───────────────────────────────────────────────────────────────────────

async function loadTasks() {
  const res = await fetch('/api/tasks');
  tasks = await res.json();
  renderCurrentView();
}

function renderCurrentView() {
  if (currentView === 'kanban')   renderKanban();
  else if (currentView === 'assignee') renderAssignee();
  else if (currentView === 'timeline') renderTimeline();
}

async function apiPut(id, data) {
  const res = await fetch(`/api/tasks/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

async function apiPost(data) {
  const res = await fetch('/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

async function apiDelete(id) {
  await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
}

// ── カンバンビュー ────────────────────────────────────────────────────────────

function renderKanban() {
  const q = document.getElementById('search').value.toLowerCase();

  for (const col of ['todo', 'wip', 'done']) {
    const container = document.getElementById(`cards-${col}`);
    const filtered = tasks.filter(t =>
      t.column === col &&
      (!q || t.title.toLowerCase().includes(q) || (t.assignee || '').toLowerCase().includes(q))
    );

    container.innerHTML = '';
    for (const task of filtered) {
      container.appendChild(createCard(task, true));
    }
    document.getElementById(`count-${col}`).textContent = filtered.length;
  }
}

function createCard(task, draggable = false) {
  const card = document.createElement('div');
  card.className = 'card';
  card.draggable = draggable;
  card.dataset.id = task.id;

  const displayColor = getPriorityColor(task.deadline, task.color);
  card.style.background = displayColor;

  const topBg = darken(displayColor, 0.2);
  const deadlineHtml = buildDeadlineHtml(task.deadline);

  card.innerHTML = `
    <div class="card-top" style="background:${topBg}">
      <span class="card-title">${esc(task.title)}</span>
      <button class="card-edit-btn" title="編集">✏️</button>
    </div>
    <div class="card-body">
      ${task.assignee ? `<div class="card-assignee">👤 ${esc(task.assignee)}</div>` : ''}
      ${deadlineHtml}
      ${task.note ? `<div class="card-note">${esc(task.note)}</div>` : ''}
    </div>
  `;

  if (draggable) {
    card.addEventListener('dragstart', (e) => {
      draggedId = task.id;
      e.dataTransfer.effectAllowed = 'move';
      setTimeout(() => card.classList.add('dragging'), 0);
    });
    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
      draggedId = null;
      document.querySelectorAll('.column').forEach(c => c.classList.remove('highlight'));
    });
  }

  card.querySelector('.card-edit-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    openEditModal(task);
  });
  card.addEventListener('click', () => openEditModal(task));

  return card;
}

function buildDeadlineHtml(deadline) {
  if (!deadline) return '';
  const days = daysRemaining(deadline);
  let cls = 'dl-ok';
  let extra = '';

  if (days === null)    { cls = ''; }
  else if (days < 0)   { cls = 'dl-overdue'; extra = ` (期限切れ ${Math.abs(days)}日)`; }
  else if (days === 0) { cls = 'dl-warn';    extra = ' (本日期限!)'; }
  else if (days <= 3)  { cls = 'dl-warn';    extra = ` (残り${days}日)`; }
  else                 { extra = ` (残り${days}日)`; }

  return `<div class="card-deadline ${cls}">📅 ${esc(deadline)}${extra}</div>`;
}

// ── ドラッグ＆ドロップ ────────────────────────────────────────────────────────

async function handleDrop(e, targetCol) {
  e.preventDefault();
  document.querySelectorAll('.column').forEach(c => c.classList.remove('highlight'));

  if (!draggedId) return;
  const task = tasks.find(t => t.id === draggedId);
  if (!task || task.column === targetCol) return;

  task.column = targetCol;
  renderKanban();

  await apiPut(draggedId, task);
  draggedId = null;
}

// ── 担当者別ビュー ────────────────────────────────────────────────────────────

function renderAssignee() {
  const q = document.getElementById('search').value.toLowerCase();
  const filtered = q
    ? tasks.filter(t => t.title.toLowerCase().includes(q) || (t.assignee || '').toLowerCase().includes(q))
    : tasks;

  const UNASSIGNED = '（未割り当て）';
  const groups = {};
  for (const t of filtered) {
    const key = t.assignee || UNASSIGNED;
    groups[key] = groups[key] || [];
    groups[key].push(t);
  }

  const order = Object.keys(groups).sort((a, b) => {
    if (a === UNASSIGNED) return 1;
    if (b === UNASSIGNED) return -1;
    return a.localeCompare(b, 'ja');
  });

  const container = document.getElementById('assignee-content');
  container.innerHTML = '';

  for (const name of order) {
    const memberTasks = groups[name];
    const counts = { todo: 0, wip: 0, done: 0 };
    for (const t of memberTasks) counts[t.column] = (counts[t.column] || 0) + 1;

    const section = document.createElement('div');
    section.className = 'assignee-section';

    const icon = name === UNASSIGNED ? '❓' : '👤';
    section.innerHTML = `
      <div class="assignee-hdr">
        <span>${icon}&nbsp;${esc(name)}</span>
        <span class="assignee-count">
          計&nbsp;${memberTasks.length}&nbsp;件&nbsp;｜&nbsp;
          待機&nbsp;${counts.todo}&nbsp;
          進行&nbsp;${counts.wip}&nbsp;
          完了&nbsp;${counts.done}
        </span>
      </div>
      <div class="assignee-cols">
        ${['todo', 'wip', 'done'].map(col => `
          <div class="assignee-col">
            <div class="status-label">${COL_META[col].label} (${counts[col] || 0})</div>
            <div class="assignee-cards" id="ac-${esc(name)}-${col}"></div>
          </div>
        `).join('')}
      </div>
      <hr class="divider-line">
    `;

    container.appendChild(section);

    for (const col of ['todo', 'wip', 'done']) {
      const cardContainer = section.querySelector(`[id="ac-${esc(name)}-${col}"]`);
      for (const task of memberTasks.filter(t => t.column === col)) {
        cardContainer.appendChild(createCard(task, false));
      }
    }
  }
}

// ── タイムラインビュー ────────────────────────────────────────────────────────

function renderTimeline() {
  const groupBy = document.querySelector('input[name="tl-group"]:checked').value;
  const span    = document.getElementById('tl-span').value;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // バー用データ構築
  const rows = [];
  for (const t of tasks) {
    let start   = t.started_at  ? new Date(t.started_at)  : null;
    let end     = t.finished_at ? new Date(t.finished_at) : null;
    const dl    = t.deadline    ? new Date(t.deadline)     : null;

    if (!start && !dl) continue;

    if (!start) { start = new Date(dl); start.setDate(start.getDate() - 7); }
    if (!end)   { end   = new Date(start); end.setHours(end.getHours() + 23); }

    const group = groupBy === 'assignee'
      ? (t.assignee || '未設定')
      : (COL_META[t.column]?.label || '不明');

    rows.push({ title: t.title, start, end, group, color: getPriorityColor(t.deadline, t.color) });
  }

  const container = document.getElementById('timeline-content');
  if (!rows.length) {
    container.innerHTML = '<div class="tl-empty">表示可能なタスクがありません。<br>期限または作業期間を設定してください。</div>';
    return;
  }

  // 表示範囲
  const minDt   = new Date(Math.min(...rows.map(r => r.start.getTime()), today.getTime()) - 2 * 86400000);
  const maxDt   = new Date(Math.max(...rows.map(r => r.end.getTime()),   today.getTime()) + 7 * 86400000);
  const totalMs = maxDt - minDt;
  const getPct  = dt => (dt - minDt) / totalMs * 100;

  // 目盛り生成
  const WD   = ['月','火','水','木','金','土','日'];
  const ticks = [];
  const curr  = new Date(minDt);
  curr.setHours(0, 0, 0, 0);

  while (curr <= maxDt) {
    const p  = getPct(curr);
    if (p >= 0 && p <= 100) {
      const wd  = WD[curr.getDay() === 0 ? 6 : curr.getDay() - 1];
      const mm  = String(curr.getMonth() + 1).padStart(2, '0');
      const dd  = String(curr.getDate()).padStart(2, '0');
      let label = span === 'daily' ? `${mm}/${dd}<br>${wd}` : `${mm}/${dd}`;
      let cls   = span === 'daily' && curr.getDay() === 6 ? 'sat'
                : span === 'daily' && curr.getDay() === 0 ? 'sun' : '';
      ticks.push({ p, label, cls });
    }
    if (span === 'daily')   curr.setDate(curr.getDate() + 1);
    else if (span === 'weekly') curr.setDate(curr.getDate() + 7);
    else                    curr.setDate(curr.getDate() + 30);
  }

  // グループ化
  const groupMap = {};
  for (const r of rows) {
    groupMap[r.group] = groupMap[r.group] || [];
    groupMap[r.group].push(r);
  }

  // HTML 構築
  const LANE_H  = 36;  // 1タスクあたりの行高さ(px)
  const BAR_H   = 22;  // バーの高さ(px)
  const BAR_PAD = (LANE_H - BAR_H) / 2;  // レーン内の上余白

  let h = '<div class="tl-wrap">';

  // 軸行
  h += '<div class="tl-axis-row"><div class="tl-group-col"></div><div class="tl-chart-col">';
  for (const { p, label, cls } of ticks) {
    h += `<div class="tl-tick ${cls}" style="left:${p.toFixed(2)}%">${label}</div>`;
  }
  h += '</div></div>';

  // データ行（グループごとにレーン数分の高さを確保して重なりを防止）
  const todayPct = getPct(today);
  for (const grp of Object.keys(groupMap).sort()) {
    const bars  = groupMap[grp];
    const rowH  = bars.length * LANE_H + 8;  // 上下余白 4px ずつ

    h += `<div class="tl-row" style="height:${rowH}px">`;
    h += `<div class="tl-group-name" style="height:${rowH}px">${esc(grp)}</div>`;
    h += `<div class="tl-chart-area" style="height:${rowH}px">`;

    for (const { p } of ticks) {
      h += `<div class="tl-gridline" style="left:${p.toFixed(2)}%"></div>`;
    }
    if (todayPct >= 0 && todayPct <= 100) {
      h += `<div class="tl-today-line" style="left:${todayPct.toFixed(2)}%"></div>`;
    }

    // 各バーを専用レーンに配置（インデックス順に縦に並べる）
    bars.forEach((r, i) => {
      const barTop = 4 + i * LANE_H + BAR_PAD;
      const left   = getPct(r.start);
      const width  = Math.max(getPct(r.end) - left, 1.5);
      h += `<div class="tl-bar-outer" style="left:${left.toFixed(2)}%;width:${width.toFixed(2)}%;top:${barTop}px;height:${BAR_H}px">`;
      h += `<div class="tl-bar-fill" style="background:${r.color}">`;
      h += `<span class="tl-bar-name">${esc(r.title)}</span>`;
      h += '</div></div>';
    });

    h += '</div></div>';
  }
  h += '</div>';

  container.innerHTML = h;
}

// ── 新規タスクフォーム ────────────────────────────────────────────────────────

async function initNewTaskForm() {
  // 今日の日付をデフォルト設定
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('nt-deadline').value = today;

  // 既存担当者リスト取得
  try {
    const res = await fetch('/api/assignees');
    const assignees = await res.json();
    const sel = document.getElementById('nt-assignee-select');
    sel.innerHTML = '<option value="">(新規入力)</option>';
    for (const a of assignees) {
      const opt = document.createElement('option');
      opt.value = a;
      opt.textContent = a;
      sel.appendChild(opt);
    }
  } catch (_) { /* ignore */ }
}

function toggleMilestone() {
  const isMilestone = document.getElementById('nt-is-milestone').checked;
  document.getElementById('nt-milestone-info').style.display  = isMilestone ? 'block' : 'none';
  document.getElementById('nt-period-section').style.display  = isMilestone ? 'none'  : 'block';
  document.getElementById('nt-color').value = isMilestone ? '#E94560' : '#FFD166';
}

async function submitNewTask() {
  const title = document.getElementById('nt-title').value.trim();
  if (!title) {
    alert('項目名を入力してください');
    document.getElementById('nt-title').focus();
    return;
  }

  const isMilestone = document.getElementById('nt-is-milestone').checked;
  const note        = document.getElementById('nt-note').value.trim();

  const data = {
    title:       isMilestone ? `🔷 ${title}` : title,
    assignee:    document.getElementById('nt-assignee').value.trim(),
    deadline:    document.getElementById('nt-deadline').value,
    column:      document.getElementById('nt-status').value,
    note:        isMilestone ? `[MS] ${note}` : note,
    color:       document.getElementById('nt-color').value,
    started_at:  isMilestone ? '' : document.getElementById('nt-started-at').value,
    finished_at: isMilestone ? '' : document.getElementById('nt-finished-at').value,
  };

  const created = await apiPost(data);
  tasks.push(created);

  // フォームリセット
  document.getElementById('nt-title').value       = '';
  document.getElementById('nt-note').value        = '';
  document.getElementById('nt-assignee').value    = '';
  document.getElementById('nt-started-at').value  = '';
  document.getElementById('nt-finished-at').value = '';
  document.getElementById('nt-is-milestone').checked = false;
  document.getElementById('nt-color').value = '#FFD166';
  toggleMilestone();

  // カンバンに移動
  switchView('kanban');
}

// ── モーダル ─────────────────────────────────────────────────────────────────

function openEditModal(task) {
  editingTask = task;
  document.getElementById('modal-title').textContent      = 'タスク編集';
  document.getElementById('task-id').value                = task.id;
  document.getElementById('task-title').value             = task.title     || '';
  document.getElementById('task-assignee').value          = task.assignee  || '';
  document.getElementById('task-deadline').value          = task.deadline  || '';
  document.getElementById('task-note').value              = task.note      || '';
  document.getElementById('task-color').value             = task.color     || '#FFD166';
  document.getElementById('task-column').value            = task.column    || 'todo';
  document.getElementById('btn-delete').style.display     = 'inline-block';
  showModal();
}

function showModal() {
  document.getElementById('overlay').style.display = 'flex';
  document.getElementById('task-title').focus();
}

function closeModal() {
  document.getElementById('overlay').style.display = 'none';
  editingTask = null;
}

async function saveTask() {
  const title = document.getElementById('task-title').value.trim();
  if (!title) {
    alert('タスク名を入力してください');
    document.getElementById('task-title').focus();
    return;
  }

  const data = {
    title,
    assignee: document.getElementById('task-assignee').value.trim(),
    deadline: document.getElementById('task-deadline').value,
    note:     document.getElementById('task-note').value.trim(),
    color:    document.getElementById('task-color').value,
    column:   document.getElementById('task-column').value,
  };

  if (editingTask) {
    Object.assign(editingTask, data);
    renderCurrentView();
    await apiPut(editingTask.id, data);
  }

  closeModal();
}

async function deleteTask() {
  if (!editingTask) return;
  if (!confirm('このタスクを削除しますか？')) return;

  const id = editingTask.id;
  tasks = tasks.filter(t => t.id !== id);
  renderCurrentView();
  closeModal();

  await apiDelete(id);
}

// ── ヘルパー ──────────────────────────────────────────────────────────────────

function getPriorityColor(deadline, color) {
  if (!deadline) return color || '#FFD166';
  const days = daysRemaining(deadline);
  if (days === null)  return color || '#FFD166';
  if (days < 0)       return '#EF476F';
  if (days <= 2)      return '#FFB347';
  return color || '#FFD166';
}

function darken(hex, factor) {
  if (!hex || hex.length < 7) return hex;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const d = v => Math.round(v * (1 - factor)).toString(16).padStart(2, '0');
  return `#${d(r)}${d(g)}${d(b)}`;
}

function daysRemaining(deadlineStr) {
  if (!deadlineStr) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dl = new Date(deadlineStr);
  return Math.round((dl - today) / 86400000);
}

function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

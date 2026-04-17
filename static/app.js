'use strict';

// 寒色→暖色の4段階（赤・オレンジは期限切れ警告色として予約済みのため除外）
const STICKY_COLORS = [
  '#118AB2', // 寒色: ブルー
  '#4CC9F0', // 寒色寄り: ライトブルー
  '#06D6A0', // 暖色寄り: ティール
  '#9842f5', // 紫
  '#f2c2ed', // ピンク
  '#FFD166', // 暖色: イエロー（デフォルト）
];

const COL_META = {
  todo: { label: '📋 待機中', bg: '#0f3460' },
  wip:  { label: '⚡ 進行中', bg: '#533483' },
  done: { label: '✅ 完了',   bg: '#1a6b3c' },
};

const UNASSIGNED = '（未割り当て）';  // 担当者なしの表示ラベル

let tasks = [];
let draggedId  = null;
let editingTask = null;
let currentView = 'assignee';
let tlLastClick = null;  // タイムラインのダブルクリック検出用 { taskId, time }
let cardDrag   = null;   // カードのPointer Events DnD用 { taskId, card, ghost, startX, startY, moved }
let _scrollY   = 0;      // スクロールロック用保存値

// タイムラインのドラッグ操作用モジュール変数
let tlMinDt   = null;   // 現在の表示ウィンドウ開始日時
let tlTotalMs = null;   // 表示ウィンドウの総ミリ秒
let tlDrag    = null;   // ドラッグ中の状態オブジェクト

// ── 初期化 ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  buildSwatches('swatches', 'task-color');
  buildSwatches('nt-swatches', 'nt-color');
  bindEvents();
  // 担当者フィールドのユーザーオートコンプリート
  initUserAutocomplete(
    document.getElementById('nt-assignee'),
    document.getElementById('nt-assignee-dropdown')
  );
  initUserAutocomplete(
    document.getElementById('task-assignee'),
    document.getElementById('task-assignee-dropdown')
  );
  // URLパラメータ ?view=xxx で初期ビューを上書き
  const urlView = new URLSearchParams(location.search).get('view');
  if (urlView) {
    currentView = urlView;
    history.replaceState(null, '', location.pathname);  // URLをクリーン
  }
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
  // ナビゲーション（モバイルではサイドバーも閉じる）
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => { switchView(btn.dataset.view); closeSidebar(); });
  });

  // ハンバーガーメニュー（モバイル）
  document.getElementById('hamburger')?.addEventListener('click', openSidebar);
  document.getElementById('sidebar-close')?.addEventListener('click', closeSidebar);
  document.getElementById('sidebar-backdrop')?.addEventListener('click', closeSidebar);

  // モーダルボタン
  document.getElementById('btn-cancel').addEventListener('click', closeModal);
  document.getElementById('btn-save').addEventListener('click', saveTask);
  // 削除: confirm()の代わりにインライン確認UIを表示
  document.getElementById('btn-delete').addEventListener('click', () => {
    document.getElementById('modal-btns').style.display        = 'none';
    document.getElementById('delete-confirm-row').style.display = 'flex';
  });
  document.getElementById('btn-delete-cancel').addEventListener('click', () => {
    document.getElementById('delete-confirm-row').style.display = 'none';
    document.getElementById('modal-btns').style.display        = 'flex';
  });
  document.getElementById('btn-delete-confirm').addEventListener('click', deleteTask);

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

  // カード DnD (Pointer Events — マウス・タッチ・ペン共通)
  document.addEventListener('pointermove', onCardPointerMove);
  document.addEventListener('pointerup',   onCardPointerUp);

  // タイムラインコントロール
  document.querySelectorAll('input[name="tl-group"]').forEach(r => {
    r.addEventListener('change', renderTimeline);
  });
  document.getElementById('tl-span').addEventListener('change', renderTimeline);

  // 期限変更時: カード色を自動更新 + 終了日(finished_at)を同期
  document.getElementById('task-deadline').addEventListener('change', () => {
    const deadline = document.getElementById('task-deadline').value;
    if (!deadline) return;
    const days = daysRemaining(deadline);
    if (days < 0)       document.getElementById('task-color').value = '#EF476F';
    else if (days <= 2) document.getElementById('task-color').value = '#FFB347';
    // 終了日を期限日 23:59 に合わせる
    document.getElementById('task-finished-at').value = `${deadline}T23:59`;
  });

  // 終了日変更時: 期限を同期
  document.getElementById('task-finished-at').addEventListener('change', () => {
    const fin = document.getElementById('task-finished-at').value;
    if (!fin) return;
    const dateOnly = fin.split('T')[0];
    document.getElementById('task-deadline').value = dateOnly;
    const days = daysRemaining(dateOnly);
    if (days < 0)       document.getElementById('task-color').value = '#EF476F';
    else if (days <= 2) document.getElementById('task-color').value = '#FFB347';
  });

  // 新規タスクフォーム: 期限 ↔ 終了日の同期
  document.getElementById('nt-deadline').addEventListener('change', () => {
    const dl = document.getElementById('nt-deadline').value;
    if (dl) document.getElementById('nt-finished-at').value = `${dl}T23:59`;
  });
  document.getElementById('nt-finished-at').addEventListener('change', () => {
    const fin = document.getElementById('nt-finished-at').value;
    if (fin) document.getElementById('nt-deadline').value = fin.split('T')[0];
  });

  // タイムラインのバーのドラッグ・リサイズ（イベント委譲）
  document.getElementById('timeline-content').addEventListener('pointerdown', onTlPointerDown);
  document.addEventListener('pointermove',   onTlPointerMove);
  document.addEventListener('pointerup',     onTlPointerUp);
  // pointercancel: iOSがスクロール等でタッチをキャンセルした際のゴーストを確実に削除
  document.addEventListener('pointercancel', onCardPointerUp);

  // 新規タスクフォーム
  document.getElementById('nt-is-milestone').addEventListener('change', toggleMilestone);
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
  else if (view === 'mytasks')   renderMyTasks();
  else if (view === 'manage')    renderManage();
  else if (view === 'new_task')  initNewTaskForm();
}

// ── API ───────────────────────────────────────────────────────────────────────

async function loadTasks() {
  const res = await fetch('/api/tasks');
  tasks = await res.json();
  switchView(currentView);  // アクティブビューを確定してから描画
}

function renderCurrentView() {
  if (currentView === 'kanban')    renderKanban();
  else if (currentView === 'assignee')  renderAssignee();
  else if (currentView === 'timeline')  renderTimeline();
  else if (currentView === 'mytasks')   renderMyTasks();
  else if (currentView === 'manage')    renderManage();
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

  // ── マイルストーンセクション（完了除く） ──
  const milestones = tasks.filter(t =>
    isMsTask(t) && t.column !== 'done' &&
    (!q || t.title.toLowerCase().includes(q) || (t.assignee || '').toLowerCase().includes(q))
  ).sort((a, b) => (a.deadline || '9999') < (b.deadline || '9999') ? -1 : 1);

  const msSection = document.getElementById('kanban-milestone-section');
  const msCards   = document.getElementById('cards-milestone');
  document.getElementById('count-milestone').textContent = milestones.length;
  msCards.innerHTML = '';
  for (const task of milestones) msCards.appendChild(createCard(task, true));
  msSection.style.display = milestones.length ? '' : 'none';

  // ── 通常カラム（マイルストーンを除外） ──
  for (const col of ['todo', 'wip', 'done']) {
    const container = document.getElementById(`cards-${col}`);
    const filtered = tasks.filter(t =>
      t.column === col &&
      !isMsTask(t) &&
      (!q || t.title.toLowerCase().includes(q) || (t.assignee || '').toLowerCase().includes(q))
    );
    container.innerHTML = '';
    for (const task of filtered) container.appendChild(createCard(task, true));
    document.getElementById(`count-${col}`).textContent = filtered.length;
  }
}

function createCard(task, draggable = false) {
  const card = document.createElement('div');
  card.className = 'card';
  if (draggable) card.dataset.draggable = 'true';  // CSS touch-action: none のトリガーにも使用
  card.dataset.id = task.id;

  const displayColor = task.column === 'done'
    ? '#8a8a9a'
    : getPriorityColor(task.deadline, task.color);
  card.style.background = displayColor;

  const topBg = darken(displayColor, 0.2);
  const deadlineHtml = buildDeadlineHtml(task.deadline);

  card.innerHTML = `
    <div class="card-top" style="background:${topBg}">
      ${draggable ? '<span class="drag-handle" title="ドラッグして移動">⠿</span>' : ''}
      <span class="card-title">${esc(task.title)}</span>
      <button class="card-copy-btn" title="コピー">📋</button>
      <button class="card-edit-btn" title="編集">✏️</button>
    </div>
    <div class="card-body">
      ${task.assignee ? `<div class="card-assignee">👤 ${esc(task.assignee)}</div>` : ''}
      ${deadlineHtml}
      ${task.note ? `<div class="card-note">${esc(task.note)}</div>` : ''}
    </div>
  `;

  if (draggable) {
    // ハンドルにのみ pointerdown を付ける → カード本体はスクロール可
    card.querySelector('.drag-handle')
        .addEventListener('pointerdown', (e) => onCardPointerDown(e, task, card));
  }

  card.querySelector('.card-copy-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    copyTask(task);
  });
  card.querySelector('.card-edit-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    openEditModal(task);
  });
  // ダブルクリック（デスクトップ）
  card.addEventListener('dblclick', (e) => {
    if (!e.target.closest('.card-edit-btn')) openEditModal(task);
  });
  // ダブルタップ（タブレット）
  let _lastTap = 0;
  card.addEventListener('touchend', (e) => {
    const now = Date.now();
    if (now - _lastTap < 300 && !e.target.closest('.card-edit-btn')) {
      e.preventDefault();
      openEditModal(task);
    }
    _lastTap = now;
  });

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

async function handleDrop(targetCol) {
  document.querySelectorAll('.column').forEach(c => c.classList.remove('highlight'));

  if (!draggedId) return;
  const task = tasks.find(t => t.id === draggedId);
  if (!task || task.column === targetCol) { draggedId = null; return; }

  task.column = targetCol;
  draggedId = null;
  renderKanban();
  await apiPut(task.id, task);
}

// ── 担当者別ビュー ────────────────────────────────────────────────────────────

function renderAssignee() {
  const q = document.getElementById('search').value.toLowerCase();
  const filtered = q
    ? tasks.filter(t => t.title.toLowerCase().includes(q) || (t.assignee || '').toLowerCase().includes(q))
    : tasks;

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

    // ── ヘッダー ──
    const hdr = document.createElement('div');
    hdr.className = 'assignee-hdr';
    hdr.innerHTML = `
      <span>${name === UNASSIGNED ? '❓' : '👤'}&nbsp;${esc(name)}</span>
      <span class="assignee-count">
        計&nbsp;${memberTasks.length}&nbsp;件&nbsp;｜&nbsp;
        待機&nbsp;${counts.todo}&nbsp;
        進行&nbsp;${counts.wip}&nbsp;
        完了&nbsp;${counts.done}
      </span>`;
    section.appendChild(hdr);

    // ── 3ステータス列（ドロップゾーンつき） ──
    const colsDiv = document.createElement('div');
    colsDiv.className = 'assignee-cols';

    for (const col of ['todo', 'wip', 'done']) {
      const colDiv = document.createElement('div');
      colDiv.className = 'assignee-col';

      const lbl = document.createElement('div');
      lbl.className = 'status-label';
      lbl.textContent = `${COL_META[col].label} (${counts[col] || 0})`;
      colDiv.appendChild(lbl);

      const cardsDiv = document.createElement('div');
      cardsDiv.className = 'assignee-cards';
      cardsDiv.dataset.assignee = name;   // UNASSIGNED 文字列もそのまま格納
      cardsDiv.dataset.col      = col;

      // ドロップゾーンのハイライトはPointer Events DnDで制御（HTML5 DnD不使用）

      // カードを追加（ドラッグ有効）、3件超は折りたたむ
      const SHOW_LIMIT = 3;
      const colTasks = memberTasks.filter(t => t.column === col);
      colTasks.forEach((task, i) => {
        const card = createCard(task, true);
        if (i >= SHOW_LIMIT) card.classList.add('card-collapsed');
        cardsDiv.appendChild(card);
      });

      colDiv.appendChild(cardsDiv);

      const extra = colTasks.length - SHOW_LIMIT;
      if (extra > 0) {
        const btn = document.createElement('button');
        btn.className = 'cards-show-more';
        btn.textContent = `▼ もっと見る（${extra}件）`;
        btn.addEventListener('click', () => {
          const isCollapsed = !!cardsDiv.querySelector('.card-collapsed');
          if (isCollapsed) {
            cardsDiv.querySelectorAll('.card-collapsed').forEach(c => c.classList.remove('card-collapsed'));
            btn.textContent = '▲ 閉じる';
          } else {
            Array.from(cardsDiv.children).slice(SHOW_LIMIT).forEach(c => c.classList.add('card-collapsed'));
            btn.textContent = `▼ もっと見る（${extra}件）`;
          }
        });
        colDiv.appendChild(btn);
      }

      colsDiv.appendChild(colDiv);
    }

    section.appendChild(colsDiv);

    const hr = document.createElement('hr');
    hr.className = 'divider-line';
    section.appendChild(hr);

    container.appendChild(section);
  }
}

async function handleAssigneeDrop(target) {
  document.querySelectorAll('.assignee-cards').forEach(c => c.classList.remove('highlight'));

  if (!draggedId) return;
  const task = tasks.find(t => t.id === draggedId);
  if (!task) { draggedId = null; return; }

  // UNASSIGNED ラベルは DB 上は空文字として扱う
  const newAssignee = target.dataset.assignee === UNASSIGNED ? '' : target.dataset.assignee;
  const newCol      = target.dataset.col;

  if ((task.assignee || '') === newAssignee && task.column === newCol) {
    draggedId = null;
    return;
  }

  // 変更フィールドのみ更新
  const updates = {};
  if (task.column !== newCol)                updates.column   = newCol;
  if ((task.assignee || '') !== newAssignee) updates.assignee = newAssignee;

  Object.assign(task, updates);
  draggedId = null;

  renderAssignee();            // 楽観的 UI 更新
  await apiPut(task.id, updates);  // DB 書き込み
}

// ── サイドバー開閉 (モバイル) ──────────────────────────────────────────────────

// ── スクロールロック (iOS Safari 対応) ────────────────────────────────────────

function lockBodyScroll() {
  _scrollY = window.scrollY;
  document.body.style.overflow = 'hidden';
  document.body.style.position = 'fixed';
  document.body.style.top      = `-${_scrollY}px`;
  document.body.style.width    = '100%';
}

function unlockBodyScroll() {
  document.body.style.overflow = '';
  document.body.style.position = '';
  document.body.style.top      = '';
  document.body.style.width    = '';
  window.scrollTo(0, _scrollY);
}

// ── サイドバー開閉 (モバイル) ──────────────────────────────────────────────────

function openSidebar() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('sidebar-backdrop').classList.add('open');
  lockBodyScroll();
}

function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebar-backdrop').classList.remove('open');
  unlockBodyScroll();
}

// ── カード DnD (Pointer Events) ───────────────────────────────────────────────

function onCardPointerDown(e, task, card) {
  if (e.button === 2) return;  // 右クリック除外

  cardDrag = {
    taskId: task.id,
    card,
    ghost: null,
    startX: e.clientX,
    startY: e.clientY,
    moved: false,
  };
  // setPointerCapture でポインターが要素外に出ても追跡
  card.setPointerCapture(e.pointerId);
}

function onCardPointerMove(e) {
  if (!cardDrag) return;

  const dx = e.clientX - cardDrag.startX;
  const dy = e.clientY - cardDrag.startY;

  if (!cardDrag.moved && Math.hypot(dx, dy) > 8) {
    // ドラッグ開始
    cardDrag.moved = true;
    draggedId = cardDrag.taskId;
    cardDrag.card.classList.add('dragging');

    // ゴーストを生成
    const ghost = cardDrag.card.cloneNode(true);
    ghost.classList.add('card-ghost');
    ghost.style.width = `${cardDrag.card.offsetWidth}px`;
    // data-draggable を除いてポインターイベントが来ないようにする
    ghost.removeAttribute('data-draggable');
    document.body.appendChild(ghost);
    cardDrag.ghost = ghost;
  }

  if (!cardDrag.moved) return;
  if (e.cancelable) e.preventDefault();  // スクロール防止

  // ゴーストを追従させる
  const gh = cardDrag.ghost;
  if (gh) {
    gh.style.left = `${e.clientX - gh.offsetWidth / 2}px`;
    gh.style.top  = `${e.clientY - gh.offsetHeight / 2}px`;

    // ドロップ候補をハイライト（display:none で一時退避してから elementFromPoint）
    gh.style.display = 'none';
    const el = document.elementFromPoint(e.clientX, e.clientY);
    gh.style.display = '';

    document.querySelectorAll('.column[data-col], .assignee-cards[data-col]')
      .forEach(c => c.classList.remove('highlight'));
    const tgt = el?.closest('.column[data-col]') ?? el?.closest('.assignee-cards[data-col]');
    if (tgt) tgt.classList.add('highlight');
  }
}

async function onCardPointerUp(e) {
  if (!cardDrag) return;

  const { card, ghost, moved } = cardDrag;
  cardDrag = null;

  card.classList.remove('dragging');
  document.querySelectorAll('.column, .assignee-cards').forEach(c => c.classList.remove('highlight'));

  if (!moved) {
    if (ghost) ghost.remove();
    draggedId = null;
    return;
  }

  // ゴーストを display:none にしてドロップ先を特定（visibility:hidden は一部WebKitで不十分）
  let dropEl = null;
  if (ghost) {
    ghost.style.display = 'none';
    dropEl = document.elementFromPoint(e.clientX, e.clientY);
    ghost.remove();
  } else {
    dropEl = document.elementFromPoint(e.clientX, e.clientY);
  }

  const colTarget      = dropEl?.closest('.column[data-col]');
  const assigneeTarget = dropEl?.closest('.assignee-cards[data-col]');

  if (colTarget)      await handleDrop(colTarget.dataset.col);
  else if (assigneeTarget) await handleAssigneeDrop(assigneeTarget);
  else draggedId = null;
}

// ── タイムラインビュー ────────────────────────────────────────────────────────

function renderTimeline() {
  const groupBy = document.querySelector('input[name="tl-group"]:checked').value;
  const span    = document.getElementById('tl-span').value;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // バー用データ構築
  const MS_GROUP = '🔷 マイルストーン';
  const rows = [];
  for (const t of tasks) {
    if (t.column === 'done') continue;  // 完了タスクはタイムラインに表示しない

    const isMs = isMsTask(t);
    let start, end;

    if (isMs) {
      // マイルストーン: 期限日のみ（バーではなくひし形を表示）
      const dl = t.deadline ? new Date(t.deadline) : null;
      if (!dl) continue;
      start = dl;
      end   = new Date(dl.getTime() + 86400000);  // ウィンドウ境界チェック用に+1日
    } else {
      start = t.started_at  ? new Date(t.started_at)  : null;
      end   = t.finished_at ? new Date(t.finished_at) : null;
      const dl = t.deadline ? new Date(t.deadline) : null;
      if (!start && !dl) continue;
      if (!start) { start = new Date(dl); start.setDate(start.getDate() - 7); }
      if (!end)   { end   = new Date(start); end.setHours(end.getHours() + 23); }
    }

    const group = isMs
      ? MS_GROUP
      : (groupBy === 'assignee' ? (t.assignee || '未設定') : (COL_META[t.column]?.label || '不明'));

    const color = isMs
      ? (t.color || '#E94560')
      : getPriorityColor(t.deadline, t.color);

    rows.push({ id: t.id, title: t.title, start, end, group, color, isMs });
  }

  const container = document.getElementById('timeline-content');
  if (!rows.length) {
    container.innerHTML = '<div class="tl-empty">表示可能なタスクがありません。<br>期限または作業期間を設定してください。</div>';
    return;
  }

  // ── スパン別の表示ウィンドウ・目盛り間隔 ──
  const SPAN_CONFIG = {
    '2w': { before:  2, after:  14, step:  1, showDow: true  },  // 2週間・日次
    '2m': { before:  7, after:  60, step:  7, showDow: false },  // 2ヶ月・週次
    '6m': { before: 14, after: 180, step: 14, showDow: false },  // 半年・隔週
    '1y': { before: 30, after: 365, step: 30, showDow: false },  // 1年・月次
  };
  const cfg = SPAN_CONFIG[span] || SPAN_CONFIG['2m'];

  const DAY = 86400000;
  const minDt   = new Date(today.getTime() - cfg.before * DAY);
  const maxDt   = new Date(today.getTime() + cfg.after  * DAY);
  const totalMs = maxDt - minDt;
  const getPct  = dt => (dt - minDt) / totalMs * 100;

  // ドラッグハンドラから参照できるようモジュール変数を更新
  tlMinDt   = minDt;
  tlTotalMs = totalMs;

  // ── 目盛り生成（ウィンドウ内のみ） ──
  const WD    = ['月','火','水','木','金','土','日'];
  const ticks = [];
  const curr  = new Date(minDt);
  curr.setHours(0, 0, 0, 0);

  while (curr <= maxDt) {
    const p  = getPct(curr);
    if (p >= 0 && p <= 100) {
      const wd  = WD[curr.getDay() === 0 ? 6 : curr.getDay() - 1];
      const mm  = String(curr.getMonth() + 1).padStart(2, '0');
      const dd  = String(curr.getDate()).padStart(2, '0');
      const label = cfg.showDow ? `${mm}/${dd}<br>${wd}` : `${mm}/${dd}`;
      const cls   = cfg.showDow && curr.getDay() === 6 ? 'sat'
                  : cfg.showDow && curr.getDay() === 0 ? 'sun' : '';
      ticks.push({ p, label, cls });
    }
    curr.setDate(curr.getDate() + cfg.step);
  }

  // ウィンドウ外のバーは除外
  const visibleMap = {};
  for (const r of rows) {
    if (r.end < minDt || r.start > maxDt) continue;
    visibleMap[r.group] = visibleMap[r.group] || [];
    visibleMap[r.group].push(r);
  }
  const groupMap = visibleMap;

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
  // マイルストーングループを先頭に
  const todayPct = getPct(today);
  const sortedGroups = Object.keys(groupMap).sort((a, b) => {
    if (a === MS_GROUP) return -1;
    if (b === MS_GROUP) return  1;
    return a.localeCompare(b, 'ja');
  });

  for (const grp of sortedGroups) {
    const bars  = groupMap[grp];
    const rowH  = bars.length * LANE_H + 8;

    h += `<div class="tl-row" style="height:${rowH}px">`;
    h += `<div class="tl-group-name" style="height:${rowH}px">${esc(grp)}</div>`;
    h += `<div class="tl-chart-area" style="height:${rowH}px">`;

    for (const { p } of ticks) {
      h += `<div class="tl-gridline" style="left:${p.toFixed(2)}%"></div>`;
    }
    if (todayPct >= 0 && todayPct <= 100) {
      h += `<div class="tl-today-line" style="left:${todayPct.toFixed(2)}%"></div>`;
    }

    bars.forEach((r, i) => {
      const laneTop = 4 + i * LANE_H;
      if (r.isMs) {
        // ── マイルストーン: ひし形を期限日の位置に表示 ──
        const dlPct = getPct(r.start);  // r.start = 期限日
        const ctrY  = laneTop + LANE_H / 2;
        const label = esc(r.title.replace(/^🔷\s*/, ''));
        h += `<div class="tl-ms-pos" data-id="${esc(r.id)}" title="${label}" style="left:${dlPct.toFixed(2)}%;top:${ctrY}px">`;
        h += `<div class="tl-ms-diamond"></div>`;
        h += `<span class="tl-ms-label">${label}</span>`;
        h += '</div>';
      } else {
        // ── 通常タスク: バー表示 ──
        const barTop = laneTop + BAR_PAD;
        const left   = getPct(r.start);
        const width  = Math.max(getPct(r.end) - left, 1.5);
        h += `<div class="tl-bar-outer" data-id="${esc(r.id)}"`;
        h += ` style="left:${left.toFixed(2)}%;width:${width.toFixed(2)}%;top:${barTop}px;height:${BAR_H}px">`;
        h += '<div class="tl-resize-handle tl-handle-left" title="開始日を変更"></div>';
        h += `<div class="tl-bar-fill" style="background:${r.color}">`;
        h += `<span class="tl-bar-name">${esc(r.title)}</span>`;
        h += '</div>';
        h += '<div class="tl-resize-handle tl-handle-right" title="終了日を変更"></div>';
        h += '</div>';
      }
    });

    h += '</div></div>';
  }
  h += '</div>';

  container.innerHTML = h;
}

// ── 新規タスクフォーム ────────────────────────────────────────────────────────

async function initNewTaskForm() {
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('nt-deadline').value = today;
  // ログイン中なら担当者をデフォルト設定（フォームリセット後も再セットされるよう毎回実行）
  const me = window.CURRENT_USER;
  if (me) {
    const assigneeEl = document.getElementById('nt-assignee');
    if (!assigneeEl.value) assigneeEl.value = me.username;
  }
}

// ── ユーザーオートコンプリート ─────────────────────────────────────────────────

function initUserAutocomplete(inputEl, dropdownEl) {
  if (!inputEl || !dropdownEl) return;
  let debounceTimer;
  inputEl.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = inputEl.value.trim();
    if (!q) { dropdownEl.style.display = 'none'; return; }
    debounceTimer = setTimeout(async () => {
      try {
        const users = await fetch(`/api/users?q=${encodeURIComponent(q)}`).then(r => r.json());
        dropdownEl.innerHTML = '';
        if (!users.length) { dropdownEl.style.display = 'none'; return; }
        users.forEach(u => {
          const item = document.createElement('div');
          item.className = 'user-suggestion';
          item.textContent = u.display_name !== u.username
            ? `${u.display_name} (@${u.username})`
            : `@${u.username}`;
          item.addEventListener('mousedown', (e) => {
            e.preventDefault();  // blurを防ぐ
            inputEl.value = u.username;
            dropdownEl.style.display = 'none';
          });
          dropdownEl.appendChild(item);
        });
        dropdownEl.style.display = 'block';
      } catch (_) { dropdownEl.style.display = 'none'; }
    }, 200);
  });
  inputEl.addEventListener('blur', () => {
    setTimeout(() => { dropdownEl.style.display = 'none'; }, 150);
  });
}

// ── マイタスクビュー ───────────────────────────────────────────────────────────

function renderMyTasks() {
  const me = (window.CURRENT_USER || {}).username || '';
  const container = document.getElementById('mytasks-content');
  if (!container) return;

  if (!me) {
    container.innerHTML = '<p style="padding:32px;color:var(--subtext)">ログインするとマイタスクが表示されます。</p>';
    return;
  }

  const myTasks = tasks.filter(t => t.assignee === me);
  container.innerHTML = '';

  if (!myTasks.length) {
    container.innerHTML = `<p style="padding:32px;color:var(--subtext)">あなたに割り当てられたタスクはありません。</p>`;
    return;
  }

  const counts = { todo: 0, wip: 0, done: 0 };
  for (const t of myTasks) counts[t.column] = (counts[t.column] || 0) + 1;

  const hdr = document.createElement('div');
  hdr.className = 'assignee-hdr';
  hdr.innerHTML = `
    <span>⭐ ${esc((window.CURRENT_USER || {}).display_name || me)}</span>
    <span class="assignee-count">
      計&nbsp;${myTasks.length}&nbsp;件&nbsp;｜&nbsp;
      待機&nbsp;${counts.todo}&nbsp;
      進行&nbsp;${counts.wip}&nbsp;
      完了&nbsp;${counts.done}
    </span>`;
  container.appendChild(hdr);

  const colsDiv = document.createElement('div');
  colsDiv.className = 'assignee-cols';

  for (const col of ['todo', 'wip', 'done']) {
    const colDiv = document.createElement('div');
    colDiv.className = 'assignee-col';

    const lbl = document.createElement('div');
    lbl.className = 'status-label';
    lbl.textContent = `${COL_META[col].label} (${counts[col] || 0})`;
    colDiv.appendChild(lbl);

    const cardsDiv = document.createElement('div');
    cardsDiv.className = 'assignee-cards';
    cardsDiv.dataset.assignee = me;
    cardsDiv.dataset.col = col;

    const SHOW_LIMIT = 3;
    const colTasks = myTasks.filter(t => t.column === col);
    colTasks.forEach((task, i) => {
      const card = createCard(task, true);
      if (i >= SHOW_LIMIT) card.classList.add('card-collapsed');
      cardsDiv.appendChild(card);
    });
    colDiv.appendChild(cardsDiv);

    const extra = colTasks.length - SHOW_LIMIT;
    if (extra > 0) {
      const btn = document.createElement('button');
      btn.className = 'cards-show-more';
      btn.textContent = `▼ もっと見る（${extra}件）`;
      btn.addEventListener('click', () => {
        const isCollapsed = !!cardsDiv.querySelector('.card-collapsed');
        if (isCollapsed) {
          cardsDiv.querySelectorAll('.card-collapsed').forEach(c => c.classList.remove('card-collapsed'));
          btn.textContent = '▲ 閉じる';
        } else {
          Array.from(cardsDiv.children).slice(SHOW_LIMIT).forEach(c => c.classList.add('card-collapsed'));
          btn.textContent = `▼ もっと見る（${extra}件）`;
        }
      });
      colDiv.appendChild(btn);
    }

    colsDiv.appendChild(colDiv);
  }

  container.appendChild(colsDiv);
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
  document.getElementById('nt-assignee').value    = (window.CURRENT_USER || {}).username || '';
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
  document.getElementById('task-started-at').value        = fmtDatetimeLocal(task.started_at);
  document.getElementById('task-finished-at').value       = fmtDatetimeLocal(task.finished_at);
  document.getElementById('btn-delete').style.display     = 'inline-block';
  showModal();
}

function copyTask(src) {
  editingTask = null;
  document.getElementById('modal-title').textContent       = 'タスクをコピー';
  document.getElementById('task-title').value              = src.title + ' のコピー';
  document.getElementById('task-assignee').value           = src.assignee   || '';
  document.getElementById('task-deadline').value           = src.deadline   || '';
  document.getElementById('task-column').value             = src.column     || 'todo';
  document.getElementById('task-note').value               = src.note       || '';
  document.getElementById('task-color').value              = src.color      || '#FFD166';
  document.getElementById('task-started-at').value         = fmtDatetimeLocal(src.started_at);
  document.getElementById('task-finished-at').value        = fmtDatetimeLocal(src.finished_at);
  document.getElementById('btn-delete').style.display      = 'none';
  showModal();
}

function showModal() {
  document.getElementById('overlay').style.display = 'flex';
  // 削除確認UIをリセット
  document.getElementById('delete-confirm-row').style.display = 'none';
  document.getElementById('modal-btns').style.display         = 'flex';
  lockBodyScroll();
  document.getElementById('task-title').focus();
}

function closeModal() {
  document.getElementById('overlay').style.display = 'none';
  editingTask = null;
  unlockBodyScroll();
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
    assignee:    document.getElementById('task-assignee').value.trim(),
    deadline:    document.getElementById('task-deadline').value,
    note:        document.getElementById('task-note').value.trim(),
    color:       document.getElementById('task-color').value,
    column:      document.getElementById('task-column').value,
    started_at:  document.getElementById('task-started-at').value  || '',
    finished_at: document.getElementById('task-finished-at').value || '',
  };

  if (editingTask) {
    Object.assign(editingTask, data);
    renderCurrentView();
    await apiPut(editingTask.id, data);
  } else {
    // コピー/新規作成モード
    const created = await apiPost(data);
    tasks.push(created);
    renderCurrentView();
  }

  closeModal();
}

async function deleteTask() {
  if (!editingTask) return;
  const id = editingTask.id;
  tasks = tasks.filter(t => t.id !== id);
  renderCurrentView();
  closeModal();

  await apiDelete(id);
}

// ── 担当者管理ビュー ──────────────────────────────────────────────────────────

async function renderManage() {
  const container = document.getElementById('manage-content');
  if (!container) return;
  container.innerHTML = '<p style="padding:24px;color:var(--subtext)">読み込み中...</p>';

  // 登録ユーザー一覧を取得
  let users = [];
  try { users = await fetch('/api/users').then(r => r.json()); } catch (_) {}
  const usernames = new Set(users.map(u => u.username));
  const userMap   = Object.fromEntries(users.map(u => [u.username, u]));

  // タスクから担当者ごとの件数を集計
  const groups = {};
  for (const t of tasks) {
    const key = t.assignee || '';
    groups[key] = (groups[key] || 0) + 1;
  }

  const assignees = Object.keys(groups).sort((a, b) => {
    if (!a) return 1; if (!b) return -1;
    return a.localeCompare(b, 'ja');
  });

  container.innerHTML = '';

  const desc = document.createElement('p');
  desc.className = 'manage-desc';
  desc.textContent = '担当者名の「→ 振り替え」で、そのユーザーのタスクを別アカウントに一括移動できます。未紐づけの担当者は登録アカウントと一致していません。';
  container.appendChild(desc);

  if (!assignees.length) {
    const empty = document.createElement('p');
    empty.style.cssText = 'padding:24px;color:var(--subtext)';
    empty.textContent = 'タスクがありません。';
    container.appendChild(empty);
    return;
  }

  const table = document.createElement('div');
  table.className = 'manage-table';

  for (const key of assignees) {
    const isLinked  = !!key && usernames.has(key);
    const label     = key || '（未割り当て）';
    const count     = groups[key];

    const row = document.createElement('div');
    row.className = 'manage-row';
    row.innerHTML = `
      <div class="manage-cell manage-name">
        <span>${esc(label)}</span>
        ${isLinked
          ? `<span class="manage-linked">✅ @${esc(key)}</span>`
          : (key ? '<span class="manage-unlinked">🔴 未紐づけ</span>' : '')}
      </div>
      <div class="manage-cell manage-count">${count}件</div>
      <div class="manage-cell manage-action">
        <button class="btn-reassign">→ 振り替え</button>
      </div>
      <div class="manage-inline" style="display:none">
        <div class="user-suggestion-wrap">
          <input type="text" class="reassign-input" placeholder="移動先ユーザーを検索...">
          <div class="user-suggestions reassign-dropdown" style="display:none"></div>
        </div>
        <button class="btn btn-primary btn-reassign-ok">実行</button>
        <button class="btn btn-cancel btn-reassign-cancel">キャンセル</button>
      </div>`;

    const btnOpen   = row.querySelector('.btn-reassign');
    const inline    = row.querySelector('.manage-inline');
    const inputEl   = row.querySelector('.reassign-input');
    const dropEl    = row.querySelector('.reassign-dropdown');
    const btnOk     = row.querySelector('.btn-reassign-ok');
    const btnCancel = row.querySelector('.btn-reassign-cancel');

    btnOpen.addEventListener('click', () => {
      inline.style.display = 'flex';
      btnOpen.style.display = 'none';
      inputEl.focus();
      initUserAutocomplete(inputEl, dropEl);
    });

    btnCancel.addEventListener('click', () => {
      inline.style.display = 'none';
      btnOpen.style.display = '';
      inputEl.value = '';
      dropEl.style.display = 'none';
    });

    btnOk.addEventListener('click', async () => {
      const toVal = inputEl.value.trim();
      if (!toVal) { inputEl.focus(); return; }
      btnOk.disabled = true;
      btnOk.textContent = '更新中...';
      try {
        await fetch('/api/tasks/reassign', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ from: key, to: toVal }),
        });
        // ローカルの tasks も即時更新
        tasks.forEach(t => { if ((t.assignee || '') === key) t.assignee = toVal; });
        renderManage();
      } catch (_) {
        btnOk.disabled = false;
        btnOk.textContent = '実行';
      }
    });

    table.appendChild(row);
  }

  container.appendChild(table);
}

// ── タイムライン インタラクション ─────────────────────────────────────────────

function getTaskTimeBounds(task) {
  let start = task.started_at  ? new Date(task.started_at)  : null;
  let end   = task.finished_at ? new Date(task.finished_at) : null;
  const dl  = task.deadline    ? new Date(task.deadline)    : null;
  if (!start && !dl) return null;
  if (!start) { start = new Date(dl); start.setDate(start.getDate() - 7); }
  if (!end)   { end   = new Date(start); end.setHours(end.getHours() + 23); }
  return { start, end };
}

/** パーセント位置を日付の区切り(0時)に変換 */
function tlPctToDay(pct) {
  const d = new Date(tlMinDt.getTime() + (pct / 100) * tlTotalMs);
  d.setHours(0, 0, 0, 0);
  return d;
}

/** ISO日時文字列を datetime-local input 用の "YYYY-MM-DDTHH:MM" に変換（ローカル時刻） */
function fmtDatetimeLocal(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  if (isNaN(d)) return '';
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

function onTlPointerDown(e) {
  const bar = e.target.closest('.tl-bar-outer, .tl-ms-pos');
  if (!bar || !tlMinDt) return;

  const isMilestone = bar.classList.contains('tl-ms-pos');
  const taskId = bar.dataset.id;
  const task   = tasks.find(t => t.id === taskId);
  if (!task) return;

  const chartArea     = bar.closest('.tl-chart-area');
  const isHandleLeft  = !isMilestone && e.target.classList.contains('tl-handle-left');
  const isHandleRight = !isMilestone && e.target.classList.contains('tl-handle-right');
  const type = isHandleLeft ? 'resize-left' : isHandleRight ? 'resize-right' : 'move';

  tlDrag = {
    type,
    taskId,
    bar,
    chartArea,
    startX:     e.clientX,
    origLeft:   parseFloat(bar.style.left),
    origWidth:  isMilestone ? 0 : parseFloat(bar.style.width),
    moved:      false,
    isMilestone,
  };

  e.preventDefault();
  bar.setPointerCapture(e.pointerId);
  bar.style.opacity = '0.75';
}

function onTlPointerMove(e) {
  if (!tlDrag) return;

  const rect     = tlDrag.chartArea.getBoundingClientRect();
  const deltaX   = e.clientX - tlDrag.startX;
  const deltaPct = (deltaX / rect.width) * 100;

  if (Math.abs(deltaX) > 3) tlDrag.moved = true;
  if (!tlDrag.moved) return;

  const MIN_W = 0.3;  // バーの最小幅 (%)

  if (tlDrag.type === 'move') {
    const newLeft = Math.max(-5, Math.min(tlDrag.origLeft + deltaPct, 105 - tlDrag.origWidth));
    tlDrag.bar.style.left = `${newLeft.toFixed(2)}%`;

  } else if (tlDrag.type === 'resize-left') {
    const newWidth = tlDrag.origWidth - deltaPct;
    if (newWidth >= MIN_W) {
      tlDrag.bar.style.left  = `${(tlDrag.origLeft + deltaPct).toFixed(2)}%`;
      tlDrag.bar.style.width = `${newWidth.toFixed(2)}%`;
    }

  } else if (tlDrag.type === 'resize-right') {
    const newWidth = Math.max(MIN_W, tlDrag.origWidth + deltaPct);
    tlDrag.bar.style.width = `${newWidth.toFixed(2)}%`;
  }
}

async function onTlPointerUp(e) {
  if (!tlDrag) return;

  const { type, taskId, bar, moved, isMilestone } = tlDrag;
  bar.style.opacity = '';
  tlDrag = null;

  const task = tasks.find(t => t.id === taskId);
  if (!task) return;

  if (!moved) {
    // ダブルクリック検出 → 編集モーダルを開く
    const now = Date.now();
    if (tlLastClick && tlLastClick.taskId === taskId && now - tlLastClick.time < 350) {
      tlLastClick = null;
      openEditModal(task);
    } else {
      tlLastClick = { taskId, time: now };
    }
    return;
  }

  // マイルストーンのドラッグ: 期限日を更新
  if (isMilestone) {
    const newDeadline = tlPctToDay(parseFloat(bar.style.left));
    const dlStr = newDeadline.toISOString().split('T')[0];
    Object.assign(task, { deadline: dlStr });
    renderTimeline();
    await apiPut(taskId, { deadline: dlStr });
    return;
  }

  // ドラッグ確定: バーの現在位置から日付を逆算して保存
  const finalLeft  = parseFloat(bar.style.left);
  const finalWidth = parseFloat(bar.style.width);
  const newStart   = tlPctToDay(finalLeft);
  const newEnd     = tlPctToDay(finalLeft + finalWidth);

  // 最低1日は確保
  if (newEnd <= newStart) newEnd.setDate(newStart.getDate() + 1);

  const updates = {
    started_at:  newStart.toISOString(),
    finished_at: newEnd.toISOString(),
    deadline:    newEnd.toISOString().split('T')[0],  // 期限を終了日に合わせる
  };

  Object.assign(task, updates);
  renderTimeline();
  await apiPut(taskId, updates);
}

// ── ヘルパー ──────────────────────────────────────────────────────────────────

/** タイトルが "🔷 " で始まるタスクをマイルストーンとみなす */
function isMsTask(task) {
  return task.title.startsWith('🔷 ');
}

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

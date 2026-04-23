'use strict';

const BOARD_COLORS = [
  '#FFD166','#EF476F','#06D6A0',
  '#118AB2','#FFB347','#C77DFF',
  '#F72585','#4CC9F0','#80ED99',
];

let allBoards    = [];
let currentBoard = null;
let boardCards   = [];
let boardDrag    = null;
let editingCard  = null;
let editingBoard = null;

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  bindBoardsEvents();
  loadBoards();
});

// ── Board list: fetch & sidebar ───────────────────────────────────────────────

async function loadBoards() {
  const res = await fetch('/api/boards');
  allBoards = await res.json();
  renderBoardsNav();
}

function renderBoardsNav() {
  const nav = document.getElementById('custom-boards-nav');
  nav.innerHTML = '';
  for (const board of allBoards) {
    const btn = document.createElement('button');
    btn.className = 'nav-btn';
    btn.dataset.view = `board-${board.id}`;
    btn.title = board.name;
    btn.innerHTML = `<span class="ni">${board.icon}</span><span class="nl"> ${board.name}</span>`;
    btn.addEventListener('click', () => { switchView(`board-${board.id}`); closeSidebar(); });
    nav.appendChild(btn);
  }
}

// ── Entry point (called by switchView) ────────────────────────────────────────

async function initCustomBoard(boardId) {
  let board = allBoards.find(b => b.id === boardId);
  if (!board) {
    // Boards may not be loaded yet; reload and retry
    await loadBoards();
    board = allBoards.find(b => b.id === boardId);
  }
  if (!board) return;

  currentBoard = board;
  document.getElementById('board-view-title').textContent = `${board.icon} ${board.name}`;

  const res = await fetch(`/api/boards/${boardId}/cards`);
  boardCards = await res.json();
  renderBoard();
}

// ── Render board ──────────────────────────────────────────────────────────────

function renderBoard() {
  if (!currentBoard) return;
  const container = document.getElementById('board-view-board');
  container.innerHTML = '';

  for (let floor = currentBoard.floors; floor >= 1; floor--) {
    container.appendChild(buildBoardFloorRow(floor));
  }
  document.getElementById('board-total').textContent = boardCards.length;
}

function buildBoardFloorRow(floor) {
  const floorCards = boardCards.filter(c => c.floor === floor);

  const row = document.createElement('div');
  row.className = 'floor-row';
  row.dataset.floor = floor;

  const label = document.createElement('div');
  label.className = 'floor-label';
  label.innerHTML = `
    <span class="floor-num">${floor}</span>
    <span class="floor-f">F</span>
    <span class="badge floor-count">${floorCards.length}</span>
  `;

  const area = document.createElement('div');
  area.className = 'floor-cards';

  for (const card of floorCards) {
    area.appendChild(buildBoardCard(card));
  }

  const addBtn = document.createElement('button');
  addBtn.className = 'floor-add-btn';
  addBtn.textContent = '＋';
  addBtn.title = `${floor}Fに追加`;
  addBtn.addEventListener('click', () => openBoardCardModal(floor));
  area.appendChild(addBtn);

  row.appendChild(label);
  row.appendChild(area);
  return row;
}

function buildBoardCard(card) {
  const el = document.createElement('div');
  el.className = 'lift-card';
  el.dataset.id = card.id;
  el.style.background = card.color;

  const topBg = boardDarken(card.color, 0.2);
  el.innerHTML = `
    <div class="card-top" style="background:${topBg}">
      <span class="card-title">${boardEsc(card.name)}</span>
      <button class="card-edit-btn" title="編集">✏️</button>
    </div>
    <div class="card-body">
      ${card.operator ? `<div class="card-assignee">👷 ${boardEsc(card.operator)}</div>` : ''}
      ${card.note     ? `<div class="card-note">${boardEsc(card.note)}</div>` : ''}
    </div>
  `;

  el.querySelector('.card-edit-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    openBoardCardEditModal(card);
  });

  // ── Pointer Events DnD ────────────────────────────────────────────────────

  el.addEventListener('pointerdown', (e) => {
    if (e.button !== 0 && e.pointerType === 'mouse') return;
    if (e.target.closest('.card-edit-btn')) return;
    e.preventDefault();
    el.setPointerCapture(e.pointerId);

    const rect = el.getBoundingClientRect();
    const ghost = el.cloneNode(true);
    ghost.className = 'card-ghost';
    ghost.style.width  = rect.width + 'px';
    ghost.style.left   = rect.left + 'px';
    ghost.style.top    = rect.top + 'px';
    document.body.appendChild(ghost);
    el.style.opacity = '0.35';

    boardDrag = {
      card, el, ghost,
      offsetX: e.clientX - rect.left,
      offsetY: e.clientY - rect.top,
      startX:  e.clientX,
      startY:  e.clientY,
      moved:   false,
    };
  });

  el.addEventListener('pointermove', (e) => {
    if (!boardDrag || boardDrag.el !== el) return;
    const dx = e.clientX - boardDrag.startX;
    const dy = e.clientY - boardDrag.startY;
    if (!boardDrag.moved && Math.hypot(dx, dy) > 4) boardDrag.moved = true;
    if (!boardDrag.moved) return;

    boardDrag.ghost.style.left = (e.clientX - boardDrag.offsetX) + 'px';
    boardDrag.ghost.style.top  = (e.clientY - boardDrag.offsetY) + 'px';

    boardDrag.ghost.style.display = 'none';
    const target = document.elementFromPoint(e.clientX, e.clientY);
    boardDrag.ghost.style.display = '';
    document.querySelectorAll('#board-view-board .floor-row').forEach(r => r.classList.remove('highlight'));
    target?.closest('.floor-row')?.classList.add('highlight');
  });

  el.addEventListener('pointerup', async (e) => {
    if (!boardDrag || boardDrag.el !== el) return;
    const { card: dragCard, ghost, moved } = boardDrag;
    boardDrag = null;
    el.style.opacity = '';
    document.querySelectorAll('#board-view-board .floor-row').forEach(r => r.classList.remove('highlight'));

    if (!moved) {
      ghost.remove();
      openBoardCardEditModal(card);
      return;
    }

    ghost.style.display = 'none';
    const target = document.elementFromPoint(e.clientX, e.clientY);
    ghost.remove();

    const row = target?.closest('.floor-row');
    if (!row) return;
    const targetFloor = parseInt(row.dataset.floor, 10);
    if (targetFloor === dragCard.floor) return;

    dragCard.floor = targetFloor;
    renderBoard();
    await fetch(`/api/boards/${currentBoard.id}/cards/${dragCard.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dragCard),
    });
  });

  el.addEventListener('lostpointercapture', () => {
    if (boardDrag && boardDrag.el === el) {
      boardDrag.ghost.remove();
      el.style.opacity = '';
      document.querySelectorAll('#board-view-board .floor-row').forEach(r => r.classList.remove('highlight'));
      boardDrag = null;
    }
  });

  return el;
}

// ── Event binding ─────────────────────────────────────────────────────────────

function bindBoardsEvents() {
  document.getElementById('board-add-btn').addEventListener('click', openBoardCreateModal);
  document.getElementById('board-edit-btn').addEventListener('click', openBoardEditModal);
  document.getElementById('board-card-new-btn').addEventListener('click', () => openBoardCardModal(1));

  // Board settings modal
  document.getElementById('board-settings-cancel').addEventListener('click', closeBoardSettingsModal);
  document.getElementById('board-settings-save').addEventListener('click', saveBoardSettings);
  document.getElementById('board-settings-delete').addEventListener('click', deleteBoard);
  document.getElementById('board-settings-overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('board-settings-overlay')) closeBoardSettingsModal();
  });

  // Board card modal
  document.getElementById('board-card-cancel').addEventListener('click', closeBoardCardModal);
  document.getElementById('board-card-save').addEventListener('click', saveBoardCard);
  document.getElementById('board-card-delete').addEventListener('click', deleteBoardCard);
  document.getElementById('board-card-overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('board-card-overlay')) closeBoardCardModal();
  });

  document.addEventListener('keydown', (e) => {
    if (document.getElementById('board-settings-overlay').style.display === 'flex') {
      if (e.key === 'Escape') closeBoardSettingsModal();
      if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') saveBoardSettings();
    }
    if (document.getElementById('board-card-overlay').style.display === 'flex') {
      if (e.key === 'Escape') closeBoardCardModal();
      if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') saveBoardCard();
    }
  });

  // Color swatches
  const swatchContainer = document.getElementById('board-card-swatches');
  const swatchWrapper = document.createElement('div');
  swatchWrapper.className = 'color-swatches';
  for (const c of BOARD_COLORS) {
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = c;
    sw.addEventListener('click', () => { document.getElementById('board-card-color').value = c; });
    swatchWrapper.appendChild(sw);
  }
  swatchContainer.appendChild(swatchWrapper);
}

// ── Board settings modal ──────────────────────────────────────────────────────

function openBoardCreateModal() {
  editingBoard = null;
  document.getElementById('board-settings-title').textContent       = '配置図を追加';
  document.getElementById('board-name').value                        = '';
  document.getElementById('board-icon').value                        = '📋';
  document.getElementById('board-floors').value                      = '8';
  document.getElementById('board-settings-delete').style.display    = 'none';
  document.getElementById('board-settings-overlay').style.display   = 'flex';
  document.getElementById('board-name').focus();
}

function openBoardEditModal() {
  if (!currentBoard) return;
  editingBoard = currentBoard;
  document.getElementById('board-settings-title').textContent       = '配置図を編集';
  document.getElementById('board-name').value                        = currentBoard.name;
  document.getElementById('board-icon').value                        = currentBoard.icon;
  document.getElementById('board-floors').value                      = String(currentBoard.floors);
  document.getElementById('board-settings-delete').style.display    = 'inline-block';
  document.getElementById('board-settings-overlay').style.display   = 'flex';
  document.getElementById('board-name').focus();
}

function closeBoardSettingsModal() {
  document.getElementById('board-settings-overlay').style.display = 'none';
  editingBoard = null;
}

async function saveBoardSettings() {
  const name   = document.getElementById('board-name').value.trim();
  const icon   = document.getElementById('board-icon').value.trim() || '📋';
  const floors = parseInt(document.getElementById('board-floors').value, 10) || 8;

  if (!name) {
    alert('名前を入力してください');
    document.getElementById('board-name').focus();
    return;
  }

  if (editingBoard) {
    const res = await fetch(`/api/boards/${editingBoard.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, icon, floors }),
    });
    const updated = await res.json();
    Object.assign(editingBoard, updated);
    currentBoard = editingBoard;
    renderBoardsNav();
    document.getElementById('board-view-title').textContent = `${icon} ${name}`;
    renderBoard();
  } else {
    const res = await fetch('/api/boards', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, icon, floors }),
    });
    const board = await res.json();
    allBoards.push(board);
    renderBoardsNav();
    switchView(`board-${board.id}`);
  }

  closeBoardSettingsModal();
}

async function deleteBoard() {
  if (!editingBoard) return;
  if (!confirm(`「${editingBoard.name}」を削除しますか？\nこの配置図のカードもすべて削除されます。`)) return;

  await fetch(`/api/boards/${editingBoard.id}`, { method: 'DELETE' });
  allBoards = allBoards.filter(b => b.id !== editingBoard.id);
  renderBoardsNav();
  closeBoardSettingsModal();
  switchView('aerial');
}

// ── Board card modal ──────────────────────────────────────────────────────────

function openBoardCardModal(floor) {
  editingCard = null;
  const defaultName = currentBoard
    ? `${currentBoard.name} ${String(boardCards.length + 1).padStart(2, '0')}`
    : '';
  document.getElementById('board-card-modal-title').textContent = 'アイテムを追加';
  document.getElementById('board-card-id').value                = '';
  document.getElementById('board-card-name').value              = defaultName;
  document.getElementById('board-card-operator').value          = '';
  document.getElementById('board-card-note').value              = '';
  document.getElementById('board-card-color').value             = BOARD_COLORS[boardCards.length % BOARD_COLORS.length];
  document.getElementById('board-card-floor').value             = String(floor);
  document.getElementById('board-card-floor').max               = String(currentBoard?.floors || 20);
  document.getElementById('board-card-delete').style.display    = 'none';
  document.getElementById('board-card-overlay').style.display   = 'flex';
  document.getElementById('board-card-name').focus();
}

function openBoardCardEditModal(card) {
  editingCard = card;
  document.getElementById('board-card-modal-title').textContent = 'アイテムを編集';
  document.getElementById('board-card-id').value                = card.id;
  document.getElementById('board-card-name').value              = card.name;
  document.getElementById('board-card-operator').value          = card.operator || '';
  document.getElementById('board-card-note').value              = card.note    || '';
  document.getElementById('board-card-color').value             = card.color;
  document.getElementById('board-card-floor').value             = String(card.floor);
  document.getElementById('board-card-floor').max               = String(currentBoard?.floors || 20);
  document.getElementById('board-card-delete').style.display    = 'inline-block';
  document.getElementById('board-card-overlay').style.display   = 'flex';
  document.getElementById('board-card-name').focus();
}

function closeBoardCardModal() {
  document.getElementById('board-card-overlay').style.display = 'none';
  editingCard = null;
}

async function saveBoardCard() {
  const name = document.getElementById('board-card-name').value.trim();
  if (!name) {
    alert('名前を入力してください');
    document.getElementById('board-card-name').focus();
    return;
  }

  const data = {
    name,
    operator: document.getElementById('board-card-operator').value.trim(),
    note:     document.getElementById('board-card-note').value.trim(),
    color:    document.getElementById('board-card-color').value,
    floor:    parseInt(document.getElementById('board-card-floor').value, 10),
  };

  if (editingCard) {
    const res = await fetch(`/api/boards/${currentBoard.id}/cards/${editingCard.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const updated = await res.json();
    const idx = boardCards.findIndex(c => c.id === editingCard.id);
    if (idx >= 0) boardCards[idx] = updated;
  } else {
    const res = await fetch(`/api/boards/${currentBoard.id}/cards`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const created = await res.json();
    boardCards.push(created);
  }

  renderBoard();
  closeBoardCardModal();
}

async function deleteBoardCard() {
  if (!editingCard) return;
  if (!confirm('このアイテムを削除しますか？')) return;

  await fetch(`/api/boards/${currentBoard.id}/cards/${editingCard.id}`, { method: 'DELETE' });
  boardCards = boardCards.filter(c => c.id !== editingCard.id);
  renderBoard();
  closeBoardCardModal();
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function boardDarken(hex, factor) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const d = v => Math.round(v * (1 - factor)).toString(16).padStart(2, '0');
  return `#${d(r)}${d(g)}${d(b)}`;
}

function boardEsc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

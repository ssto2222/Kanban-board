'use strict';

const LIFT_COLORS = [
  '#FFD166','#EF476F','#06D6A0',
  '#118AB2','#FFB347','#C77DFF',
  '#F72585','#4CC9F0','#80ED99',
];

let lifts      = [];
let draggedId  = null;
let editingLift = null;

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  buildSwatches();
  bindEvents();
  loadLifts();
});

function buildSwatches() {
  const container = document.getElementById('swatches');
  for (const c of LIFT_COLORS) {
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = c;
    sw.title = c;
    sw.addEventListener('click', () => {
      document.getElementById('lift-color').value = c;
    });
    container.appendChild(sw);
  }
}

function bindEvents() {
  document.getElementById('btn-new').addEventListener('click', () => openNewModal(1));
  document.getElementById('btn-cancel').addEventListener('click', closeModal);
  document.getElementById('btn-save').addEventListener('click', saveLift);
  document.getElementById('btn-delete').addEventListener('click', deleteLift);

  document.getElementById('overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('overlay')) closeModal();
  });

  document.addEventListener('keydown', (e) => {
    const overlay = document.getElementById('overlay');
    if (overlay.style.display !== 'flex') return;
    if (e.key === 'Escape') closeModal();
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') saveLift();
  });
}

// ── API ───────────────────────────────────────────────────────────────────────

async function loadLifts() {
  const res = await fetch('/api/lifts');
  lifts = await res.json();
  render();
}

async function apiPut(id, data) {
  await fetch(`/api/lifts/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

async function apiPost(data) {
  const res = await fetch('/api/lifts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

async function apiDelete(id) {
  await fetch(`/api/lifts/${id}`, { method: 'DELETE' });
}

// ── Render ────────────────────────────────────────────────────────────────────

function render() {
  const board = document.getElementById('board');
  board.innerHTML = '';

  // 8F at top → 1F at bottom
  for (let floor = 8; floor >= 1; floor--) {
    board.appendChild(createFloorRow(floor));
  }

  document.getElementById('total-count').textContent = lifts.length;
}

function createFloorRow(floor) {
  const floorLifts = lifts.filter(l => l.floor === floor);

  const row = document.createElement('div');
  row.className = 'floor-row';
  row.dataset.floor = floor;

  // Floor label
  const label = document.createElement('div');
  label.className = 'floor-label';
  label.innerHTML = `
    <span class="floor-num">${floor}</span>
    <span class="floor-f">F</span>
    <span class="floor-count">${floorLifts.length}</span>
  `;

  // Cards area
  const cardsArea = document.createElement('div');
  cardsArea.className = 'floor-cards';
  cardsArea.dataset.floor = floor;

  for (const lift of floorLifts) {
    cardsArea.appendChild(createCard(lift));
  }

  // Per-floor add button
  const addBtn = document.createElement('button');
  addBtn.className = 'floor-add-btn';
  addBtn.textContent = '＋';
  addBtn.title = `${floor}Fに追加`;
  addBtn.addEventListener('click', () => openNewModal(floor));
  cardsArea.appendChild(addBtn);

  // Drag-and-drop for the whole row
  row.addEventListener('dragover', (e) => {
    e.preventDefault();
    row.classList.add('highlight');
  });
  row.addEventListener('dragleave', (e) => {
    if (!row.contains(e.relatedTarget)) row.classList.remove('highlight');
  });
  row.addEventListener('drop', (e) => handleDrop(e, floor));

  row.appendChild(label);
  row.appendChild(cardsArea);
  return row;
}

function createCard(lift) {
  const card = document.createElement('div');
  card.className = 'lift-card';
  card.draggable = true;
  card.dataset.id = lift.id;
  card.style.background = lift.color;

  const topBg = darken(lift.color, 0.2);

  card.innerHTML = `
    <div class="card-top" style="background:${topBg}">
      <span class="card-title">${esc(lift.name)}</span>
      <button class="card-edit-btn" title="編集">✏️</button>
    </div>
    <div class="card-body">
      ${lift.operator ? `<div class="card-operator">👷 ${esc(lift.operator)}</div>` : ''}
      ${lift.note     ? `<div class="card-note">${esc(lift.note)}</div>` : ''}
    </div>
  `;

  card.addEventListener('dragstart', (e) => {
    draggedId = lift.id;
    e.dataTransfer.effectAllowed = 'move';
    setTimeout(() => card.classList.add('dragging'), 0);
  });
  card.addEventListener('dragend', () => {
    card.classList.remove('dragging');
    draggedId = null;
    document.querySelectorAll('.floor-row').forEach(r => r.classList.remove('highlight'));
  });

  card.querySelector('.card-edit-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    openEditModal(lift);
  });
  card.addEventListener('click', () => openEditModal(lift));

  return card;
}

// ── Drag & Drop ───────────────────────────────────────────────────────────────

async function handleDrop(e, targetFloor) {
  e.preventDefault();
  document.querySelectorAll('.floor-row').forEach(r => r.classList.remove('highlight'));

  if (!draggedId) return;
  const lift = lifts.find(l => l.id === draggedId);
  if (!lift || lift.floor === targetFloor) return;

  lift.floor = targetFloor;
  render();

  await apiPut(draggedId, lift);
  draggedId = null;
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function openNewModal(floor) {
  editingLift = null;
  document.getElementById('modal-title').textContent = '高所作業車 追加';
  document.getElementById('lift-id').value       = '';
  document.getElementById('lift-name').value     = `高所作業車 ${String(lifts.length + 1).padStart(2, '0')}`;
  document.getElementById('lift-operator').value = '';
  document.getElementById('lift-note').value     = '';
  document.getElementById('lift-color').value    = LIFT_COLORS[lifts.length % LIFT_COLORS.length];
  document.getElementById('lift-floor').value    = floor;
  document.getElementById('btn-delete').style.display = 'none';
  showModal();
}

function openEditModal(lift) {
  editingLift = lift;
  document.getElementById('modal-title').textContent = '高所作業車 編集';
  document.getElementById('lift-id').value       = lift.id;
  document.getElementById('lift-name').value     = lift.name;
  document.getElementById('lift-operator').value = lift.operator || '';
  document.getElementById('lift-note').value     = lift.note    || '';
  document.getElementById('lift-color').value    = lift.color;
  document.getElementById('lift-floor').value    = lift.floor;
  document.getElementById('btn-delete').style.display = 'inline-block';
  showModal();
}

function showModal() {
  document.getElementById('overlay').style.display = 'flex';
  document.getElementById('lift-name').focus();
}

function closeModal() {
  document.getElementById('overlay').style.display = 'none';
  editingLift = null;
}

async function saveLift() {
  const name = document.getElementById('lift-name').value.trim();
  if (!name) {
    alert('車両名を入力してください');
    document.getElementById('lift-name').focus();
    return;
  }

  const data = {
    name,
    operator: document.getElementById('lift-operator').value.trim(),
    note:     document.getElementById('lift-note').value.trim(),
    color:    document.getElementById('lift-color').value,
    floor:    parseInt(document.getElementById('lift-floor').value, 10),
  };

  if (editingLift) {
    Object.assign(editingLift, data);
    render();
    await apiPut(editingLift.id, editingLift);
  } else {
    const created = await apiPost(data);
    lifts.push(created);
    render();
  }

  closeModal();
}

async function deleteLift() {
  if (!editingLift) return;
  if (!confirm('この高所作業車を削除しますか？')) return;

  const id = editingLift.id;
  lifts = lifts.filter(l => l.id !== id);
  render();
  closeModal();

  await apiDelete(id);
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function darken(hex, factor) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const d = (v) => Math.round(v * (1 - factor)).toString(16).padStart(2, '0');
  return `#${d(r)}${d(g)}${d(b)}`;
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

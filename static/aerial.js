'use strict';

const LIFT_COLORS = [
  '#FFD166','#EF476F','#06D6A0',
  '#118AB2','#FFB347','#C77DFF',
  '#F72585','#4CC9F0','#80ED99',
];

let lifts       = [];
let liftDrag    = null;   // { lift, card, ghost, offsetX, offsetY, startX, startY, moved }
let editingLift = null;
let aerialReady = false;

// ── Entry point ───────────────────────────────────────────────────────────────

function initAerial() {
  if (!aerialReady) {
    aerialReady = true;
    buildAerialSwatches();
    bindAerialEvents();
    loadLifts();
  } else {
    renderLifts();
  }
}

// ── Setup ─────────────────────────────────────────────────────────────────────

function buildAerialSwatches() {
  const container = document.getElementById('aerial-swatches');
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

function bindAerialEvents() {
  document.getElementById('aerial-btn-new').addEventListener('click', () => openLiftModal(1));
  document.getElementById('aerial-btn-cancel').addEventListener('click', closeLiftModal);
  document.getElementById('aerial-btn-save').addEventListener('click', saveLift);
  document.getElementById('aerial-btn-delete').addEventListener('click', deleteLift);

  document.getElementById('aerial-overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('aerial-overlay')) closeLiftModal();
  });

  document.addEventListener('keydown', (e) => {
    if (document.getElementById('aerial-overlay').style.display !== 'flex') return;
    if (e.key === 'Escape') closeLiftModal();
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') saveLift();
  });
}

// ── API ───────────────────────────────────────────────────────────────────────

async function loadLifts() {
  const res = await fetch('/api/lifts');
  lifts = await res.json();
  renderLifts();
}

async function liftPut(id, data) {
  await fetch(`/api/lifts/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

async function liftPost(data) {
  const res = await fetch('/api/lifts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

async function liftDelete(id) {
  await fetch(`/api/lifts/${id}`, { method: 'DELETE' });
}

// ── Render ────────────────────────────────────────────────────────────────────

function renderLifts() {
  const board = document.getElementById('aerial-board');
  board.innerHTML = '';
  for (let floor = 8; floor >= 1; floor--) {
    board.appendChild(buildFloorRow(floor));
  }
  document.getElementById('aerial-total').textContent = lifts.length;
}

function buildFloorRow(floor) {
  const floorLifts = lifts.filter(l => l.floor === floor);

  const row = document.createElement('div');
  row.className = 'floor-row';
  row.dataset.floor = floor;

  const label = document.createElement('div');
  label.className = 'floor-label';
  label.innerHTML = `
    <span class="floor-num">${floor}</span>
    <span class="floor-f">F</span>
    <span class="badge floor-count">${floorLifts.length}</span>
  `;

  const area = document.createElement('div');
  area.className = 'floor-cards';

  for (const lift of floorLifts) {
    area.appendChild(buildLiftCard(lift));
  }

  const addBtn = document.createElement('button');
  addBtn.className = 'floor-add-btn';
  addBtn.textContent = '＋';
  addBtn.title = `${floor}Fに追加`;
  addBtn.addEventListener('click', () => openLiftModal(floor));
  area.appendChild(addBtn);

  row.appendChild(label);
  row.appendChild(area);
  return row;
}

function buildLiftCard(lift) {
  const card = document.createElement('div');
  card.className = 'lift-card';
  card.dataset.id = lift.id;
  card.style.background = lift.color;

  const topBg = liftDarken(lift.color, 0.2);
  card.innerHTML = `
    <div class="card-top" style="background:${topBg}">
      <span class="card-title">${liftEsc(lift.name)}</span>
      <button class="card-edit-btn" title="編集">✏️</button>
    </div>
    <div class="card-body">
      ${lift.operator ? `<div class="card-assignee">👷 ${liftEsc(lift.operator)}</div>` : ''}
      ${lift.note     ? `<div class="card-note">${liftEsc(lift.note)}</div>` : ''}
    </div>
  `;

  card.querySelector('.card-edit-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    openLiftEditModal(lift);
  });

  // ── Pointer Events DnD (mouse + touch + pen) ──────────────────────────────

  card.addEventListener('pointerdown', (e) => {
    if (e.button !== 0 && e.pointerType === 'mouse') return;
    if (e.target.closest('.card-edit-btn')) return;
    e.preventDefault();
    card.setPointerCapture(e.pointerId);

    const rect = card.getBoundingClientRect();
    const ghost = card.cloneNode(true);
    ghost.className = 'card-ghost';
    ghost.style.width  = rect.width + 'px';
    ghost.style.left   = rect.left + 'px';
    ghost.style.top    = rect.top + 'px';
    document.body.appendChild(ghost);
    card.style.opacity = '0.35';

    liftDrag = {
      lift, card, ghost,
      offsetX: e.clientX - rect.left,
      offsetY: e.clientY - rect.top,
      startX:  e.clientX,
      startY:  e.clientY,
      moved:   false,
    };
  });

  card.addEventListener('pointermove', (e) => {
    if (!liftDrag || liftDrag.card !== card) return;
    const dx = e.clientX - liftDrag.startX;
    const dy = e.clientY - liftDrag.startY;
    if (!liftDrag.moved && Math.hypot(dx, dy) > 4) liftDrag.moved = true;
    if (!liftDrag.moved) return;

    liftDrag.ghost.style.left = (e.clientX - liftDrag.offsetX) + 'px';
    liftDrag.ghost.style.top  = (e.clientY - liftDrag.offsetY) + 'px';

    liftDrag.ghost.style.display = 'none';
    const el = document.elementFromPoint(e.clientX, e.clientY);
    liftDrag.ghost.style.display = '';
    document.querySelectorAll('#aerial-board .floor-row').forEach(r => r.classList.remove('highlight'));
    el?.closest('.floor-row')?.classList.add('highlight');
  });

  card.addEventListener('pointerup', async (e) => {
    if (!liftDrag || liftDrag.card !== card) return;
    const { lift: dragLift, ghost, moved } = liftDrag;
    liftDrag = null;
    card.style.opacity = '';
    document.querySelectorAll('#aerial-board .floor-row').forEach(r => r.classList.remove('highlight'));

    if (!moved) {
      ghost.remove();
      openLiftEditModal(lift);
      return;
    }

    ghost.style.display = 'none';
    const el = document.elementFromPoint(e.clientX, e.clientY);
    ghost.remove();

    const row = el?.closest('.floor-row');
    if (!row) return;
    const targetFloor = parseInt(row.dataset.floor, 10);
    if (targetFloor === dragLift.floor) return;

    dragLift.floor = targetFloor;
    renderLifts();
    await liftPut(dragLift.id, dragLift);
  });

  card.addEventListener('lostpointercapture', () => {
    if (liftDrag && liftDrag.card === card) {
      liftDrag.ghost.remove();
      card.style.opacity = '';
      document.querySelectorAll('#aerial-board .floor-row').forEach(r => r.classList.remove('highlight'));
      liftDrag = null;
    }
  });

  return card;
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function openLiftModal(floor) {
  editingLift = null;
  document.getElementById('aerial-modal-title').textContent  = '高所作業車 追加';
  document.getElementById('lift-id').value                   = '';
  document.getElementById('lift-name').value                 = `高所作業車 ${String(lifts.length + 1).padStart(2, '0')}`;
  document.getElementById('lift-operator').value             = '';
  document.getElementById('lift-note').value                 = '';
  document.getElementById('lift-color').value                = LIFT_COLORS[lifts.length % LIFT_COLORS.length];
  document.getElementById('lift-floor').value                = String(floor);
  document.getElementById('aerial-btn-delete').style.display = 'none';
  showLiftModal();
}

function openLiftEditModal(lift) {
  editingLift = lift;
  document.getElementById('aerial-modal-title').textContent  = '高所作業車 編集';
  document.getElementById('lift-id').value                   = lift.id;
  document.getElementById('lift-name').value                 = lift.name;
  document.getElementById('lift-operator').value             = lift.operator || '';
  document.getElementById('lift-note').value                 = lift.note    || '';
  document.getElementById('lift-color').value                = lift.color;
  document.getElementById('lift-floor').value                = String(lift.floor);
  document.getElementById('aerial-btn-delete').style.display = 'inline-block';
  showLiftModal();
}

function showLiftModal() {
  document.getElementById('aerial-overlay').style.display = 'flex';
  document.getElementById('lift-name').focus();
}

function closeLiftModal() {
  document.getElementById('aerial-overlay').style.display = 'none';
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
    renderLifts();
    await liftPut(editingLift.id, editingLift);
  } else {
    const created = await liftPost(data);
    lifts.push(created);
    renderLifts();
  }

  closeLiftModal();
}

async function deleteLift() {
  if (!editingLift) return;
  if (!confirm('この高所作業車を削除しますか？')) return;

  const id = editingLift.id;
  lifts = lifts.filter(l => l.id !== id);
  renderLifts();
  closeLiftModal();
  await liftDelete(id);
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function liftDarken(hex, factor) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const d = (v) => Math.round(v * (1 - factor)).toString(16).padStart(2, '0');
  return `#${d(r)}${d(g)}${d(b)}`;
}

function liftEsc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

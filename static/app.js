'use strict';

const STICKY_COLORS = [
  '#FFD166','#EF476F','#06D6A0',
  '#118AB2','#FFB347','#C77DFF',
  '#F72585','#4CC9F0','#80ED99',
];

let tasks = [];
let draggedId = null;
let editingTask = null;

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  buildSwatches();
  bindEvents();
  loadTasks();
});

function buildSwatches() {
  const container = document.getElementById('swatches');
  for (const c of STICKY_COLORS) {
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = c;
    sw.title = c;
    sw.addEventListener('click', () => {
      document.getElementById('task-color').value = c;
    });
    container.appendChild(sw);
  }
}

function bindEvents() {
  document.getElementById('btn-new').addEventListener('click', openNewModal);
  document.getElementById('btn-cancel').addEventListener('click', closeModal);
  document.getElementById('btn-save').addEventListener('click', saveTask);
  document.getElementById('btn-delete').addEventListener('click', deleteTask);
  document.getElementById('search').addEventListener('input', render);

  // Close modal when clicking backdrop
  document.getElementById('overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('overlay')) closeModal();
  });

  // Keyboard shortcut: Enter to save, Escape to close
  document.addEventListener('keydown', (e) => {
    const overlay = document.getElementById('overlay');
    if (overlay.style.display !== 'flex') return;
    if (e.key === 'Escape') closeModal();
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') saveTask();
  });

  // Drop zones
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
}

// ── API ───────────────────────────────────────────────────────────────────────

async function loadTasks() {
  const res = await fetch('/api/tasks');
  tasks = await res.json();
  render();
}

async function apiPut(id, data) {
  await fetch(`/api/tasks/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
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

// ── Render ────────────────────────────────────────────────────────────────────

function render() {
  const q = document.getElementById('search').value.toLowerCase();

  for (const col of ['todo', 'wip', 'done']) {
    const container = document.getElementById(`cards-${col}`);
    const filtered = tasks.filter(t =>
      t.column === col &&
      (!q || t.title.toLowerCase().includes(q) || t.assignee.toLowerCase().includes(q))
    );

    container.innerHTML = '';
    for (const task of filtered) {
      container.appendChild(createCard(task));
    }
    document.getElementById(`count-${col}`).textContent = filtered.length;
  }
}

function createCard(task) {
  const card = document.createElement('div');
  card.className = 'card';
  card.draggable = true;
  card.dataset.id = task.id;
  card.style.background = task.color;

  const topBg = darken(task.color, 0.2);

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

  // Drag events
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

  // Edit button
  card.querySelector('.card-edit-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    openEditModal(task);
  });

  // Click anywhere on card
  card.addEventListener('click', () => openEditModal(task));

  return card;
}

function buildDeadlineHtml(deadline) {
  if (!deadline) return '';
  const days = daysRemaining(deadline);
  let cls = 'dl-ok';
  let extra = '';

  if (days === null) {
    cls = '';
  } else if (days < 0) {
    cls = 'dl-overdue';
    extra = ` (期限切れ ${Math.abs(days)}日)`;
  } else if (days === 0) {
    cls = 'dl-warn';
    extra = ' (本日期限!)';
  } else if (days <= 3) {
    cls = 'dl-warn';
    extra = ` (残り${days}日)`;
  } else {
    extra = ` (残り${days}日)`;
  }

  return `<div class="card-deadline ${cls}">📅 ${esc(deadline)}${extra}</div>`;
}

// ── Drag & Drop ───────────────────────────────────────────────────────────────

async function handleDrop(e, targetCol) {
  e.preventDefault();
  document.querySelectorAll('.column').forEach(c => c.classList.remove('highlight'));

  if (!draggedId) return;
  const task = tasks.find(t => t.id === draggedId);
  if (!task || task.column === targetCol) return;

  task.column = targetCol;
  render();  // Optimistic update

  await apiPut(draggedId, task);
  draggedId = null;
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function openNewModal() {
  editingTask = null;
  document.getElementById('modal-title').textContent = '新規タスク';
  document.getElementById('task-id').value = '';
  document.getElementById('task-title').value = '';
  document.getElementById('task-assignee').value = '';
  document.getElementById('task-deadline').value = '';
  document.getElementById('task-note').value = '';
  document.getElementById('task-color').value = '#FFD166';
  document.getElementById('btn-delete').style.display = 'none';
  showModal();
}

function openEditModal(task) {
  editingTask = task;
  document.getElementById('modal-title').textContent = 'タスク編集';
  document.getElementById('task-id').value = task.id;
  document.getElementById('task-title').value = task.title;
  document.getElementById('task-assignee').value = task.assignee;
  document.getElementById('task-deadline').value = task.deadline;
  document.getElementById('task-note').value = task.note;
  document.getElementById('task-color').value = task.color;
  document.getElementById('btn-delete').style.display = 'inline-block';
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
  };

  if (editingTask) {
    const updated = { ...editingTask, ...data };
    Object.assign(editingTask, data);
    render();  // Optimistic
    await apiPut(editingTask.id, updated);
  } else {
    const created = await apiPost({ ...data, column: 'todo' });
    tasks.push(created);
    render();
  }

  closeModal();
}

async function deleteTask() {
  if (!editingTask) return;
  if (!confirm('このタスクを削除しますか？')) return;

  const id = editingTask.id;
  tasks = tasks.filter(t => t.id !== id);
  render();  // Optimistic
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

function daysRemaining(deadlineStr) {
  if (!deadlineStr) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dl = new Date(deadlineStr);
  return Math.round((dl - today) / 86400000);
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

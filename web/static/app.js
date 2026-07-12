// ============================================================
// STATE
// ============================================================
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const dpr = Math.max(1, window.devicePixelRatio || 1);

const PALETTE = ['#5EEAD4','#F2B84B','#F87171','#818CF8','#4ADE80','#F472B6','#60A5FA','#FBBF24','#C084FC','#2DD4BF'];

const state = {
  strokes: [],          // {id, colorHex, points:[{x,y}] in MATH coords, equations:[...], pending:bool}
  currentRaw: [],
  drawing: false,
  baseScale: 40,
  zoom: 1,
  panX: 0, panY: 0,
  selectedEqId: null,
  nextId: 1,
  animT: 0,
};

let originX = 0, originY = 0;

function resize() {
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  canvas.style.width = rect.width + 'px';
  canvas.style.height = rect.height + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  originX = rect.width / 2 + state.panX;
  originY = rect.height / 2 + state.panY;
  render();
}
window.addEventListener('resize', resize);

function toMath(px, py) {
  const s = state.baseScale * state.zoom;
  return { x: (px - originX) / s, y: -(py - originY) / s };
}
function toPixel(x, y) {
  const s = state.baseScale * state.zoom;
  return { px: originX + x * s, py: originY - y * s };
}

// ============================================================
// BACKEND CALL
// ============================================================
async function fitStrokeOnServer(mathPoints) {
  const res = await fetch('/api/fit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ points: mathPoints.map(p => ({ x: p.x, y: p.y })) }),
  });
  if (!res.ok) throw new Error(`fit request failed: ${res.status}`);
  const data = await res.json();
  return (data.equations || []).map(eq => ({
    id: state.nextId++,
    latex: eq.latex,
    domain: eq.domain,
    meta: eq.meta,
    range: eq.range,
  }));
}

// ============================================================
// RENDERING
// ============================================================
function drawGrid() {
  const rect = canvas.getBoundingClientRect();
  const w = rect.width, h = rect.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#0A0E1A';
  ctx.fillRect(0, 0, w, h);

  const s = state.baseScale * state.zoom;
  ctx.strokeStyle = '#161D38';
  ctx.lineWidth = 1;
  ctx.beginPath();
  const startX = originX % s, startY = originY % s;
  for (let x = startX; x < w; x += s) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
  for (let y = startY; y < h; y += s) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
  ctx.stroke();

  ctx.strokeStyle = '#313C67';
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(0, originY); ctx.lineTo(w, originY);
  ctx.moveTo(originX, 0); ctx.lineTo(originX, h);
  ctx.stroke();

  ctx.fillStyle = '#545F87';
  ctx.font = '10px "JetBrains Mono", monospace';
  const step = state.zoom < 0.6 ? 5 : (state.zoom > 1.8 ? 1 : 2);
  for (let ux = -40; ux <= 40; ux += step) {
    if (ux === 0) continue;
    const { px } = toPixel(ux, 0);
    if (px < 0 || px > w) continue;
    ctx.fillText(String(ux), px + 3, originY + 13);
  }
  for (let uy = -40; uy <= 40; uy += step) {
    if (uy === 0) continue;
    const { py } = toPixel(0, uy);
    if (py < 0 || py > h) continue;
    ctx.fillText(String(uy), originX + 5, py - 3);
  }
}

function pathFromPoints(points, range) {
  const [s, e] = range || [0, points.length - 1];
  return points.slice(s, e + 1).map(p => toPixel(p.x, p.y));
}

function render() {
  drawGrid();
  for (const stroke of state.strokes) {
    const pixels = stroke.points.map(p => toPixel(p.x, p.y));
    ctx.strokeStyle = stroke.colorHex;
    ctx.globalAlpha = stroke.pending ? 0.45 : 0.9;
    ctx.lineWidth = 2.25;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.beginPath();
    pixels.forEach((p, i) => i === 0 ? ctx.moveTo(p.px, p.py) : ctx.lineTo(p.px, p.py));
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  if (state.selectedEqId != null) {
    const found = findEquation(state.selectedEqId);
    if (found) {
      const { stroke, eq } = found;
      const pixels = pathFromPoints(stroke.points, eq.range);
      ctx.save();
      ctx.strokeStyle = '#F2B84B';
      ctx.lineWidth = 5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.shadowColor = '#F2B84B';
      ctx.shadowBlur = 14;
      ctx.setLineDash([9, 7]);
      ctx.lineDashOffset = -state.animT;
      ctx.beginPath();
      pixels.forEach((p, i) => i === 0 ? ctx.moveTo(p.px, p.py) : ctx.lineTo(p.px, p.py));
      ctx.stroke();
      ctx.restore();
    }
  }

  if (state.drawing && state.currentRaw.length > 1) {
    ctx.strokeStyle = '#E7ECFA';
    ctx.globalAlpha = 0.55;
    ctx.lineWidth = 2.25;
    ctx.lineCap = 'round';
    ctx.beginPath();
    state.currentRaw.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
}

function findEquation(id) {
  for (const stroke of state.strokes) {
    for (const eq of stroke.equations || []) {
      if (eq.id === id) return { stroke, eq };
    }
  }
  return null;
}

let animRunning = false;
function animLoop() {
  if (state.selectedEqId == null) { animRunning = false; return; }
  state.animT = (state.animT + 0.4) % 1000;
  render();
  requestAnimationFrame(animLoop);
}
function startAnim() {
  if (!animRunning) { animRunning = true; requestAnimationFrame(animLoop); }
}

// ============================================================
// SIDEBAR
// ============================================================
function renderSidebar() {
  const list = document.getElementById('eq-list');
  const total = state.strokes.reduce((s, st) => s + (st.equations || []).length, 0);
  document.getElementById('eq-count').textContent = total;
  document.getElementById('undo-btn').disabled = state.strokes.length === 0;
  document.getElementById('clear-btn').disabled = state.strokes.length === 0;

  if (state.strokes.length === 0) {
    list.innerHTML = `<div id="empty-state"><span class="big">nothing plotted yet</span>draw a curve on the canvas and its equation will show up here. click an equation to highlight its line.</div>`;
    return;
  }

  list.innerHTML = '';
  state.strokes.forEach((stroke, si) => {
    const group = document.createElement('div');
    group.className = 'stroke-group';
    const label = document.createElement('div');
    label.className = 'stroke-label';
    if (stroke.pending) {
      label.innerHTML = `<span class="swatch" style="background:${stroke.colorHex}"></span> line ${si + 1} · fitting…`;
      group.appendChild(label);
      list.appendChild(group);
      return;
    }
    label.innerHTML = `<span class="swatch" style="background:${stroke.colorHex}"></span> line ${si + 1}${(stroke.equations||[]).length > 1 ? ` · ${stroke.equations.length} segments` : ''}`;
    group.appendChild(label);

    (stroke.equations || []).forEach(eq => {
      const card = document.createElement('div');
      card.className = 'eq-card' + (state.selectedEqId === eq.id ? ' selected' : '');
      card.style.borderLeftColor = state.selectedEqId === eq.id ? stroke.colorHex : 'transparent';
      card.innerHTML = `
        <div class="eq-main" style="color:${state.selectedEqId===eq.id ? '#F2B84B' : '#E7ECFA'}">${escapeHtml(eq.latex)}</div>
        <div class="eq-domain">${escapeHtml(eq.domain)}</div>
        <div class="eq-meta">${escapeHtml(eq.meta)}</div>
      `;
      card.addEventListener('click', () => {
        state.selectedEqId = state.selectedEqId === eq.id ? null : eq.id;
        renderSidebar();
        render();
        if (state.selectedEqId != null) startAnim();
      });
      group.appendChild(card);
    });
    list.appendChild(group);
  });
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ============================================================
// INPUT HANDLING
// ============================================================
function getPos(e) {
  const rect = canvas.getBoundingClientRect();
  const p = e.touches ? e.touches[0] : e;
  return { x: p.clientX - rect.left, y: p.clientY - rect.top };
}

canvas.addEventListener('pointerdown', (e) => {
  state.drawing = true;
  state.currentRaw = [getPos(e)];
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener('pointermove', (e) => {
  if (!state.drawing) return;
  state.currentRaw.push(getPos(e));
  render();
});
canvas.addEventListener('pointerup', () => finishStroke());
canvas.addEventListener('pointercancel', () => finishStroke());

async function finishStroke() {
  if (!state.drawing) return;
  state.drawing = false;
  if (state.currentRaw.length < 4) { state.currentRaw = []; render(); return; }
  const mathPts = state.currentRaw.map(p => toMath(p.x, p.y));
  const stroke = {
    id: state.nextId++,
    colorHex: PALETTE[state.strokes.length % PALETTE.length],
    points: mathPts,
    equations: [],
    pending: true,
  };
  state.strokes.push(stroke);
  state.currentRaw = [];
  document.getElementById('hint').style.opacity = '0';
  renderSidebar();
  render();

  try {
    stroke.equations = await fitStrokeOnServer(mathPts);
  } catch (err) {
    console.error(err);
    stroke.equations = [];
  } finally {
    stroke.pending = false;
    renderSidebar();
    render();
  }
}

canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const factor = e.deltaY < 0 ? 1.08 : 1 / 1.08;
  applyZoom(factor);
}, { passive: false });

function applyZoom(factor) {
  state.zoom = Math.min(4, Math.max(0.25, state.zoom * factor));
  document.getElementById('zoom-label').textContent = Math.round(state.zoom * 100) + '%';
  render();
}

document.getElementById('zoom-in').addEventListener('click', () => applyZoom(1.2));
document.getElementById('zoom-out').addEventListener('click', () => applyZoom(1 / 1.2));
document.getElementById('zoom-reset').addEventListener('click', () => {
  state.zoom = 1; state.panX = 0; state.panY = 0;
  document.getElementById('zoom-label').textContent = '100%';
  resize();
});

document.getElementById('undo-btn').addEventListener('click', () => {
  if (state.strokes.length === 0) return;
  const removed = state.strokes.pop();
  if ((removed.equations || []).some(eq => eq.id === state.selectedEqId)) state.selectedEqId = null;
  renderSidebar();
  render();
});
document.getElementById('clear-btn').addEventListener('click', () => {
  state.strokes = [];
  state.selectedEqId = null;
  renderSidebar();
  render();
});

window.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'z') { e.preventDefault(); document.getElementById('undo-btn').click(); }
});

resize();
renderSidebar();

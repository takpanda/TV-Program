"use strict";

/* ── Constants ── */
const SLOT_PX_DEFAULT = 72;  // fallback px per 30-minute slot
const DAYS     = ['月','火','水','木','金','土','日'];
const WKND_SET = new Set(['土','日']);

/* Day header colors */
const DAY_COLORS = {
  '月': '#1565c0',
  '火': '#c62828',
  '水': '#2e7d32',
  '木': '#e65100',
  '金': '#6a1b9a',
  '土': '#0277bd',
  '日': '#b71c1c',
};

/* ── Helpers ── */
function getTodayDay() {
  return ['日','月','火','水','木','金','土'][new Date().getDay()];
}

function getNowMinutes() {
  const d = new Date();
  return d.getHours() * 60 + d.getMinutes();
}

function toMins(t) {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

function fmtHHMM(mins) {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function el(tag, cls) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  return e;
}

/**
 * Greedy interval-graph coloring with per-cluster totalCols.
 */
function assignColumns(progs) {
  if (!progs.length) return [];

  const n      = progs.length;
  const cols   = new Array(n).fill(0);
  const starts = progs.map(p => toMins(p.startTime));
  const ends   = progs.map(p => toMins(p.endTime));

  const parent = Array.from({length: n}, (_, i) => i);
  function find(x) { return parent[x] === x ? x : (parent[x] = find(parent[x])); }
  function union(x, y) { parent[find(x)] = find(y); }

  for (let i = 0; i < n; i++)
    for (let j = i+1; j < n; j++)
      if (starts[i] < ends[j] && starts[j] < ends[i]) union(i, j);

  const groups = {};
  for (let i = 0; i < n; i++) {
    const r = find(i);
    (groups[r] = groups[r] || []).push(i);
  }

  const totalColsMap = new Array(n).fill(1);
  for (const members of Object.values(groups)) {
    const sorted = [...members].sort((a, b) => starts[a] - starts[b]);
    for (const i of sorted) {
      const used = new Set();
      for (const j of members)
        if (j !== i && starts[i] < ends[j] && starts[j] < ends[i]) used.add(cols[j]);
      let c = 0;
      while (used.has(c)) c++;
      cols[i] = c;
    }
    const maxC = Math.max(...members.map(i => cols[i]), 0);
    members.forEach(i => { totalColsMap[i] = maxC + 1; });
  }

  return progs.map((_, i) => ({ col: cols[i], totalCols: totalColsMap[i] }));
}

/* ── Ticker Banner builder ── */
function buildTicker(items) {
  if (!items || !items.length) return;

  const wrap = document.getElementById('ticker-wrap');
  if (!wrap) return;
  wrap.className = 'ticker-wrap';

  const label = document.createElement('div');
  label.className = 'ticker-label';
  label.textContent = '💬 口コミ';
  wrap.appendChild(label);

  const trackWrap = document.createElement('div');
  trackWrap.className = 'ticker-track-wrap';

  const track = document.createElement('div');
  track.className = 'ticker-track';

  [...items, ...items].forEach((item) => {
    const span = document.createElement('span');
    span.className = 'ticker-item';
    span.innerHTML =
      `<span class="ticker-item-title ${escHtml(item.sentiment || 'positive')}">【${escHtml(item.title)}】</span>` +
      escHtml(item.text) +
      `<span class="ticker-sep">｜</span>`;
    track.appendChild(span);
  });

  trackWrap.appendChild(track);
  wrap.appendChild(trackWrap);
}

/* ── Ranking Panel builder ── */
function buildRanking(data) {
  const { channels, ranking } = data;
  if (!ranking || !ranking.length) return;

  const chMap = Object.fromEntries(channels.map(c => [c.id, c]));
  const panel = document.getElementById('ranking-panel');
  if (!panel) return;

  const title = document.createElement('div');
  title.className = 'ranking-panel-title';
  title.textContent = '🏆 話題のドラマ TOP 10';
  panel.appendChild(title);

  const MEDALS = ['medal-gold', 'medal-silver', 'medal-bronze'];

  ranking.forEach(item => {
    const ch = chMap[item.channel] || { name: item.channel, color: '#8c959f' };
    const badgeCls = item.rank <= 3 ? MEDALS[item.rank - 1] : 'rank-normal';

    const card = document.createElement('div');
    card.className = 'rank-card';
    card.title = `${item.rank}位 ${item.title}（${ch.name}）`;

    card.innerHTML =
      `<div class="rank-badge ${escHtml(badgeCls)}">${escHtml(String(item.rank))}</div>` +
      `<div class="rank-card-body">` +
        `<div class="rank-title">${escHtml(item.title)}</div>` +
        `<span class="rank-ch" style="background:${escHtml(ch.color)}">${escHtml(ch.name)}</span>` +
      `</div>`;

    panel.appendChild(card);
  });
}

/* ── Main builder ── */
function buildSchedule(data) {
  const rankPanel = document.getElementById('ranking-panel');
  if (rankPanel) rankPanel.innerHTML = '';

  const { settings, channels, programs } = data;

  buildRanking(data);

  /* Fixed time range: 20:00〜24:00（23時台まで） */
  const slotMins   = settings.slotMinutes ?? 30;
  const nowMin     = getNowMinutes();
  const startMin   = 20 * 60;
  const endMin     = 24 * 60;
  const totalSlots = (endMin - startMin) / slotMins;

  /* Dynamically calculate slot height to fill the schedule-wrapper */
  const sw = document.querySelector('.schedule-wrapper');
  const availH = sw ? sw.clientHeight : 600;
  const DAY_HDR_H = 48;
  const SLOT_PX = Math.max(36, Math.floor((availH - DAY_HDR_H - 4) / totalSlots));

  const totalPx    = totalSlots * SLOT_PX;

  /* Page title */
  const titleStr = settings.title || '週間テレビ番組表';
  document.getElementById('app-title').textContent = titleStr;
  document.title = titleStr;

  /* Date label */
  const d = new Date();
  document.getElementById('date-label').textContent =
    `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日（${getTodayDay()}）`;

  /* Channel map */
  const chMap = Object.fromEntries(channels.map(c => [c.id, c]));

  /* Legend */
  document.getElementById('legend-wrap').innerHTML =
    `<div class="legend">
      <span class="legend-label">チャンネル :</span>
      ${channels.map(c =>
        `<div class="legend-item">
          <div class="legend-dot" style="background:${escHtml(c.color)}"></div>
          <span>${escHtml(c.name)}</span>
        </div>`
      ).join('')}
    </div>`;

  const flex    = document.getElementById('schedule-flex');
  flex.innerHTML = '';
  const today   = getTodayDay();
  const todayIdx    = DAYS.indexOf(today);
  const orderedDays = todayIdx >= 0
    ? [...DAYS.slice(todayIdx), ...DAYS.slice(0, todayIdx)]
    : DAYS;

  /* ── Time column ── */
  const tcWrap = el('div', 'time-col-wrap');
  tcWrap.appendChild(el('div', 'time-col-spacer'));

  const tc = el('div', 'time-col');
  tc.style.height = totalPx + 'px';

  for (let i = 0; i <= totalSlots; i++) {
    const mins = startMin + i * slotMins;
    const isHr = (mins % 60 === 0);
    const tick = el('div', 'time-tick ' + (isHr ? 'hour-mark' : 'half-mark'));
    tick.style.top = (i * SLOT_PX) + 'px';
    tick.textContent = isHr ? String(Math.floor(mins / 60)) : '30';
    tc.appendChild(tick);
  }
  tcWrap.appendChild(tc);
  flex.appendChild(tcWrap);

  /* ── Day columns ── */
  orderedDays.forEach(day => {
    const isToday  = day === today;
    const isWknd   = WKND_SET.has(day);
    const dayColor = DAY_COLORS[day] || '#607d8b';
    const hdrBg    = isToday ? dayColor : (isWknd ? dayColor + 'cc' : dayColor + 'dd');

    const wrap = el('div', 'day-col-wrap');

    /* Header */
    const hdr = el('div', 'day-header' + (isToday ? ' today' : ''));
    hdr.style.background = hdrBg;
    hdr.textContent = day + '曜';
    if (isToday) hdr.style.boxShadow = `inset 0 -3px 0 rgba(255,255,255,0.35)`;
    wrap.appendChild(hdr);

    /* Body */
    const bodyCls = 'day-body' + (isToday ? ' today' : '') + (isWknd ? ' wknd' : '');
    const body = el('div', bodyCls);
    body.style.height = totalPx + 'px';
    if (isToday) body.style.borderColor = dayColor;

    /* Grid lines */
    for (let i = 0; i <= totalSlots; i++) {
      const line = el('div', 'grid-line ' + (i % 2 === 0 ? 'hour' : 'half'));
      line.style.top = (i * SLOT_PX) + 'px';
      body.appendChild(line);
    }

    /* Current time line (today only) */
    if (isToday && nowMin >= startMin && nowMin <= endMin) {
      const ctl = el('div', 'current-time-line');
      ctl.style.top = ((nowMin - startMin) / slotMins * SLOT_PX) + 'px';
      body.appendChild(ctl);
    }

    /* Programs */
    const dayProgs = programs
      .filter(p => p.day === day)
      .filter(p => toMins(p.endTime) > startMin && toMins(p.startTime) < endMin)
      .sort((a, b) => toMins(a.startTime) - toMins(b.startTime));

    const colInfo = assignColumns(dayProgs);

    dayProgs.forEach((prog, idx) => {
      const s   = Math.max(toMins(prog.startTime), startMin);
      const e   = Math.min(toMins(prog.endTime),   endMin);
      const top = (s - startMin) / slotMins * SLOT_PX;
      const ht  = (e - s)        / slotMins * SLOT_PX - 2;

      const { col, totalCols } = colInfo[idx];
      const wPct = 100 / totalCols;
      const lPct = col * wPct;

      const ch = chMap[prog.channel] || { name: prog.channel, color: '#8c959f' };

      const card = el('div', 'program-card');
      card.style.top             = top + 'px';
      card.style.height          = ht  + 'px';
      card.style.left            = lPct + '%';
      card.style.width           = `calc(${wPct}% - 2px)`;
      card.style.borderLeftColor = ch.color;
      card.title =
        `${prog.title}\n${prog.startTime}〜${prog.endTime}  ${ch.name}` +
        (prog.memo ? `\n📝 ${prog.memo}` : '');

      let inner = `<div class="prog-start">${escHtml(fmtHHMM(toMins(prog.startTime)))}</div>`;
      inner    += `<div class="prog-title">${escHtml(prog.title)}</div>`;
      if (ht >= 36) {
        inner += `<span class="prog-ch" style="background:${escHtml(ch.color)}">${escHtml(ch.name)}</span>`;
      }
      if (prog.memo && ht >= 60) {
        inner += `<div class="prog-memo">${escHtml(prog.memo)}</div>`;
      }
      card.innerHTML = inner;

      body.appendChild(card);
    });

    wrap.appendChild(body);
    flex.appendChild(wrap);
  });
}

/* ── Boot ── */
const DEFAULT_REFRESH_INTERVAL = 60 * 1000;
let autoTimer = null;
let refreshInProgress = false;

function setRefreshStatus(msg, isError) {
  const el = document.getElementById('refresh-status');
  if (el) { el.textContent = msg || ''; el.style.color = isError ? '#cf222e' : '#54707a'; }
}

function clearTickerAndRanking() {
  const tw = document.getElementById('ticker-wrap'); if (tw) tw.innerHTML = '';
  const rp = document.getElementById('ranking-panel'); if (rp) rp.innerHTML = '';
  const lg = document.getElementById('legend-wrap'); if (lg) lg.innerHTML = '';
}

function fetchAndRender() {
  if (refreshInProgress) return Promise.resolve();
  refreshInProgress = true;
  const btn = document.getElementById('refresh-btn');
  if (btn) { btn.disabled = true; btn.textContent = '更新中…'; }
  setRefreshStatus('読み込み中…');

  const scrollY = window.scrollY || 0;
  const sw = document.querySelector('.schedule-wrapper');
  const scheduleScroll = sw ? sw.scrollLeft : 0;

  clearTickerAndRanking();

  return Promise.all([
    fetch('programs.json').then(r => { if (!r.ok) throw new Error(`HTTP ${r.status} — programs.json を取得できません`); return r.json(); }),
    fetch('kuchikomi.json').then(r => { if (!r.ok) throw new Error(`HTTP ${r.status} — kuchikomi.json を取得できません`); return r.json(); })
  ])
  .then(([programsData, kuchikoiData]) => {
    buildSchedule(programsData);
    buildTicker(kuchikoiData);
    if (sw) sw.scrollLeft = scheduleScroll;
    window.scrollTo(0, scrollY);
    setRefreshStatus('更新完了');
  })
  .catch(err => {
    const container = document.getElementById('schedule-flex');
    if (container) container.innerHTML =
      `<div class="error-box">
        <h2>データを読み込めませんでした</h2>
        <p>このファイルはローカルサーバー経由で開く必要があります。<br>
        ターミナルで以下を実行してください:</p>
        <code>python3 -m http.server 8000</code>
        <p>起動後、<a href="http://localhost:8000">http://localhost:8000</a> にアクセスしてください。</p>
        <p style="margin-top:12px;font-size:11px;color:#8c959f">詳細: ${escHtml(err.message)}</p>
      </div>`;
    setRefreshStatus('データ取得エラー', true);
    console.error(err);
  })
  .finally(() => {
    refreshInProgress = false;
    if (btn) { btn.disabled = false; btn.textContent = '更新'; }
  });
}

function startAutoRefresh(intervalMs = DEFAULT_REFRESH_INTERVAL) {
  stopAutoRefresh();
  autoTimer = setInterval(() => { fetchAndRender(); }, intervalMs);
}
function stopAutoRefresh() { if (autoTimer) { clearInterval(autoTimer); autoTimer = null; } }

document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('refresh-btn');
  if (btn) btn.addEventListener('click', () => { fetchAndRender(); });

  const autoCheckbox = document.getElementById('auto-refresh');
  if (autoCheckbox) {
    autoCheckbox.addEventListener('change', (e) => {
      if (e.target.checked) { startAutoRefresh(); setRefreshStatus('自動更新: ON'); }
      else { stopAutoRefresh(); setRefreshStatus('自動更新: OFF'); }
    });
    if (autoCheckbox.checked) { startAutoRefresh(); setRefreshStatus('自動更新: ON'); }
  }

  window.addEventListener('focus', () => {
    const auto = document.getElementById('auto-refresh');
    if (auto && auto.checked) fetchAndRender();
  });

  fetchAndRender();
});

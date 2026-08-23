<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ApuestasMurcia · Marcador</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Teko:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root{
    --bg: #0a1f16;
    --surface: #103526;
    --surface-2: #16442f;
    --line: #244d38;
    --gold: #e8b430;
    --win: #4fae6f;
    --loss: #d6584a;
    --pending: #7c93a8;
    --ink: #f2efe4;
    --ink-muted: #93ac9e;
  }
  *{ box-sizing:border-box; }
  html{ scroll-behavior:smooth; }
  body{
    margin:0;
    background:
      radial-gradient(circle at 50% -10%, rgba(232,180,48,0.08), transparent 45%),
      repeating-linear-gradient(90deg, rgba(255,255,255,0.015) 0 2px, transparent 2px 140px),
      var(--bg);
    color:var(--ink);
    font-family:'Inter', sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  .wrap{ max-width:1080px; margin:0 auto; padding:32px 20px 80px; }

  header.board{
    background:linear-gradient(180deg, var(--surface-2), var(--surface));
    border:1px solid var(--line);
    border-radius:18px;
    padding:28px clamp(16px,4vw,40px);
    position:relative;
    overflow:hidden;
  }
  header.board::before{
    content:"";
    position:absolute; inset:0;
    background:repeating-linear-gradient(0deg, transparent 0 3px, rgba(0,0,0,0.15) 3px 4px);
    pointer-events:none; opacity:.4;
  }
  .board-top{
    display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:8px;
    position:relative; z-index:1;
  }
  .brand{
    font-family:'Teko', sans-serif; font-weight:700; letter-spacing:.04em;
    font-size:clamp(28px,4vw,38px); text-transform:uppercase; color:var(--ink);
  }
  .brand small{ display:block; font-family:'Inter'; font-weight:500; font-size:12px; letter-spacing:.12em; color:var(--ink-muted); text-transform:uppercase; }
  .updated{ font-size:12px; color:var(--ink-muted); font-family:'JetBrains Mono'; }

  .score-row{
    margin-top:22px; display:flex; align-items:flex-end; gap:clamp(20px,5vw,56px); flex-wrap:wrap;
    position:relative; z-index:1;
  }
  .score-main{ line-height:.85; }
  .score-main .amount{
    font-family:'JetBrains Mono', monospace; font-weight:700;
    font-size:clamp(40px,8vw,72px);
    text-shadow:0 0 18px currentColor;
  }
  .amount.pos{ color:var(--gold); }
  .amount.neg{ color:var(--loss); }
  .score-main .label{ font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:var(--ink-muted); margin-top:6px; }

  .tiles{ display:flex; gap:clamp(14px,4vw,28px); flex-wrap:wrap; }
  .tile .num{ font-family:'Teko'; font-weight:600; font-size:clamp(26px,4vw,34px); }
  .tile .lbl{ font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-muted); }
  .tile.win .num{ color:var(--win); }
  .tile.loss .num{ color:var(--loss); }
  .tile.pending .num{ color:var(--pending); }

  .controls{
    display:flex; gap:10px; flex-wrap:wrap; margin:26px 0 18px; align-items:center;
  }
  .controls select, .controls input{
    background:var(--surface); border:1px solid var(--line); color:var(--ink);
    border-radius:9px; padding:9px 12px; font-family:'Inter'; font-size:13px;
  }
  .controls input{ flex:1; min-width:160px; }
  .controls select:focus, .controls input:focus{ outline:2px solid var(--gold); outline-offset:1px; }
  .pill-group{ display:flex; gap:6px; }
  .pill{
    background:transparent; border:1px solid var(--line); color:var(--ink-muted);
    padding:8px 14px; border-radius:999px; font-size:12px; letter-spacing:.04em;
    cursor:pointer; font-family:'Inter'; font-weight:500;
  }
  .pill:hover{ border-color:var(--gold); color:var(--ink); }
  .pill.active{ background:var(--gold); border-color:var(--gold); color:#1a1207; }

  .table-card{
    background:var(--surface); border:1px solid var(--line); border-radius:14px; overflow:hidden;
  }
  table{ width:100%; border-collapse:collapse; font-size:13px; }
  thead th{
    text-align:left; padding:12px 14px; font-size:10px; letter-spacing:.1em; text-transform:uppercase;
    color:var(--ink-muted); border-bottom:1px solid var(--line); font-weight:600;
  }
  tbody td{ padding:12px 14px; border-bottom:1px solid rgba(255,255,255,0.04); vertical-align:top; }
  tbody tr:last-child td{ border-bottom:none; }
  tbody tr:hover{ background:rgba(255,255,255,0.02); }
  .match-cell strong{ display:block; font-weight:600; }
  .match-cell span{ color:var(--ink-muted); font-size:11px; }
  .odds{ font-family:'JetBrains Mono'; }
  .badge{
    display:inline-block; padding:3px 9px; border-radius:999px; font-size:10px;
    letter-spacing:.06em; text-transform:uppercase; font-weight:600; font-family:'Inter';
  }
  .badge.GANADA{ background:rgba(79,174,111,0.15); color:var(--win); }
  .badge.PERDIDA{ background:rgba(214,88,74,0.15); color:var(--loss); }
  .badge.PENDIENTE{ background:rgba(124,147,168,0.15); color:var(--pending); }
  .profit-cell{ font-family:'JetBrains Mono'; }
  .profit-cell.pos{ color:var(--win); }
  .profit-cell.neg{ color:var(--loss); }

  .section-title{
    font-family:'Teko'; font-weight:600; font-size:22px; letter-spacing:.03em; text-transform:uppercase;
    color:var(--ink-muted); margin:40px 0 14px;
  }
  .strategy-grid{ display:grid; grid-template-columns:repeat(auto-fill, minmax(200px,1fr)); gap:12px; }
  .strategy-card{
    background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:16px;
  }
  .strategy-card h4{ margin:0 0 10px; font-size:13px; font-weight:600; }
  .strategy-card .row{ display:flex; justify-content:space-between; font-size:12px; color:var(--ink-muted); margin-top:4px; }
  .strategy-card .row b{ color:var(--ink); font-weight:600; }

  .empty, .loading{ text-align:center; padding:60px 20px; color:var(--ink-muted); font-size:14px; }
  .empty code{ background:var(--surface-2); padding:2px 6px; border-radius:5px; }

  footer{ text-align:center; margin-top:40px; font-size:11px; color:var(--ink-muted); }
  footer a{ color:var(--gold); text-decoration:none; }

  @media (prefers-reduced-motion: reduce){ html{ scroll-behavior:auto; } }
</style>
</head>
<body>
<div class="wrap">

  <header class="board">
    <div class="board-top">
      <div class="brand">ApuestasMurcia<small>Marcador de señales</small></div>
      <div class="updated" id="updated">cargando…</div>
    </div>
    <div class="score-row">
      <div class="score-main">
        <div class="amount" id="totalProfit">—</div>
        <div class="label">Ganancia acumulada (COP)</div>
      </div>
      <div class="tiles">
        <div class="tile win"><div class="num" id="tWon">0</div><div class="lbl">Ganadas</div></div>
        <div class="tile loss"><div class="num" id="tLost">0</div><div class="lbl">Perdidas</div></div>
        <div class="tile pending"><div class="num" id="tPending">0</div><div class="lbl">Pendientes</div></div>
        <div class="tile"><div class="num" id="tEff">0%</div><div class="lbl">Efectividad</div></div>
      </div>
    </div>
  </header>

  <div class="controls">
    <div class="pill-group" id="periodPills">
      <button class="pill active" data-period="all">Todo</button>
      <button class="pill" data-period="today">Hoy</button>
      <button class="pill" data-period="week">7 días</button>
      <button class="pill" data-period="month">Este mes</button>
    </div>
    <select id="strategyFilter"><option value="">Todas las estrategias</option></select>
    <select id="resultFilter">
      <option value="">Todos los resultados</option>
      <option value="GANADA">Ganadas</option>
      <option value="PERDIDA">Perdidas</option>
      <option value="PENDIENTE">Pendientes</option>
    </select>
    <input type="text" id="searchBox" placeholder="Buscar equipo o liga…">
  </div>

  <div class="table-card">
    <table>
      <thead>
        <tr>
          <th>#</th><th>Partido</th><th>Estrategia</th><th>Cuota</th><th>Resultado</th><th>Ganancia</th>
        </tr>
      </thead>
      <tbody id="tableBody"></tbody>
    </table>
    <div class="empty" id="emptyState" style="display:none;">
      Sin señales que coincidan con el filtro actual.
    </div>
    <div class="loading" id="loadingState">Cargando <code>signals.json</code>…</div>
  </div>

  <div class="section-title">Por estrategia</div>
  <div class="strategy-grid" id="strategyGrid"></div>

  <footer id="footerNote"></footer>
</div>

<script>
const CONFIG = {
  repo: new URLSearchParams(location.search).get('repo') || 'usuario/repositorio',
  branch: new URLSearchParams(location.search).get('branch') || 'main',
  file: 'signals.json'
};

const state = { signals: [], period: 'all', strategy: '', result: '', search: '' };

function fmtMoney(n){
  const sign = n < 0 ? '-' : '';
  return sign + '$' + Math.abs(Math.round(n)).toLocaleString('es-CO');
}

function withinPeriod(signal, period){
  if(period === 'all') return true;
  const dt = new Date(signal.registered_at.replace(' ', 'T') + 'Z');
  if(isNaN(dt)) return false;
  const now = new Date();
  if(period === 'today'){
    return dt.toISOString().slice(0,10) === now.toISOString().slice(0,10);
  }
  if(period === 'week'){
    return (now - dt) <= 7*24*60*60*1000;
  }
  if(period === 'month'){
    return dt.getUTCFullYear() === now.getUTCFullYear() && dt.getUTCMonth() === now.getUTCMonth();
  }
  return true;
}

function applyFilters(){
  return state.signals.filter(s => {
    if(!withinPeriod(s, state.period)) return false;
    if(state.strategy && s.strategy !== state.strategy) return false;
    if(state.result && s.result !== state.result) return false;
    if(state.search){
      const hay = (s.match + ' ' + s.league).toLowerCase();
      if(!hay.includes(state.search.toLowerCase())) return false;
    }
    return true;
  });
}

function computeStats(list){
  const won = list.filter(s => s.result === 'GANADA').length;
  const lost = list.filter(s => s.result === 'PERDIDA').length;
  const pending = list.filter(s => s.result === 'PENDIENTE').length;
  const finished = won + lost;
  const eff = finished ? (won/finished*100) : 0;
  const profit = list.reduce((a,s) => a + (s.profit || 0), 0);
  return {won, lost, pending, eff, profit, total:list.length};
}

function render(){
  const filtered = applyFilters();
  const stats = computeStats(filtered);

  const amountEl = document.getElementById('totalProfit');
  amountEl.textContent = fmtMoney(stats.profit);
  amountEl.className = 'amount ' + (stats.profit >= 0 ? 'pos' : 'neg');

  document.getElementById('tWon').textContent = stats.won;
  document.getElementById('tLost').textContent = stats.lost;
  document.getElementById('tPending').textContent = stats.pending;
  document.getElementById('tEff').textContent = stats.eff.toFixed(1) + '%';

  const tbody = document.getElementById('tableBody');
  tbody.innerHTML = '';
  const sorted = [...filtered].sort((a,b) => (b.registered_at || '').localeCompare(a.registered_at || ''));

  for(const s of sorted){
    const tr = document.createElement('tr');
    const profitClass = (s.profit || 0) > 0 ? 'pos' : (s.profit || 0) < 0 ? 'neg' : '';
    tr.innerHTML = `
      <td>#${s.id}</td>
      <td class="match-cell"><strong>${s.match || 'N/D'}</strong><span>${s.league || ''} · ${s.date || ''}</span></td>
      <td>${s.strategy || 'SIN ESTRATEGIA'}</td>
      <td class="odds">${s.odds ? s.odds.toFixed(2) : 'N/D'}</td>
      <td><span class="badge ${s.result}">${s.result}</span></td>
      <td class="profit-cell ${profitClass}">${fmtMoney(s.profit || 0)}</td>
    `;
    tbody.appendChild(tr);
  }

  document.getElementById('emptyState').style.display = filtered.length ? 'none' : 'block';

  const grid = document.getElementById('strategyGrid');
  grid.innerHTML = '';
  const byStrategy = {};
  for(const s of filtered){
    const key = s.strategy || 'SIN ESTRATEGIA';
    (byStrategy[key] = byStrategy[key] || []).push(s);
  }
  for(const [name, items] of Object.entries(byStrategy)){
    const st = computeStats(items);
    const card = document.createElement('div');
    card.className = 'strategy-card';
    card.innerHTML = `
      <h4>${name}</h4>
      <div class="row"><span>Señales</span><b>${st.total}</b></div>
      <div class="row"><span>Efectividad</span><b>${st.eff.toFixed(1)}%</b></div>
      <div class="row"><span>Ganancia</span><b>${fmtMoney(st.profit)}</b></div>
    `;
    grid.appendChild(card);
  }
}

function populateStrategyFilter(){
  const sel = document.getElementById('strategyFilter');
  const strategies = [...new Set(state.signals.map(s => s.strategy || 'SIN ESTRATEGIA'))].sort();
  for(const s of strategies){
    const opt = document.createElement('option');
    opt.value = s; opt.textContent = s;
    sel.appendChild(opt);
  }
}

async function loadData(){
  const url = `https://raw.githubusercontent.com/${CONFIG.repo}/${CONFIG.branch}/${CONFIG.file}`;
  try{
    const res = await fetch(url, { cache: 'no-store' });
    if(!res.ok) throw new Error('HTTP ' + res.status);
    state.signals = await res.json();
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('updated').textContent = 'Actualizado ' + new Date().toLocaleString('es-CO');
    populateStrategyFilter();
    render();
  }catch(err){
    document.getElementById('loadingState').innerHTML =
      `No se pudo cargar <code>${CONFIG.file}</code> desde <code>${CONFIG.repo}</code>.<br>` +
      `Verifica que el repositorio sea público y que la rama/nombre de archivo sean correctos.`;
    console.error(err);
  }
}

document.getElementById('periodPills').addEventListener('click', e => {
  if(!e.target.matches('.pill')) return;
  document.querySelectorAll('#periodPills .pill').forEach(p => p.classList.remove('active'));
  e.target.classList.add('active');
  state.period = e.target.dataset.period;
  render();
});
document.getElementById('strategyFilter').addEventListener('change', e => { state.strategy = e.target.value; render(); });
document.getElementById('resultFilter').addEventListener('change', e => { state.result = e.target.value; render(); });
document.getElementById('searchBox').addEventListener('input', e => { state.search = e.target.value; render(); });

document.getElementById('footerNote').innerHTML =
  `Leyendo <code>${CONFIG.file}</code> de <a href="https://github.com/${CONFIG.repo}" target="_blank">${CONFIG.repo}</a> (rama ${CONFIG.branch})`;

loadData();
</script>
</body>
</html>

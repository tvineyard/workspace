(() => {
  // Every roster is bundled in the page (data/rosters.seed.js), so nothing is
  // fetched at runtime. window.VOL_ROSTERS is {sport: {season: [names]}}.
  const DATA = window.VOL_ROSTERS || {};

  const SPORTS = {
    football:   {label: 'Football',   start: 1990, end: 2026, span: false, min: 20},
    basketball: {label: 'Basketball', start: 1990, end: 2025, span: true,  min: 8},
  };

  let sport = localStorage.getItem('nav_sport') || 'football';
  if (!SPORTS[sport] || !DATA[sport]) sport = Object.keys(SPORTS).find(s => DATA[s]) || 'football';

  const cfg = () => SPORTS[sport];
  const rosters = () => DATA[sport] || {};
  const allYears = () => {
    const c = cfg();
    return Array.from({length: c.end - c.start + 1}, (_, i) => String(c.start + i));
  };
  // Basketball seasons straddle two calendar years and are named that way.
  const displayYear = y => cfg().span ? `${y}-${String(Number(y) + 1).slice(-2)}` : y;
  const hasRoster = y => { const r = rosters()[y]; return Array.isArray(r) && r.length >= cfg().min; };
  const playableYears = () => allYears().filter(hasRoster);

  const maxAttempts = 3;
  const MIN_QUERY_LETTERS = 5;   // letters (spaces ignored) required before suggesting

  let mode = localStorage.getItem('nav_mode') || 'endless';
  let currentYear = null, attempts = 0, finished = false;
  let activeSuggestion = -1, visibleSuggestions = [], playerIndex = [];

  const $ = s => document.querySelector(s);
  const yearEl = $('#year'), input = $('#player'), form = $('#guessForm');
  const message = $('#message'), answer = $('#answer'), actions = $('#actions');
  const streakEl = $('#streak'), scoreEl = $('#score'), seasonCountEl = $('#seasonCount');
  const suggestionsEl = $('#suggestions'), indexStatus = $('#indexStatus'), submitBtn = $('#submitBtn');
  const nameInput = $('#playerName'), boardList = $('#boardList');
  const importBox = $('#importBox'), importBtn = $('#importBtn'), importNote = $('#importNote');

  function normalize(s) {
    return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/&/g, 'and').replace(/[’']/g, '')
      .replace(/\b(jr|sr|ii|iii|iv)\b\.?/g, '')
      .replace(/[^a-z0-9]/g, ' ').replace(/\s+/g, ' ').trim();
  }

  // ---- per-sport progress ---------------------------------------------------
  const key = k => `nav_${k}_${sport}`;
  let stats = {streak: 0, score: 0};
  function loadStats() {
    stats = {
      streak: Number(localStorage.getItem(key('streak')) || 0),
      score:  Number(localStorage.getItem(key('score'))  || 0),
    };
  }
  function saveStats() {
    localStorage.setItem(key('streak'), stats.streak);
    localStorage.setItem(key('score'), stats.score);
  }

  // Player identity for the no-repeat rule is the normalized name. utsports
  // publishes an athlete id per bio URL, but those ids are not stable across
  // seasons (Arian Foster is 14775 for 2004-2007 and 14267 for 2008), so keying
  // on id would let the same player be used once per id - the exact bug this
  // rule prevents. data/athlete-ids.json keeps the ids for reference.
  const playerKey = name => 'nm:' + normalize(name);

  // Players already answered correctly this run. Cleared when the streak breaks.
  let used = new Set();
  function loadUsed() {
    used = new Set();
    try { const r = JSON.parse(localStorage.getItem(key('used')) || '[]'); if (Array.isArray(r)) used = new Set(r); } catch {}
  }
  const saveUsed = () => { try { localStorage.setItem(key('used'), JSON.stringify([...used])); } catch {} };
  const unusedIn = y => (rosters()[y] || []).filter(n => !used.has(playerKey(n)));

  // ---- leaderboard ----------------------------------------------------------
  // A static page has no server, so the board is built from this browser's own
  // bests plus results friends paste in. Share text carries a NAV1 line the
  // import box reads back.
  const loadBoard = () => { try { return JSON.parse(localStorage.getItem('nav_board') || '{}'); } catch { return {}; } };
  const saveBoard = b => { try { localStorage.setItem('nav_board', JSON.stringify(b)); } catch {} };
  const cleanName = n => String(n || '').replace(/[|\r\n]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 24);
  const myName = () => cleanName(localStorage.getItem('nav_name') || '');

  function recordBest() {
    const nm = myName();
    if (!nm) return;
    const b = loadBoard(), k = normalize(nm) + '|' + sport;
    const cur = b[k];
    if (!cur || stats.streak > cur.streak || (stats.streak === cur.streak && stats.score > cur.score)) {
      b[k] = {name: nm, sport, streak: stats.streak, score: stats.score};
      saveBoard(b);
    }
    renderBoard();
  }

  function renderBoard() {
    if (!boardList) return;
    const rows = Object.values(loadBoard()).filter(e => e.sport === sport)
      .sort((a, b) => b.streak - a.streak || b.score - a.score || a.name.localeCompare(b.name));
    if (!rows.length) {
      boardList.innerHTML = '<li class="board-empty">No results yet. Win a round to get on the board.</li>';
      return;
    }
    const me = normalize(myName());
    boardList.innerHTML = rows.map((e, i) => {
      const mine = normalize(e.name) === me && me;
      return `<li class="${mine ? 'is-me' : ''}"><span class="rank">${i + 1}</span>` +
             `<span class="who">${escapeHtml(e.name)}${mine ? ' (you)' : ''}</span>` +
             `<span class="streak">${e.streak}</span></li>`;
    }).join('');
  }

  function shareText() {
    const nm = myName() || 'Anonymous';
    const b = loadBoard()[normalize(nm) + '|' + sport] || {streak: stats.streak, score: stats.score};
    return `Name a Vol — ${cfg().label}\n${nm}: best streak ${b.streak}, score ${b.score}\n` +
           `NAV1|${sport}|${nm}|${b.streak}|${b.score}`;
  }

  function importResults(text) {
    const b = loadBoard();
    let added = 0;
    for (const line of String(text || '').split(/\r?\n/)) {
      const m = line.trim().match(/^NAV1\|([a-z]+)\|([^|]{1,24})\|(\d{1,4})\|(\d{1,6})$/i);
      if (!m) continue;
      const [, sp, nm, st, sc] = m;
      if (!SPORTS[sp]) continue;
      const name = cleanName(nm);
      if (!name) continue;
      const k = normalize(name) + '|' + sp;
      const cur = b[k], streak = Number(st), score = Number(sc);
      if (!cur || streak > cur.streak || (streak === cur.streak && score > cur.score)) {
        b[k] = {name, sport: sp, streak, score};
        added++;
      }
    }
    saveBoard(b);
    renderBoard();
    return added;
  }

  // ---- search index ---------------------------------------------------------
  function rebuildPlayerIndex() {
    const map = new Map();
    Object.values(rosters()).forEach(list => (list || []).forEach(name => {
      const k = normalize(name);
      if (k && !map.has(k)) map.set(k, {name});
    }));
    playerIndex = [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  function updateIndexStatus() {
    const n = playableYears().length, total = allYears().length;
    if (seasonCountEl) seasonCountEl.textContent = n;
    let html = n === total
      ? `Player search: <strong>${playerIndex.length.toLocaleString()} names</strong> across all ${total} seasons.`
      : `Playing <strong>${n} of ${total} seasons</strong> — searching ${playerIndex.length.toLocaleString()} players.`;
    if (used.size) html += ` <strong>${used.size}</strong> already used this run.`;
    indexStatus.innerHTML = html;
  }

  // ---- matching -------------------------------------------------------------
  function levenshtein(a, b) {
    const dp = Array.from({length: a.length + 1}, () => Array(b.length + 1).fill(0));
    for (let i = 0; i <= a.length; i++) dp[i][0] = i;
    for (let j = 0; j <= b.length; j++) dp[0][j] = j;
    for (let i = 1; i <= a.length; i++)
      for (let j = 1; j <= b.length; j++)
        dp[i][j] = Math.min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + (a[i-1] === b[j-1] ? 0 : 1));
    return dp[a.length][b.length];
  }
  const tokensOf = s => normalize(s).split(' ').filter(Boolean);
  // Typo tolerance scaled to length. Under five characters must be exact, so a
  // short surname does not sweep up unrelated players.
  function fuzzyEq(a, b) {
    if (a === b) return true;
    const n = Math.min(a.length, b.length);
    if (n < 5) return false;
    const tol = n >= 12 ? 2 : 1;
    return Math.abs(a.length - b.length) <= tol && levenshtein(a, b) <= tol;
  }
  // The prompt asks for ANY player on the roster, so a surname landing on a real
  // player is a correct answer even when several share it. Candidates rank by how
  // exact the match is, and an unused player wins ties so a surname guess does not
  // resolve onto someone already spent this run.
  function matchGuess(guess, roster) {
    const g = normalize(guess);
    if (!g || g.length < 3) return null;
    const gt = tokensOf(guess), gSorted = [...gt].sort().join(' ');
    const cands = [];
    for (const player of roster) {
      const p = normalize(player), pt = tokensOf(player);
      if (g === p) { cands.push({player, rank: 0}); continue; }
      if (fuzzyEq(g, p)) { cands.push({player, rank: 1}); continue; }
      if (gt.length > 1 && gt.length === pt.length && gSorted === [...pt].sort().join(' ')) { cands.push({player, rank: 2}); continue; }
      if (gt.length === 1 && pt.length > 1 && fuzzyEq(gt[0], pt[pt.length - 1])) { cands.push({player, rank: 3}); continue; }
    }
    if (!cands.length) return null;
    cands.sort((a, b) => a.rank - b.rank);
    const tied = cands.filter(c => c.rank === cands[0].rank);
    return (tied.find(c => !used.has(playerKey(c.player))) || tied[0]).player;
  }

  // ---- round flow -----------------------------------------------------------
  function easternDateKey() {
    const s = new Intl.DateTimeFormat('en-CA', {timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date());
    return Number(s.replace(/-/g, ''));
  }
  function seededDailyYear() {
    const pool = playableYears();
    return pool.length ? pool[easternDateKey() % pool.length] : null;
  }
  function chooseYear() {
    if (mode === 'daily') return seededDailyYear();
    const pool = playableYears();
    if (!pool.length) return null;
    // Skip seasons whose whole roster is used, so a round is always winnable.
    let open = pool.filter(y => unusedIn(y).length > 0);
    if (!open.length) { used = new Set(); saveUsed(); open = pool; }
    const choices = open.length > 1 ? open.filter(y => y !== currentYear) : open;
    return choices[Math.floor(Math.random() * choices.length)];
  }

  const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  function renderStats() { streakEl.textContent = stats.streak; scoreEl.textContent = stats.score; }
  function renderDots() {
    const wrap = $('#attempts'); wrap.innerHTML = '';
    for (let i = 0; i < maxAttempts; i++) {
      const d = document.createElement('div');
      d.className = 'dot' + (i < attempts ? ' used' : '');
      wrap.appendChild(d);
    }
  }
  const closeSuggestions = () => { suggestionsEl.classList.remove('open'); activeSuggestion = -1; };

  function highlightName(name, q) {
    const raw = q.trim().toLowerCase(), idx = name.toLowerCase().indexOf(raw);
    if (!raw || idx < 0) return escapeHtml(name);
    return escapeHtml(name.slice(0, idx)) + '<mark>' + escapeHtml(name.slice(idx, idx + raw.length)) + '</mark>' + escapeHtml(name.slice(idx + raw.length));
  }
  const queryLetters = q => normalize(q).replace(/ /g, '').length;
  function searchPlayers(q) {
    const nq = normalize(q);
    if (!nq || queryLetters(q) < MIN_QUERY_LETTERS) return [];
    const terms = nq.split(' ');
    return playerIndex.map(p => {
      const n = normalize(p.name), tokens = n.split(' ');
      let score = 99;
      if (n.startsWith(nq)) score = 0;
      else if (tokens.some(t => t.startsWith(nq))) score = 1;
      else if (terms.every(t => tokens.some(x => x.startsWith(t)))) score = 2;
      else if (n.includes(nq)) score = 3;
      return {...p, score};
    }).filter(x => x.score < 99).sort((a, b) => a.score - b.score || a.name.localeCompare(b.name)).slice(0, 9);
  }
  function renderSuggestions() {
    const q = input.value.trim();
    if (!q) { closeSuggestions(); return; }
    const need = MIN_QUERY_LETTERS - queryLetters(q);
    if (need > 0) {
      suggestionsEl.innerHTML = `<div class="no-match">Type ${need} more character${need === 1 ? '' : 's'} to search.</div>`;
      suggestionsEl.classList.add('open'); visibleSuggestions = []; activeSuggestion = -1; return;
    }
    visibleSuggestions = searchPlayers(q); activeSuggestion = -1;
    if (!visibleSuggestions.length) {
      suggestionsEl.innerHTML = '<div class="no-match">No matching Tennessee player.</div>';
      suggestionsEl.classList.add('open'); return;
    }
    // The name sits in one element because .suggestion is a flex container:
    // bare text nodes around <mark> would each become a flex item and the spaces
    // between them would be stripped, rendering "Al Wilson" as "AlWilson".
    suggestionsEl.innerHTML = visibleSuggestions.map((p, i) =>
      `<button type="button" class="suggestion" data-i="${i}"><span class="s-name">${highlightName(p.name, q)}</span></button>`).join('');
    suggestionsEl.classList.add('open');
  }
  function selectSuggestion(i) {
    const p = visibleSuggestions[i];
    if (!p) return;
    input.value = p.name; closeSuggestions(); input.focus();
  }
  function moveSuggestion(dir) {
    if (!suggestionsEl.classList.contains('open') || !visibleSuggestions.length) return false;
    activeSuggestion = (activeSuggestion + dir + visibleSuggestions.length) % visibleSuggestions.length;
    [...suggestionsEl.querySelectorAll('.suggestion')].forEach((el, i) => el.classList.toggle('active', i === activeSuggestion));
    suggestionsEl.querySelector('.suggestion.active')?.scrollIntoView({block: 'nearest'});
    return true;
  }

  function startRound() {
    const year = chooseYear();
    if (!year) {
      message.textContent = `No ${cfg().label.toLowerCase()} rosters are bundled.`;
      message.className = 'message bad';
      return;
    }
    currentYear = year; attempts = 0; finished = false;
    yearEl.textContent = displayYear(currentYear);
    input.value = ''; input.disabled = false; submitBtn.disabled = false;
    message.textContent = ''; message.className = 'message';
    answer.style.display = 'none'; answer.textContent = '';
    actions.style.display = 'none';
    closeSuggestions(); renderDots(); updateIndexStatus();
    input.focus();
  }

  function endRound(win, matchedPlayer = null) {
    finished = true; input.disabled = true; closeSuggestions();
    const roster = rosters()[currentYear] || [];
    if (win) {
      stats.streak++; stats.score += Math.max(1, 4 - attempts);
      used.add(playerKey(matchedPlayer)); saveUsed();
      message.textContent = `${matchedPlayer}. That Vol rocked.`;
      message.className = 'message good';
    } else {
      stats.streak = 0;
      const pool = unusedIn(currentYear), from = pool.length ? pool : roster;
      const reveal = from[Math.floor(Math.random() * from.length)];
      used = new Set(); saveUsed();
      message.textContent = 'Nope — three strikes.';
      message.className = 'message bad';
      answer.textContent = `One answer: ${reveal}`;
      answer.style.display = 'block';
    }
    saveStats(); renderStats(); recordBest(); updateIndexStatus();
    actions.style.display = 'flex';
  }

  function switchSport(next) {
    if (!SPORTS[next] || next === sport) return;
    sport = next;
    localStorage.setItem('nav_sport', sport);
    document.querySelectorAll('.sport-btn').forEach(b => b.classList.toggle('active', b.dataset.sport === sport));
    loadStats(); loadUsed(); rebuildPlayerIndex(); renderStats(); renderBoard();
    currentYear = null;
    startRound();
  }

  // ---- wiring ---------------------------------------------------------------
  input.addEventListener('input', renderSuggestions);
  input.addEventListener('focus', () => { if (input.value.trim()) renderSuggestions(); });
  input.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { if (moveSuggestion(1)) e.preventDefault(); }
    else if (e.key === 'ArrowUp') { if (moveSuggestion(-1)) e.preventDefault(); }
    else if (e.key === 'Escape') closeSuggestions();
    else if (e.key === 'Enter' && activeSuggestion >= 0) { e.preventDefault(); selectSuggestion(activeSuggestion); }
  });
  suggestionsEl.addEventListener('mousedown', e => {
    const b = e.target.closest('.suggestion');
    if (!b) return;
    e.preventDefault(); selectSuggestion(Number(b.dataset.i));
  });
  document.addEventListener('click', e => { if (!e.target.closest('.input-wrap')) closeSuggestions(); });

  form.addEventListener('submit', e => {
    e.preventDefault();
    if (finished) return;
    const guess = input.value.trim();
    if (!guess) return;
    const matched = matchGuess(guess, rosters()[currentYear] || []);
    if (matched && used.has(playerKey(matched))) {
      message.textContent = `You already used ${matched} this run — name someone else.`;
      message.className = 'message bad';
      input.select(); renderSuggestions(); return;
    }
    attempts++; renderDots();
    if (matched) { endRound(true, matched); return; }
    if (attempts >= maxAttempts) endRound(false);
    else {
      const left = maxAttempts - attempts;
      message.textContent = `Not on the ${displayYear(currentYear)} roster. ${left} guess${left === 1 ? '' : 'es'} left.`;
      message.className = 'message bad';
      input.select(); renderSuggestions();
    }
  });

  $('#nextBtn').addEventListener('click', startRound);
  $('#shareBtn').addEventListener('click', async () => {
    const text = shareText();
    try {
      await navigator.clipboard.writeText(text);
      $('#shareBtn').textContent = 'Copied!';
      setTimeout(() => { $('#shareBtn').textContent = 'Share result'; }, 1200);
    } catch { alert(text); }
  });

  document.querySelectorAll('.mode-btn').forEach(btn => btn.addEventListener('click', () => {
    mode = btn.dataset.mode;
    localStorage.setItem('nav_mode', mode);
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
    startRound();
  }));
  document.querySelectorAll('.sport-btn').forEach(btn =>
    btn.addEventListener('click', () => switchSport(btn.dataset.sport)));

  if (nameInput) {
    nameInput.value = myName();
    const commit = () => {
      const v = cleanName(nameInput.value);
      nameInput.value = v;
      localStorage.setItem('nav_name', v);
      recordBest(); renderBoard();
    };
    nameInput.addEventListener('change', commit);
    nameInput.addEventListener('blur', commit);
  }
  if (importBtn) importBtn.addEventListener('click', () => {
    const n = importResults(importBox.value);
    importNote.textContent = n ? `Added ${n} result${n === 1 ? '' : 's'}.` : 'No results found in that text.';
    if (n) importBox.value = '';
    setTimeout(() => { importNote.textContent = ''; }, 4000);
  });

  // ---- boot -----------------------------------------------------------------
  document.querySelectorAll('.sport-btn').forEach(b => b.classList.toggle('active', b.dataset.sport === sport));
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
  loadStats(); loadUsed(); rebuildPlayerIndex(); renderStats(); renderBoard();
  startRound();
})();

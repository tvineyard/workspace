(() => {
  // Everything is bundled in the page, so nothing is fetched at runtime.
  // window.VOL_ROSTERS   is {sport: {season: [names]}}
  // window.VOL_POSITIONS is {sport: {season: {name: group}}}
  let DATA = window.VOL_ROSTERS || {};
  // Tolerate the pre-multi-sport shape in case a cached copy of either file is a
  // version behind: a hard crash here would freeze the page rather than degrade.
  if (Object.values(DATA).some(Array.isArray)) DATA = {football: DATA};
  const POS = window.VOL_POSITIONS || {};
  const PLABEL = window.VOL_POSITION_LABELS || {};

  const SPORTS = {
    football:   {label: 'Football',   start: 1990, end: 2026, span: false, min: 20, listFloor: 6},
    basketball: {label: 'Basketball', start: 1990, end: 2025, span: true,  min: 8,  listFloor: 4},
  };
  const MODES = {classic: 'Classic', position: 'By position', howmany: 'How many'};

  let sport = localStorage.getItem('nav_sport') || 'football';
  if (!SPORTS[sport] || !DATA[sport]) sport = Object.keys(SPORTS).find(s => DATA[s]) || 'football';
  let mode = localStorage.getItem('nav_mode2') || 'classic';
  if (!MODES[mode]) mode = 'classic';

  const cfg = () => SPORTS[sport];
  const rosters = () => DATA[sport] || {};
  const positions = () => POS[sport] || {};
  const allYears = () => {
    const c = cfg();
    return Array.from({length: c.end - c.start + 1}, (_, i) => String(c.start + i));
  };
  // Basketball seasons straddle two calendar years and are named that way.
  const displayYear = y => cfg().span ? `${y}-${String(Number(y) + 1).slice(-2)}` : y;
  const hasRoster = y => { const r = rosters()[y]; return Array.isArray(r) && r.length >= cfg().min; };
  // Every season this sport actually has data for, ignoring the user's range.
  const seasonsWithData = () => allYears().filter(hasRoster);

  // Season range, per sport. Someone who does not remember the nineties can cut
  // the game down to the years they lived through.
  let range = {from: null, to: null};
  function loadRange() {
    const have = seasonsWithData();
    const get = k => localStorage.getItem(key(k));
    const from = get('from'), to = get('to');
    range = {
      from: have.includes(from) ? from : (have[0] || null),
      to:   have.includes(to)   ? to   : (have[have.length - 1] || null),
    };
    if (range.from && range.to && Number(range.from) > Number(range.to)) {
      range = {from: range.to, to: range.from};
    }
  }
  function saveRange() {
    localStorage.setItem(key('from'), range.from);
    localStorage.setItem(key('to'), range.to);
  }
  const playableYears = () => seasonsWithData().filter(y =>
    (!range.from || Number(y) >= Number(range.from)) &&
    (!range.to   || Number(y) <= Number(range.to)));
  const playersAt = (y, g) => {
    const table = positions()[y] || {};
    return (rosters()[y] || []).filter(n => table[n] === g);
  };
  // Season/position pairs holding at least `floor` players.
  function pairs(floor) {
    const out = [];
    for (const y of playableYears()) {
      const table = positions()[y];
      if (!table) continue;
      const counts = {};
      Object.values(table).forEach(g => { counts[g] = (counts[g] || 0) + 1; });
      for (const g of Object.keys(counts)) if (counts[g] >= floor) out.push([y, g]);
    }
    return out;
  }
  const groupName = (g, plural) => (PLABEL[g] || [g, g])[plural ? 1 : 0];

  const maxAttempts = 3;
  const MIN_QUERY_LETTERS = 5;

  let currentYear = null, currentGroup = null;
  let attempts = 0, finished = false, found = [];
  let activeSuggestion = -1, visibleSuggestions = [], playerIndex = [];

  const $ = s => document.querySelector(s);
  const promptEl = $('#prompt'), input = $('#player'), form = $('#guessForm');
  const message = $('#message'), answer = $('#answer'), actions = $('#actions');
  const foundEl = $('#foundList');
  const eyebrowEl = $('#eyebrow'), helpEl = $('#help');
  const t1v = $('#t1v'), t1l = $('#t1l'), t2v = $('#t2v'), t2l = $('#t2l'), t3v = $('#t3v'), t3l = $('#t3l');
  const suggestionsEl = $('#suggestions'), submitBtn = $('#submitBtn'), shareHint = $('#shareHint');
  const settingsBtn = $('#settingsBtn'), settingsPanel = $('#settingsPanel'), rangeLabel = $('#rangeLabel');
  const fromSel = $('#fromYear'), toSel = $('#toYear'), resetRange = $('#resetRange');

  function normalize(s) {
    return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/&/g, 'and').replace(/[’']/g, '')
      .replace(/\b(jr|sr|ii|iii|iv)\b\.?/g, '')
      .replace(/[^a-z0-9]/g, ' ').replace(/\s+/g, ' ').trim();
  }
  const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));

  // ---- progress, per sport --------------------------------------------------
  const key = k => `nav_${k}_${sport}`;
  // streak/best/wins/rounds drive the round-based modes. listBest is the most
  // players ever named in one How many round.
  let stats = {streak: 0, best: 0, wins: 0, rounds: 0, listBest: 0};
  function loadStats() {
    const num = k => Number(localStorage.getItem(key(k)) || 0);
    stats = {streak: num('streak'), best: num('best'), wins: num('wins'),
             rounds: num('rounds'), listBest: num('listBest')};
    if (stats.streak > stats.best) stats.best = stats.streak;
  }
  const saveStats = () => ['streak','best','wins','rounds','listBest']
    .forEach(k => localStorage.setItem(key(k), stats[k]));
  const scoreLabel = () => stats.rounds ? Math.round(stats.wins / stats.rounds * 100) + '%' : '—';

  const playerKey = name => 'nm:' + normalize(name);
  let used = new Set();
  function loadUsed() {
    used = new Set();
    try { const r = JSON.parse(localStorage.getItem(key('used')) || '[]'); if (Array.isArray(r)) used = new Set(r); } catch {}
  }
  const saveUsed = () => { try { localStorage.setItem(key('used'), JSON.stringify([...used])); } catch {} };
  // The no-repeat rule belongs to the streak modes. How many is a single round
  // about exhausting one position, so a player spent in an earlier run must not
  // be locked out of it.
  const usesNoRepeat = () => mode !== 'howmany';

  // ---- search index ---------------------------------------------------------
  function rebuildPlayerIndex() {
    const map = new Map();
    Object.values(rosters()).forEach(list => (list || []).forEach(name => {
      const k = normalize(name);
      if (k && !map.has(k)) map.set(k, {name});
    }));
    playerIndex = [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
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
  // Tolerance scales with length; under five characters must be exact so a short
  // surname does not sweep up unrelated players.
  function fuzzyEq(a, b) {
    if (a === b) return true;
    const n = Math.min(a.length, b.length);
    if (n < 5) return false;
    const tol = n >= 12 ? 2 : 1;
    return Math.abs(a.length - b.length) <= tol && levenshtein(a, b) <= tol;
  }
  // A surname landing on a real player counts, since the prompt asks for anyone
  // who fits. Candidates rank by exactness, and an unused player wins ties.
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
  // The set a guess is checked against, for the round in play.
  function targetRoster() {
    if (mode === 'classic') return rosters()[currentYear] || [];
    const all = playersAt(currentYear, currentGroup);
    return mode === 'howmany' ? all.filter(n => !found.includes(n)) : all;
  }

  // ---- rendering ------------------------------------------------------------
  function renderStats() {
    if (mode === 'howmany') {
      t1v.textContent = found.length;   t1l.textContent = 'Found';
      t2v.textContent = stats.listBest; t2l.textContent = 'Best';
      t3v.textContent = scoreLabel();   t3l.textContent = 'Score';
    } else {
      t1v.textContent = stats.streak;   t1l.textContent = 'Streak';
      t2v.textContent = stats.best;     t2l.textContent = 'Longest';
      t3v.textContent = scoreLabel();   t3l.textContent = 'Score';
    }
  }
  function renderDots() {
    const wrap = $('#attempts'); wrap.innerHTML = '';
    for (let i = 0; i < maxAttempts; i++) {
      const d = document.createElement('div');
      d.className = 'dot' + (i < attempts ? ' used' : '');
      wrap.appendChild(d);
    }
  }
  function renderFound() {
    if (!foundEl) return;
    foundEl.innerHTML = found.map(n => `<span class="chip">${escapeHtml(n)}</span>`).join('');
    foundEl.style.display = found.length ? 'flex' : 'none';
  }
  function renderPrompt() {
    const y = displayYear(currentYear);
    if (mode === 'classic') {
      promptEl.innerHTML = `Who played for the <span class="year">${y}</span> Tennessee Volunteers?`;
      eyebrowEl.textContent = 'Name one player';
      helpEl.textContent = "Anyone on that season's roster counts. You get three guesses.";
    } else if (mode === 'position') {
      promptEl.innerHTML = `Name a ${escapeHtml(groupName(currentGroup))} from the <span class="year">${y}</span> Volunteers.`;
      eyebrowEl.textContent = 'Name one player';
      helpEl.textContent = `Only ${groupName(currentGroup, true)} count. You get three guesses.`;
    } else {
      promptEl.innerHTML = `How many <span class="year">${y}</span> ${escapeHtml(groupName(currentGroup, true))} can you name?`;
      eyebrowEl.textContent = 'Name as many as you can';
      helpEl.textContent = 'Keep going until three wrong guesses end the round.';
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
    // The name sits in one element because .suggestion is a flex container: bare
    // text nodes around <mark> would each become a flex item and the spaces
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

  // ---- rounds ---------------------------------------------------------------
  const pick = arr => arr[Math.floor(Math.random() * arr.length)];

  function chooseRound() {
    if (mode === 'classic') {
      const pool = playableYears();
      if (!pool.length) return null;
      let open = pool.filter(y => (rosters()[y] || []).some(n => !used.has(playerKey(n))));
      if (!open.length) { used = new Set(); saveUsed(); open = pool; }
      const choices = open.length > 1 ? open.filter(y => y !== currentYear) : open;
      return {year: pick(choices), group: null};
    }
    if (mode === 'howmany') {
      const all = pairs(cfg().listFloor);
      if (!all.length) return null;
      const choices = all.filter(([y, g]) => !(y === currentYear && g === currentGroup));
      const [y, g] = pick(choices.length ? choices : all);
      return {year: y, group: g};
    }
    // By position: only serve a pairing that still has someone unused.
    let all = pairs(1).filter(([y, g]) => playersAt(y, g).some(n => !used.has(playerKey(n))));
    if (!all.length) { used = new Set(); saveUsed(); all = pairs(1); }
    if (!all.length) return null;
    const choices = all.filter(([y, g]) => !(y === currentYear && g === currentGroup));
    const [y, g] = pick(choices.length ? choices : all);
    return {year: y, group: g};
  }

  function startRound() {
    const r = chooseRound();
    if (!r) {
      const narrowed = playableYears().length < seasonsWithData().length;
      message.textContent = narrowed
        ? 'No rounds in this season range for this mode — widen it in Seasons.'
        : `No ${cfg().label.toLowerCase()} rounds available for this mode.`;
      message.className = 'message bad';
      promptEl.textContent = ''; eyebrowEl.textContent = ''; helpEl.textContent = '';
      actions.style.display = 'none';
      return;
    }
    currentYear = r.year; currentGroup = r.group;
    attempts = 0; finished = false; found = [];
    renderPrompt();
    input.value = ''; input.disabled = false; submitBtn.disabled = false;
    message.textContent = ''; message.className = 'message';
    answer.style.display = 'none'; answer.textContent = '';
    actions.style.display = 'none';
    closeSuggestions(); renderDots(); renderFound(); renderStats();
    input.focus();
  }

  function endRound(win, matchedPlayer = null) {
    finished = true; input.disabled = true; closeSuggestions();

    if (mode === 'howmany') {
      const total = playersAt(currentYear, currentGroup).length;
      if (found.length > stats.listBest) stats.listBest = found.length;
      stats.rounds++;
      if (found.length === total) stats.wins++;
      const missed = playersAt(currentYear, currentGroup).filter(n => !found.includes(n));
      message.textContent = `You named ${found.length} of ${total}.`;
      message.className = 'message ' + (found.length === total ? 'good' : 'bad');
      if (missed.length) {
        answer.innerHTML = `<strong>You missed:</strong> ${missed.map(escapeHtml).join(', ')}`;
        answer.style.display = 'block';
      }
    } else {
      const roster = mode === 'classic' ? (rosters()[currentYear] || []) : playersAt(currentYear, currentGroup);
      stats.rounds++;
      if (win) {
        stats.wins++; stats.streak++;
        if (stats.streak > stats.best) stats.best = stats.streak;
        used.add(playerKey(matchedPlayer)); saveUsed();
        message.textContent = `${matchedPlayer}. That Vol rocked.`;
        message.className = 'message good';
      } else {
        stats.streak = 0;
        const open = roster.filter(n => !used.has(playerKey(n)));
        const from = open.length ? open : roster;
        used = new Set(); saveUsed();
        message.textContent = 'Nope — three strikes.';
        message.className = 'message bad';
        if (from.length) {
          answer.textContent = `One answer: ${pick(from)}`;
          answer.style.display = 'block';
        }
      }
    }
    saveStats(); renderStats();
    actions.style.display = 'flex';
  }

  // ---- sharing --------------------------------------------------------------
  function shareText() {
    const lines = [`Name a Vol — ${cfg().label}`];
    if (mode === 'howmany') {
      const total = playersAt(currentYear, currentGroup).length;
      lines.push(`${displayYear(currentYear)} ${groupName(currentGroup, true)}`);
      lines.push(finished ? `Named ${found.length} of ${total}` : `Named ${found.length} so far`);
      lines.push(`Best: ${stats.listBest}`);
    } else {
      if (finished) {
        const won = message.className.includes('good');
        lines.push(`${displayYear(currentYear)}` + (currentGroup ? ` ${groupName(currentGroup, true)}` : '') +
                   ' ' + (won ? `🟧 ${attempts}/${maxAttempts}` : '⬛ missed'));
      }
      lines.push(`Current streak: ${stats.streak}`);
      lines.push(`Longest streak: ${stats.best}`);
    }
    if (stats.rounds) lines.push(`Score: ${scoreLabel()} (${stats.wins}/${stats.rounds})`);
    lines.push(location.href.split('?')[0]);
    return lines.join('\n');
  }

  // ---- switching ------------------------------------------------------------
  function switchSport(next) {
    if (!SPORTS[next] || next === sport) return;
    sport = next; localStorage.setItem('nav_sport', sport);
    document.querySelectorAll('.sport-btn').forEach(b => b.classList.toggle('active', b.dataset.sport === sport));
    loadStats(); loadUsed(); loadRange(); renderRange(); rebuildPlayerIndex();
    currentYear = null; currentGroup = null;
    startRound();
  }
  function switchMode(next) {
    if (!MODES[next] || next === mode) return;
    mode = next; localStorage.setItem('nav_mode2', mode);
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
    currentYear = null; currentGroup = null;
    startRound();
  }

  // ---- settings -------------------------------------------------------------
  function renderRange() {
    const have = seasonsWithData();
    if (!have.length) return;
    const opts = sel => have.map(y =>
      `<option value="${y}"${y === sel ? ' selected' : ''}>${displayYear(y)}</option>`).join('');
    fromSel.innerHTML = opts(range.from);
    toSel.innerHTML = opts(range.to);
    const whole = range.from === have[0] && range.to === have[have.length - 1];
    rangeLabel.textContent = whole ? 'all' : `${displayYear(range.from)}–${displayYear(range.to)}`;
  }
  function applyRange(from, to) {
    range = {from, to};
    if (Number(range.from) > Number(range.to)) range = {from: to, to: from};
    saveRange(); renderRange(); startRound();
  }
  settingsBtn.addEventListener('click', () => {
    const open = settingsPanel.hasAttribute('hidden');
    settingsPanel.toggleAttribute('hidden', !open);
    settingsBtn.setAttribute('aria-expanded', String(open));
  });
  fromSel.addEventListener('change', () => applyRange(fromSel.value, toSel.value));
  toSel.addEventListener('change', () => applyRange(fromSel.value, toSel.value));
  resetRange.addEventListener('click', () => {
    const have = seasonsWithData();
    applyRange(have[0], have[have.length - 1]);
  });

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
    const matched = matchGuess(guess, targetRoster());

    if (mode === 'howmany') {
      if (matched) {
        found.push(matched);
        input.value = ''; renderFound(); renderStats(); closeSuggestions();
        message.textContent = `${matched}. Keep going.`;
        message.className = 'message good';
        if (!targetRoster().length) endRound(true);
        return;
      }
      // Naming someone already on your list should not cost a strike.
      if (matchGuess(guess, playersAt(currentYear, currentGroup))) {
        message.textContent = 'Already on your list — name someone else.';
        message.className = 'message bad';
        input.select(); return;
      }
      attempts++; renderDots();
      if (attempts >= maxAttempts) { endRound(false); return; }
      message.textContent = `Not a ${groupName(currentGroup)} that season. ${maxAttempts - attempts} left.`;
      message.className = 'message bad';
      input.select(); return;
    }

    if (matched && usesNoRepeat() && used.has(playerKey(matched))) {
      message.textContent = `You already used ${matched} this run — name someone else.`;
      message.className = 'message bad';
      input.select(); renderSuggestions(); return;
    }
    attempts++; renderDots();
    if (matched) { endRound(true, matched); return; }
    if (attempts >= maxAttempts) { endRound(false); return; }
    const left = maxAttempts - attempts;
    message.textContent = mode === 'position'
      ? `Not a ${groupName(currentGroup)} on that roster. ${left} guess${left === 1 ? '' : 'es'} left.`
      : `Not on the ${displayYear(currentYear)} roster. ${left} guess${left === 1 ? '' : 'es'} left.`;
    message.className = 'message bad';
    input.select(); renderSuggestions();
  });

  $('#nextBtn').addEventListener('click', startRound);
  $('#shareBtn').addEventListener('click', async () => {
    const text = shareText();
    const done = () => {
      $('#shareBtn').textContent = 'Copied — paste to share';
      if (shareHint) shareHint.textContent = 'Paste it into your group chat to share.';
      setTimeout(() => {
        $('#shareBtn').textContent = 'Copy result';
        if (shareHint) shareHint.textContent = '';
      }, 4000);
    };
    try { await navigator.clipboard.writeText(text); done(); }
    catch { window.prompt('Copy this, then paste to share:', text); }
  });
  $('#doneBtn')?.addEventListener('click', () => { if (!finished) endRound(false); });

  document.querySelectorAll('.sport-btn').forEach(b => b.addEventListener('click', () => switchSport(b.dataset.sport)));
  document.querySelectorAll('.mode-btn').forEach(b => b.addEventListener('click', () => switchMode(b.dataset.mode)));

  // ---- boot -----------------------------------------------------------------
  document.querySelectorAll('.sport-btn').forEach(b => b.classList.toggle('active', b.dataset.sport === sport));
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
  loadStats(); loadUsed(); loadRange(); renderRange(); rebuildPlayerIndex(); renderStats();
  startRound();
})();

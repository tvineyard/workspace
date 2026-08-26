(() => {
  const START_YEAR = 1990;
  const END_YEAR = 2026;
  const ALL_YEARS = Array.from({length: END_YEAR-START_YEAR+1}, (_,i)=>String(START_YEAR+i));
  const rosters = window.VOL_ROSTERS = window.VOL_ROSTERS || {};
  // Seasons physically bundled in data/rosters.seed.js. These always work offline, so they
  // define the Daily pool — everyone gets the same puzzle regardless of what their browser
  // managed to fetch. Bake more seasons into the seed file and this pool grows on its own.
  const SEED_YEARS = ALL_YEARS.filter(y => Array.isArray(rosters[y]) && rosters[y].length >= 20);

  // Player identity for the no-repeat rule is the normalized name.
  //
  // utsports publishes an athlete id in each bio URL, which looks like a better
  // key, but those ids are not stable across seasons: Arian Foster is 14775 for
  // 2004-2007 and 14267 for 2008, and A.J. Johnson changes id when the spelling
  // changes. Keying on id would let the same player be used once per id, which is
  // exactly the bug this rule exists to prevent. The normalized name merges both
  // of those cases correctly. data/athlete-ids.json keeps the ids for reference.
  function playerKey(name){return 'nm:'+normalize(name)}

  // Players already answered correctly during this run. Cleared when the streak breaks.
  let used = new Set();
  try{const raw=JSON.parse(localStorage.getItem('nav_used')||'[]');if(Array.isArray(raw))used=new Set(raw)}catch{}
  function saveUsed(){try{localStorage.setItem('nav_used',JSON.stringify([...used]))}catch{}}
  function unusedIn(year){const r=rosters[year]||[];return r.filter(n=>!used.has(playerKey(n)))}
  const cacheVersion = 'v3';
  let mode = localStorage.getItem('nav_mode') || 'endless';
  let currentYear = null;
  let attempts = 0;
  let finished = false;
  let roundLoading = false;
  const maxAttempts = 3;
  let indexStarted = false;
  let indexPromise = null;
  let activeSuggestion = -1;
  let visibleSuggestions = [];

  const $ = s => document.querySelector(s);
  const yearEl=$('#year'), input=$('#player'), form=$('#guessForm'), message=$('#message'), answer=$('#answer'), actions=$('#actions');
  const streakEl=$('#streak'), scoreEl=$('#score'), seasonCountEl=$('#seasonCount'), suggestionsEl=$('#suggestions'), indexStatus=$('#indexStatus'), roundLoader=$('#roundLoader'), submitBtn=$('#submitBtn');
  const stats={streak:Number(localStorage.getItem('nav_streak')||0),score:Number(localStorage.getItem('nav_score')||0)};

  function normalize(s){return String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/&/g,'and').replace(/[’']/g,'').replace(/\b(jr|sr|ii|iii|iv)\b\.?/g,'').replace(/[^a-z0-9]/g,' ').replace(/\s+/g,' ').trim()}
  function cleanMarkdownName(s){
    s=String(s||'').trim().replace(/^\[([^\]]+)\]\([^)]+\)$/,'$1').replace(/\*\*/g,'').replace(/<[^>]+>/g,'').trim();
    return s.replace(/\s+/g,' ');
  }
  function parseRosterMarkdown(text){
    const names=[];
    for(const raw of String(text||'').split(/\r?\n/)){
      const line=raw.trim();
      if(!line.includes('|')) continue;
      const cells=line.split('|').map(x=>x.trim());
      if(cells.length<3) continue;
      const jersey=cells[0].replace(/[*_]/g,'').trim();
      if(!/^\d{1,2}$/.test(jersey)) continue;
      const name=cleanMarkdownName(cells[1]);
      if(!name || /^(name|image)$/i.test(name) || name.length<3 || name.length>60) continue;
      if(!/[a-z]/i.test(name)) continue;
      names.push(name);
    }
    // Fallback for Reader output that omits the compact table.
    if(names.length<20){
      for(const m of String(text||'').matchAll(/Full Bio for\s+([^\n\r]+)/gi)){
        const name=cleanMarkdownName(m[1]);
        if(name && name.length<60) names.push(name);
      }
    }
    return [...new Map(names.map(n=>[normalize(n),n])).values()];
  }
  function cacheKey(year){return `nav_roster_${cacheVersion}_${year}`}
  function loadCachedRosters(){
    ALL_YEARS.forEach(y=>{
      try{const x=JSON.parse(localStorage.getItem(cacheKey(y))||'null');if(Array.isArray(x)&&x.length>=20)rosters[y]=x}catch{}
    });
  }
  async function fetchOfficialRoster(year){
    const target=`https://utsports.com/sports/football/roster/${year}`;
    const reader=`https://r.jina.ai/${target}`;
    const res=await fetch(reader,{headers:{'Accept':'text/plain'}});
    if(!res.ok) throw new Error(`Roster source returned ${res.status}`);
    const text=await res.text();
    const names=parseRosterMarkdown(text);
    if(names.length<20) throw new Error(`Only found ${names.length} players`);
    rosters[year]=names;
    try{localStorage.setItem(cacheKey(year),JSON.stringify(names))}catch{}
    rebuildPlayerIndex();
    updateIndexStatus();
    return names;
  }
  async function ensureRoster(year){
    if(Array.isArray(rosters[year])&&rosters[year].length>=20) return rosters[year];
    return fetchOfficialRoster(year);
  }
  function sleep(ms){return new Promise(r=>setTimeout(r,ms))}
  async function preloadAllRosters(){
    if(indexPromise) return indexPromise;
    indexStarted=true;
    updateIndexStatus();
    indexPromise=(async()=>{
      const missing=ALL_YEARS.filter(y=>!(Array.isArray(rosters[y])&&rosters[y].length>=20));
      // Small batches keep the free reader endpoint from being hammered.
      for(let i=0;i<missing.length;i+=3){
        const batch=missing.slice(i,i+3);
        await Promise.all(batch.map(async y=>{
          try{await fetchOfficialRoster(y)}catch(e){console.warn('Could not load',y,e.message)}
        }));
        updateIndexStatus();
        if(i+3<missing.length) await sleep(650);
      }
      updateIndexStatus(true);
    })();
    return indexPromise;
  }

  let playerIndex=[];
  function rebuildPlayerIndex(){
    const map=new Map();
    Object.entries(rosters).forEach(([year,list])=>{
      (list||[]).forEach(name=>{
        const key=normalize(name); if(!key) return;
        if(!map.has(key)) map.set(key,{name,years:[]});
        map.get(key).years.push(year);
      })
    });
    playerIndex=[...map.values()].sort((a,b)=>a.name.localeCompare(b.name));
  }
  function playableYears(){return ALL_YEARS.filter(y=>Array.isArray(rosters[y])&&rosters[y].length>=20)}
  function loadedSeasonCount(){return playableYears().length}
  function updateIndexStatus(done=false){
    const n=loadedSeasonCount(), total=ALL_YEARS.length;
    seasonCountEl.textContent=n;
    if(n===total) indexStatus.innerHTML=`Player search: <strong>${playerIndex.length.toLocaleString()} names</strong> across all ${total} seasons.`;
    else if(indexStarted&&!done) indexStatus.innerHTML=`Looking for more seasons… <strong>${n}/${total}</strong> loaded so far.`;
    else indexStatus.innerHTML=`Playing <strong>${n} of ${total} seasons</strong> — searching ${playerIndex.length.toLocaleString()} Tennessee players.`;
    if(used.size) indexStatus.innerHTML += ` <strong>${used.size}</strong> already used this run.`;
  }

  function levenshtein(a,b){const dp=Array.from({length:a.length+1},()=>Array(b.length+1).fill(0));for(let i=0;i<=a.length;i++)dp[i][0]=i;for(let j=0;j<=b.length;j++)dp[0][j]=j;for(let i=1;i<=a.length;i++)for(let j=1;j<=b.length;j++)dp[i][j]=Math.min(dp[i-1][j]+1,dp[i][j-1]+1,dp[i-1][j-1]+(a[i-1]===b[j-1]?0:1));return dp[a.length][b.length]}
  function matchGuess(guess,roster){const g=normalize(guess);if(!g||g.length<3)return null;for(const player of roster){const p=normalize(player);if(g===p)return player;const tolerance=p.length>=14?2:1;if(Math.abs(g.length-p.length)<=tolerance&&levenshtein(g,p)<=tolerance)return player}return null}
  function easternDateKey(){const s=new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());return Number(s.replace(/-/g,''))}
  function seededDailyYear(){const pool=SEED_YEARS.length?SEED_YEARS:playableYears();return pool.length?pool[easternDateKey()%pool.length]:null}
  function chooseYear(){
    if(mode==='daily')return seededDailyYear();
    const pool=playableYears();
    if(!pool.length)return null;
    // Skip seasons whose whole roster has already been used, so a round is always winnable.
    let open=pool.filter(y=>unusedIn(y).length>0);
    if(!open.length){used=new Set();saveUsed();open=pool}
    const choices=open.length>1?open.filter(y=>y!==currentYear):open;
    return choices[Math.floor(Math.random()*choices.length)];
  }
  function renderStats(){streakEl.textContent=stats.streak;scoreEl.textContent=stats.score;seasonCountEl.textContent=loadedSeasonCount()}
  function renderDots(){const wrap=$('#attempts');wrap.innerHTML='';for(let i=0;i<maxAttempts;i++){const d=document.createElement('div');d.className='dot'+(i<attempts?' used':'');wrap.appendChild(d)}}
  function closeSuggestions(){suggestionsEl.classList.remove('open');activeSuggestion=-1}
  function highlightName(name,q){
    const nq=normalize(q); if(!nq) return escapeHtml(name);
    const lower=name.toLowerCase(), raw=q.trim().toLowerCase();
    let idx=lower.indexOf(raw); if(idx<0) return escapeHtml(name);
    return escapeHtml(name.slice(0,idx))+'<mark>'+escapeHtml(name.slice(idx,idx+raw.length))+'</mark>'+escapeHtml(name.slice(idx+raw.length));
  }
  function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}
  function searchPlayers(q){
    const nq=normalize(q); if(nq.length<1)return [];
    const terms=nq.split(' ');
    return playerIndex.map(p=>{
      const n=normalize(p.name), tokens=n.split(' ');let score=99;
      if(n.startsWith(nq))score=0;
      else if(tokens.some(t=>t.startsWith(nq)))score=1;
      else if(terms.every(term=>tokens.some(t=>t.startsWith(term))))score=2;
      else if(n.includes(nq))score=3;
      return {...p,score};
    }).filter(x=>x.score<99).sort((a,b)=>a.score-b.score||a.name.localeCompare(b.name)).slice(0,9);
  }
  function renderSuggestions(){
    const q=input.value.trim(); if(!q){closeSuggestions();return}
    visibleSuggestions=searchPlayers(q);activeSuggestion=-1;
    if(!visibleSuggestions.length){suggestionsEl.innerHTML='<div class="no-match">No matching Tennessee player loaded yet.</div>';suggestionsEl.classList.add('open');return}
    suggestionsEl.innerHTML=visibleSuggestions.map((p,i)=>`<button type="button" class="suggestion" data-i="${i}">${highlightName(p.name,q)}</button>`).join('');
    suggestionsEl.classList.add('open');
  }
  function selectSuggestion(i){const p=visibleSuggestions[i];if(!p)return;input.value=p.name;closeSuggestions();input.focus()}
  function moveSuggestion(dir){
    if(!suggestionsEl.classList.contains('open')||!visibleSuggestions.length)return false;
    activeSuggestion=(activeSuggestion+dir+visibleSuggestions.length)%visibleSuggestions.length;
    [...suggestionsEl.querySelectorAll('.suggestion')].forEach((el,i)=>el.classList.toggle('active',i===activeSuggestion));
    suggestionsEl.querySelector('.suggestion.active')?.scrollIntoView({block:'nearest'});return true;
  }

  async function startRound(){
    const year=chooseYear();
    if(!year){message.textContent='No rosters are bundled yet. Rebuild data/rosters.seed.js and reload.';message.className='message bad';roundLoader.classList.remove('show');return}
    currentYear=year;attempts=0;finished=false;roundLoading=true;yearEl.textContent=currentYear;const ly=$('#loadingYear');if(ly)ly.textContent=currentYear;input.value='';input.disabled=true;submitBtn.disabled=true;message.textContent='';message.className='message';answer.style.display='none';answer.textContent='';actions.style.display='none';closeSuggestions();renderDots();roundLoader.classList.add('show');
    try{await ensureRoster(currentYear);message.textContent=''}catch(e){
      message.textContent=`Could not load the ${currentYear} roster. Try Next season.`;message.className='message bad';actions.style.display='flex';roundLoading=false;roundLoader.classList.remove('show');return;
    }
    roundLoading=false;roundLoader.classList.remove('show');input.disabled=false;submitBtn.disabled=false;input.focus();
  }
  function endRound(win,matchedPlayer=null){finished=true;input.disabled=true;closeSuggestions();const roster=rosters[currentYear];if(win){stats.streak++;stats.score+=Math.max(1,4-attempts);used.add(playerKey(matchedPlayer));saveUsed();message.textContent=`${matchedPlayer}. That Vol rocked.`;message.className='message good'}else{stats.streak=0;const pool=unusedIn(currentYear);const from=pool.length?pool:roster;const reveal=from[Math.floor(Math.random()*from.length)];used=new Set();saveUsed();message.textContent='Nope — three strikes.';message.className='message bad';answer.textContent=`One answer: ${reveal}`;answer.style.display='block'}localStorage.setItem('nav_streak',stats.streak);localStorage.setItem('nav_score',stats.score);renderStats();updateIndexStatus();actions.style.display='flex'}

  input.addEventListener('focus',()=>{if(!indexStarted)preloadAllRosters();if(input.value.trim())renderSuggestions()});
  input.addEventListener('input',()=>{if(!indexStarted)preloadAllRosters();renderSuggestions()});
  input.addEventListener('keydown',e=>{
    if(e.key==='ArrowDown'){if(moveSuggestion(1))e.preventDefault()}
    else if(e.key==='ArrowUp'){if(moveSuggestion(-1))e.preventDefault()}
    else if(e.key==='Escape')closeSuggestions();
    else if(e.key==='Enter'&&activeSuggestion>=0){e.preventDefault();selectSuggestion(activeSuggestion)}
  });
  suggestionsEl.addEventListener('mousedown',e=>{const b=e.target.closest('.suggestion');if(!b)return;e.preventDefault();selectSuggestion(Number(b.dataset.i))});
  document.addEventListener('click',e=>{if(!e.target.closest('.input-wrap'))closeSuggestions()});

  form.addEventListener('submit',e=>{e.preventDefault();if(finished||roundLoading)return;const guess=input.value.trim();if(!guess)return;const matched=matchGuess(guess,rosters[currentYear]);
    if(matched&&used.has(playerKey(matched))){
      message.textContent=`You already used ${matched} this run — name someone else.`;message.className='message bad';
      input.select();renderSuggestions();return;
    }
    attempts++;renderDots();if(matched){endRound(true,matched);return}if(attempts>=maxAttempts)endRound(false);else{message.textContent=`Not on the ${currentYear} roster. ${maxAttempts-attempts} guess${maxAttempts-attempts===1?'':'es'} left.`;message.className='message bad';input.select();renderSuggestions()}});
  $('#nextBtn').addEventListener('click',startRound);
  $('#shareBtn').addEventListener('click',async()=>{const result=message.classList.contains('good')?'🟧':'⬛',text=`Name a Vol — ${currentYear}\n${result} ${attempts}/${maxAttempts}\nStreak: ${stats.streak}`;try{await navigator.clipboard.writeText(text);$('#shareBtn').textContent='Copied!';setTimeout(()=>$('#shareBtn').textContent='Share result',1200)}catch{alert(text)}});
  document.querySelectorAll('.mode-btn').forEach(btn=>btn.addEventListener('click',()=>{mode=btn.dataset.mode;localStorage.setItem('nav_mode',mode);document.querySelectorAll('.mode-btn').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));startRound()}));

  loadCachedRosters();rebuildPlayerIndex();updateIndexStatus();document.querySelectorAll('.mode-btn').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));renderStats();startRound();
})();

import re, json, pathlib, html
src=pathlib.Path('/mnt/data/name-a-vol-single.html').read_text()
m=re.search(r'window\.VOL_ROSTERS\s*=\s*(\{.*?\});\s*</script>', src, re.S)
if not m:
    raise SystemExit('roster object not found')
rosters=json.loads(m.group(1))
print('seed years', sorted(rosters), 'players', sum(map(len,rosters.values())))
roster_json=json.dumps(rosters, ensure_ascii=False, separators=(',',':'))
years=list(range(1990,2027))

css=r'''
:root{--orange:#ff8200;--cream:#fff8ef;--ink:#171717;--muted:#6b665f;--card:#fff;--line:#e8ded2;--good:#1c7c54;--bad:#b42318;--shadow:0 18px 50px rgba(54,35,13,.08)}
*{box-sizing:border-box}body{margin:0;min-height:100vh;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);background:radial-gradient(circle at 15% 10%,rgba(255,130,0,.16),transparent 26rem),linear-gradient(180deg,#fffaf4 0%,#fff 52%,#fffaf4 100%)}
.shell{width:min(760px,calc(100% - 28px));margin:0 auto;padding:28px 0 52px}header{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:36px}.brand{display:flex;align-items:center;gap:12px}.badge{width:44px;height:44px;border-radius:12px;display:grid;place-items:center;background:var(--orange);color:white;font-weight:950;font-size:24px;letter-spacing:-1px;box-shadow:0 8px 24px rgba(255,130,0,.25)}h1{margin:0;font-size:24px;line-height:1;letter-spacing:-.03em}.subbrand{color:var(--muted);font-size:12px;margin-top:4px}.stats{display:flex;gap:8px}.stat{min-width:66px;border:1px solid var(--line);border-radius:12px;padding:8px 10px;background:rgba(255,255,255,.8);text-align:center}.stat strong{display:block;font-size:16px}.stat span{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.09em}
.card{background:rgba(255,255,255,.94);border:1px solid var(--line);border-radius:22px;box-shadow:var(--shadow);overflow:visible}.topbar{height:8px;background:var(--orange);border-radius:22px 22px 0 0}.content{padding:32px}.eyebrow{color:var(--orange);font-size:12px;text-transform:uppercase;letter-spacing:.16em;font-weight:900;margin-bottom:12px}.prompt{font-size:clamp(29px,6vw,48px);line-height:1.02;letter-spacing:-.055em;font-weight:950;margin:0 0 10px}.prompt .year{color:var(--orange)}.help{color:var(--muted);font-size:15px;margin-bottom:24px}.mode-row{display:flex;gap:8px;margin-bottom:20px}.mode-btn{border:1px solid var(--line);background:white;border-radius:999px;padding:8px 12px;font-weight:800;cursor:pointer}.mode-btn.active{background:var(--ink);color:white;border-color:var(--ink)}
form{display:flex;gap:10px;position:relative}.input-wrap{position:relative;flex:1;min-width:0}input{width:100%;border:2px solid var(--line);border-radius:14px;padding:15px 42px 15px 16px;font-size:17px;outline:none;background:#fff}input:focus{border-color:var(--orange);box-shadow:0 0 0 4px rgba(255,130,0,.10)}.search-icon{position:absolute;right:14px;top:50%;transform:translateY(-50%);font-size:18px;color:#91877c;pointer-events:none}.suggestions{display:none;position:absolute;left:0;right:0;top:calc(100% + 7px);z-index:40;background:white;border:1px solid var(--line);border-radius:14px;box-shadow:0 18px 45px rgba(35,25,16,.16);overflow:hidden;max-height:310px;overflow-y:auto}.suggestions.open{display:block}.suggestion{width:100%;display:flex;align-items:center;text-align:left;border:0;border-bottom:1px solid #f2ebe3;background:#fff;padding:12px 14px;cursor:pointer;font-size:15px;font-weight:800;color:var(--ink)}.suggestion:last-child{border-bottom:0}.suggestion:hover,.suggestion.active{background:#fff4e8}.suggestion mark{background:transparent;color:var(--orange);font-weight:950}.no-match{padding:12px 14px;color:var(--muted);font-size:13px}.index-status{font-size:12px;color:var(--muted);margin-top:8px;min-height:18px}.index-status strong{color:var(--ink)}
button.primary{border:0;background:var(--orange);color:white;border-radius:14px;padding:0 20px;font-weight:900;font-size:16px;cursor:pointer;min-width:98px}button.primary:hover{filter:brightness(.96)}button.primary:disabled{opacity:.55;cursor:default}.attempts{display:flex;gap:7px;margin:18px 0 0}.dot{width:10px;height:10px;border-radius:50%;background:#ddd3c7}.dot.used{background:var(--bad)}.message{min-height:28px;margin-top:18px;font-weight:800}.message.good{color:var(--good)}.message.bad{color:var(--bad)}.answer{margin-top:16px;border:1px dashed var(--line);border-radius:14px;padding:14px 16px;color:var(--muted);display:none}.actions{display:none;gap:10px;margin-top:18px;flex-wrap:wrap}.actions button{border:1px solid var(--line);background:white;border-radius:12px;padding:11px 14px;font-weight:850;cursor:pointer}.actions button.next{background:var(--ink);color:white;border-color:var(--ink)}
.loading{display:none;align-items:center;gap:8px;margin:12px 0 0;color:var(--muted);font-size:13px}.loading.show{display:flex}.spinner{width:14px;height:14px;border:2px solid #eaded0;border-top-color:var(--orange);border-radius:50%;animation:spin .8s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
.sources{margin-top:24px;padding:18px;border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.7)}.sources summary{cursor:pointer;font-weight:850}.sources p{color:var(--muted);font-size:13px;line-height:1.55}.footer{text-align:center;color:var(--muted);font-size:12px;margin-top:18px;line-height:1.5}
@media(max-width:620px){header{align-items:flex-start}.stats{gap:5px}.stat{min-width:56px;padding:7px}.content{padding:25px 20px}form{flex-direction:column}button.primary{min-height:50px}.suggestions{top:calc(50px + 7px)}}
'''

js=rf'''
(() => {{
  const START_YEAR = 1990;
  const END_YEAR = 2026;
  const ALL_YEARS = Array.from({{length: END_YEAR-START_YEAR+1}}, (_,i)=>String(START_YEAR+i));
  const rosters = window.VOL_ROSTERS = window.VOL_ROSTERS || {{}};
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
  const stats={{streak:Number(localStorage.getItem('nav_streak')||0),score:Number(localStorage.getItem('nav_score')||0)}};

  function normalize(s){{return String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/&/g,'and').replace(/[’']/g,'').replace(/\b(jr|sr|ii|iii|iv)\b\.?/g,'').replace(/[^a-z0-9]/g,' ').replace(/\s+/g,' ').trim()}}
  function cleanMarkdownName(s){{
    s=String(s||'').trim().replace(/^\[([^\]]+)\]\([^)]+\)$/,'$1').replace(/\*\*/g,'').replace(/<[^>]+>/g,'').trim();
    return s.replace(/\s+/g,' ');
  }}
  function parseRosterMarkdown(text){{
    const names=[];
    for(const raw of String(text||'').split(/\r?\n/)){{
      const line=raw.trim();
      if(!line.includes('|')) continue;
      const cells=line.split('|').map(x=>x.trim());
      if(cells.length<3) continue;
      const jersey=cells[0].replace(/[*_]/g,'').trim();
      if(!/^\d{{1,2}}$/.test(jersey)) continue;
      const name=cleanMarkdownName(cells[1]);
      if(!name || /^(name|image)$/i.test(name) || name.length<3 || name.length>60) continue;
      if(!/[a-z]/i.test(name)) continue;
      names.push(name);
    }}
    // Fallback for Reader output that omits the compact table.
    if(names.length<20){{
      for(const m of String(text||'').matchAll(/Full Bio for\s+([^\n\r]+)/gi)){{
        const name=cleanMarkdownName(m[1]);
        if(name && name.length<60) names.push(name);
      }}
    }}
    return [...new Map(names.map(n=>[normalize(n),n])).values()];
  }}
  function cacheKey(year){{return `nav_roster_${{cacheVersion}}_${{year}}`}}
  function loadCachedRosters(){{
    ALL_YEARS.forEach(y=>{{
      try{{const x=JSON.parse(localStorage.getItem(cacheKey(y))||'null');if(Array.isArray(x)&&x.length>=20)rosters[y]=x}}catch{{}}
    }});
  }}
  async function fetchOfficialRoster(year){{
    const target=`https://utsports.com/sports/football/roster/${{year}}`;
    const reader=`https://r.jina.ai/${{target}}`;
    const res=await fetch(reader,{{headers:{{'Accept':'text/plain'}}}});
    if(!res.ok) throw new Error(`Roster source returned ${{res.status}}`);
    const text=await res.text();
    const names=parseRosterMarkdown(text);
    if(names.length<20) throw new Error(`Only found ${{names.length}} players`);
    rosters[year]=names;
    try{{localStorage.setItem(cacheKey(year),JSON.stringify(names))}}catch{{}}
    rebuildPlayerIndex();
    updateIndexStatus();
    return names;
  }}
  async function ensureRoster(year){{
    if(Array.isArray(rosters[year])&&rosters[year].length>=20) return rosters[year];
    return fetchOfficialRoster(year);
  }}
  function sleep(ms){{return new Promise(r=>setTimeout(r,ms))}}
  async function preloadAllRosters(){{
    if(indexPromise) return indexPromise;
    indexStarted=true;
    updateIndexStatus();
    indexPromise=(async()=>{{
      const missing=ALL_YEARS.filter(y=>!(Array.isArray(rosters[y])&&rosters[y].length>=20));
      // Small batches keep the free reader endpoint from being hammered.
      for(let i=0;i<missing.length;i+=3){{
        const batch=missing.slice(i,i+3);
        await Promise.all(batch.map(async y=>{{
          try{{await fetchOfficialRoster(y)}}catch(e){{console.warn('Could not load',y,e.message)}}
        }}));
        updateIndexStatus();
        if(i+3<missing.length) await sleep(650);
      }}
      updateIndexStatus(true);
    }})();
    return indexPromise;
  }}

  let playerIndex=[];
  function rebuildPlayerIndex(){{
    const map=new Map();
    Object.entries(rosters).forEach(([year,list])=>{{
      (list||[]).forEach(name=>{{
        const key=normalize(name); if(!key) return;
        if(!map.has(key)) map.set(key,{{name,years:[]}});
        map.get(key).years.push(year);
      }})
    }});
    playerIndex=[...map.values()].sort((a,b)=>a.name.localeCompare(b.name));
  }}
  function loadedSeasonCount(){{return ALL_YEARS.filter(y=>Array.isArray(rosters[y])&&rosters[y].length>=20).length}}
  function updateIndexStatus(done=false){{
    const n=loadedSeasonCount();
    if(n===ALL_YEARS.length) indexStatus.innerHTML=`Player search: <strong>${{playerIndex.length.toLocaleString()}} names</strong> from all 37 seasons.`;
    else if(indexStarted) indexStatus.innerHTML=`Building player search… <strong>${{n}}/37 seasons</strong> loaded.`;
    else indexStatus.textContent='Start typing to search Tennessee players from every season.';
  }}

  function levenshtein(a,b){{const dp=Array.from({{length:a.length+1}},()=>Array(b.length+1).fill(0));for(let i=0;i<=a.length;i++)dp[i][0]=i;for(let j=0;j<=b.length;j++)dp[0][j]=j;for(let i=1;i<=a.length;i++)for(let j=1;j<=b.length;j++)dp[i][j]=Math.min(dp[i-1][j]+1,dp[i][j-1]+1,dp[i-1][j-1]+(a[i-1]===b[j-1]?0:1));return dp[a.length][b.length]}}
  function matchGuess(guess,roster){{const g=normalize(guess);if(!g||g.length<3)return null;for(const player of roster){{const p=normalize(player);if(g===p)return player;const tolerance=p.length>=14?2:1;if(Math.abs(g.length-p.length)<=tolerance&&levenshtein(g,p)<=tolerance)return player}}return null}}
  function seededDailyYear(){{const d=new Date(), key=Number(`${{d.getFullYear()}}${{String(d.getMonth()+1).padStart(2,'0')}}${{String(d.getDate()).padStart(2,'0')}}`);return ALL_YEARS[key%ALL_YEARS.length]}}
  function chooseYear(){{if(mode==='daily')return seededDailyYear();const pool=ALL_YEARS.filter(y=>y!==currentYear);return pool[Math.floor(Math.random()*pool.length)]}}
  function renderStats(){{streakEl.textContent=stats.streak;scoreEl.textContent=stats.score;seasonCountEl.textContent=ALL_YEARS.length}}
  function renderDots(){{const wrap=$('#attempts');wrap.innerHTML='';for(let i=0;i<maxAttempts;i++){{const d=document.createElement('div');d.className='dot'+(i<attempts?' used':'');wrap.appendChild(d)}}}}
  function closeSuggestions(){{suggestionsEl.classList.remove('open');activeSuggestion=-1}}
  function highlightName(name,q){{
    const nq=normalize(q); if(!nq) return escapeHtml(name);
    const lower=name.toLowerCase(), raw=q.trim().toLowerCase();
    let idx=lower.indexOf(raw); if(idx<0) return escapeHtml(name);
    return escapeHtml(name.slice(0,idx))+'<mark>'+escapeHtml(name.slice(idx,idx+raw.length))+'</mark>'+escapeHtml(name.slice(idx+raw.length));
  }}
  function escapeHtml(s){{return String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}}[c]))}}
  function searchPlayers(q){{
    const nq=normalize(q); if(nq.length<1)return [];
    const terms=nq.split(' ');
    return playerIndex.map(p=>{{
      const n=normalize(p.name), tokens=n.split(' ');let score=99;
      if(n.startsWith(nq))score=0;
      else if(tokens.some(t=>t.startsWith(nq)))score=1;
      else if(terms.every(term=>tokens.some(t=>t.startsWith(term))))score=2;
      else if(n.includes(nq))score=3;
      return {{...p,score}};
    }}).filter(x=>x.score<99).sort((a,b)=>a.score-b.score||a.name.localeCompare(b.name)).slice(0,9);
  }}
  function renderSuggestions(){{
    const q=input.value.trim(); if(!q){{closeSuggestions();return}}
    visibleSuggestions=searchPlayers(q);activeSuggestion=-1;
    if(!visibleSuggestions.length){{suggestionsEl.innerHTML='<div class="no-match">No matching Tennessee player loaded yet.</div>';suggestionsEl.classList.add('open');return}}
    suggestionsEl.innerHTML=visibleSuggestions.map((p,i)=>`<button type="button" class="suggestion" data-i="${{i}}">${{highlightName(p.name,q)}}</button>`).join('');
    suggestionsEl.classList.add('open');
  }}
  function selectSuggestion(i){{const p=visibleSuggestions[i];if(!p)return;input.value=p.name;closeSuggestions();input.focus()}}
  function moveSuggestion(dir){{
    if(!suggestionsEl.classList.contains('open')||!visibleSuggestions.length)return false;
    activeSuggestion=(activeSuggestion+dir+visibleSuggestions.length)%visibleSuggestions.length;
    [...suggestionsEl.querySelectorAll('.suggestion')].forEach((el,i)=>el.classList.toggle('active',i===activeSuggestion));
    suggestionsEl.querySelector('.suggestion.active')?.scrollIntoView({{block:'nearest'}});return true;
  }}

  async function startRound(){{
    currentYear=chooseYear();attempts=0;finished=false;roundLoading=true;yearEl.textContent=currentYear;input.value='';input.disabled=true;submitBtn.disabled=true;message.textContent='';message.className='message';answer.style.display='none';answer.textContent='';actions.style.display='none';closeSuggestions();renderDots();roundLoader.classList.add('show');
    try{{await ensureRoster(currentYear);message.textContent=''}}catch(e){{
      message.textContent=`Could not load the ${{currentYear}} roster. Check your connection and try Next season.`;message.className='message bad';actions.style.display='flex';roundLoading=false;roundLoader.classList.remove('show');return;
    }}
    roundLoading=false;roundLoader.classList.remove('show');input.disabled=false;submitBtn.disabled=false;input.focus();
  }}
  function endRound(win,matchedPlayer=null){{finished=true;input.disabled=true;closeSuggestions();const roster=rosters[currentYear];if(win){{stats.streak++;stats.score+=Math.max(1,4-attempts);message.textContent=`${{matchedPlayer}}. That Vol rocked.`;message.className='message good'}}else{{stats.streak=0;const reveal=roster[Math.floor(Math.random()*roster.length)];message.textContent='Nope — three strikes.';message.className='message bad';answer.textContent=`One answer: ${{reveal}}`;answer.style.display='block'}}localStorage.setItem('nav_streak',stats.streak);localStorage.setItem('nav_score',stats.score);renderStats();actions.style.display='flex'}}

  input.addEventListener('focus',()=>{{if(!indexStarted)preloadAllRosters();if(input.value.trim())renderSuggestions()}});
  input.addEventListener('input',()=>{{if(!indexStarted)preloadAllRosters();renderSuggestions()}});
  input.addEventListener('keydown',e=>{{
    if(e.key==='ArrowDown'){{if(moveSuggestion(1))e.preventDefault()}}
    else if(e.key==='ArrowUp'){{if(moveSuggestion(-1))e.preventDefault()}}
    else if(e.key==='Escape')closeSuggestions();
    else if(e.key==='Enter'&&activeSuggestion>=0){{e.preventDefault();selectSuggestion(activeSuggestion)}}
  }});
  suggestionsEl.addEventListener('mousedown',e=>{{const b=e.target.closest('.suggestion');if(!b)return;e.preventDefault();selectSuggestion(Number(b.dataset.i))}});
  document.addEventListener('click',e=>{{if(!e.target.closest('.input-wrap'))closeSuggestions()}});

  form.addEventListener('submit',e=>{{e.preventDefault();if(finished||roundLoading)return;const guess=input.value.trim();if(!guess)return;const matched=matchGuess(guess,rosters[currentYear]);attempts++;renderDots();if(matched){{endRound(true,matched);return}}if(attempts>=maxAttempts)endRound(false);else{{message.textContent=`Not on the ${{currentYear}} roster. ${{maxAttempts-attempts}} guess${{maxAttempts-attempts===1?'':'es'}} left.`;message.className='message bad';input.select();renderSuggestions()}}}});
  $('#nextBtn').addEventListener('click',startRound);
  $('#shareBtn').addEventListener('click',async()=>{{const result=message.classList.contains('good')?'🟧':'⬛',text=`Name a Vol — ${{currentYear}}\n${{result}} ${{attempts}}/${{maxAttempts}}\nStreak: ${{stats.streak}}`;try{{await navigator.clipboard.writeText(text);$('#shareBtn').textContent='Copied!';setTimeout(()=>$('#shareBtn').textContent='Share result',1200)}}catch{{alert(text)}}}});
  document.querySelectorAll('.mode-btn').forEach(btn=>btn.addEventListener('click',()=>{{mode=btn.dataset.mode;localStorage.setItem('nav_mode',mode);document.querySelectorAll('.mode-btn').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));startRound()}}));

  loadCachedRosters();rebuildPlayerIndex();updateIndexStatus();document.querySelectorAll('.mode-btn').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));renderStats();startRound();
}})();
'''

html_doc=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#ff8200"><title>Name a Vol</title><style>{css}</style></head>
<body><main class="shell">
<header><div class="brand"><div class="badge">V</div><div><h1>Name a Vol</h1><div class="subbrand">Tennessee football roster trivia</div></div></div><div class="stats"><div class="stat"><strong id="streak">0</strong><span>Streak</span></div><div class="stat"><strong id="score">0</strong><span>Score</span></div><div class="stat"><strong id="seasonCount">37</strong><span>Years</span></div></div></header>
<section class="card"><div class="topbar"></div><div class="content"><div class="mode-row"><button class="mode-btn" data-mode="endless" type="button">Endless</button><button class="mode-btn" data-mode="daily" type="button">Daily</button></div><div class="eyebrow">Name one player</div><p class="prompt">Who played for the <span class="year" id="year">1998</span> Tennessee Volunteers?</p><div class="help">Any player on that season's roster counts. You get three guesses.</div>
<form id="guessForm" autocomplete="off"><div class="input-wrap"><input id="player" type="text" placeholder="Start typing a Tennessee player…" aria-label="Player name" aria-autocomplete="list" aria-controls="suggestions"><span class="search-icon">⌕</span><div id="suggestions" class="suggestions" role="listbox"></div></div><button id="submitBtn" class="primary" type="submit">Submit</button></form>
<div id="indexStatus" class="index-status"></div><div id="roundLoader" class="loading"><span class="spinner"></span><span>Loading official <strong id="loadingYear">Tennessee</strong> roster…</span></div><div id="attempts" class="attempts" aria-label="Attempts"></div><div id="message" class="message" aria-live="polite"></div><div id="answer" class="answer"></div><div id="actions" class="actions"><button id="nextBtn" class="next" type="button">Next season</button><button id="shareBtn" type="button">Share result</button></div></div></section>
<details class="sources"><summary>Roster data</summary><p>Seasons run from 1990 through 2026. Six rosters are bundled into this prototype for instant play. The remaining seasons are pulled from the University of Tennessee Athletics roster archive through a reader endpoint and cached in your browser. Once loaded, the autocomplete searches the combined player list across all 37 seasons.</p><p>The search list deliberately shows names only — not seasons — so it doesn't reveal whether a suggestion is correct for the year on screen.</p></details><div class="footer">Independent fan project. Not affiliated with or endorsed by the University of Tennessee, NCAA, or SEC.</div></main>
<script>window.VOL_ROSTERS={roster_json};</script><script>{js}</script></body></html>'''

out=pathlib.Path('/mnt/data/name-a-vol-single.html');out.write_text(html_doc)
proj=pathlib.Path('/mnt/data/name-a-vol');proj.mkdir(exist_ok=True)
(proj/'index.html').write_text(html_doc)
(proj/'README.md').write_text('''# Name a Vol\n\nTennessee football roster trivia prototype.\n\n## What changed\n- Seasons: 1990–2026 (37 total)\n- Live autocomplete searches the combined player index by first or last name\n- Keyboard navigation: Up/Down + Enter\n- Suggestions do not show seasons, so they do not give away the answer\n- Six rosters are bundled for instant play; remaining official rosters are fetched from the UT Athletics roster archive through Jina Reader and cached locally\n\nOpen `index.html` in a browser with internet access. After the all-season index has loaded once, cached rosters remain available in that browser.\n''')
print('wrote', out, len(html_doc))

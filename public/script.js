/* ── Constants ───────────────────────────────────────────────────── */
const FREE_USES    = 1;
const USED_KEY     = 'tai_used';
const SESSION_KEY  = 'tai_key';
const HISTORY_KEY  = 'tai_history';

/* ── Usage helpers ───────────────────────────────────────────────── */
function usesLeft() {
  return Math.max(0, FREE_USES - parseInt(localStorage.getItem(USED_KEY) || '0', 10));
}
function consumeUse() {
  localStorage.setItem(USED_KEY, (parseInt(localStorage.getItem(USED_KEY) || '0', 10) + 1).toString());
}
function getUserKey() { return sessionStorage.getItem(SESSION_KEY) || null; }
function setUserKey(k) { k ? sessionStorage.setItem(SESSION_KEY, k) : sessionStorage.removeItem(SESSION_KEY); }

function updateUsageBadge() {
  const ind   = el('usage-indicator');
  const label = el('usage-label');
  const key   = getUserKey();
  const sm    = window.innerWidth <= 520;
  if (key) {
    ind.className = 'usage-indicator byok';
    label.textContent = sm ? 'My key' : 'Using your key';
  } else if (usesLeft() > 0) {
    ind.className = 'usage-indicator';
    label.textContent = sm ? `${usesLeft()} free left` : `${usesLeft()} free use remaining`;
  } else {
    ind.className = 'usage-indicator exhausted';
    label.textContent = sm ? 'Free used' : 'Free use exhausted';
  }
}

/* ── DOM shortcuts ───────────────────────────────────────────────── */
const el = id => document.getElementById(id);

/* ── Workspace state machine ─────────────────────────────────────── */
const STATES = ['state-upload', 'state-processing', 'state-result'];
function setState(s) {
  STATES.forEach(id => el(id).classList.toggle('hidden', id !== s));
  if (s !== 'state-result') el('layout').classList.remove('mobile-results');
}

/* ── Pipeline ────────────────────────────────────────────────────── */
const PIPE_STAGES = ['upload', 'transcribe', 'analyze'];

function setPipe(active) {
  const idx = PIPE_STAGES.indexOf(active);
  PIPE_STAGES.forEach((s, i) => {
    const node = el('pipe-' + s);
    node.classList.remove('active', 'done');
    if (i < idx)      node.classList.add('done');
    else if (i === idx) node.classList.add('active');
  });
  [el('track-1'), el('track-2')].forEach((t, i) => {
    t.style.width = i < idx ? '100%' : '0%';
  });
}

function pipeAllDone() {
  PIPE_STAGES.forEach(s => {
    const n = el('pipe-' + s);
    n.classList.remove('active');
    n.classList.add('done');
  });
  [el('track-1'), el('track-2')].forEach(t => t.style.width = '100%');
}

/* ── Waveform ────────────────────────────────────────────────────── */
function buildWaveform() {
  const w = el('waveform');
  w.innerHTML = '';
  for (let i = 0; i < 30; i++) {
    const b = document.createElement('div');
    b.className = 'waveform-bar';
    b.style.animationDelay    = `${(i * 0.065).toFixed(3)}s`;
    b.style.animationDuration = `${(0.65 + (i % 7) * 0.07).toFixed(2)}s`;
    w.appendChild(b);
  }
}

/* ── BYOK strip ──────────────────────────────────────────────────── */
el('byok-toggle').addEventListener('click', () => {
  const strip = el('byok-strip');
  const open  = strip.classList.toggle('hidden') === false;
  document.getElementById('app').classList.toggle('byok-open', open);
  if (open) {
    const existing = getUserKey();
    if (existing) el('byok-input').value = existing;
    el('byok-input').focus();
  }
});

el('byok-apply').addEventListener('click', applyByok);
el('byok-input').addEventListener('keydown', e => { if (e.key === 'Enter') applyByok(); });

function applyByok() {
  const k = el('byok-input').value.trim();
  if (!k.startsWith('sk-')) {
    flash(el('byok-input'), 'error');
    return;
  }
  setUserKey(k);
  updateUsageBadge();
  el('byok-strip').classList.add('hidden');
  document.getElementById('app').classList.remove('byok-open');
}

el('byok-remove').addEventListener('click', () => {
  setUserKey(null);
  el('byok-input').value = '';
  updateUsageBadge();
  el('byok-strip').classList.add('hidden');
  document.getElementById('app').classList.remove('byok-open');
});

function flash(input, cls) {
  input.classList.add(cls);
  setTimeout(() => input.classList.remove(cls), 1400);
}

/* ── Rate limit modal ────────────────────────────────────────────── */
function showLimitModal() {
  return new Promise(resolve => {
    const modal = el('limit-modal');
    const input = el('modal-key');
    modal.classList.remove('hidden');
    input.value = '';
    input.focus();

    function cleanup() {
      modal.classList.add('hidden');
      el('modal-continue').removeEventListener('click', onGo);
      el('modal-cancel').removeEventListener('click', onNo);
      input.removeEventListener('keydown', onEnter);
    }

    function onGo() {
      const k = input.value.trim();
      if (!k.startsWith('sk-')) { flash(input, 'error'); return; }
      setUserKey(k);
      updateUsageBadge();
      cleanup();
      resolve(true);
    }

    function onNo() { cleanup(); resolve(false); }
    function onEnter(e) { if (e.key === 'Enter') onGo(); }

    el('modal-continue').addEventListener('click', onGo);
    el('modal-cancel').addEventListener('click', onNo);
    input.addEventListener('keydown', onEnter);
  });
}

async function canProceed() {
  if (getUserKey()) return true;
  if (usesLeft() > 0) return true;
  return showLimitModal();
}

/* ── Drag & drop / file input ────────────────────────────────────── */
const dropZone = el('drop-zone');
const fileInput = el('file-input');

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  const files = Array.from(e.dataTransfer.files);
  if (files.length) handleFile(files[0]);
});

dropZone.addEventListener('click', () => fileInput.click());
el('browse-btn').addEventListener('click', e => { e.stopPropagation(); fileInput.click(); });
fileInput.addEventListener('change', () => {
  if (fileInput.files.length) handleFile(fileInput.files[0]);
  fileInput.value = '';
});

/* ── Core upload flow ────────────────────────────────────────────── */
async function handleFile(file) {
  if (!(await canProceed())) return;
  await runUpload(file);
}

async function runUpload(file) {
  /* switch to processing UI */
  setState('state-processing');
  el('proc-name').textContent = file.name;
  el('proc-label').textContent = 'Uploading…';
  setPipe('upload');
  buildWaveform();

  /* reset analysis panel */
  el('analysis-empty').classList.remove('hidden');
  el('analysis-content').classList.add('hidden');
  el('analysis-status').classList.remove('hidden');

  const formData = new FormData();
  formData.append('audio', file);

  const headers = {};
  const userKey = getUserKey();
  if (userKey) headers['X-OpenAI-Key'] = userKey;

  let data;
  try {
    data = await xhrUpload('/transcribe-and-analyze', formData, headers, pct => {
      if (pct === 100) {
        setPipe('transcribe');
        el('proc-label').textContent = 'Transcribing…';
      }
    });
  } catch (err) {
    showError(err.message);
    return;
  }

  /* transition to analyze stage */
  setPipe('analyze');
  el('proc-label').textContent = 'Analyzing…';
  await pause(350);

  /* consume free use if applicable */
  if (!getUserKey()) consumeUse();
  updateUsageBadge();

  pipeAllDone();
  await pause(280);

  /* show results */
  showResult(file.name, data);
  addHistory(file.name, data);
}

function xhrUpload(url, formData, headers, onUploadProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url, true);
    Object.entries(headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));

    xhr.upload.onprogress = e => {
      if (e.lengthComputable) onUploadProgress(Math.round(e.loaded / e.total * 100));
    };

    xhr.onload = () => {
      if (xhr.status === 200) {
        try { resolve(JSON.parse(xhr.responseText)); }
        catch { reject(new Error('Invalid server response')); }
      } else {
        let msg = 'Upload failed';
        try { msg = JSON.parse(xhr.responseText).error || msg; } catch {}
        reject(new Error(msg));
      }
    };

    xhr.onerror = () => reject(new Error('Network error — is the server running?'));
    xhr.send(formData);
  });
}

async function showError(msg) {
  el('proc-label').textContent = `Error: ${msg}`;
  el('proc-label').style.color = 'var(--red)';
  el('proc-spinner').style.display = 'none';
  await pause(2500);
  el('proc-label').style.color = '';
  el('proc-spinner').style.display = '';
  setState('state-upload');
}

/* ── Display results ─────────────────────────────────────────────── */
function showResult(filename, data) {
  el('result-filename').textContent = filename;
  el('transcript-text').textContent = data.text || '(empty transcript)';

  el('analysis-status').classList.add('hidden');
  el('analysis-empty').classList.add('hidden');

  fillSection('a-notes',   data.notes,   'notes');
  fillSection('a-summary', data.summary, 'summary');
  fillSection('a-actions', data.action,  'actions');

  el('analysis-content').classList.remove('hidden');
  el('analysis-content').classList.add('fade-up');

  setState('state-result');
  if (window.innerWidth <= 520) el('layout').classList.add('mobile-results');
}

function fillSection(id, content, type) {
  const container = el(id);
  container.innerHTML = '';
  container.className = 'a-body';

  if (!content) {
    container.textContent = 'No data available.';
    return;
  }

  if (Array.isArray(content)) {
    const ul = document.createElement('ul');
    if (type === 'actions') { ul.className = 'actions-list'; }
    content.forEach(item => {
      const li = document.createElement('li');
      if (type === 'actions') li.className = 'action-item';
      li.textContent = item;
      ul.appendChild(li);
    });
    container.appendChild(ul);
  } else if (typeof content === 'string' && content.includes('\n')) {
    /* multi-line string from notes/actions */
    const lines = content.split('\n').filter(l => l.trim());
    const ul = document.createElement('ul');
    lines.forEach(line => {
      const li = document.createElement('li');
      li.textContent = line.replace(/^[•\-\d.]\s*/, '');
      ul.appendChild(li);
    });
    container.appendChild(ul);
  } else {
    container.textContent = content;
  }
}

/* ── Copy & New ──────────────────────────────────────────────────── */
el('copy-btn').addEventListener('click', async () => {
  const text = el('transcript-text').textContent;
  await navigator.clipboard.writeText(text).catch(() => {});
  el('copy-btn').textContent = 'Copied!';
  setTimeout(() => {
    el('copy-btn').innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg> Copy`;
  }, 2000);
});

el('new-btn').addEventListener('click', () => {
  setState('state-upload');
});

/* ── History ─────────────────────────────────────────────────────── */
function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
  catch { return []; }
}

function saveHistory(h) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(h));
}

function addHistory(filename, data) {
  const h = loadHistory();
  h.unshift({ id: Date.now(), filename, timestamp: new Date().toISOString(), data });
  if (h.length > 30) h.pop();
  saveHistory(h);
  renderHistory(h);
}

function renderHistory(history) {
  const list = el('history-list');
  if (!history.length) {
    list.innerHTML = `
      <div class="sidebar-empty">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 00-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0020 4.77 5.07 5.07 0 0019.91 1S18.73.65 16 2.48a13.38 13.38 0 00-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 005 4.77a5.44 5.44 0 00-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 009 18.13V22"/>
        </svg>
        <p>No sessions yet</p>
        <p class="muted">Drop an audio file to start</p>
      </div>`;
    return;
  }

  list.innerHTML = '';
  history.forEach(item => {
    const div = document.createElement('div');
    div.className = 'history-item fade-up';
    div.dataset.id = item.id;

    const time = new Date(item.timestamp);
    const timeStr = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    div.innerHTML = `
      <div class="hi-name">${esc(item.filename)}</div>
      <div class="hi-time">${timeStr}</div>
      <div class="hi-preview">${esc((item.data.text || '').substring(0, 58))}${(item.data.text || '').length > 58 ? '…' : ''}</div>
    `;

    div.addEventListener('click', () => {
      document.querySelectorAll('.history-item').forEach(i => i.classList.remove('active'));
      div.classList.add('active');
      showResult(item.filename, item.data);
    });

    list.appendChild(div);
  });
}

el('clear-all').addEventListener('click', () => {
  if (!confirm('Clear all session history?')) return;
  saveHistory([]);
  renderHistory([]);
  setState('state-upload');
  el('analysis-empty').classList.remove('hidden');
  el('analysis-content').classList.add('hidden');
});

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function pause(ms) { return new Promise(r => setTimeout(r, ms)); }

/* ── Init ────────────────────────────────────────────────────────── */
updateUsageBadge();
renderHistory(loadHistory());
setState('state-upload');

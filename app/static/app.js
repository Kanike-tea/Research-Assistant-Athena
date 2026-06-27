/* ================================================================
   Research Assistant — Dashboard Controller
   SSE streaming consumer with per-component state management
   ================================================================ */

(() => {
  'use strict';

  // ── Channel Keys ──────────────────────────────────────────────
  const CHANNELS = ['category', 'summary', 'keywords', 'explanation'];
  const TOTAL    = CHANNELS.length;

  // ── DOM Cache ─────────────────────────────────────────────────
  const dom = {
    form:         document.getElementById('search-form'),
    input:        document.getElementById('topic-input'),
    btn:          document.getElementById('btn-execute'),
    progressBar:  document.getElementById('progress-bar'),
    progressFill: document.getElementById('progress-fill'),
    progressLabel:document.getElementById('progress-label'),
    errorBanner:  document.getElementById('error-banner'),
    errorMessage: document.getElementById('error-message'),
    statusDot:    document.getElementById('status-dot'),
    statusText:   document.getElementById('status-text'),
    themeBtn:     document.getElementById('theme-toggle'),
  };

  // ── Theme Management ──────────────────────────────────────────
  function initTheme() {
    const stored = localStorage.getItem('theme');
    if (stored === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    }
    
    dom.themeBtn.addEventListener('click', () => {
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';
      if (isLight) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
      }
    });
  }
  initTheme();

  // Per-channel panel & body refs
  const panels = {};
  const bodies = {};
  CHANNELS.forEach(ch => {
    panels[ch] = document.getElementById(`panel-${ch}`);
    bodies[ch] = document.getElementById(`body-${ch}`);
  });


  // ── Skeleton HTML ─────────────────────────────────────────────
  const SKELETONS = {
    category:    '<div class="skel skel-badge"></div>',
    summary:     '<div class="skel skel-line"></div>'.repeat(3),
    keywords:    '<span class="skel skel-pill"></span>'.repeat(6),
    explanation: '<div class="skel skel-line"></div>'.repeat(6),
  };


  // ── State ─────────────────────────────────────────────────────
  let completed = 0;


  // ── Panel State Machine ───────────────────────────────────────
  function setPanelState(channel, state) {
    const panel = panels[channel];
    if (!panel) return;
    panel.setAttribute('data-state', state);
  }

  function resetAllPanels() {
    CHANNELS.forEach(ch => {
      setPanelState(ch, 'skeleton');
      bodies[ch].innerHTML = SKELETONS[ch];
    });
  }

  function setAllProcessing() {
    CHANNELS.forEach(ch => setPanelState(ch, 'processing'));
  }


  // ── Progress Bar ──────────────────────────────────────────────
  function showProgress() {
    dom.progressBar.classList.add('visible');
    updateProgress(0);
  }

  function hideProgress() {
    dom.progressBar.classList.remove('visible');
  }

  function updateProgress(count) {
    completed = count;
    const pct = Math.round((count / TOTAL) * 100);
    dom.progressFill.style.width = `${pct}%`;
    dom.progressLabel.textContent = `${count} / ${TOTAL} tasks`;
  }


  // ── Header Status ─────────────────────────────────────────────
  function setHeaderStatus(mode) {
    const dot  = dom.statusDot;
    const text = dom.statusText;
    dot.classList.remove('ready', 'processing');

    switch (mode) {
      case 'ready':
        dot.classList.add('ready');
        text.textContent = 'READY';
        break;
      case 'processing':
        dot.classList.add('processing');
        text.textContent = 'PROCESSING';
        break;
      case 'done':
        dot.classList.add('ready');
        text.textContent = 'COMPLETE';
        break;
    }
  }


  // ── Error ─────────────────────────────────────────────────────
  function showError(msg) {
    dom.errorMessage.textContent = msg;
    dom.errorBanner.classList.add('visible');
  }

  function hideError() {
    dom.errorBanner.classList.remove('visible');
  }


  // ── Loading State ─────────────────────────────────────────────
  function setLoading(on) {
    dom.btn.classList.toggle('loading', on);
    dom.btn.disabled   = on;
    dom.input.disabled = on;
  }


  // ── Content Renderers (per-channel) ───────────────────────────
  // Each renders content as a COMPLETE BLOCK — no typing animation.

  const renderers = {
    category(value) {
      bodies.category.innerHTML = `<div class="category-badge">${esc(value)}</div>`;
    },

    summary(value) {
      bodies.summary.innerHTML = `<p class="summary-text">${esc(value)}</p>`;
    },

    keywords(value) {
      const list = Array.isArray(value) ? value : [value];
      const pills = list.map(kw => `<li class="kw-pill">${esc(kw)}</li>`).join('');
      bodies.keywords.innerHTML = `<ul class="kw-cloud">${pills}</ul>`;
    },

    explanation(value) {
      const html = typeof marked !== 'undefined' && marked.parse
        ? marked.parse(value)
        : `<p>${esc(value)}</p>`;
      bodies.explanation.innerHTML = `<div class="md-content">${html}</div>`;
    },
  };


  // ── SSE Stream Consumer ───────────────────────────────────────
  // We use fetch + ReadableStream (not EventSource) because this
  // is a POST endpoint. We parse SSE lines manually.

  async function consumeStream(topic) {
    const response = await fetch('/research/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${response.status})`);
    }

    const reader  = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer    = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE messages are separated by double newlines
      const messages = buffer.split('\n\n');
      // Last element is incomplete — keep in buffer
      buffer = messages.pop();

      for (const msg of messages) {
        if (!msg.trim()) continue;
        processSSEMessage(msg);
      }
    }

    // Process any remaining buffer
    if (buffer.trim()) {
      processSSEMessage(buffer);
    }
  }

  function processSSEMessage(raw) {
    let eventName = '';
    let dataStr   = '';

    for (const line of raw.split('\n')) {
      if (line.startsWith('event: ')) {
        eventName = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        dataStr = line.slice(6);
      }
    }

    if (eventName === 'done') {
      // All tasks complete
      return;
    }

    if (eventName === 'error') {
      try {
        const errData = JSON.parse(dataStr);
        showError(errData.error || 'Pipeline error');
      } catch {
        showError('Pipeline error');
      }
      return;
    }

    // Data channel event
    if (CHANNELS.includes(eventName) && dataStr) {
      try {
        const payload = JSON.parse(dataStr);
        const renderer = renderers[eventName];
        if (renderer) {
          renderer(payload.value);
          setPanelState(eventName, 'populated');
          updateProgress(completed + 1);
        }
      } catch (e) {
        console.error(`Failed to parse ${eventName} data:`, e);
      }
    }
  }


  // ── Form Handler ──────────────────────────────────────────────
  dom.form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const topic = dom.input.value.trim();
    if (!topic) return;

    hideError();
    resetAllPanels();
    setAllProcessing();
    showProgress();
    setLoading(true);
    setHeaderStatus('processing');

    try {
      await consumeStream(topic);
      setHeaderStatus('done');
    } catch (err) {
      showError(err.message || 'An unexpected error occurred.');
      setHeaderStatus('ready');
    } finally {
      setLoading(false);
      // Keep progress visible showing 4/4
      if (completed >= TOTAL) {
        setTimeout(() => hideProgress(), 2000);
      } else {
        hideProgress();
      }
    }
  });


  // ── Utility ───────────────────────────────────────────────────
  function esc(str) {
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
  }

})();

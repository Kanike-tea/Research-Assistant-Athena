/* ================================================================
   Research Assistant — Client-side Application Logic
   Handles form submission, API calls, and UI state management
   ================================================================ */

(() => {
  'use strict';

  // ── DOM References ────────────────────────────────────────────
  const form            = document.getElementById('search-form');
  const topicInput      = document.getElementById('topic-input');
  const btnSearch       = document.getElementById('btn-search');
  const errorBanner     = document.getElementById('error-banner');
  const errorMessage    = document.getElementById('error-message');
  const resultsSection  = document.getElementById('results-section');
  const resultsTopic    = document.getElementById('results-topic');

  const explanationEl   = document.getElementById('explanation-content');
  const summaryEl       = document.getElementById('summary-content');
  const keywordsEl      = document.getElementById('keywords-content');
  const categoryEl      = document.getElementById('category-content');


  // ── Skeleton HTML generators ──────────────────────────────────
  function skeletonLines(count) {
    return Array.from({ length: count }, () =>
      `<div class="skeleton skeleton-line"></div>`
    ).join('');
  }

  function skeletonPills(count) {
    return Array.from({ length: count }, () =>
      `<span class="skeleton skeleton-pill"></span>`
    ).join('');
  }

  function skeletonBadge() {
    return `<div class="skeleton skeleton-badge"></div>`;
  }

  function showSkeletons() {
    explanationEl.innerHTML = skeletonLines(8);
    summaryEl.innerHTML     = skeletonLines(3);
    keywordsEl.innerHTML    = skeletonPills(6);
    categoryEl.innerHTML    = skeletonBadge();
  }


  // ── UI State Helpers ──────────────────────────────────────────
  function setLoading(isLoading) {
    btnSearch.classList.toggle('loading', isLoading);
    btnSearch.disabled  = isLoading;
    topicInput.disabled = isLoading;
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorBanner.classList.add('visible');
  }

  function hideError() {
    errorBanner.classList.remove('visible');
  }

  function showResults() {
    resultsSection.classList.add('visible');
  }

  function hideResults() {
    resultsSection.classList.remove('visible');
  }


  // ── Render Results ────────────────────────────────────────────
  function renderExplanation(markdown) {
    const html = typeof marked !== 'undefined' && marked.parse
      ? marked.parse(markdown)
      : `<p>${markdown}</p>`;
    explanationEl.innerHTML = `<div class="markdown-content">${html}</div>`;
  }

  function renderSummary(text) {
    summaryEl.innerHTML = `<p class="summary-text">${escapeHtml(text)}</p>`;
  }

  function renderKeywords(keywords) {
    const pills = keywords.map(kw =>
      `<li class="keyword-pill">${escapeHtml(kw)}</li>`
    ).join('');
    keywordsEl.innerHTML = `<ul class="keywords-list">${pills}</ul>`;
  }

  function renderCategory(category) {
    categoryEl.innerHTML = `
      <div class="category-badge">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
        </svg>
        ${escapeHtml(category)}
      </div>`;
  }

  function renderAll(data) {
    resultsTopic.textContent = data.topic;
    renderExplanation(data.explanation);
    renderSummary(data.summary);
    renderKeywords(data.keywords);
    renderCategory(data.category);

    // Re-trigger card animations by briefly removing & re-adding the class
    const cards = resultsSection.querySelectorAll('.card');
    cards.forEach(card => {
      card.style.animation = 'none';
      // Force reflow
      void card.offsetHeight;
      card.style.animation = '';
    });

    showResults();
  }


  // ── API Call ──────────────────────────────────────────────────
  async function fetchResearch(topic) {
    const response = await fetch('/research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Request failed with status ${response.status}`);
    }

    return response.json();
  }


  // ── Form Handler ──────────────────────────────────────────────
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const topic = topicInput.value.trim();
    if (!topic) return;

    hideError();
    showResults();
    showSkeletons();
    setLoading(true);

    try {
      const data = await fetchResearch(topic);
      renderAll(data);
    } catch (err) {
      hideResults();
      showError(err.message || 'An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  });


  // ── Utility ───────────────────────────────────────────────────
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

})();

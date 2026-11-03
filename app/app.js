/**
 * PROPRESENTER 7 NATIVE PRODUCTION ENGINE - CLIENT CONTROLLER
 * High performance, zero lag, direct Pro7 layout & slide canvas grid
 */

(function () {
  'use strict';

  // State
  const state = {
    allCount: 0,
    currentResults: [],
    renderedCount: 0,
    selectedSong: null,
    rundown: [],
    activeCategory: 'ALL',
    searchTimeout: null,
    toastTimeout: null,
    isLargeFont: false,
    chunkSize: 60
  };

  // DOM Elements
  const statusIndicator = document.getElementById('status-indicator');
  const statusText = document.getElementById('status-text');
  const resultsCount = document.getElementById('results-count');
  const rundownCount = document.getElementById('rundown-count');
  const searchInput = document.getElementById('search-input');
  const clearSearchBtn = document.getElementById('clear-search-btn');
  const filterTabs = document.querySelectorAll('.pro-tab');
  const songListEl = document.getElementById('song-list');
  const inspectorCategoryEl = document.getElementById('inspector-category');
  const inspectorTitleEl = document.getElementById('inspector-song-title');
  const inspectorArtistEl = document.getElementById('inspector-artist');
  const inspectorContentEl = document.getElementById('inspector-content');
  const addToRundownBtn = document.getElementById('add-to-rundown-btn');
  const playlistNameInput = document.getElementById('playlist-name-input');
  const rundownListEl = document.getElementById('rundown-list');
  const clearRundownBtn = document.getElementById('clear-rundown-btn');
  const copyWaBtn = document.getElementById('copy-wa-btn');
  const injectBtn = document.getElementById('inject-btn');
  const modalOverlay = document.getElementById('modal-overlay');
  const modalTitle = document.getElementById('modal-title');
  const modalBody = document.getElementById('modal-body');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const modalOkBtn = document.getElementById('modal-ok-btn');
  const zoomInBtn = document.getElementById('zoom-in-btn');
  const zoomOutBtn = document.getElementById('zoom-out-btn');
  const zoomLevelLabel = document.getElementById('zoom-level-label');
  const fullscreenToggleBtn = document.getElementById('fullscreen-toggle');
  const toastEl = document.getElementById('toast');

  // Scale presets (Default: 1.20)
  const SCALE_STEPS = [1.0, 1.1, 1.2, 1.35, 1.5];
  let currentScale = 1.2;

  function applyScale(scale) {
    currentScale = Math.round(scale * 100) / 100;
    document.documentElement.style.setProperty('--pro-scale', currentScale);
    if (zoomLevelLabel) {
      zoomLevelLabel.textContent = Math.round(currentScale * 100) + '%';
    }
    try {
      localStorage.setItem('pro7_scale', currentScale.toString());
    } catch {
      // Ignore
    }
  }

  function changeScale(direction) {
    let curIdx = SCALE_STEPS.findIndex(s => Math.abs(s - currentScale) < 0.05);
    if (curIdx === -1) curIdx = 2;
    let nextIdx = curIdx + direction;
    if (nextIdx < 0) nextIdx = 0;
    if (nextIdx >= SCALE_STEPS.length) nextIdx = SCALE_STEPS.length - 1;
    applyScale(SCALE_STEPS[nextIdx]);
    showToast(`Display Scale: ${Math.round(SCALE_STEPS[nextIdx] * 100)}%`);
  }

  // Group Color Mapping helper
  function getGroupClass(header) {
    const h = (header || '').toUpperCase();
    if (h.includes('VERSE')) return 'group-verse';
    if (h.includes('CHORUS') && !h.includes('PRE')) return 'group-chorus';
    if (h.includes('BRIDGE')) return 'group-bridge';
    if (h.includes('PRE-CHORUS') || h.includes('PRECHORUS')) return 'group-pre-chorus';
    if (h.includes('BLANK') || h.includes('INTRO')) return 'group-blank';
    if (h.includes('ENDING') || h.includes('OUTRO') || h.includes('TAG')) return 'group-ending';
    return 'group-verse';
  }

  // Initialization
  async function init() {
    loadPreferences();
    setupDefaultPlaylistName();
    setupEventListeners();
    await checkStatus();
    loadSongs();
  }

  function loadPreferences() {
    try {
      const savedScale = parseFloat(localStorage.getItem('pro7_scale'));
      if (savedScale && !isNaN(savedScale)) {
        applyScale(savedScale);
      } else {
        applyScale(1.20);
      }

      const savedRundown = localStorage.getItem('pro7_rundown');
      if (savedRundown) {
        const parsed = JSON.parse(savedRundown);
        if (Array.isArray(parsed)) {
          state.rundown = parsed;
          renderRundown();
        }
      }

      const savedName = localStorage.getItem('pro7_playlist_name');
      if (savedName && playlistNameInput) {
        playlistNameInput.value = savedName;
      }
    } catch {
      // Storage access blocked or unavailable
    }
  }

  function savePreferences() {
    try {
      localStorage.setItem('pro7_rundown', JSON.stringify(state.rundown));
      if (playlistNameInput && playlistNameInput.value) {
        localStorage.setItem('pro7_playlist_name', playlistNameInput.value.trim());
      }
    } catch {
      // Ignore
    }
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  }

  function setupDefaultPlaylistName() {
    if (playlistNameInput && (!playlistNameInput.value || playlistNameInput.value === 'Sunday Service')) {
      const today = new Date();
      const daysUntilSunday = (7 - today.getDay()) % 7;
      const nextSunday = new Date(today);
      nextSunday.setDate(today.getDate() + (daysUntilSunday === 0 ? 0 : daysUntilSunday));

      const options = { day: 'numeric', month: 'short', year: 'numeric' };
      const dateStr = nextSunday.toLocaleDateString('id-ID', options);
      playlistNameInput.value = `Sunday Service - ${dateStr}`;
    }
  }

  // System & ProPresenter Status
  async function checkStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      state.allCount = data.total_songs || 0;

      if (data.catalog_stale) {
        // Catalog in RAM predates the DB on disk (imports / edits happened after start).
        // Old engine builds have no catalog_stale field -> guarded.
        statusIndicator.className = 'pro-dot offline';
        statusText.textContent = 'Library Updated - Reloading...';
        try {
          const r = await fetch('/api/reload');
          const d = await r.json();
          state.allCount = d.total_songs || state.allCount;
          loadSongs();
          statusText.textContent = `ProPresenter 7 Ready (${state.allCount.toLocaleString()} songs)`;
          statusIndicator.className = 'pro-dot';
        } catch {
          statusText.textContent = 'Library Updated - Press Reload';
        }
        return;
      }

      if (data.propresenter_dir) {
        statusIndicator.className = 'pro-dot';
        statusText.textContent = 'ProPresenter 7 Ready';
      } else {
        statusIndicator.className = 'pro-dot offline';
        statusText.textContent = 'Vault Mode (ProPresenter Not Found)';
      }
    } catch {
      statusIndicator.className = 'pro-dot error';
      statusText.textContent = 'Engine Offline';
    }
  }

  // Load Songs with Smart Number Search
  async function loadSongs() {
    let q = searchInput.value.trim();
    songListEl.innerHTML = '<div class="pro-empty-canvas" style="padding: 24px;"><p class="empty-sub-text">Searching Library...</p></div>';

    // Auto-prefix number searches if inside a specific hymnal category
    if (/^\d+$/.test(q) && state.activeCategory !== 'ALL' && state.activeCategory !== 'ID' && state.activeCategory !== 'EN') {
      q = `${state.activeCategory} ${q}`;
    }

    try {
      const url = `/api/songs?q=${encodeURIComponent(q)}&category=${encodeURIComponent(state.activeCategory)}&limit=300`;
      const res = await fetch(url);
      const data = await res.json();
      state.currentResults = data.songs || [];
      state.renderedCount = 0;
      resultsCount.textContent = state.currentResults.length.toLocaleString();
      resetSelection();
      renderSongListInitial();
    } catch {
      songListEl.innerHTML = '<div class="pro-empty-canvas" style="padding: 24px;"><p class="empty-sub-text">Error loading songs</p></div>';
    }
  }

  function resetSelection() {
    state.selectedSong = null;
    addToRundownBtn.disabled = true;
    inspectorCategoryEl.textContent = 'READY';
    inspectorTitleEl.textContent = 'Select a song from Library';
    inspectorArtistEl.textContent = '';
    inspectorContentEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-main-text">No Presentation Selected</p><p class="empty-sub-text">Click any song from the Library on the left to preview slide canvas.</p></div>';
  }

  function renderSongListInitial() {
    songListEl.innerHTML = '';
    state.renderedCount = 0;

    if (!state.currentResults.length) {
      songListEl.innerHTML = '<div class="pro-empty-canvas" style="padding: 24px;"><p class="empty-sub-text">No matching songs in Library</p></div>';
      return;
    }

    appendSongChunk();
  }

  function appendSongChunk() {
    if (state.renderedCount >= state.currentResults.length) return;

    const fragment = document.createDocumentFragment();
    const nextBatch = state.currentResults.slice(state.renderedCount, state.renderedCount + state.chunkSize);

    nextBatch.forEach((song, i) => {
      const globalIdx = state.renderedCount + i;
      const row = document.createElement('div');
      const isSelected = state.selectedSong && state.selectedSong.filename === song.filename;
      row.className = 'pro-row' + (isSelected ? ' selected' : '');
      row.setAttribute('role', 'option');
      row.setAttribute('data-idx', globalIdx);
      row.setAttribute('aria-selected', isSelected ? 'true' : 'false');
      row.setAttribute('tabindex', '-1');
      row.title = song.title;

      row.innerHTML = `
        <div class="pro-row-main">
          <span class="pro-row-title">${escapeHtml(song.title)}</span>
          <span class="pro-row-artist">${escapeHtml(song.artist || '')}</span>
        </div>
        <div class="pro-row-right">
          <span class="pro-tag-mini">${escapeHtml(song.category)}</span>
          <button class="pro-row-add-btn" title="Add to Playlist" aria-label="Add ${escapeHtml(song.title)}">+</button>
        </div>
      `;

      // Select / Preview
      row.addEventListener('click', (e) => {
        if (e.target.closest('.pro-row-add-btn')) return;
        selectSong(song);
      });

      // Double click to add
      row.addEventListener('dblclick', () => {
        addToRundown(song);
      });

      // Quick add button
      row.querySelector('.pro-row-add-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        addToRundown(song);
      });

      fragment.appendChild(row);
    });

    songListEl.appendChild(fragment);
    state.renderedCount += nextBatch.length;
  }

  function handleSongListScroll() {
    const scrollBottom = songListEl.scrollHeight - songListEl.scrollTop - songListEl.clientHeight;
    if (scrollBottom < 160) {
      appendSongChunk();
    }
  }

  // Song Select & Slide Canvas Rendering
  async function selectSong(song) {
    state.selectedSong = song;
    addToRundownBtn.disabled = false;

    // Highlight row
    document.querySelectorAll('.pro-row').forEach(el => {
      const idx = el.getAttribute('data-idx');
      const hit = state.currentResults[idx] && state.currentResults[idx].filename === song.filename;
      el.classList.toggle('selected', !!hit);
      el.setAttribute('aria-selected', hit ? 'true' : 'false');
    });

    inspectorCategoryEl.textContent = song.category || 'PRO';
    inspectorTitleEl.textContent = song.title;
    inspectorArtistEl.textContent = song.artist ? `by ${song.artist}` : '';
    inspectorContentEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-sub-text">Loading slides...</p></div>';

    try {
      const res = await fetch(`/api/lyrics?file=${encodeURIComponent(song.filename)}`);
      const data = await res.json();
      renderSlideGrid(data);
    } catch {
      inspectorContentEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-sub-text">Failed to load presentation slides</p></div>';
    }
  }

  // Render 16:9 Black Widescreen Slide Cards
  function renderSlideGrid(data) {
    if (!data.groups || !data.groups.length) {
      inspectorContentEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-sub-text">No slide content available</p></div>';
      return;
    }

    inspectorContentEl.innerHTML = '';
    const fragment = document.createDocumentFragment();
    let globalSlideNum = 1;

    data.groups.forEach(group => {
      const groupHeader = group.header || 'VERSE';
      const isBlankGroup = groupHeader === 'BLANK';
      const groupClass = getGroupClass(groupHeader);

      group.slides.forEach(slideLines => {
        const slideCard = document.createElement('div');
        slideCard.className = 'pro-slide-card' + (isBlankGroup ? ' blank-card' : '');

        // Click on slide also adds to playlist or triggers preview
        slideCard.addEventListener('dblclick', () => {
          if (state.selectedSong) addToRundown(state.selectedSong);
        });

        // Slide Lyric Text Lines
        const textWrapper = document.createElement('div');
        textWrapper.className = 'pro-slide-text';

        if (isBlankGroup) {
          textWrapper.style.color = '#737373';
          textWrapper.style.fontSize = '14px';
          textWrapper.textContent = slideLines.join(' ');
        } else {
          slideLines.forEach(line => {
            const p = document.createElement('div');
            p.textContent = line;
            textWrapper.appendChild(p);
          });
        }
        slideCard.appendChild(textWrapper);

        // Slide Bottom Strip with Number & Group
        const strip = document.createElement('div');
        strip.className = 'pro-slide-strip';

        const numBadge = document.createElement('span');
        numBadge.className = `pro-slide-num-badge ${groupClass}`;
        numBadge.textContent = globalSlideNum++;

        const labelBadge = document.createElement('span');
        labelBadge.className = 'pro-slide-label';
        labelBadge.textContent = groupHeader;

        strip.appendChild(numBadge);
        strip.appendChild(labelBadge);
        slideCard.appendChild(strip);

        fragment.appendChild(slideCard);
      });
    });

    inspectorContentEl.appendChild(fragment);
  }

  // Rundown Playlist Management
  function addToRundown(song) {
    if (!song) return;
    state.rundown.push({
      filename: song.filename,
      title: song.title,
      artist: song.artist,
      category: song.category,
      pro: song.pro,
      uid: Date.now() + Math.random().toString(36).substring(2, 6)
    });

    renderRundown();
    savePreferences();
    showToast(`Added: ${song.title}`);

    setTimeout(() => {
      rundownListEl.scrollTop = rundownListEl.scrollHeight;
    }, 40);
  }

  function renderRundown() {
    rundownCount.textContent = state.rundown.length.toString();
    injectBtn.disabled = state.rundown.length === 0;

    if (!state.rundown.length) {
      rundownListEl.innerHTML = '<div class="pro-empty-canvas" style="padding: 24px;"><p class="empty-sub-text">Playlist is empty</p></div>';
      return;
    }

    const fragment = document.createDocumentFragment();
    state.rundown.forEach((item, idx) => {
      const row = document.createElement('div');
      row.className = 'pro-playlist-row';

      row.innerHTML = `
        <div class="pro-row-main">
          <span class="pro-pl-num">${idx + 1}</span>
          <span class="pro-row-title">${escapeHtml(item.title)}</span>
          <span class="pro-row-artist">${escapeHtml(item.artist || item.category)}</span>
        </div>
        <div class="pro-pl-controls">
          <button class="pro-mini-btn btn-up" title="Move Up" ${idx === 0 ? 'disabled' : ''}>▲</button>
          <button class="pro-mini-btn btn-down" title="Move Down" ${idx === state.rundown.length - 1 ? 'disabled' : ''}>▼</button>
          <button class="pro-mini-btn pro-mini-btn-del btn-del" title="Remove">✕</button>
        </div>
      `;

      row.querySelector('.btn-up').addEventListener('click', () => moveRundown(idx, -1));
      row.querySelector('.btn-down').addEventListener('click', () => moveRundown(idx, 1));
      row.querySelector('.btn-del').addEventListener('click', () => removeRundown(idx));

      fragment.appendChild(row);
    });

    rundownListEl.innerHTML = '';
    rundownListEl.appendChild(fragment);
  }

  function moveRundown(index, delta) {
    const target = index + delta;
    if (target < 0 || target >= state.rundown.length) return;
    const temp = state.rundown[index];
    state.rundown[index] = state.rundown[target];
    state.rundown[target] = temp;
    renderRundown();
    savePreferences();
  }

  function removeRundown(index) {
    state.rundown.splice(index, 1);
    renderRundown();
    savePreferences();
  }

  // Copy for WhatsApp
  function copyRundownForWhatsApp() {
    if (!state.rundown.length) {
      showToast('Playlist is empty');
      return;
    }

    const playlistTitle = (playlistNameInput.value.trim() || 'Sunday Service').toUpperCase();
    const lines = [
      `*${playlistTitle}*`,
      `Total: ${state.rundown.length} Songs`,
      ''
    ];

    state.rundown.forEach((song, i) => {
      const artistPart = song.artist ? ` - ${song.artist}` : '';
      lines.push(`${i + 1}. ${song.title}${artistPart}`);
    });

    lines.push('');
    lines.push('(Prepared via ProPresenter 7 Vault)');

    const text = lines.join('\n');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showToast('Rundown copied to clipboard for WhatsApp');
      }).catch(() => fallbackCopy(text));
    } else {
      fallbackCopy(text);
    }
  }

  function fallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand('copy');
      showToast('Rundown copied to clipboard');
    } catch {
      showToast('Failed to copy');
    }
    document.body.removeChild(ta);
  }

  // Realtime Inject Action
  async function injectToProPresenter() {
    if (!state.rundown.length) return;
    const playlistName = playlistNameInput.value.trim() || 'Sunday Service';

    injectBtn.disabled = true;
    injectBtn.innerHTML = '<span>Compiling...</span>';

    const songFileNames = state.rundown.map(s => s.pro);

    try {
      const res = await fetch('/api/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: playlistName,
          songs: songFileNames
        })
      });

      const data = await res.json();
      const missing = Array.isArray(data.missing_in_pro) ? data.missing_in_pro : [];
      const compiledCount = (typeof data.compiled_to_library === 'number') ? data.compiled_to_library : (data.songs_count || 0);
      if (missing.length === 0 && (res.ok || data.success)) {
        showModal(
          'Injection Successful',
          `
            <div style="font-weight: 700; color: #30d158; font-size: 14px; margin-bottom: 10px;">
              ✓ Playlist '${escapeHtml(data.playlist)}' injected into ProPresenter 7
            </div>
            <div style="background: #181818; border: 1px solid #333; padding: 10px; margin-bottom: 12px; border-radius: 4px;">
              <p style="margin-bottom: 4px;"><strong>Songs in Playlist:</strong> ${data.songs_count} songs</p>
              <p><strong>Compiled to Banks:</strong> ${compiledCount} presentations</p>
            </div>
            <div style="font-size: 12px; color: #999999; line-height: 1.4;">
              Open <strong>ProPresenter 7</strong>. The playlist is active under Library Playlists and ready for live presentation immediately without restart.
            </div>
          `
        );
      } else {
        const missingList = missing.length
          ? `<div style="background: #2a1214; border: 1px solid #5a2226; padding: 10px; margin-bottom: 12px; border-radius: 4px;">
              <p style="color: #ff9d97; margin-bottom: 6px;"><strong>Gagal dikompilasi (${missing.length}):</strong></p>
              <ul style="margin: 0; padding-left: 16px; color: #e0e0e0; font-size: 12px; line-height: 1.5;">
                ${missing.map(m => `<li>${escapeHtml(m)}</li>`).join('')}
              </ul>
            </div>`
          : '';
        showModal(
          compiledCount > 0 ? 'Injection Partial' : 'Injection Failed',
          `
            <div style="font-weight: 700; color: ${compiledCount > 0 ? '#ffd60a' : '#ff453a'}; font-size: 14px; margin-bottom: 10px;">
              ${compiledCount > 0 ? '⚠' : '✕'} Playlist '${escapeHtml(data.playlist || playlistName)}' ${compiledCount > 0 ? 'partially injected' : 'failed'}
            </div>
            <div style="background: #181818; border: 1px solid #333; padding: 10px; margin-bottom: 12px; border-radius: 4px;">
              <p style="margin-bottom: 4px;"><strong>Requested:</strong> ${data.songs_count || songFileNames.length} songs</p>
              <p><strong>Compiled to Banks:</strong> ${compiledCount}</p>
            </div>
            ${missingList}
            <div style="font-size: 12px; color: #999999; line-height: 1.4;">
              ${escapeHtml(data.error || data.engine_output || 'Compiler error')}
            </div>
          `
        );
      }
    } catch {
      showModal('Connection Error', '<div style="color: #ff453a;">Cannot connect to local engine at 127.0.0.1:5050.</div>');
    } finally {
      injectBtn.disabled = false;
      injectBtn.innerHTML = '<span class="pro-btn-glyph">▶</span><span>INJECT TO PRO7</span>';
    }
  }

  // Modal
  function showModal(title, html) {
    modalTitle.textContent = title;
    modalBody.innerHTML = html;
    modalOverlay.classList.remove('hidden');
    modalOkBtn.focus();
  }

  function hideModal() {
    modalOverlay.classList.add('hidden');
  }

  // Toast
  function showToast(msg) {
    clearTimeout(state.toastTimeout);
    toastEl.textContent = msg;
    toastEl.classList.remove('hidden');
    state.toastTimeout = setTimeout(() => {
      toastEl.classList.add('hidden');
    }, 2400);
  }

  // Event Listeners
  function setupEventListeners() {
    // Search input
    searchInput.addEventListener('input', () => {
      clearTimeout(state.searchTimeout);
      state.searchTimeout = setTimeout(loadSongs, 70);
    });

    clearSearchBtn.addEventListener('click', () => {
      searchInput.value = '';
      loadSongs();
      searchInput.focus();
    });

    // Infinite scroll
    songListEl.addEventListener('scroll', handleSongListScroll);

    // Scale & Fullscreen
    if (zoomInBtn) zoomInBtn.addEventListener('click', () => changeScale(1));
    if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => changeScale(-1));
    if (fullscreenToggleBtn) fullscreenToggleBtn.addEventListener('click', toggleFullscreen);

    // Category Tabs
    filterTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        filterTabs.forEach(t => {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');
        state.activeCategory = tab.getAttribute('data-category');
        loadSongs();
      });
    });

    // Add button
    addToRundownBtn.addEventListener('click', () => {
      if (state.selectedSong) addToRundown(state.selectedSong);
    });

    // Playlist name input save
    playlistNameInput.addEventListener('input', () => {
      savePreferences();
    });

    // Clear rundown
    clearRundownBtn.addEventListener('click', () => {
      if (!state.rundown.length) return;
      if (window.confirm('Clear all songs from playlist?')) {
        state.rundown = [];
        renderRundown();
        savePreferences();
        showToast('Playlist cleared');
      }
    });

    // WA button & Inject button
    copyWaBtn.addEventListener('click', copyRundownForWhatsApp);
    injectBtn.addEventListener('click', injectToProPresenter);

    // Modal close
    modalCloseBtn.addEventListener('click', hideModal);
    modalOkBtn.addEventListener('click', hideModal);
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) hideModal();
    });

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
      if ((e.key === '/' || e.key === 'F3') && document.activeElement !== searchInput && document.activeElement !== playlistNameInput) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }

      if (e.key === 'F11') {
        e.preventDefault();
        toggleFullscreen();
      }

      // Zoom Scale shortcuts
      if (e.ctrlKey && (e.key === '=' || e.key === '+')) {
        e.preventDefault();
        changeScale(1);
      }
      if (e.ctrlKey && (e.key === '-' || e.key === '_')) {
        e.preventDefault();
        changeScale(-1);
      }
      if (e.ctrlKey && e.key === '0') {
        e.preventDefault();
        applyScale(1.20);
        showToast('Display Scale Reset: 120%');
      }

      if (e.key === 'Enter') {
        if (!modalOverlay.classList.contains('hidden')) {
          hideModal();
          return;
        }

        if (document.activeElement === searchInput) {
          if (state.currentResults.length > 0) {
            e.preventDefault();
            if (state.currentResults.length === 1) {
              addToRundown(state.currentResults[0]);
            } else if (state.selectedSong) {
              addToRundown(state.selectedSong);
            } else {
              selectSong(state.currentResults[0]);
            }
          }
        } else if (state.selectedSong && document.activeElement !== playlistNameInput) {
          addToRundown(state.selectedSong);
        }
      }

      if (e.key === 'Escape') {
        if (!modalOverlay.classList.contains('hidden')) {
          hideModal();
        } else if (searchInput.value) {
          searchInput.value = '';
          loadSongs();
        }
      }

      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        if (document.activeElement === searchInput || document.activeElement === songListEl) {
          e.preventDefault();
          navigateSongList(e.key === 'ArrowDown' ? 1 : -1);
        }
      }
    });
  }

  function navigateSongList(direction) {
    if (!state.currentResults.length) return;
    let curIdx = state.selectedSong ? state.currentResults.findIndex(s => s.filename === state.selectedSong.filename) : -1;
    let nextIdx = curIdx + direction;
    if (nextIdx < 0) nextIdx = 0;
    if (nextIdx >= state.currentResults.length) nextIdx = state.currentResults.length - 1;

    const nextSong = state.currentResults[nextIdx];
    if (nextSong) {
      selectSong(nextSong);
      const rows = songListEl.querySelectorAll('.pro-row');
      if (rows[nextIdx]) {
        rows[nextIdx].scrollIntoView({ block: 'nearest' });
      }
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

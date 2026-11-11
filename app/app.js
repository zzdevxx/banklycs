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
    searchSeq: 0,
    lyricsSeq: 0,
    toastTimeout: null,
    banksCount: 0,
    chunkSize: 60,
    propresenterDir: '',
    savedScale: 1.20,
    tempScale: 1.20,
    activeTheme: 'Lyric - Praise',
    themesList: [],
    lastFocusedBeforeModal: null,
    activeDescendantId: ''
  };

  // DOM Elements
  const resultsCount = document.getElementById('results-count');
  const rundownCount = document.getElementById('rundown-count');
  const searchInput = document.getElementById('search-input');
  const clearSearchBtn = document.getElementById('clear-search-btn');
  const filterTabs = Array.from(document.querySelectorAll('.pro-tab'));
  const songListEl = document.getElementById('song-list');
  const libraryPanel = document.getElementById('library-panel');
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

  // Settings Modal Elements
  const settingsBtn = document.getElementById('settings-btn');
  const settingsOverlay = document.getElementById('settings-overlay');
  const settingsCloseBtn = document.getElementById('settings-close-btn');
  const settingsCancelBtn = document.getElementById('settings-cancel-btn');
  const settingsSaveBtn = document.getElementById('settings-save-btn');
  const scaleMinusBtn = document.getElementById('scale-minus-btn');
  const scalePlusBtn = document.getElementById('scale-plus-btn');
  const scaleSlider = document.getElementById('scale-slider');
  const settingsScaleBadge = document.getElementById('settings-scale-badge');
  const settingsThemeSelect = document.getElementById('settings-theme-select');
  const previewThemeTag = document.getElementById('preview-theme-tag');
  const settingsProPath = document.getElementById('settings-pro-path');

  // About Modal Elements
  const aboutBtn = document.getElementById('about-btn');
  const aboutOverlay = document.getElementById('about-overlay');
  const aboutCloseBtn = document.getElementById('about-close-btn');
  const aboutOkBtn = document.getElementById('about-ok-btn');

  // Main Modal & Toast
  const modalOverlay = document.getElementById('modal-overlay');
  const modalTitle = document.getElementById('modal-title');
  const modalBody = document.getElementById('modal-body');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const modalOkBtn = document.getElementById('modal-ok-btn');
  const toastEl = document.getElementById('toast');
  const mainWorkspaceEl = document.querySelector('.pro-workspace');
  const mainToolbarEl = document.querySelector('.pro-toolbar');

  let currentScale = 1.2;
  // Slider-aligned steps (100..150, step 5) used by keyboard zoom shortcuts.
  const SCALE_STEPS = [1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.45, 1.5];

  function applyScale(scale) {
    currentScale = Math.round(scale * 100) / 100;
    document.documentElement.style.setProperty('--pro-scale', currentScale);
    if (settingsScaleBadge) {
      settingsScaleBadge.textContent = Math.round(currentScale * 100) + '%';
    }
    if (scaleSlider) {
      const pct = Math.round(currentScale * 100);
      scaleSlider.value = pct;
      scaleSlider.setAttribute('aria-valuetext', `${pct} persen`);
    }
    syncStepperBounds();
    try {
      localStorage.setItem('pro7_scale', currentScale.toString());
    } catch {
      // Storage unavailable (private mode); the in-memory scale still applies.
    }
  }

  function syncStepperBounds() {
    const pct = Math.round(currentScale * 100);
    if (scaleMinusBtn) {
      scaleMinusBtn.disabled = pct <= 100;
      scaleMinusBtn.setAttribute('aria-disabled', scaleMinusBtn.disabled ? 'true' : 'false');
    }
    if (scalePlusBtn) {
      scalePlusBtn.disabled = pct >= 150;
      scalePlusBtn.setAttribute('aria-disabled', scalePlusBtn.disabled ? 'true' : 'false');
    }
  }

  function changeScale(direction) {
    let curIdx = SCALE_STEPS.findIndex(s => Math.abs(s - currentScale) < 0.026);
    if (curIdx === -1) curIdx = SCALE_STEPS.findIndex(s => s >= currentScale);
    if (curIdx === -1) curIdx = SCALE_STEPS.length - 1;
    const nextIdx = Math.min(SCALE_STEPS.length - 1, Math.max(0, curIdx + direction));
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
    if (h.includes('INTERLUDE')) return 'group-intro';
    return 'group-verse';
  }

  // Initialization
  async function init() {
    loadPreferences();
    setupDefaultPlaylistName();
    setupEventListeners();
    await checkStatus();
    await loadThemes();
    loadSongs();
  }

  function loadPreferences() {
    try {
      const savedScale = parseFloat(localStorage.getItem('pro7_scale'));
      applyScale(savedScale && !isNaN(savedScale) ? savedScale : 1.20);

      const savedTheme = localStorage.getItem('pro7_theme');
      if (savedTheme) {
        state.activeTheme = savedTheme;
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
      // Corrupt or unavailable localStorage: fall back to the defaults above.
      applyScale(1.20);
    }
  }

  async function loadThemes() {
    try {
      const res = await fetch('/api/themes');
      const data = await res.json();
      state.themesList = data.themes || [];
      if (data.active_theme) {
        state.activeTheme = data.active_theme;
      }

      const fontBadge = document.getElementById('settings-font-badge');
      const installFontBtn = document.getElementById('install-font-btn');
      if (fontBadge) {
        if (data.cmg_font_installed) {
          fontBadge.className = 'settings-tag-ok';
          fontBadge.textContent = data.times_normal_installed === false
            ? '⚠ Times New Normal Belum Terpasang (fallback: Times New Roman)'
            : '✓ CMG Sans + Times New Normal Terpasang';
          if (installFontBtn) installFontBtn.classList.add('hidden');
        } else {
          fontBadge.className = 'settings-tag-warning';
          fontBadge.textContent = '⚠ CMG Sans Belum Terpasang (Worship fallback: Times New Roman)';
          if (installFontBtn) installFontBtn.classList.remove('hidden');
        }
      }

      if (settingsThemeSelect && state.themesList.length > 0) {
        settingsThemeSelect.innerHTML = '';

        const groups = {};
        state.themesList.forEach(t => {
          const g = t.group || 'Banklycs';
          if (!groups[g]) groups[g] = [];
          groups[g].push(t);
        });

        Object.keys(groups).forEach(gName => {
          const optGroup = document.createElement('optgroup');
          optGroup.label = gName === 'Banklycs' ? 'Banklycs (Official Stage Theme)' : `ProPresenter: ${gName}`;
          groups[gName].forEach(t => {
            const opt = document.createElement('option');
            opt.value = t.slide_name;
            opt.textContent = `${t.slide_name} (1920×1080)`;
            if (t.slide_name.toLowerCase() === state.activeTheme.toLowerCase()) {
              opt.selected = true;
            }
            optGroup.appendChild(opt);
          });
          settingsThemeSelect.appendChild(optGroup);
        });
      }
      updateThemePreview();
    } catch {
      // Themes endpoint offline: keep the static options already in the DOM.
    }
  }

  function updateThemePreview() {
    if (!previewThemeTag || !settingsThemeSelect) return;
    const selected = settingsThemeSelect.value || state.activeTheme || 'Lyric - Praise';
    const low = selected.toLowerCase();

    const previewBox = document.querySelector('.preview-text-box');
    const line1 = document.querySelector('.preview-line-1');
    const line2 = document.querySelector('.preview-line-2');
    const resTag = document.querySelector('.preview-res-tag');

    previewThemeTag.textContent = selected.toUpperCase();

    if (low.includes('worship')) {
      if (previewBox) previewBox.className = 'preview-text-box font-worship';
      if (line1) line1.textContent = 'Kudus, kudus, kuduslah Tuhan';
      if (line2) line2.textContent = 'Bumi penuh kemuliaan-Mu';
      if (resTag) resTag.textContent = 'Times New Roman • fs150';
    } else if (low.includes('bible')) {
      if (previewBox) previewBox.className = 'preview-text-box font-bible';
      if (line1) line1.textContent = 'Sebab firman Allah hidup dan kuat,';
      if (line2) line2.textContent = 'lebih tajam dari pedang bermata dua.';
      if (resTag) resTag.textContent = 'Arial • fs100';
    } else {
      if (previewBox) previewBox.className = 'preview-text-box font-praise';
      if (line1) line1.textContent = 'KAU ALLAH YANG BESAR';
      if (line2) line2.textContent = 'AJAIB DAN BERKUASA';
      if (resTag) resTag.textContent = 'CMGSans-Bold • fs134';
    }
  }

  function savePreferences() {
    try {
      localStorage.setItem('pro7_rundown', JSON.stringify(state.rundown));
      if (playlistNameInput && playlistNameInput.value) {
        localStorage.setItem('pro7_playlist_name', playlistNameInput.value.trim());
      }
    } catch {
      // Quota or blocked storage: the rundown still lives in memory.
    }
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => showToast('Fullscreen tidak tersedia'));
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
      state.propresenterDir = data.propresenter_dir || '';
      state.banksCount = data.banks_count || 0;
      updateSettingsStatusText();
      updateAboutStats(data);

      if (data.catalog_stale) {
        try {
          // /api/reload is POST-only; a GET here silently returned 405 and the
          // catalog stayed stale for the whole session.
          const r = await fetch('/api/reload', { method: 'POST' });
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          const d = await r.json();
          state.allCount = d.total_songs || state.allCount;
          await loadSongs();
          showToast('Katalog lagu dimuat ulang');
        } catch {
          showToast('Library berubah, gagal reload katalog');
        }
      }
    } catch {
      showToast('Engine offline: jalankan START.vbs');
    }
  }

  // The About panel used to hardcode the catalog size, which drifted from the
  // live database. Bind it to /api/status instead of trusting a literal.
  function updateAboutStats(data) {
    const songsEl = document.getElementById('about-stat-songs');
    const dbEl = document.getElementById('about-stat-db');
    if (songsEl && typeof data.total_songs === 'number') {
      songsEl.textContent = data.total_songs.toLocaleString('id-ID');
    }
    if (dbEl && typeof data.db_size_bytes === 'number' && data.db_size_bytes > 0) {
      // Decimal MB, matching the documented 61.42 MB. Binary MiB here showed
      // 58.6 MB for the same file, so the UI contradicted the docs.
      dbEl.textContent = (data.db_size_bytes / 1_000_000).toFixed(2) + ' MB';
    }
  }

  function updateSettingsStatusText() {
    if (settingsProPath) {
      settingsProPath.textContent = state.propresenterDir || 'Folder ProPresenter tidak terdeteksi otomatis';
    }
    const banksCountEl = document.getElementById('settings-banks-count');
    if (banksCountEl) {
      banksCountEl.textContent = `${state.banksCount} Presentasi Aktif`;
    }
  }

  // Load Songs with Smart Number Search
  async function loadSongs() {
    let q = searchInput.value.trim();
    songListEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-sub-text">Searching Library...</p></div>';

    // Auto-prefix number searches if inside a specific hymnal category
    if (/^\d+$/.test(q) && state.activeCategory !== 'ALL' && state.activeCategory !== 'ID' && state.activeCategory !== 'EN') {
      q = `${state.activeCategory} ${q}`;
    }

    const seq = ++state.searchSeq;
    try {
      const url = `/api/songs?q=${encodeURIComponent(q)}&category=${encodeURIComponent(state.activeCategory)}&limit=300`;
      const res = await fetch(url);
      const data = await res.json();
      // A slower earlier request must not overwrite a newer result set.
      if (seq !== state.searchSeq) return;
      state.currentResults = data.songs || [];
      state.renderedCount = 0;

      const totalMatched = typeof data.total_matched === 'number' ? data.total_matched : state.currentResults.length;
      if (q.length === 0 && state.activeCategory === 'ALL') {
        const totalDb = data.total_catalog || state.allCount || 0;
        resultsCount.textContent = `${totalDb.toLocaleString('id-ID')} Lagu`;
      } else if (q.length === 0) {
        resultsCount.textContent = `${totalMatched.toLocaleString('id-ID')} Lagu`;
      } else {
        resultsCount.textContent = `${totalMatched.toLocaleString('id-ID')} Ditemukan`;
      }

      resetSelection();
      renderSongListInitial();
    } catch {
      songListEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-sub-text">Gagal memuat lagu</p></div>';
    }
  }

  function resetSelection() {
    state.selectedSong = null;
    state.activeDescendantId = '';
    addToRundownBtn.disabled = true;
    addToRundownBtn.setAttribute('aria-disabled', 'true');
    inspectorCategoryEl.textContent = 'READY';
    inspectorTitleEl.textContent = 'Select a song from Library';
    inspectorArtistEl.textContent = '';
    inspectorContentEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-main-text">No Presentation Selected</p><p class="empty-sub-text">Pilih lagu dari Library di sebelah kiri untuk melihat slide.</p></div>';
  }

  function renderSongListInitial() {
    songListEl.innerHTML = '';
    songListEl.removeAttribute('aria-activedescendant');
    state.renderedCount = 0;

    if (!state.currentResults.length) {
      songListEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-sub-text">No matching songs in Library</p></div>';
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
      row.id = `song-row-${globalIdx}`;
      row.setAttribute('role', 'option');
      row.setAttribute('data-idx', globalIdx);
      row.setAttribute('aria-selected', isSelected ? 'true' : 'false');
      row.title = song.title;

      row.innerHTML = `
        <div class="pro-row-main">
          <span class="pro-row-title">${escapeHtml(song.title)}</span>
          <span class="pro-row-artist">${escapeHtml(song.artist || '')}</span>
        </div>
        <div class="pro-row-right">
          <span class="pro-tag-mini">${escapeHtml(song.category)}</span>
          <button class="pro-row-add-btn" type="button" title="Add to Playlist" aria-label="Tambahkan ${escapeHtml(song.title)} ke playlist">+</button>
        </div>
      `;

      row.addEventListener('click', (e) => {
        if (e.target.closest('.pro-row-add-btn')) return;
        focusSongRow(globalIdx);
        selectSong(song);
      });

      row.addEventListener('dblclick', () => {
        addToRundown(song);
      });

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

  function focusSongRow(index) {
    const row = document.getElementById(`song-row-${index}`);
    if (!row) return;
    songListEl.setAttribute('aria-activedescendant', row.id);
    state.activeDescendantId = row.id;
  }

  // Song Select & Slide Canvas Rendering
  async function selectSong(song) {
    state.selectedSong = song;
    addToRundownBtn.disabled = false;
    addToRundownBtn.setAttribute('aria-disabled', 'false');

    document.querySelectorAll('.pro-row').forEach(el => {
      const idx = el.getAttribute('data-idx');
      const hit = state.currentResults[idx] && state.currentResults[idx].filename === song.filename;
      el.classList.toggle('selected', !!hit);
      el.setAttribute('aria-selected', hit ? 'true' : 'false');
      if (hit) {
        songListEl.setAttribute('aria-activedescendant', el.id);
        state.activeDescendantId = el.id;
      }
    });

    inspectorCategoryEl.textContent = song.category || 'PRO';
    inspectorTitleEl.textContent = song.title;
    inspectorArtistEl.textContent = song.artist ? `by ${song.artist}` : '';
    inspectorContentEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-sub-text">Loading slides...</p></div>';

    const seq = ++state.lyricsSeq;
    try {
      const res = await fetch(`/api/lyrics?file=${encodeURIComponent(song.filename)}`);
      const data = await res.json();
      // Rapid row clicks: only the last selection may paint the slide grid.
      if (seq !== state.lyricsSeq || !state.selectedSong || state.selectedSong.filename !== song.filename) return;
      renderSlideGrid(data);
    } catch {
      if (seq !== state.lyricsSeq) return;
      inspectorContentEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-sub-text">Gagal memuat slide presentasi</p></div>';
    }
  }

  // Render 16:9 Black Widescreen Slide Cards
  function renderSlideGrid(data) {
    if (!data.groups || !data.groups.length) {
      inspectorContentEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-sub-text">Tidak ada konten slide</p></div>';
      return;
    }

    inspectorContentEl.innerHTML = '';
    const fragment = document.createDocumentFragment();
    let globalSlideNum = 1;
    const themeLow = state.activeTheme.toLowerCase();
    const fontClass = themeLow.includes('worship') ? 'font-worship' :
                      themeLow.includes('bible') ? 'font-bible' : '';

    data.groups.forEach(group => {
      const groupHeader = group.header || 'VERSE';
      const isBlankGroup = groupHeader === 'BLANK';
      const groupClass = getGroupClass(groupHeader);

      group.slides.forEach(slideLines => {
        const slideCard = document.createElement('div');
        slideCard.className = 'pro-slide-card' + (isBlankGroup ? ' blank-card' : '');
        slideCard.tabIndex = 0;
        slideCard.setAttribute('role', 'button');

        const slideNo = globalSlideNum;
        const firstLine = (slideLines[0] || '').trim().slice(0, 60);
        slideCard.setAttribute('aria-label', `Slide ${slideNo}, ${groupHeader}: ${firstLine || 'kosong'}`);

        const activate = () => {
          if (state.selectedSong) addToRundown(state.selectedSong);
        };
        slideCard.addEventListener('dblclick', activate);
        slideCard.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            e.stopPropagation();
            activate();
          }
        });

        const textWrapper = document.createElement('div');
        textWrapper.className = `pro-slide-text ${fontClass}`.trim();

        if (isBlankGroup) {
          textWrapper.classList.add('slide-text-blank');
          textWrapper.textContent = slideLines.join(' ');
        } else {
          slideLines.forEach(line => {
            const p = document.createElement('div');
            p.textContent = line;
            textWrapper.appendChild(p);
          });
        }
        slideCard.appendChild(textWrapper);

        const strip = document.createElement('div');
        strip.className = 'pro-slide-strip';
        strip.setAttribute('aria-hidden', 'true');

        const numBadge = document.createElement('span');
        numBadge.className = `pro-slide-num-badge ${groupClass}`;
        numBadge.textContent = String(globalSlideNum++);

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

  function setRundownActionState(hasItems) {
    injectBtn.disabled = !hasItems;
    injectBtn.setAttribute('aria-disabled', hasItems ? 'false' : 'true');
    copyWaBtn.disabled = !hasItems;
    copyWaBtn.setAttribute('aria-disabled', hasItems ? 'false' : 'true');
    clearRundownBtn.disabled = !hasItems;
    clearRundownBtn.setAttribute('aria-disabled', hasItems ? 'false' : 'true');
  }

  function renderRundown() {
    rundownCount.textContent = state.rundown.length.toString();
    setRundownActionState(state.rundown.length > 0);

    if (!state.rundown.length) {
      rundownListEl.innerHTML = '<div class="pro-empty-canvas"><p class="empty-sub-text">Playlist is empty</p></div>';
      return;
    }

    const fragment = document.createDocumentFragment();
    state.rundown.forEach((item, idx) => {
      const row = document.createElement('div');
      row.className = 'pro-playlist-row';
      row.setAttribute('role', 'listitem');

      row.innerHTML = `
        <div class="pro-row-main">
          <span class="pro-pl-num">${idx + 1}</span>
          <span class="pro-row-title">${escapeHtml(item.title)}</span>
          <span class="pro-row-artist">${escapeHtml(item.artist || item.category)}</span>
        </div>
        <div class="pro-pl-controls">
          <button class="pro-mini-btn btn-up" type="button" title="Move Up" aria-label="Naikkan ${escapeHtml(item.title)}" ${idx === 0 ? 'disabled aria-disabled="true"' : ''}>▲</button>
          <button class="pro-mini-btn btn-down" type="button" title="Move Down" aria-label="Turunkan ${escapeHtml(item.title)}" ${idx === state.rundown.length - 1 ? 'disabled aria-disabled="true"' : ''}>▼</button>
          <button class="pro-mini-btn pro-mini-btn-del btn-del" type="button" title="Remove" aria-label="Hapus ${escapeHtml(item.title)} dari rundown">✕</button>
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
        headers: {
          'Content-Type': 'application/json',
          'X-Banklycs-Inject': '1'
        },
        body: JSON.stringify({
          name: playlistName,
          songs: songFileNames
        })
      });

      const data = await res.json();
      const missing = Array.isArray(data.missing_in_pro) ? data.missing_in_pro : [];
      const skipped = Array.isArray(data.skipped_modified) ? data.skipped_modified : [];
      const compiledCount = (typeof data.compiled_to_library === 'number') ? data.compiled_to_library : (data.songs_count || 0);
      if (missing.length === 0 && (res.ok || data.success)) {
        const skippedBox = skipped.length
          ? `<div class="modal-missing-box">
              <p class="modal-missing-title"><strong>Dilewati — sudah diedit di ProPresenter (${skipped.length}):</strong></p>
              <ul class="modal-missing-list">
                ${skipped.map(m => `<li>${escapeHtml(m)}</li>`).join('')}
              </ul>
              <p style="margin-top:6px;">Editanmu di ProPresenter dipertahankan. Matikan proteksi di Settings bila tetap ingin menimpa.</p>
            </div>`
          : '';
        showModal(
          'Injection Successful',
          `
            <div class="modal-status modal-status-ok">
              ✓ Playlist '${escapeHtml(data.playlist)}' injected into ProPresenter 7
            </div>
            <div class="modal-detail-box">
              <p><strong>Songs in Playlist:</strong> ${data.songs_count} songs</p>
              <p><strong>Compiled to Banks:</strong> ${compiledCount} presentations</p>
              ${skipped.length ? `<p><strong>Protected (skipped):</strong> ${skipped.length}</p>` : ''}
            </div>
            ${skippedBox}
            <div class="modal-note">
              Open <strong>ProPresenter 7</strong>. The playlist is active under Library Playlists and ready for live presentation immediately without restart.
            </div>
          `
        );
      } else {
        const missingList = missing.length
          ? `<div class="modal-missing-box">
              <p class="modal-missing-title"><strong>Gagal dikompilasi (${missing.length}):</strong></p>
              <ul class="modal-missing-list">
                ${missing.map(m => `<li>${escapeHtml(m)}</li>`).join('')}
              </ul>
            </div>`
          : '';
        showModal(
          compiledCount > 0 ? 'Injection Partial' : 'Injection Failed',
          `
            <div class="modal-status ${compiledCount > 0 ? 'modal-status-warn' : 'modal-status-error'}">
              ${compiledCount > 0 ? '⚠' : '✕'} Playlist '${escapeHtml(data.playlist || playlistName)}' ${compiledCount > 0 ? 'partially injected' : 'failed'}
            </div>
            <div class="modal-detail-box">
              <p><strong>Requested:</strong> ${data.songs_count || songFileNames.length} songs</p>
              <p><strong>Compiled to Banks:</strong> ${compiledCount}</p>
            </div>
            ${missingList}
            <div class="modal-note">
              ${escapeHtml(data.error || data.engine_output || 'Compiler error')}
            </div>
          `
        );
      }
    } catch {
      showModal('Connection Error', `<div class="modal-status modal-status-error">Cannot connect to local engine at ${escapeHtml(location.host)}.</div>`);
    } finally {
      injectBtn.disabled = state.rundown.length === 0;
      injectBtn.setAttribute('aria-disabled', injectBtn.disabled ? 'true' : 'false');
      injectBtn.innerHTML = '<span>INJECT</span>';
    }
  }

  // ============================================================
  // Update center: dual channels (app v2.x / database timestamp)
  // ============================================================

  function formatDbVersion(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' }) +
      ' ' + d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
  }

  function formatBytes(bytes) {
    if (!bytes) return '';
    return (bytes / (1024 * 1024)).toFixed(1).replace('.', ',') + ' MB';
  }

  async function loadUpdateSettings() {
    const appVersionEl = document.getElementById('settings-app-version');
    const dbVersionEl = document.getElementById('settings-db-version');
    const appAutoEl = document.getElementById('settings-app-auto');
    const dbAutoEl = document.getElementById('settings-db-auto');
    const protectEl = document.getElementById('settings-protect');
    const appResult = document.getElementById('app-update-result');
    const dbResult = document.getElementById('db-update-result');
    const appLink = document.getElementById('app-update-link');
    const dbApply = document.getElementById('db-apply-btn');
    try {
      const res = await fetch('/api/settings');
      const data = await res.json();
      if (appVersionEl) appVersionEl.textContent = 'v' + (data.app_version || '—');
      if (dbVersionEl) dbVersionEl.textContent = formatDbVersion(data.db_version);
      if (appAutoEl) appAutoEl.checked = !!data.app_auto_check;
      if (dbAutoEl) dbAutoEl.checked = !!data.db_auto_check;
      if (protectEl) protectEl.checked = !!data.protect_user_edits;
    } catch {
      if (appResult) { appResult.hidden = false; appResult.textContent = 'Engine tidak merespons.'; }
      return;
    }
    if (appResult) appResult.hidden = true;
    if (dbResult) dbResult.hidden = true;
    if (appLink) appLink.classList.add('hidden');
    if (dbApply) dbApply.classList.add('hidden');
  }

  async function saveUpdateFlag(key, value) {
    try {
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [key]: value })
      });
      showToast(value ? 'Diaktifkan' : 'Dimatikan');
    } catch {
      showToast('Gagal menyimpan setting');
    }
  }

  async function recheckAppUpdate() {
    const result = document.getElementById('app-update-result');
    const link = document.getElementById('app-update-link');
    const btn = document.getElementById('app-recheck-btn');
    if (!result || !btn) return;
    btn.disabled = true;
    result.hidden = false;
    result.textContent = 'Memeriksa rilis terbaru...';
    try {
      const res = await fetch('/api/update/app');
      const data = await res.json();
      if (data.error) {
        result.textContent = '⚠ ' + data.error;
      } else if (data.update_available) {
        result.textContent = `✓ Update tersedia: ${data.latest} (terpasang v${data.current})`;
        if (link) link.classList.remove('hidden');
      } else {
        result.textContent = `✓ Sudah versi terbaru (v${data.current})`;
        if (link) link.classList.add('hidden');
      }
    } catch {
      result.textContent = '⚠ Koneksi ke engine gagal.';
    } finally {
      btn.disabled = false;
    }
  }

  async function recheckDbUpdate() {
    const result = document.getElementById('db-update-result');
    const applyBtn = document.getElementById('db-apply-btn');
    const btn = document.getElementById('db-recheck-btn');
    if (!result || !btn) return;
    btn.disabled = true;
    result.hidden = false;
    result.textContent = 'Memeriksa katalog terbaru...';
    try {
      const res = await fetch('/api/update/db');
      const data = await res.json();
      if (data.error) {
        result.textContent = '⚠ ' + data.error;
        if (applyBtn) applyBtn.classList.add('hidden');
      } else if (data.update_available) {
        result.innerHTML = `✓ Katalog baru tersedia: <strong>${formatDbVersion(data.latest_version)}</strong> ` +
          `(terpasang ${formatDbVersion(data.current_version)})${data.size ? ' — ' + formatBytes(data.size) : ''}`;
        if (applyBtn) applyBtn.classList.remove('hidden');
      } else {
        result.textContent = `✓ Database sudah versi terbaru (${formatDbVersion(data.current_version)})`;
        if (applyBtn) applyBtn.classList.add('hidden');
      }
    } catch {
      result.textContent = '⚠ Koneksi ke engine gagal.';
    } finally {
      btn.disabled = false;
    }
  }

  async function applyDbUpdate() {
    const result = document.getElementById('db-update-result');
    const applyBtn = document.getElementById('db-apply-btn');
    if (!result || !applyBtn) return;
    applyBtn.disabled = true;
    applyBtn.textContent = 'Mengunduh...';
    result.hidden = false;
    result.textContent = 'Mengunduh database baru (±61 MB) dan memverifikasi SHA-256...';
    try {
      const res = await fetch('/api/update/db/apply', { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.success) {
        result.innerHTML = `✓ Database diperbarui ke <strong>${formatDbVersion(data.db_version)}</strong> — ${data.total_songs.toLocaleString('id-ID')} lagu dimuat ulang.`;
        applyBtn.classList.add('hidden');
        showToast('Database berhasil diperbarui');
        await checkStatus();
        loadSongs();
      } else {
        result.textContent = '✕ ' + (data.error || data.title || 'Gagal memperbarui database.');
      }
    } catch {
      result.textContent = '✕ Koneksi ke engine gagal saat mengunduh.';
    } finally {
      applyBtn.disabled = false;
      applyBtn.textContent = 'Unduh & Terapkan';
    }
  }

  function setupUpdateCenter() {
    const appAuto = document.getElementById('settings-app-auto');
    const dbAuto = document.getElementById('settings-db-auto');
    const protect = document.getElementById('settings-protect');
    const appRecheck = document.getElementById('app-recheck-btn');
    const dbRecheck = document.getElementById('db-recheck-btn');
    const dbApply = document.getElementById('db-apply-btn');
    if (appAuto) appAuto.addEventListener('change', () => saveUpdateFlag('app_auto_check', appAuto.checked));
    if (dbAuto) dbAuto.addEventListener('change', () => saveUpdateFlag('db_auto_check', dbAuto.checked));
    if (protect) protect.addEventListener('change', () => saveUpdateFlag('protect_user_edits', protect.checked));
    if (appRecheck) appRecheck.addEventListener('click', recheckAppUpdate);
    if (dbRecheck) dbRecheck.addEventListener('click', recheckDbUpdate);
    if (dbApply) dbApply.addEventListener('click', applyDbUpdate);
  }

  // Modal focus management: focus trap, return focus to trigger, and inert background
  const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function setBackgroundInert(isInert) {
    [mainWorkspaceEl, mainToolbarEl].forEach(el => {
      if (!el) return;
      if (isInert) {
        el.setAttribute('inert', '');
        el.setAttribute('aria-hidden', 'true');
      } else {
        el.removeAttribute('inert');
        el.removeAttribute('aria-hidden');
      }
    });
  }

  function openDialog(overlay, focusTarget) {
    state.lastFocusedBeforeModal = document.activeElement;
    setBackgroundInert(true);
    overlay.classList.remove('hidden');
    if (focusTarget) focusTarget.focus();
  }

  function closeDialog(overlay) {
    overlay.classList.add('hidden');
    const anyOpen = [modalOverlay, settingsOverlay, aboutOverlay].some(o => o && !o.classList.contains('hidden'));
    if (!anyOpen) setBackgroundInert(false);
    const back = state.lastFocusedBeforeModal;
    if (back && typeof back.focus === 'function') {
      back.focus();
    }
  }

  function trapFocus(e, overlay) {
    if (e.key !== 'Tab') return;
    const nodes = Array.from(overlay.querySelectorAll(FOCUSABLE)).filter(el => el.offsetParent !== null);
    if (!nodes.length) return;
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  // Settings Modal Handlers
  async function showSettings() {
    if (!settingsOverlay) return;
    state.savedScale = currentScale;
    state.tempScale = currentScale;

    applyScale(currentScale);

    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      state.banksCount = data.banks_count || 0;
      state.propresenterDir = data.propresenter_dir || state.propresenterDir;
    } catch {
      // Keep the last known status values; the dialog still opens.
    }

    updateSettingsStatusText();
    loadUpdateSettings();

    if (settingsThemeSelect && state.activeTheme) {
      for (let i = 0; i < settingsThemeSelect.options.length; i++) {
        if (settingsThemeSelect.options[i].value.toLowerCase() === state.activeTheme.toLowerCase()) {
          settingsThemeSelect.selectedIndex = i;
          break;
        }
      }
      updateThemePreview();
    }

    openDialog(settingsOverlay, settingsSaveBtn);
  }

  function cancelSettings() {
    applyScale(state.savedScale);
    closeDialog(settingsOverlay);
  }

  async function saveSettings() {
    state.savedScale = state.tempScale;
    applyScale(state.savedScale);

    if (settingsThemeSelect) {
      const chosenTheme = settingsThemeSelect.value;
      state.activeTheme = chosenTheme;
      try {
        await fetch('/api/themes/select', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ slide_name: chosenTheme })
        });
        localStorage.setItem('pro7_theme', chosenTheme);
      } catch {
        showToast('Tema tersimpan lokal, engine offline');
      }
    }

    closeDialog(settingsOverlay);
    showToast('Settings Saved');
  }

  function updateTempScale(val) {
    const clamped = Math.min(150, Math.max(100, Math.round(val)));
    state.tempScale = clamped / 100;
    applyScale(state.tempScale);
  }

  // About Modal Handlers
  function showAbout() {
    if (!aboutOverlay) return;
    openDialog(aboutOverlay, aboutOkBtn);
  }

  function hideAbout() {
    closeDialog(aboutOverlay);
  }

  // Modal
  function showModal(title, html) {
    modalTitle.textContent = title;
    modalBody.innerHTML = html;
    openDialog(modalOverlay, modalOkBtn);
  }

  function hideModal() {
    closeDialog(modalOverlay);
  }

  // Toast
  function showToast(msg) {
    clearTimeout(state.toastTimeout);
    toastEl.textContent = msg;
    toastEl.classList.remove('hidden');
    toastEl.removeAttribute('aria-hidden');
    state.toastTimeout = setTimeout(() => {
      toastEl.classList.add('hidden');
      toastEl.setAttribute('aria-hidden', 'true');
    }, 2400);
  }

  // WAI-ARIA tabs pattern: roving tabindex and arrow/Home/End navigation
  function activateTab(tab) {
    filterTabs.forEach(t => {
      const active = t === tab;
      t.classList.toggle('active', active);
      t.setAttribute('aria-selected', active ? 'true' : 'false');
      t.tabIndex = active ? 0 : -1;
    });
    state.activeCategory = tab.getAttribute('data-category');
    if (libraryPanel) libraryPanel.setAttribute('aria-labelledby', tab.id);
    loadSongs();
  }

  function onTabKeydown(e) {
    const idx = filterTabs.indexOf(e.currentTarget);
    let next = -1;
    if (e.key === 'ArrowRight') next = (idx + 1) % filterTabs.length;
    else if (e.key === 'ArrowLeft') next = (idx - 1 + filterTabs.length) % filterTabs.length;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = filterTabs.length - 1;
    if (next === -1) return;
    e.preventDefault();
    filterTabs[next].focus();
    activateTab(filterTabs[next]);
  }

  // Event Listeners
  function setupEventListeners() {
    searchInput.addEventListener('input', () => {
      clearTimeout(state.searchTimeout);
      state.searchTimeout = setTimeout(loadSongs, 70);
    });

    clearSearchBtn.addEventListener('click', () => {
      searchInput.value = '';
      loadSongs();
      searchInput.focus();
    });

    songListEl.addEventListener('scroll', handleSongListScroll);

    // Keyboard navigation inside the listbox container
    songListEl.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        navigateSongList(e.key === 'ArrowDown' ? 1 : -1);
      } else if (e.key === 'Home') {
        e.preventDefault();
        navigateSongList(-state.currentResults.length);
      } else if (e.key === 'End') {
        e.preventDefault();
        navigateSongList(state.currentResults.length);
      } else if (e.key === 'Enter' || e.key === ' ') {
        if (state.selectedSong) {
          e.preventDefault();
          addToRundown(state.selectedSong);
        }
      }
    });

    filterTabs.forEach(tab => {
      tab.addEventListener('click', () => activateTab(tab));
      tab.addEventListener('keydown', onTabKeydown);
    });

    addToRundownBtn.addEventListener('click', () => {
      if (state.selectedSong) addToRundown(state.selectedSong);
    });

    playlistNameInput.addEventListener('input', () => {
      savePreferences();
    });

    clearRundownBtn.addEventListener('click', () => {
      if (!state.rundown.length) return;
      if (window.confirm('Clear all songs from playlist?')) {
        state.rundown = [];
        renderRundown();
        savePreferences();
        showToast('Playlist cleared');
      }
    });

    copyWaBtn.addEventListener('click', copyRundownForWhatsApp);
    injectBtn.addEventListener('click', injectToProPresenter);

    // Settings Modal
    if (settingsBtn) settingsBtn.addEventListener('click', showSettings);
    setupUpdateCenter();
    if (settingsCloseBtn) settingsCloseBtn.addEventListener('click', cancelSettings);
    if (settingsCancelBtn) settingsCancelBtn.addEventListener('click', cancelSettings);
    if (settingsSaveBtn) settingsSaveBtn.addEventListener('click', saveSettings);
    if (settingsOverlay) {
      settingsOverlay.addEventListener('click', (e) => {
        if (e.target === settingsOverlay) cancelSettings();
      });
      settingsOverlay.addEventListener('keydown', (e) => trapFocus(e, settingsOverlay));
    }

    if (scaleSlider) {
      scaleSlider.addEventListener('input', (e) => {
        updateTempScale(parseFloat(e.target.value));
      });
    }

    if (scaleMinusBtn) {
      scaleMinusBtn.addEventListener('click', () => {
        updateTempScale(Math.round(currentScale * 100) - 5);
      });
    }

    if (scalePlusBtn) {
      scalePlusBtn.addEventListener('click', () => {
        updateTempScale(Math.round(currentScale * 100) + 5);
      });
    }

    if (settingsThemeSelect) {
      settingsThemeSelect.addEventListener('change', updateThemePreview);
    }

    const installFontBtn = document.getElementById('install-font-btn');
    if (installFontBtn) {
      installFontBtn.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/font/install', { method: 'POST' });
          const data = await res.json();
          if (!res.ok || !data.success) throw new Error('font launch failed');
          showToast('Membuka font installer di Windows...');
        } catch {
          showToast('File font tersedia di tools/fonts/CMGSans-Bold.ttf');
        }
      });
    }

    const cleanBanksBtn = document.getElementById('clean-banks-btn');
    if (cleanBanksBtn) {
      cleanBanksBtn.addEventListener('click', async () => {
        if (window.confirm('Bersihkan seluruh presentasi .pro di folder Banks ProPresenter?')) {
          try {
            const res = await fetch('/api/banks/clean', {
              method: 'POST',
              headers: { 'X-Banklycs-Confirm': 'clean-banks' }
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
            state.banksCount = 0;
            updateSettingsStatusText();
            showToast(data.message || 'Folder Banks dibersihkan');
          } catch {
            showToast('Gagal membersihkan Banks');
          }
        }
      });
    }

    const openBanksBtn = document.getElementById('open-banks-btn');
    if (openBanksBtn) {
      openBanksBtn.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/banks/open', { method: 'POST' });
          const data = await res.json();
          if (!res.ok || !data.success) throw new Error('open failed');
          showToast('Membuka folder Libraries/Banks di Explorer...');
        } catch {
          showToast('Folder Libraries/Banks tidak ditemukan');
        }
      });
    }

    // About Modal
    if (aboutBtn) aboutBtn.addEventListener('click', showAbout);
    if (aboutCloseBtn) aboutCloseBtn.addEventListener('click', hideAbout);
    if (aboutOkBtn) aboutOkBtn.addEventListener('click', hideAbout);
    if (aboutOverlay) {
      aboutOverlay.addEventListener('click', (e) => {
        if (e.target === aboutOverlay) hideAbout();
      });
      aboutOverlay.addEventListener('keydown', (e) => trapFocus(e, aboutOverlay));
    }

    // Modal close
    modalCloseBtn.addEventListener('click', hideModal);
    modalOkBtn.addEventListener('click', hideModal);
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) hideModal();
    });
    modalOverlay.addEventListener('keydown', (e) => trapFocus(e, modalOverlay));

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
      const tag = (e.target && e.target.tagName) || '';
      const isTypingField = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
      const isFormControl = isTypingField || tag === 'BUTTON' || tag === 'A';

      if ((e.key === '/' || e.key === 'F3') && !isTypingField) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }

      if (e.key === 'F11') {
        e.preventDefault();
        toggleFullscreen();
      }

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
        if (aboutOverlay && !aboutOverlay.classList.contains('hidden')) {
          hideAbout();
          return;
        }

        if (settingsOverlay && !settingsOverlay.classList.contains('hidden')) {
          saveSettings();
          return;
        }

        if (!modalOverlay.classList.contains('hidden')) {
          hideModal();
          return;
        }

        // Only the search field or the listbox may trigger "add on Enter".
        // Native buttons/links/selects keep their own activation behaviour.
        if (isFormControl && document.activeElement !== searchInput) return;

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
        } else if (state.selectedSong) {
          addToRundown(state.selectedSong);
        }
      }

      if (e.key === 'Escape') {
        if (aboutOverlay && !aboutOverlay.classList.contains('hidden')) {
          hideAbout();
        } else if (settingsOverlay && !settingsOverlay.classList.contains('hidden')) {
          cancelSettings();
        } else if (!modalOverlay.classList.contains('hidden')) {
          hideModal();
        } else if (searchInput.value) {
          searchInput.value = '';
          loadSongs();
        }
      }
    });
  }

  function navigateSongList(direction) {
    if (!state.currentResults.length) return;
    let curIdx = state.selectedSong ? state.currentResults.findIndex(s => s.filename === state.selectedSong.filename) : -1;
    let nextIdx;
    if (Math.abs(direction) > 1) {
      nextIdx = direction > 0 ? state.currentResults.length - 1 : 0;
    } else {
      nextIdx = curIdx + direction;
    }
    if (nextIdx < 0) nextIdx = 0;
    if (nextIdx >= state.currentResults.length) nextIdx = state.currentResults.length - 1;

    const nextSong = state.currentResults[nextIdx];
    if (!nextSong) return;
    selectSong(nextSong);
    const row = document.getElementById(`song-row-${nextIdx}`);
    if (row) row.scrollIntoView({ block: 'nearest' });
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

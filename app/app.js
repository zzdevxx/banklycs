// ==============================================================================
// PROPRESENTER LYRICBANKS — APP.JS
// High Performance, Zero-Lag, Studio Console Logic
// ==============================================================================

(function () {
  'use strict';

  // State
  let allCount = 0;
  let currentResults = [];
  let selectedSong = null;
  let rundown = [];
  let activeCategory = 'ALL';
  let searchTimeout = null;

  // DOM Elements
  const statusText = document.getElementById('status-text');
  const resultsCount = document.getElementById('results-count');
  const rundownCount = document.getElementById('rundown-count');
  const searchInput = document.getElementById('search-input');
  const clearSearchBtn = document.getElementById('clear-search-btn');
  const filterChips = document.querySelectorAll('.filter-chip');
  const songListEl = document.getElementById('song-list');
  const inspectorTitleEl = document.getElementById('inspector-song-title');
  const inspectorContentEl = document.getElementById('inspector-content');
  const addToRundownBtn = document.getElementById('add-to-rundown-btn');
  const playlistNameInput = document.getElementById('playlist-name-input');
  const rundownListEl = document.getElementById('rundown-list');
  const clearRundownBtn = document.getElementById('clear-rundown-btn');
  const injectBtn = document.getElementById('inject-btn');
  const modalOverlay = document.getElementById('modal-overlay');
  const modalTitle = document.getElementById('modal-title');
  const modalBody = document.getElementById('modal-body');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const modalOkBtn = document.getElementById('modal-ok-btn');

  // Initialize
  async function init() {
    setupDefaultPlaylistName();
    setupEventListeners();
    await checkStatus();
    loadSongs();
  }

  function setupDefaultPlaylistName() {
    // Default name: "Ibadah Raya - [Next Sunday Date]"
    const today = new Date();
    const daysUntilSunday = (7 - today.getDay()) % 7;
    const nextSunday = new Date(today);
    nextSunday.setDate(today.getDate() + (daysUntilSunday === 0 ? 0 : daysUntilSunday));
    
    const options = { day: 'numeric', month: 'short', year: 'numeric' };
    const dateStr = nextSunday.toLocaleDateString('id-ID', options);
    playlistNameInput.value = `Ibadah Raya - ${dateStr}`;
  }

  async function checkStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      allCount = data.total_songs || 0;
      statusText.textContent = `${allCount.toLocaleString()} LAGU MASTER TERHUBUNG`;
      if (!data.propresenter_dir) {
        statusText.textContent += ' (PROPRESENTER TIDAK TERDETEKSI)';
      }
    } catch (e) {
      statusText.textContent = 'GAGAL TERHUBUNG KE SERVER LOKAL';
    }
  }

  async function loadSongs() {
    const q = searchInput.value.trim();
    songListEl.innerHTML = '<div class="empty-placeholder">Mencari lagu...</div>';

    try {
      const url = `/api/songs?q=${encodeURIComponent(q)}&category=${encodeURIComponent(activeCategory)}&limit=150`;
      const res = await fetch(url);
      const data = await res.json();
      currentResults = data.songs || [];
      resultsCount.textContent = `${currentResults.length} LAGU DITEMUKAN`;
      renderSongList();
    } catch (e) {
      songListEl.innerHTML = '<div class="empty-placeholder">Error memuat data</div>';
    }
  }

  function renderSongList() {
    if (!currentResults.length) {
      songListEl.innerHTML = '<div class="empty-placeholder">Tidak ada lagu yang cocok dengan pencarian.</div>';
      return;
    }

    const fragment = document.createDocumentFragment();
    currentResults.forEach((song, idx) => {
      const item = document.createElement('div');
      item.className = 'song-item' + (selectedSong && selectedSong.filename === song.filename ? ' selected' : '');
      item.setAttribute('role', 'option');
      item.setAttribute('data-idx', idx);

      item.innerHTML = `
        <div class="song-item-info">
          <div class="song-item-title">${escapeHtml(song.title)}</div>
          <div class="song-item-artist">${escapeHtml(song.artist || 'Artis Tidak Diketahui')}</div>
        </div>
        <span class="cat-tag">${escapeHtml(song.category)}</span>
      `;

      item.addEventListener('click', () => {
        selectSong(song);
      });

      fragment.appendChild(item);
    });

    songListEl.innerHTML = '';
    songListEl.appendChild(fragment);
  }

  async function selectSong(song) {
    selectedSong = song;
    addToRundownBtn.disabled = false;

    // Highlight selected item in list
    document.querySelectorAll('.song-item').forEach(el => el.classList.remove('selected'));
    const matchedEl = Array.from(document.querySelectorAll('.song-item')).find(el => {
      const idx = el.getAttribute('data-idx');
      return currentResults[idx] && currentResults[idx].filename === song.filename;
    });
    if (matchedEl) matchedEl.classList.add('selected');

    inspectorTitleEl.textContent = song.title + (song.artist ? ` — ${song.artist}` : '');
    inspectorContentEl.innerHTML = '<div class="empty-placeholder">Memuat slide lirik...</div>';

    try {
      const res = await fetch(`/api/lyrics?file=${encodeURIComponent(song.filename)}`);
      const data = await res.json();
      renderLyrics(data);
    } catch (e) {
      inspectorContentEl.innerHTML = '<div class="empty-placeholder">Gagal memuat lirik lagu ini.</div>';
    }
  }

  function renderLyrics(data) {
    if (!data.groups || !data.groups.length) {
      inspectorContentEl.innerHTML = '<div class="empty-placeholder">Format lirik kosong.</div>';
      return;
    }

    inspectorContentEl.innerHTML = '';
    let globalSlideNum = 1;

    data.groups.forEach(group => {
      const groupBlock = document.createElement('div');
      groupBlock.className = 'slide-group-block';

      const headerLabel = document.createElement('div');
      headerLabel.className = 'group-header-label';
      headerLabel.textContent = group.header;
      groupBlock.appendChild(headerLabel);

      group.slides.forEach(slideLines => {
        const slideCard = document.createElement('div');
        const isBlank = group.header === 'BLANK';
        slideCard.className = 'slide-card' + (isBlank ? ' slide-card-blank' : '');

        const numSpan = document.createElement('span');
        numSpan.className = 'slide-number';
        numSpan.textContent = `SLIDE ${globalSlideNum++}`;
        slideCard.appendChild(numSpan);

        slideLines.forEach(line => {
          const p = document.createElement('div');
          p.className = 'slide-text-line';
          p.textContent = line;
          slideCard.appendChild(p);
        });

        groupBlock.appendChild(slideCard);
      });

      inspectorContentEl.appendChild(groupBlock);
    });
  }

  function addToRundown(song) {
    if (!song) return;
    rundown.push({ ...song, id: Date.now() + Math.random() });
    renderRundown();
  }

  function renderRundown() {
    rundownCount.textContent = `${rundown.length} LAGU`;
    injectBtn.disabled = rundown.length === 0;

    if (!rundown.length) {
      rundownListEl.innerHTML = '<div class="empty-placeholder">Rundown ibadah masih kosong. Pilih lagu dari tengah lalu klik [+ Tambah ke Rundown].</div>';
      return;
    }

    rundownListEl.innerHTML = '';
    rundown.forEach((item, idx) => {
      const el = document.createElement('div');
      el.className = 'rundown-item';

      el.innerHTML = `
        <div class="rundown-item-left">
          <span class="rundown-order-num">${idx + 1}.</span>
          <div class="rundown-item-text">
            <div class="rundown-item-title">${escapeHtml(item.title)}</div>
            <div class="rundown-item-artist">${escapeHtml(item.artist || item.category)}</div>
          </div>
        </div>
        <div class="rundown-item-controls">
          <button class="btn-ctrl btn-ctrl-up" title="Pindah ke atas" ${idx === 0 ? 'disabled' : ''}>▲</button>
          <button class="btn-ctrl btn-ctrl-down" title="Pindah ke bawah" ${idx === rundown.length - 1 ? 'disabled' : ''}>▼</button>
          <button class="btn-ctrl btn-ctrl-remove" title="Hapus dari rundown">✕</button>
        </div>
      `;

      el.querySelector('.btn-ctrl-up').addEventListener('click', () => moveRundown(idx, -1));
      el.querySelector('.btn-ctrl-down').addEventListener('click', () => moveRundown(idx, 1));
      el.querySelector('.btn-ctrl-remove').addEventListener('click', () => removeRundown(idx));

      rundownListEl.appendChild(el);
    });
  }

  function moveRundown(index, delta) {
    const target = index + delta;
    if (target < 0 || target >= rundown.length) return;
    const temp = rundown[index];
    rundown[index] = rundown[target];
    rundown[target] = temp;
    renderRundown();
  }

  function removeRundown(index) {
    rundown.splice(index, 1);
    renderRundown();
  }

  async function injectToProPresenter() {
    if (!rundown.length) return;
    const playlistName = playlistNameInput.value.trim() || 'Ibadah Hari Minggu';

    injectBtn.disabled = true;
    injectBtn.textContent = 'MENG-INJECT KE PROPRESENTER...';

    const songFileNames = rundown.map(s => s.pro);

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
      if (res.ok && data.success) {
        showModal(
          'Injeksi Berhasil!',
          `
            <div style="font-weight: 700; color: #22c55e; margin-bottom: 8px;">
              Playlist '${escapeHtml(data.playlist)}' berhasil didaftarkan ke ProPresenter!
            </div>
            <p><strong>Total Lagu:</strong> ${data.songs_count} lagu</p>
            <p><strong>Disalin ke Library Banks:</strong> ${data.copied_to_library} file .pro</p>
            <div style="margin-top: 12px; padding: 10px; background: #141414; border: 1px solid #333; font-size: 13px;">
              Buka aplikasi ProPresenter 7 sekarang. Playlist sudah langsung muncul di panel Playlist tanpa perlu restart!
            </div>
          `
        );
      } else {
        showModal('Injeksi Gagal', `<div style="color: #ef4444;">${escapeHtml(data.error || 'Terjadi kesalahan sistem')}</div>`);
      }
    } catch (e) {
      showModal('Koneksi Gagal', 'Tidak dapat berkomunikasi dengan engine lokal.');
    } finally {
      injectBtn.disabled = false;
      injectBtn.textContent = 'INJECT KE PROPRESENTER';
    }
  }

  function showModal(title, htmlBody) {
    modalTitle.textContent = title;
    modalBody.innerHTML = htmlBody;
    modalOverlay.classList.remove('hidden');
  }

  function hideModal() {
    modalOverlay.classList.add('hidden');
  }

  function setupEventListeners() {
    // Search input typing debounce
    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(loadSongs, 150);
    });

    clearSearchBtn.addEventListener('click', () => {
      searchInput.value = '';
      loadSongs();
      searchInput.focus();
    });

    // Category filter tabs
    filterChips.forEach(chip => {
      chip.addEventListener('click', () => {
        filterChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        activeCategory = chip.getAttribute('data-category');
        loadSongs();
      });
    });

    // Add to rundown
    addToRundownBtn.addEventListener('click', () => {
      if (selectedSong) addToRundown(selectedSong);
    });

    // Clear rundown
    clearRundownBtn.addEventListener('click', () => {
      if (!rundown.length) return;
      if (confirm('Kosongkan semua lagu dari rundown playlist?')) {
        rundown = [];
        renderRundown();
      }
    });

    // Inject action
    injectBtn.addEventListener('click', injectToProPresenter);

    // Modal close
    modalCloseBtn.addEventListener('click', hideModal);
    modalOkBtn.addEventListener('click', hideModal);
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) hideModal();
    });

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
      if (e.key === '/' && document.activeElement !== searchInput && document.activeElement !== playlistNameInput) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
      if (e.key === 'Escape') {
        if (!modalOverlay.classList.contains('hidden')) {
          hideModal();
        } else if (searchInput.value) {
          searchInput.value = '';
          loadSongs();
        }
      }
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Run app
  document.addEventListener('DOMContentLoaded', init);
})();

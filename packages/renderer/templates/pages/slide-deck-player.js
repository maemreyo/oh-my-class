
(() => {
  const VALID_PRINT_MODES = ['print-mode--paged-1', 'print-mode--paged-2', 'print-mode--paged-4', 'print-mode--paged-6', 'print-mode--continuous'];

  function isValidPrintMode(value) {
    return VALID_PRINT_MODES.indexOf(value) !== -1;
  }

  function printModeFromLayout(layout, perPage) {
    if (layout === 'continuous') return 'print-mode--continuous';
    const allowed = [1, 2, 4, 6];
    const n = allowed.indexOf(perPage) !== -1 ? perPage : 1;
    return 'print-mode--paged-' + n;
  }

  // SDH-03: '?print=paged&slidesPerPage=4' or '#surface=student' -- read
  // from both query and hash so either style of link works, and never throw
  // on a malformed value (falls through to the server-resolved default).
  function readLocationOverrides() {
    const overrides = {};
    try {
      const query = new URLSearchParams(window.location.search);
      const hash = new URLSearchParams(window.location.hash.replace(/^#/, ''));
      const printParam = query.get('print') || hash.get('print');
      const perPageParam = query.get('slidesPerPage') || hash.get('slidesPerPage');
      if (printParam === 'paged' || printParam === 'continuous') {
        overrides.printMode = printModeFromLayout(printParam, perPageParam ? parseInt(perPageParam, 10) : 1);
      }
      const surfaceParam = query.get('surface') || hash.get('surface');
      if (surfaceParam === 'student' || surfaceParam === 'teacher') overrides.surfacePreview = surfaceParam;
    } catch (locationError) {
      // ponytail: a malformed hash/query degrades to the server-resolved default, never throws.
    }
    return overrides;
  }

  function storageKey(deckId) {
    return 'omc:slide-deck:' + deckId + ':prefs';
  }

  function readStoredPrefs(deckId) {
    try {
      const raw = window.localStorage.getItem(storageKey(deckId));
      return raw ? JSON.parse(raw) : null;
    } catch (storageError) {
      return null; // file://, private mode, or storage disabled -- degrade gracefully.
    }
  }

  function writeStoredPrefs(deckId, prefs) {
    try {
      window.localStorage.setItem(storageKey(deckId), JSON.stringify(prefs));
    } catch (storageError) {
      // ponytail: storage unavailable -- in-memory state still works for this page view.
    }
  }

  function initializeSlideDecks() {
  const decks = document.querySelectorAll('[data-slide-deck]');
  const locationOverrides = readLocationOverrides();
  decks.forEach((deck) => {
    const deckId = deck.getAttribute('data-deck-id') || 'unknown-deck';
    const isTeacherDeck = deck.dataset.surface === 'teacher' || deck.dataset.surface === 'review';
    const slides = Array.from(deck.querySelectorAll('[data-slide]'));
    const progress = deck.querySelector('[data-slide-progress]');
    const previous = deck.querySelector('[data-slide-prev]');
    const next = deck.querySelector('[data-slide-next]');
    const print = deck.querySelector('[data-slide-print]');
    const printModeButtons = Array.from(deck.querySelectorAll('[data-slide-print-mode]'));
    const chromeToggle = deck.querySelector('[data-slide-chrome-toggle]');
    const previewToggle = deck.querySelector('[data-slide-teacher-preview]');
    let current = 0;
    // ponytail: only a teacher/review render ever reads/writes localStorage
    // -- a student-clean export's persisted state must never exist (SDH-03).
    const stored = isTeacherDeck ? readStoredPrefs(deckId) : null;

    function persist() {
      if (!isTeacherDeck) return;
      writeStoredPrefs(deckId, {
        printMode: VALID_PRINT_MODES.filter((cls) => deck.classList.contains(cls))[0] || 'print-mode--paged-1',
        studentPreview: deck.classList.contains('slide-deck--student-preview'),
        chromeVisible: !document.body.classList.contains('omc-hide-footer-print'),
      });
    }

    function applyPrintMode(mode) {
      VALID_PRINT_MODES.forEach((cls) => deck.classList.remove(cls));
      deck.classList.add(mode);
      printModeButtons.forEach((button) => {
        const active = button.getAttribute('data-print-mode-value') === mode;
        button.setAttribute('aria-checked', String(active));
        button.classList.toggle('slide-print-mode-option--active', active);
      });
    }

    function applyStudentPreview(active) {
      deck.classList.toggle('slide-deck--student-preview', active);
      if (previewToggle) previewToggle.setAttribute('aria-checked', String(active));
    }

    function applyChromeVisible(visible) {
      document.body.classList.toggle('omc-hide-footer-print', !visible);
      if (chromeToggle) chromeToggle.setAttribute('aria-checked', String(visible));
    }

    const initialPrintMode = locationOverrides.printMode
      || (stored && isValidPrintMode(stored.printMode) ? stored.printMode : null);
    if (initialPrintMode) applyPrintMode(initialPrintMode);

    if (isTeacherDeck) {
      const initialPreview = locationOverrides.surfacePreview
        ? locationOverrides.surfacePreview === 'student'
        : !!(stored && stored.studentPreview);
      applyStudentPreview(initialPreview);
      applyChromeVisible(!(stored && stored.chromeVisible === false));
    }

    function show(index) {
      current = Math.max(0, Math.min(index, slides.length - 1));
      slides.forEach((slide, slideIndex) => {
        const active = slideIndex === current;
        slide.setAttribute('aria-hidden', String(!active));
      });
      if (progress) progress.textContent = 'Slide ' + (current + 1) + ' / ' + slides.length;
      if (previous) previous.disabled = current === 0;
      if (next) next.disabled = current === slides.length - 1;
    }

    previous?.addEventListener('click', () => show(current - 1));
    next?.addEventListener('click', () => show(current + 1));
    print?.addEventListener('click', () => window.print());
    printModeButtons.forEach((button) => {
      button.addEventListener('click', () => {
        const mode = button.getAttribute('data-print-mode-value');
        if (isValidPrintMode(mode)) { applyPrintMode(mode); persist(); }
      });
    });
    previewToggle?.addEventListener('click', () => {
      applyStudentPreview(previewToggle.getAttribute('aria-checked') !== 'true');
      persist();
    });
    chromeToggle?.addEventListener('click', () => {
      applyChromeVisible(chromeToggle.getAttribute('aria-checked') !== 'true');
      persist();
    });

    // Arrow/space/home/end drive slide navigation, but not while a toolbar
    // button (print-mode radio, chrome/preview switch, prev/next/print
    // itself) has focus -- otherwise Space on a focused toggle button would
    // also flip slides underneath it, and this deck's own nav buttons would
    // double-fire on every click.
    document.addEventListener('keydown', (event) => {
      if (event.target instanceof Element && event.target.closest('.slide-toolbar')) return;
      if (event.key === 'ArrowRight' || event.key === ' ') show(current + 1);
      if (event.key === 'ArrowLeft') show(current - 1);
      if (event.key === 'Home') show(0);
      if (event.key === 'End') show(slides.length - 1);
    });
    deck.classList.add('slide-deck--js-ready');
    show(0);
  });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeSlideDecks, { once: true });
  } else {
    initializeSlideDecks();
  }
})();
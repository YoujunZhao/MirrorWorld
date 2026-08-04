(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  const playVideos = (videos, { reset = false } = {}) => {
    if (reset) {
      videos.forEach((video) => {
        video.currentTime = 0;
      });
    }

    videos.forEach((video) => {
      const attempt = video.play();
      if (attempt && typeof attempt.catch === 'function') {
        attempt.catch(() => {
          // Autoplay can be blocked; the visible group control remains available.
        });
      }
    });
  };

  const pauseVideos = (videos) => {
    videos.forEach((video) => video.pause());
  };

  const updateToggle = (button, paused) => {
    if (!button) return;
    button.setAttribute('aria-pressed', String(paused));
    const icon = button.querySelector('.toggle-icon');
    const label = button.querySelector('.toggle-label');
    if (icon) icon.textContent = paused ? '▶' : 'Ⅱ';
    if (label) label.textContent = paused ? 'Play all' : 'Pause all';
  };

  const videoGroups = [...document.querySelectorAll('[data-video-group]')];

  videoGroups.forEach((group) => {
    const groupName = group.dataset.videoGroup;
    const button = document.querySelector(`[data-toggle-group="${groupName}"]`);
    const videos = [...group.querySelectorAll('video')];

    button?.addEventListener('click', () => {
      const shouldPause = group.dataset.userPaused !== 'true';
      group.dataset.userPaused = String(shouldPause);
      if (shouldPause) {
        pauseVideos(videos);
      } else {
        playVideos(videos, { reset: true });
      }
      updateToggle(button, shouldPause);
    });
  });

  if ('IntersectionObserver' in window) {
    const groupObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const group = entry.target;
          const videos = [...group.querySelectorAll('video')];
          if (entry.isIntersecting && group.dataset.userPaused !== 'true' && !reducedMotion.matches) {
            playVideos(videos, { reset: true });
          } else {
            pauseVideos(videos);
          }
        });
      },
      { threshold: 0.22 }
    );
    videoGroups.forEach((group) => groupObserver.observe(group));

    const ambientObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const video = entry.target;
          if (entry.isIntersecting && !reducedMotion.matches && !video.dataset.userPaused) {
            const attempt = video.play();
            if (attempt && typeof attempt.catch === 'function') attempt.catch(() => {});
          } else if (!entry.isIntersecting) {
            video.pause();
          }
        });
      },
      { threshold: 0.35 }
    );
    document.querySelectorAll('.ambient-video').forEach((video) => ambientObserver.observe(video));
  }

  document.querySelectorAll('.ambient-video').forEach((video) => {
    video.addEventListener('pause', () => {
      if (video.currentTime > 0 && !video.ended) video.dataset.userPaused = 'true';
    });
    video.addEventListener('play', () => {
      delete video.dataset.userPaused;
    });
  });

  const reveals = [...document.querySelectorAll('.reveal')];
  if (reducedMotion.matches || !('IntersectionObserver' in window)) {
    reveals.forEach((element) => element.classList.add('is-visible'));
  } else {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.08 }
    );
    reveals.forEach((element) => revealObserver.observe(element));
  }

  const navLinks = new Map(
    [...document.querySelectorAll('[data-nav-link]')].map((link) => [link.hash.slice(1), link])
  );
  if ('IntersectionObserver' in window) {
    const sectionObserver = new IntersectionObserver(
      (entries) => {
        const visibleEntry = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!visibleEntry) return;
        navLinks.forEach((link, id) => {
          link.classList.toggle('is-active', id === visibleEntry.target.id);
        });
      },
      { rootMargin: '-20% 0px -65% 0px', threshold: [0, 0.25, 0.5] }
    );
    document.querySelectorAll('[data-section]').forEach((section) => sectionObserver.observe(section));
  }

  const copyButton = document.querySelector('[data-copy-bibtex]');
  const bibtex = document.querySelector('#bibtex-code');
  copyButton?.addEventListener('click', async () => {
    const text = bibtex?.textContent?.trim() || '';
    const label = copyButton.querySelector('.copy-label');
    const icon = copyButton.querySelector('.copy-icon');

    try {
      await navigator.clipboard.writeText(text);
      if (label) label.textContent = 'Copied';
      if (icon) icon.textContent = '✓';
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(bibtex);
      selection.removeAllRanges();
      selection.addRange(range);
      if (label) label.textContent = 'Selected — press copy';
    }

    window.setTimeout(() => {
      if (label) label.textContent = 'Copy BibTeX';
      if (icon) icon.textContent = '□';
    }, 2200);
  });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      pauseVideos([...document.querySelectorAll('video')]);
    }
  });
})();

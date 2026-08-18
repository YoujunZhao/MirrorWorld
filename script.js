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

  const syncAmbientPlayback = (videos) => {
    const visibleVideos = videos.filter(
      (video) => !document.hidden && !reducedMotion.matches && video.dataset.inViewport !== 'false'
    );
    const pausedVideos = videos.filter((video) => !visibleVideos.includes(video));

    pauseVideos(pausedVideos);
    playVideos(visibleVideos);
  };

  const updateToggle = (button, paused) => {
    if (!button) return;
    button.setAttribute('aria-pressed', String(paused));
    const icon = button.querySelector('.toggle-icon');
    const label = button.querySelector('.toggle-label');
    if (icon) icon.textContent = paused ? '▶' : 'Ⅱ';
    if (label) label.textContent = paused ? 'Play all' : 'Pause all';
  };

  const setSliderPosition = (slider, value) => {
    const position = Math.max(0, Math.min(100, Number(value) || 0));
    slider.dataset.sliderPosition = String(position);
    slider.style.setProperty('--slider-position', `${position}%`);

    const handle = slider.querySelector('[data-slider-handle]');
    if (!handle) return;
    handle.setAttribute('aria-valuenow', String(Math.round(position)));
    handle.setAttribute('aria-valuetext', position <= 5 ? 'Reflection' : position >= 95 ? 'Input' : 'Input and reflection');
    handle.setAttribute('aria-pressed', String(position <= 5 || position >= 95));
  };

  const toggleSlider = (slider) => {
    const current = Number(slider.dataset.sliderPosition || 50);
    setSliderPosition(slider, current < 50 ? 100 : 0);
  };

  const setupVideoSliders = () => {
    document.querySelectorAll('[data-video-slider]').forEach((slider) => {
      const handle = slider.querySelector('[data-slider-handle]');
      const divider = slider.querySelector('.video-slider-divider');
      const videos = [...slider.querySelectorAll('video')];
      const directPlay = Boolean(slider.closest('[data-slider-direct-play]'));
      if (!handle) return;
      divider?.removeAttribute('aria-hidden');
      slider.dataset.sliderInViewport = 'false';

      setSliderPosition(slider, 50);

      let dragging = false;
      let dragged = false;
      let startX = 0;
      const updateFromPointer = (event) => {
        const bounds = slider.getBoundingClientRect();
        const next = ((event.clientX - bounds.left) / bounds.width) * 100;
        setSliderPosition(slider, next);
      };

      handle.addEventListener('pointerdown', (event) => {
        dragging = true;
        dragged = false;
        startX = event.clientX;
        handle.setPointerCapture?.(event.pointerId);
        event.preventDefault();
      });
      handle.addEventListener('pointermove', (event) => {
        if (!dragging) return;
        if (Math.abs(event.clientX - startX) > 3) dragged = true;
        updateFromPointer(event);
      });
      handle.addEventListener('pointerup', (event) => {
        dragging = false;
        handle.releasePointerCapture?.(event.pointerId);
      });
      handle.addEventListener('pointercancel', () => {
        dragging = false;
      });
      handle.addEventListener('click', () => {
        if (dragged) {
          dragged = false;
          return;
        }
        toggleSlider(slider);
      });
      handle.addEventListener('keydown', (event) => {
        const current = Number(slider.dataset.sliderPosition || 50);
        if (event.key === 'ArrowLeft') {
          event.preventDefault();
          setSliderPosition(slider, current - 5);
        } else if (event.key === 'ArrowRight') {
          event.preventDefault();
          setSliderPosition(slider, current + 5);
        } else if (event.key === 'Home') {
          event.preventDefault();
          setSliderPosition(slider, 0);
        } else if (event.key === 'End') {
          event.preventDefault();
          setSliderPosition(slider, 100);
        } else if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          toggleSlider(slider);
        }
      });

      if (directPlay) {
        videos.forEach((video) => {
          video.playbackRate = 1;
        });
        return;
      }

      const masterVideo = slider.querySelector('.video-slider-input') || videos[0];
      const followerVideos = videos.filter((video) => video !== masterVideo);
      if (masterVideo && followerVideos.length) {
        const updateFollowerRates = () => {
          if (!Number.isFinite(masterVideo.duration) || masterVideo.duration <= 0) return;
          followerVideos.forEach((video) => {
            if (!Number.isFinite(video.duration) || video.duration <= 0) return;
            const rate = video.duration / masterVideo.duration;
            video.playbackRate = Math.max(0.5, Math.min(2, rate));
          });
        };
        const alignFollowers = (force = false) => {
          followerVideos.forEach((video) => {
            if (video.readyState < 1) return;
            const duration = Number.isFinite(video.duration) ? video.duration : masterVideo.currentTime;
            const target = Math.min(masterVideo.currentTime, duration || masterVideo.currentTime);
            if (force || Math.abs(video.currentTime - target) > 0.3) video.currentTime = target;
          });
        };

        [masterVideo, ...followerVideos].forEach((video) => {
          video.addEventListener('loadedmetadata', () => {
            updateFollowerRates();
            alignFollowers(true);
          });
        });
        masterVideo.addEventListener('play', () => {
          alignFollowers(true);
          followerVideos.forEach((video) => {
            const attempt = video.play();
            if (attempt && typeof attempt.catch === 'function') attempt.catch(() => {});
          });
        });
        masterVideo.addEventListener('pause', () => pauseVideos(followerVideos));
        masterVideo.addEventListener('seeking', () => alignFollowers(true));
        masterVideo.addEventListener('timeupdate', () => alignFollowers());
      }
    });
  };

  setupVideoSliders();

  const sharedInputGroups = new Map();
  document.querySelectorAll('[data-video-slider] .video-slider-input').forEach((video) => {
    if (video.closest('[data-slider-direct-play]')) return;
    const source = (video.getAttribute('src') || '').split('?')[0];
    if (!source) return;
    video.dataset.sliderInputSource = source;
    const group = sharedInputGroups.get(source) || [];
    group.push(video);
    sharedInputGroups.set(source, group);
  });

  const visibleSharedInputs = (group) => group.filter((video) => (
    video.closest('[data-video-slider]')?.dataset.sliderInViewport === 'true'
  ));

  const syncSharedInputGroup = (group, preferredReference = null, force = false) => {
    const visible = visibleSharedInputs(group);
    if (!visible.length) return;
    const reference = preferredReference && visible.includes(preferredReference)
      ? preferredReference
      : visible[visible.length - 1];
    visible.forEach((video) => {
      if (video === reference || video.readyState < 1) return;
      if (force || Math.abs(video.currentTime - reference.currentTime) > 0.16) {
        video.currentTime = reference.currentTime;
      }
      if (!reference.paused && video.paused) {
        const attempt = video.play();
        if (attempt && typeof attempt.catch === 'function') attempt.catch(() => {});
      } else if (reference.paused && !video.paused) {
        video.pause();
      }
    });
  };

  sharedInputGroups.forEach((group) => {
    if (group.length < 2) return;
    group.forEach((video) => {
      video.playbackRate = 1;
      video.addEventListener('loadedmetadata', () => syncSharedInputGroup(group, video, true));
      video.addEventListener('play', () => syncSharedInputGroup(group, video, true));
      video.addEventListener('timeupdate', () => {
        const visible = visibleSharedInputs(group);
        if (visible[visible.length - 1] === video) syncSharedInputGroup(group, video);
      });
    });
  });

  const syncSliderPlayback = (slider, inViewport) => {
    const group = slider.closest('[data-video-group]');
    const videos = [...slider.querySelectorAll('video')];
    slider.dataset.sliderInViewport = String(inViewport);
    const shouldPlay = inViewport && !document.hidden && !reducedMotion.matches && group?.dataset.userPaused !== 'true';
    if (shouldPlay) {
      playVideos(videos);
    } else {
      pauseVideos(videos);
    }
  };

  const videoGroups = [...document.querySelectorAll('[data-video-group]')];
  const ambientVideos = [...document.querySelectorAll('.ambient-video')];

  videoGroups.forEach((group) => {
    const groupName = group.dataset.videoGroup;
    const button = document.querySelector(`[data-toggle-group="${groupName}"]`);
    const videos = [...group.querySelectorAll('video')];

    button?.addEventListener('click', () => {
      const shouldPause = group.dataset.userPaused !== 'true';
      group.dataset.userPaused = String(shouldPause);
      if (shouldPause) {
        pauseVideos(videos);
      } else if (group.querySelector('[data-video-slider]')) {
        group.querySelectorAll('[data-video-slider]').forEach((slider) => {
          if (slider.dataset.sliderInViewport === 'true') {
            playVideos([...slider.querySelectorAll('video')], { reset: true });
          }
        });
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
          const sliders = [...group.querySelectorAll('[data-video-slider]')];
          if (sliders.length) {
            sliders.forEach((slider) => syncSliderPlayback(slider, entry.isIntersecting && slider.dataset.sliderInViewport === 'true'));
            return;
          }
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

    const sliderObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => syncSliderPlayback(entry.target, entry.isIntersecting));
      },
      { threshold: 0.18 }
    );
    document.querySelectorAll('[data-video-slider]').forEach((slider) => sliderObserver.observe(slider));

    const ambientObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const video = entry.target;
          video.dataset.inViewport = String(entry.isIntersecting);
          syncAmbientPlayback([video]);
        });
      },
      { threshold: 0.35 }
    );
    ambientVideos.forEach((video) => ambientObserver.observe(video));
  }

  syncAmbientPlayback(ambientVideos);

  reducedMotion.addEventListener('change', () => {
    const videos = [...document.querySelectorAll('.ambient-video')];
    if (reducedMotion.matches) {
      pauseVideos(videos);
      return;
    }

    syncAmbientPlayback(videos);
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
      return;
    }

    syncAmbientPlayback(ambientVideos);
  });
})();

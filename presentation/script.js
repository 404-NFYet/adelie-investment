// ============================================
// ADELIE Presentation — Slide Navigation
// ============================================

(function () {
    const slides = document.querySelectorAll('.slide');
    const totalSlides = slides.length;
    let currentIndex = 0;
    let isAnimating = false;

    const currentSlideEl = document.getElementById('current-slide');
    const totalSlidesEl = document.getElementById('total-slides');
    const progressFill = document.getElementById('progress-fill');

    totalSlidesEl.textContent = totalSlides;

    function updateUI() {
        currentSlideEl.textContent = currentIndex + 1;
        const progress = ((currentIndex) / (totalSlides - 1)) * 100;
        progressFill.style.width = progress + '%';
    }

    function goToSlide(index) {
        if (isAnimating || index === currentIndex || index < 0 || index >= totalSlides) return;
        isAnimating = true;

        const direction = index > currentIndex ? 1 : -1;
        const current = slides[currentIndex];
        const next = slides[index];

        // Remove all states
        slides.forEach(s => {
            s.classList.remove('active', 'prev');
        });

        // Set exit direction
        if (direction > 0) {
            current.classList.add('prev');
        }

        // Set enter direction
        next.style.transform = direction > 0 ? 'translateX(60px)' : 'translateX(-60px)';
        next.style.opacity = '0';
        next.style.visibility = 'visible';

        // Force reflow
        void next.offsetWidth;

        // Animate in
        next.classList.add('active');
        next.style.transform = '';
        next.style.opacity = '';

        currentIndex = index;
        updateUI();

        setTimeout(() => {
            isAnimating = false;
            slides.forEach((s, i) => {
                if (i !== currentIndex) {
                    s.style.visibility = 'hidden';
                    s.style.transform = '';
                    s.style.opacity = '';
                }
            });
        }, 600);
    }

    function nextSlide() {
        if (currentIndex < totalSlides - 1) {
            goToSlide(currentIndex + 1);
        }
    }

    function prevSlide() {
        if (currentIndex > 0) {
            goToSlide(currentIndex - 1);
        }
    }

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        switch (e.key) {
            case 'ArrowRight':
            case 'ArrowDown':
            case ' ':
            case 'PageDown':
                e.preventDefault();
                nextSlide();
                break;
            case 'ArrowLeft':
            case 'ArrowUp':
            case 'PageUp':
                e.preventDefault();
                prevSlide();
                break;
            case 'Home':
                e.preventDefault();
                goToSlide(0);
                break;
            case 'End':
                e.preventDefault();
                goToSlide(totalSlides - 1);
                break;
        }
    });

    // Click navigation (left half = prev, right half = next)
    document.addEventListener('click', (e) => {
        // Don't navigate when clicking interactive elements
        if (e.target.closest('a, button, input, select, textarea')) return;

        const x = e.clientX;
        const width = window.innerWidth;

        if (x < width * 0.3) {
            prevSlide();
        } else if (x > width * 0.7) {
            nextSlide();
        }
    });

    // Touch support
    let touchStartX = 0;
    let touchStartY = 0;

    document.addEventListener('touchstart', (e) => {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
    }, { passive: true });

    document.addEventListener('touchend', (e) => {
        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;

        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
            if (deltaX < 0) {
                nextSlide();
            } else {
                prevSlide();
            }
        }
    }, { passive: true });

    // Mouse wheel
    let wheelTimeout;
    document.addEventListener('wheel', (e) => {
        e.preventDefault();
        clearTimeout(wheelTimeout);
        wheelTimeout = setTimeout(() => {
            if (e.deltaY > 0) {
                nextSlide();
            } else {
                prevSlide();
            }
        }, 50);
    }, { passive: false });

    // Initialize
    updateUI();
    slides[0].classList.add('active');
    slides[0].style.visibility = 'visible';

    // Add staggered animation to child elements
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const children = entry.target.querySelectorAll(
                    '.stat-card, .feature-card, .toc__item, .problem-card, .flow-node, .risk-card, .solution-card, .principle-card, .trend-card, .mapping-row, .timeline__item, .context-node, .vision-item, .vibe-card, .scenario__step'
                );
                children.forEach((child, i) => {
                    child.style.opacity = '0';
                    child.style.transform = 'translateY(20px)';
                    setTimeout(() => {
                        child.style.transition = 'opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1), transform 0.5s cubic-bezier(0.16, 1, 0.3, 1)';
                        child.style.opacity = '1';
                        child.style.transform = 'translateY(0)';
                    }, 100 + i * 80);
                });
            }
        });
    });

    slides.forEach(slide => observer.observe(slide));

    // Re-trigger animation when slide becomes active
    const mutationObserver = new MutationObserver((mutations) => {
        mutations.forEach(mutation => {
            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                const slide = mutation.target;
                if (slide.classList.contains('active')) {
                    const children = slide.querySelectorAll(
                        '.stat-card, .feature-card, .toc__item, .problem-card, .flow-node, .risk-card, .solution-card, .principle-card, .trend-card, .mapping-row, .timeline__item, .context-node, .vision-item, .vibe-card, .scenario__step'
                    );
                    children.forEach((child, i) => {
                        child.style.opacity = '0';
                        child.style.transform = 'translateY(20px)';
                        child.style.transition = 'none';
                        void child.offsetWidth;
                        setTimeout(() => {
                            child.style.transition = 'opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1), transform 0.5s cubic-bezier(0.16, 1, 0.3, 1)';
                            child.style.opacity = '1';
                            child.style.transform = 'translateY(0)';
                        }, 100 + i * 80);
                    });
                }
            }
        });
    });

    slides.forEach(slide => {
        mutationObserver.observe(slide, { attributes: true });
    });
})();

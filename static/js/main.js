// BT Construction - Main JavaScript

document.addEventListener('DOMContentLoaded', function () {

  // ── Mobile nav toggle ──
  var btn = document.getElementById('mobile-menu-btn');
  var menu = document.getElementById('mobile-menu');
  var hamburger = document.getElementById('hamburger-icon');
  var closeIcon = document.getElementById('close-icon');

  if (btn && menu) {
    btn.addEventListener('click', function () {
      var isOpen = !menu.classList.contains('hidden');
      menu.classList.toggle('hidden');
      hamburger.classList.toggle('hidden');
      closeIcon.classList.toggle('hidden');
      btn.setAttribute('aria-expanded', !isOpen);
    });
  }

  // ── Portfolio filter ──
  var filterBtns = document.querySelectorAll('.filter-btn');
  var portfolioItems = document.querySelectorAll('[data-category]');

  filterBtns.forEach(function (filterBtn) {
    filterBtn.addEventListener('click', function () {
      var filter = this.getAttribute('data-filter');

      // Update active state
      filterBtns.forEach(function (b) { b.classList.remove('active'); });
      this.classList.add('active');

      // Show/hide items
      portfolioItems.forEach(function (item) {
        if (filter === 'all' || item.getAttribute('data-category') === filter) {
          item.style.display = '';
        } else {
          item.style.display = 'none';
        }
      });
    });
  });

  // ── Image lightbox ──
  var lightboxTriggers = document.querySelectorAll('[data-lightbox]');

  if (lightboxTriggers.length > 0) {
    // Collect image sources
    var images = [];
    lightboxTriggers.forEach(function (el) {
      images.push(el.getAttribute('data-lightbox'));
    });

    var currentIndex = 0;

    // Create overlay
    var overlay = document.createElement('div');
    overlay.id = 'lightbox-overlay';
    overlay.className = 'fixed inset-0 bg-black bg-opacity-90 z-50 hidden flex items-center justify-center';
    overlay.innerHTML =
      '<button id="lb-close" class="absolute top-4 right-4 text-white text-3xl font-bold z-10 hover:text-gold">&times;</button>' +
      '<button id="lb-prev" class="absolute left-4 text-white text-4xl font-bold z-10 hover:text-gold">&lsaquo;</button>' +
      '<button id="lb-next" class="absolute right-4 text-white text-4xl font-bold z-10 hover:text-gold">&rsaquo;</button>' +
      '<img id="lb-img" class="max-w-full max-h-[80vh] rounded-lg shadow-lg" src="" alt="Lightbox image">';
    document.body.appendChild(overlay);

    var lbImg = document.getElementById('lb-img');

    function showImage(index) {
      currentIndex = index;
      lbImg.src = images[index];
    }

    function openLightbox(index) {
      showImage(index);
      overlay.classList.remove('hidden');
      overlay.classList.add('flex');
      document.body.style.overflow = 'hidden';
    }

    function closeLightbox() {
      overlay.classList.add('hidden');
      overlay.classList.remove('flex');
      document.body.style.overflow = '';
    }

    lightboxTriggers.forEach(function (el, i) {
      el.addEventListener('click', function () { openLightbox(i); });
    });

    document.getElementById('lb-close').addEventListener('click', closeLightbox);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeLightbox();
    });

    document.getElementById('lb-prev').addEventListener('click', function (e) {
      e.stopPropagation();
      showImage((currentIndex - 1 + images.length) % images.length);
    });

    document.getElementById('lb-next').addEventListener('click', function (e) {
      e.stopPropagation();
      showImage((currentIndex + 1) % images.length);
    });

    document.addEventListener('keydown', function (e) {
      if (overlay.classList.contains('hidden')) return;
      if (e.key === 'Escape') closeLightbox();
      if (e.key === 'ArrowLeft') document.getElementById('lb-prev').click();
      if (e.key === 'ArrowRight') document.getElementById('lb-next').click();
    });
  }

  // ── Before/after slider ──
  var containers = document.querySelectorAll('.before-after-container');

  containers.forEach(function (container) {
    var slider = container.querySelector('.before-after-slider');
    var afterLayer = container.querySelector('.before-after-after');
    if (!slider || !afterLayer) return;

    var isDragging = false;

    function updateSlider(x) {
      var rect = container.getBoundingClientRect();
      var pos = Math.max(0, Math.min(x - rect.left, rect.width));
      var pct = (pos / rect.width) * 100;
      slider.style.left = pct + '%';
      afterLayer.style.clipPath = 'inset(0 0 0 ' + pct + '%)';
    }

    slider.addEventListener('mousedown', function (e) {
      e.preventDefault();
      isDragging = true;
    });

    document.addEventListener('mousemove', function (e) {
      if (!isDragging) return;
      updateSlider(e.clientX);
    });

    document.addEventListener('mouseup', function () {
      isDragging = false;
    });

    // Touch support
    slider.addEventListener('touchstart', function (e) {
      e.preventDefault();
      isDragging = true;
    });

    document.addEventListener('touchmove', function (e) {
      if (!isDragging) return;
      updateSlider(e.touches[0].clientX);
    });

    document.addEventListener('touchend', function () {
      isDragging = false;
    });
  });

  // ── Form validation & submission ──
  var apiBase = (document.querySelector('meta[name="api-base"]') || {}).content || '';
  var forms = document.querySelectorAll('[data-form]');

  forms.forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      // Check required fields
      var requiredFields = form.querySelectorAll('[required]');
      var valid = true;

      requiredFields.forEach(function (field) {
        if (!field.value.trim()) {
          valid = false;
          field.classList.add('border-red-500');
          field.addEventListener('input', function handler() {
            field.classList.remove('border-red-500');
            field.removeEventListener('input', handler);
          });
        }
      });

      if (!valid) return;

      var formName = form.getAttribute('data-form');
      var endpoint = formName === 'quote' ? '/submit/quote' : '/submit/contact';
      var successMsg = formName === 'quote'
        ? 'Thank you! Your quote request has been submitted. We\'ll be in touch within one business day.'
        : 'Thank you for your message! We\'ll get back to you soon.';

      // Check for file inputs with files selected
      var fileInput = form.querySelector('input[type="file"]');
      var hasFiles = fileInput && fileInput.files && fileInput.files.length > 0;

      var fetchOpts = { method: 'POST' };

      if (hasFiles) {
        // Use FormData for multipart upload
        var formData = new FormData();
        var fields = form.querySelectorAll('input:not([type="file"]), textarea, select');
        fields.forEach(function (field) {
          if (field.name) formData.append(field.name, field.value.trim());
        });
        for (var i = 0; i < fileInput.files.length; i++) {
          formData.append('photos', fileInput.files[i]);
        }
        fetchOpts.body = formData;
      } else {
        // Collect form data as JSON
        var payload = {};
        var fields = form.querySelectorAll('input, textarea, select');
        fields.forEach(function (field) {
          if (field.name) payload[field.name] = field.value.trim();
        });
        fetchOpts.headers = { 'Content-Type': 'application/json' };
        fetchOpts.body = JSON.stringify(payload);
      }

      // Disable submit button
      var submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;

      fetch(apiBase + endpoint, fetchOpts)
        .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, data: d }; }); })
        .then(function (result) {
          if (result.ok) {
            var successDiv = document.createElement('div');
            successDiv.className = 'form-success';
            successDiv.textContent = successMsg;
            form.parentNode.insertBefore(successDiv, form);
            form.style.display = 'none';
          } else {
            var errorDiv = form.querySelector('.form-error');
            if (!errorDiv) {
              errorDiv = document.createElement('div');
              errorDiv.className = 'form-error bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4';
              form.insertBefore(errorDiv, form.firstChild);
            }
            errorDiv.textContent = result.data.error || 'Something went wrong. Please try again.';
            if (submitBtn) submitBtn.disabled = false;
          }
        })
        .catch(function () {
          var errorDiv = form.querySelector('.form-error');
          if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'form-error bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4';
            form.insertBefore(errorDiv, form.firstChild);
          }
          errorDiv.textContent = 'Could not connect to server. Please try again later.';
          if (submitBtn) submitBtn.disabled = false;
        });
    });
  });

});

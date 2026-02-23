(function () {
  function injectRequiredStyles() {
    if (document.getElementById('novo-cadastro-required-style')) return;
    var style = document.createElement('style');
    style.id = 'novo-cadastro-required-style';
    style.textContent = '' +
      '.required-mark{color:#b91c1c;font-weight:700;margin-left:4px;}' +
      '.required-missing{outline:2px solid rgba(185,28,28,.45)!important;border-color:#b91c1c!important;border-radius:6px;}' +
      '.required-widget-missing{border:2px solid rgba(185,28,28,.45)!important;border-radius:8px;padding:8px;}' +
      '.duplicate-missing{outline:2px solid rgba(185,28,28,.45)!important;border-color:#b91c1c!important;border-radius:6px;}';
    document.head.appendChild(style);
  }

  function appendRequiredMarkToLabel(label) {
    if (!label) return;
    if (label.querySelector('.required-mark')) return;
    var mark = document.createElement('span');
    mark.className = 'required-mark';
    mark.textContent = '*';
    mark.setAttribute('aria-hidden', 'true');
    label.appendChild(mark);
  }

  function nearestLabel(field) {
    if (!field) return null;
    var wrapped = field.closest('label');
    if (wrapped) return wrapped;
    if (field.id) {
      var byFor = document.querySelector('label[for="' + field.id + '"]');
      if (byFor) return byFor;
    }
    var prev = field.previousElementSibling;
    if (prev && prev.classList && prev.classList.contains('label')) return prev;
    return null;
  }

  function clearMissingState(form) {
    form.querySelectorAll('.required-missing').forEach(function (el) {
      el.classList.remove('required-missing');
    });
    form.querySelectorAll('.required-widget-missing').forEach(function (el) {
      el.classList.remove('required-widget-missing');
    });
    form.querySelectorAll('.duplicate-missing').forEach(function (el) {
      el.classList.remove('duplicate-missing');
    });
  }

  function validateRequiredOnSubmit(form) {
    var hasError = false;
    clearMissingState(form);

    var requiredFields = form.querySelectorAll('input[required], select[required], textarea[required]');
    requiredFields.forEach(function (field) {
      if (field.type === 'radio') {
        var group = form.querySelectorAll('input[type="radio"][name="' + field.name + '"]');
        var anyChecked = Array.prototype.some.call(group, function (item) { return item.checked; });
        if (!anyChecked) {
          group.forEach(function (item) { item.classList.add('required-missing'); });
          hasError = true;
        }
        return;
      }
      if (!String(field.value || '').trim()) {
        field.classList.add('required-missing');
        var label = nearestLabel(field);
        if (label && label.classList) label.classList.add('required-missing');
        hasError = true;
      }
    });

    var customRequired = form.querySelectorAll('input[type="hidden"][data-required="true"]');
    customRequired.forEach(function (hidden) {
      if (String(hidden.value || '').trim()) return;
      hasError = true;
      var targetSelector = hidden.getAttribute('data-required-target');
      if (targetSelector) {
        var target = form.querySelector(targetSelector);
        if (target) target.classList.add('required-widget-missing');
      }
    });

    if (hasError) {
      var status = form.querySelector('.status');
      if (status) {
        status.innerHTML = '<p data-state="error">Preencha todos os campos obrigatórios (*) antes de continuar.</p>';
      }
    }
    return !hasError && !form.dataset.hasDuplicateError;
  }

  function normalizeCpf(value) {
    return String(value || '').replace(/\D+/g, '');
  }

  function normalizeDocText(value) {
    return String(value || '').toUpperCase().replace(/[^A-Z0-9]+/g, '');
  }

  function markDuplicateStatus(form, field, message) {
    form.dataset.hasDuplicateError = '1';
    field.classList.add('duplicate-missing');
    var status = form.querySelector('.status');
    if (status) {
      status.innerHTML = '<p data-state="error">' + message + '</p>';
    }
  }

  function clearDuplicateStatus(form, field) {
    field.classList.remove('duplicate-missing');
    var hasAny = form.querySelector('.duplicate-missing');
    if (!hasAny) {
      delete form.dataset.hasDuplicateError;
    }
  }

  function initDocumentDuplicateCheck() {
    var form = document.querySelector('form[data-doc-check-url]');
    if (!form) return;
    var url = form.getAttribute('data-doc-check-url');
    if (!url) return;

    var fields = [
      { name: 'cpf_aventureiro', type: 'cpf', min: 11 },
      { name: 'cpf_pai', type: 'cpf', min: 11 },
      { name: 'cpf_mae', type: 'cpf', min: 11 },
      { name: 'cpf_responsavel', type: 'cpf', min: 11 },
      { name: 'rg', type: 'doc', min: 4 },
      { name: 'certidao_nascimento', type: 'doc', min: 6 }
    ];

    fields.forEach(function (cfg) {
      var field = form.querySelector('[name="' + cfg.name + '"]');
      if (!field) return;
      var timer = null;

      function normalizeLocal() {
        if (cfg.type === 'cpf') {
          field.value = normalizeCpf(field.value);
        } else {
          field.value = normalizeDocText(field.value);
        }
      }

      function checkDuplicate() {
        normalizeLocal();
        var value = String(field.value || '').trim();
        if (!value || value.length < cfg.min) {
          clearDuplicateStatus(form, field);
          return;
        }
        var params = new URLSearchParams({ field: cfg.name, value: value });
        fetch(url + '?' + params.toString(), {
          method: 'GET',
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
          .then(function (res) { return res.json(); })
          .then(function (data) {
            if (!data || data.ok !== true) return;
            if (data.normalized) {
              field.value = data.normalized;
            }
            if (data.duplicate) {
              markDuplicateStatus(form, field, data.message || 'Documento já cadastrado.');
            } else {
              clearDuplicateStatus(form, field);
            }
          })
          .catch(function () {});
      }

      field.addEventListener('input', function () {
        normalizeLocal();
        if (timer) clearTimeout(timer);
        timer = setTimeout(checkDuplicate, 350);
      });
      field.addEventListener('blur', checkDuplicate);
    });

    form.addEventListener('submit', function (event) {
      if (form.dataset.hasDuplicateError) {
        event.preventDefault();
        var status = form.querySelector('.status');
        if (status) {
          status.innerHTML = '<p data-state="error">Existem documentos duplicados. Corrija para continuar.</p>';
        }
      }
    });
  }

  function initRequiredMarkersAndValidation() {
    injectRequiredStyles();
    var forms = document.querySelectorAll('form');
    forms.forEach(function (form) {
      var requiredMode = (form.getAttribute('data-required-mode') || 'global').toLowerCase();
      var radioGroups = {};
      var checkboxGroups = {};
      if (requiredMode !== 'explicit') {
        var fieldsForGlobalRequired = form.querySelectorAll('input, select, textarea');
        fieldsForGlobalRequired.forEach(function (field) {
          var tag = (field.tagName || '').toLowerCase();
          var type = (field.type || '').toLowerCase();
          var name = (field.name || '').toLowerCase();
          if (tag === 'button') return;
          if (type === 'hidden' || type === 'submit' || type === 'button' || type === 'reset') return;
          if (type === 'file') return;
          if (field.hasAttribute('data-optional') || name === 'classes') {
            field.required = false;
            return;
          }
          if (type === 'radio') {
            if (!field.name) return;
            if (!radioGroups[field.name]) {
              field.required = true;
              radioGroups[field.name] = true;
            }
            return;
          }
          if (type === 'checkbox') {
            if (!field.name) return;
            if (!checkboxGroups[field.name]) {
              field.required = true;
              checkboxGroups[field.name] = true;
            }
            return;
          }
          field.required = true;
        });
      }

      var requiredFields = form.querySelectorAll('input[required], select[required], textarea[required]');
      requiredFields.forEach(function (field) {
        var label = nearestLabel(field);
        appendRequiredMarkToLabel(label);
      });

      var customRequired = form.querySelectorAll('input[type="hidden"][data-required="true"]');
      customRequired.forEach(function (hidden) {
        var targetSelector = hidden.getAttribute('data-required-target');
        if (!targetSelector) return;
        var target = form.querySelector(targetSelector);
        if (!target) return;
        appendRequiredMarkToLabel(target);
      });

      form.addEventListener('submit', function (event) {
        if (!validateRequiredOnSubmit(form)) {
          event.preventDefault();
        }
      });
    });
  }

  function initPhotoToDataUrl() {
    var input = document.getElementById('foto-file');
    var hidden = document.getElementById('foto-3x4');
    var preview = document.getElementById('foto-preview');
    var placeholder = document.getElementById('photo-placeholder');
    if (!input || !hidden) return;
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function (event) {
        hidden.value = event.target.result || '';
        if (preview) {
          preview.src = hidden.value;
          preview.style.display = 'block';
        }
        if (placeholder) {
          placeholder.style.display = 'none';
        }
      };
      reader.readAsDataURL(file);
    });
    if (hidden.value && preview) {
      preview.src = hidden.value;
      preview.style.display = 'block';
    }
    if (hidden.value && placeholder) {
      placeholder.style.display = 'none';
    }
  }

  function initParentAbsentToggles() {
    var form = document.querySelector('form');
    if (!form) return;

    function applyToggle(parentKey) {
      var toggle = form.querySelector('[data-parent-absent-toggle="' + parentKey + '"]');
      var block = form.querySelector('[data-parent-block="' + parentKey + '"]');
      if (!toggle || !block) return;
      var disabled = !!toggle.checked;
      block.classList.toggle('parent-block-disabled', disabled);
      var fields = block.querySelectorAll('[data-parent-field="' + parentKey + '"]');
      fields.forEach(function (field) {
        field.disabled = disabled;
        if (disabled) {
          field.classList.remove('required-missing');
          field.classList.remove('duplicate-missing');
        }
      });
      if (disabled && form.dataset.hasDuplicateError) {
        var anyDuplicate = form.querySelector('.duplicate-missing');
        if (!anyDuplicate) delete form.dataset.hasDuplicateError;
      }
    }

    ['pai', 'mae'].forEach(function (parentKey) {
      var toggle = form.querySelector('[data-parent-absent-toggle="' + parentKey + '"]');
      if (!toggle) return;
      toggle.addEventListener('change', function () { applyToggle(parentKey); });
      applyToggle(parentKey);
    });
  }

  function initSignatureWidgets() {
    var widgets = document.querySelectorAll('.signature-widget');
    widgets.forEach(function (widget) {
      var canvas = widget.querySelector('canvas');
      var clearBtn = widget.querySelector('[data-action="clear-sign"]');
      var saveBtn = widget.querySelector('[data-action="save-sign"]');
      var hidden = widget.querySelector('input[type="hidden"]');
      var status = widget.querySelector('.signature-status');
      if (!canvas || !hidden) return;

      var ctx = canvas.getContext('2d');
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#1f2937';
      ctx.lineCap = 'round';
      var drawing = false;
      // Prevent mobile browsers from interpreting drawing gestures as page scroll.
      canvas.style.touchAction = 'none';
      canvas.style.webkitUserSelect = 'none';

      function getCanvasPoint(event) {
        var rect = canvas.getBoundingClientRect();
        var scaleX = canvas.width / rect.width;
        var scaleY = canvas.height / rect.height;
        return {
          x: (event.clientX - rect.left) * scaleX,
          y: (event.clientY - rect.top) * scaleY,
        };
      }

      function clearCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        hidden.value = '';
        if (status) status.textContent = 'Assinatura limpa.';
      }

      canvas.addEventListener('pointerdown', function (event) {
        event.preventDefault();
        drawing = true;
        canvas.setPointerCapture(event.pointerId);
        var point = getCanvasPoint(event);
        ctx.beginPath();
        ctx.moveTo(point.x, point.y);
      });

      canvas.addEventListener('pointermove', function (event) {
        if (!drawing) return;
        event.preventDefault();
        var point = getCanvasPoint(event);
        ctx.lineTo(point.x, point.y);
        ctx.stroke();
      });

      function stopDraw(event) {
        if (event) {
          try { canvas.releasePointerCapture(event.pointerId); } catch (e) {}
        }
        drawing = false;
      }

      canvas.addEventListener('pointerup', stopDraw);
      canvas.addEventListener('pointerleave', stopDraw);
      canvas.addEventListener('touchstart', function (event) { event.preventDefault(); }, { passive: false });
      canvas.addEventListener('touchmove', function (event) { event.preventDefault(); }, { passive: false });
      canvas.addEventListener('touchend', function (event) { event.preventDefault(); }, { passive: false });

      if (clearBtn) clearBtn.addEventListener('click', clearCanvas);

      if (saveBtn) {
        saveBtn.addEventListener('click', function () {
          hidden.value = canvas.toDataURL('image/png');
          if (status) status.textContent = 'Assinatura salva.';
        });
      }

      if (hidden.value) {
        var img = new Image();
        img.onload = function () {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        };
        img.src = hidden.value;
      }
    });
  }

  initPhotoToDataUrl();
  initParentAbsentToggles();
  initSignatureWidgets();
  initRequiredMarkersAndValidation();
  initDocumentDuplicateCheck();
})();

(function () {
  var canvas = document.getElementById('doc-canvas');
  if (!canvas) return;

  var background = document.getElementById('doc-background');
  var fieldPalette = document.getElementById('doc-fields');
  var saveInput = document.getElementById('doc-positions');
  var fontSizeInput = document.getElementById('doc-font-size');
  var widthInput = document.getElementById('doc-width');
  var heightInput = document.getElementById('doc-height');
  var floatingControls = document.getElementById('doc-floating-controls');
  var closeControls = document.getElementById('doc-controls-close');

  var selectedField = null;
  var placedFields = [];
  var activeDrag = null;
  var dragOffset = { x: 0, y: 0 };

  function getScale() {
    if (!background) return { scaleX: 1, scaleY: 1 };
    var rect = background.getBoundingClientRect();
    var scaleX = background.naturalWidth ? background.naturalWidth / rect.width : 1;
    var scaleY = background.naturalHeight ? background.naturalHeight / rect.height : 1;
    return { scaleX: scaleX, scaleY: scaleY };
  }

  function setSelected(el) {
    if (selectedField) selectedField.classList.remove('doc-field-selected');
    selectedField = el;
    if (selectedField) selectedField.classList.add('doc-field-selected');
    syncControls();
    positionControls();
  }

  function syncControls() {
    if (!selectedField) return;
    if (fontSizeInput) {
      fontSizeInput.value = selectedField.dataset.fontSize || '18';
    }
    if (widthInput) {
      widthInput.value = Math.round(selectedField.offsetWidth || 0);
    }
    if (heightInput) {
      heightInput.value = Math.round(selectedField.offsetHeight || 0);
    }
  }

  function applyControls() {
    if (!selectedField) return;
    if (fontSizeInput) {
      var fontSize = parseInt(fontSizeInput.value || '18', 10);
      selectedField.dataset.fontSize = String(fontSize);
      selectedField.style.fontSize = fontSize + 'px';
    }
    if (widthInput) {
      var width = parseInt(widthInput.value || '0', 10);
      if (width > 0) selectedField.style.width = width + 'px';
    }
    if (heightInput) {
      var height = parseInt(heightInput.value || '0', 10);
      if (height > 0) selectedField.style.height = height + 'px';
    }
  }

  function positionControls() {
    if (!floatingControls) return;
    if (!selectedField) {
      floatingControls.classList.remove('show');
      return;
    }
    var rect = selectedField.getBoundingClientRect();
    var canvasRect = canvas.getBoundingClientRect();
    var left = rect.right - canvasRect.left + 12;
    var top = rect.top - canvasRect.top;
    if (left + 260 > canvasRect.width) {
      left = rect.left - canvasRect.left - 260;
    }
    if (top < 0) top = 0;
    floatingControls.style.left = left + 'px';
    floatingControls.style.top = top + 'px';
    floatingControls.classList.add('show');
  }

  function createFieldElement(item) {
    var el = document.createElement('div');
    el.className = 'doc-field';
    el.textContent = item.label;
    el.dataset.key = item.key;
    el.dataset.type = item.type;
    el.dataset.fontSize = item.font_size || 18;
    el.style.left = item.x + 'px';
    el.style.top = item.y + 'px';
    el.style.fontSize = (item.font_size || 18) + 'px';
    el.style.width = item.w ? item.w + 'px' : '';
    el.style.height = item.h ? item.h + 'px' : '';
    if (item.type === 'image') {
      el.classList.add('doc-field-image');
    }
    canvas.appendChild(el);
    placedFields.push(el);
    enableDrag(el);
    el.addEventListener('click', function () {
      setSelected(el);
    });
  }

  function enableDrag(el) {
    el.addEventListener('pointerdown', function (event) {
      activeDrag = el;
      setSelected(el);
      var rect = el.getBoundingClientRect();
      dragOffset.x = event.clientX - rect.left;
      dragOffset.y = event.clientY - rect.top;
      el.setPointerCapture(event.pointerId);
    });
    el.addEventListener('pointerup', function () {
      activeDrag = null;
    });
    el.addEventListener('pointermove', function (event) {
      if (!activeDrag) return;
      var canvasRect = canvas.getBoundingClientRect();
      var left = event.clientX - canvasRect.left - dragOffset.x;
      var top = event.clientY - canvasRect.top - dragOffset.y;
      left = Math.max(0, Math.min(left, canvasRect.width - activeDrag.offsetWidth));
      top = Math.max(0, Math.min(top, canvasRect.height - activeDrag.offsetHeight));
      activeDrag.style.left = left + 'px';
      activeDrag.style.top = top + 'px';
    });
  }

  function handleDrop(event) {
    event.preventDefault();
    var key = event.dataTransfer.getData('text/key');
    var label = event.dataTransfer.getData('text/label');
    var type = event.dataTransfer.getData('text/type');
    if (!key) return;

    var canvasRect = canvas.getBoundingClientRect();
    var x = event.clientX - canvasRect.left;
    var y = event.clientY - canvasRect.top;

    createFieldElement({
      key: key,
      label: label,
      type: type,
      x: x,
      y: y,
      w: type === 'image' ? 140 : 160,
      h: type === 'image' ? 100 : 30,
      font_size: 18,
    });
    setSelected(placedFields[placedFields.length - 1]);
  }

  function setupPalette() {
    if (!fieldPalette) return;
    var items = fieldPalette.querySelectorAll('.doc-field-pill');
    items.forEach(function (item) {
      item.addEventListener('dragstart', function (event) {
        event.dataTransfer.setData('text/key', item.dataset.key);
        event.dataTransfer.setData('text/label', item.textContent);
        event.dataTransfer.setData('text/type', item.dataset.type || 'text');
      });
    });
  }

  function loadSavedPositions() {
    var script = document.getElementById('doc-positions-data');
    if (!script) return;
    try {
      var positions = JSON.parse(script.textContent || '[]');
      positions.forEach(function (item) {
        createFieldElement(item);
      });
    } catch (err) {
      // ignore
    }
  }

  function serializePositions() {
    var scale = getScale();
    var data = placedFields.map(function (el) {
      var rect = el.getBoundingClientRect();
      var canvasRect = canvas.getBoundingClientRect();
      var x = (rect.left - canvasRect.left) * scale.scaleX;
      var y = (rect.top - canvasRect.top) * scale.scaleY;
      var w = rect.width * scale.scaleX;
      var h = rect.height * scale.scaleY;
      var fontScale = scale.scaleX;
      return {
        key: el.dataset.key,
        label: el.textContent,
        type: el.dataset.type || 'text',
        x: Math.round(x),
        y: Math.round(y),
        w: Math.round(w),
        h: Math.round(h),
        font_size: Math.max(8, Math.round((Number(el.dataset.fontSize || 18)) * fontScale)),
      };
    });
    return data;
  }

  function setupGenerateLinks() {
    var config = window.documentosConfig || {};
    var base = config.generateBase || '';
    if (!base) return;
    function build(baseUrl, templateId, kind, id) {
      return baseUrl
        .replace('/0/', '/' + templateId + '/')
        .replace('/responsavel/', '/' + kind + '/')
        .replace('/0/', '/' + id + '/');
    }
    var templateId = config.templateId;
    var respSelect = document.getElementById('doc-responsavel-select');
    var respLink = document.getElementById('doc-responsavel-generate');
    var avSelect = document.getElementById('doc-aventureiro-select');
    var avLink = document.getElementById('doc-aventureiro-generate');
    var dirSelect = document.getElementById('doc-diretoria-select');
    var dirLink = document.getElementById('doc-diretoria-generate');

    function bind(select, link, kind) {
      if (!select || !link) return;
      select.addEventListener('change', function () {
        var value = select.value;
        if (!value) {
          link.href = '#';
          link.classList.add('disabled');
          return;
        }
        link.href = build(base, templateId, kind, value);
        link.classList.remove('disabled');
      });
      if (!select.value) {
        link.href = '#';
        link.classList.add('disabled');
      }
    }

    bind(respSelect, respLink, 'responsavel');
    bind(avSelect, avLink, 'aventureiro');
    bind(dirSelect, dirLink, 'diretoria');
  }

  if (canvas) {
    canvas.addEventListener('dragover', function (event) {
      event.preventDefault();
    });
    canvas.addEventListener('drop', handleDrop);
  }

  var saveForm = document.getElementById('doc-save-form');
  if (saveForm) {
    saveForm.addEventListener('submit', function () {
      if (!saveInput) return;
      saveInput.value = JSON.stringify(serializePositions());
    });
  }

  if (fontSizeInput) fontSizeInput.addEventListener('input', applyControls);
  if (widthInput) widthInput.addEventListener('input', applyControls);
  if (heightInput) heightInput.addEventListener('input', applyControls);
  if (closeControls) {
    closeControls.addEventListener('click', function () {
      if (!floatingControls) return;
      floatingControls.classList.remove('show');
      if (selectedField) selectedField.classList.remove('doc-field-selected');
      selectedField = null;
    });
  }

  setupPalette();
  loadSavedPositions();
  setupGenerateLinks();
  window.addEventListener('resize', positionControls);
})();

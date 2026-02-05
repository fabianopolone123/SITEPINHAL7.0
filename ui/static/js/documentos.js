(function () {
  var canvas = document.getElementById('doc-canvas');
  if (!canvas) return;

  var background = document.getElementById('doc-background');
  var fieldPalette = document.getElementById('doc-fields');
  var saveInput = document.getElementById('doc-positions');

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

  function createFieldElement(item) {
    var el = document.createElement('div');
    el.className = 'doc-field';
    el.textContent = item.label;
    el.dataset.key = item.key;
    el.dataset.type = item.type;
    el.style.left = item.x + 'px';
    el.style.top = item.y + 'px';
    el.style.width = item.w ? item.w + 'px' : '';
    el.style.height = item.h ? item.h + 'px' : '';
    if (item.type === 'image') {
      el.classList.add('doc-field-image');
    }
    canvas.appendChild(el);
    placedFields.push(el);
    enableDrag(el);
  }

  function enableDrag(el) {
    el.addEventListener('pointerdown', function (event) {
      activeDrag = el;
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
      w: type === 'image' ? 140 : null,
      h: type === 'image' ? 100 : null,
    });
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
      return {
        key: el.dataset.key,
        label: el.textContent,
        type: el.dataset.type || 'text',
        x: Math.round(x),
        y: Math.round(y),
        w: Math.round(w),
        h: Math.round(h),
        font_size: el.dataset.fontSize ? Number(el.dataset.fontSize) : 18,
      };
    });
    return data;
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

  setupPalette();
  loadSavedPositions();
})();

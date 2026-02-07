(function () {
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
        drawing = true;
        canvas.setPointerCapture(event.pointerId);
        var point = getCanvasPoint(event);
        ctx.beginPath();
        ctx.moveTo(point.x, point.y);
      });

      canvas.addEventListener('pointermove', function (event) {
        if (!drawing) return;
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
  initSignatureWidgets();
})();

(() => {
  const createSignatureFlow = (config) => {
    const {
      modalId,
      canvasId,
      openButtonId,
      closeButtonId,
      clearButtonId,
      saveButtonId,
      previewId,
      placeholderId,
      canvasErrorId,
      signatureFieldId,
    } = config;

    const modal = document.getElementById(modalId);
    const canvas = document.getElementById(canvasId);
    const openButton = document.getElementById(openButtonId);
    const closeButton = document.getElementById(closeButtonId);
    const clearButton = document.getElementById(clearButtonId);
    const saveButton = document.getElementById(saveButtonId);
    const preview = document.getElementById(previewId);
    const previewPlaceholder = document.getElementById(placeholderId);
    const canvasError = document.getElementById(canvasErrorId);
    const signatureField = signatureFieldId ? document.getElementById(signatureFieldId) : null;

    if (!modal || !canvas || !openButton || !closeButton || !clearButton || !saveButton || !preview || !previewPlaceholder || !canvasError) {
      return;
    }

    const ctx = canvas.getContext('2d');
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#1f2937';
    ctx.lineCap = 'round';

    let drawing = false;

    const start = (event) => {
      drawing = true;
      const { offsetX, offsetY } = event;
      ctx.beginPath();
      ctx.moveTo(offsetX, offsetY);
    };

    const draw = (event) => {
      if (!drawing) return;
      const { offsetX, offsetY } = event;
      ctx.lineTo(offsetX, offsetY);
      ctx.stroke();
    };

    const stop = () => {
      drawing = false;
    };

    canvas.addEventListener('pointerdown', (event) => {
      canvas.setPointerCapture(event.pointerId);
      start(event);
    });
    canvas.addEventListener('pointermove', draw);
    canvas.addEventListener('pointerup', (event) => {
      stop();
      canvas.releasePointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointerleave', stop);

    const showModal = () => {
      modal.classList.add('show');
      modal.setAttribute('aria-hidden', 'false');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      canvasError.textContent = '';
    };

    const closeModal = () => {
      modal.classList.remove('show');
      modal.setAttribute('aria-hidden', 'true');
    };

    const analyzeCanvas = () => {
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const threshold = 8;
      let minX = canvas.width;
      let minY = canvas.height;
      let maxX = 0;
      let maxY = 0;
      let drawn = false;

      for (let y = 0; y < canvas.height; y++) {
        for (let x = 0; x < canvas.width; x++) {
          const idx = (y * canvas.width + x) * 4 + 3;
          if (imageData.data[idx] !== 0) {
            drawn = true;
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
          }
        }
      }

      if (!drawn) {
        return { drawn: false };
      }

      return {
        drawn: true,
        hitsBorder:
          minX < threshold ||
          minY < threshold ||
          maxX > canvas.width - threshold ||
          maxY > canvas.height - threshold,
      };
    };

    openButton.addEventListener('click', showModal);
    closeButton.addEventListener('click', closeModal);

    clearButton.addEventListener('click', () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      canvasError.textContent = '';
      if (signatureField) {
        signatureField.value = '';
      }
    });

    saveButton.addEventListener('click', () => {
      const analysis = analyzeCanvas();
      if (!analysis.drawn) {
        canvasError.textContent = 'Desenhe a assinatura antes de salvar.';
        return;
      }
      if (analysis.hitsBorder) {
        canvasError.textContent = 'Assinatura muito próxima da borda; limpe e refaça com margem.';
        return;
      }
      canvasError.textContent = '';
      const dataUrl = canvas.toDataURL('image/png');
      preview.src = dataUrl;
      preview.style.display = 'block';
      previewPlaceholder.style.display = 'none';
      if (signatureField) {
        signatureField.value = dataUrl;
      }
      closeModal();
    });

    previewPlaceholder.style.display = 'block';
    preview.style.display = 'none';
    if (signatureField) {
      signatureField.value = '';
    }
  };

  createSignatureFlow({
    modalId: 'signature-modal',
    canvasId: 'signature-canvas',
    openButtonId: 'open-signature',
    closeButtonId: 'close-signature',
    clearButtonId: 'clear-signature',
    saveButtonId: 'save-signature',
    previewId: 'signature-image',
    placeholderId: 'signature-placeholder',
    canvasErrorId: 'canvas-error',
    signatureFieldId: 'signature-value',
  });

  createSignatureFlow({
    modalId: 'signature-modal-av',
    canvasId: 'signature-canvas-av',
    openButtonId: 'open-signature-av',
    closeButtonId: 'close-signature-av',
    clearButtonId: 'clear-signature-av',
    saveButtonId: 'save-signature-av',
    previewId: 'signature-image-av',
    placeholderId: 'signature-placeholder-av',
    canvasErrorId: 'canvas-error-av',
    signatureFieldId: 'signature-value-av',
  });
})();

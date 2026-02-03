(() => {
  const modal = document.getElementById('signature-modal');
  const canvas = document.getElementById('signature-canvas');
  const openButton = document.getElementById('open-signature');
  const closeButton = document.getElementById('close-signature');
  const clearButton = document.getElementById('clear-signature');
  const saveButton = document.getElementById('save-signature');
  const preview = document.getElementById('signature-image');
  if (!modal || !canvas || !openButton || !closeButton || !clearButton || !saveButton || !preview) {
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

  openButton.addEventListener('click', () => {
    modal.classList.add('show');
    modal.setAttribute('aria-hidden', 'false');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  });

  const closeModal = () => {
    modal.classList.remove('show');
    modal.setAttribute('aria-hidden', 'true');
  };

  closeButton.addEventListener('click', closeModal);

  clearButton.addEventListener('click', () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  });

  saveButton.addEventListener('click', () => {
    const dataUrl = canvas.toDataURL('image/png');
    preview.src = dataUrl;
    closeModal();
  });
})();

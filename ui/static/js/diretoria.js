(() => {
  const form = document.querySelector('.diretoria-form');
  if (!form) return;

  const status = document.querySelector('.status');
  const photoInput = document.getElementById('photo-input-dir');
  const photoValueField = document.getElementById('photo-value-dir');
  const photoPreview = document.getElementById('photo-preview-img-dir');
  const signatureField = document.getElementById('signature-value-dir');

  const setStatus = (message, state = 'error') => {
    if (!status) return;
    status.textContent = message;
    status.dataset.state = state;
  };

  const clearFrontErrors = () => {
    form.querySelectorAll('[data-front-error="true"]').forEach((el) => {
      el.classList.remove('input-error');
      el.removeAttribute('data-front-error');
    });
  };

  const markError = (selector) => {
    const el = form.querySelector(selector);
    if (!el) return;
    el.classList.add('input-error');
    el.dataset.frontError = 'true';
  };

  const radioChecked = (name) => Boolean(form.querySelector(`input[name="${name}"]:checked`));

  const requiredSelectors = [
    'input[name="username"]',
    'input[name="password"]',
    'input[name="password_confirm"]',
    'input[name="nome"]',
    'input[name="igreja"]',
    'input[name="endereco"]',
    'input[name="distrito"]',
    'input[name="numero"]',
    'input[name="bairro"]',
    'input[name="cep"]',
    'input[name="cidade"]',
    'input[name="estado"]',
    'input[name="email"]',
    'input[name="whatsapp"]',
    'input[name="nascimento"]',
    'input[name="estado_civil"]',
    'input[name="cpf"]',
    'input[name="rg"]',
  ];

  const validate = () => {
    clearFrontErrors();
    let ok = true;

    requiredSelectors.forEach((selector) => {
      const field = form.querySelector(selector);
      if (!field || String(field.value || '').trim()) return;
      field.classList.add('input-error');
      field.dataset.frontError = 'true';
      ok = false;
    });

    if (!radioChecked('possui_limitacao_saude')) {
      markError('input[name="possui_limitacao_saude"]');
      ok = false;
    }
    if (!radioChecked('escolaridade')) {
      markError('input[name="escolaridade"]');
      ok = false;
    }

    const limitacao = form.querySelector('input[name="possui_limitacao_saude"]:checked')?.value;
    if (limitacao === 'sim') {
      const descricao = form.querySelector('textarea[name="limitacao_saude_descricao"]');
      if (!descricao || !descricao.value.trim()) {
        markError('textarea[name="limitacao_saude_descricao"]');
        ok = false;
      }
    }

    const autorizacao = form.querySelector('input[name="autorizacao_imagem"]');
    const declaracao = form.querySelector('input[name="declaracao_medica"]');
    if (!autorizacao?.checked) {
      markError('input[name="autorizacao_imagem"]');
      ok = false;
    }
    if (!declaracao?.checked) {
      markError('input[name="declaracao_medica"]');
      ok = false;
    }

    if (!signatureField?.value?.trim()) {
      markError('#open-signature-dir');
      ok = false;
    }

    if (!photoValueField?.value?.trim()) {
      markError('#photo-input-dir');
      ok = false;
    }

    if (!ok) {
      setStatus('Há campos obrigatórios pendentes; corrija e envie novamente.', 'error');
    } else {
      setStatus('Pronto para concluir o cadastro.', 'info');
    }

    return ok;
  };

  if (photoInput) {
    photoInput.addEventListener('change', () => {
      const file = photoInput.files?.[0];
      if (!file) {
        if (photoValueField) photoValueField.value = '';
        if (photoPreview) {
          photoPreview.src = '';
          photoPreview.style.display = 'none';
        }
        return;
      }
      const reader = new FileReader();
      reader.addEventListener('load', (event) => {
        const dataUrl = event.target?.result;
        if (typeof dataUrl !== 'string') return;
        if (photoValueField) photoValueField.value = dataUrl;
        if (photoPreview) {
          photoPreview.src = dataUrl;
          photoPreview.style.display = 'block';
        }
      });
      reader.readAsDataURL(file);
    });
  }

  if (photoValueField?.value && photoPreview) {
    photoPreview.src = photoValueField.value;
    photoPreview.style.display = 'block';
  } else if (photoPreview) {
    photoPreview.style.display = 'none';
  }

  form.addEventListener('submit', (event) => {
    if (!validate()) event.preventDefault();
  });
})();

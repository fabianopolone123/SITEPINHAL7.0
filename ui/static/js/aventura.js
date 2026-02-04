const adventureForm = document.querySelector('.aventura-form');
const status = document.querySelector('.status');
const statusAlert = document.getElementById('campo-pendente-alert');
const adventureSignature = document.getElementById('signature-value-av');
const adventureCounter = document.getElementById('aventura-counter');
const adventureCounterValue = document.getElementById('aventura-counter-value');
const adventureSequenceInput = document.getElementById('aventura-sequence');
const addAnotherButton = document.getElementById('add-another-av');
const signaturePreview = document.getElementById('signature-image-av');
const signaturePlaceholder = document.getElementById('signature-placeholder-av');
const signatureError = document.getElementById('signature-error-av');
const photoInput = document.getElementById('photo-input');
const photoValueField = document.getElementById('photo-value');
const photoPreviewImg = document.getElementById('photo-preview-img');

const ALERT_MESSAGE = 'Há campos obrigatórios pendentes; complete-os antes de continuar.';

const formatSequence = (value) => String(value).padStart(2, '0');
let currentSequence = Number(adventureCounter?.dataset.currentNumber || adventureSequenceInput?.value || 1);
if (Number.isNaN(currentSequence) || currentSequence < 1) {
  currentSequence = 1;
}

const updateSequenceDisplay = () => {
  const formatted = formatSequence(currentSequence);
  if (adventureCounter) {
    adventureCounter.dataset.currentNumber = currentSequence;
  }
  if (adventureCounterValue) {
    adventureCounterValue.textContent = formatted;
  }
  if (adventureSequenceInput) {
    adventureSequenceInput.value = currentSequence;
  }
};

const showCampoAlert = () => {
  if (!statusAlert) return;
  statusAlert.classList.remove('hidden');
  statusAlert.textContent = ALERT_MESSAGE;
};

const hideCampoAlert = () => {
  if (!statusAlert) return;
  statusAlert.classList.add('hidden');
};

const addFieldError = (element) => {
  if (!element) return;
  element.classList.add('input-error');
  element.dataset.frontError = 'true';
};

const updatePhotoPreview = (url) => {
  if (!photoPreviewImg) return;
  if (url) {
    photoPreviewImg.src = url;
    photoPreviewImg.style.display = 'block';
  } else {
    photoPreviewImg.src = '';
    photoPreviewImg.style.display = 'none';
  }
};

const clearFrontFieldErrors = () => {
  document.querySelectorAll('[data-front-error="true"]').forEach((el) => {
    el.classList.remove('input-error');
    el.removeAttribute('data-front-error');
  });
};

const getRadioValue = (name) => adventureForm.querySelector(`[name="${name}"]:checked`)?.value;

const setStatusError = (message) => {
  if (status) {
    status.textContent = message;
    status.dataset.state = 'error';
  }
  showCampoAlert();
};

const validarAventuraAtual = () => {
  clearFrontFieldErrors();
  let valid = true;
  const formData = new FormData(adventureForm);
  const nome = formData.get('nome')?.trim();
  const religiao = formData.get('religiao')?.trim();
  const nascimento = formData.get('nascimento')?.trim();
  const serie = formData.get('serie')?.trim();
  const colegio = formData.get('colegio')?.trim();
  const bolsa = getRadioValue('bolsa');
  const sexo = getRadioValue('sexo');
  const plano = getRadioValue('plano');
  const tipoSangue = getRadioValue('tipo_sangue');
  const declaracaoMedica = document.querySelector('[name="declaracao_medica"]')?.checked;
  const autorizacaoImagem = document.querySelector('[name="autorizacao_imagem"]')?.checked;

  const ensureText = (name, value, message) => {
    if (!value) {
      const field = adventureForm.querySelector(`[name="${name}"]`);
      addFieldError(field);
      if (valid) setStatusError(message);
      valid = false;
    }
  };

  const photoValue = photoValueField?.value?.trim();
  if (!photoValue) {
    addFieldError(photoInput);
    if (valid) setStatusError('Anexe a foto 3x4 do aventureiro.');
    valid = false;
  }

  ensureText('nome', nome, 'Informe o nome do aventureiro antes de continuar.');
  ensureText('religiao', religiao, 'Informe a religião do aventureiro.');
  ensureText('nascimento', nascimento, 'Informe a data de nascimento.');
  ensureText('serie', serie, 'Informe a série/ano.');
  ensureText('colegio', colegio, 'Informe o colégio.');

  if (!sexo) {
    addFieldError(adventureForm.querySelector('[name="sexo"]')?.closest('.radio-row'));
    if (valid) setStatusError('Informe o sexo do aventureiro.');
    valid = false;
  }

  if (!bolsa) {
    addFieldError(adventureForm.querySelector('[name="bolsa"]')?.closest('.radio-row'));
    if (valid) setStatusError('Informe se recebe Bolsa Família.');
    valid = false;
  }

  const certidao = formData.get('certidao')?.trim();
  const rg = formData.get('rg')?.trim();
  const orgao = formData.get('orgao')?.trim();
  const cpf = formData.get('cpf')?.trim();
  const hasDoc = certidao || cpf || (rg && orgao);
  if (!hasDoc) {
    ['certidao', 'rg', 'orgao', 'cpf'].forEach((name) => addFieldError(adventureForm.querySelector(`[name="${name}"]`)));
    if (valid) setStatusError('Informe ao menos uma documentação válida.');
    valid = false;
  }
  if (rg && !orgao) {
    addFieldError(adventureForm.querySelector('[name="orgao"]'));
    if (valid) setStatusError('Informe o órgão expedidor junto com o RG.');
    valid = false;
  }
  if (orgao && !rg) {
    addFieldError(adventureForm.querySelector('[name="rg"]'));
    if (valid) setStatusError('Informe o número do RG que pertence ao órgão expedidor.');
    valid = false;
  }

  if (!plano) {
    addFieldError(adventureForm.querySelector('[name="plano"]')?.closest('.radio-row'));
    if (valid) setStatusError('Informe se possui plano de saúde.');
    valid = false;
  }
  if (plano === 'sim') {
    const planName = formData.get('plano_nome')?.trim();
    if (!planName) {
      addFieldError(adventureForm.querySelector('[name="plano_nome"]'));
      if (valid) setStatusError('Informe o nome do plano de saúde.');
      valid = false;
    }
  }

  if (!tipoSangue) {
    addFieldError(adventureForm.querySelector('[name="tipo_sangue"]')?.closest('.checkbox-grid'));
    if (valid) setStatusError('Selecione o tipo sanguíneo.');
    valid = false;
  }

  ['cardiaco', 'diabetico', 'renal', 'psicologico'].forEach((prefix) => {
    const condicao = getRadioValue(prefix);
    if (!condicao) {
      addFieldError(adventureForm.querySelector(`[name="${prefix}"]`)?.closest('.radio-group'));
      if (valid) setStatusError('Informe sim ou não para todas as condições de saúde.');
      valid = false;
      return;
    }
    if (condicao === 'sim') {
      const detalhe = formData.get(`${prefix}_detalhe`)?.trim();
      if (!detalhe) {
        addFieldError(adventureForm.querySelector(`[name="${prefix}_detalhe"]`));
        if (valid) setStatusError('Descreva a condição indicada.');
        valid = false;
      }
    }
    const medicamento = getRadioValue(`${prefix}_medicamento`);
    if (!medicamento) {
      addFieldError(adventureForm.querySelector(`[name="${prefix}_medicamento"]`)?.closest('.radio-group'));
      if (valid) setStatusError('Informe se utiliza remédios.');
      valid = false;
      return;
    }
    if (medicamento === 'sim') {
      const remedio = formData.get(`${prefix}_remedio`)?.trim();
      if (!remedio) {
        addFieldError(adventureForm.querySelector(`[name="${prefix}_remedio"]`));
        if (valid) setStatusError('Informe o medicamento utilizado.');
        valid = false;
      }
    }
  });

  [['alergia_pele', 'alergia_pele_descricao'], ['alergia_alimento', 'alergia_alimento_descricao'], ['alergia_medicamento', 'alergia_medicamento_descricao']].forEach(([field, detail]) => {
    const value = getRadioValue(field);
    if (!value) {
      addFieldError(adventureForm.querySelector(`[name="${field}"]`)?.closest('.radio-group'));
      if (valid) setStatusError('Informe sim ou não para todas as alergias.');
      valid = false;
      return;
    }
    if (value === 'sim') {
      const detailValue = formData.get(detail)?.trim();
      if (!detailValue) {
        addFieldError(adventureForm.querySelector(`[name="${detail}"]`));
        if (valid) setStatusError('Descreva a alergia indicada.');
        valid = false;
      }
    }
  });

  if (!declaracaoMedica) {
    addFieldError(adventureForm.querySelector('[name="declaracao_medica"]'));
    if (valid) setStatusError('Aceite a declaração médica.');
    valid = false;
  }
  if (!autorizacaoImagem) {
    addFieldError(adventureForm.querySelector('[name="autorizacao_imagem"]'));
    if (valid) setStatusError('Aceite o termo de autorização de imagem.');
    valid = false;
  }

  if (!valid) {
    return false;
  }

  if (status) {
    status.textContent = 'Pronto para prosseguir.';
    status.dataset.state = 'info';
  }
  hideCampoAlert();
  return true;
};

const limparFormulario = () => {
  adventureForm.reset();
  status.textContent = '';
  status.removeAttribute('data-state');
  if (signaturePreview) {
    signaturePreview.src = '';
    signaturePreview.style.display = 'none';
  }
  if (signaturePlaceholder) {
    signaturePlaceholder.style.display = 'block';
  }
  if (adventureSignature) {
    adventureSignature.value = '';
  }
  if (signatureError) {
    signatureError.textContent = '';
  }
  if (photoInput) {
    photoInput.value = '';
  }
  if (photoValueField) {
    photoValueField.value = '';
  }
  updatePhotoPreview(null);
  hideCampoAlert();
};

updateSequenceDisplay();

adventureForm.addEventListener('submit', (event) => {
  if (!validarAventuraAtual()) {
    event.preventDefault();
    return;
  }
  if (status) {
    status.textContent = 'Enviando dados do aventureiro...';
    status.dataset.state = 'info';
  }
});

if (photoInput) {
  photoInput.addEventListener('change', () => {
    const file = photoInput.files?.[0];
    if (!file) {
      if (photoValueField) {
        photoValueField.value = '';
      }
      updatePhotoPreview(null);
      return;
    }
    const reader = new FileReader();
    reader.addEventListener('load', (event) => {
      const dataUrl = event.target?.result;
      if (photoValueField && typeof dataUrl === 'string') {
        photoValueField.value = dataUrl;
      }
      if (typeof dataUrl === 'string') {
        updatePhotoPreview(dataUrl);
      }
    });
    reader.readAsDataURL(file);
  });
}

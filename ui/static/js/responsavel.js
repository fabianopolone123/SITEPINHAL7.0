const form = document.querySelector('.responsavel-form');
const status = document.querySelector('.status');
const signatureValue = document.getElementById('signature-value');

const normalize = (value) => value?.trim() ?? '';

form.addEventListener('submit', (event) => {
  const formData = new FormData(form);
  const hasAnyParent = normalize(formData.get('pai_nome')) || normalize(formData.get('mae_nome'));
  const responsavel = normalize(formData.get('responsavel_nome'));

  if (!hasAnyParent && !responsavel) {
    event.preventDefault();
    status.textContent = 'Informe ao menos um responsável (pai, mãe ou responsável legal).';
    status.dataset.state = 'error';
    return;
  }

  if (!signatureValue?.value) {
    event.preventDefault();
    status.textContent = 'Assine o formulário antes de prosseguir.';
    status.dataset.state = 'error';
    return;
  }

  status.textContent = 'Enviando dados do responsável...';
  status.dataset.state = 'info';
});

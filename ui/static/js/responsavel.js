const form = document.querySelector('.responsavel-form');
const status = document.querySelector('.status');

const normalize = (value) => value?.trim() ?? '';

form.addEventListener('submit', (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const hasAnyParent = normalize(formData.get('pai_nome')) || normalize(formData.get('mae_nome'));
  const responsavel = normalize(formData.get('responsavel_nome'));

  if (!hasAnyParent && !responsavel) {
    status.textContent = 'Informe ao menos um responsável (pai, mãe ou responsável legal).';
    status.dataset.state = 'error';
    return;
  }

  status.textContent = 'Dados salvos localmente. Próxima etapa: preenchimento do aventureiro.';
  status.dataset.state = 'success';
});

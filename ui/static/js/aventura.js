const adventureForm = document.querySelector('.aventura-form');
const status = document.querySelector('.status');

adventureForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const formData = new FormData(adventureForm);
  const nome = formData.get('nome_aventura')?.trim();

  if (!nome) {
    status.textContent = 'Informe o nome do aventureiro antes de continuar.';
    status.dataset.state = 'error';
    return;
  }

  status.textContent = 'Informações salvas localmente. Faltam apenas autorizações e revisões.';
  status.dataset.state = 'success';
});

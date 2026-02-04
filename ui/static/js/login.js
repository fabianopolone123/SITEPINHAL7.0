const form = document.querySelector('.login-form');
const status = document.querySelector('.status');

const setMessage = (text, type) => {
  status.textContent = text;
  status.dataset.state = type;
};

form.addEventListener('submit', (event) => {
  const formData = new FormData(form);
  const username = formData.get('username')?.trim();
  const password = formData.get('password')?.trim();

  if (!username || !password) {
    event.preventDefault();
    setMessage('Informe usuário e senha antes de entrar.', 'error');
    return;
  }

  setMessage('Enviando as credenciais...', 'info');
});


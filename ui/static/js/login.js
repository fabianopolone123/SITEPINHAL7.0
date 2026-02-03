const form = document.querySelector('.login-form');
const status = document.querySelector('.status');

const dummyCredentials = {
  username: 'aventura',
  password: 'pinhal123'
};

const setMessage = (text, type) => {
  status.textContent = text;
  status.dataset.state = type;
};

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const formData = new FormData(form);
  const username = formData.get('username')?.trim();
  const password = formData.get('password')?.trim();

  if (!username || !password) {
    setMessage('Informe usuário e senha antes de entrar.', 'error');
    return;
  }

  setMessage('Validando...', 'info');
  setTimeout(() => {
    if (username === dummyCredentials.username && password === dummyCredentials.password) {
      setMessage('Acesso liberado! Bem-vindo ao Clube de Aventureiros Pinhal Junior.', 'success');
    } else {
      setMessage('Credenciais incorretas. Tente novamente ou redefina sua senha.', 'error');
    }
  }, 800);
});


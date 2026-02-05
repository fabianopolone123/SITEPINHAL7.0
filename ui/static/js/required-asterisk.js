(() => {
  const selectors = [
    '.responsavel-form',
    '.diretoria-form',
    '.aventura-form',
  ];

  const forms = selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector)));
  if (!forms.length) return;

  forms.forEach((form) => {
    const labels = form.querySelectorAll('label');
    labels.forEach((label) => {
      const requiredField = label.querySelector('input[required], select[required], textarea[required]');
      if (!requiredField) return;
      if (requiredField.type === 'radio' || requiredField.type === 'checkbox') return;
      if (label.querySelector('.required-mark')) return;

      const mark = document.createElement('span');
      mark.className = 'required-mark';
      mark.textContent = ' *';
      mark.setAttribute('aria-hidden', 'true');
      label.append(mark);
    });
  });
})();

(() => {
  const selectors = [
    '.responsavel-form',
    '.diretoria-form',
    '.aventura-form',
  ];

  const forms = selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector)));
  if (!forms.length) return;

  const findLabelForField = (form, field) => {
    const wrappedLabel = field.closest('label');
    if (wrappedLabel) return wrappedLabel;

    if (!field.id) return null;
    return form.querySelector(`label[for="${field.id}"]`);
  };

  const ensureRequiredMark = (label) => {
    if (!label || label.querySelector('.required-mark')) return;
    const mark = document.createElement('span');
    mark.className = 'required-mark';
    mark.textContent = ' *';
    mark.setAttribute('aria-hidden', 'true');
    label.append(mark);
  };

  forms.forEach((form) => {
    const requiredFields = form.querySelectorAll('input[required], select[required], textarea[required]');
    requiredFields.forEach((field) => {
      if (field.type === 'radio' || field.type === 'checkbox' || field.type === 'hidden') return;
      const label = findLabelForField(form, field);
      ensureRequiredMark(label);
    });
  });
})();

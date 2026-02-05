(function () {
  var selectors = ['.responsavel-form', '.diretoria-form', '.aventura-form'];
  var forms = [];

  function collectForms() {
    for (var i = 0; i < selectors.length; i += 1) {
      var found = document.querySelectorAll(selectors[i]);
      for (var j = 0; j < found.length; j += 1) {
        forms.push(found[j]);
      }
    }
  }

  function safeNameSelector(name) {
    return name.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
  }

  function findLabelForField(form, field) {
    var wrapped = field.closest ? field.closest('label') : null;
    if (wrapped) return wrapped;
    if (!field.id) return null;
    var byFor = form.querySelector('label[for="' + field.id + '"]');
    if (byFor) return byFor;
    return null;
  }

  function findNearestSiblingLabel(field) {
    var previous = field.previousElementSibling;
    if (previous && previous.tagName === 'LABEL') return previous;
    var parent = field.parentElement;
    if (!parent) return null;
    var children = parent.children;
    for (var i = 0; i < children.length; i += 1) {
      if (children[i] !== field) continue;
      if (i > 0 && children[i - 1].tagName === 'LABEL') return children[i - 1];
      break;
    }
    return null;
  }

  function appendMark(label) {
    if (!label || label.querySelector('.required-mark')) return;
    var mark = document.createElement('span');
    mark.className = 'required-mark';
    mark.textContent = ' *';
    mark.setAttribute('aria-hidden', 'true');
    label.appendChild(mark);
  }

  function markByFieldList(form, names) {
    for (var i = 0; i < names.length; i += 1) {
      var rawName = names[i] ? names[i].trim() : '';
      if (!rawName) continue;
      var fields = form.querySelectorAll('[name="' + safeNameSelector(rawName) + '"]');
      if (!fields.length) continue;

      var target = fields[0];
      if (target.type === 'hidden') continue;

      if (target.type === 'radio' || target.type === 'checkbox') {
        appendMark(findLabelForField(form, target) || findNearestSiblingLabel(target));
      } else {
        appendMark(findLabelForField(form, target) || findNearestSiblingLabel(target));
      }
    }
  }

  function markByRequiredAttr(form) {
    var fields = form.querySelectorAll('input[required], select[required], textarea[required]');
    for (var i = 0; i < fields.length; i += 1) {
      var field = fields[i];
      if (field.type === 'hidden') continue;
      appendMark(findLabelForField(form, field) || findNearestSiblingLabel(field));
    }
  }

  collectForms();
  if (!forms.length) return;

  for (var i = 0; i < forms.length; i += 1) {
    var form = forms[i];
    var requiredFromData = (form.getAttribute('data-required-fields') || '').split(',');
    markByFieldList(form, requiredFromData);
    markByRequiredAttr(form);
  }
})();

# Rotas e Fluxo – MVP

Este documento descreve apenas o fluxo atual do sistema.

---

## 🖥️ Rotas de UI

Prefixo: /

/login        → login do usuário
/register     → cadastro
/logout       → logout
/dashboard    → área protegida

## Novas rotas Django

- `/responsavel` → formulário do responsável (cria `User`, `Responsavel` e salva assinatura).
- `/aventura` → ficha médica do aventureiro; exige login e persiste doenças/condições/alergias + assinatura.
- `/confirmacao` → painel final que agrupa o responsável autenticado e os aventureiros salvos.

Renderização feita com templates Django.

---

## 🔒 Proteção

- /dashboard exige login
- Usuário não autenticado é redirecionado para /login

---

## 🔌 API (futuro)

Quando necessário:
- Prefixo: /api/
- Usar Django REST Framework
- Somente quando UI não for suficiente

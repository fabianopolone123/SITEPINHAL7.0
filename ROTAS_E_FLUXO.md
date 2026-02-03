# Rotas e Fluxo – MVP

Este documento descreve apenas o fluxo atual do sistema.

---

## 🖥️ Rotas de UI

Prefixo: /

/login        → login do usuário
/register     → cadastro
/logout       → logout
/dashboard    → área protegida

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

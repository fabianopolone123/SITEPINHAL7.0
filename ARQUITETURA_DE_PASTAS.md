# Arquitetura de Pastas – MVP Simples e Evolutivo

Este documento define a organização mínima do projeto no MVP.
A arquitetura pode evoluir conforme o sistema cresce.

---

## 🎯 Objetivo

- Começar simples (login + cadastro + painel)
- Manter clareza
- Permitir crescimento sem reescrita
- Evitar overengineering no início

---

## 🧱 Stack Base

- Backend: Django
- UI: Django Templates
- API: Django REST Framework (quando necessário)
- Banco: PostgreSQL
- Deploy: VPS Ubuntu + Gunicorn + Nginx

---

## 📁 Estrutura Inicial (MVP)

/project-root
│
├── README.md
├── ARQUITETURA_DE_PASTAS.md
├── HISTORICO_DE_MUDANCAS.md
│
├── backend/
│   ├── manage.py
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── apps/
│   │   └── accounts/        # login, cadastro, usuários
│   │
│   ├── ui/
│   │   ├── templates/
│   │   │   ├── base.html
│   │   │   ├── login.html
│   │   │   ├── register.html
│   │   │   └── dashboard.html
│   │   └── static/
│   │
│   └── common/              # utils simples (opcional)
│
└── infra/
    ├── nginx/
    └── systemd/

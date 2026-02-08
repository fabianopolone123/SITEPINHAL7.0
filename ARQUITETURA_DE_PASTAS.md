# Arquitetura de Pastas - MVP Simples e Evolutivo

Este documento define a organizacao base do projeto para manter clareza e facilitar evolucao.

## Objetivo

- Comecar simples (cadastro, login e painel).
- Manter separacao de responsabilidades.
- Facilitar manutencao e deploy.

## Stack base

- Backend: Django
- Frontend: Django Templates + JS/CSS
- Banco: SQLite (atual), com possibilidade de migracao futura
- Deploy: VPS Ubuntu + Gunicorn + Nginx

## Estrutura principal

```text
SITEPINHAL7.0/
  backend/
    accounts/
    config/
    manage.py
    requirements.txt
  ui/
    static/
    templates/
  deploy/
    deploy.sh
  media/
  README.md
  SISTEMA_ATUAL.md
  ROTAS_E_FLUXO.md
  CONTRIBUTING.md
  HISTORICO_DE_MUDANCAS.md
```

## Pastas e responsabilidades

- `backend/accounts/`: regras de negocio, modelos, formularios, views e urls.
- `backend/config/`: configuracoes globais do Django (settings, urls, wsgi/asgi).
- `ui/templates/`: telas em HTML.
- `ui/static/`: CSS, JavaScript e imagens estaticas.
- `media/`: arquivos enviados/gerados (fotos, assinaturas, documentos).
- `deploy/`: scripts e configuracoes de deploy.

## Regras de arquitetura

1. Nao remover fluxo antigo sem backup.
2. Novas features devem entrar sem quebrar rotas legadas.
3. Alteracoes estruturais precisam ser registradas no historico.

# Checklist de Debug

Checklist rapido para investigacao de problemas sem perder contexto.

## 1. Reproducao

- O que o usuario fez?
- O que era esperado?
- O que aconteceu de fato?

## 2. Contexto

- Qual rota/tela?
- Qual perfil de usuario?
- Erro apareceu no navegador, backend ou ambos?

## 3. Validacao tecnica

- Console do navegador (F12).
- Logs do Django/Gunicorn.
- Ultimo commit aplicado.
- Estado de migracoes (`python backend/manage.py showmigrations`).

## 4. Correcao

- Corrigir causa raiz.
- Evitar workaround que gere regressao.
- Garantir que o fluxo principal permanece funcional.

## 5. Fechamento obrigatorio

1. Validar com `python backend/manage.py check`.
2. Commitar.
3. Push.
4. Registrar no `HISTORICO_DE_MUDANCAS.md`.

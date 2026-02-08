# Contribuindo com o projeto

Este documento define o processo minimo para qualquer alteracao no sistema.

## Leitura obrigatoria antes de alterar

1. `README.md`
2. `SISTEMA_ATUAL.md`
3. `ROTAS_E_FLUXO.md`
4. `HISTORICO_DE_MUDANCAS.md`

## Regras de implementacao

1. Nao apagar fluxos existentes sem backup claro.
2. Priorizar compatibilidade com dados ja cadastrados.
3. Evitar mudancas grandes sem registrar impacto em rotas/modelos.
4. Toda alteracao funcional deve ter validacao minima (`python backend/manage.py check`).

## Padrao de commit (obrigatorio)

Formato pedido para este projeto:

`<arquivo_principal>: <descricao objetiva da mudanca>`

Exemplos:

- `backend/accounts/views.py: adiciona validacao de CPF duplicado no novo cadastro`
- `ui/templates/permissoes.html: adiciona busca e rolagem nos blocos de usuarios`

## Checklist obrigatorio de entrega

1. Implementar a mudanca.
2. Validar localmente (`python backend/manage.py check`).
3. Commitar com mensagem no padrao acima.
4. Fazer push para o remoto.
5. Atualizar `HISTORICO_DE_MUDANCAS.md` com:
   - data,
   - resumo objetivo,
   - arquivos principais impactados.

## Regra critica

Uma tarefa so e considerada concluida quando:

- codigo esta no git remoto (`push`), e
- historico foi atualizado.

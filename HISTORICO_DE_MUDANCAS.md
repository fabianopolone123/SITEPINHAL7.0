# Historico de Mudancas

Arquivo oficial de registro das entregas concluidas.

## Regras

- Toda alteracao concluida deve ser registrada aqui.
- Nenhuma tarefa e considerada finalizada sem commit, push e atualizacao deste arquivo.
- Padrao de commit adotado no projeto:
  - `<arquivo_principal>: <descricao objetiva>`

## Fase 1 - Base do sistema (03/02/2026 a 04/02/2026)

- Login, registro e formularios iniciais de responsavel/aventureiro.
- Backend Django inicial com modelos principais e fluxo de confirmacao.
- Validacoes de campos obrigatorios e feedback visual.
- Persistencia de assinaturas e foto 3x4.
- Evolucao do deploy para VPS com script dedicado.

## Fase 2 - Painel, perfis e operacao (04/02/2026 em diante)

- Tela de painel logado (`/painel/`) como entrada apos login.
- Sidebar com menus por permissao.
- Modulo "Meus dados" para responsavel, diretoria e aventureiros.
- Perfis multiplos por usuario via `UserAccess`.
- Permissoes por grupo e excecao individual por usuario.

## Fase 3 - Modulos administrativos

- Modulo WhatsApp com:
  - preferencias por contato,
  - mensagens modelo,
  - envio de teste,
  - fila de envio com worker.
- Modulo Documentos de inscricao com templates e geracao de documentos.
- Modulo Eventos com:
  - criacao de evento,
  - campos extras dinamicos,
  - pre-configuracoes,
  - regra de exclusao por data/hora.

## Fase 4 - Fluxos novos de cadastro

- Novo fluxo de cadastro de aventureiro em etapas:
  - login inicial,
  - ficha de inscricao,
  - ficha medica,
  - declaracao medica,
  - termo de imagem,
  - resumo/finalizacao.
- Novo fluxo de cadastro de diretoria em etapas:
  - login inicial,
  - compromisso voluntariado,
  - termo de imagem,
  - resumo/finalizacao.
- Fluxo legado mantido em paralelo para compatibilidade.

## 08/02/2026 - Limpeza de documentacao

- Documentacao principal consolidada (`README`, `SISTEMA_ATUAL`, `ROTAS_E_FLUXO`, `CONTRIBUTING`).
- Correcao de arquivos `.md` com problemas de codificacao (UTF-8/ANSI).
- Reorganizacao deste historico em formato consolidado por fases para evitar texto corrompido.

## 08/02/2026 - Ajustes em eventos e arquitetura

- Corrigido carregamento de pre-configuracoes na tela `Eventos` para perfil Diretor, evitando falha ao selecionar preset apos salvar.
- Ajustado `presets_json` no backend para envio em formato estruturado (sem dupla serializacao).
- Adicionado parse defensivo no JavaScript de `ui/templates/eventos.html` para garantir leitura dos presets.
- Documento `ARQUITETURA_DE_PASTAS.md` alinhado ao estado real: inclusao de `backend/accounts/migrations/` e `backend/accounts/management/commands/`, e remocao da referencia a `asgi`.

## 08/02/2026 - Eventos: exibicao condicional de nome da pre-configuracao

- Tela `Eventos` ajustada para mostrar o campo "Nome para salvar esta configuracao" apenas ao clicar em `Salvar pre-configuracao`.
- Botao `Salvar pre-configuracao` passou a funcionar em duas etapas: primeiro revela o campo com foco; no segundo clique envia o formulario.
- Ao clicar em `Salvar evento`, o campo de nome da pre-configuracao e ocultado novamente.

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
- Ajustado reset de estado do modal: ao abrir/fechar `Criar novo evento`, o campo de nome da pre-configuracao volta a ficar oculto para nao reaparecer indevidamente.
- Corrigido conflito de CSS no modal de eventos: aplicado seletor `#preset-name-label[hidden] { display: none !important; }` para garantir que o campo fique realmente invisivel ao abrir `Criar novo evento`.

## 08/02/2026 - Modulo Presenca (Diretor)

- Adicionado novo menu `Presenca` para perfil Diretor com permissao dedicada (`presenca`) e rotas novas em `backend/accounts/urls.py`.
- Criada tela `ui/templates/presenca.html` com foco mobile: selecao de evento, busca rapida e lista simples de aventureiros com botao de alternancia `Ausente/Presente`.
- Ordenacao de eventos ajustada para priorizar sempre `Hoje` e `Amanha` no topo da lista.
- Implementado modelo `EventoPresenca` com migracao `0020_eventopresenca.py` para persistir presenca por evento e aventureiro.
- Criadas APIs de atualizacao e consulta em tempo real (`/presenca/toggle/` e `/presenca/status/`) com polling a cada 2s para sincronizar marcacoes entre dispositivos abertos ao mesmo tempo.
- Melhorado visual das caixas `Evento` e `Buscar aventureiro` com cards destacados para leitura rapida no celular.
- Adicionado destaque por cor dos eventos na tela de presenca (`Hoje`, `Amanha`, `Em X dias`, `Ha X dias`) com badges e lista visual clicavel.

## 08/02/2026 - Cadastro de aventureiro: RG e orgao expedidor opcionais

- Removida a obrigatoriedade de preencher RG junto com orgao expedidor no cadastro de aventureiro.
- Validacao de documentos ajustada para aceitar qualquer um entre `certidao`, `RG` ou `CPF`.
- JavaScript do formulario legado (`ui/static/js/aventura.js`) atualizado para nao bloquear envio quando RG estiver sem orgao expedidor.
- Texto explicativo da secao de documentos atualizado nos templates `ui/templates/aventura.html` e `ui/templates/backup_cadastro_antigo/aventura.html`.
- No fluxo novo (`/novo-cadastro/inscricao/`), o formulario passou para `data-required-mode=\"explicit\"` em `ui/templates/novo_cadastro/ficha_inscricao.html`, evitando que `RG` e `Orgao Expedidor` recebam `*` automaticamente.
- Removida tambem a obrigatoriedade de `Certidao de nascimento` e `CPF` no cadastro de aventureiro (documentos totalmente opcionais neste fluxo).
- Adicionado `data-optional=\"true\"` nos campos de documentos do fluxo novo para impedir marcacao automatica de `*` em cenarios de cache antigo.

## 08/02/2026 - Perfil Responsavel: botao para adicionar aventureiro no fluxo novo

- Adicionado botao `Adicionar aventureiro` em `ui/templates/meus_dados_responsavel.html`.
- Criada rota de atalho `meus-dados/responsavel/adicionar-aventureiro/` para abrir o fluxo normal de cadastro de aventureiro a partir do perfil do responsavel.
- Fluxo novo ajustado para reutilizar usuario/responsavel ja autenticado quando iniciado por esse atalho, evitando criar conta duplicada ao finalizar.
- Finalizacao desse caminho agora retorna para `Meus dados` com mensagem de sucesso.

## 08/02/2026 - Recuperacao de senha por CPF + WhatsApp

- Adicionado link `Recuperar senha` na tela inicial de login.
- Implementada rota `recuperar-senha/` com fluxo em etapas:
  - consulta por CPF,
  - exibicao do username encontrado,
  - envio de codigo numerico de 4 digitos para o WhatsApp cadastrado,
  - validacao do codigo,
  - redefinicao da senha com confirmacao em dois campos.
- Incluida protecao basica no fluxo: expiracao do codigo em 10 minutos e limite de tentativas invalidas antes de exigir novo envio.
- Criado template dedicado `ui/templates/password_recovery.html`.

## 08/02/2026 - Cadastro diretoria: telefone residencial opcional

- Removida a obrigatoriedade de `telefone_residencial` no fluxo novo da diretoria (`novo_diretoria/compromisso_voluntariado.html`).

## 08/02/2026 - Unificacao de login e selecao de perfil ativo

- Adicionado seletor de `perfil ativo` na sidebar (`ui/templates/_painel_sidebar.html`) para usuarios com perfis multiplos.
- Criada rota `perfil/alternar/` e view `AlterarPerfilAtivoView` para salvar perfil ativo na sessao.
- Menus do painel agora sao calculados considerando o perfil ativo selecionado.
- Tela de edicao de usuario (`ui/templates/usuario_permissoes_editar.html`) recebeu novo bloco `Unificar login`.
- Implementada unificacao em `UsuarioPermissaoEditarView`:
  - incorpora dados de `Responsavel` e/ou `Diretoria` do login secundario no login principal,
  - combina perfis, grupos e overrides de menu,
  - inativa o login secundario e remove possibilidade de autenticar com ele.
- Incluida validacao de seguranca para bloquear unificacao quando os dois logins ja possuem o mesmo tipo de cadastro (`Responsavel` com `Responsavel` ou `Diretoria` com `Diretoria`).

## 08/02/2026 - CPF entre perfis: Responsavel x Diretoria

- Ajustada validacao de CPF para permitir cadastro cruzado entre perfis (`Responsavel` e `Diretoria`) para a mesma pessoa.
- No fluxo de inscricao (`novo_cadastro`), a checagem de duplicidade passou a usar escopo proprio:
  - `cpf_aventureiro` valida apenas contra `Aventureiro`;
  - `cpf_pai`, `cpf_mae` e `cpf_responsavel` validam apenas contra `Responsavel`.
- No fluxo de diretoria (`novo_diretoria`), o CPF agora bloqueia apenas quando ja existe em `Diretoria`.
- Mantida validacao de RG/certidao conforme regras anteriores.
- Tela de `Presenca` atualizada com miniatura da foto do aventureiro em cada linha para identificacao rapida, com fallback visual `Sem foto` quando nao houver imagem.
- Ajustado fallback da miniatura em `Presenca`: quando `av.foto` nao existir, usa `inscricao_data.foto_3x4` da ficha completa (data URL), corrigindo casos em que a foto nao aparecia na lista.

## 08/02/2026 - Fluxo adicionar aventureiro (responsavel logado)

- Corrigido bloqueio indevido de CPF no fluxo `Adicionar aventureiro` para responsavel ja cadastrado:
  - nesse fluxo, nao bloqueia mais `cpf_pai`, `cpf_mae` e `cpf_responsavel` por duplicidade.
- Mantida validacao de duplicidade para `cpf_aventureiro`, `rg` e `certidao_nascimento`.
- Ajustado pre-preenchimento da ficha de inscricao:
  - quando abrir `Adicionar aventureiro` sem dados temporarios, a tela agora puxa automaticamente os dados do responsavel ja existente (pai/mae/responsavel e contatos).
- Ajustada API de verificacao em tempo real de documentos para respeitar essa mesma regra no fluxo de responsavel existente.

## 08/02/2026 - Cadastro diretoria: escolaridade opcional

- No formulario `novo_diretoria/compromisso_voluntariado`, a secao `Informacoes Educacionais` deixou de ser obrigatoria.
- Removida a validacao obrigatoria de `escolaridade` no backend do passo `NovoCadastroDiretoriaCompromissoView`.
- Removido o marcador oculto de obrigatoriedade de escolaridade no template desse passo.
- No mesmo formulario, o `required mode` passou para `explicit`, garantindo asterisco apenas nos campos realmente obrigatorios.
- `telefone_residencial` e `telefone_comercial` ficaram claramente opcionais no HTML (`se tiver` + `data-optional`), sem marcacao de obrigatorio.
- Ajustado visual da secao `Informacoes Pessoais`: os rótulos dos campos obrigatorios agora exibem `*` diretamente no template, inclusive em linhas com multiplos campos.

## 08/02/2026 - WhatsApp: confirmação automática de inscrição

- Adicionada nova categoria de notificação WhatsApp: `Confirmacao de inscricao`.
- Ao concluir cadastro (novo fluxo e legado) de:
  - `Responsavel + Aventureiro`, e
  - `Diretoria`,
  o sistema envia mensagem automática para o WhatsApp do próprio inscrito com confirmação e orientação de login no `pinhaljunior.com.br`.
- Adicionada nova opção no módulo `WhatsApp`:
  - coluna com caixinha `Confirmacao inscricao` por usuário (liga/desliga recebimento),
  - novo template `Mensagem de Confirmacao` com placeholders próprios.
- Persistência atualizada com migração `0021_whatsapp_confirmacao_notificacao.py`:
  - novo campo `notify_confirmacao` em `WhatsAppPreference`,
  - novo tipo `confirmacao` em `WhatsAppQueue` e `WhatsAppTemplate`.
- Validacao backend do compromisso da diretoria atualizada para nao exigir `telefone_residencial`.
- Removida tambem a obrigatoriedade de `telefone_comercial` no mesmo fluxo (HTML + validacao backend).

## 08/02/2026 - Auditoria (perfil Diretor)

- Adicionado novo menu `Auditoria` no painel do perfil Diretor, com permissao dedicada.
- Criado modelo `AuditLog` com migracao `0022_auditlog.py` para registrar:
  - quem (usuario/username/perfil),
  - onde (tela/rota),
  - o que fez (acao),
  - data e hora,
  - metadados tecnicos (metodo HTTP, path, IP e user agent).
- Criada tela `auditoria/` com busca por usuario, acao, local e detalhes.
- Adicionado logging automatico de autenticacao:
  - login no sistema,
  - logout do sistema.
- Adicionado logging automatico de operacoes autenticadas `POST/PUT/PATCH/DELETE` via middleware.
- Adicionado log explicito de marcacao de presenca (evento, aventureiro e status presente/ausente).
- Adicionado log explicito de administracao de usuarios:
  - unificacao de logins,
  - alteracao de permissoes/perfis.

## 08/02/2026 - Auditoria: filtros e abrangencia de registro

- Tela `Auditoria` ampliada com filtros por:
  - busca geral (`q`),
  - usuario,
  - acao,
  - assunto,
  - onde (tela/rota),
  - metodo HTTP,
  - periodo (`data_inicio` e `data_fim`).
- Adicionado botao `Limpar` para resetar filtros rapidamente.
- Tabela de auditoria agora exibe tambem a coluna `Metodo`.
- Middleware de auditoria passou a registrar tambem acessos de tela por `GET` autenticado (com filtros de ruido para APIs e endpoints de polling), alem das operacoes de escrita (`POST/PUT/PATCH/DELETE`).

## 08/02/2026 - Auditoria: remocao de ruído de navegador

- Middleware de auditoria ajustado para ignorar requisicoes de navegador que nao sao acao funcional do usuario:
  - `/favicon.ico`
  - `/robots.txt`
- Com isso, eventos como `Acesso de tela: /favicon.ico` deixam de aparecer no log.

## 23/02/2026 - WhatsApp: confirmacao de inscricao desmarcada por padrao em novos usuarios

- Corrigido o comportamento da preferencia WhatsApp `Confirmacao inscricao` para novos cadastros: agora `notify_confirmacao` nasce desmarcado (`False`) em vez de marcado automaticamente.
- Adicionada migracao `0023_alter_whatsapppreference_notify_confirmacao.py` para alinhar o schema ao novo padrao.
- Observacao: a alteracao vale para novos registros de preferencia; usuarios ja existentes nao foram alterados automaticamente.

## 23/02/2026 - WhatsApp: confirmacao de inscricao automatica sem checkbox por usuario

- Removida da tela `WhatsApp` a coluna/caixinha `Confirmacao inscricao` por usuario, pois essa mensagem e automatica e enviada apenas na conclusao da inscricao.
- Ajustada a `WhatsAppView` para nao salvar nem exibir resumo dessa preferencia no formulario de contatos.
- O envio de confirmacao de inscricao agora ocorre independentemente da preferencia `notify_confirmacao`, garantindo que novos inscritos recebam a notificacao ao concluir o cadastro.
## 23/02/2026 - Meus dados (Diretoria): permitir alterar foto no editar

- Formulario `Meus dados > Diretoria > Editar` passou a exibir o campo `foto` no `DiretoriaDadosForm`.
- View `MinhaDiretoriaEditarView` ajustada para receber `request.FILES`, permitindo salvar upload de nova foto.
- Template `meus_dados_diretoria_editar.html` atualizado para `multipart/form-data`.
## 23/02/2026 - Meus dados (foto): priorizar nova foto quando `Limpar` estiver marcado

- Ajustado o widget de upload nas edicoes de `Aventureiro` e `Diretoria` para evitar erro de conflito quando o usuario marca `Limpar` e seleciona uma nova foto ao mesmo tempo.
- Nessa situacao, o sistema agora prioriza a nova foto enviada e salva a substituicao normalmente.
## 23/02/2026 - Permissoes: perfis sincronizados com grupos (inclui grupos novos)

- Ajustada a logica de perfis disponiveis na sidebar para considerar tambem os grupos vinculados ao usuario (`AccessGroup`), permitindo que grupos personalizados (ex.: `secretaria`) aparecam como opcoes de perfil.
- Ajustado filtro de menus por `perfil ativo` para aceitar perfis derivados de grupos personalizados (usa o codigo do grupo).
- Tela `Permissoes` agora sincroniza `UserAccess.profiles` automaticamente ao montar a lista e ao salvar vinculos de usuario x grupo, corrigindo casos em que o usuario estava em varios grupos mas o menu nao mostrava `Trocar perfil`.
## 23/02/2026 - Sidebar do painel: rolagem e responsividade para muitos menus

- Sidebar do painel ajustada para ter altura da viewport no desktop (`100vh`) e rolagem vertical propria no bloco de menu, evitando que itens fiquem escondidos quando houver muitos menus/perfis.
- Em telas menores (mobile/tablet), a sidebar volta a altura automatica e a rolagem interna e desativada para manter a navegacao responsiva.
- Ajuste pensado para uso em celular, garantindo acesso aos menus mesmo com mais opcoes de perfil.
## 23/02/2026 - Perfil ativo: menu respeita apenas o grupo/perfil selecionado

- Corrigido filtro de menus por `perfil ativo` para impedir que grupos personalizados (ex.: `secretaria`) aparecam em outros perfis selecionados.
- Agora, ao trocar perfil na sidebar, os menus exibidos sao filtrados apenas pelos grupos/perfil correspondentes ao perfil ativo escolhido.
## 23/02/2026 - Permissões: alinhamento entre perfil `Diretoria` e grupo `diretoria`

- Criado grupo padrão `diretoria` (mesmos menus administrativos do grupo `diretor`) para alinhar com o perfil `Diretoria` existente no sistema.
- Ajustado o mapeamento do perfil `Diretoria` para usar o grupo `diretoria` no filtro de menus por perfil ativo.
- A tela `Permissões` agora adiciona automaticamente grupos padrão faltantes por perfil (ex.: usuário com perfil `Diretoria` recebe o grupo `diretoria`, sem remover outros grupos já marcados).
- Grupo padrão `diretoria` protegido contra exclusão na tela de permissões.
## 23/02/2026 - Permissões (UX): esconder `Excluir` no grupo padrão `Diretoria`

- Tela `Permissões` ajustada para ocultar o botão `Excluir` também no grupo padrão `diretoria`, mantendo coerência com a regra do backend.
- Texto informativo de grupos padrão atualizado para listar `Diretoria`.
## 23/02/2026 - Permissões: salvar vínculos de grupo ignora linhas bloqueadas por exceção individual

- Corrigido o salvamento de `Usuários por grupo` na tela `Permissões`: linhas bloqueadas por `Exceção por usuário` agora são ignoradas no backend (em vez de serem processadas com checkboxes desabilitados).
- Adicionada mensagem informativa após salvar, indicando quantas linhas foram ignoradas por exceção individual ativa.
## 23/02/2026 - Permissões: `Usuários por grupo` não remarca grupos automaticamente ao recarregar

- Corrigido o bloco `Usuários por grupo` para não readicionar grupos padrão automaticamente durante o carregamento da tela `Permissões`.
- Isso corrige o caso em que o usuário desmarcava um grupo (ex.: `Diretoria`), salvava, e a caixa voltava marcada ao reabrir/recarregar a página.
- A sincronização de perfis continua, mas sem forçar novamente o vínculo de grupo no `GET` da tela.
## 23/02/2026 - Cadastro de aventureiro (inscrição): `Pai/Mãe ausente` + documentos obrigatórios

- Adicionadas as opções `Pai ausente` e `Mãe ausente` na ficha de inscrição (`novo_cadastro/ficha_inscricao`).
- Ao marcar, os campos do respectivo bloco (pai ou mãe) são desabilitados no frontend e o backend limpa esses dados no salvamento da etapa.
- Validação de duplicidade de CPF no passo de inscrição passou a ignorar `cpf_pai`/`cpf_mae` quando o respectivo responsável estiver marcado como ausente.
- Restaurada a obrigatoriedade dos documentos na inscrição do aventureiro (`Certidão de nascimento`, `RG`, `Órgão Expedidor` e `CPF`), com validação no frontend e no backend.
## 23/02/2026 - Ficha de inscrição (aventureiro): revisão de campos obrigatórios com `*`

- Revisados os campos da ficha de inscrição do aventureiro e adicionados `required` nos campos obrigatórios principais (dados do aventureiro e do responsável legal), para exibição automática de `*` no frontend.
- Validação backend da etapa `novo_cadastro_inscricao` alinhada aos mesmos campos obrigatórios, evitando inconsistência entre asterisco/HTML e processamento do servidor.
## 23/02/2026 - Módulo Financeiro (inicial): menu + mensalidades por aventureiro

- Adicionado novo menu `Financeiro` no painel (via permissões), habilitado por padrão no grupo `diretor`.
- Criada rota/tela `financeiro/` com aba inicial `Mensalidades` (aberta por padrão).
- Implementado cadastro/geração de mensalidades por aventureiro:
  - seleciona o aventureiro,
  - clica em `Gerar mensalidades`,
  - sistema gera mensalidades do mês atual até dezembro do ano vigente (sem duplicar registros existentes).
- A tela exibe abaixo o aventureiro selecionado e a lista das mensalidades geradas.
- Criado modelo `MensalidadeAventureiro` com migração `0024_mensalidadeaventureiro.py`.
## 23/02/2026 - Permissões: menus por grupo deixam de ser remarcados automaticamente

- Corrigida a função de grupos padrão para não recompor automaticamente os `menus liberados por grupo` em grupos já existentes.
- Isso corrige o caso em que o usuário marcava/desmarcava menus, clicava em `Salvar menus dos grupos` e as caixas voltavam ao estado anterior.
- A função continua garantindo a criação dos grupos padrão e ajustando o nome exibido, sem sobrescrever os menus configurados manualmente.
## 23/02/2026 - Financeiro > Mensalidades: valor configurável e grade horizontal por aventureiro

- Adicionado campo de valor na geração de mensalidades (padrão `35`), permitindo informar o valor antes de clicar em `Gerar mensalidades`.
- Modelo `MensalidadeAventureiro` atualizado com campo `valor` e migração `0025_mensalidadeaventureiro_valor.py`.
- Lista do aventureiro selecionado passou a exibir também o valor de cada mensalidade.
- Adicionada tabela fixa de resumo (ano atual) com os aventureiros que já possuem mensalidades cadastradas, mostrando os meses na horizontal.
## 23/02/2026 - Financeiro > Mensalidades: edição/exclusão por clique em modal

- Ao clicar em uma mensalidade cadastrada (na lista do aventureiro ou na grade horizontal), a tela agora abre uma janela suspensa para editar o valor ou excluir o registro.
- `FinanceiroView` passou a tratar as ações `editar_mensalidade` e `excluir_mensalidade`, mantendo o aventureiro selecionado após salvar.
- A grade de resumo ganhou metadados por célula (`id`, `competência`, `valor`) para permitir edição direta por clique.
## 23/02/2026 - Financeiro (Responsável): visão de mensalidades pendentes dos próprios aventureiros

- A tela `Financeiro` passou a ter uma visão específica para o perfil ativo `Responsável`, mostrando apenas os aventureiros vinculados ao usuário logado.
- Nessa visão são exibidas somente mensalidades pendentes atrasadas e do mês atual, com caixas de seleção por mensalidade.
- Adicionado botão `Pagar` (placeholder), com mensagem informativa de que a funcionalidade de pagamento será implementada depois.
- Grupo padrão `responsavel` atualizado para incluir o menu `financeiro`.
## 23/02/2026 - Financeiro (Responsável): soma automática das mensalidades selecionadas

- Na visão de `Financeiro` do perfil `Responsável`, a tela agora exibe o total das mensalidades marcadas ao lado do botão `Pagar`.
- O valor é atualizado automaticamente ao marcar/desmarcar mensalidades, sem recarregar a página.

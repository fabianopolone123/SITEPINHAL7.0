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
## 23/02/2026 - Financeiro (Responsável): integração Pix com Mercado Pago no botão `Pagar`

- Integrado o botão `Pagar` da visão `Responsável` ao Mercado Pago (Pix), baseado no padrão usado no projeto `SITEANDREWS`.
- Ao selecionar mensalidades pendentes e clicar em `Pagar`, o sistema cria um pagamento Pix no Mercado Pago, registra localmente o vínculo com as mensalidades e abre modal com QR Code + código copia e cola.
- Adicionada API de status do pagamento para atualização da situação no modal e marcação automática das mensalidades como `Paga` quando o Mercado Pago retornar `approved`.
- Criado modelo `PagamentoMensalidade` com migração `0026_pagamentomensalidade.py`.
- Token usado via variável de ambiente `MP_ACCESS_TOKEN_PROD` (ou `MP_ACCESS_TOKEN` como fallback).
## 23/02/2026 - Financeiro (Responsável): webhook Mercado Pago para atualizar pagamento em tempo real

- Adicionado endpoint público de webhook em `accounts/financeiro/mp-webhook/` para receber notificações do Mercado Pago (Pix).
- Ao receber a notificação, o sistema consulta o pagamento no Mercado Pago, sincroniza o status local e marca as mensalidades vinculadas como `Paga` quando o pagamento for aprovado.
- A criação do Pix passou a enviar `notification_url` automaticamente (ou usar `MP_NOTIFICATION_URL` quando configurado), permitindo atualização mais rápida no modal do responsável.
- Suporte opcional à validação de assinatura do webhook via `MP_WEBHOOK_SECRET`.
## 23/02/2026 - Financeiro (Mercado Pago): correção de `payer.email` válido para Pix

- Corrigida a geração do `payer.email` no pagamento Pix de mensalidades para usar e-mail válido do usuário/responsável quando disponível.
- Adicionado fallback com domínio público (via `MP_PAYER_EMAIL_DOMAIN`, `SITE_DOMAIN` ou host da requisição), evitando rejeição do Mercado Pago por domínio inválido (`.local`).
## 23/02/2026 - Financeiro (Responsável): recarrega lista após fechar modal com pagamento aprovado

- Ao fechar o modal Pix após o status `Pagamento aprovado`, a tela de mensalidades do responsável agora recarrega automaticamente.
- Isso atualiza a lista imediatamente para remover as mensalidades que já foram pagas.
## 23/02/2026 - Financeiro (Diretor): marcar mensalidade como paga/pendente no modal

- No painel `Financeiro` do perfil `Diretor`, o modal da mensalidade agora permite marcar o registro como `Paga` ou voltar para `Pendente`.
- A lista do aventureiro e a grade horizontal passaram a destacar visualmente mensalidades pagas.
- Mantidos os recursos existentes de editar valor e excluir mensalidade no mesmo modal.
## 23/02/2026 - WhatsApp: notificação automática de pagamento aprovado + mensagem padrão configurável

- Quando um pagamento de mensalidades é aprovado no Mercado Pago, o sistema agora envia WhatsApp automaticamente para o responsável com agradecimento e lista do que foi pago.
- Adicionado suporte a contatos adicionais na notificação de pagamento aprovado via módulo `WhatsApp` (coluna `Pagamento aprovado`), com caixas desmarcadas por padrão.
- Adicionada nova mensagem padrão `Pagamento aprovado` em `WhatsApp > Mensagens padrão`, com placeholders de mensalidades/valor total/pagamento.
- Criado campo `whatsapp_notified_at` em `PagamentoMensalidade` para evitar reenvio duplicado após aprovações sincronizadas por polling/webhook.
- Migração adicionada: `0027_pagamentomensalidade_whatsapp_notified_at_and_more.py`.
## 23/02/2026 - Financeiro: separação entre `Inscrição` e `Mensalidade` + geração automática no novo cadastro

- `MensalidadeAventureiro` ganhou campo `tipo` (`Inscrição` ou `Mensalidade`) para separar a primeira cobrança das demais no módulo Financeiro.
- Ao gerar cobranças no `Financeiro` (Diretor), o mês atual passa a ser criado como `Inscrição` e os meses seguintes até dezembro como `Mensalidade`.
- Ao concluir uma nova inscrição de aventureiro, o sistema agora gera automaticamente as cobranças no mesmo formato (`Inscrição` no mês atual + mensalidades até dezembro).
- As listagens e mensagens de pagamento passaram a exibir o tipo da cobrança (`Inscrição`/`Mensalidade`).
- Migração adicionada: `0028_mensalidadeaventureiro_tipo.py`.
## 23/02/2026 - Financeiro (Diretor): botão para gerar cobranças de todos os aventureiros

- Adicionado botão `Gerar para todos` na tela `Financeiro > Mensalidades` (perfil Diretor).
- O botão gera cobranças em lote para todos os aventureiros usando a mesma lógica atual (mês atual como `Inscrição` e meses seguintes como `Mensalidade`).
- O processo respeita registros já existentes: não sobrescreve nem duplica cobranças já geradas.
- A mensagem de retorno resume quantidade total criada e quantos aventureiros foram afetados.
## 23/02/2026 - Loja (Diretor): módulo inicial de cadastro de produtos com variações

- Adicionado novo menu `Loja` no painel (perfil `Diretor`) com tela inicial de cadastro e listagem de produtos.
- Cadastro de produto com campos: `foto`, `título`, `descrição` e variações dinâmicas.
- Cada variação permite informar `nome`, `valor` e `estoque` (opcional).
- Criados modelos `LojaProduto` e `LojaProdutoVariacao` com migração `0029_lojaproduto_lojaprodutovariacao.py`.
- O cadastro valida ao menos uma variação com valor e não exige estoque.
## 23/02/2026 - Financeiro: valor padrão das cobranças ajustado para 30

- Alterado o valor padrão das cobranças/mensalidades de `35` para `30` no módulo Financeiro.
- Ajuste aplicado no campo de geração manual, nos fallbacks do backend e na geração automática após nova inscrição.
- Atualizado também o default do modelo `MensalidadeAventureiro` (migração `0030_alter_mensalidadeaventureiro_valor_default.py`).
## 23/02/2026 - Pontos (Diretor/Diretoria): lançamentos individuais/todos + pré-registros padrão

- Adicionado novo menu `Pontos` no painel (habilitado por padrão para `Diretor` e `Diretoria`).
- Criada tela de pontos com lançamento manual exigindo `valor` e `motivo`, podendo aplicar para um aventureiro específico ou para todos.
- Suporte a pontos positivos e negativos (ex.: `15`, `-10`).
- Criado cadastro de pré-registros padrão (ex.: `Presença +15`, `Bom comportamento +10`, `Mau comportamento -10`) com aplicação individual ou para todos.
- Incluídos ranking de totais por aventureiro e histórico de lançamentos recentes na mesma tela.
- Modelos criados: `AventureiroPontosPreset` e `AventureiroPontosLancamento` com migração `0031_aventureiropontospreset_aventureiropontoslancamento.py`.
## 23/02/2026 - Pontos (UX): textos mais claros no lançamento e aplicação de pré-registro

- Renomeado o bloco `Lançar pontos (manual)` para `Cadastrar lançamento`.
- Botão principal do lançamento manual também alterado para `Cadastrar lançamento`.
- No bloco `Aplicar pré-registro`, o texto `Destino` foi trocado por `Aplicar para` para reduzir confusão.
## 23/02/2026 - Pontos (UX): reorganização dos blocos de pré-registro para melhor entendimento

- Reorganizada a tela `Pontos` para agrupar `Cadastrar pré-registro padrão` e `Aplicar pré-registro` no mesmo card.
- A lista de pré-registros cadastrados foi mantida logo abaixo desses dois formulários, no mesmo contexto visual.
- Objetivo: deixar mais claro que o pré-registro é cadastrado e usado no mesmo fluxo.
## 23/02/2026 - Pontos (Responsável): consulta de totais e extrato dos próprios aventureiros

- O menu `Pontos` também foi liberado para o perfil `Responsável`.
- A tela `Pontos` passou a ter uma visão específica para responsável (somente consulta), exibindo:
  - total de pontos por aventureiro vinculado,
  - extrato de lançamentos de pontos de cada aventureiro.
- Na visão de responsável não há lançamentos manuais nem cadastro/aplicação de pré-registros.
## 23/02/2026 - Pontos (Responsável): exibe foto do aventureiro no card de extrato

- Adicionada a foto do aventureiro nos cards da visão `Pontos` do perfil `Responsável`.
- Quando o aventureiro não tiver foto, a tela mostra um fallback com a inicial do nome.
## 23/02/2026 - Pontos (Responsável): textos de cabeçalho e aviso ajustados para modo consulta

- A visão `Pontos` do perfil `Responsável` deixou de exibir textos de administração (lançamento/pré-registro).
- Cabeçalho e mensagem inicial agora mostram orientação de consulta (totais e extrato dos aventureiros).
## 23/02/2026 - Pontos (Responsável): removidos textos extras de cabeçalho/aviso

- A visão `Pontos` do perfil `Responsável` ficou mais limpa, sem textos descritivos no cabeçalho e no bloco de status quando não houver mensagens.
- Mantido apenas o conteúdo principal (cards com totais e extratos).
## 23/02/2026 - Pontos (Responsável): oculta card de status vazio

- Removido o card em branco no topo da tela `Pontos` (perfil `Responsável`) quando não houver mensagens para exibir.
- O card de status continua aparecendo normalmente no modo administrativo e sempre que houver mensagens.
## 23/02/2026 - Pontos (Diretor): unifica lançamento e pré-registros em um único card

- Reorganizada a tela `Pontos` no modo administrativo para concentrar `Cadastrar lançamento`, `Pré-registros padrão` e `Aplicar pré-registro` em um único card principal.
- O fluxo de uso ficou mais claro no painel, mantendo a listagem de pré-registros no mesmo contexto visual.
- `Totais por aventureiro` e `Lançamentos recentes` permanecem em cards separados abaixo.
## 23/02/2026 - Pontos (Diretor): formulário único com salvar lançamento como pré-registro

- A tela de `Pontos` (modo administrativo) passou a usar um único formulário para `Lançamentos e pré-registros`.
- Adicionado campo `Pré-registro salvo (opcional)` para preencher automaticamente `Nome do pré-registro`, `Pontos` e `Motivo`.
- Botão `Cadastrar lançamento` foi renomeado para `Enviar lançamento`.
- Adicionado botão `Salvar lançamento`, que grava o preenchimento atual como pré-registro padrão para reutilização posterior.
- Removidos da tela os controles de `Pré-registro ativo` e a coluna `Status` da tabela de pré-registros.
## 23/02/2026 - Pontos (Diretor): confirmação visual ao enviar lançamento

- Ao enviar um lançamento com sucesso, a tela `Pontos` agora destaca a confirmação levando o foco ao bloco de status.
- Também exibe um alerta de confirmação com a mensagem de sucesso para dar retorno imediato ao usuário.
## 23/02/2026 - Correção de codificação (PT-BR): textos com caracteres quebrados

- Corrigidos textos com codificação quebrada (`Ã`, `�`) em `backend/accounts/views.py`.
- Ajustados rótulos de menu (ex.: `Início`, `Presença`, `Usuários`, `Permissões`, `Documentos inscrição`) e mensagens de validação/feedback para acentuação correta em PT-BR.
## 23/02/2026 - Permissões: padrão de novos usuários e responsável com grupo automático

- Ajustado o `UserAccess` para não forçar perfil `Responsável` automaticamente em usuários genéricos sem grupo/cadastro vinculado.
- Sincronização de perfis por grupos/cadastros deixou de remarcar perfil por fallback quando o usuário não possui vínculo real.
- No cadastro de responsável com aventureiro, o usuário novo passa a receber automaticamente o grupo padrão `responsavel` (ficando marcado/liberado em `Permissões`).
## 23/02/2026 - Permissões: menus do grupo passam a valer para diretor/diretoria

- Corrigida a lógica de menus para priorizar permissões do grupo quando o usuário possui grupo vinculado no perfil ativo.
- Agora desmarcar `Pontos`, `Loja` (ou qualquer outro menu) em `Menus liberados por grupo` remove o botão da sidebar corretamente.
- Mantido fallback de compatibilidade apenas para usuários antigos sem grupos vinculados.
## 23/02/2026 - Permissões (UX): explicação visual de Diretor x Diretoria

- Adicionada uma legenda explicativa na tela `Permissões` esclarecendo a diferença entre `Diretor` (perfil/grupo administrativo) e `Diretoria` (perfil de cadastro da pessoa da diretoria).
- Ajuste somente visual, sem alterar regras de acesso.
## 23/02/2026 - Aventureiros: classificação automática por classes (idade)

- A lista `Aventureiros cadastrados` passou a ser organizada por classes automáticas com base na idade (data de nascimento):
  - `Abelhinhas` (6 anos)
  - `Luminares` (7 anos)
  - `Edificadores` (8 anos)
  - `Mãos Ajudadoras` (9 anos)
- Crianças fora dessas faixas (ou sem data de nascimento) ficam na seção `Sem classe`.
- A classificação é calculada automaticamente, então novos inscritos já aparecem na classe correta sem cadastro manual.
- Regra ajustada para usar a idade na data de corte `30/06` do ano atual (ex.: quem completa 6 anos até 30/06 entra em `Abelhinhas`).
- Ajuste refinado: a regra de corte `30/06` passou a valer somente para `Abelhinhas` (crianças com 5 anos que completam 6 até 30/06). As demais classes seguem pela idade atual.
## 23/02/2026 - Aventureiro (detalhe): visualização mais clara de documentos, condições e alergias

- Reorganizada a tela de detalhes do aventureiro em seções mais claras (`Dados básicos`, `Documentos e saúde`, `Doenças`, `Condições`, `Alergias`, `Deficiências`).
- `Condições` e `Alergias` passaram a usar tabela com colunas separadas (resposta, detalhes, remédios), evitando textos ambíguos como `Sim - Não`.
- Valores genéricos como `Não`, `-` e `Nenhum` em campos de descrição são tratados como “sem descrição informada” / “não se aplica” para melhorar a leitura.
- Ajustes aplicados tanto na visão do responsável quanto na visão geral da diretoria.
## 23/02/2026 - Cadastro de alergias (ficha médica): corrige interpretação de "Não" em campo livre

- Corrigida a conversão das alergias no fluxo de inscrição antigo (`ficha médica`): textos como `Não`, `Nao`, `-`, `Nenhum` não são mais gravados como resposta `Sim`.
- Ajustada também a leitura dos registros antigos para tratar esses casos como `Não` na tela de detalhes do aventureiro.
- Motivo: os campos de alergia nesse fluxo são texto livre e vários cadastros tinham `Não` digitado, o que antes era interpretado incorretamente como alergia existente.
## 25/02/2026 - Novo cadastro de aventureiro: quantidade de fichas + redesign visual das etapas

- Adicionado no login inicial do cadastro de aventureiro o campo `Quantos aventureiros vai cadastrar no clube?` (1 a 10).
- O fluxo agora usa essa quantidade para controlar o resumo/finalização e o botão `Cadastrar próximo aventureiro`, sem perder o reaproveitamento dos dados dos responsáveis já preenchidos.
- Ao atingir a quantidade informada, o resumo passa a orientar a revisão/finalização e bloqueia o acréscimo além do total escolhido.
- Redesign visual das telas `Ficha de Inscrição`, `Ficha Médica` e `Termo de Imagem`, mantendo os mesmos campos e hooks do sistema (assinatura, foto, validações e JS).
- Incluídas barras de progresso nessas etapas mostrando `Aventureiro X de Y`, quantidade salva e restante.
## 25/02/2026 - Cadastro (ficha de inscrição): compressão automática da foto 3x4 no navegador

- A foto 3x4 enviada na ficha de inscrição passa a ser redimensionada/comprimida no navegador antes de ir para o campo oculto em Base64.
- Objetivo: reduzir o payload do POST e evitar `Bad Request (400)` por requisição muito grande ao enviar a primeira ficha.
- Mantido o preview da foto e a compatibilidade com o fluxo atual de assinatura/validação.
## 25/02/2026 - Resumo do cadastro: finalização bloqueada até completar a quantidade e foto no card

- No resumo/finalização do cadastro de aventureiro, o botão `Finalizar` agora só aparece quando a quantidade de aventureiros informada no início foi completamente preenchida.
- Adicionada validação no backend para impedir finalização antecipada (com mensagem amigável), evitando erro ao clicar em `Finalizar` antes da hora.
- Os cards de confirmação no resumo agora exibem a foto 3x4 do aventureiro cadastrado.
## 25/02/2026 - Novo cadastro: tela de sucesso com modal e retorno controlado ao login

- Após finalizar o cadastro de novo responsável com aventureiros, o fluxo agora redireciona para uma tela de sucesso dedicada (`novo-cadastro/sucesso/`) antes do login.
- A tela mostra um modal de confirmação com resumo do cadastro (responsável, usuário e quantidade de aventureiros) e botão único `Voltar para tela de login`.
- Adicionados bloqueios visuais/comportamentais na tela de sucesso (sem botão de fechar e com contenção de navegação por script), além de cabeçalhos `no-store` para reduzir retorno por cache após sair.
## 25/02/2026 - Novo cadastro (login inicial): textos mais claros para o responsável

- Ajustados os textos de abertura da tela inicial do novo cadastro de aventureiros para ficarem direcionados ao usuário responsável que está preenchendo.
- Mantida a mesma lógica/campos da etapa (somente melhoria de comunicação/UX).
## 25/02/2026 - Loja: múltiplas fotos por produto com vínculo obrigatório por variação

- O cadastro de produtos da `Loja` agora permite adicionar várias fotos no mesmo produto.
- Cada foto é cadastrada em uma linha própria e deve ser vinculada a uma variação do produto (`P`, `M`, cor, tamanho etc.).
- Criado modelo `LojaProdutoFoto` para armazenar as fotos vinculadas às variações, mantendo compatibilidade com produtos antigos que ainda usam foto única.
- A listagem de produtos passou a exibir as fotos vinculadas em cada variação, com miniaturas nos cards da loja.
## 25/02/2026 - Loja: foto pode pertencer a múltiplas variações ou a todas

- Evoluído o cadastro de fotos da `Loja` para permitir que uma mesma foto seja vinculada a várias variações do produto.
- Adicionada opção `Todas as variações` por foto, evitando cadastro duplicado da mesma imagem quando ela serve para o produto inteiro.
- Mantida compatibilidade com o vínculo anterior de foto para variação única.
## 25/02/2026 - Loja: mínimo de pedidos pagos para produção (opcional) no produto

- Adicionado no cadastro de produto da `Loja` o campo opcional `Mínimo de pedidos pagos para produção`.
- Permite configurar regras como “camiseta de atividade só enviar para confecção após 10 pedidos pagos”.
- A regra fica salva no produto e é exibida na listagem dos itens cadastrados.
## 25/02/2026 - Loja (UX mobile): seleção de variações das fotos trocada para checkboxes

- A seleção de vínculo das fotos com variações no cadastro da `Loja` foi trocada de `select múltiplo` para `checkboxes`.
- Mantida a opção `Todas as variações`, com comportamento automático para desmarcar as demais ao selecionar.
- Objetivo: facilitar o uso no celular e evitar dificuldade de seleção múltipla em navegadores móveis.
## 25/02/2026 - Loja (Responsável): catálogo com cards responsivos, variação e quantidade

- A rota `Loja` passou a ter uma visão específica para o perfil ativo `Responsável`, exibindo somente produtos ativos.
- Criado catálogo com cards responsivos (celular/PC) mostrando foto, título, descrição, regra de mínimo de pedidos pagos (quando existir), variações e valor.
- Seleção de variação agora atualiza o valor exibido e troca a foto principal/minigaleria conforme as fotos vinculadas à variação.
- Adicionados controles de quantidade com botões `+` e `-` (mínimo 1) e botão `Adicionar ao carrinho` como placeholder para a próxima etapa.
- Incluído `Loja` no menu padrão do perfil `Responsável` para novos grupos/perfis.
## 25/02/2026 - Loja (Responsável) UX: lista suspensa de variações e cards com largura controlada

- No catálogo da `Loja` para `Responsável`, a escolha de variações foi ajustada para `lista suspensa` (select), em vez de lista expandida.
- Removida do card do responsável a faixa visual de `Produção sob pedido: mínimo de pedidos pagos`.
- Ajustado o grid dos cards para largura controlada no PC (evitando card gigante quando há poucos produtos) e mantendo responsividade no celular.
- Mantida exibição da foto principal com `object-fit: contain` e miniaturas sem corte para melhor visualização do produto.
## 25/02/2026 - Loja (Responsável): visualização ampliada da foto em modal responsivo

- No catálogo da `Loja` para `Responsável`, clicar na foto principal ou nas miniaturas agora abre uma janela suspensa responsiva com a imagem ampliada.
- Modal com fechamento por botão, clique no fundo e tecla `Esc`, mantendo a foto em `object-fit: contain` para não cortar a imagem.
## 25/02/2026 - Loja (Responsável): navegação entre fotos dentro do modal ampliado

- A janela suspensa de visualização de fotos do catálogo da `Loja` passou a permitir alternar entre as imagens da variação selecionada sem fechar o modal.
- Adicionados controles `anterior/próxima`, contador de fotos e suporte às teclas `←` e `→`.
## 25/02/2026 - Loja (Responsável): carrinho lateral com itens, total e pagamento (placeholder)

- Implementado carrinho no catálogo da `Loja` para o perfil `Responsável`, com abertura automática em painel lateral ao adicionar item.
- Carrinho mostra itens adicionados (produto, variação, foto, valor unitário, subtotal) e permite editar quantidade com `+`/`-` e remover item.
- Exibe total do pedido, seleção de forma de pagamento e botão `Finalizar pedido` (por enquanto como placeholder de próxima etapa).
- Carrinho fica salvo no navegador (`localStorage`) para manter os itens durante a navegação/atualização da página.
## 25/02/2026 - Loja (Responsável): finalização com Pix Mercado Pago (pedido + QR Code + status)

- Implementado backend de `Pedidos da Loja` (`LojaPedido` e `LojaPedidoItem`) com status, itens, total e campos de integração Mercado Pago.
- O botão `Finalizar pedido` do carrinho agora cria um pedido real da loja e gera pagamento Pix via Mercado Pago.
- Adicionado modal Pix no catálogo da loja com QR Code, código copia-e-cola, atualização manual de status e polling automático.
- Criados endpoints para `criar pedido Pix`, consultar `status do pedido` e `webhook` da loja, marcando o pedido como pago quando confirmado pelo Mercado Pago.
- Mantida forma de pagamento somente `Pix` por enquanto.
## 25/02/2026 - Loja (Respons�vel): confirma��o visual do pedido pago, WhatsApp e ajuste de estoque no cat�logo

- Adicionada uma segunda janela suspensa (modal de sucesso) no cat�logo da `Loja` para confirmar visualmente quando o pedido Pix for aprovado.
- O modal de sucesso abre automaticamente quando o status do pedido muda para `Pago` (via polling/manual) e mostra n�mero do pedido, status e total.
- Pagamentos aprovados de `Pedidos da Loja` agora enviam WhatsApp ao respons�vel usando a mensagem padr�o de `Pagamento aprovado` (Financeiro), incluindo resumo dos itens do pedido; contatos extras marcados nessa notifica��o tamb�m recebem.
- Adicionado controle `whatsapp_notified_at` em `LojaPedido` para evitar envio duplicado de WhatsApp quando webhook e consulta de status processam o mesmo pagamento.
- No cat�logo do perfil `Respons�vel`, removida a exibi��o de `Estoque n�o informado` quando a varia��o n�o possui estoque cadastrado.
## 25/02/2026 - Loja (Respons�vel): bot�o Meus pedidos com resumo e detalhes do pedido

- Adicionado bot�o `Meus pedidos` na tela da `Loja` para o perfil `Respons�vel`, ao lado do bot�o `Carrinho`.
- O bot�o abre uma janela suspensa responsiva com resumo dos pedidos (um por linha), mostrando n�mero do pedido, data/hora, quantidade de itens, status e total.
- Cada linha pode ser clicada para expandir e ver os detalhes completos do pedido, incluindo itens, varia��o, quantidade, valores e forma de pagamento.
- A listagem usa os pedidos do respons�vel logado e respeita o status atual salvo no sistema (`Pagamento aprovado`, `Aguardando pagamento`, etc.).
## 25/02/2026 - Loja (Respons�vel) UX: removido texto t�cnico do rodap� do carrinho

- Removido do carrinho da `Loja` (perfil `Respons�vel`) o texto t�cnico sobre etapas futuras de hist�rico/gest�o de pedidos.
- Objetivo: deixar a interface mais limpa e focada no cliente final.
## 25/02/2026 - Presen�a (Respons�vel): consulta por aventureiro com foto e hist�rico por evento

- A tela `Presen�a` agora tem uma vis�o pr�pria para o perfil `Respons�vel` (somente consulta).
- Exibe cards com foto dos aventureiros vinculados ao respons�vel logado.
- Ao clicar no card, abre o hist�rico completo de eventos daquele aventureiro, mostrando se estava `Presente` ou `Ausente` em cada evento.
- Mantida a tela de marca��o de presen�a para perfis administrativos (`Diretor/Diretoria`).
- Bloqueada no backend a API de marcar presen�a (`toggle`) para perfil `Respons�vel`.
## 25/02/2026 - Loja (Diretoria) UX: formul�rio em bot�o expans�vel e lista compacta de produtos

- O cadastro de novo produto na `Loja` (modo diretoria/admin) foi colocado dentro de um bloco expans�vel `Cadastrar novo produto`, reduzindo polui��o visual da tela.
- O formul�rio continua o mesmo (campos, varia��es, fotos e JS), apenas com abertura/fechamento por clique.
- `Produtos cadastrados` deixou de usar cards grandes e passou para uma lista compacta em uma linha por produto.
- Ao clicar na linha, o produto expande para mostrar detalhes (foto, descri��o, regras e varia��es com fotos vinculadas).
- Objetivo: melhorar leitura no desktop e no celular sem alterar a l�gica de cadastro atual.
## 25/02/2026 - Loja (Diretoria): edi��o de produto e painel de pedidos com pagamento/entrega

- Adicionada edi��o de produto cadastrado no modo diretoria (dados principais): t�tulo, descri��o, status ativo/inativo e m�nimo de pedidos pagos.
- A edi��o fica dentro do detalhe do produto na lista compacta de `Produtos cadastrados`.
- Criado painel `Pedidos` na `Loja` (diretoria), com lista compacta de todos os pedidos feitos.
- Cada pedido mostra resumo por linha (respons�vel, se est� pago/n�o pago, valor total) e, ao clicar, abre detalhes do pedido.
- Nos detalhes do pedido, passa a aparecer tamb�m o status de entrega (`Entregue` / `N�o entregue`) e bot�o para marcar/desmarcar entrega.
- Adicionado campo `entregue` em `LojaPedido` para controle de entrega no sistema.
## 26/02/2026 - Hotfix Loja: campo `entregue` corrigido no model de pedido

- Corrigido erro de modelagem que colocou o campo `entregue` no model `PagamentoMensalidade` em vez de `LojaPedido`.
- A tela `Loja` (modo diretoria) passou a usar novamente o campo correto de entrega do pedido sem gerar erro 500.
- Mantida a migra��o `0037_lojapedido_entregue` (sem nova migra��o, apenas alinhamento do model ao estado correto).

## 26/02/2026 - Hardening de deploy e debug (prevencao de drift de banco/migrations)

- O script `deploy/deploy.sh` agora executa `makemigrations --check --dry-run` antes do `migrate`.
- Com isso, o deploy falha cedo se houver alteracao de model sem migration versionada no Git.
- Adicionada validacao de schema da Loja apos migracoes: se a tabela `accounts_lojapedido` existir, a coluna `entregue` passa a ser obrigatoria; se faltar, o deploy interrompe com mensagem clara.
- README atualizado com orientacao obrigatoria para comandos manuais no VPS: carregar `/etc/sitepinhal.env` antes de rodar `manage.py`.
- `CHECKLIST_DEBUG.md` atualizado com o mesmo alerta para evitar diagnostico em banco errado.

## 26/02/2026 - Apostila para Diretor e Professor (classes + cadastro de requisitos)

- Criado novo menu `Apostila` com permiss�o dedicada no sistema.
- O bot�o `Apostila` foi adicionado na sidebar e na matriz de permiss�es (grupos e usu�rio).
- Implementada a rota `accounts:apostila` com tela exclusiva para perfis ativos `Diretor` e `Professor`.
- A tela mostra bot�es por classe (`Abelhinhas`, `Luminares`, `Edificadores`, `M�os Ajudadoras`) e total de requisitos por classe.
- Em cada classe, foi adicionado o bot�o/formul�rio `Cadastrar requisito` com os campos:
  - n�mero do requisito
  - descri��o
  - resposta (opcional)
- Criado o model `ApostilaRequisito` com persist�ncia em banco, autoria e ordena��o por classe/n�mero.
- Criada a migration `0038_apostilarequisito` com ajuste autom�tico dos grupos padr�o para incluir o menu `apostila` em `diretor` e `professor`.

## 26/02/2026 - Apostila: dicas por requisito e subrequisitos (A, B, C...)

- Cada requisito da Apostila agora possui campo `dicas` (opcional).
- Implementado novo cadastro de `subrequisitos` por requisito, com:
  - c�digo do subrequisito (ex.: A, B, C)
  - descri��o
  - resposta (opcional)
- A tela de Apostila foi atualizada para exibir:
  - dicas do requisito
  - lista dos subrequisitos vinculados ao requisito
  - formul�rio de cadastro de subrequisito dentro de cada requisito
- Criada nova tabela/model `ApostilaSubRequisito` com v�nculo ao requisito e bloqueio de c�digo duplicado no mesmo requisito.
- Criada migration `0039_apostilasubrequisito_apostilarequisito_dicas` para adicionar `dicas` em requisito e criar subrequisitos.

## 26/02/2026 - Apostila: foto no requisito, multiplas dicas e arquivos por dica

- Adicionada foto opcional em cada requisito da apostila (`foto do requisito`), exibida junto ao card do requisito.
- O cadastro de requisito passou a aceitar upload de imagem.
- Implementado cadastro de m�ltiplas dicas por requisito (n�o apenas um texto �nico).
- Cada dica agora permite anexar m�ltiplos arquivos.
- A tela da apostila passou a exibir lista de dicas por requisito e links dos arquivos anexados em cada dica.
- Criados os novos models `ApostilaDica` e `ApostilaDicaArquivo`.
- Criada migration `0040_apostiladica_apostiladicaarquivo_and_more` para incluir `foto_requisito` e as novas tabelas de dicas/arquivos.

## 26/02/2026 - Apostila UX: fluxo guiado por passos e bot�es mais claros

- Tela da Apostila recebeu bloco `Passo a passo` para orientar o usu�rio final.
- Mensagens e r�tulos foram simplificados com foco em a��o:
  - `Adicionar novo requisito` / `Salvar requisito`
  - `Adicionar dica neste requisito` / `Salvar dica`
  - `Adicionar subrequisito neste requisito` / `Salvar subrequisito`
- Formul�rio de requisito ficou aberto por padr�o para reduzir cliques e facilitar o in�cio do fluxo.
- Inclu�das dicas contextuais em cada etapa para reduzir d�vida durante o uso.

## 26/02/2026 - Apostila UX: removida op��o de subrequisito da interface

- Removida da tela da Apostila a se��o `Adicionar subrequisito neste requisito`.
- Tamb�m foi removida a listagem visual de subrequisitos para simplificar o fluxo ao usu�rio final.
- O passo a passo no topo foi atualizado para focar apenas em `requisito` e `dicas`.

## 26/02/2026 - Apostila UX: clique na foto do requisito abre visualizacao ampliada

- A foto cadastrada no requisito agora abre em tamanho maior ao clicar.
- Implementado modal responsivo (desktop e celular) com:
  - titulo do requisito
  - botao fechar
  - fechamento por clique no fundo
  - fechamento por tecla `Esc`
- Objetivo: facilitar a leitura da imagem sem perder contexto da tela.

## 26/02/2026 - Apostila UI: formul�rios em janelas suspensas responsivas

- A tela da Apostila foi reorganizada para reduzir polui��o visual sem sair do padr�o do sistema.
- O cadastro de requisito saiu do bloco fixo e agora abre em modal responsivo (`Adicionar novo requisito`).
- O cadastro de dica tamb�m passou para modal responsivo por requisito (`Adicionar dica neste requisito`).
- Mantido o modal de foto ampliada do requisito.
- Melhorias de usabilidade:
  - menos rolagem na tela principal
  - foco no conte�do dos requisitos
  - fechamento de modais por bot�o, clique no fundo e tecla `Esc`
  - reabertura autom�tica do modal de requisito/dica quando h� erro de valida��o

## 27/02/2026 - Apostila UX: edicao de requisito e conteudo recolhido por clique

- Implementada acao editar_requisito no backend da Apostila com validacao de classe/requisito, atualizacao de numero, descricao, resposta e foto.
- Adicionado suporte para remover foto atual do requisito durante a edicao.
- A lista de requisitos foi alterada para abrir os dados somente ao clicar no item (cards recolhidos por padrao).
- Dentro de cada requisito, os blocos Resposta e Dicas passaram a ficar minimizados por padrao, com abertura sob demanda.
- Criado modal responsivo Editar requisito, preenchido automaticamente ao clicar no botao Editar requisito da linha.


## 27/02/2026 - Apostila UI: removida frase auxiliar no topo da classe

- Removido o texto "Abra o cadastro em janela suspensa para manter a tela organizada." da tela da Apostila.
- Mantido apenas o botao Adicionar novo requisito no topo da secao da classe.

## 28/02/2026 - Usuarios: separacao por categoria e acesso ao cadastro completo

- Tela Usuarios reorganizada em 3 categorias clicaveis: Diretoria, Responsaveis e Aventureiros.
- Cada categoria agora lista somente os registros correspondentes e mostra contagem por grupo.
- Adicionado botao Ver cadastro completo em cada linha para abrir os dados detalhados do registro selecionado.
- Para Aventureiros, a listagem usa todos os aventureiros cadastrados e linka para o detalhe individual.
- O detalhe de usuario (usuario_detalhe.html) foi ampliado para exibir os campos completos de Diretoria e Responsavel.
- Ajustado o acesso ao detalhe de aventureiro para permitir abertura tambem quando o usuario veio pelo modulo Usuarios.

## 28/02/2026 - Perfis controlados por Permissoes (grupos)

- A regra de perfis ativos passou a considerar apenas os grupos marcados em Permissoes.
- Removida a heranca automatica de perfil por existencia de cadastro Diretoria/Responsavel.
- Sincronizacao de UserAccess.profiles agora usa somente os codigos dos grupos vinculados ao usuario.
- Cadastro novo de diretoria agora vincula automaticamente o grupo diretoria e sincroniza perfis.
- Cadastro novo de responsavel continua vinculando responsavel, com sincronizacao de perfis por grupo.
- Tela de Usuarios e usuario_detalhe agora exibem perfis calculados pela regra de grupos.


## 28/02/2026 - Classificacao de aventureiros: abaixo de 6 anos em Abelhinhas

- Ajustada a regra de classificacao para que qualquer crianca com idade real abaixo de 6 anos seja classificada em Abelhinhas.
- Removida a regra anterior de corte em 30/06 para esse caso.

## 28/02/2026 - Financeiro: robustez no Pix e opcao de pagar ano todo

- Ajustado o fluxo de criacao de pagamento Pix de mensalidades para reduzir falhas na geracao de QR Code.
- O sistema agora tenta reconsultar o pagamento no Mercado Pago quando o retorno inicial nao traz transaction_data completo.
- O pagamento nao falha mais apenas por ausencia de qr_code_base64 quando o pix_code existe.
- Adicionada opcao no perfil Responsavel para incluir mensalidades futuras do ano atual na listagem de pagamento.
- Com essa opcao marcada, fica possivel pagar todas as mensalidades pendentes do ano de uma vez.
- Incluidos botoes Selecionar todas e Limpar para agilizar a selecao em lote das mensalidades.


## 01/03/2026 - Financeiro: diagnostico e resiliencia no pagamento Pix de mensalidades

- Melhorado o cliente do Mercado Pago para tratar melhor falhas de conexao e timeout no inicio do pagamento Pix.
- Adicionado retry automatico (2 tentativas) para erros de rede antes de falhar a criacao do pagamento.
- Erros HTTP do Mercado Pago agora exibem mensagem mais completa (incluindo causa quando enviada pela API).
- Quando ocorre falha inesperada ao iniciar pagamento, o sistema grava log tecnico e mostra detalhe resumido na tela.


## 01/03/2026 - Financeiro: correcao do campo entregue em PagamentoMensalidade

- Corrigido erro ao iniciar pagamento de mensalidades: NOT NULL constraint failed: accounts_pagamentomensalidade.entregue.
- Adicionado campo entregue no model PagamentoMensalidade com default False para garantir insert consistente.
- Criada migration de guarda (0041_pagamentomensalidade_entregue_guard) para alinhar bancos com drift.
- Se a coluna entregue ja existe, normaliza valores nulos para 0.
- Se a coluna nao existe, cria com NOT NULL e default seguro.
- Com isso, o fluxo de geracao de pagamento Pix em mensalidades volta a funcionar sem ajuste manual no banco.

## 01/03/2026 - Eventos: exclusao com senha de override apos data/hora

- Mantido o bloqueio padrao de exclusao para eventos cuja data/hora ja foi atingida.
- Adicionada excecao por senha: ao excluir evento passado, o sistema pede senha e permite excluir quando a senha informada for pinhal.
- Incluido campo oculto de senha no formulario de exclusao e prompt no frontend somente para eventos que ja passaram.
- Backend validando a senha antes de excluir, com mensagem clara quando a senha nao e informada ou esta incorreta.

## 01/03/2026 - Pontos: lancamento por classe

- No modulo Pontos, o destino do lancamento agora aceita tres modos: Individual, Por classe e Todos os aventureiros.
- Adicionado seletor de classe (Abelhinhas, Luminares, Edificadores e Maos Ajudadoras) para aplicar pontos em lote por classe.
- Backend atualizado para calcular a classe do aventureiro pela mesma regra de idade do sistema e criar os lancamentos em massa da classe selecionada.
- Mensagens de retorno ajustadas para confirmar quantidade de aventureiros afetados por classe.
- Interface ajustada para mostrar apenas os campos relevantes conforme o modo de destino selecionado.

## 01/03/2026 - Cadastro Diretoria: layout alinhado e validacoes revisadas

- Fluxo novo de diretoria atualizado para o mesmo padrao visual do cadastro de aventureiro nas telas de login, compromisso, termo e resumo.
- Tela de login da diretoria agora usa formulario especifico (sem quantidade de aventureiros), corrigindo erro de validacao que impedia avancar.
- Reforcadas validacoes no compromisso: escolaridade obrigatoria, e-mail valido e data de nascimento valida.
- Reforcada validacao no termo de imagem: e-mail de contato obrigatoriamente valido.
- Ajustado tratamento de saude para limpar descricao quando a opcao for nao.

## 01/03/2026 - Presenca (admin): ampliacao de foto do aventureiro

- Na tela de Presenca para perfis administrativos, a miniatura da foto do aventureiro agora pode ser clicada para abrir em tamanho grande.
- Adicionada janela suspensa responsiva com foto ampliada, titulo e botao fechar.
- Fechamento da janela por botao, clique fora da imagem e tecla Esc.
- Alteracao aplicada somente no modo de marcacao de presenca (nao afeta a visao do perfil responsavel).

## 01/03/2026 - Presenca (admin): busca com sugestao ao digitar

- No campo Buscar aventureiro da tela de Presenca (admin), a pesquisa agora mostra sugestoes automaticamente enquanto voce digita.
- As sugestoes consideram nome do aventureiro, nome do responsavel e username vinculado.
- Mantido o filtro em tempo real da lista para nao alterar o fluxo atual de marcacao de presenca.



## 01/03/2026 - Presenca (admin): busca sem acento e sem caractere especial

- Ajustada a pesquisa da Presenca (admin) para ignorar acentos e caracteres especiais no texto digitado.
- Exemplo: ao digitar perola, o sistema tambem encontra P�rola.
- Mantido o autocomplete e o filtro em tempo real da lista.

## 01/03/2026 - Presenca (admin): modal de falta inscricao com foto

- Adicionado botao Falta inscricao na tela de Presenca (modo administrativo).
- Ao clicar, abre uma janela suspensa para registrar nome e foto de quem esta sem inscricao no evento selecionado.
- O campo de foto aceita captura direta da camera no celular (input com capture).
- Na mesma janela, agora aparece a lista dos ja cadastrados de falta inscricao para o evento.
- Adicionado endpoint de API para listar e cadastrar esses registros sem recarregar a tela.

## 01/03/2026 - Presenca (admin): upload mais rapido no falta inscricao

- Melhorado o envio de foto no modal Falta inscricao com otimizacao da imagem antes do upload.
- Fotos grandes agora sao redimensionadas e comprimidas no navegador antes de enviar ao servidor.
- Mantido fallback automatico para envio original caso a otimizacao nao seja possivel.
- Resultado: menos tempo de upload em conexoes moveis e menor chance de lentidao ao salvar.

## 01/03/2026 - Presenca (admin): foto ampliada acima do modal de falta inscricao

- Ajustada a camada (z-index) da janela de foto ampliada para abrir por cima da janela Falta inscricao.
- Agora, ao clicar na foto em Falta inscricao, a imagem ampliada fica visivel corretamente para melhor visualizacao.

## 01/03/2026 - Menu lateral no celular: inicia minimizado e recolhe apos clique

- Ajustado o menu lateral para abrir minimizado por padrao em telas de celular.
- Adicionado botao Menu/Fechar no topo da barra lateral para expandir e recolher manualmente.
- Ao tocar em qualquer item do menu no celular, o menu recolhe automaticamente para nao atrapalhar a visualizacao.
- No desktop, o comportamento continua expandido normalmente.

## 01/03/2026 - Menu lateral mobile/tablet: correcao de carregamento inicial

- Corrigido o comportamento para mobile e tablet: agora o menu inicia fechado ao abrir ou atualizar a pagina.
- Ajustado breakpoint para incluir tablet (ate 1100px) com o mesmo comportamento de menu recolhido.
- No desktop, a barra lateral permanece fixa e aberta com os menus visiveis.

## 01/03/2026 - Menu lateral mobile/tablet: fix robusto de abrir/fechar

- Reforcado controle do menu lateral no proprio JavaScript para esconder/mostrar os blocos do sidebar mesmo com cache antigo de CSS.
- Adicionado controle por hidden nos blocos do menu e dados de perfil conforme estado aberto/fechado.
- Botao Menu/Fechar e recolhimento apos clique agora funcionam de forma consistente em celular e tablet.

## 01/03/2026 - Sidebar mobile/tablet: botao Menu/Fechar maior e com visual melhorado

- Aumentado tamanho do botao Menu/Fechar para facilitar o toque no celular e tablet.
- Ajustado visual com gradiente, cantos mais arredondados e sombra para melhor destaque.
- Adicionados estados de hover/active para feedback visual mais claro.

## 01/03/2026 - Mensalidades: gerar desde o mes passado para inscricoes recentes

- Ajustada a geracao de mensalidades para considerar inscricao no mes passado.
- Quando o aventureiro foi inscrito no mes passado e ainda nao existe cobranca daquele mes, a geracao inicia no mes passado.
- Mantido o comportamento atual para os demais casos (inicio no mes atual).
- Regra aplicada tanto na geracao individual quanto em Gerar para todos (mesmo helper).

## 02/03/2026 - Financeiro: evita mensagem WhatsApp duplicada em pagamento aprovado

- Corrigido envio de confirmacao de pagamento de mensalidades para disparar apenas uma vez por pagamento aprovado.
- Adicionado lock transacional no pagamento para evitar corrida entre webhook e consulta de status (polling) que podia gerar mensagem duplicada.
- Se nenhum envio for concluido com sucesso, o marcador de notificacao e liberado para permitir nova tentativa depois.

## 05/03/2026 - Usuarios: diretor define telefone WhatsApp do responsavel na edicao

- Na tela de edicao de usuario, quando o perfil possui cadastro de responsavel, foi adicionada secao para definir qual telefone sera usado no envio de WhatsApp.
- O diretor pode escolher: modo automatico, um dos telefones do cadastro (responsavel/mae/pai) ou informar telefone manual.
- O telefone escolhido passa a ser salvo em `WhatsAppPreference.phone_number`, que tem prioridade no envio (inclusive na recuperacao de senha).
- Incluida exibicao do telefone efetivo atual e registro em auditoria da alteracao realizada.

## 05/03/2026 - Usuarios: atalhos visiveis para editar permissoes e WhatsApp

- Adicionado atalho `Editar permissoes/WhatsApp` na listagem de Usuarios (Diretoria e Responsaveis).
- Adicionado o mesmo atalho no topo da tela de detalhe do usuario.
- Objetivo: facilitar acesso ao ponto onde o diretor define o telefone de WhatsApp do responsavel.

## 05/03/2026 - Usuarios: selecao explicita do telefone principal de WhatsApp

- A tela de edicao de usuario (responsavel) passou a mostrar as opcoes de telefone em lista com selecao direta de principal.
- As opcoes aparecem por origem (celular/telefone de responsavel, mae e pai), com indicacao quando nao ha numero cadastrado.
- Mantida opcao de telefone manual, agora com habilitacao automatica apenas quando a opcao manual estiver marcada.

## 08/03/2026 - Financeiro: relatorios para diretor com bruto e liquido

- Adicionada aba `Relatorios` no modulo Financeiro quando o perfil ativo e Diretor.
- A nova visao lista pagamentos de mensalidades pagos e pedidos pagos da loja.
- Incluidos cards de totais com `Caixa bruto` (mensalidades pagas + pedidos pagos da loja) e `Caixa liquido` (apenas mensalidades pagas).
- Regra aplicada: pedidos da loja entram no bruto, mas nao somam no saldo liquido do caixa.

## 08/03/2026 - Cadastro diretoria: novos usuarios entram tambem como professor

- Ajustado o cadastro novo de diretoria para vincular automaticamente os grupos `diretoria` e `professor`.
- Com isso, novos usuarios de diretoria passam a receber tambem o perfil e as permissoes de professor.
- O fluxo legado de cadastro de diretoria tambem passou a marcar o perfil `professor` junto com `diretoria`.

## 08/03/2026 - Loja: perfil professor com acesso de compra como responsavel

- O perfil `professor` passou a enxergar o menu `Loja`.
- O fluxo de catalogo, carrinho, Pix e consulta de status da loja foi liberado tambem para o perfil `professor`.
- Quando o usuario professor nao possui cadastro de responsavel, o sistema cria automaticamente um cadastro auxiliar a partir dos dados da diretoria para viabilizar os pedidos da loja.
- Objetivo: permitir que usuarios de diretoria/professor tambem comprem na loja com fluxo igual ao de responsavel.

## 08/03/2026 - Permissoes: cabecalho fixo nas tabelas com rolagem

- Ajustado o CSS das tabelas `Usuarios por grupo` e `Excecao por usuario` para manter o cabecalho visivel durante a rolagem.
- O cabecalho agora fica fixo no topo da area rolavel, facilitando identificar os grupos e menus enquanto navega pela lista.

## 13/03/2026 - WhatsApp: notificacao de pedido da loja pago com destinatarios dedicados

- Adicionada nova categoria de notificacao Loja no modulo WhatsApp, com coluna propria para marcar os usuarios que receberao alerta de pedido da loja pago.
- Incluido template padrao especifico para pedido da loja pago na tela de configuracao do WhatsApp.
- O envio de pedido da loja aprovado agora usa preferencia e fila proprias (notify_loja / TYPE_LOJA).
- Mantido o fluxo financeiro separado: pagamento de mensalidades continua usando notify_financeiro / TYPE_FINANCEIRO.

## 13/03/2026 - WhatsApp Loja: envio apenas para diretoria responsavel

- O aviso de pedido da loja pago deixou de ser enviado automaticamente para quem realizou o pagamento.
- Agora o envio considera apenas usuarios da diretoria/diretor marcados na coluna Pedido loja pago.
- Confirmado que o fluxo de pedido da loja usa template e tipo Loja (nao usa a mensagem de Pagamento aprovado).
- Atualizado o texto da tela de WhatsApp para refletir esse comportamento.

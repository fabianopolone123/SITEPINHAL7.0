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

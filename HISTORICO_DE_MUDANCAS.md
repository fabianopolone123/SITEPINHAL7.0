# Histórico de Mudanças

Este arquivo registra tudo que já foi concluído no projeto.
Ele é a memória oficial do sistema.

---

## Fase 1 – MVP (Login e Cadastro)

### Planejado
- [ ] Estrutura inicial do projeto
- [ ] App accounts criado
- [ ] Login funcionando
- [ ] Cadastro funcionando
- [ ] Dashboard protegido
- [ ] Deploy no VPS

---

## Regras
- Toda mudança deve ser registrada aqui
- Marcar itens concluídos com [x]
- Criar nova fase quando o escopo mudar

### 03/02/2026 – Login inicial
- [x] Criado template `ui/templates/login.html` com campo de usuário/senha, botões e área de status.
- [x] Adicionados estilos responsivos (`ui/static/css/styles.css`) e script de validação simulada (`ui/static/js/login.js`).
- [x] Logo movido para `ui/static/images/logo.jpeg` e README atualizado para facilitar testes locais.

### 03/02/2026 – Interface de cadastro revisada
- [x] `ui/templates/register.html` agora apresenta apenas dois botões (Aventureiro e Diretoria) como próxima etapa pós-“Cadastre-se”.
- [x] Estilos (`ui/static/css/styles.css`) ajustados para os cartões de opção.
- [x] README atualizada para explicar como testar a tela de seleção.

### 03/02/2026 – Tela de responsáveis
- [x] Criada `ui/templates/responsavel.html` com campos para pai, mãe, responsável legal e endereço.
- [x] Adicionado `ui/static/js/responsavel.js` para garantir ao menos um responsável e mostrar feedback visual.
- [x] Estilos (`ui/static/css/styles.css`) atualizados para os cartões de seção e o layout do formulário.

### 03/02/2026 – Formulário do aventureiro
- [x] Criado `ui/templates/aventura.html` com todos os blocos exigidos — dados pessoais, documentos, ficha médica, alergias, condições, deficiências, declarações e termo de uso de imagem.
- [x] Adicionado `ui/static/js/aventura.js` para feedback após preencher o nome do aventureiro.
- [x] Estilizado o formulário com grids responsivos (row-grid, inline-grid e checkbox-grid) para manter a organização nas diferentes larguras (`ui/static/css/styles.css`).

### 03/02/2026 – Ajuste de layout de questões
- [x] `.inline-grid` e `.inline-space` atualizados para garantir que as perguntas “Utiliza medicamentos?” e similares quebrem corretamente e fiquem alinhadas dentro do grid.

### 03/02/2026 – Recriação completa da tela de aventureiro
- [x] Formulário refeito (`ui/templates/aventura.html`) agora segue o roteiro completo “Ficha cadastral e médica – Clube de Aventureiros”, com cada número e campo solicitados.
- [x] CSS mantém os cards, campos e question rows alinhados, sem split layout, usando os estilos já adotados nos outros formulários.
- [x] README descreve o novo fluxo feito por blocos numerados e caixas finais de aceite.
- [x] Termo de imagem e declaração médica seguem com textos oficiais (checkbox obrigatória).
- [x] A ficha médica repete o aviso “Já teve ou tem (marque apenas as opções positivas)” antes da lista de doenças.
- [x] Condições e alergias têm radios Seguidos de “Se sim, qual?” conforme o roteiro e também os campos “Utiliza medicamentos”.
- [x] Perguntas “Utiliza remédios?” adicionam novos campos para registrar o nome do remédio quando a resposta for sim.
- [x] Botões de ação ao final agora oferecem “Salvar e concluir” e “Adicionar outro aventureiro”.
- [x] Botão “Assinar” abre modal com canvas, salvar/limpar e preview (`ui/static/js/signature.js`, `ui/static/css/styles.css`), agora com validação contra assinaturas encostando na borda.
- [x] Tela de assinatura também presente em `aventura.html`, com preview e modal compartilhados entre os dois formulários.
- [x] Criada `confirmacao.html` para revisar responsável e aventureiros antes de finalizar o cadastro.
- [x] Preview da assinatura ocupa 100% da largura do card do formulário, garantindo consistência com a tela (`ui/static/css/styles.css`).

### 03/02/2026 – Credenciais no responsável
- [x] Incluída a seção “Acesso ao portal” no topo do formulário `ui/templates/responsavel.html` com os campos `username` e `password`, alinhando o cadastro do responsável com o restante das etapas.
- [x] Acrescentado campo “Repita a senha” para confirmar o cadastro da senha no mesmo formulário, reforçando a validação antes de enviar.

### 03/02/2026 – Backend Django inicial
- [x] Criado `backend/` com Django, models de `Responsavel` e `Aventureiro`, SQLite e armazenamento das assinaturas PNG em `backend/media/signatures`.
- [x] Views `/responsavel/`, `/aventura/`, `/confirmacao/` e login/logout tratam os formulários, protegem a área dos aventureiros e exibem o resumo final para o responsável autenticado.
- [x] Templates foram ajustados (`{% static %}`, `{% csrf_token %}`, actions apontam para as URLs nomeadas) e os scripts validam apenas os campos obrigatórios antes de permitir o envio ao backend.
- [x] Template de responsáveis agora repovoa os campos após erro e mostra mensagens específicas (`field-error`) de cada campo com falha.
- [x] Formulário do aventureiro exige nome completo do aventureiro, documentos válidos (certidão ou CPF ou RG+órgão), plano de saúde e tipo sanguíneo obrigatórios, camisetas em lista fixa e geração de erros inline para guiar o preenchimento.
- [x] Campos com erro agora recebem bordas vermelhas (`input-error`), tornando visível o bloqueio quando o backend recusa o envio (documentação, ficha médica, tipo sanguíneo e declarações ficam destacados).
- [x] Os campos de dados pessoais obrigatórios (`sexo`, `religião`, nascimento, série e colégio) e todas as perguntas de condições de saúde/alergias agora exigem “sim” ou “não” com validação visual; o backend sinaliza quais inputs travam o avanço.
- [x] O template do formulário do aventureiro preserva os valores de texto e radios após falhas, evitando que o usuário precise reescrever tudo quando um campo bloqueia o avanço.
- [x] A pergunta “Beneficiário do Bolsa Família” também passou a ser obrigatória com destaque visual, garantindo que o sim/não seja selecionado antes de concluir.

### 04/02/2026 – Fluxo final e botões ativos
- [x] Botão principal renomeado para “Salvar e confirmar”: validação continua igual (incluindo o alerta visual e as mensagens de campo), mas agora redireciona direto para `/confirmacao/`, onde o responsável finaliza clicando em “Salvar tudo” e, só então, os dados são gravados no banco.
- [x] “Adicionar outro aventureiro” ainda limpa a ficha após validações e incrementa o contador, porém só funciona quando a ficha atual está salva para revisão (ele passou a se comportar como uma extensão da revisão, não como um avanço obrigatório).
- [x] O backend registra as fichas válidas em sessão, a confirmação exibe os pendentes e o botão “Salvar tudo” transforma esse buffer em registros permanentes antes de fazer logout; o checklist foi atualizado com `python backend/manage.py check`.
- [x] As datas dos aventureiros agora são serializadas com `isoformat()` ao ir para a sessão e reconvertidas com `date.fromisoformat()` antes de salvar definitivamente, evitando o erro “date is not JSON serializable”.
- [x] O buffer de fichas pendentes filtra apenas os campos do modelo (`AVENTUREIRO_FIELDS`) antes de instanciar `Aventureiro`, limpando atributos extras como `cardiaco_remedio` e evitando o `TypeError` na confirmação.
- [x] Adicionado o campo obrigatório de foto 3x4 com preview + campo escondido; a validação exige a foto antes de “Salvar e confirmar” ou “Adicionar outro aventureiro”, e a imagem é armazenada temporariamente na sessão e salva definitivamente junto com o aventureiro na confirmação final.
- [x] “Voltar para editar” foi removido da tela de confirmação para evitar voltar ao formulário depois que os dados já estão pendentes, deixando o “Salvar tudo” como único ponto de saída.
- [x] A lista de aventureiros pendentes agora exibe a foto 3x4 enviada em cada cartão para facilitar a revisão antes da confirmação.
- [x] O buffer de fichas pendentes armazena somente os campos do modelo `Aventureiro`, filtrando campos como condições/alergias individuais para evitar `TypeError` ao criar a instância na confirmação.

### 04/02/2026 – Preparação para deploy (VPS)
- [x] Atualizado `backend/config/settings.py` para suportar variáveis de ambiente (SECRET_KEY, DEBUG, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS) e paths configuráveis para SQLite, `MEDIA_ROOT` e `STATIC_ROOT`.
- [x] Atualizado `backend/requirements.txt` para Django 5.2 (LTS) e adicionado `gunicorn` para execução em produção.
- [x] Adicionados templates de deploy em `deploy/` (exemplo de env, unit do systemd, config do nginx e script simples de deploy).

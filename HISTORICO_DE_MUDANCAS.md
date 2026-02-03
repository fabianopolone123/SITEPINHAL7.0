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
- [x] Preview da assinatura ocupa 100% da largura do card do formulário, garantindo consistência com a tela (`ui/static/css/styles.css`).

# Sistema Atual - estado consolidado

Objetivo deste arquivo: permitir que um novo chat/novo dev entenda rapidamente o sistema atual sem depender de historico conversacional.

## Stack e operacao

- Backend: Django
- Frontend: Django Templates + CSS + JavaScript vanilla
- Banco atual: SQLite
- Midia: `media/` (fotos, assinaturas, fundos de documentos, documentos gerados)
- Deploy: VPS Linux com Gunicorn + Nginx + `deploy/deploy.sh`

## Modulos ativos

1. Cadastro novo de aventureiro (fluxo multi-etapas)
- etapa de login inicial do responsavel (`username`, `senha`, `confirmacao`)
- ficha de inscricao
- ficha medica
- declaracao medica
- termo de imagem
- resumo com opcoes: adicionar outro aventureiro ou finalizar
- persistencia definitiva somente na finalizacao

2. Cadastro novo de diretoria (fluxo multi-etapas)
- etapa de login da diretoria
- compromisso voluntariado
- termo de imagem
- resumo e finalizacao

3. Fluxo legado (mantido)
- rotas antigas de responsavel/aventura/confirmacao/diretoria ainda existem para compatibilidade

4. Painel logado
- menu lateral dinamico por permissao
- inicio
- meus dados
- aventureiros (visao geral para perfil com permissao)
- usuarios
- permissoes
- whatsapp
- documentos inscricao
- eventos

5. Permissoes
- perfis por usuario em `UserAccess` (suporta multiplos perfis)
- grupos de acesso em `AccessGroup`
- permissoes por menu no grupo
- excecao individual por usuario (`menu_allow`) sobrescreve o grupo

6. WhatsApp
- preferencias por usuario destino
- modelos de mensagem (cadastro e teste)
- fila de envio (`WhatsAppQueue`)
- comando de processamento com pausa configuravel (padrao 2s)
- notificacao automatica em cadastro concluido

7. Documentos de inscricao
- templates com fundo e posicionamento de campos
- geracao de documento preenchido por aventureiro/responsavel
- visualizacao e exclusao de documento gerado

8. Eventos
- criacao de evento com nome/data/hora obrigatorios
- campos extras dinamicos por evento
- suporte a pre-configuracoes (`EventoPreset`)
- indicador temporal na lista (hoje, amanha, em X dias, etc)
- exclusao somente antes do horario do evento

## Modelos principais (accounts)

- `Responsavel`
- `Aventureiro`
- `AventureiroFicha`
- `Diretoria`
- `DiretoriaFicha`
- `UserAccess`
- `AccessGroup`
- `WhatsAppPreference`
- `WhatsAppTemplate`
- `WhatsAppQueue`
- `DocumentoTemplate`
- `DocumentoInscricaoGerado`
- `Evento`
- `EventoPreset`

## Regras de dados e fluxo

1. Novo cadastro:
- dados ficam em sessao durante o fluxo
- gravacao no banco ocorre no fechamento/finalizacao

2. Assinaturas:
- cada assinatura e guardada separadamente por etapa/ficha
- assinatura precisa manter vinculo com a pessoa correta para impressao posterior

3. Validacoes:
- frontend ajuda com feedback visual
- backend mantem validacao final

## Regras de processo (equipe)

1. Toda alteracao exige commit e push.
2. Toda alteracao concluida deve entrar no `HISTORICO_DE_MUDANCAS.md`.
3. Commit deve seguir o padrao:
   - `<arquivo_principal>: <descricao objetiva>`

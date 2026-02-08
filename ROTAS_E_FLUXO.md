# Rotas e Fluxo - mapa atual

## Publicas

- `/` -> redireciona para login
- `/login/` -> login
- `/logout/` -> logout + redireciona para login
- `/register/` -> escolha do tipo de cadastro

## Novo cadastro - Aventureiro

- `/novo-cadastro/login/`
- `/novo-cadastro/inscricao/`
- `/novo-cadastro/verificar-documento/` (validacao de documento)
- `/novo-cadastro/medica/`
- `/novo-cadastro/declaracao-medica/`
- `/novo-cadastro/termo-imagem/`
- `/novo-cadastro/resumo/`

Fluxo:

1. cria login do responsavel (temporario na sessao);
2. preenche fichas em etapas;
3. pode adicionar outro aventureiro;
4. finaliza e grava no banco.

## Novo cadastro - Diretoria

- `/novo-cadastro-diretoria/login/`
- `/novo-cadastro-diretoria/compromisso/`
- `/novo-cadastro-diretoria/termo-imagem/`
- `/novo-cadastro-diretoria/resumo/`

## Rotas legadas (mantidas)

- `/responsavel/`
- `/diretoria/`
- `/aventura/`
- `/confirmacao/`

Alias legados explicitos:

- `/legacy/responsavel/`
- `/legacy/diretoria/`
- `/legacy/aventura/`
- `/legacy/confirmacao/`

## Painel e modulos logados

- `/painel/`
- `/meus-dados/`
- `/meus-dados/responsavel/`
- `/meus-dados/responsavel/editar/`
- `/meus-dados/diretoria/`
- `/meus-dados/diretoria/editar/`
- `/meus-dados/aventureiro/<id>/`
- `/meus-dados/aventureiro/<id>/editar/`

- `/aventureiros-gerais/`
- `/aventureiros-gerais/<id>/`

- `/usuarios/`
- `/usuarios/<id>/`
- `/usuarios/<id>/editar/`

- `/permissoes/`
- `/whatsapp/`
- `/documentos/`
- `/documentos/inscricao-gerado/<id>/`
- `/documentos/gerar/<template_id>/<kind>/<pk>/`
- `/eventos/`

## Regras resumidas de permissao

1. Usuario autenticado precisa ter menu liberado para acessar cada modulo.
2. Permissoes base podem vir de grupo.
3. Excecao individual (`menu_allow`) pode sobrescrever.

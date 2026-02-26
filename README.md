# Clube de Aventureiros Pinhal Junior

Sistema Django para cadastro (responsavel, aventureiro e diretoria), painel interno, permissoes por menu, notificacoes WhatsApp, documentos e eventos.

## Documentacao principal

- `SISTEMA_ATUAL.md`: estado consolidado do sistema (modulos, entidades, regras e operacao).
- `ROTAS_E_FLUXO.md`: mapa de rotas e fluxo funcional atual.
- `CONTRIBUTING.md`: padrao de desenvolvimento, commits e checklist obrigatorio.
- `HISTORICO_DE_MUDANCAS.md`: memoria oficial de tudo que foi entregue.

## Rodar localmente (Windows / PowerShell)

```powershell
cd SITEPINHAL7.0
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python backend\manage.py migrate
python backend\manage.py runserver
```

## Deploy VPS (resumo)

- Arquivos de deploy em `deploy/`.
- Script principal: `deploy/deploy.sh` (alias comum no VPS: `sitepinhal-deploy`).
- Fluxo esperado do deploy: atualizar codigo, aplicar migracoes, coletar estaticos e reiniciar servicos.

### Comandos manuais no VPS (importante)

Sempre carregue o mesmo arquivo de ambiente do servico antes de rodar `manage.py`:

```bash
cd /srv/sitepinhal/current/backend
source /srv/sitepinhal/venv/bin/activate
set -a; source /etc/sitepinhal.env; set +a
python manage.py check
deactivate
```

Sem isso, o `manage.py` pode usar outro banco e gerar diagnostico incorreto.

## Regra operacional obrigatoria

Toda alteracao deve seguir este ciclo:

1. implementar e validar;
2. criar commit;
3. fazer push para o remoto;
4. registrar a entrega no `HISTORICO_DE_MUDANCAS.md`.

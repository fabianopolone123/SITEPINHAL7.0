import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import LojaPedido
from accounts.views import LojaView


class Command(BaseCommand):
    help = 'Sincroniza pedidos pendentes/processando da loja com Mercado Pago.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Janela em dias para buscar pedidos (padrao: 3).',
        )
        parser.add_argument(
            '--max-items',
            type=int,
            default=150,
            help='Quantidade maxima de pedidos por execucao (padrao: 150).',
        )
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Executa em loop continuo.',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=120,
            help='Intervalo em segundos no modo --watch (padrao: 120).',
        )

    def _run_once(self, *, days, max_items):
        cutoff = timezone.now() - timedelta(days=max(1, days))
        base_qs = (
            LojaPedido.objects
            .filter(
                status__in=[LojaPedido.STATUS_PENDENTE, LojaPedido.STATUS_PROCESSANDO],
                created_at__gte=cutoff,
                mp_payment_id__isnull=False,
            )
            .exclude(mp_payment_id='')
            .order_by('created_at', 'id')
        )
        if max_items > 0:
            pedidos = list(base_qs[:max_items])
        else:
            pedidos = list(base_qs)

        if not pedidos:
            self.stdout.write(self.style.WARNING('Nenhum pedido pendente/processando para sincronizar.'))
            return {
                'checked': 0,
                'changed': 0,
                'approved_now': 0,
                'failed': 0,
            }

        loja_view = LojaView()
        checked = 0
        changed = 0
        approved_now = 0
        failed = 0

        for pedido in pedidos:
            checked += 1
            previous_status = pedido.status
            try:
                payment_data = loja_view._get_mp_payment(str(pedido.mp_payment_id or '').strip())
                loja_view._sync_pedido_loja_from_mp(pedido, payment_data)
                pedido.refresh_from_db(fields=['status', 'paid_at'])
                if pedido.status != previous_status:
                    changed += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Pedido #{pedido.id}: {previous_status} -> {pedido.status}'
                        )
                    )
                if previous_status != LojaPedido.STATUS_PAGO and pedido.status == LojaPedido.STATUS_PAGO:
                    approved_now += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f'Pedido #{pedido.id}: falha na sincronizacao ({exc})')
                )

        return {
            'checked': checked,
            'changed': changed,
            'approved_now': approved_now,
            'failed': failed,
        }

    def handle(self, *args, **options):
        days = max(1, int(options.get('days') or 3))
        max_items = int(options.get('max_items') or 150)
        interval = max(15, int(options.get('interval') or 120))
        watch = bool(options.get('watch'))

        while True:
            started = timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S')
            self.stdout.write(f'[sync_loja_pagamentos] Inicio: {started}')
            result = self._run_once(days=days, max_items=max_items)
            self.stdout.write(
                self.style.SUCCESS(
                    (
                        '[sync_loja_pagamentos] Fim | '
                        f"checados={result['checked']} "
                        f"alterados={result['changed']} "
                        f"pagos_agora={result['approved_now']} "
                        f"falhas={result['failed']}"
                    )
                )
            )
            if not watch:
                break
            time.sleep(interval)

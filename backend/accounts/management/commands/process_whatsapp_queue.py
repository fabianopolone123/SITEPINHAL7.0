import time

from django.core.management.base import BaseCommand

from accounts.whatsapp import process_next_queue_item


class Command(BaseCommand):
    help = 'Processa fila de notificacoes WhatsApp com pausa entre envios.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Processa apenas um item da fila.')
        parser.add_argument('--sleep', type=float, default=2.0, help='Intervalo entre envios, em segundos.')
        parser.add_argument('--max-items', type=int, default=0, help='Limite de itens por execucao (0 = sem limite).')

    def handle(self, *args, **options):
        sleep_seconds = max(0.0, options['sleep'])
        max_items = max(0, options['max_items'])
        processed = 0

        while True:
            item = process_next_queue_item()
            if not item:
                if processed == 0:
                    self.stdout.write(self.style.WARNING('Fila vazia.'))
                break

            processed += 1
            if item.status == item.STATUS_SENT:
                self.stdout.write(self.style.SUCCESS(f'Enviado para {item.phone_number} ({item.notification_type}).'))
            else:
                self.stdout.write(self.style.ERROR(f'Falha para {item.phone_number}: {item.last_error}'))

            if options['once']:
                break
            if max_items and processed >= max_items:
                break
            time.sleep(sleep_seconds)

        self.stdout.write(self.style.SUCCESS(f'Processamento finalizado. Itens processados: {processed}.'))

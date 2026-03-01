from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


def signature_upload_to(instance, filename):
    prefix = 'signatures'
    role = getattr(instance, 'role_slug', filename)
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f"{prefix}/{role}/{timestamp}_{filename}" if filename else f"{prefix}/{role}/{timestamp}.png"


class UserAccess(models.Model):
    ROLE_RESPONSAVEL = 'responsavel'
    ROLE_DIRETORIA = 'diretoria'
    ROLE_DIRETOR = 'diretor'
    ROLE_PROFESSOR = 'professor'

    ROLE_CHOICES = [
        (ROLE_RESPONSAVEL, 'Responsável'),
        (ROLE_DIRETORIA, 'Diretoria'),
        (ROLE_DIRETOR, 'Diretor'),
        (ROLE_PROFESSOR, 'Professor'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='access')
    role = models.CharField('perfil de acesso', max_length=32, choices=ROLE_CHOICES, default=ROLE_RESPONSAVEL)
    profiles = models.JSONField('perfis de acesso', default=list, blank=True)
    menu_allow = models.JSONField('menus liberados por usuário', default=list, blank=True)
    menu_deny = models.JSONField('menus bloqueados por usuário', default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} ({", ".join(self.get_profiles_display())})'

    def has_profile(self, profile):
        current = set(self.profiles or [])
        if not current and self.role:
            current.add(self.role)
        return profile in current

    def add_profile(self, profile):
        current = set(self.profiles or [])
        if self.role:
            current.add(self.role)
        current.add(profile)
        self.profiles = sorted(current)
        if self.role not in current:
            self.role = profile

    def get_profiles_display(self):
        mapping = dict(self.ROLE_CHOICES)
        current = list(self.profiles or [])
        if not current and self.role:
            current = [self.role]
        return [mapping.get(item, item) for item in current]


class Responsavel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='responsavel')
    pai_nome = models.CharField('nome do pai', max_length=255, blank=True)
    pai_cpf = models.CharField('cpf do pai', max_length=32, blank=True)
    pai_email = models.EmailField('e-mail do pai', blank=True)
    pai_telefone = models.CharField('telefone do pai', max_length=32, blank=True)
    pai_celular = models.CharField('celular do pai', max_length=32, blank=True)
    mae_nome = models.CharField('nome da mãe', max_length=255, blank=True)
    mae_cpf = models.CharField('cpf da mãe', max_length=32, blank=True)
    mae_email = models.EmailField('e-mail da mãe', blank=True)
    mae_telefone = models.CharField('telefone da mãe', max_length=32, blank=True)
    mae_celular = models.CharField('celular da mãe', max_length=32, blank=True)
    responsavel_nome = models.CharField('nome do responsável', max_length=255, blank=True)
    responsavel_parentesco = models.CharField('parentesco', max_length=64, blank=True)
    responsavel_cpf = models.CharField('cpf do responsável', max_length=32, blank=True)
    responsavel_email = models.EmailField('e-mail do responsável', blank=True)
    responsavel_telefone = models.CharField('telefone do responsável', max_length=32, blank=True)
    responsavel_celular = models.CharField('celular do responsável', max_length=32, blank=True)
    endereco = models.CharField('endereço', max_length=255, blank=True)
    bairro = models.CharField('bairro', max_length=128, blank=True)
    cidade = models.CharField('cidade', max_length=128, blank=True)
    cep = models.CharField('CEP', max_length=16, blank=True)
    estado = models.CharField('estado', max_length=32, blank=True)
    signature = models.ImageField('assinatura do responsável', upload_to='signatures/responsavel', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def role_slug(self):
        return 'responsavel'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


class Diretoria(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='diretoria')
    nome = models.CharField('nome', max_length=255)
    igreja = models.CharField('igreja', max_length=255)
    endereco = models.CharField('endereço', max_length=255)
    distrito = models.CharField('distrito', max_length=128)
    numero = models.CharField('número', max_length=32)
    bairro = models.CharField('bairro', max_length=128)
    cep = models.CharField('CEP', max_length=16)
    cidade = models.CharField('cidade', max_length=128)
    estado = models.CharField('estado', max_length=64)
    email = models.EmailField('e-mail')
    whatsapp = models.CharField('whatsapp', max_length=32)
    telefone_residencial = models.CharField('telefone residencial', max_length=32, blank=True)
    telefone_comercial = models.CharField('telefone comercial', max_length=32, blank=True)
    nascimento = models.DateField('data de nascimento')
    estado_civil = models.CharField('estado civil', max_length=64)
    cpf = models.CharField('CPF', max_length=32)
    rg = models.CharField('RG', max_length=32)
    conjuge = models.CharField('esposa(o)', max_length=255, blank=True)
    filho_1 = models.CharField('filho(a) 1', max_length=255, blank=True)
    filho_2 = models.CharField('filho(a) 2', max_length=255, blank=True)
    filho_3 = models.CharField('filho(a) 3', max_length=255, blank=True)
    possui_limitacao_saude = models.CharField('possui limitação de saúde', max_length=8)
    limitacao_saude_descricao = models.TextField('descrição da limitação', blank=True)
    escolaridade = models.CharField('escolaridade', max_length=32)
    autorizacao_imagem = models.BooleanField('autorização de imagem aceita', default=False)
    declaracao_medica = models.BooleanField('declaração médica aceita', default=False)
    foto = models.ImageField('foto 3x4', upload_to='photos/diretoria', null=True, blank=True)
    assinatura = models.ImageField('assinatura da diretoria', upload_to='signatures/diretoria', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def role_slug(self):
        return 'diretoria'

    def __str__(self):
        return self.nome


class Aventureiro(models.Model):
    responsavel = models.ForeignKey(Responsavel, on_delete=models.CASCADE, related_name='aventures')
    nome = models.CharField('nome completo', max_length=255)
    sexo = models.CharField('sexo', max_length=32, blank=True)
    nascimento = models.DateField('data de nascimento', null=True, blank=True)
    serie = models.CharField('série', max_length=128, blank=True)
    colegio = models.CharField('colégio', max_length=255, blank=True)
    bolsa = models.CharField('bolsa', max_length=16, blank=True)
    religiao = models.CharField('religião', max_length=128, blank=True)
    certidao = models.CharField('certidão de nascimento', max_length=255, blank=True)
    rg = models.CharField('RG', max_length=64, blank=True)
    orgao = models.CharField('órgão expedidor', max_length=64, blank=True)
    cpf = models.CharField('CPF', max_length=32, blank=True)
    camiseta = models.CharField('camiseta', max_length=32, blank=True)
    plano = models.CharField('possui plano de saúde', max_length=16, blank=True)
    plano_nome = models.CharField('nome do plano', max_length=255, blank=True)
    cns = models.CharField('CNS', max_length=64, blank=True)
    doencas = models.JSONField('doenças', default=list, blank=True)
    condicoes = models.JSONField('condições', default=dict, blank=True)
    alergias = models.JSONField('alergias', default=dict, blank=True)
    deficiencias = models.JSONField('deficiências', default=list, blank=True)
    tipo_sangue = models.CharField('tipo sanguíneo', max_length=8, blank=True)
    declaracao_medica = models.BooleanField('declaracao médica aceita', default=False)
    autorizacao_imagem = models.BooleanField('autorização de imagem', default=False)
    foto = models.ImageField('foto 3x4', upload_to='photos/aventura', null=True, blank=True)
    assinatura = models.ImageField('assinatura do aventureiro', upload_to='signatures/aventura', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({self.responsavel.user.username})"

    @property
    def role_slug(self):
        return 'aventura'


class WhatsAppPreference(models.Model):
    NOTIFY_CADASTRO = 'cadastro'
    NOTIFY_DIRETORIA = 'diretoria'
    NOTIFY_CONFIRMACAO = 'confirmacao'
    NOTIFY_FINANCEIRO = 'financeiro'
    NOTIFY_GERAL = 'geral'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='whatsapp_preference')
    phone_number = models.CharField('numero whatsapp', max_length=32, blank=True)
    notify_cadastro = models.BooleanField('notificacao de cadastro', default=False)
    notify_diretoria = models.BooleanField('notificacao de cadastro de diretoria', default=False)
    notify_confirmacao = models.BooleanField('notificacao de confirmacao de inscricao', default=False)
    notify_financeiro = models.BooleanField('notificacao financeira', default=False)
    notify_geral = models.BooleanField('notificacao geral', default=False)
    cadastro_message = models.TextField('mensagem de cadastro', blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} ({self.phone_number or "sem numero"})'

    def enabled_for(self, notification_type):
        mapping = {
            self.NOTIFY_CADASTRO: self.notify_cadastro,
            self.NOTIFY_DIRETORIA: self.notify_diretoria,
            self.NOTIFY_CONFIRMACAO: self.notify_confirmacao,
            self.NOTIFY_FINANCEIRO: self.notify_financeiro,
            self.NOTIFY_GERAL: self.notify_geral,
        }
        return mapping.get(notification_type, False)


class WhatsAppQueue(models.Model):
    TYPE_CADASTRO = WhatsAppPreference.NOTIFY_CADASTRO
    TYPE_DIRETORIA = WhatsAppPreference.NOTIFY_DIRETORIA
    TYPE_CONFIRMACAO = WhatsAppPreference.NOTIFY_CONFIRMACAO
    TYPE_FINANCEIRO = WhatsAppPreference.NOTIFY_FINANCEIRO
    TYPE_GERAL = WhatsAppPreference.NOTIFY_GERAL
    TYPE_TESTE = 'teste'

    TYPE_CHOICES = [
        (TYPE_CADASTRO, 'Cadastro'),
        (TYPE_DIRETORIA, 'Diretoria'),
        (TYPE_CONFIRMACAO, 'Confirmação'),
        (TYPE_FINANCEIRO, 'Financeiro'),
        (TYPE_GERAL, 'Geral'),
        (TYPE_TESTE, 'Teste'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendente'),
        (STATUS_SENT, 'Enviado'),
        (STATUS_FAILED, 'Falhou'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='whatsapp_queue')
    phone_number = models.CharField('numero destino', max_length=32)
    notification_type = models.CharField('tipo notificacao', max_length=32, choices=TYPE_CHOICES, default=TYPE_GERAL)
    message_text = models.TextField('mensagem')
    status = models.CharField('status envio', max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    attempts = models.PositiveIntegerField('tentativas', default=0)
    provider_message_id = models.CharField('id provedor', max_length=128, blank=True)
    last_error = models.TextField('ultimo erro', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField('enviado em', null=True, blank=True)

    class Meta:
        ordering = ('created_at',)

    def __str__(self):
        return f'{self.phone_number} [{self.get_status_display()}]'


class WhatsAppTemplate(models.Model):
    TYPE_CADASTRO = WhatsAppPreference.NOTIFY_CADASTRO
    TYPE_DIRETORIA = WhatsAppPreference.NOTIFY_DIRETORIA
    TYPE_CONFIRMACAO = WhatsAppPreference.NOTIFY_CONFIRMACAO
    TYPE_FINANCEIRO = WhatsAppPreference.NOTIFY_FINANCEIRO
    TYPE_TESTE = 'teste'

    TYPE_CHOICES = [
        (TYPE_CADASTRO, 'Cadastro'),
        (TYPE_DIRETORIA, 'Diretoria'),
        (TYPE_CONFIRMACAO, 'Confirmação'),
        (TYPE_FINANCEIRO, 'Financeiro'),
        (TYPE_TESTE, 'Teste'),
    ]

    notification_type = models.CharField('tipo de notificacao', max_length=32, choices=TYPE_CHOICES, unique=True)
    message_text = models.TextField('mensagem')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.get_notification_type_display()}'


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    username = models.CharField('username', max_length=150, blank=True)
    profile = models.CharField('perfil', max_length=64, blank=True)
    location = models.CharField('onde', max_length=255, blank=True)
    action = models.CharField('o que fez', max_length=255)
    details = models.TextField('detalhes', blank=True)
    method = models.CharField('metodo', max_length=12, blank=True)
    path = models.CharField('caminho', max_length=255, blank=True)
    ip_address = models.CharField('ip', max_length=64, blank=True)
    user_agent = models.CharField('user agent', max_length=255, blank=True)
    created_at = models.DateTimeField('data/hora', auto_now_add=True)

    class Meta:
        verbose_name = 'log de auditoria'
        verbose_name_plural = 'logs de auditoria'
        ordering = ('-created_at',)

    def __str__(self):
        when = timezone.localtime(self.created_at).strftime('%d/%m/%Y %H:%M')
        who = self.username or (self.user.username if self.user else 'anonimo')
        return f'[{when}] {who} - {self.action}'


class DocumentoTemplate(models.Model):
    TYPE_RESPONSAVEL = 'responsavel'
    TYPE_AVENTUREIRO = 'aventureiro'
    TYPE_DIRETORIA = 'diretoria'

    TYPE_CHOICES = [
        (TYPE_RESPONSAVEL, 'Responsável'),
        (TYPE_AVENTUREIRO, 'Aventureiro'),
        (TYPE_DIRETORIA, 'Diretoria'),
    ]

    name = models.CharField('nome', max_length=120)
    template_type = models.CharField('tipo', max_length=24, choices=TYPE_CHOICES)
    background = models.ImageField('imagem de fundo', upload_to='documentos/templates')
    positions = models.JSONField('posições', default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'template de documento'
        verbose_name_plural = 'templates de documentos'

    def __str__(self):
        return f'{self.name} ({self.get_template_type_display()})'


class AccessGroup(models.Model):
    code = models.CharField('código', max_length=64, unique=True)
    name = models.CharField('nome', max_length=128, unique=True)
    users = models.ManyToManyField(User, blank=True, related_name='access_groups', verbose_name='usuários')
    menu_permissions = models.JSONField('menus permitidos', default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'grupo de acesso'
        verbose_name_plural = 'grupos de acesso'
        ordering = ('name',)

    def __str__(self):
        return self.name


class AventureiroFicha(models.Model):
    aventureiro = models.OneToOneField(Aventureiro, on_delete=models.CASCADE, related_name='ficha_completa')
    inscricao_data = models.JSONField('dados da ficha de inscricao', default=dict, blank=True)
    ficha_medica_data = models.JSONField('dados da ficha medica', default=dict, blank=True)
    declaracao_medica_data = models.JSONField('dados da declaracao medica', default=dict, blank=True)
    termo_imagem_data = models.JSONField('dados do termo de imagem', default=dict, blank=True)
    assinatura_inscricao = models.ImageField(
        'assinatura da ficha de inscricao',
        upload_to='signatures/fichas/inscricao',
        null=True,
        blank=True,
    )
    assinatura_declaracao_medica = models.ImageField(
        'assinatura da declaracao medica',
        upload_to='signatures/fichas/declaracao_medica',
        null=True,
        blank=True,
    )
    assinatura_termo_imagem = models.ImageField(
        'assinatura do termo de imagem',
        upload_to='signatures/fichas/termo_imagem',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ficha completa do aventureiro'
        verbose_name_plural = 'fichas completas dos aventureiros'

    def __str__(self):
        return f'Ficha completa - {self.aventureiro.nome}'


class DiretoriaFicha(models.Model):
    diretoria = models.OneToOneField(Diretoria, on_delete=models.CASCADE, related_name='ficha_completa')
    compromisso_data = models.JSONField('dados do compromisso voluntariado', default=dict, blank=True)
    termo_imagem_data = models.JSONField('dados do termo de imagem', default=dict, blank=True)
    assinatura_compromisso = models.ImageField(
        'assinatura do compromisso voluntariado',
        upload_to='signatures/fichas/diretoria_compromisso',
        null=True,
        blank=True,
    )
    assinatura_termo_imagem = models.ImageField(
        'assinatura do termo de imagem da diretoria',
        upload_to='signatures/fichas/diretoria_termo_imagem',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ficha completa da diretoria'
        verbose_name_plural = 'fichas completas da diretoria'

    def __str__(self):
        return f'Ficha completa da diretoria - {self.diretoria.nome}'


class DocumentoInscricaoGerado(models.Model):
    TYPE_INSCRICAO = 'ficha_inscricao'
    TYPE_MEDICA = 'ficha_medica'
    TYPE_DECLARACAO = 'declaracao_medica'
    TYPE_TERMO = 'termo_imagem'

    TYPE_CHOICES = [
        (TYPE_INSCRICAO, 'Ficha de inscrição'),
        (TYPE_MEDICA, 'Ficha médica'),
        (TYPE_DECLARACAO, 'Declaração médica'),
        (TYPE_TERMO, 'Termo de imagem'),
    ]

    aventureiro = models.ForeignKey(Aventureiro, on_delete=models.CASCADE, related_name='documentos_gerados')
    doc_type = models.CharField('tipo de documento', max_length=32, choices=TYPE_CHOICES)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_inscricao_gerados')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'documento de inscrição gerado'
        verbose_name_plural = 'documentos de inscrição gerados'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.get_doc_type_display()} - {self.aventureiro.nome}'


class Evento(models.Model):
    name = models.CharField('nome do evento', max_length=255)
    event_type = models.CharField('tipo do evento', max_length=128, blank=True)
    event_date = models.DateField('data do evento', null=True, blank=True)
    event_time = models.TimeField('hora do evento', null=True, blank=True)
    fields_data = models.JSONField('campos do evento', default=list, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='eventos_criados',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'evento'
        verbose_name_plural = 'eventos'

    def __str__(self):
        return self.name


class EventoPreset(models.Model):
    preset_name = models.CharField('nome da pré-configuração', max_length=160)
    event_name = models.CharField('nome padrão do evento', max_length=255, blank=True)
    event_type = models.CharField('tipo padrão do evento', max_length=128, blank=True)
    event_date = models.DateField('data padrão', null=True, blank=True)
    event_time = models.TimeField('hora padrão', null=True, blank=True)
    fields_data = models.JSONField('campos padrão', default=list, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='eventos_presets_criados',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        ordering = ('preset_name',)
        verbose_name = 'pré-configuração de evento'
        verbose_name_plural = 'pré-configurações de evento'

    def __str__(self):
        return self.preset_name


class EventoPresenca(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='presencas')
    aventureiro = models.ForeignKey(Aventureiro, on_delete=models.CASCADE, related_name='presencas_evento')
    presente = models.BooleanField('presente', default=False)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='presencas_atualizadas',
    )
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'presença em evento'
        verbose_name_plural = 'presenças em evento'
        unique_together = ('evento', 'aventureiro')
        ordering = ('aventureiro__nome',)

    def __str__(self):
        status = 'presente' if self.presente else 'ausente'
        return f'{self.evento.name} - {self.aventureiro.nome} ({status})'


class MensalidadeAventureiro(models.Model):
    TIPO_INSCRICAO = 'inscricao'
    TIPO_MENSALIDADE = 'mensalidade'

    TIPO_CHOICES = [
        (TIPO_INSCRICAO, 'Inscrição'),
        (TIPO_MENSALIDADE, 'Mensalidade'),
    ]

    STATUS_PENDENTE = 'pendente'
    STATUS_PAGA = 'paga'

    STATUS_CHOICES = [
        (STATUS_PENDENTE, 'Pendente'),
        (STATUS_PAGA, 'Paga'),
    ]

    aventureiro = models.ForeignKey(Aventureiro, on_delete=models.CASCADE, related_name='mensalidades')
    ano_referencia = models.PositiveIntegerField('ano de referência')
    mes_referencia = models.PositiveSmallIntegerField('mês de referência')
    tipo = models.CharField('tipo', max_length=16, choices=TIPO_CHOICES, default=TIPO_MENSALIDADE)
    valor = models.DecimalField('valor', max_digits=10, decimal_places=2, default=Decimal('30.00'))
    status = models.CharField('status', max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDENTE)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mensalidades_criadas',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'mensalidade do aventureiro'
        verbose_name_plural = 'mensalidades dos aventureiros'
        unique_together = ('aventureiro', 'ano_referencia', 'mes_referencia')
        ordering = ('aventureiro__nome', 'ano_referencia', 'mes_referencia')

    def __str__(self):
        return f'{self.aventureiro.nome} - {self.mes_referencia:02d}/{self.ano_referencia}'


class PagamentoMensalidade(models.Model):
    STATUS_PENDENTE = 'pendente'
    STATUS_PROCESSANDO = 'processando'
    STATUS_PAGO = 'pago'
    STATUS_CANCELADO = 'cancelado'
    STATUS_FALHA = 'falha'

    STATUS_CHOICES = [
        (STATUS_PENDENTE, 'Pendente'),
        (STATUS_PROCESSANDO, 'Processando'),
        (STATUS_PAGO, 'Pago'),
        (STATUS_CANCELADO, 'Cancelado'),
        (STATUS_FALHA, 'Falha'),
    ]

    responsavel = models.ForeignKey('Responsavel', on_delete=models.CASCADE, related_name='pagamentos_mensalidade')
    mensalidades = models.ManyToManyField(MensalidadeAventureiro, related_name='pagamentos', blank=True)
    valor_total = models.DecimalField('valor total', max_digits=10, decimal_places=2)
    status = models.CharField('status', max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDENTE)
    mp_payment_id = models.CharField('MP payment id', max_length=64, blank=True)
    mp_external_reference = models.CharField('MP external reference', max_length=128, blank=True)
    mp_status = models.CharField('MP status', max_length=32, blank=True)
    mp_status_detail = models.CharField('MP status detail', max_length=128, blank=True)
    mp_qr_code = models.TextField('MP QR code Pix', blank=True)
    mp_qr_code_base64 = models.TextField('MP QR code base64', blank=True)
    entregue = models.BooleanField('entregue', default=False)
    paid_at = models.DateTimeField('pago em', null=True, blank=True)
    whatsapp_notified_at = models.DateTimeField('whatsapp notificado em', null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagamentos_mensalidade_criados',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'pagamento de mensalidades'
        verbose_name_plural = 'pagamentos de mensalidades'
        ordering = ('-created_at',)

    def __str__(self):
        return f'Pagamento mensalidades #{self.pk} - {self.responsavel}'


class LojaProduto(models.Model):
    titulo = models.CharField('título', max_length=255)
    descricao = models.TextField('descrição', blank=True)
    foto = models.ImageField('foto', upload_to='loja/produtos', null=True, blank=True)
    minimo_pedidos_pagos = models.PositiveIntegerField(
        'mínimo de pedidos pagos para produção',
        null=True,
        blank=True,
    )
    ativo = models.BooleanField('ativo', default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loja_produtos_criados',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'produto da loja'
        verbose_name_plural = 'produtos da loja'
        ordering = ('-created_at',)

    def __str__(self):
        return self.titulo


class LojaProdutoVariacao(models.Model):
    produto = models.ForeignKey(LojaProduto, on_delete=models.CASCADE, related_name='variacoes')
    nome = models.CharField('variação', max_length=255)
    valor = models.DecimalField('valor', max_digits=10, decimal_places=2)
    estoque = models.IntegerField('estoque', null=True, blank=True)
    ativo = models.BooleanField('ativo', default=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'variação de produto'
        verbose_name_plural = 'variações de produto'
        ordering = ('produto__titulo', 'nome')

    def __str__(self):
        return f'{self.produto.titulo} - {self.nome}'


class LojaProdutoFoto(models.Model):
    produto = models.ForeignKey(LojaProduto, on_delete=models.CASCADE, related_name='fotos')
    variacao = models.ForeignKey(LojaProdutoVariacao, on_delete=models.CASCADE, related_name='fotos')
    variacoes_vinculadas = models.ManyToManyField(
        LojaProdutoVariacao,
        related_name='fotos_vinculadas_loja',
        blank=True,
    )
    todas_variacoes = models.BooleanField('todas as variações', default=False)
    foto = models.ImageField('foto', upload_to='loja/produtos')
    ordem = models.PositiveIntegerField('ordem', default=0)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'foto de produto'
        verbose_name_plural = 'fotos de produto'
        ordering = ('produto__titulo', 'ordem', 'id')

    def __str__(self):
        if self.todas_variacoes:
            alvo = 'todas as variações'
        else:
            alvo = self.variacao.nome
        return f'Foto de {self.produto.titulo} ({alvo})'


class LojaPedido(models.Model):
    FORMA_PAGAMENTO_PIX = 'pix'
    FORMA_PAGAMENTO_CHOICES = [
        (FORMA_PAGAMENTO_PIX, 'Pix'),
    ]

    STATUS_PENDENTE = 'pendente'
    STATUS_PROCESSANDO = 'processando'
    STATUS_PAGO = 'pago'
    STATUS_CANCELADO = 'cancelado'
    STATUS_FALHA = 'falha'

    STATUS_CHOICES = [
        (STATUS_PENDENTE, 'Pendente'),
        (STATUS_PROCESSANDO, 'Processando'),
        (STATUS_PAGO, 'Pago'),
        (STATUS_CANCELADO, 'Cancelado'),
        (STATUS_FALHA, 'Falha'),
    ]

    responsavel = models.ForeignKey('Responsavel', on_delete=models.CASCADE, related_name='pedidos_loja')
    forma_pagamento = models.CharField(
        'forma de pagamento',
        max_length=24,
        choices=FORMA_PAGAMENTO_CHOICES,
        default=FORMA_PAGAMENTO_PIX,
    )
    valor_total = models.DecimalField('valor total', max_digits=10, decimal_places=2)
    status = models.CharField('status', max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDENTE)
    mp_payment_id = models.CharField('MP payment id', max_length=64, blank=True)
    mp_external_reference = models.CharField('MP external reference', max_length=128, blank=True)
    mp_status = models.CharField('MP status', max_length=32, blank=True)
    mp_status_detail = models.CharField('MP status detail', max_length=128, blank=True)
    mp_qr_code = models.TextField('MP QR code Pix', blank=True)
    mp_qr_code_base64 = models.TextField('MP QR code base64', blank=True)
    paid_at = models.DateTimeField('pago em', null=True, blank=True)
    entregue = models.BooleanField('entregue', default=False)
    whatsapp_notified_at = models.DateTimeField('whatsapp notificado em', null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_loja_criados',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'pedido da loja'
        verbose_name_plural = 'pedidos da loja'
        ordering = ('-created_at',)

    def __str__(self):
        return f'Pedido loja #{self.pk} - {self.responsavel}'


class LojaPedidoItem(models.Model):
    pedido = models.ForeignKey(LojaPedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(LojaProduto, on_delete=models.SET_NULL, null=True, blank=True, related_name='itens_pedido')
    variacao = models.ForeignKey(LojaProdutoVariacao, on_delete=models.SET_NULL, null=True, blank=True, related_name='itens_pedido')
    produto_titulo = models.CharField('produto (snapshot)', max_length=255)
    variacao_nome = models.CharField('variação (snapshot)', max_length=255)
    quantidade = models.PositiveIntegerField('quantidade')
    valor_unitario = models.DecimalField('valor unitário', max_digits=10, decimal_places=2)
    valor_total = models.DecimalField('valor total', max_digits=10, decimal_places=2)
    foto_url = models.TextField('foto URL (snapshot)', blank=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'item do pedido da loja'
        verbose_name_plural = 'itens dos pedidos da loja'
        ordering = ('pedido_id', 'id')

    def __str__(self):
        return f'Item pedido #{self.pedido_id} - {self.produto_titulo} ({self.variacao_nome})'


class ApostilaRequisito(models.Model):
    CLASSE_ABELHINHAS = 'abelhinhas'
    CLASSE_LUMINARES = 'luminares'
    CLASSE_EDIFICADORES = 'edificadores'
    CLASSE_MAOS_AJUDADORAS = 'maos_ajudadoras'

    CLASSE_CHOICES = [
        (CLASSE_ABELHINHAS, 'Abelhinhas'),
        (CLASSE_LUMINARES, 'Luminares'),
        (CLASSE_EDIFICADORES, 'Edificadores'),
        (CLASSE_MAOS_AJUDADORAS, 'Mãos Ajudadoras'),
    ]

    classe = models.CharField('classe', max_length=32, choices=CLASSE_CHOICES)
    numero_requisito = models.CharField('número do requisito', max_length=64)
    descricao = models.TextField('descrição')
    resposta = models.TextField('resposta', blank=True)
    dicas = models.TextField('dicas', blank=True)
    foto_requisito = models.ImageField('foto do requisito', upload_to='apostila/requisitos', null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='apostila_requisitos_criados',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'requisito da apostila'
        verbose_name_plural = 'requisitos da apostila'
        ordering = ('classe', 'numero_requisito', 'id')

    def __str__(self):
        return f'{self.get_classe_display()} - {self.numero_requisito}'


class ApostilaSubRequisito(models.Model):
    requisito = models.ForeignKey(ApostilaRequisito, on_delete=models.CASCADE, related_name='subrequisitos')
    codigo_subrequisito = models.CharField('código do subrequisito', max_length=32)
    descricao = models.TextField('descrição')
    resposta = models.TextField('resposta', blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='apostila_subrequisitos_criados',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'subrequisito da apostila'
        verbose_name_plural = 'subrequisitos da apostila'
        ordering = ('requisito_id', 'codigo_subrequisito', 'id')
        unique_together = ('requisito', 'codigo_subrequisito')

    def __str__(self):
        return f'{self.requisito.numero_requisito}.{self.codigo_subrequisito}'


class ApostilaDica(models.Model):
    requisito = models.ForeignKey(ApostilaRequisito, on_delete=models.CASCADE, related_name='dicas_rows')
    texto = models.TextField('texto da dica')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='apostila_dicas_criadas',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'dica da apostila'
        verbose_name_plural = 'dicas da apostila'
        ordering = ('requisito_id', 'id')

    def __str__(self):
        return f'Dica do requisito {self.requisito.numero_requisito}'


class ApostilaDicaArquivo(models.Model):
    dica = models.ForeignKey(ApostilaDica, on_delete=models.CASCADE, related_name='arquivos')
    arquivo = models.FileField('arquivo da dica', upload_to='apostila/dicas/arquivos')
    created_at = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'arquivo da dica da apostila'
        verbose_name_plural = 'arquivos das dicas da apostila'
        ordering = ('dica_id', 'id')

    def __str__(self):
        return f'Arquivo da dica #{self.dica_id}'


class AventureiroPontosPreset(models.Model):
    nome = models.CharField('nome', max_length=160)
    pontos = models.IntegerField('pontos')
    motivo_padrao = models.CharField('motivo padrão', max_length=255)
    ativo = models.BooleanField('ativo', default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pontos_presets_criados',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'pré-registro de pontos'
        verbose_name_plural = 'pré-registros de pontos'
        ordering = ('nome',)

    def __str__(self):
        sinal = '+' if self.pontos > 0 else ''
        return f'{self.nome} ({sinal}{self.pontos})'


class AventureiroPontosLancamento(models.Model):
    aventureiro = models.ForeignKey(Aventureiro, on_delete=models.CASCADE, related_name='pontos_lancamentos')
    pontos = models.IntegerField('pontos')
    motivo = models.CharField('motivo', max_length=255)
    preset = models.ForeignKey(
        AventureiroPontosPreset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lancamentos',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pontos_lancados',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'lançamento de pontos do aventureiro'
        verbose_name_plural = 'lançamentos de pontos dos aventureiros'
        ordering = ('-created_at',)

    def __str__(self):
        sinal = '+' if self.pontos > 0 else ''
        return f'{self.aventureiro.nome}: {sinal}{self.pontos} ({self.motivo})'

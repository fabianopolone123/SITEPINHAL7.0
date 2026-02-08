from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

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
    NOTIFY_FINANCEIRO = 'financeiro'
    NOTIFY_GERAL = 'geral'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='whatsapp_preference')
    phone_number = models.CharField('numero whatsapp', max_length=32, blank=True)
    notify_cadastro = models.BooleanField('notificacao de cadastro', default=False)
    notify_diretoria = models.BooleanField('notificacao de cadastro de diretoria', default=False)
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
            self.NOTIFY_FINANCEIRO: self.notify_financeiro,
            self.NOTIFY_GERAL: self.notify_geral,
        }
        return mapping.get(notification_type, False)


class WhatsAppQueue(models.Model):
    TYPE_CADASTRO = WhatsAppPreference.NOTIFY_CADASTRO
    TYPE_DIRETORIA = WhatsAppPreference.NOTIFY_DIRETORIA
    TYPE_FINANCEIRO = WhatsAppPreference.NOTIFY_FINANCEIRO
    TYPE_GERAL = WhatsAppPreference.NOTIFY_GERAL
    TYPE_TESTE = 'teste'

    TYPE_CHOICES = [
        (TYPE_CADASTRO, 'Cadastro'),
        (TYPE_DIRETORIA, 'Diretoria'),
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
    TYPE_TESTE = 'teste'

    TYPE_CHOICES = [
        (TYPE_CADASTRO, 'Cadastro'),
        (TYPE_DIRETORIA, 'Diretoria'),
        (TYPE_TESTE, 'Teste'),
    ]

    notification_type = models.CharField('tipo de notificacao', max_length=32, choices=TYPE_CHOICES, unique=True)
    message_text = models.TextField('mensagem')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.get_notification_type_display()}'


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

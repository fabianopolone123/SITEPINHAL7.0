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

    ROLE_CHOICES = [
        (ROLE_RESPONSAVEL, 'Responsável'),
        (ROLE_DIRETORIA, 'Diretoria'),
        (ROLE_DIRETOR, 'Diretor'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='access')
    role = models.CharField('perfil de acesso', max_length=32, choices=ROLE_CHOICES, default=ROLE_RESPONSAVEL)
    profiles = models.JSONField('perfis de acesso', default=list, blank=True)
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
    NOTIFY_FINANCEIRO = 'financeiro'
    NOTIFY_GERAL = 'geral'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='whatsapp_preference')
    phone_number = models.CharField('numero whatsapp', max_length=32, blank=True)
    notify_cadastro = models.BooleanField('notificacao de cadastro', default=True)
    notify_financeiro = models.BooleanField('notificacao financeira', default=False)
    notify_geral = models.BooleanField('notificacao geral', default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} ({self.phone_number or "sem numero"})'

    def enabled_for(self, notification_type):
        mapping = {
            self.NOTIFY_CADASTRO: self.notify_cadastro,
            self.NOTIFY_FINANCEIRO: self.notify_financeiro,
            self.NOTIFY_GERAL: self.notify_geral,
        }
        return mapping.get(notification_type, False)


class WhatsAppQueue(models.Model):
    TYPE_CADASTRO = WhatsAppPreference.NOTIFY_CADASTRO
    TYPE_FINANCEIRO = WhatsAppPreference.NOTIFY_FINANCEIRO
    TYPE_GERAL = WhatsAppPreference.NOTIFY_GERAL

    TYPE_CHOICES = [
        (TYPE_CADASTRO, 'Cadastro'),
        (TYPE_FINANCEIRO, 'Financeiro'),
        (TYPE_GERAL, 'Geral'),
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

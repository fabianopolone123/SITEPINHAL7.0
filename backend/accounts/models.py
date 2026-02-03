from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


def signature_upload_to(instance, filename):
    prefix = 'signatures'
    role = getattr(instance, 'role_slug', filename)
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f"{prefix}/{role}/{timestamp}_{filename}" if filename else f"{prefix}/{role}/{timestamp}.png"


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
    assinatura = models.ImageField('assinatura do aventureiro', upload_to='signatures/aventura', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({self.responsavel.user.username})"

    @property
    def role_slug(self):
        return 'aventura'

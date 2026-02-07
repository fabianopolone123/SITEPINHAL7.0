from django import forms
from django.contrib.auth import get_user_model
from .models import Responsavel, Aventureiro, Diretoria, UserAccess
from .utils import decode_signature, decode_photo

User = get_user_model()


def _upsert_user_profile(user, profile):
    access, _ = UserAccess.objects.get_or_create(
        user=user,
        defaults={'role': profile, 'profiles': [profile]},
    )
    access.add_profile(profile)
    if profile == UserAccess.ROLE_DIRETOR:
        access.role = UserAccess.ROLE_DIRETOR
    access.save(update_fields=['role', 'profiles', 'updated_at'])
    return access


class ResponsavelForm(forms.ModelForm):
    required_display_fields = [
        'username', 'password', 'password_confirm',
        'pai_nome', 'pai_cpf', 'pai_email', 'pai_telefone', 'pai_celular',
        'mae_nome', 'mae_cpf', 'mae_email', 'mae_telefone', 'mae_celular',
        'responsavel_nome', 'responsavel_parentesco', 'responsavel_cpf',
        'responsavel_email', 'responsavel_telefone', 'responsavel_celular',
        'endereco', 'bairro', 'cidade', 'cep', 'estado',
        'signature_value',
    ]
    username = forms.CharField(max_length=150, label='nome de usuário')
    password = forms.CharField(widget=forms.PasswordInput, label='senha')
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='repita a senha')
    signature_value = forms.CharField(widget=forms.HiddenInput, required=True)

    class Meta:
        model = Responsavel
        exclude = ('user', 'signature', 'created_at')

    def clean(self):
        cleaned = super().clean()
        senha = cleaned.get('password')
        confirm = cleaned.get('password_confirm')
        if senha and confirm and senha != confirm:
            self.add_error('password_confirm', 'As senhas precisam coincidir.')
        if not (cleaned.get('pai_nome') or cleaned.get('mae_nome') or cleaned.get('responsavel_nome')):
            raise forms.ValidationError('Informe o pai, a mãe ou o responsável legal.')
        return cleaned

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError('Este nome de usuário já está em uso.')
        return username

    def save(self, commit=True):
        username = self.cleaned_data.pop('username')
        password = self.cleaned_data.pop('password')
        self.cleaned_data.pop('password_confirm', None)
        signature_data = self.cleaned_data.pop('signature_value', None)
        user = User.objects.create_user(username=username, password=password)
        responsavel = super().save(commit=False)
        responsavel.user = user
        signature_file = decode_signature(signature_data, 'responsavel')
        if signature_file:
            responsavel.signature.save(signature_file.name, signature_file, save=False)
        if commit:
            responsavel.save()
            _upsert_user_profile(user, UserAccess.ROLE_RESPONSAVEL)
        return responsavel


class AventureiroForm(forms.ModelForm):
    required_display_fields = [
        'nome', 'religiao', 'sexo', 'nascimento', 'serie', 'colegio', 'bolsa',
        'camiseta', 'plano', 'tipo_sangue', 'declaracao_medica',
        'autorizacao_imagem', 'signature_value_av', 'photo_value',
    ]
    signature_value_av = forms.CharField(widget=forms.HiddenInput, required=True)
    photo_value = forms.CharField(widget=forms.HiddenInput, required=False)
    cardiaco_detalhe = forms.CharField(required=False)
    cardiaco_medicamento = forms.CharField(required=False)
    cardiaco_remedio = forms.CharField(required=False)
    diabetico_detalhe = forms.CharField(required=False)
    diabetico_medicamento = forms.CharField(required=False)
    diabetico_remedio = forms.CharField(required=False)
    renal_detalhe = forms.CharField(required=False)
    renal_medicamento = forms.CharField(required=False)
    renal_remedio = forms.CharField(required=False)
    psicologico_detalhe = forms.CharField(required=False)
    psicologico_medicamento = forms.CharField(required=False)
    psicologico_remedio = forms.CharField(required=False)
    alergia_pele = forms.CharField(required=False)
    alergia_pele_descricao = forms.CharField(required=False)
    alergia_alimento = forms.CharField(required=False)
    alergia_alimento_descricao = forms.CharField(required=False)
    alergia_medicamento = forms.CharField(required=False)
    alergia_medicamento_descricao = forms.CharField(required=False)

    class Meta:
        model = Aventureiro
        exclude = ('responsavel', 'assinatura', 'created_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.documentacao_error = False

    def clean_doencas(self):
        return self.data.getlist('doenca')

    def clean_deficiencias(self):
        return self.data.getlist('deficiencia')

    def clean_condicoes(self):
        condicoes = {}
        for prefix in ('cardiaco', 'diabetico', 'renal', 'psicologico'):
            condicoes[prefix] = {
                'resposta': self.data.get(prefix),
                'detalhe': self.data.get(f"{prefix}_detalhe"),
                'medicamento': self.data.get(f"{prefix}_medicamento"),
                'remedio': self.data.get(f"{prefix}_remedio"),
            }
        return condicoes

    def clean_alergias(self):
        alergias = {}
        pairs = [
            ('alergia_pele', 'alergia_pele_descricao'),
            ('alergia_alimento', 'alergia_alimento_descricao'),
            ('alergia_medicamento', 'alergia_medicamento_descricao'),
        ]
        for field, detail in pairs:
            alergias[field] = {
                'resposta': self.data.get(field),
                'descricao': self.data.get(detail),
            }
        return alergias

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('nome'):
            self.add_error('nome', 'Informe o nome do aventureiro.')
        if not cleaned.get('signature_value_av') or not cleaned['signature_value_av'].strip():
            self.add_error('signature_value_av', 'Assine a ficha antes de enviar.')
        photo_value = cleaned.get('photo_value') or self.data.get('photo_value')
        if not (photo_value and photo_value.strip()):
            self.add_error('photo_value', 'Anexe a foto 3x4 do aventureiro.')
        self.documentacao_error = False
        self._validate_basic_fields(cleaned)
        self._validate_doc_requirements(cleaned)
        self._validate_plano(cleaned)
        self._validate_camiseta(cleaned)
        self._validate_tipo_sangue(cleaned)
        self._validate_condicoes()
        self._validate_alergias()
        self._validate_declaracoes(cleaned)
        return cleaned

    def _validate_basic_fields(self, cleaned):
        required = [
            ('religiao', 'Informe a religião.'),
            ('sexo', 'Informe o sexo.'),
            ('nascimento', 'Informe a data de nascimento.'),
            ('serie', 'Informe a série/ano.'),
            ('colegio', 'Informe o colégio.'),
            ('bolsa', 'Informe se recebe Bolsa Família.'),
        ]
        for field, message in required:
            if not cleaned.get(field):
                self.add_error(field, message)

    def _validate_doc_requirements(self, cleaned):
        certidao = cleaned.get('certidao')
        rg = cleaned.get('rg')
        orgao = cleaned.get('orgao')
        cpf = cleaned.get('cpf')

        has_rg_with_orgao = bool(rg and orgao)
        has_certidao = bool(certidao)
        has_cpf = bool(cpf)

        if not (has_certidao or has_rg_with_orgao or has_cpf):
            self.documentacao_error = True
            raise forms.ValidationError('Informe pelo menos uma documentação válida: certidão, RG (com órgão) ou CPF.')
        if rg and not orgao:
            self.add_error('orgao', 'Informe o órgão expedidor junto com o RG.')
        if orgao and not rg:
            self.add_error('rg', 'Informe o número do RG que pertence ao órgão expedidor.')

    def _validate_plano(self, cleaned):
        plano = cleaned.get('plano')
        if not plano:
            self.add_error('plano', 'Informe se possui plano de saúde.')
        elif plano == 'sim' and not cleaned.get('plano_nome'):
            self.add_error('plano_nome', 'Informe o nome do plano de saúde.')

    def _validate_camiseta(self, cleaned):
        if not cleaned.get('camiseta'):
            self.add_error('camiseta', 'Selecione um tamanho de camiseta.')

    def _validate_tipo_sangue(self, cleaned):
        if not cleaned.get('tipo_sangue'):
            self.add_error('tipo_sangue', 'Selecione o tipo sanguíneo.')

    def _validate_condicoes(self):
        for prefix in ('cardiaco', 'diabetico', 'renal', 'psicologico'):
            if self.data.get(prefix) not in ('sim', 'nao'):
                self.add_error(prefix, 'Informe sim ou não para essa condição.')
            if self.data.get(prefix) == 'sim' and not self.data.get(f"{prefix}_detalhe"):
                self.add_error(f"{prefix}_detalhe", 'Descreva a condição indicada.')
            med_flag = self.data.get(f"{prefix}_medicamento")
            if med_flag not in ('sim', 'nao'):
                self.add_error(f"{prefix}_medicamento", 'Informe sim ou não para essa pergunta.')
            elif med_flag == 'sim' and not self.data.get(f"{prefix}_remedio"):
                self.add_error(f"{prefix}_remedio", 'Informe o medicamento utilizado.')

    def _validate_alergias(self):
        pairs = [
            ('alergia_pele', 'alergia_pele_descricao'),
            ('alergia_alimento', 'alergia_alimento_descricao'),
            ('alergia_medicamento', 'alergia_medicamento_descricao'),
        ]
        for field, detail in pairs:
            value = self.data.get(field)
            if value not in ('sim', 'nao'):
                self.add_error(field, 'Informe sim ou não para essa alergia.')
            if value == 'sim' and not self.data.get(detail):
                self.add_error(detail, 'Informe o detalhe da alergia indicada.')

    def _validate_declaracoes(self, cleaned):
        if not cleaned.get('declaracao_medica'):
            self.add_error('declaracao_medica', 'Aceite a declaração médica.')
        if not cleaned.get('autorizacao_imagem'):
            self.add_error('autorizacao_imagem', 'Aceite o termo de autorização de imagem.')

    def save(self, responsavel, commit=True):
        adventure = super().save(commit=False)
        adventure.responsavel = responsavel
        signature_data = self.cleaned_data.get('signature_value_av')
        if signature := decode_signature(signature_data, 'aventura'):
            adventure.assinatura.save(signature.name, signature, save=False)
        if commit:
            adventure.save()
        return adventure


class ResponsavelDadosForm(forms.ModelForm):
    class Meta:
        model = Responsavel
        exclude = ('user', 'signature', 'created_at')


class AventureiroDadosForm(forms.ModelForm):
    class Meta:
        model = Aventureiro
        fields = [
            'nome', 'sexo', 'nascimento', 'serie', 'colegio', 'bolsa', 'religiao',
            'certidao', 'rg', 'orgao', 'cpf', 'camiseta', 'plano', 'plano_nome',
            'cns', 'tipo_sangue', 'declaracao_medica', 'autorizacao_imagem', 'foto',
        ]


class DiretoriaForm(forms.ModelForm):
    required_display_fields = [
        'username', 'password', 'password_confirm',
        'nome', 'igreja', 'endereco', 'distrito', 'numero', 'bairro', 'cep',
        'cidade', 'estado', 'email', 'whatsapp', 'nascimento', 'estado_civil',
        'cpf', 'rg', 'conjuge', 'filho_1', 'filho_2', 'filho_3',
        'possui_limitacao_saude', 'escolaridade',
        'autorizacao_imagem', 'declaracao_medica',
        'signature_value_dir', 'photo_value_dir',
    ]
    username = forms.CharField(max_length=150, label='nome de usuário')
    password = forms.CharField(widget=forms.PasswordInput, label='senha')
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='repita a senha')
    signature_value_dir = forms.CharField(widget=forms.HiddenInput, required=True)
    photo_value_dir = forms.CharField(widget=forms.HiddenInput, required=True)

    class Meta:
        model = Diretoria
        exclude = ('user', 'assinatura', 'foto', 'created_at')

    def clean(self):
        cleaned = super().clean()
        senha = cleaned.get('password')
        confirm = cleaned.get('password_confirm')
        if senha and confirm and senha != confirm:
            self.add_error('password_confirm', 'As senhas precisam coincidir.')

        possui_limitacao = cleaned.get('possui_limitacao_saude')
        descricao = cleaned.get('limitacao_saude_descricao')
        if possui_limitacao == 'sim' and not (descricao and descricao.strip()):
            self.add_error('limitacao_saude_descricao', 'Descreva a limitação de saúde informada.')

        if not cleaned.get('conjuge'):
            self.add_error('conjuge', 'Informe a esposa(o).')
        if not cleaned.get('filho_1'):
            self.add_error('filho_1', 'Informe o(a) filho(a) 1.')
        if not cleaned.get('filho_2'):
            self.add_error('filho_2', 'Informe o(a) filho(a) 2.')
        if not cleaned.get('filho_3'):
            self.add_error('filho_3', 'Informe o(a) filho(a) 3.')

        if not cleaned.get('autorizacao_imagem'):
            self.add_error('autorizacao_imagem', 'Aceite a autorização de uso de imagem.')
        if not cleaned.get('declaracao_medica'):
            self.add_error('declaracao_medica', 'Aceite a declaração médica.')

        signature_data = cleaned.get('signature_value_dir')
        if not signature_data or not signature_data.strip():
            self.add_error('signature_value_dir', 'Assine a ficha antes de concluir.')

        photo_data = cleaned.get('photo_value_dir')
        if not photo_data or not photo_data.strip():
            self.add_error('photo_value_dir', 'Anexe a foto 3x4 antes de concluir.')

        return cleaned

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError('Este nome de usuário já está em uso.')
        return username

    def save(self, commit=True):
        username = self.cleaned_data.pop('username')
        password = self.cleaned_data.pop('password')
        self.cleaned_data.pop('password_confirm', None)
        signature_data = self.cleaned_data.pop('signature_value_dir', None)
        photo_data = self.cleaned_data.pop('photo_value_dir', None)

        user = User.objects.create_user(username=username, password=password)
        diretoria = super().save(commit=False)
        diretoria.user = user

        signature_file = decode_signature(signature_data, 'diretoria')
        if signature_file:
            diretoria.assinatura.save(signature_file.name, signature_file, save=False)

        photo_file = decode_photo(photo_data, prefix='diretoria_photo')
        if photo_file:
            diretoria.foto.save(photo_file.name, photo_file, save=False)

        if commit:
            diretoria.save()
            _upsert_user_profile(user, UserAccess.ROLE_DIRETORIA)
        return diretoria


class DiretoriaDadosForm(forms.ModelForm):
    class Meta:
        model = Diretoria
        exclude = ('user', 'assinatura', 'foto', 'created_at')


class UserAccessForm(forms.Form):
    profiles = forms.MultipleChoiceField(
        label='perfis',
        choices=UserAccess.ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )
    is_active = forms.BooleanField(label='usuário ativo', required=False)

    def clean_profiles(self):
        profiles = self.cleaned_data.get('profiles') or []
        if not profiles:
            raise forms.ValidationError('Selecione pelo menos um perfil.')
        return profiles


class NovoCadastroLoginForm(forms.Form):
    username = forms.CharField(max_length=150, label='Username')
    password = forms.CharField(widget=forms.PasswordInput, label='Senha')
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='Confirmar senha')

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get('username', '').strip()
        senha = cleaned.get('password')
        confirm = cleaned.get('password_confirm')
        if not username:
            self.add_error('username', 'Informe o username.')
        if username and User.objects.filter(username=username).exists():
            self.add_error('username', 'Este username já existe.')
        if senha and confirm and senha != confirm:
            self.add_error('password_confirm', 'As senhas não conferem.')
        return cleaned

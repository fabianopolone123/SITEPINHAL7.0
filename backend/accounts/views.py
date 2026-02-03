from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

from .forms import ResponsavelForm, AventureiroForm
from .models import Responsavel


class RegisterView(View):
    template_name = 'register.html'

    def get(self, request):
        return render(request, self.template_name)


class ResponsavelView(View):
    template_name = 'responsavel.html'

    def get(self, request):
        form = ResponsavelForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ResponsavelForm(request.POST)
        if form.is_valid():
            responsavel = form.save()
            login(request, responsavel.user)
            messages.success(request, 'Responsável cadastrado com sucesso. Continue com a ficha do aventureiro.')
            return redirect('accounts:aventura')
        messages.error(request, 'Há campos obrigatórios pendentes; corrija e envie novamente.')
        return render(request, self.template_name, {'form': form})


class AventuraView(LoginRequiredMixin, View):
    template_name = 'aventura.html'

    def get(self, request):
        form = AventureiroForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = AventureiroForm(request.POST)
        responsavel = getattr(request.user, 'responsavel', None)
        if not responsavel:
            messages.error(request, 'Complete primeiro os dados do responsável para continuar.')
            return redirect('accounts:responsavel')
        if form.is_valid():
            form.save(responsavel=responsavel)
            messages.success(request, 'Aventureiro salvo. Revise tudo na confirmação.')
            return redirect('accounts:confirmacao')
        messages.error(request, 'Verifique os campos antes de salvar o aventureiro.')
        return render(request, self.template_name, {'form': form})


class ConfirmacaoView(LoginRequiredMixin, View):
    template_name = 'confirmacao.html'

    def get(self, request):
        responsavel = getattr(request.user, 'responsavel', None)
        if not responsavel:
            messages.error(request, 'Complete os dados do responsável antes de revisar os aventureiros.')
            return redirect('accounts:responsavel')
        context = {
            'responsavel': responsavel,
            'aventures': responsavel.aventures.all(),
        }
        return render(request, self.template_name, context)

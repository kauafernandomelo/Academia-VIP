import re
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, Aluno, Plano, Matricula
from regras import gerar_mensalidade_inicial

alunos_bp = Blueprint("alunos", __name__)


def validar_cpf(cpf):
    """Valida CPF (formato e dígitos verificadores)."""
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
        digito = (soma * 10 % 11) % 10
        if int(cpf[i]) != digito:
            return False
    return True


def validar_email(email):
    """Validação simples de email."""
    if not email:
        return True  # opcional
    return bool(re.match(r'^[^@]+@[^@]+\.[^@]+$', email))


def validar_telefone(telefone):
    """Validação simples de telefone brasileiro."""
    nums = re.sub(r'[^0-9]', '', telefone)
    return len(nums) >= 10 and len(nums) <= 11


@alunos_bp.route("/")
@login_required
def listar():
    busca = request.args.get("busca", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Aluno.query
    if busca:
        query = query.filter(
            Aluno.nome.ilike(f"%{busca}%") | Aluno.cpf.ilike(f"%{busca}%")
        )

    pagination = query.order_by(Aluno.nome).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template(
        "alunos/listar.html",
        alunos=pagination.items,
        pagination=pagination,
        busca=busca,
    )


@alunos_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        cpf = request.form["cpf"].strip()
        telefone = request.form["telefone"].strip()
        
        # Validações
        erros = []
        if not nome:
            erros.append("Nome é obrigatório.")
        if not validar_cpf(cpf):
            erros.append("CPF inválido.")
        if not validar_telefone(telefone):
            erros.append("Telefone inválido. Use formato (00) 00000-0000.")
        
        if erros:
            for erro in erros:
                flash(erro, "danger")
            planos = Plano.query.filter_by(ativo=True).order_by(Plano.nome).all()
            return render_template("alunos/form.html", aluno=None, edicao=False, planos=planos, hoje=date.today().isoformat()), 400
        
        if Aluno.query.filter_by(cpf=cpf).first():
            flash("Já existe um aluno com este CPF.", "danger")
            planos = Plano.query.filter_by(ativo=True).order_by(Plano.nome).all()
            return render_template("alunos/form.html", aluno=None, edicao=False, planos=planos, hoje=date.today().isoformat()), 400
        
        aluno = Aluno(nome=nome, cpf=cpf, telefone=telefone)
        db.session.add(aluno)
        db.session.flush()

        # Criar matricula automaticamente
        plano_id = int(request.form["plano_id"])
        data_inicio = date.fromisoformat(request.form["data_inicio"])
        forma_pagamento = request.form.get("forma_pagamento", "pix").strip()

        plano = Plano.query.get_or_404(plano_id)
        data_fim = data_inicio + relativedelta(months=plano.duracao_meses)

        matricula = Matricula(
            aluno_id=aluno.id,
            plano_id=plano_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        db.session.add(matricula)
        db.session.flush()

        # Pagamento integral do plano no ato da matricula
        gerar_mensalidade_inicial(matricula, plano, data_inicio, forma_pagamento)

        db.session.commit()
        flash("Aluno cadastrado e matriculado com sucesso!", "success")
        return redirect(url_for("alunos.detalhes", id=aluno.id))

    planos = Plano.query.filter_by(ativo=True).order_by(Plano.nome).all()
    return render_template("alunos/form.html", aluno=None, edicao=False, planos=planos, hoje=date.today().isoformat())


@alunos_bp.route("/<int:id>")
@login_required
def detalhes(id):
    aluno = Aluno.query.get_or_404(id)
    return render_template("alunos/detalhes.html", aluno=aluno)


@alunos_bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar(id):
    aluno = Aluno.query.get_or_404(id)

    if request.method == "POST":
        nome = request.form["nome"].strip()
        telefone = request.form["telefone"].strip()
        email = request.form.get("email", "").strip() or None
        
        # Validações
        erros = []
        if not nome:
            erros.append("Nome é obrigatório.")
        if not validar_telefone(telefone):
            erros.append("Telefone inválido. Use formato (00) 00000-0000.")
        if email and not validar_email(email):
            erros.append("E-mail inválido.")
        
        if erros:
            for erro in erros:
                flash(erro, "danger")
            return render_template("alunos/form.html", aluno=aluno, edicao=True), 400
        
        aluno.nome = nome
        aluno.telefone = telefone
        aluno.email = email
        aluno.data_nascimento = _parse_date(request.form.get("data_nascimento"))
        aluno.ativo = "ativo" in request.form

        db.session.commit()
        flash("Aluno atualizado com sucesso!", "success")
        return redirect(url_for("alunos.detalhes", id=aluno.id))

    return render_template("alunos/form.html", aluno=aluno, edicao=True)


@alunos_bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
def excluir(id):
    aluno = Aluno.query.get_or_404(id)
    db.session.delete(aluno)
    db.session.commit()
    flash("Aluno excluido com sucesso!", "success")
    return redirect(url_for("alunos.listar"))


def _parse_date(date_str):
    if date_str:
        return date.fromisoformat(date_str)
    return None

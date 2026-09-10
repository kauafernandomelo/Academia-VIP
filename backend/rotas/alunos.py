from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, Aluno, Plano, Matricula
from regras import gerar_mensalidade_inicial

alunos_bp = Blueprint("alunos", __name__)


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
        aluno = Aluno(
            nome=request.form["nome"].strip(),
            cpf=request.form["cpf"].strip(),
            telefone=request.form["telefone"].strip(),
        )

        if Aluno.query.filter_by(cpf=aluno.cpf).first():
            flash("Ja existe um aluno com este CPF.", "danger")
            planos = Plano.query.filter_by(ativo=True).order_by(Plano.nome).all()
            return render_template("alunos/form.html", aluno=aluno, edicao=False, planos=planos, hoje=date.today().isoformat())

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
        aluno.nome = request.form["nome"].strip()
        aluno.telefone = request.form["telefone"].strip()
        aluno.email = request.form.get("email", "").strip() or None
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

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, Matricula, Aluno, Plano
from regras import gerar_mensalidade_inicial

matriculas_bp = Blueprint("matriculas", __name__)


@matriculas_bp.route("/")
@login_required
def listar():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "todas")

    query = Matricula.query
    if status == "ativas":
        query = query.filter_by(ativa=True)
    elif status == "encerradas":
        query = query.filter_by(ativa=False)

    pagination = query.order_by(Matricula.data_inicio.desc()).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template(
        "matriculas/listar.html",
        matriculas=pagination.items,
        pagination=pagination,
        status=status,
    )


@matriculas_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    if request.method == "POST":
        aluno_id = request.form.get("aluno_id", type=int)
        plano_id = request.form.get("plano_id", type=int)
        data_inicio_str = request.form.get("data_inicio", "").strip()
        forma_pagamento = request.form.get("forma_pagamento", "pix").strip()
        
        erros = []
        if not aluno_id:
            erros.append("Aluno é obrigatório.")
        if not plano_id:
            erros.append("Plano é obrigatório.")
        if not data_inicio_str:
            erros.append("Data de início é obrigatória.")
        
        if erros:
            for erro in erros:
                flash(erro, "danger")
            alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
            planos = Plano.query.filter_by(ativo=True).order_by(Plano.nome).all()
            return render_template("matriculas/form.html", alunos=alunos, planos=planos, matricula=None, hoje=date.today().isoformat()), 400
        
        try:
            data_inicio = date.fromisoformat(data_inicio_str)
        except ValueError:
            flash("Data de início inválida.", "danger")
            alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
            planos = Plano.query.filter_by(ativo=True).order_by(Plano.nome).all()
            return render_template("matriculas/form.html", alunos=alunos, planos=planos, matricula=None, hoje=date.today().isoformat()), 400
        
        aluno = Aluno.query.get_or_404(aluno_id)
        if not aluno.ativo:
            flash("Aluno está inativo. Ative o aluno antes de matricular.", "danger")
            alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
            planos = Plano.query.filter_by(ativo=True).order_by(Plano.nome).all()
            return render_template("matriculas/form.html", alunos=alunos, planos=planos, matricula=None, hoje=date.today().isoformat()), 400
        
        plano = Plano.query.get_or_404(plano_id)
        if not plano.ativo:
            flash("Plano está inativo.", "danger")
            alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
            planos = Plano.query.filter_by(ativo=True).order_by(Plano.nome).all()
            return render_template("matriculas/form.html", alunos=alunos, planos=planos, matricula=None, hoje=date.today().isoformat()), 400
        
        data_fim = data_inicio + relativedelta(months=plano.duracao_meses)
        
        if data_inicio > data_fim:
            flash("Data de início não pode ser posterior à data de fim.", "danger")
            alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
            planos = Plano.query.filter_by(ativo=True).order_by(Plano.nome).all()
            return render_template("matriculas/form.html", alunos=alunos, planos=planos, matricula=None, hoje=date.today().isoformat()), 400

        matricula = Matricula(
            aluno_id=aluno_id,
            plano_id=plano_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        db.session.add(matricula)
        db.session.flush()

        # Pagamento integral do plano no ato da matricula
        gerar_mensalidade_inicial(matricula, plano, data_inicio, forma_pagamento)

        db.session.commit()
        flash("Matrícula realizada com sucesso!", "success")
        return redirect(url_for("matriculas.detalhes", id=matricula.id))

    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
    planos = Plano.query.filter_by(ativo=True).order_by(Plano.nome).all()
    return render_template(
        "matriculas/form.html",
        alunos=alunos,
        planos=planos,
        matricula=None,
        hoje=date.today().isoformat(),
    )


@matriculas_bp.route("/<int:id>")
@login_required
def detalhes(id):
    matricula = Matricula.query.get_or_404(id)
    return render_template("matriculas/detalhes.html", matricula=matricula)


@matriculas_bp.route("/<int:id>/encerrar", methods=["POST"])
@login_required
def encerrar(id):
    matricula = Matricula.query.get_or_404(id)
    matricula.ativa = False
    db.session.commit()
    flash("Matrícula encerrada.", "info")
    return redirect(url_for("matriculas.detalhes", id=matricula.id))

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, Matricula, Aluno, Plano, Mensalidade

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
        aluno_id = int(request.form["aluno_id"])
        plano_id = int(request.form["plano_id"])
        data_inicio = date.fromisoformat(request.form["data_inicio"])

        plano = Plano.query.get_or_404(plano_id)
        data_fim = data_inicio + relativedelta(months=plano.duracao_meses)

        matricula = Matricula(
            aluno_id=aluno_id,
            plano_id=plano_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        db.session.add(matricula)
        db.session.flush()

        _gerar_mensalidades(matricula, plano, data_inicio)

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


def _gerar_mensalidades(matricula, plano, data_inicio):
    for i in range(plano.duracao_meses):
        vencimento = data_inicio + relativedelta(months=i)
        mensalidade = Mensalidade(
            matricula_id=matricula.id,
            valor=plano.valor,
            data_vencimento=vencimento,
        )
        db.session.add(mensalidade)

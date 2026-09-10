from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, Plano

planos_bp = Blueprint("planos", __name__)


@planos_bp.route("/")
@login_required
def listar():
    planos = Plano.query.order_by(Plano.nome).all()
    return render_template("planos/listar.html", planos=planos)


@planos_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if request.method == "POST":
        plano = Plano(
            nome=request.form["nome"].strip(),
            valor=float(request.form["valor"]),
            duracao_meses=int(request.form["duracao_meses"]),
            descricao=request.form.get("descricao", "").strip() or None,
        )

        db.session.add(plano)
        db.session.commit()
        flash("Plano criado com sucesso!", "success")
        return redirect(url_for("planos.listar"))

    return render_template("planos/form.html", plano=None, edicao=False)


@planos_bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar(id):
    plano = Plano.query.get_or_404(id)

    if request.method == "POST":
        plano.nome = request.form["nome"].strip()
        plano.valor = float(request.form["valor"])
        plano.duracao_meses = int(request.form["duracao_meses"])
        plano.descricao = request.form.get("descricao", "").strip() or None
        plano.ativo = "ativo" in request.form

        db.session.commit()
        flash("Plano atualizado com sucesso!", "success")
        return redirect(url_for("planos.listar"))

    return render_template("planos/form.html", plano=plano, edicao=True)


@planos_bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
def excluir(id):
    plano = Plano.query.get_or_404(id)

    if plano.matriculas:
        flash("Não é possível excluir um plano com matrículas vinculadas.", "danger")
        return redirect(url_for("planos.listar"))

    db.session.delete(plano)
    db.session.commit()
    flash("Plano excluído com sucesso!", "success")
    return redirect(url_for("planos.listar"))

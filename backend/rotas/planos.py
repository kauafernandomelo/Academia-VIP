import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, Plano

planos_bp = Blueprint("planos", __name__)


def validar_valor_monetario(valor_str):
    """Valida e converte valor monetário."""
    try:
        valor = float(valor_str.replace(',', '.'))
        return valor if valor > 0 else None
    except (ValueError, AttributeError):
        return None


def validar_duracao(duracao_str):
    """Valida duração em meses."""
    try:
        duracao = int(duracao_str)
        return duracao if 1 <= duracao <= 60 else None
    except (ValueError, AttributeError):
        return None


@planos_bp.route("/")
@login_required
def listar():
    planos = Plano.query.order_by(Plano.nome).all()
    return render_template("planos/listar.html", planos=planos)


@planos_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        valor = validar_valor_monetario(request.form.get("valor", ""))
        duracao = validar_duracao(request.form.get("duracao_meses", ""))
        descricao = request.form.get("descricao", "").strip() or None
        
        erros = []
        if not nome:
            erros.append("Nome é obrigatório.")
        if valor is None:
            erros.append("Valor inválido. Deve ser maior que zero.")
        if duracao is None:
            erros.append("Duração inválida. Deve ser entre 1 e 60 meses.")
        
        if erros:
            for erro in erros:
                flash(erro, "danger")
            return render_template("planos/form.html", plano=None, edicao=False), 400
        
        plano = Plano(nome=nome, valor=valor, duracao_meses=duracao, descricao=descricao)
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
        nome = request.form["nome"].strip()
        valor = validar_valor_monetario(request.form.get("valor", ""))
        duracao = validar_duracao(request.form.get("duracao_meses", ""))
        descricao = request.form.get("descricao", "").strip() or None
        
        erros = []
        if not nome:
            erros.append("Nome é obrigatório.")
        if valor is None:
            erros.append("Valor inválido. Deve ser maior que zero.")
        if duracao is None:
            erros.append("Duração inválida. Deve ser entre 1 e 60 meses.")
        
        if erros:
            for erro in erros:
                flash(erro, "danger")
            return render_template("planos/form.html", plano=plano, edicao=True), 400
        
        plano.nome = nome
        plano.valor = valor
        plano.duracao_meses = duracao
        plano.descricao = descricao
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

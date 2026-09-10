from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, Mensalidade, Pagamento

mensalidades_bp = Blueprint("mensalidades", __name__)


@mensalidades_bp.route("/")
@login_required
def listar():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "todas")

    query = Mensalidade.query
    if status == "pendentes":
        query = query.filter_by(paga=False).filter(
            Mensalidade.data_vencimento >= date.today()
        )
    elif status == "atrasadas":
        query = query.filter_by(paga=False).filter(
            Mensalidade.data_vencimento < date.today()
        )
    elif status == "pagas":
        query = query.filter_by(paga=True)

    pagination = query.order_by(Mensalidade.data_vencimento.desc()).paginate(
        page=page, per_page=15, error_out=False
    )

    return render_template(
        "mensalidades/listar.html",
        mensalidades=pagination.items,
        pagination=pagination,
        status=status,
    )


@mensalidades_bp.route("/<int:id>/pagar", methods=["GET", "POST"])
@login_required
def pagar(id):
    mensalidade = Mensalidade.query.get_or_404(id)

    if mensalidade.paga:
        flash("Esta mensalidade já foi paga.", "info")
        return redirect(url_for("mensalidades.listar"))

    if request.method == "POST":
        pagamento = Pagamento(
            mensalidade_id=mensalidade.id,
            valor_pago=float(request.form["valor_pago"]),
            data_pagamento=date.today(),
            forma_pagamento=request.form["forma_pagamento"],
            observacao=request.form.get("observacao", "").strip() or None,
        )

        mensalidade.paga = True
        mensalidade.data_pagamento = date.today()

        db.session.add(pagamento)
        db.session.commit()
        flash("Pagamento registrado com sucesso!", "success")
        return redirect(url_for("mensalidades.listar"))

    return render_template("mensalidades/pagar.html", mensalidade=mensalidade)

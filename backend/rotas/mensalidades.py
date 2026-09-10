from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, Mensalidade, Pagamento, Aluno

mensalidades_bp = Blueprint("mensalidades", __name__)


@mensalidades_bp.route("/")
@login_required
def listar():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "todas")
    q = request.args.get("q", "").strip()

    query = Mensalidade.query.join(Mensalidade.matricula).join(Aluno)

    if status == "pendentes":
        query = query.filter(Mensalidade.paga == False, Mensalidade.data_vencimento >= date.today())
    elif status == "atrasadas":
        query = query.filter(Mensalidade.paga == False, Mensalidade.data_vencimento < date.today())
    elif status == "pagas":
        query = query.filter(Mensalidade.paga == True)

    if q:
        ql = q.lower()
        query = query.filter(
            (Aluno.nome.ilike(f"%{q}%")) | (Aluno.cpf.like(f"%{q}%"))
        )

    pagination = query.order_by(Mensalidade.data_vencimento.desc()).paginate(
        page=page, per_page=15, error_out=False
    )

    return render_template(
        "mensalidades/listar.html",
        mensalidades=pagination.items,
        pagination=pagination,
        status=status,
        q=q,
    )


@mensalidades_bp.route("/<int:id>/pagar", methods=["GET", "POST"])
@login_required
def pagar(id):
    mensalidade = Mensalidade.query.get_or_404(id)

    if mensalidade.paga:
        flash("Esta mensalidade ja foi paga.", "info")
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

        # Encontrar proxima mensalidade
        proxima = Mensalidade.query.filter(
            Mensalidade.matricula_id == mensalidade.matricula_id,
            Mensalidade.paga == False,
            Mensalidade.id != mensalidade.id,
        ).order_by(Mensalidade.data_vencimento).first()

        return redirect(url_for("mensalidades.sucesso", pagamento_id=pagamento.id, proxima_id=proxima.id if proxima else None))

    return render_template("mensalidades/pagar.html", mensalidade=mensalidade)


@mensalidades_bp.route("/sucesso")
@login_required
def sucesso():
    pagamento_id = request.args.get("pagamento_id", type=int)
    proxima_id = request.args.get("proxima_id", type=int)

    pagamento = Pagamento.query.get_or_404(pagamento_id)
    proxima = Mensalidade.query.get(proxima_id) if proxima_id else None

    return render_template(
        "mensalidades/sucesso.html",
        pagamento=pagamento,
        proxima=proxima,
    )

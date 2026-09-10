from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, Mensalidade, Pagamento, Aluno
from regras import aplicar_pagamento

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


def validar_valor_pago(valor_str, valor_mensalidade):
    """Valida valor pago (não pode ser negativo nem muito maior que o valor da mensalidade)."""
    try:
        valor = float(valor_str.replace(',', '.'))
        if valor <= 0:
            return None
        # Permite até 1 centavo de diferença para arredondamento
        if valor > float(valor_mensalidade) + 0.01:
            return None
        return valor
    except (ValueError, AttributeError):
        return None


@mensalidades_bp.route("/<int:id>/pagar", methods=["GET", "POST"])
@login_required
def pagar(id):
    mensalidade = Mensalidade.query.get_or_404(id)

    if mensalidade.paga:
        flash("Esta mensalidade já foi paga.", "info")
        return redirect(url_for("mensalidades.listar"))

    if request.method == "POST":
        valor_pago = validar_valor_pago(request.form.get("valor_pago", ""), mensalidade.valor)
        forma_pagamento = request.form.get("forma_pagamento", "").strip()
        observacao = request.form.get("observacao", "").strip() or None
        
        erros = []
        if valor_pago is None:
            erros.append(f"Valor inválido. Deve ser entre 0.01 e {float(mensalidade.valor) + 0.01:.2f}.")
        if not forma_pagamento:
            erros.append("Forma de pagamento é obrigatória.")
        
        if erros:
            for erro in erros:
                flash(erro, "danger")
            return render_template("mensalidades/pagar.html", mensalidade=mensalidade), 400
        
        aplicar_pagamento(
            mensalidade,
            valor_pago=valor_pago,
            forma_pagamento=forma_pagamento,
            observacao=observacao,
        )
        db.session.commit()

        # Encontrar proxima mensalidade
        proxima = Mensalidade.query.filter(
            Mensalidade.matricula_id == mensalidade.matricula_id,
            Mensalidade.paga == False,
            Mensalidade.id != mensalidade.id,
        ).order_by(Mensalidade.data_vencimento).first()

        return redirect(url_for("mensalidades.sucesso", pagamento_id=mensalidade.pagamentos[-1].id if mensalidade.pagamentos else None, proxima_id=proxima.id if proxima else None))

    return render_template("mensalidades/pagar.html", mensalidade=mensalidade)


@mensalidades_bp.route("/sucesso")
@login_required
def sucesso():
    pagamento_id = request.args.get("pagamento_id", type=int)
    proxima_id = request.args.get("proxima_id", type=int)

    pagamento = Pagamento.query.get_or_404(pagamento_id)
    proxima = Mensalidade.query.get(proxima_id) if proxima_id else None
    matricula = pagamento.mensalidade.matricula if pagamento.mensalidade else None

    return render_template(
        "mensalidades/sucesso.html",
        pagamento=pagamento,
        proxima=proxima,
        matricula=matricula,
    )

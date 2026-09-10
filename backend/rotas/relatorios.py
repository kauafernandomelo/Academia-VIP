from datetime import date
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from models import db, Aluno, Matricula, Mensalidade, Pagamento

relatorios_bp = Blueprint("relatorios", __name__)


@relatorios_bp.route("/")
@login_required
def index():
    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year
    proximo_mes = hoje + relativedelta(months=1)

    # 1. FATURAMENTO DO MES ATUAL
    pagamentos_mes = (
        db.session.query(Pagamento)
        .join(Mensalidade)
        .filter(
            func.extract("month", Pagamento.data_pagamento) == mes_atual,
            func.extract("year", Pagamento.data_pagamento) == ano_atual,
        )
        .all()
    )
    total_faturamento = sum(float(p.valor_pago) for p in pagamentos_mes)

    # 2. INADIMPLENCIA (mensalidades atrasadas)
    mensalidades_atrasadas = (
        Mensalidade.query.filter_by(paga=False)
        .filter(Mensalidade.data_vencimento < hoje)
        .order_by(Mensalidade.data_vencimento)
        .all()
    )
    total_inadimplencia = sum(float(m.valor) for m in mensalidades_atrasadas)

    # 3. ESTIMATIVA PROXIMO MES
    mensalidades_proximo_mes = (
        Mensalidade.query.filter_by(paga=False)
        .filter(
            func.extract("month", Mensalidade.data_vencimento) == proximo_mes.month,
            func.extract("year", Mensalidade.data_vencimento) == proximo_mes.year,
        )
        .all()
    )
    total_estimativa = sum(float(m.valor) for m in mensalidades_proximo_mes)

    # 4. ALUNOS COM AVISO (faltam 7 dias ou menos)
    from datetime import timedelta
    data_limite = hoje + timedelta(days=7)
    mensalidades_aviso = (
        Mensalidade.query.filter_by(paga=False)
        .filter(
            Mensalidade.data_vencimento >= hoje,
            Mensalidade.data_vencimento <= data_limite,
        )
        .order_by(Mensalidade.data_vencimento)
        .all()
    )

    return render_template(
        "relatorios/index.html",
        pagamentos_mes=pagamentos_mes,
        total_faturamento=total_faturamento,
        mensalidades_atrasadas=mensalidades_atrasadas,
        total_inadimplencia=total_inadimplencia,
        mensalidades_proximo_mes=mensalidades_proximo_mes,
        total_estimativa=total_estimativa,
        mensalidades_aviso=mensalidades_aviso,
        mes_atual=mes_atual,
        ano_atual=ano_atual,
        proximo_mes=proximo_mes,
        meses=[
            "",
            "Janeiro",
            "Fevereiro",
            "Marco",
            "Abril",
            "Maio",
            "Junho",
            "Julho",
            "Agosto",
            "Setembro",
            "Outubro",
            "Novembro",
            "Dezembro",
        ],
        hoje=hoje,
    )

"""Service layer para relatórios - lógica de negócio separada das rotas."""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from models import db, Aluno, Matricula, Mensalidade, Pagamento
from regras import garantir_renovacoes
# MESES duplicado aqui para evitar problemas de import circular/config
MESES = [
    "", "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def calcular_perfil_pagamento(aluno):
    """Calcula o perfil de pagamento de um aluno baseado no histórico."""
    pagamentos = (
        db.session.query(Pagamento)
        .join(Mensalidade)
        .join(Matricula)
        .filter(Matricula.aluno_id == aluno.id, Pagamento.data_pagamento.isnot(None))
        .all()
    )
    if not pagamentos:
        return {"dias_medio": 0, "tendencia": "Sem dados", "status": "sem_dados", "total_pagamentos": 0}

    dias_atraso = []
    for p in pagamentos:
        if p.mensalidade and p.data_pagamento and p.mensalidade.data_vencimento:
            delta = (p.data_pagamento - p.mensalidade.data_vencimento).days
            dias_atraso.append(delta)

    if not dias_atraso:
        return {"dias_medio": 0, "tendencia": "Sem dados", "status": "sem_dados", "total_pagamentos": len(pagamentos)}

    media = sum(dias_atraso) / len(dias_atraso)

    if media <= 0:
        status = "pontual"
        tendencia = "✅ Pontual"
    elif media <= 3:
        status = "levemente_atrasado"
        tendencia = "⚠️ Levemente atrasado"
    else:
        status = "sempre_atrasado"
        tendencia = "🔴 Sempre atrasado"

    return {
        "dias_medio": round(media, 1),
        "tendencia": tendencia,
        "status": status,
        "total_pagamentos": len(pagamentos),
    }


def obter_dados_relatorios(hoje=None):
    """
    Obtém todos os dados necessários para os relatórios.
    
    Args:
        hoje: date para usar como referência (padrão: date.today())
              Útil para testes com datas fixas.
    
    Returns:
        dict com todos os dados agregados para relatórios.
    """
    hoje = hoje or date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year
    proximo_mes = hoje + relativedelta(months=1)

    # Garantir cobranças de renovação para aparecerem nos relatórios
    garantir_renovacoes(hoje)

    # 1. FATURAMENTO DO MÊS ATUAL
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

    # 2. INADIMPLÊNCIA
    mensalidades_atrasadas = (
        Mensalidade.query.filter_by(paga=False)
        .filter(Mensalidade.data_vencimento < hoje)
        .order_by(Mensalidade.data_vencimento)
        .all()
    )
    total_inadimplencia = sum(float(m.valor) for m in mensalidades_atrasadas)

    # 3. ESTIMATIVA PRÓXIMO MÊS - apenas cobranças reais pendentes + planos mensais
    matriculas_ativas = Matricula.query.filter_by(ativa=True).all()
    estimativas = []
    for mat in matriculas_ativas:
        # Cobrança (renovação ou mensalidade) pendente no próximo mês?
        pendente_prox = None
        for m in mat.mensalidades:
            if (
                not m.paga
                and m.data_vencimento.month == proximo_mes.month
                and m.data_vencimento.year == proximo_mes.year
            ):
                pendente_prox = m
                break

        if pendente_prox:
            estimativas.append({
                "aluno": mat.aluno.nome,
                "plano": mat.plano.nome,
                "valor": float(pendente_prox.valor),
                "vencimento": pendente_prox.data_vencimento,
                "status": "pendente",
            })
        elif mat.plano.duracao_meses == 1:
            # Plano mensal: projeta a cobrança do próximo mês (se ainda não existir)
            estimativas.append({
                "aluno": mat.aluno.nome,
                "plano": mat.plano.nome,
                "valor": float(mat.plano.valor),
                "vencimento": hoje + relativedelta(months=1, day=mat.data_inicio.day),
                "status": "estimado",
            })
        # else: planos integrais (trimestral/semestral/anual) já pagos até data_fim,
        # sem cobrança de renovação pendente -> não entram na projeção

    total_estimativa = sum(e["valor"] for e in estimativas)

    # 4. ALUNOS COM AVISO (faltam 7 dias ou menos)
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

    # 5. PERFIL DE PAGAMENTO DOS ALUNOS
    alunos_ativos = Aluno.query.filter_by(ativo=True).all()
    perfis = []
    for aluno in alunos_ativos:
        perfil = calcular_perfil_pagamento(aluno)
        if perfil["total_pagamentos"] > 0:
            perfis.append({"aluno": aluno.nome, **_perfil_para_dict(perfil)})
    perfis.sort(key=lambda x: x["dias_medio"], reverse=True)

    # 6. DADOS PARA GRÁFICOS
    # Últimos 6 meses de faturamento
    faturamento_mensal = []
    for i in range(5, -1, -1):
        data_ref = hoje - relativedelta(months=i)
        pagamentos = (
            db.session.query(Pagamento)
            .join(Mensalidade)
            .filter(
                func.extract("month", Pagamento.data_pagamento) == data_ref.month,
                func.extract("year", Pagamento.data_pagamento) == data_ref.year,
            )
            .all()
        )
        total = sum(float(p.valor_pago) for p in pagamentos)
        faturamento_mensal.append({"mes": MESES[data_ref.month], "valor": total})

    # Status das mensalidades do mês atual
    todas_mensalidades_mes = Mensalidade.query.filter(
        func.extract("month", Mensalidade.data_vencimento) == mes_atual,
        func.extract("year", Mensalidade.data_vencimento) == ano_atual,
    ).all()
    status_count = {"pagas": 0, "pendentes": 0, "atrasadas": 0}
    for m in todas_mensalidades_mes:
        if m.paga:
            status_count["pagas"] += 1
        elif m.esta_atrasada:
            status_count["atrasadas"] += 1
        else:
            status_count["pendentes"] += 1

    return {
        "pagamentos_mes": pagamentos_mes,
        "total_faturamento": total_faturamento,
        "mensalidades_atrasadas": mensalidades_atrasadas,
        "total_inadimplencia": total_inadimplencia,
        "estimativas": estimativas,
        "total_estimativa": total_estimativa,
        "mensalidades_aviso": mensalidades_aviso,
        "perfis": perfis,
        "faturamento_mensal": faturamento_mensal,
        "status_count": status_count,
        "mes_atual": mes_atual,
        "ano_atual": ano_atual,
        "proximo_mes": proximo_mes,
        "hoje": hoje,
    }


def _perfil_para_dict(perfil):
    """Converte perfil em dict para serialização."""
    return {
        "dias_medio": perfil["dias_medio"],
        "tendencia": perfil["tendencia"],
        "status": perfil["status"],
        "total_pagamentos": perfil["total_pagamentos"],
    }


def filtrar_dados_por_busca(dados, query_str):
    """Filtra todos os dados do relatório por termo de busca (nome/CPF)."""
    if not query_str:
        return dados
    
    ql = query_str.lower()
    
    return {
        **dados,
        "pagamentos_mes": [
            p for p in dados["pagamentos_mes"]
            if ql in p.mensalidade.matricula.aluno.nome.lower()
            or query_str in p.mensalidade.matricula.aluno.cpf
        ],
        "mensalidades_atrasadas": [
            m for m in dados["mensalidades_atrasadas"]
            if ql in m.matricula.aluno.nome.lower()
            or query_str in m.matricula.aluno.cpf
        ],
        "estimativas": [
            e for e in dados["estimativas"]
            if ql in e["aluno"].lower()
        ],
        "mensalidades_aviso": [
            m for m in dados["mensalidades_aviso"]
            if ql in m.matricula.aluno.nome.lower()
            or query_str in m.matricula.aluno.cpf
        ],
        "perfis": [
            p for p in dados["perfis"]
            if ql in p["aluno"].lower()
        ],
    }


def paginar(lista, page, per_page=10):
    """Pagina uma lista."""
    total = len(lista)
    start = (page - 1) * per_page
    end = start + per_page
    pages = max(1, (total + per_page - 1) // per_page)
    return {
        "lista": lista[start:end],
        "page": min(page, pages),
        "total": total,
        "pages": pages,
    }
"""Regras de negocio: cobranca integral no ato da matricula e renovacao do plano.

Nova regra (unificada):
- No ato da matricula, o plano inteiro e pago de uma vez (Mensal = 1 mes,
  Trimestral = 3, Semestral = 6, Anual = 12). Nao ha cobrancas mensais
  separadas durante o periodo.
- Quando faltar JANELA_RENOVACAO dias (ou ja tiver vencido), o sistema cria
  UMA cobranca de renovacao com o valor cheio do plano.
"""

from datetime import date
from dateutil.relativedelta import relativedelta
from models import db, Matricula, Mensalidade, Pagamento

JANELA_RENOVACAO = 7


def gerar_mensalidade_inicial(matricula, plano, data_inicio, forma_pagamento="pix", observacao=None):
    """Registra o pagamento integral do plano no ato da matricula.

    Cria uma unica mensalidade paga (valor cheio do plano) e o Pagamento
    correspondente, para que o faturamento registre a receita real.
    """
    mensalidade = Mensalidade(
        matricula_id=matricula.id,
        valor=plano.valor,
        data_vencimento=data_inicio,
        paga=True,
        data_pagamento=data_inicio,
    )
    db.session.add(mensalidade)
    db.session.flush()

    pagamento = Pagamento(
        mensalidade_id=mensalidade.id,
        valor_pago=plano.valor,
        data_pagamento=data_inicio,
        forma_pagamento=forma_pagamento,
        observacao=observacao or f"Pagamento integral do plano {plano.nome}",
    )
    db.session.add(pagamento)
    return mensalidade


def garantir_renovacao(matricula, hoje=None):
    """Cria a cobranca de renovacao quando o plano estiver perto de vencer.

    Regra: faltam <= JANELA_RENOVACAO dias para data_fim (ou a data ja
    passou) e ainda nao existe nenhuma mensalidade com vencimento = data_fim.
    O vencimento da renovacao e a propria data de expiracao do plano.
    """
    if not matricula.ativa or not matricula.plano:
        return None
    hoje = hoje or date.today()
    if (matricula.data_fim - hoje).days > JANELA_RENOVACAO:
        return None

    ja_existe = Mensalidade.query.filter_by(
        matricula_id=matricula.id, data_vencimento=matricula.data_fim
    ).first()
    if ja_existe:
        return ja_existe

    renovacao = Mensalidade(
        matricula_id=matricula.id,
        valor=matricula.plano.valor,
        data_vencimento=matricula.data_fim,
        paga=False,
    )
    db.session.add(renovacao)
    db.session.flush()
    return renovacao


def garantir_renovacoes(hoje=None):
    """Garante as cobrancas de renovacao de todas as matriculas ativas."""
    hoje = hoje or date.today()
    for matricula in Matricula.query.filter_by(ativa=True).all():
        garantir_renovacao(matricula, hoje)
    db.session.commit()


def eh_renovacao(mensalidade):
    """True se a mensalidade for a cobranca de renovacao do plano."""
    return mensalidade.data_vencimento >= mensalidade.matricula.data_fim


def aplicar_pagamento(mensalidade, valor_pago, forma_pagamento, data_pagamento=None, observacao=None):
    """Marca a mensalidade como paga e estende o plano quando for renovacao."""
    data_pagamento = data_pagamento or date.today()

    pagamento = Pagamento(
        mensalidade_id=mensalidade.id,
        valor_pago=valor_pago,
        data_pagamento=data_pagamento,
        forma_pagamento=forma_pagamento,
        observacao=observacao,
    )
    mensalidade.paga = True
    mensalidade.data_pagamento = data_pagamento
    db.session.add(pagamento)

    matricula = mensalidade.matricula
    if matricula and matricula.plano and eh_renovacao(mensalidade):
        matricula.data_fim = max(matricula.data_fim, data_pagamento) + relativedelta(
            months=matricula.plano.duracao_meses
        )
        matricula.ativa = True

    return pagamento


def corrigir_dados_legados():
    """Corrige dados criados com a regra antiga (mensalidades fracionadas).

    Para cada matricula ativa:
      1. Localiza a primeira mensalidade paga (data_vencimento = data_inicio).
         Se existir mais de uma com vencimento = data_inicio, mescla pagamentos
         para ficar apenas uma.
      2. Exclui mensalidades NAO pagas durante a vigencia do plano
         (vencimento > data_inicio E < data_fim) — sao as "fantasmas" da
         regra antiga.
      3. Se a matricula esta vencida mas nao tem renovacao pendente, marca
         como inativa (sera reativada quando o aluno pagar).
    """
    from datetime import datetime as dt

    matriculas_corrigidas = 0
    mensalidades_removidas = 0

    for mat in Matricula.query.all():
        if not mat.plano:
            continue

        mensalidades = Mensalidade.query.filter_by(matricula_id=mat.id).order_by(
            Mensalidade.data_vencimento
        ).all()

        if not mensalidades:
            continue

        # Separar: integral paga (vencimento == data_inicio), fantasmas nao pagas, renovacao pendente
        integral = [m for m in mensalidades if m.data_vencimento == mat.data_inicio and m.paga]
        fantasmas = [m for m in mensalidades if m.data_vencimento > mat.data_inicio and m.data_vencimento < mat.data_fim and not m.paga]
        renovacao_pendente = [m for m in mensalidades if m.data_vencimento >= mat.data_fim and not m.paga]

        # Se tem integral, garantir que so existe UMA (mesclar pagamentos se duplicada)
        if integral and len(integral) > 1:
            keeps = integral[0]
            for dup in integral[1:]:
                # Mover pagamentos para a primeira
                for pg in Pagamento.query.filter_by(mensalidade_id=dup.id).all():
                    pg.mensalidade_id = keeps.id
                db.session.delete(dup)
                db.session.flush()

        # Se NAO tem integral, e a matricula era do tipo "antigo" com mensalidades fracionadas
        # Reconstruir: pegar todos os pagos e criar UMA integral se necessario
        if not integral:
            pagas = [m for m in mensalidades if m.paga]
            if pagas:
                total_pago = sum(float(p.valor_pago) for p in pagas
                                for p in Pagamento.query.filter_by(mensalidade_id=p.id).all())
                if total_pago > 0:
                    # Pegar a primeira data de pagamento
                    primeiro_pag = min(
                        (p.data_pagamento for p in pagas
                         for pg in Pagamento.query.filter_by(mensalidade_id=p.id).all()),
                        default=mat.data_inicio,
                    )
                    # Criar integral
                    int_mens = Mensalidade(
                        matricula_id=mat.id,
                        valor=mat.plano.valor,
                        data_vencimento=mat.data_inicio,
                        paga=True,
                        data_pagamento=primeiro_pag,
                    )
                    db.session.add(int_mens)
                    db.session.flush()

                    # Mover pagamentos antigos para a integral
                    for p in pagas:
                        for pg in Pagamento.query.filter_by(mensalidade_id=p.id).all():
                            pg.mensalidade_id = int_mens.id
                        db.session.delete(p)
                        db.session.flush()

        # Excluir fantasmas nao pagas durante a vigencia
        for f in fantasmas:
            db.session.delete(f)
            mensalidades_removidas += 1

        # Se matricula vencida e sem renovacao pendente, desativar
        hoje = date.today()
        if mat.data_fim < hoje and not renovacao_pendente:
            mat.ativa = False

        matriculas_corrigidas += 1

    db.session.commit()
    return matriculas_corrigidas, mensalidades_removidas
"""Testes de regras de negocio (regras.py)."""

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from helpers import criar_aluno_com_matricula
from models import db, Matricula, Mensalidade, Pagamento
from regras import (
    aplicar_pagamento,
    corrigir_dados_legados,
    eh_renovacao,
    garantir_renovacao,
    garantir_renovacoes,
    gerar_mensalidade_inicial,
)


class TestGerarMensalidadeInicial:
    def test_cria_uma_mensalidade_paga(self, app, plano_trimestral):
        with app.app_context():
            hoje = date.today()
            _, matricula = criar_aluno_com_matricula(plano_trimestral, hoje)

            mensalidades = Mensalidade.query.filter_by(matricula_id=matricula.id).all()
            assert len(mensalidades) == 1
            m = mensalidades[0]
            assert m.paga is True
            assert float(m.valor) == 175.50  # valor cheio do plano
            assert m.data_vencimento == hoje

            pagamentos = Pagamento.query.filter_by(mensalidade_id=m.id).all()
            assert len(pagamentos) == 1
            assert float(pagamentos[0].valor_pago) == 175.50

    def test_nao_cria_cobrancas_mensais(self, app, plano_trimestral):
        with app.app_context():
            hoje = date.today()
            _, matricula = criar_aluno_com_matricula(plano_trimestral, hoje)

            # Plano de 3 meses deve ter SO 1 mensalidade (integral paga)
            meses_do_plano = plano_trimestral.duracao_meses
            total = Mensalidade.query.filter_by(matricula_id=matricula.id).count()
            assert total == 1, f"Esperava 1 mensalidade integral, achei {total} (plano de {meses_do_plano}m)"


class TestGarantirRenovacao:
    def test_cria_renovacao_faltando_7_dias(self, app, plano_mensal):
        with app.app_context():
            hoje = date.today()
            # Matricula comeca 1 mes antes -> vence hoje (dentro da janela)
            inicio = hoje - relativedelta(months=1)
            _, matricula = criar_aluno_com_matricula(plano_mensal, inicio)

            ren = garantir_renovacao(matricula, hoje)
            db.session.commit()

            assert ren is not None
            assert ren.paga is False
            assert ren.data_vencimento == matricula.data_fim
            assert float(ren.valor) == 65.00

    def test_nao_cria_renovacao_fora_da_janela(self, app, plano_mensal):
        with app.app_context():
            hoje = date.today()
            # Vence em 30 dias -> fora da janela de 7
            inicio = hoje - relativedelta(months=1) + relativedelta(days=30)
            _, matricula = criar_aluno_com_matricula(plano_mensal, inicio)

            ren = garantir_renovacao(matricula, hoje)
            assert ren is None

    def test_nao_duplica_renovacao(self, app, plano_mensal):
        with app.app_context():
            hoje = date.today()
            inicio = hoje - relativedelta(months=1)
            _, matricula = criar_aluno_com_matricula(plano_mensal, inicio)

            garantir_renovacao(matricula, hoje)
            garantir_renovacao(matricula, hoje)
            db.session.commit()

            total = Mensalidade.query.filter_by(matricula_id=matricula.id, paga=False).count()
            assert total == 1

    def test_nao_cria_renovacao_para_matricula_inativa(self, app, plano_mensal):
        with app.app_context():
            hoje = date.today()
            inicio = hoje - relativedelta(months=2)
            _, matricula = criar_aluno_com_matricula(plano_mensal, inicio)
            matricula.ativa = False
            db.session.commit()

            ren = garantir_renovacao(matricula, hoje)
            assert ren is None


class TestEhRenovacao:
    def test_renovacao_reconhecida(self, app, plano_mensal):
        with app.app_context():
            hoje = date.today()
            inicio = hoje - relativedelta(months=1)
            _, matricula = criar_aluno_com_matricula(plano_mensal, inicio)
            ren = garantir_renovacao(matricula, hoje)
            assert eh_renovacao(ren) is True

    def test_integral_nao_e_renovacao(self, app, plano_mensal):
        with app.app_context():
            hoje = date.today()
            _, matricula = criar_aluno_com_matricula(plano_mensal, hoje)
            integral = matricula.mensalidades[0]
            assert eh_renovacao(integral) is False


class TestAplicarPagamento:
    def test_renovacao_paga_estende_plano(self, app, plano_trimestral):
        with app.app_context():
            hoje = date.today()
            inicio = hoje - relativedelta(months=3)
            _, matricula = criar_aluno_com_matricula(plano_trimestral, inicio)
            data_fim_original = matricula.data_fim

            ren = garantir_renovacao(matricula, hoje)
            db.session.commit()

            aplicar_pagamento(ren, 175.50, "pix", data_pagamento=hoje)
            db.session.commit()

            assert ren.paga is True
            esperado = max(data_fim_original, hoje) + relativedelta(months=3)
            assert matricula.data_fim == esperado
            assert matricula.data_fim > data_fim_original
            assert matricula.ativa is True

    def test_pagamento_gera_pagamento(self, app, plano_trimestral):
        with app.app_context():
            hoje = date.today()
            inicio = hoje - relativedelta(months=3)
            _, matricula = criar_aluno_com_matricula(plano_trimestral, inicio)
            ren = garantir_renovacao(matricula, hoje)
            db.session.commit()

            pag = aplicar_pagamento(ren, 175.50, "cartao_credito", data_pagamento=hoje)
            db.session.commit()

            assert pag.valor_pago == 175.50
            assert pag.forma_pagamento == "cartao_credito"
            assert len(ren.pagamentos) == 1


class TestCorrigirDadosLegados:
    def test_mescla_mensalidades_fracionadas(self, app, plano_trimestral):
        """Dados antigos com mensalidades mensais: fantasmas removidas, integral paga mantida."""
        with app.app_context():
            hoje = date.today()
            inicio = hoje - relativedelta(months=1)
            _, matricula = criar_aluno_com_matricula(plano_trimestral, inicio)

            # Simular regra antiga: remover integral e criar 3 mensais fracionadas
            Mensalidade.query.filter_by(matricula_id=matricula.id).delete()
            db.session.commit()

            valor_mensal = 175.50 / 3
            for j in range(3):
                venc = inicio + relativedelta(months=j)
                m = Mensalidade(
                    matricula_id=matricula.id,
                    valor=valor_mensal,
                    data_vencimento=venc,
                    paga=j == 0,
                    data_pagamento=venc if j == 0 else None,
                )
                db.session.add(m)
                db.session.flush()
                if j == 0:
                    db.session.add(Pagamento(
                        mensalidade_id=m.id,
                        valor_pago=valor_mensal,
                        data_pagamento=venc,
                        forma_pagamento="pix",
                    ))
            db.session.commit()

            total_antes = Mensalidade.query.filter_by(matricula_id=matricula.id).count()
            assert total_antes == 3

            corrigir_dados_legados()

            mensalidades = Mensalidade.query.filter_by(matricula_id=matricula.id).all()
            # Fantasmas nao pagas durante a vigencia foram removidas
            nao_pagas = [m for m in mensalidades if not m.paga]
            assert len(nao_pagas) == 0
            # A integral paga (data_vencimento == data_inicio) continua existindo
            pagas = [m for m in mensalidades if m.paga]
            assert len(pagas) == 1
            assert pagas[0].data_vencimento == matricula.data_inicio

    def test_remove_fantasmas_nao_pagas(self, app, plano_trimestral):
        with app.app_context():
            hoje = date.today()
            inicio = hoje - relativedelta(months=1)
            _, matricula = criar_aluno_com_matricula(plano_trimestral, inicio)

            # Adicionar 2 mensalidades fantasma NAO pagas durante a vigencia
            for j in [1, 2]:
                venc = inicio + relativedelta(months=j)
                db.session.add(Mensalidade(
                    matricula_id=matricula.id,
                    valor=65.00,
                    data_vencimento=venc,
                    paga=False,
                ))
            db.session.commit()

            total_antes = Mensalidade.query.filter_by(matricula_id=matricula.id).count()
            assert total_antes == 3  # integral + 2 fantasmas

            corrigir_dados_legados()

            total_depois = Mensalidade.query.filter_by(matricula_id=matricula.id).count()
            assert total_depois == 1  # so a integral

    def test_desativa_matricula_vencida_sem_renovacao(self, app, plano_mensal):
        with app.app_context():
            hoje = date.today()
            inicio = hoje - relativedelta(months=2)
            _, matricula = criar_aluno_com_matricula(plano_mensal, inicio)
            # Matricula vencida ha 1 mes, sem renovacao pendente
            assert matricula.data_fim < hoje
            assert matricula.ativa is True

            corrigir_dados_legados()
            db.session.refresh(matricula)
            assert matricula.ativa is False


class TestGarantirRenovacoes:
    def test_processa_todas_matriculas(self, app, plano_mensal, plano_trimestral):
        with app.app_context():
            hoje = date.today()
            # Matricula vencendo hoje (dentro da janela de 7 dias) -> renovação
            criar_aluno_com_matricula(plano_mensal, hoje - relativedelta(months=1))
            # Matricula trimestral com data_fim 3 meses no futuro -> fora da janela
            criar_aluno_com_matricula(plano_trimestral, hoje - relativedelta(days=5))
            # Matricula longe de vencer -> sem renovacao
            criar_aluno_com_matricula(plano_mensal, hoje)

            garantir_renovacoes(hoje)

            renovacoes = Mensalidade.query.filter_by(paga=False).count()
            # Apenas 1 renovacao (o mensal que vence hoje)
            assert renovacoes == 1
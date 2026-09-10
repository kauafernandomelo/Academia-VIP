"""Testes de integracao das rotas (autenticacao, alunos, mensalidades, relatorios)."""

import io
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from helpers import criar_aluno_com_matricula
from models import Aluno, Matricula, Mensalidade, Pagamento, Plano, db
from regras import garantir_renovacao


class TestAutenticacao:
    def test_login_ok(self, app, cliente):
        resp = cliente.post("/login", data={"login": "admin", "senha": "admin123"})
        assert resp.status_code == 302
        assert "/" in resp.headers["Location"]

    def test_login_errado(self, cliente):
        resp = cliente.post("/login", data={"login": "admin", "senha": "errada"})
        assert resp.status_code == 200
        assert "Login ou senha incorretos" in resp.get_data(as_text=True)

    def test_dashboard_exige_login(self, cliente):
        resp = cliente.get("/")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_logout(self, aluno_logado):
        cliente = aluno_logado
        resp = cliente.get("/logout")
        assert resp.status_code == 302


class TestAlunos:
    def test_listar_alunos(self, aluno_logado, plano_mensal):
        with aluno_logado.application.app_context():
            criar_aluno_com_matricula(plano_mensal, date.today())
        resp = aluno_logado.get("/alunos/")
        assert resp.status_code == 200
        assert "Aluno Teste" in resp.get_data(as_text=True)

    def test_cadastrar_aluno_integral(self, aluno_logado, app):
        resp = aluno_logado.post("/alunos/novo", data={
            "nome": "Novo Aluno",
            "cpf": "999.999.999-99",
            "telefone": "(11) 98888-8888",
            "plano_id": "1",
            "data_inicio": date.today().isoformat(),
            "forma_pagamento": "pix",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert "Novo Aluno" in resp.get_data(as_text=True)

        with app.app_context():
            aluno = Aluno.query.filter_by(cpf="999.999.999-99").first()
            assert aluno is not None
            mat = Matricula.query.filter_by(aluno_id=aluno.id).first()
            assert mat is not None
            mensalidades = Mensalidade.query.filter_by(matricula_id=mat.id).all()
            # So 1 mensalidade (integral paga)
            assert len(mensalidades) == 1
            assert mensalidades[0].paga is True
            assert float(mensalidades[0].valor) == float(mat.plano.valor)

    def test_busca_aluno(self, aluno_logado, plano_mensal):
        with aluno_logado.application.app_context():
            criar_aluno_com_matricula(plano_mensal, date.today())
        resp = aluno_logado.get("/alunos/?q=Teste")
        assert resp.status_code == 200
        assert "Aluno Teste" in resp.get_data(as_text=True)


class TestMensalidades:
    def test_listar_com_renovacao(self, aluno_logado, app, plano_mensal):
        with app.app_context():
            hoje = date.today()
            inicio = hoje - relativedelta(months=1)
            _, matricula = criar_aluno_com_matricula(plano_mensal, inicio)
            garantir_renovacao(matricula, hoje)
            db.session.commit()

        resp = aluno_logado.get("/mensalidades/")
        assert resp.status_code == 200
        texto = resp.get_data(as_text=True)
        assert "Aluno Teste" in texto
        assert "Renovacao do plano" in texto

    def test_pagar_renovacao_estende_plano(self, aluno_logado, app, plano_mensal):
        with app.app_context():
            hoje = date.today()
            inicio = hoje - relativedelta(months=1)
            _, matricula = criar_aluno_com_matricula(plano_mensal, inicio)
            ren = garantir_renovacao(matricula, hoje)
            db.session.commit()
            ren_id = ren.id
            data_fim_original = matricula.data_fim

        resp = aluno_logado.post(f"/mensalidades/{ren.id}/pagar", data={
            "valor_pago": "65.00",
            "forma_pagamento": "pix",
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            ren2 = Mensalidade.query.get(ren_id)
            assert ren2.paga is True
            mat = ren2.matricula
            assert mat.data_fim > data_fim_original
            assert mat.ativa is True

    def test_sucesso_sem_proxima_cobranca(self, aluno_logado, app, plano_trimestral):
        """Apos pagar renovacao, mostra a validade do plano."""
        with app.app_context():
            hoje = date.today()
            inicio = hoje - relativedelta(months=3)
            _, matricula = criar_aluno_com_matricula(plano_trimestral, inicio)
            ren = garantir_renovacao(matricula, hoje)
            db.session.commit()
            ren_id = ren.id

        resp = aluno_logado.post(f"/mensalidades/{ren_id}/pagar", data={
            "valor_pago": "175.50",
            "forma_pagamento": "pix",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert "Plano vigente" in resp.get_data(as_text=True)


class TestRelatorios:
    def test_pagina_relatorios(self, aluno_logado, plano_mensal):
        with aluno_logado.application.app_context():
            criar_aluno_com_matricula(plano_mensal, date.today())
        resp = aluno_logado.get("/relatorios/")
        assert resp.status_code == 200

    def test_baixar_pdf(self, aluno_logado, plano_mensal):
        with aluno_logado.application.app_context():
            criar_aluno_com_matricula(plano_mensal, date.today())
        resp = aluno_logado.get("/relatorios/pdf")
        assert resp.status_code == 200
        assert resp.content_type.startswith("application/pdf")
        assert resp.data.startswith(b"%PDF")

    def test_baixar_excel(self, aluno_logado, plano_mensal):
        with aluno_logado.application.app_context():
            criar_aluno_com_matricula(plano_mensal, date.today())
        resp = aluno_logado.get("/relatorios/excel")
        assert resp.status_code == 200
        assert resp.content_type.startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        assert resp.data[:2] == b"PK"


class TestDashboard:
    def test_dashboard_carregado(self, aluno_logado, plano_mensal):
        with aluno_logado.application.app_context():
            criar_aluno_com_matricula(plano_mensal, date.today())
        resp = aluno_logado.get("/")
        assert resp.status_code == 200
        assert "Dashboard" in resp.get_data(as_text=True)
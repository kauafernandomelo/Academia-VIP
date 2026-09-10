#!/usr/bin/env python3
"""
Script de seed - Gera 100 alunos aleatorios com cobranca integral
Roda: cd backend && python seed.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from app import criar_app
from models import db, Aluno, Plano, Matricula, Mensalidade, Pagamento
from scripts.seed_utils import criar_alunos_com_matriculas, imprimir_resumo_seed


def criar_seed():
    app = criar_app()

    with app.app_context():
        print("Limpando dados antigos...")
        Pagamento.query.delete()
        Mensalidade.query.delete()
        Matricula.query.delete()
        Aluno.query.delete()
        db.session.commit()

        print("Buscando planos...")
        planos = Plano.query.filter_by(ativo=True).order_by(Plano.valor).all()
        if not planos:
            print("ERRO: Nenhum plano encontrado. Execute init_db.py primeiro.")
            return

        print(f"Planos encontrados: {[p.nome for p in planos]}")

        hoje = date.today()
        
        alunos_criados, mensalidades_criadas, pagamentos, renovacoes = criar_alunos_com_matriculas(
            qtd=100,
            planos=planos,
            hoje=hoje,
            cpfs_existentes=set(),  # banco limpo
        )
        
        db.session.commit()
        imprimir_resumo_seed(alunos_criados, mensalidades_criadas, pagamentos, renovacoes, hoje)


if __name__ == "__main__":
    criar_seed()
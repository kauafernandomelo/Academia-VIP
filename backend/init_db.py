"""Script para inicializar o banco de dados, criar o primeiro administrador, planos padrao e 100 alunos de teste.

Inclui:
- Correcao automatica de dados legados (regra antiga com mensalidades fracionadas)
- Seed de 100 alunos com cobranca integral (1 pagamento pelo valor cheio do plano)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from app import criar_app
from models import db, Usuario, Plano, Aluno, Mensalidade, Pagamento
from regras import corrigir_dados_legados
from scripts.seed_utils import criar_alunos_com_matriculas, imprimir_resumo_seed


app = criar_app()

with app.app_context():
    db.create_all()

    # --- Correcao de dados legados ---
    total_mensalidades_antes = Mensalidade.query.count()
    if total_mensalidades_antes > 0:
        print(f"\nBanco contem {total_mensalidades_antes} mensalidades. Verificando dados legados...")
        corrigidos, removidos = corrigir_dados_legados()
        print(f"  Matriculas corrigidas: {corrigidos}")
        print(f"  Mensalidades fantasmas removidas: {removidos}")

    # --- Administrador ---
    if not Usuario.query.filter_by(login="admin").first():
        admin = Usuario(nome="Administrador", login="admin", admin=True)
        admin.definir_senha("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Administrador criado: admin / admin123")
    else:
        print("Administrador ja existe.")

    # --- Planos padrao ---
    planos_padrao = [
        {"nome": "Mensal", "valor": 65.00, "duracao_meses": 1, "descricao": "Plano mensal sem desconto"},
        {"nome": "Trimestral", "valor": 175.50, "duracao_meses": 3, "descricao": "Plano trimestral com 10% de desconto (R$58,50/mes)"},
        {"nome": "Semestral", "valor": 331.50, "duracao_meses": 6, "descricao": "Plano semestral com 15% de desconto (R$55,25/mes)"},
        {"nome": "Anual", "valor": 624.00, "duracao_meses": 12, "descricao": "Plano anual com 20% de desconto (R$52,00/mes)"},
    ]

    for plano_data in planos_padrao:
        if not Plano.query.filter_by(nome=plano_data["nome"]).first():
            plano = Plano(**plano_data)
            db.session.add(plano)

    db.session.commit()
    print("Planos criados/verificados.")

    # --- Seed 100 alunos ---
    planos = Plano.query.filter_by(ativo=True).all()
    hoje = date.today()
    
    # CPFs já existentes no banco
    cpfs_existentes = {a.cpf for a in Aluno.query.all()}
    
    alunos_criados, mensalidades_criadas, pagamentos, renovacoes = criar_alunos_com_matriculas(
        qtd=100,
        planos=planos,
        hoje=hoje,
        cpfs_existentes=cpfs_existentes,
    )
    
    db.session.commit()
    imprimir_resumo_seed(alunos_criados, mensalidades_criadas, pagamentos, renovacoes, hoje)

    print("\nInicializacao concluida!")
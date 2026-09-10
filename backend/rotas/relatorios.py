from datetime import date
from io import BytesIO
from flask import Blueprint, render_template, make_response, request
from flask_login import login_required
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, PieChart, Reference

from services.relatorios_service import (
    obter_dados_relatorios,
    filtrar_dados_por_busca,
    paginar,
    MESES,
)

relatorios_bp = Blueprint("relatorios", __name__)


@relatorios_bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    status_filtro = request.args.get("status", "todas")

    dados = obter_dados_relatorios()
    dados = filtrar_dados_por_busca(dados, q)

    # Paginação por tabela (10 por página)
    page_fat = request.args.get("page_fat", 1, type=int)
    page_inad = request.args.get("page_inad", 1, type=int)
    page_est = request.args.get("page_est", 1, type=int)
    page_aviso = request.args.get("page_aviso", 1, type=int)
    page_perfil = request.args.get("page_perfil", 1, type=int)

    # Se for requisição AJAX, retornar apenas o partial da seção solicitada
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        section = request.args.get('section', 'fat')
        
        # Recalcular paginação para a seção específica
        fat_pag = paginar(dados["pagamentos_mes"], page_fat)
        inad_pag = paginar(dados["mensalidades_atrasadas"], page_inad)
        est_pag = paginar(dados["estimativas"], page_est)
        aviso_pag = paginar(dados["mensalidades_aviso"], page_aviso)
        perfil_pag = paginar(dados["perfis"], page_perfil)
        
        context = {
            "q": q,
            "fat": fat_pag,
            "inad": inad_pag,
            "est": est_pag,
            "aviso": aviso_pag,
            "perfil": perfil_pag,
            "hoje": dados["hoje"],
            "meses": MESES,
        }
        
        template_map = {
            'fat': 'relatorios/partials/_table_fat.html',
            'inad': 'relatorios/partials/_table_inad.html',
            'est': 'relatorios/partials/_table_est.html',
            'aviso': 'relatorios/partials/_table_aviso.html',
            'perfil': 'relatorios/partials/_table_perfil.html',
        }
        
        template = template_map.get(section, 'relatorios/partials/_table_fat.html')
        return render_template(template, **context)

    return render_template(
        "relatorios/index.html",
        meses=MESES,
        q=q,
        status=status_filtro,
        fat=paginar(dados["pagamentos_mes"], page_fat),
        inad=paginar(dados["mensalidades_atrasadas"], page_inad),
        est=paginar(dados["estimativas"], page_est),
        aviso=paginar(dados["mensalidades_aviso"], page_aviso),
        perfil=paginar(dados["perfis"], page_perfil),
        total_faturamento=dados["total_faturamento"],
        total_inadimplencia=dados["total_inadimplencia"],
        total_estimativa=dados["total_estimativa"],
        faturamento_mensal=dados["faturamento_mensal"],
        status_count=dados["status_count"],
        mes_atual=dados["mes_atual"],
        ano_atual=dados["ano_atual"],
        proximo_mes=dados["proximo_mes"],
        hoje=dados["hoje"],
    )


@relatorios_bp.route("/pdf")
@login_required
def pdf():
    from xhtml2pdf import pisa
    
    dados = obter_dados_relatorios()
    html = render_template(
        "relatorios/pdf.html",
        meses=MESES,
        **dados,
    )
    result = BytesIO()
    pdf = pisa.pisaDocument(html, result)
    if not pdf.err:
        response = make_response(result.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "attachment; filename=relatorio_academia_vip.pdf"
        return response
    return "Erro ao gerar PDF", 500


@relatorios_bp.route("/excel")
@login_required
def excel():
    dados = obter_dados_relatorios()
    wb = Workbook()

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1a1a2e", end_color="1a1a2e", fill_type="solid")
    gold_font = Font(bold=True, color="B8860B")
    red_font = Font(bold=True, color="FF1744")
    green_font = Font(bold=True, color="00A844")
    bold_font = Font(bold=True)
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    moeda = 'R$ #,##0.00'

    def estilizar_cabecalho(ws, cols, row=1):
        for col in range(1, cols + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

    def ajustar_larguras(ws, largura=20):
        for col in ws.columns:
            ws.column_dimensions[get_column_letter(col[0].column)].width = largura

    def adicionar_total(ws, merge_ate, col_valor, valor):
        linha = ws.max_row + 1
        ws.cell(row=linha, column=1, value="TOTAL")
        if merge_ate > 1:
            ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=merge_ate)
        cell = ws.cell(row=linha, column=col_valor, value=float(valor))
        cell.number_format = moeda
        cell.font = gold_font
        return linha

    # ============ ABA 0: RESUMO ============
    ws0 = wb.active
    ws0.title = "Resumo"
    ws0.sheet_view.showGridLines = False

    ws0["A1"] = "ACADEMIA VIP - RELATORIO GERAL"
    ws0["A1"].font = Font(bold=True, size=16, color="1a1a2e")
    ws0["A2"] = (
        f"{MESES[dados['mes_atual']]}/{dados['ano_atual']} - Gerado em {dados['hoje'].strftime('%d/%m/%Y')}"
    )
    ws0["A2"].font = Font(size=10, color="666666")
    ws0.merge_cells("A1:F1")
    ws0.merge_cells("A2:F2")

    # KPIs
    kpis = [
        ("Faturamento do Mes", dados["total_faturamento"], "R$", "green"),
        ("Inadimplencia", dados["total_inadimplencia"], "R$", "red"),
        ("Estimativa Proximo Mes", dados["total_estimativa"], "R$", "green"),
        ("Avisos 7 Dias", len(dados["mensalidades_aviso"]), "", "amber"),
    ]
    row = 4
    ws0.cell(row=row, column=1, value="INDICADORES").font = Font(bold=True, color="B8860B", size=11)
    row += 1
    for i, (label, valor, tipo, _) in enumerate(kpis, start=2):
        ws0.cell(row=row, column=1, value=label).font = bold_font
        c = ws0.cell(row=row, column=2, value=float(valor))
        if tipo == "R$":
            c.number_format = moeda
        c.border = thin_border
        row += 1
    row += 1

    # Tabela faturamento 6 meses + BarChart
    ws0.cell(row=row, column=1, value="FATURAMENTO - ULTIMOS 6 MESES").font = Font(bold=True, color="B8860B", size=11)
    row += 1
    ws0.cell(row=row, column=1, value="Mes")
    ws0.cell(row=row, column=2, value="Valor")
    estilizar_cabecalho(ws0, 2, row)
    row += 1
    inicio_fat = row
    for f in dados["faturamento_mensal"]:
        ws0.cell(row=row, column=1, value=f["mes"])
        c = ws0.cell(row=row, column=2, value=float(f["valor"]))
        c.number_format = moeda
        row += 1
    fim_fat = row - 1

    grafico = BarChart()
    grafico.type = "col"
    grafico.title = "Faturamento mensal (R$)"
    grafico.width = 16
    grafico.height = 8
    dados_ref = Reference(ws0, min_col=1, min_row=inicio_fat - 1, max_row=fim_fat)
    valores_ref = Reference(ws0, min_col=2, min_row=inicio_fat - 1, max_row=fim_fat)
    grafico.add_data(valores_ref, titles_from_data=True)
    grafico.set_categories(dados_ref)
    grafico.legend = None
    ws0.add_chart(grafico, f"D4")

    row += 1

    # Tabela status + PieChart
    ws0.cell(row=row, column=1, value="STATUS DAS MENSALIDADES").font = Font(bold=True, color="B8860B", size=11)
    row += 1
    ws0.cell(row=row, column=1, value="Status")
    ws0.cell(row=row, column=2, value="Quantidade")
    estilizar_cabecalho(ws0, 2, row)
    row += 1
    inicio_status = row
    status_linhas = [
        ("Pagas", dados["status_count"]["pagas"], "00C853"),
        ("Pendentes", dados["status_count"]["pendentes"], "FFAB00"),
        ("Atrasadas", dados["status_count"]["atrasadas"], "FF1744"),
    ]
    for label, qtd, cor in status_linhas:
        ws0.cell(row=row, column=1, value=label)
        ws0.cell(row=row, column=2, value=qtd)
        row += 1
    fim_status = row - 1

    pizza = PieChart()
    pizza.title = "Status mensalidades"
    pizza.width = 12
    pizza.height = 8
    pizza.add_data(Reference(ws0, min_col=2, min_row=inicio_status - 1, max_row=fim_status), titles_from_data=True)
    pizza.set_categories(Reference(ws0, min_col=1, min_row=inicio_status, max_row=fim_status))
    ws0.add_chart(pizza, f"D20")

    row += 1

    # Tabela por forma de pagamento + BarChart
    formas = {}
    for p in dados["pagamentos_mes"]:
        nome = p.forma_pagamento.replace("_", " ").title()
        formas[nome] = formas.get(nome, 0) + float(p.valor_pago)

    ws0.cell(row=row, column=1, value="FATURAMENTO POR FORMA DE PAGAMENTO").font = Font(bold=True, color="B8860B", size=11)
    row += 1
    ws0.cell(row=row, column=1, value="Forma")
    ws0.cell(row=row, column=2, value="Total")
    estilizar_cabecalho(ws0, 2, row)
    row += 1
    inicio_forma = row
    for nome, total in sorted(formas.items()):
        ws0.cell(row=row, column=1, value=nome)
        c = ws0.cell(row=row, column=2, value=total)
        c.number_format = moeda
        row += 1
    fim_forma = max(row - 1, inicio_forma)

    if formas:
        barra = BarChart()
        barra.type = "bar"
        barra.title = "Por forma de pagamento"
        barra.width = 14
        barra.height = 7
        barra.add_data(Reference(ws0, min_col=2, min_row=inicio_forma - 1, max_row=fim_forma), titles_from_data=True)
        barra.set_categories(Reference(ws0, min_col=1, min_row=inicio_forma, max_row=fim_forma))
        barra.legend = None
        ws0.add_chart(barra, "D36")

    # Resumo de números adicionais
    from models import Aluno, Matricula
    pagamentos_mes = len(dados["pagamentos_mes"])
    ticket = dados["total_faturamento"] / pagamentos_mes if pagamentos_mes else 0
    row += 1
    ws0.cell(row=row, column=1, value="NUMEROS ADICIONAIS").font = Font(bold=True, color="B8860B", size=11)
    row += 1
    adicionais = [
        ("Alunos ativos", Aluno.query.filter_by(ativo=True).count()),
        ("Matriculas ativas", Matricula.query.filter_by(ativa=True).count()),
        ("Total de pagamentos no mes", pagamentos_mes),
        ("Ticket medio", ticket, "R$"),
    ]
    for item in adicionais:
        ws0.cell(row=row, column=1, value=item[0]).font = bold_font
        c = ws0.cell(row=row, column=2, value=float(item[1]))
        if len(item) > 2 and item[2] == "R$":
            c.number_format = moeda
        row += 1

    ajustar_larguras(ws0, 30)

    # ============ ABA 1: FATURAMENTO ============
    ws1 = wb.create_sheet("Faturamento")
    ws1.append(["Data Pagamento", "Aluno", "Plano", "Valor", "Forma"])
    estilizar_cabecalho(ws1, 5)
    for p in dados["pagamentos_mes"]:
        ws1.append([
            p.data_pagamento.strftime("%d/%m/%Y"),
            p.mensalidade.matricula.aluno.nome,
            p.mensalidade.matricula.plano.nome,
            float(p.valor_pago),
            p.forma_pagamento.replace("_", " ").title(),
        ])
    for linha in range(2, ws1.max_row + 1):
        ws1.cell(row=linha, column=4).number_format = moeda
    adicionar_total(ws1, 3, 4, dados["total_faturamento"])
    ws1.auto_filter.ref = ws1.dimensions
    ws1.freeze_panes = "A2"
    ajustar_larguras(ws1)

    # ============ ABA 2: INADIMPLENCIA ============
    ws2 = wb.create_sheet("Inadimplencia")
    ws2.append(["Aluno", "Plano", "Valor", "Vencimento", "Dias em Atraso"])
    estilizar_cabecalho(ws2, 5)
    for m in dados["mensalidades_atrasadas"]:
        dias = (dados["hoje"] - m.data_vencimento).days
        ws2.append([
            m.matricula.aluno.nome,
            m.matricula.plano.nome,
            float(m.valor),
            m.data_vencimento.strftime("%d/%m/%Y"),
            dias,
        ])
        ws2.cell(row=ws2.max_row, column=3).number_format = moeda
        ws2.cell(row=ws2.max_row, column=5).font = red_font
    adicionar_total(ws2, 2, 3, dados["total_inadimplencia"])
    ws2.auto_filter.ref = ws2.dimensions
    ws2.freeze_panes = "A2"
    ajustar_larguras(ws2)

    # ============ ABA 3: ESTIMATIVA ============
    ws3 = wb.create_sheet(f"Estimativa {MESES[dados['proximo_mes'].month]}")
    ws3.append(["Aluno", "Plano", "Valor", "Vencimento", "Status"])
    estilizar_cabecalho(ws3, 5)
    for e in dados["estimativas"]:
        ws3.append([
            e["aluno"],
            e["plano"],
            float(e["valor"]),
            e["vencimento"].strftime("%d/%m/%Y"),
            "Estimado" if e["status"] == "estimado" else "Pendente",
        ])
        ws3.cell(row=ws3.max_row, column=3).number_format = moeda
    adicionar_total(ws3, 2, 3, dados["total_estimativa"])
    ws3.auto_filter.ref = ws3.dimensions
    ws3.freeze_panes = "A2"
    ajustar_larguras(ws3)

    # ============ ABA 4: AVISO 7 DIAS ============
    ws4 = wb.create_sheet("Aviso 7 Dias")
    ws4.append(["Aluno", "Plano", "Valor", "Vencimento", "Faltam (dias)"])
    estilizar_cabecalho(ws4, 5)
    for m in dados["mensalidades_aviso"]:
        ws4.append([
            m.matricula.aluno.nome,
            m.matricula.plano.nome,
            float(m.valor),
            m.data_vencimento.strftime("%d/%m/%Y"),
            (m.data_vencimento - dados["hoje"]).days,
        ])
        ws4.cell(row=ws4.max_row, column=3).number_format = moeda
    ws4.auto_filter.ref = ws4.dimensions
    ws4.freeze_panes = "A2"
    ajustar_larguras(ws4)

    # ============ ABA 5: PERFIL DE PAGAMENTO ============
    ws5 = wb.create_sheet("Perfil de Pagamento")
    ws5.append(["Aluno", "Media Dias Atraso", "Tendencia", "Total Pagamentos"])
    estilizar_cabecalho(ws5, 4)
    for p in dados["perfis"]:
        ws5.append([
            p["aluno"],
            p["dias_medio"],
            p["tendencia"],
            p["total_pagamentos"],
        ])
        ws5.cell(row=ws5.max_row, column=2).font = (
            green_font if p["dias_medio"] <= 0 else red_font if p["dias_medio"] > 3 else Font(bold=True, color="FF8F00")
        )
    ws5.auto_filter.ref = ws5.dimensions
    ws5.freeze_panes = "A2"
    ajustar_larguras(ws5, 25)

    # ============ ABA 6: POR FORMA / PLANO ============
    ws6 = wb.create_sheet("Por Forma e Plano")
    ws6.append(["Tipo", "Nome", "Total"])
    estilizar_cabecalho(ws6, 3)
    for nome, total in sorted(formas.items()):
        linha = ws6.max_row + 1
        ws6.append(["Forma de Pagamento", nome, total])
        ws6.cell(row=linha, column=3).number_format = moeda

    planos_dict = {}
    for p in dados["pagamentos_mes"]:
        nome = p.mensalidade.matricula.plano.nome
        planos_dict[nome] = planos_dict.get(nome, 0) + float(p.valor_pago)
    for nome, total in sorted(planos_dict.items()):
        linha = ws6.max_row + 1
        ws6.append(["Plano", nome, total])
        ws6.cell(row=linha, column=3).number_format = moeda
    ws6.auto_filter.ref = ws6.dimensions
    ws6.freeze_panes = "A2"
    ajustar_larguras(ws6)

    result = BytesIO()
    wb.save(result)
    result.seek(0)
    response = make_response(result.getvalue())
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response.headers["Content-Disposition"] = "attachment; filename=relatorio_academia_vip.xlsx"
    return response
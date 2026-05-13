"""Geração do contrato MaLuê em PDF a partir de um dicionário de dados.

Mantém o visual padrão (logo no cabeçalho com linhas, marca d'água central,
título justificado à direita) e devolve o PDF em bytes — pronto pra ser
baixado pelo Streamlit ou salvo em disco.
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass

from reportlab.lib.colors import black
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, SimpleDocTemplate

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_HEADER = os.path.join(ASSETS_DIR, "malue_logo_black.png")
LOGO_WATERMARK = os.path.join(ASSETS_DIR, "malue_logo_watermark.png")


@dataclass
class DadosContrato:
    # Contratante
    contratante_nome: str
    contratante_doc_tipo: str  # "CPF" ou "CNPJ"
    contratante_doc: str  # já formatado: "817.941.931-20" ou "00.000.000/0000-00"
    contratante_endereco: str
    # Evento
    local_show: str
    cidade_show: str
    data_show_extenso: str  # "03 de outubro de 2026"
    horario_show: str  # "23h"
    exemplo_inicio_show: str  # "23:00h"
    exemplo_liberacao_palco: str  # "22:30h"
    # Duração
    duracao_extenso: str  # "2 (duas) horas contínuas"
    duracao_extenso_curto: str  # "2 (duas) horas"
    # Pagamento
    valor_numerico: str  # "R$ 18.000,00"
    valor_extenso: str  # "dezoito mil reais"
    # Assinatura
    data_assinatura_extenso: str  # "11 de maio de 2026"


def _build_styles():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=20,
        alignment=TA_JUSTIFY,
        leftIndent=6.5 * cm,
        spaceAfter=22,
        textColor=black,
    )
    party_style = ParagraphStyle(
        "PartyStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
    )
    intro_style = ParagraphStyle(
        "IntroStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        firstLineIndent=1.0 * cm,
        spaceBefore=8,
        spaceAfter=14,
    )
    clause_title_style = ParagraphStyle(
        "ClauseTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceBefore=12,
        spaceAfter=8,
        alignment=TA_LEFT,
    )
    clause_body_style = ParagraphStyle(
        "ClauseBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        firstLineIndent=1.0 * cm,
        spaceAfter=8,
    )
    clause_item_style = ParagraphStyle(
        "ClauseItem",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        leftIndent=1.0 * cm,
        spaceAfter=8,
    )
    clause_sub_item_style = ParagraphStyle(
        "ClauseSubItem",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        leftIndent=1.6 * cm,
        bulletIndent=1.0 * cm,
        spaceAfter=6,
    )
    bank_box_style = ParagraphStyle(
        "BankBox",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_LEFT,
        leftIndent=0.5 * cm,
        rightIndent=0.5 * cm,
        borderPadding=6,
        borderWidth=0.5,
        borderColor=black,
        spaceBefore=6,
        spaceAfter=10,
    )
    signature_style = ParagraphStyle(
        "Signature",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        spaceBefore=4,
        spaceAfter=24,
    )
    city_date_style = ParagraphStyle(
        "CityDate",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_LEFT,
        spaceBefore=18,
        spaceAfter=36,
    )
    sig_line_style = ParagraphStyle(
        "SigLine",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        spaceBefore=30,
        spaceAfter=2,
    )

    return {
        "title": title_style,
        "party": party_style,
        "intro": intro_style,
        "clause_title": clause_title_style,
        "clause_body": clause_body_style,
        "clause_item": clause_item_style,
        "clause_sub": clause_sub_item_style,
        "bank": bank_box_style,
        "signature": signature_style,
        "city_date": city_date_style,
        "sig_line": sig_line_style,
    }


def _draw_page_decoration(canvas, doc):
    page_w, page_h = A4
    canvas.saveState()

    # Marca d'água central
    if os.path.exists(LOGO_WATERMARK):
        wm = ImageReader(LOGO_WATERMARK)
        wm_w = 14 * cm
        wm_h = wm_w * (294 / 517)
        canvas.drawImage(
            wm,
            (page_w - wm_w) / 2,
            (page_h - wm_h) / 2,
            width=wm_w,
            height=wm_h,
            mask="auto",
            preserveAspectRatio=True,
        )

    # Cabeçalho: linha à esquerda + logo central + linha à direita
    if os.path.exists(LOGO_HEADER):
        logo = ImageReader(LOGO_HEADER)
        logo_w = 2.6 * cm
        logo_h = logo_w * (294 / 517)
        header_y = page_h - 1.6 * cm
        logo_x = (page_w - logo_w) / 2
        logo_y = header_y - logo_h / 2
        canvas.drawImage(
            logo,
            logo_x,
            logo_y,
            width=logo_w,
            height=logo_h,
            mask="auto",
            preserveAspectRatio=True,
        )
        canvas.setStrokeColor(black)
        canvas.setLineWidth(0.6)
        line_y = header_y
        canvas.line(2.5 * cm, line_y, logo_x - 0.3 * cm, line_y)
        canvas.line(
            logo_x + logo_w + 0.3 * cm, line_y, page_w - 2.5 * cm, line_y
        )

    # Número da página no rodapé
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(black)
    canvas.drawRightString(page_w - 2.5 * cm, 1.5 * cm, str(doc.page))

    canvas.restoreState()


_OBRIGACOES = [
    (
        "A.",
        "impedir a permanência no palco, principalmente durante o show, de "
        "qualquer pessoa que não faça parte da equipe MaLuê.",
    ),
    (
        "B.",
        "o CONTRATANTE se responsabiliza integralmente por qualquer dano ao "
        "material da banda antes, durante e após (desmontagem) a "
        "apresentação, ocasionado por comportamento/ação de terceiros e/ou "
        'convidados, como por exemplo: "derrubar bebida na pedaleira ou '
        "alguém não autorizado subir no palco e quebrar/estragar algum "
        'material da banda";',
    ),
    (
        "C.",
        "água mineral durante montagem, passagem de som, apresentação "
        "musical e desmontagem,",
    ),
    (
        "D.",
        "fornecimento de energia elétrica condizente, sem oscilações de "
        "voltagem. Observar se há necessidade de gerador, sou houver, "
        "deverá ser de no mínimo 150 Kva.",
    ),
    (
        "E.",
        "PA contendo no mínimo 4 lines array com potência mínima de 900 RMS "
        "cada caixa estéreo, e 2 sub's duplos de 18 polegadas com 2 "
        "falantes em cada caixa com no mínimo 1600 rms por caixa. com 3 ou "
        "4 vias compatível com a dispersão acústica do local, com uma "
        "resposta em SPL de 110 dB (sem distorção ou clipagem). Colocar "
        "front fill para complementar a cobertura caso necessário. "
        "IMPORTANTE: Observar a necessidade da instalação de torre de "
        'delay. Não aceitamos caixas do tipo "caseiras" e telas ortofônicas '
        "na frente do PA. SUGESTÕES: EAW KF850 / SB 850, LINE ARRAY NORTON, "
        "LS ÁUDIO, NEXO, FZ ÁUDIO, DAS, ATTACK E JBL. (Rider em anexo)",
    ),
    (
        "F.",
        "01 medusa 12 vias, 04 pedestais pequenos para microfone do bumbo, "
        "10 pedestais girafa, 02 pedestais para microfone sem fio, cabos "
        "XLR para ligação de todo input e output, 05 cabos p10 de 05 metros "
        "cada, 07 pontos de energia 220v, microfonação de bateria.",
    ),
    (
        "G.",
        "12 movings head beam, 10 par led 9 watts rgb, 1 fog com ventilador, "
        "04 estrobos RGB, 02 estrobos ATOMIC, 1 console MA2on PC, 02 "
        "cilindros com 25kg de CO2 cada para uso exclusivo da CONTRATADA. "
        "(Rider em anexo)",
    ),
    (
        "H.",
        "Camarim ou espaço físico para 8 pessoas, com banheiro, água "
        "mineral e jantar simples.",
    ),
    (
        "I.",
        "Palco com metragem mínima de 4x4 mts, totalmente protegido de "
        "chuva e que não balance.",
    ),
    (
        "J.",
        "As despesas com alvarás, multas e direitos autorais das entidades "
        "arrecadadoras serão de responsabilidade exclusiva do CONTRATANTE.",
    ),
]


def gerar_pdf(dados: DadosContrato) -> bytes:
    """Gera o contrato e devolve o PDF como bytes."""
    s = _build_styles()
    story = []

    # Título
    story.append(
        Paragraph(
            'CONTRATO DE APRESENTAÇÃO MUSICAL "MALUÊ" QUE FAZEM ENTRE SI '
            f"{dados.contratante_nome.upper()} E MALUÊ LTDA",
            s["title"],
        )
    )

    # Partes
    story.append(
        Paragraph(
            f"<b>CONTRATANTE</b>: <b>{dados.contratante_nome.upper()}</b>, "
            f"{dados.contratante_doc_tipo} {dados.contratante_doc}, com endereço "
            f"em {dados.contratante_endereco}.",
            s["party"],
        )
    )
    story.append(
        Paragraph(
            "<b>CONTRATADA</b>: <b>MALUÊ</b> CNPJ 42.447.411/0001-70, com sede na "
            "Rua Fortaleza, 380, Goiânia - GO, neste ato representada por Luene "
            "Carvalho dos Santos, brasileira, casada, cantora, CPF 006.406.281-33, "
            "RG 4665708.",
            s["party"],
        )
    )

    story.append(
        Paragraph(
            "As partes acima identificadas têm, entre si, justo e acertado o "
            "presente Contrato de Apresentação Musical, que se regerá pelas "
            "cláusulas seguintes e pelas condições descritas no presente.",
            s["intro"],
        )
    )

    # Cláusula 1
    story.append(Paragraph("1. CLÁUSULA PRIMEIRA - OBJETO", s["clause_title"]))
    story.append(
        Paragraph(
            "1.1. Este contrato tem como objeto a apresentação de show musical, "
            'por parte de "MaLuê", neste ato representada por sua representante '
            f'legal a CONTRATADA, ao público presente em "{dados.local_show}", '
            f"no município de {dados.cidade_show}, no dia "
            f"{dados.data_show_extenso}, com horário de início às "
            f"{dados.horario_show}.",
            s["clause_body"],
        )
    )

    # Cláusula 2
    story.append(
        Paragraph(
            "2. CLÁUSULA SEGUNDA - DA DURAÇÃO E ATRASO", s["clause_title"]
        )
    )
    story.append(
        Paragraph(
            f"2.1. <b>Duração:</b> A apresentação artística terá a duração de "
            f"<b>{dados.duracao_extenso}</b>.",
            s["clause_body"],
        )
    )
    story.append(
        Paragraph(
            "2.2. <b>Tolerância:</b> Será admitida uma tolerância máxima de "
            "<b>15 (quinze) minutos</b> para o início da apresentação em "
            "relação ao horário agendado.",
            s["clause_body"],
        )
    )
    story.append(
        Paragraph(
            "2.3. Caso o início da apresentação seja postergado por período "
            "superior à tolerância de 15 (quinze) minutos, por <b>ação, omissão "
            "ou critério exclusivo do CONTRATANTE</b>, a <b>CONTRATADA</b> "
            "reserva-se o direito de encerrar a apresentação exatamente "
            f"<b>{dados.duracao_extenso_curto} após o horário originalmente "
            "agendado</b> para o início, independentemente do horário efetivo "
            "em que a apresentação for iniciada.",
            s["clause_body"],
        )
    )
    story.append(
        Paragraph(
            "2.4. Caso a <b>CONTRATADA</b> atrase o início da apresentação por "
            "período superior à tolerância de 15 (quinze) minutos, a "
            "<b>CONTRATADA</b> se obrigará a:",
            s["clause_body"],
        )
    )
    story.append(
        Paragraph(
            "<b>a)</b> Pagar ao <b>CONTRATANTE</b> multa moratória equivalente "
            "a <b>10% (dez por cento)</b> do valor total deste Contrato.",
            s["clause_sub"],
            bulletText="•",
        )
    )
    story.append(
        Paragraph(
            f"<b>b)</b> Manter a duração integral da apresentação, encerrando-a "
            f"<b>{dados.duracao_extenso_curto} após o horário de seu efetivo "
            "início</b>.",
            s["clause_sub"],
            bulletText="•",
        )
    )
    story.append(
        Paragraph(
            "2.5. Em caso de mais de uma atração no evento e essa atração se "
            "apresente antes da CONTRATADA, deve ser observada a seguinte "
            "condição: após o término da apresentação da primeira atração, a "
            "mesma deverá deixar o palco totalmente livre de cabos, "
            "instrumentos, equipamentos e integrantes. <b>Após a primeira "
            "atração (inclusive DJ) retirar tudo do palco, a CONTRATADA "
            "precisa de no mínimo 30 (trinta) minutos para reposicionar o "
            "equipamento, instrumentos, cabos, etc. Os 30 (trinta) minutos são "
            "contabilizados a partir do momento que o palco não estiver com "
            "nenhum equipamento da primeira atração.</b> Ou seja, por exemplo, "
            f"se o show da CONTRATADA está programado para "
            f"{dados.exemplo_inicio_show} e tem uma atração musical antes, o "
            f"palco deverá estar totalmente liberado e sem nenhum equipamento "
            f"da primeira atração, no mínimo {dados.exemplo_liberacao_palco}.",
            s["clause_body"],
        )
    )

    # Cláusula 3
    story.append(
        Paragraph("3. CLÁUSULA TERCEIRA - DO PAGAMENTO", s["clause_title"])
    )
    story.append(
        Paragraph(
            f"3.1. O CONTRATANTE se compromete a pagar a quantia de "
            f"<b>{dados.valor_numerico} ({dados.valor_extenso})</b>, sendo 30% "
            f"na assinatura do contrato e o restante até 04 dias antes do "
            f"evento, por transferência bancária na conta abaixo:",
            s["clause_body"],
        )
    )
    story.append(
        Paragraph(
            "Banco Itaú, agência 9049, conta corrente 01360-1. Luene Carvalho "
            "dos Santos, pix: malueoficial@gmail.com.",
            s["bank"],
        )
    )
    story.append(
        Paragraph(
            "3.1.1. Por motivos de segurança do CONTRATANTE e do CONTRATADO, "
            "só recebemos por transferência bancária, a fim de evitar o "
            "transporte de pagamento em espécie no dia do evento. Não "
            "trabalhamos com pagamento em cheque e não recebemos nenhum valor "
            "no dia do evento, a não ser em caso de hora extra, a qual "
            "receberemos apenas em espécie no ato ou pix.",
            s["clause_body"],
        )
    )

    # Cláusula 4
    story.append(
        Paragraph(
            "4. CLÁUSULA QUARTA - DAS OBRIGAÇÕES DO CONTRATANTE",
            s["clause_title"],
        )
    )
    story.append(
        Paragraph(
            "A CONTRATANTE compromete-se a oferecer as seguintes condições "
            "fundamentais para a realização do show:",
            s["clause_body"],
        )
    )
    for letra, texto in _OBRIGACOES:
        story.append(
            Paragraph(f"<b>{letra}</b> {texto}", s["clause_item"])
        )

    # Cláusula 5
    story.append(
        Paragraph(
            "5. CLÁUSULA QUINTA - DAS OBRIGAÇÕES DA CONTRATADA",
            s["clause_title"],
        )
    )
    story.append(
        Paragraph(
            "5.1. A CONTRATADA fornecerá banda, microfonação de voz, mesa de "
            "som, sistema de ear sem fio, técnico de som, técnico de luz, para "
            "uso exclusivo da CONTRATADA.",
            s["clause_body"],
        )
    )

    # Cláusula 6
    story.append(
        Paragraph(
            "6. CLÁUSULA SEXTA - DEMAIS DISPOSIÇÕES", s["clause_title"]
        )
    )
    story.append(
        Paragraph(
            "6.1. Este contrato não é passível de transferência por nenhuma das "
            "partes contratantes à terceiros, tão pouco transferência da data, "
            "local e horário de execução, sem anuência de ambas as partes.",
            s["clause_body"],
        )
    )
    story.append(
        Paragraph(
            "6.2. O presente contrato será rescindo caso uma das partes "
            "descumpra o pactuado nas cláusulas deste instrumento.",
            s["clause_body"],
        )
    )
    story.append(
        Paragraph(
            "6.3. Caso ocorra algum impedimento à realização do show, ligado a "
            "caso fortuito ou a força maior, as partes deverão pactuar outra "
            "data.",
            s["clause_body"],
        )
    )

    # Cláusula 7
    story.append(
        Paragraph("7. CLÁUSULA SÉTIMA - DA MULTA", s["clause_title"])
    )
    story.append(
        Paragraph(
            "7.1. A parte que infringir alguma cláusula ou der causa à rescisão "
            "do presente instrumento pagará multa de 30% do valor do contrato "
            "se até 30 dias antes do evento. Caso ocorra rescisão do contrato, "
            "faltando menos de 30 dias corridos para realização do evento, a "
            "multa será de 100% do valor do contrato.",
            s["clause_body"],
        )
    )

    # Cláusula 8
    story.append(
        Paragraph("8. CLÁUSULA OITAVA - DO FORO", s["clause_title"])
    )
    story.append(
        Paragraph(
            "8.1. Para dirimir quaisquer controvérsias oriundas do CONTRATO, as "
            "partes elegem o foro da comarca de Goiânia - GO.",
            s["clause_body"],
        )
    )
    story.append(
        Paragraph(
            "Por estarem assim justos e contratados, firmam o presente "
            "instrumento, em duas vias de igual teor, juntamente com 2 (duas) "
            "testemunhas.",
            s["clause_body"],
        )
    )

    # Data e assinaturas
    story.append(
        Paragraph(
            f"Goiânia, {dados.data_assinatura_extenso}.", s["city_date"]
        )
    )
    story.append(
        Paragraph("___________________________________________", s["sig_line"])
    )
    story.append(
        Paragraph("<b>MALUÊ LTDA - CONTRATADA</b>", s["signature"])
    )
    story.append(
        Paragraph("___________________________________________", s["sig_line"])
    )
    story.append(
        Paragraph(
            f"<b>{dados.contratante_nome.upper()} - CONTRATANTE</b>",
            s["signature"],
        )
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=3.2 * cm,
        bottomMargin=2.5 * cm,
        title="Contrato de Apresentação Musical MaLuê",
        author="MaLuê Ltda",
    )
    doc.build(
        story,
        onFirstPage=_draw_page_decoration,
        onLaterPages=_draw_page_decoration,
    )
    return buffer.getvalue()

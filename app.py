"""Gerador de Contrato MaLuê — interface Streamlit.

Rode localmente com:
    streamlit run app.py

Ou hospede gratuitamente no Streamlit Community Cloud (veja INSTRUCOES_DEPLOY.md).
"""
from __future__ import annotations

import urllib.parse
from datetime import date

import streamlit as st

from contrato import DadosContrato, gerar_pdf
from utils import (
    data_compacta,
    data_por_extenso,
    detecta_e_formata_documento,
    duracao_extensos,
    formata_valor_brl,
    horario_palco_liberado,
    parse_valor,
    valor_por_extenso,
)

# ============================================================
# Configuração da página
# ============================================================
st.set_page_config(
    page_title="Gerador de Contrato MaLuê",
    page_icon="malue_icon.png",
    layout="centered",
)

# CSS leve pra deixar bonito no celular
st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; padding-bottom: 4rem; }
      h1 { font-weight: 700; }
      .preview-card {
        background: #f7f5f0;
        border-left: 4px solid #b9985a;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        margin: 0.5rem 0 1rem 0;
        font-size: 0.95rem;
      }
      .stButton>button {
        width: 100%;
        background: #1a1a1a;
        color: #fff;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-weight: 600;
      }
      .stDownloadButton>button {
        width: 100%;
        background: #b9985a;
        color: #1a1a1a;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-weight: 700;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.image("malue_logo_black.png", width=180)
st.title("Gerador de Contrato")
st.caption(
    "Preencha os campos abaixo e baixe o contrato pronto. O padrão de pagamento, "
    "dados bancários, foro e duração de 2 horas já estão fixos."
)

# ============================================================
# Formulário
# ============================================================
with st.form("contrato_form", clear_on_submit=False):
    st.subheader("Contratante")
    contratante_nome = st.text_input(
        "Nome completo do contratante",
        placeholder="Ex.: João da Silva ou Empresa XPTO LTDA",
    )
    contratante_doc = st.text_input(
        "CPF ou CNPJ",
        placeholder="Aceita com ou sem pontuação",
    )
    contratante_endereco = st.text_area(
        "Endereço completo",
        placeholder="Rua, número, bairro, cidade - UF, CEP",
        height=80,
    )

    st.subheader("Evento")
    col1, col2 = st.columns(2)
    with col1:
        local_show = st.text_input(
            "Local do show", placeholder="Ex.: Casa Lis"
        )
    with col2:
        cidade_show = st.text_input(
            "Cidade do show", placeholder="Ex.: Goiânia"
        )
    col3, col4 = st.columns(2)
    with col3:
        data_show = st.date_input(
            "Data do evento",
            value=date.today(),
            format="DD/MM/YYYY",
        )
    with col4:
        horario_show = st.text_input(
            "Horário de início",
            value="23h",
            help="Aceita formatos como '23h', '23:00' ou '23:30'",
        )

    st.subheader("Pagamento")
    valor_input = st.text_input(
        "Valor do show",
        placeholder="Ex.: 18000 ou 18.000,00",
    )

    st.subheader("Assinatura")
    data_assinatura = st.date_input(
        "Data da assinatura",
        value=date.today(),
        format="DD/MM/YYYY",
    )

    with st.expander("Opções avançadas (duração diferente de 2h)"):
        usar_duracao_custom = st.checkbox(
            "Este show tem duração diferente de 2 horas",
            value=False,
        )
        col5, col6 = st.columns(2)
        with col5:
            horas_input = st.number_input(
                "Horas", min_value=0, max_value=10, value=2, step=1
            )
        with col6:
            minutos_input = st.number_input(
                "Minutos", min_value=0, max_value=55, value=0, step=5
            )

    submitted = st.form_submit_button("🎼 Gerar contrato")

# ============================================================
# Validação e geração
# ============================================================
if submitted:
    erros = []

    if not contratante_nome.strip():
        erros.append("Informe o nome do contratante.")
    if not contratante_endereco.strip():
        erros.append("Informe o endereço do contratante.")
    if not local_show.strip():
        erros.append("Informe o local do show.")
    if not cidade_show.strip():
        erros.append("Informe a cidade do show.")
    if not horario_show.strip():
        erros.append("Informe o horário do show.")

    # Documento
    doc_info = detecta_e_formata_documento(contratante_doc) if contratante_doc else None
    if not doc_info:
        erros.append(
            "CPF ou CNPJ inválido. Confira os dígitos (CPF tem 11 dígitos, "
            "CNPJ tem 14)."
        )

    # Valor
    valor_decimal = parse_valor(valor_input) if valor_input else None
    if valor_decimal is None:
        erros.append(
            "Valor do show inválido. Use formatos como '18000' ou '18.000,00'."
        )

    # Horário do palco
    try:
        exemplo_inicio, exemplo_liberacao = horario_palco_liberado(horario_show)
    except Exception:
        erros.append("Horário do show inválido (ex.: '23h' ou '23:00').")
        exemplo_inicio = exemplo_liberacao = ""

    # Duração
    if usar_duracao_custom:
        if horas_input == 0 and minutos_input == 0:
            erros.append("Defina ao menos 1 hora ou alguns minutos de duração.")
            duracao_dados = None
        else:
            duracao_dados = duracao_extensos(int(horas_input), int(minutos_input))
    else:
        duracao_dados = duracao_extensos(2, 0)

    if erros:
        for e in erros:
            st.error(e)
        st.stop()

    # Tudo válido — gera
    tipo_doc, doc_formatado = doc_info
    valor_num = formata_valor_brl(valor_decimal)
    valor_ext = valor_por_extenso(valor_decimal)
    data_show_ext = data_por_extenso(data_show)
    data_assinatura_ext = data_por_extenso(data_assinatura)
    _, duracao_ext, duracao_curto = duracao_dados

    # Padroniza horário pra exibição na cláusula 1.1 (sem zerar minutos se vierem)
    horario_show_clean = horario_show.strip()
    if not horario_show_clean.endswith("h"):
        # se a usuária digitou "23:00", mostramos "23h" na 1.1
        h_part = horario_show_clean.split(":")[0]
        horario_show_clean = f"{int(h_part)}h"

    dados = DadosContrato(
        contratante_nome=contratante_nome.strip(),
        contratante_doc_tipo=tipo_doc,
        contratante_doc=doc_formatado,
        contratante_endereco=contratante_endereco.strip(),
        local_show=local_show.strip(),
        cidade_show=cidade_show.strip(),
        data_show_extenso=data_show_ext,
        horario_show=horario_show_clean,
        exemplo_inicio_show=exemplo_inicio,
        exemplo_liberacao_palco=exemplo_liberacao,
        duracao_extenso=duracao_ext,
        duracao_extenso_curto=duracao_curto,
        valor_numerico=valor_num,
        valor_extenso=valor_ext,
        data_assinatura_extenso=data_assinatura_ext,
    )

    with st.spinner("Gerando contrato..."):
        pdf_bytes = gerar_pdf(dados)

    st.success("Contrato gerado com sucesso!")

    # Preview dos campos calculados
    st.markdown(
        f"""
        <div class="preview-card">
          <b>Resumo:</b><br>
          • {tipo_doc} validado: {doc_formatado}<br>
          • Valor: <b>{valor_num}</b> ({valor_ext})<br>
          • Evento: {data_show_ext} às {horario_show_clean}<br>
          • Palco liberado em: {exemplo_liberacao}<br>
          • Duração: {duracao_ext}<br>
          • Assinatura: {data_assinatura_ext}
        </div>
        """,
        unsafe_allow_html=True,
    )

    nome_arquivo = (
        f"Contrato MaLuê - {contratante_nome.strip()} - "
        f"{data_compacta(data_show)}.pdf"
    )

    st.download_button(
        label="📥 Baixar contrato em PDF",
        data=pdf_bytes,
        file_name=nome_arquivo,
        mime="application/pdf",
    )

    # Link de WhatsApp
    mensagem_wpp = (
        f"Olá! Segue em anexo o contrato para o show no dia {data_show_ext}. "
        f"Qualquer dúvida estou à disposição. — MaLuê"
    )
    wpp_url = "https://wa.me/?text=" + urllib.parse.quote(mensagem_wpp)
    st.markdown(
        f"""
        <a href="{wpp_url}" target="_blank"
           style="display:block;text-align:center;background:#25D366;color:#fff;
                  padding:0.6rem 1rem;border-radius:8px;text-decoration:none;
                  font-weight:700;margin-top:0.6rem;">
          📲 Abrir WhatsApp com mensagem pronta
        </a>
        <small style="display:block;margin-top:0.4rem;color:#666;">
          Depois de abrir o WhatsApp, escolha o contato e anexe o PDF que você
          acabou de baixar.
        </small>
        """,
        unsafe_allow_html=True,
    )

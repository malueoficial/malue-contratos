"""Gerador de Contrato MaLuê — interface Streamlit.

Rode localmente com:
    streamlit run app.py

Ou hospede gratuitamente no Streamlit Community Cloud (veja INSTRUCOES_DEPLOY.md).
"""
from __future__ import annotations

import base64
import urllib.parse
from datetime import date
from pathlib import Path

import requests
import streamlit as st

DIAS_SEMANA_PT = [
    "Segunda", "Terça", "Quarta", "Quinta",
    "Sexta", "Sábado", "Domingo",
]

# Materiais fixos enviados junto com cada contrato
# Os PDFs ficam no repo; a URL pública vem do GitHub raw.
CAMARIM_FILE = "camarim_malue_2026.pdf"
RIDER_FILE = "rider_malue_2026.pdf"
CAMARIM_URL = (
    "https://raw.githubusercontent.com/malueoficial/malue-contratos/main/"
    + CAMARIM_FILE
)
RIDER_URL = (
    "https://raw.githubusercontent.com/malueoficial/malue-contratos/main/"
    + RIDER_FILE
)


def dia_semana_pt(d: date) -> str:
    return DIAS_SEMANA_PT[d.weekday()]


def _webhook_url() -> str:
    try:
        return st.secrets.get("WEBHOOK_URL", "") or ""
    except Exception:
        return ""


def adicionar_a_agenda(linha: dict) -> tuple[bool, str, int | None]:
    """POST pro webhook do Apps Script — adiciona linha na agenda.

    Retorna (ok, msg, row). 'row' é o número da linha criada (1-indexed,
    com header na linha 1), ou None se falhou ou se o webhook não devolveu.
    """
    webhook = _webhook_url()
    if not webhook:
        return False, "Webhook não configurado", None
    try:
        r = requests.post(webhook, json={"append": linha}, timeout=20)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}", None
        try:
            j = r.json()
        except Exception:
            return True, "ok (sem row)", None
        if not j.get("ok"):
            return False, j.get("error", "erro desconhecido"), None
        return True, "ok", j.get("row")
    except Exception as e:
        return False, str(e), None


def upload_contrato_drive(row: int, pdf_bytes: bytes, file_name: str) -> tuple[bool, str]:
    """Sobe o PDF pro Drive via webhook e grava a URL na coluna 'Contrato URL'.

    Retorna (ok, url_ou_erro).
    """
    webhook = _webhook_url()
    if not webhook:
        return False, "Webhook não configurado"
    if not row:
        return False, "Row não recebido do append"
    try:
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
        payload = {
            "uploadContrato": {
                "row": int(row),
                "pdfBase64": pdf_b64,
                "fileName": file_name,
            }
        }
        r = requests.post(webhook, json=payload, timeout=60)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        try:
            j = r.json()
        except Exception:
            return False, "resposta não-JSON"
        if not j.get("ok"):
            return False, j.get("error", "erro desconhecido")
        return True, j.get("url", "")
    except Exception as e:
        return False, str(e)

from contrato import DadosContrato, gerar_pdf
from extrator import extrair_tudo
from utils import (
    data_compacta,
    data_por_extenso,
    detecta_e_formata_documento,
    duracao_extensos,
    formata_cnpj,
    formata_cpf,
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
    "Cole a mensagem do cliente abaixo, clique em preencher automaticamente e revise. "
    "Padrão de pagamento, dados bancários, foro e duração de 2 horas já estão fixos."
)

# ============================================================
# Estado inicial
# ============================================================
def _defaults() -> dict:
    return {
        "nome": "",
        "doc": "",
        "endereco": "",
        "local": "",
        "cidade": "Goiânia",
        "data": date.today(),
        "horario": "23h",
    }


if "dados_form" not in st.session_state:
    st.session_state.dados_form = _defaults()

# ============================================================
# Área de extração (fora do form)
# ============================================================
st.subheader("Mensagem do cliente")
texto_cliente = st.text_area(
    "Cole aqui tudo que o cliente mandou no WhatsApp",
    height=140,
    placeholder=(
        "Ex.: 'Oi! Sou o João da Silva, CPF 123.456.789-09, RG 12.345.678-9, "
        "endereço Rua das Flores 100 Setor Oeste Goiânia-GO. Festa dia 15/11/2026 "
        "às 23h no Salão Aurora.'"
    ),
    key="texto_cliente",
)

col_a, col_b = st.columns([2, 1])
with col_a:
    if st.button("✨ Preencher automaticamente", type="primary"):
        if not texto_cliente.strip():
            st.warning("Cola a mensagem do cliente primeiro.")
        else:
            extraido = extrair_tudo(texto_cliente)
            achados = []
            if "nome" in extraido:
                st.session_state.dados_form["nome"] = extraido["nome"]
                achados.append(f"Nome: {extraido['nome']}")
            if "doc" in extraido:
                tipo = extraido["doc_tipo"]
                if tipo == "CPF":
                    formatado = formata_cpf(extraido["doc"])
                else:
                    formatado = formata_cnpj(extraido["doc"])
                st.session_state.dados_form["doc"] = formatado
                achados.append(f"{tipo}: {formatado}")
            if "endereco" in extraido:
                st.session_state.dados_form["endereco"] = extraido["endereco"]
                achados.append(f"Endereço: {extraido['endereco'][:60]}...")
            if "local" in extraido:
                st.session_state.dados_form["local"] = extraido["local"]
                achados.append(f"Local: {extraido['local']}")
            if "cidade" in extraido:
                st.session_state.dados_form["cidade"] = extraido["cidade"]
                achados.append(f"Cidade: {extraido['cidade']}")
            if "data" in extraido:
                st.session_state.dados_form["data"] = extraido["data"]
                achados.append(f"Data: {extraido['data'].strftime('%d/%m/%Y')}")
            if "horario" in extraido:
                st.session_state.dados_form["horario"] = extraido["horario"]
                achados.append(f"Horário: {extraido['horario']}")

            if achados:
                st.success(
                    "Identifiquei "
                    + str(len(achados))
                    + " campos. Revise abaixo:"
                )
                st.markdown(
                    "<div class='preview-card'>"
                    + "<br>".join("• " + a for a in achados)
                    + "</div>",
                    unsafe_allow_html=True,
                )
                st.rerun()
            else:
                st.warning(
                    "Não consegui identificar nada. Preencha manualmente abaixo."
                )

with col_b:
    if st.button("🗑️ Limpar tudo"):
        st.session_state.dados_form = _defaults()
        st.session_state.texto_cliente = ""
        st.rerun()

st.divider()

# ============================================================
# Formulário (campos populáveis)
# ============================================================
with st.form("contrato_form", clear_on_submit=False):
    st.subheader("Contratante")
    contratante_nome = st.text_input(
        "Nome completo do contratante",
        value=st.session_state.dados_form["nome"],
        placeholder="Ex.: João da Silva ou Empresa XPTO LTDA",
    )
    contratante_doc = st.text_input(
        "CPF ou CNPJ",
        value=st.session_state.dados_form["doc"],
        placeholder="Aceita com ou sem pontuação",
    )
    contratante_endereco = st.text_area(
        "Endereço completo",
        value=st.session_state.dados_form["endereco"],
        placeholder="Rua, número, bairro, cidade - UF, CEP",
        height=80,
    )

    st.subheader("Evento")
    col1, col2 = st.columns(2)
    with col1:
        local_show = st.text_input(
            "Local do show",
            value=st.session_state.dados_form["local"],
            placeholder="Ex.: Casa Lis",
        )
    with col2:
        cidade_show = st.text_input(
            "Cidade do show",
            value=st.session_state.dados_form["cidade"],
            placeholder="Ex.: Goiânia",
        )
    col3, col4 = st.columns(2)
    with col3:
        data_show = st.date_input(
            "Data do evento",
            value=st.session_state.dados_form["data"],
            format="DD/MM/YYYY",
        )
    with col4:
        horario_show = st.text_input(
            "Horário de início",
            value=st.session_state.dados_form["horario"],
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

    # Padroniza horário pra exibição na cláusula 1.1
    horario_show_clean = horario_show.strip()
    if not horario_show_clean.endswith("h"):
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

    # Nome do arquivo PDF (também usado pra subir no Drive)
    nome_arquivo = (
        f"Contrato MaLuê - {contratante_nome.strip()} - "
        f"{data_compacta(data_show)}.pdf"
    )

    # ============================================================
    # Alimenta a agenda automaticamente
    # ============================================================
    linha_agenda = {
        "Data": data_show.strftime("%d/%m/%Y"),
        "Dia": dia_semana_pt(data_show),
        "Horário Show": horario_show_clean,
        "Local": local_show.strip(),
        "Cidade": cidade_show.strip(),
        "Contratante": contratante_nome.strip(),
        "Tipo Evento": "",
        "Valor": valor_num,
        "Status": "Contrato assinado",
        "Observações": f"Contrato gerado em {data_assinatura_ext}",
    }
    ok_agenda, msg_agenda, sheet_row = adicionar_a_agenda(linha_agenda)
    if ok_agenda:
        st.info(
            "📅 Show também foi adicionado à agenda automaticamente. "
            "Confira em [malue-painel.streamlit.app](https://malue-painel.streamlit.app)."
        )
    else:
        st.warning(f"PDF ok, mas não consegui adicionar na agenda ({msg_agenda}). Adicione manualmente.")

    # ============================================================
    # Sobe o PDF pro Drive e grava a URL na agenda (coluna 'Contrato URL')
    # ============================================================
    contrato_url_publica = ""
    if ok_agenda and sheet_row:
        with st.spinner("Subindo PDF pro Drive..."):
            ok_up, url_ou_erro = upload_contrato_drive(sheet_row, pdf_bytes, nome_arquivo)
        if ok_up:
            contrato_url_publica = url_ou_erro
            st.info(
                f"📎 Contrato disponível no Drive — também aparece com botão "
                f"'Ver contrato' no card desse show no admin.  \n"
                f"[Abrir PDF agora]({url_ou_erro})"
            )
        else:
            st.warning(
                f"PDF gerado e agenda atualizada, mas não consegui subir o "
                f"contrato pro Drive ({url_ou_erro}). Use o botão de download abaixo."
            )

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

    st.download_button(
        label="📥 Baixar contrato em PDF",
        data=pdf_bytes,
        file_name=nome_arquivo,
        mime="application/pdf",
    )

    # ============================================================
    # Materiais fixos (Camarim + Rider) — vão junto com cada contrato
    # ============================================================
    st.markdown("---")
    st.markdown(
        "**📎 Materiais fixos que vão junto:**  \n"
        "Camarim e Rider são iguais em todo show. Baixa aqui pra anexar no "
        "WhatsApp junto com o contrato."
    )
    col_cam, col_rid = st.columns(2)
    try:
        with open(CAMARIM_FILE, "rb") as fh:
            camarim_bytes = fh.read()
        with col_cam:
            st.download_button(
                label="🛋️ Baixar Camarim",
                data=camarim_bytes,
                file_name="Camarim MaLuê 2026.pdf",
                mime="application/pdf",
                key="dl_camarim",
            )
    except FileNotFoundError:
        with col_cam:
            st.warning("Camarim não encontrado no repo.")
    try:
        with open(RIDER_FILE, "rb") as fh:
            rider_bytes = fh.read()
        with col_rid:
            st.download_button(
                label="🎤 Baixar Rider",
                data=rider_bytes,
                file_name="Rider MaLuê 2026.pdf",
                mime="application/pdf",
                key="dl_rider",
            )
    except FileNotFoundError:
        with col_rid:
            st.warning("Rider não encontrado no repo.")

    contrato_linha = (
        f"📄 Contrato: {contrato_url_publica}"
        if contrato_url_publica
        else "📄 Contrato: (em anexo)"
    )
    mensagem_wpp = (
        f"Olá! Segue o contrato para o show no dia {data_show_ext}, "
        f"junto com o camarim e o rider técnico.\n\n"
        f"{contrato_linha}\n"
        f"🛋️ Camarim: {CAMARIM_URL}\n"
        f"🎤 Rider: {RIDER_URL}\n\n"
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
          A mensagem já vai com os 3 links (contrato, camarim e rider) prontos
          pro cliente clicar e abrir. Os botões de download acima ficam pra
          caso você queira anexar os PDFs também.
        </small>
        """,
        unsafe_allow_html=True,
    )

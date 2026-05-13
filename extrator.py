"""Extração de dados de cliente a partir de texto solto (mensagem WhatsApp).

Detecta:
- CPF / CNPJ (com validação de dígito verificador)
- RG
- Nome completo
- Endereço
- Local do evento
- Cidade
- Data do evento
- Horário do show

Estratégia geral: percorrer linha a linha quando há labels ("Nome:", "Endereço:")
e usar regex específicos como fallback pra mensagens sem labels.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

from utils import _so_digitos, valida_cnpj, valida_cpf

MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}

# Labels que indicam novo campo (usado pra saber quando parar de capturar endereço)
LABELS_CAMPO = (
    r"(?:nome|nome\s+completo|cpf|cnpj|rg|telefone|celular|local|cidade|"
    r"data|evento|data\s+do\s+evento|hor[áa]rio|valor|email|e-?mail)"
)


def _normaliza(texto: str) -> str:
    """Remove acentos pra facilitar matching insensível."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ============================================================
# CPF / CNPJ
# ============================================================
def extrair_cpf(texto: str) -> str | None:
    for match in re.finditer(
        r"(?<!\d)(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2})(?!\d)", texto
    ):
        digitos = _so_digitos(match.group(1))
        if len(digitos) == 11 and valida_cpf(digitos):
            return digitos
    return None


def extrair_cnpj(texto: str) -> str | None:
    for match in re.finditer(
        r"(?<!\d)(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})(?!\d)", texto
    ):
        digitos = _so_digitos(match.group(1))
        if len(digitos) == 14 and valida_cnpj(digitos):
            return digitos
    return None


# ============================================================
# RG
# ============================================================
def extrair_rg(texto: str) -> str | None:
    match = re.search(
        r"\bRG\b[\s:.\-nº°º]*([\d.\-\sXx]{5,20})",
        texto,
        re.IGNORECASE,
    )
    if not match:
        return None
    rg_raw = match.group(1).strip()
    rg_clean = re.sub(r"[^\dXx.\-]", "", rg_raw).strip(".-")
    digitos = re.sub(r"\D", "", rg_clean)
    if len(digitos) < 5:
        return None
    return rg_clean


# ============================================================
# Nome
# ============================================================
def extrair_nome(texto: str) -> str | None:
    # Tenta labels: "Nome: João" ou "Empresa: X LTDA"
    for line in texto.splitlines():
        m = re.match(
            r"\s*(?:nome\s+completo|nome|cliente|contratante|empresa|raz[ãa]o\s+social)\s*[:\-]\s*(.+)",
            line,
            re.IGNORECASE,
        )
        if m:
            nome = _limpa_nome(m.group(1))
            if nome:
                return nome

    # Heurística: "sou o/a NOME"
    match = re.search(
        r"\b(?:sou\s+(?:o|a))\s+([A-ZÁÊÉÍÓÚÂÃÕÇ][^\n,.;]{3,80})",
        texto,
        re.IGNORECASE,
    )
    if match:
        nome = _limpa_nome(match.group(1))
        if nome:
            return nome

    # Heurística: "Pode anotar: NOME, ..." ou "Aqui tá: NOME"
    match = re.search(
        r"\b(?:pode\s+anotar|aqui\s+t[aá]|segue|seguem)[\s:]+([A-ZÁÊÉÍÓÚÂÃÕÇ][a-záêéíóúâãõç]+(?:\s+[A-ZÁÊÉÍÓÚÂÃÕÇa-záêéíóúâãõç]+){1,5})",
        texto,
        re.IGNORECASE,
    )
    if match:
        nome = _limpa_nome(match.group(1))
        if nome:
            return nome

    return None


def _limpa_nome(s: str) -> str:
    s = s.strip().rstrip(".,;")
    s = re.split(
        r"\s+(?:CPF|RG|CNPJ|endereço|endereco|telefone|celular)\b",
        s,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    s = s.strip(" ,.-")
    # Aceita nomes de 1 palavra desde que pareçam nome próprio (LTDA, ME, etc.)
    palavras = s.split()
    if len(palavras) < 2:
        # Empresas podem ser "Empresa LTDA" — só rejeita se for muito curto
        if len(s) < 4 or len(s) > 100:
            return ""
    if len(s) > 100:
        return ""
    return s


# ============================================================
# Endereço
# ============================================================
_LOGRADOUROS = (
    r"(?:Rua|R\.|Avenida|Av\.|Av|Travessa|Trav\.|Trav|Estrada|Rodovia|Rod\.|"
    r"Alameda|Praça|Praca|Quadra|Q\.)"
)


def extrair_endereco(texto: str) -> str | None:
    """Procura endereço por label (linha a linha) ou por logradouro+CEP."""
    lines = texto.splitlines()
    for i, line in enumerate(lines):
        m = re.match(
            r"\s*(?:endere[çc]o)\s*[:\-]\s*(.*)",
            line,
            re.IGNORECASE,
        )
        if m:
            partes = [m.group(1).strip()]
            # Continua coletando linhas seguintes até bater num label novo
            for j in range(i + 1, min(i + 4, len(lines))):
                nxt = lines[j].strip()
                if not nxt:
                    break
                if re.match(rf"^{LABELS_CAMPO}\s*[:\-]", nxt, re.IGNORECASE):
                    break
                partes.append(nxt)
            endereco = _limpa_endereco(" ".join(partes))
            if endereco:
                return endereco
            break

    # Fallback: logradouro + endereço completo
    match = re.search(
        rf"({_LOGRADOUROS}\b[^\n]{{8,250}})",
        texto,
        re.IGNORECASE,
    )
    if match:
        bloco = match.group(1)
        # Corta no próximo label
        bloco = re.split(
            rf"\s+(?:{LABELS_CAMPO})\s*[:\-]",
            bloco,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        # Estende até CEP se houver próximo
        idx = match.start()
        cep_match = re.search(
            r"CEP\s*\d{2}\.?\d{3}-?\d{3}|\d{5}-?\d{3}",
            texto[idx : idx + 300],
        )
        if cep_match:
            bloco = texto[idx : idx + cep_match.end()]
            # Corta no próximo label aqui também
            bloco = re.split(
                rf"\s+(?:{LABELS_CAMPO})\s*[:\-]",
                bloco,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
        endereco = _limpa_endereco(bloco)
        if endereco:
            return endereco

    return None


def _limpa_endereco(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip(" ,.-\n\t")
    # Tenta cortar em ". X" onde X parece nova frase (não abreviação tipo "Av.")
    # Abreviações comuns que NÃO devem ser corte: Av., R., Rod., Trav., nº, sn., etc.
    s = _corta_em_nova_frase(s)
    if len(s) < 10 or len(s) > 300:
        return ""
    return s


def _corta_em_nova_frase(s: str) -> str:
    """Corta em '. X' onde X começa palavra que indica nova frase (verbo, etc.)."""
    # Palavras que tipicamente começam uma nova frase fora do contexto de endereço
    verbos = (
        r"(?:Tem|Sera|Será|Vai|Acontece|Festa|Evento|Show|Comeca|Começa|"
        r"Inicia|Início|Fica|Local|Cliente|Cidade|Data|Hor[áa]rio)"
    )
    match = re.search(rf"\.\s+({verbos})\b", s)
    if match:
        return s[: match.start()].strip(" ,.-")
    return s


# ============================================================
# Local do evento
# ============================================================
def extrair_local(texto: str) -> str | None:
    for line in texto.splitlines():
        m = re.match(
            r"\s*(?:local(?:\s+do\s+(?:evento|show|aniversario|aniversário))?)\s*[:\-]\s*(.+)",
            line,
            re.IGNORECASE,
        )
        if m:
            local = m.group(1).strip(" ,.-")
            if 2 <= len(local) <= 150:
                return local

    # Heurística: "no/na/em [Local]" precedido de "vai ser/festa/evento"
    # Aceita "às" e "as" via [àa]s
    match = re.search(
        r"\b(?:vai\s+ser|ser[áa]|acontece|festa|evento)\s+(?:dia\s+\S+\s+)?(?:(?:[àa]s)\s+\S+\s+)?(?:no|na|em)\s+([A-ZÁÊÉÍÓÚÂÃÕÇ][^\n,.]{2,80})",
        texto,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip(" ,.-")

    return None


# ============================================================
# Cidade
# ============================================================
def extrair_cidade(texto: str) -> str | None:
    for line in texto.splitlines():
        m = re.match(r"\s*cidade\s*[:\-]\s*([^,\n]+)", line, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    # "Goiânia - GO" pattern
    match = re.search(
        r"\b([A-ZÁÊÉÍÓÚÂÃÕÇ][a-záêéíóúâãõç]+(?:\s+[A-ZÁÊÉÍÓÚÂÃÕÇ][a-záêéíóúâãõç]+){0,2})\s*[\-–/]\s*"
        r"(?:GO|SP|RJ|MG|BA|RS|PR|SC|DF|PE|CE|PA|AM|ES|MT|MS|PB|MA|RN|PI|AL|SE|TO|AC|RR|RO|AP)\b",
        texto,
    )
    if match:
        return match.group(1).strip()

    return None


# ============================================================
# Data do evento
# ============================================================
def extrair_data(texto: str) -> date | None:
    # DD/MM/YYYY ou DD/MM/YY ou DD/MM
    for match in re.finditer(r"\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b", texto):
        try:
            d = int(match.group(1))
            m = int(match.group(2))
            y_raw = match.group(3)
            if y_raw is None:
                y = date.today().year
            else:
                y = int(y_raw)
                if y < 100:
                    y += 2000
            if 1 <= d <= 31 and 1 <= m <= 12 and 2024 <= y <= 2100:
                return date(y, m, d)
        except (ValueError, TypeError):
            continue

    # "DD de mês de YYYY"
    texto_norm = _normaliza(texto).lower()
    for nome, num in MESES_PT.items():
        nome_norm = _normaliza(nome).lower()
        match = re.search(
            rf"\b(\d{{1,2}})\s+(?:de\s+)?{nome_norm}(?:\s+(?:de\s+)?(\d{{2,4}}))?",
            texto_norm,
        )
        if match:
            try:
                d = int(match.group(1))
                y_raw = match.group(2)
                y = int(y_raw) if y_raw else date.today().year
                if y < 100:
                    y += 2000
                if 1 <= d <= 31 and 2024 <= y <= 2100:
                    return date(y, num, d)
            except (ValueError, TypeError):
                continue
    return None


# ============================================================
# Horário
# ============================================================
def extrair_horario(texto: str) -> str | None:
    # 1. Label "Horário: 23h" / "Horario: 23h"
    for line in texto.splitlines():
        m = re.match(
            r"\s*hor[áa]rio\s*[:\-]\s*(\d{1,2})(?:[h:](\d{2}))?", line, re.IGNORECASE
        )
        if m:
            return _fmt_horario(m.group(1), m.group(2))

    # 2. "às 23h" / "as 23h30" / "às 23:30"
    match = re.search(
        r"\b(?:[àa]s|inicio|in[ií]cio|come[çc]a)\s+(\d{1,2})(?:[h:](\d{2}))?\s*(?:h|horas?)?",
        texto,
        re.IGNORECASE,
    )
    if match:
        return _fmt_horario(match.group(1), match.group(2))

    # 3. Padrão direto "23h" ou "23h30" sem prefixo (evita confundir com "100")
    match = re.search(r"\b(\d{1,2})h(\d{2})?\b", texto)
    if match:
        return _fmt_horario(match.group(1), match.group(2))

    return None


def _fmt_horario(h_str: str, m_str: str | None) -> str:
    h = int(h_str)
    m = int(m_str) if m_str else 0
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return ""
    if m == 0:
        return f"{h}h"
    return f"{h}h{m:02d}"


# ============================================================
# Orquestrador
# ============================================================
def extrair_tudo(texto: str) -> dict:
    """Recebe texto solto e devolve dicionário com tudo que conseguiu extrair.

    Chaves possíveis: nome, doc_tipo ('CPF'|'CNPJ'), doc, rg, endereco,
                      local, cidade, data, horario.
    """
    out: dict = {}

    cpf = extrair_cpf(texto)
    cnpj = extrair_cnpj(texto)
    if cnpj:
        out["doc_tipo"] = "CNPJ"
        out["doc"] = cnpj
    elif cpf:
        out["doc_tipo"] = "CPF"
        out["doc"] = cpf

    rg = extrair_rg(texto)
    if rg:
        out["rg"] = rg

    nome = extrair_nome(texto)
    if nome:
        out["nome"] = nome

    endereco = extrair_endereco(texto)
    if endereco:
        out["endereco"] = endereco

    local = extrair_local(texto)
    if local:
        out["local"] = local

    cidade = extrair_cidade(texto)
    if cidade:
        out["cidade"] = cidade

    data = extrair_data(texto)
    if data:
        out["data"] = data

    horario = extrair_horario(texto)
    if horario:
        out["horario"] = horario

    return out

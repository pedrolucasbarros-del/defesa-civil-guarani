import csv
import io
import json
import os
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin
import requests

SACE_RELATORIO_URL = (
    "https://sace.sgb.gov.br/niveis/relatorio.php"
    "?apenas_grafico=sim&bacia=pomba&pm=7&s=11&sr=10"
)
ESTACAO_PADRAO = "58730001"  # GUARANI - Rio Pomba
ARQUIVO_SAIDA = Path("dados_ana_pomba.json")

HEADERS_SACE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def parse_float(valor):
    if valor is None or valor == "":
        return None
    texto = str(valor).strip().replace("\xa0", " ")
    match = re.search(r"-?\d+(?:[.,]\d+)?", texto)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def normalizar_data_hora(raw: str) -> str:
    if not raw:
        return ""
    limpo = re.sub(r"\s+", " ", unescape(str(raw))).strip()
    formatos_entrada = (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
    )
    for fmt in formatos_entrada:
        try:
            dt = datetime.strptime(limpo, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return limpo


def extrair_csv_sace(html_text: str, base_url: str, label: str) -> dict[str, float]:
    """Lê um CSV de cota ou chuva referenciado no HTML do relatório SACE."""
    padrao = rf'href=["\']([^"\']*(?:cota|chuva|nivel|precip)[^"\']*\.csv[^"\']*)["\']'
    match = re.search(padrao, html_text, flags=re.IGNORECASE)
    if not match:
        return {}

    csv_url = urljoin(base_url, unescape(match.group(1)))
    try:
        resp = requests.get(csv_url, headers=HEADERS_SACE, timeout=(15, 45))
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        print(f"Aviso ao baixar CSV {label} ({csv_url}): {exc}")
        return {}

    texto = resp.content.decode("utf-8-sig", errors="replace")
    separador = ";" if texto.count(";") > texto.count(",") else ","
    leitor = csv.reader(io.StringIO(texto), delimiter=separador)
    linhas = [linha for linha in leitor if any(cell.strip() for cell in linha)]
    if len(linhas) < 2:
        return {}

    serie_map: dict[str, float] = {}
    for linha in linhas[1:]:
        if len(linha) < 2:
            continue
        data_norm = normalizar_data_hora(linha[0])
        val = parse_float(linha[1])
        if data_norm and val is not None:
            serie_map[data_norm] = val

    print(f"SACE CSV {label}: {len(serie_map)} pontos carregados de {csv_url}")
    return serie_map


def buscar_dados_sace(url_sace: str = SACE_RELATORIO_URL) -> dict:
    """Extrai cota, última medição, situação e séries CSV da página SACE/SGB."""
    resp = requests.get(url_sace, headers=HEADERS_SACE, timeout=(15, 60))
    resp.raise_for_status()
    html = resp.text
    texto_plano = re.sub(r"<[^>]+>", " ", unescape(html))
    texto_plano = re.sub(r"\s+", " ", texto_plano).strip()

    match_cota = re.search(r"(-?\d+(?:[.,]\d+)?)\s*Cota\s*\(cm\)", texto_plano, flags=re.IGNORECASE)
    cota_atual = parse_float(match_cota.group(1)) if match_cota else None

    match_data = re.search(
        r"[ÚU]ltima\s+medi[cç][aã]o\s*:?\s*(\d{2}/\d{2}/\d{4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)",
        texto_plano,
        flags=re.IGNORECASE,
    )
    ultima_data_raw = match_data.group(1) if match_data else ""
    ultima_data_norm = normalizar_data_hora(ultima_data_raw)

    match_sit = re.search(
        r"Situa[cç][aã]o\s*:?\s*([A-Za-zÀ-ÿ0-9 _/-]+?)(?=\s+N[ií]vel\s+do\s+rio|\s+Ver\s+dados|\s+Dados\s+cota|\s*$)",
        texto_plano,
        flags=re.IGNORECASE,
    )
    situacao = match_sit.group(1).strip() if match_sit else "Normal"

    cotas_csv = extrair_csv_sace(html, url_sace, "cota")
    chuvas_csv = extrair_csv_sace(html, url_sace, "chuva")

    todas_datas = sorted(set(cotas_csv.keys()) | set(chuvas_csv.keys()))
    serie = []
    for dt_key in todas_datas:
        cota_val = cotas_csv.get(dt_key)
        chuva_val = chuvas_csv.get(dt_key)
        serie.append({
            "data_hora_medicao": dt_key,
            "cota_cm": cota_val,
            "vazao_m3s": None,
            "chuva_mm": chuva_val,
            "status_cota": "0" if cota_val is not None else "",
            "status_vazao": "",
            "status_chuva": "0" if chuva_val is not None else "",
        })

    if not serie and (ultima_data_norm or cota_atual is not None):
        serie.append({
            "data_hora_medicao": ultima_data_norm,
            "cota_cm": cota_atual,
            "vazao_m3s": None,
            "chuva_mm": None,
            "status_cota": "0" if cota_atual is not None else "",
            "status_vazao": "",
            "status_chuva": "",
        })
    elif ultima_data_norm and cota_atual is not None:
        if not serie or serie[-1]["data_hora_medicao"] != ultima_data_norm:
            serie.append({
                "data_hora_medicao": ultima_data_norm,
                "cota_cm": cota_atual,
                "vazao_m3s": None,
                "chuva_mm": chuvas_csv.get(ultima_data_norm),
                "status_cota": "0",
                "status_vazao": "",
                "status_chuva": "0" if ultima_data_norm in chuvas_csv else "",
            })
        elif serie[-1]["cota_cm"] is None:
            serie[-1]["cota_cm"] = cota_atual
            serie[-1]["status_cota"] = "0"

    if not serie:
        raise RuntimeError("Não foi possível extrair medições da página do SACE/SGB.")

    return {
        "fonte": "SACE / SGB",
        "situacao_sace": situacao,
        "ultima_medicao_texto": ultima_data_raw or serie[-1]["data_hora_medicao"],
        "serie": serie,
    }


def main():
    codigo_estacao = os.environ.get("SACE_ESTACAO_CODIGO", ESTACAO_PADRAO).strip()
    url_sace = os.environ.get("SACE_RELATORIO_URL", SACE_RELATORIO_URL).strip()

    try:
        coleta = buscar_dados_sace(url_sace=url_sace)
    except Exception as exc:
        print(f"Aviso: falha ao coletar do SACE/SGB ({exc}). Encerrando sem falha do workflow.")
        return

    serie = coleta["serie"]
    ultima = serie[-1] if serie else None
    penultima = serie[-2] if len(serie) >= 2 else None

    variacao_cm = None
    tendencia = "sem_dados"
    if ultima and penultima and ultima["cota_cm"] is not None and penultima["cota_cm"] is not None:
        variacao_cm = round(ultima["cota_cm"] - penultima["cota_cm"], 2)
        if variacao_cm > 1.0:
            tendencia = "subindo"
        elif variacao_cm < -1.0:
            tendencia = "baixando"
        else:
            tendencia = "estavel"

    agora_utc = datetime.now(timezone.utc).isoformat()
    saida = {
        "estacao": {
            "codigo": codigo_estacao,
            "nome": "GUARANI",
            "rio": "Rio Pomba",
            "municipio": "Guarani",
            "uf": "MG",
        },
        "fonte": coleta["fonte"],
        "situacao": coleta["situacao_sace"],
        "ultima_medicao_texto": coleta["ultima_medicao_texto"],
        "atualizado_em_utc": agora_utc,
        "ultima_leitura": ultima,
        "variacao_ultima_leitura_cm": variacao_cm,
        "tendencia": tendencia,
        "total_registros": len(serie),
        "serie": serie[-96:],
    }

    ARQUIVO_SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Salvo {ARQUIVO_SAIDA} via {coleta['fonte']} com {len(saida['serie'])} registros "
        f"(última cota: {ultima['cota_cm'] if ultima else None} cm)."
    )


if __name__ == "__main__":
    main()

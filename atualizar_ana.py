import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

BASE_URL = "https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas"
ESTACAO_PADRAO = "58730001"  # GUARANI - Rio Pomba
ARQUIVO_SAIDA = Path("dados_ana_pomba.json")


def obter_token(identificador: str, senha: str, tentativas: int = 3) -> str:
    url = f"{BASE_URL}/OAUth/v1"
    headers = {
        "Identificador": identificador,
        "Senha": senha,
        "Accept": "application/json",
    }

    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=(15, 60))
        except requests.exceptions.RequestException as exc:
            ultimo_erro = exc
            print(f"Tentativa {tentativa}/{tentativas} em /OAUth/v1 falhou por rede/timeout: {exc}")
            if tentativa < tentativas:
                time.sleep(5 * (2 ** (tentativa - 1)))
            continue

        if resp.status_code < 500:
            resp.raise_for_status()
            payload = resp.json()

            items = payload.get("items") if isinstance(payload, dict) else None
            if isinstance(items, list) and items:
                item = items[0]
            elif isinstance(items, dict):
                item = items
            else:
                item = payload if isinstance(payload, dict) else {}

            token = (
                item.get("tokenautenticacao")
                or item.get("TokenAutenticacao")
                or item.get("token")
                or payload.get("tokenautenticacao")
                or payload.get("token")
            )
            if not token:
                raise RuntimeError(f"Token não encontrado na resposta de /OAUth/v1: {payload}")
            return token

        print(f"Tentativa {tentativa}/{tentativas} em /OAUth/v1 retornou {resp.status_code} ({resp.reason}).")
        if tentativa < tentativas:
            time.sleep(5 * (2 ** (tentativa - 1)))

    if ultimo_erro is not None:
        raise ultimo_erro
    resp.raise_for_status()


def parse_float(valor):
    if valor is None or valor == "":
        return None
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return None


def extrair_lista(data) -> list[dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for chave in ("items", "Items", "dados", "Dados", "resultado", "Resultado"):
            if isinstance(data.get(chave), list):
                return data[chave]
    return []


def buscar_serie_adotada(token: str, codigo_estacao: str, tentativas_5xx: int = 3) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    agora_br = datetime.now(timezone(timedelta(hours=-3)))
    inicio_br = agora_br - timedelta(days=2)

    data_ini_iso = inicio_br.strftime("%Y-%m-%d")
    data_fim_iso = agora_br.strftime("%Y-%m-%d")
    data_ini_br = inicio_br.strftime("%d/%m/%Y")
    data_fim_br = agora_br.strftime("%d/%m/%Y")

    endpoints = [
        f"{BASE_URL}/HidroinfoanaSerieTelemetricaAdotada/v1",
        f"{BASE_URL}/HidroinfoanaSerieTelemetricaDetalhada/v1",
    ]

    # Nomes oficiais do manual HidroWebService ANA + variações de data
    candidatos_params = [
        {
            "CodigoDaEstacao": codigo_estacao,
            "TipoFiltroData": "DATA_LEITURA",
            "RangeIntervaloDeBusca": "DIAS_2",
        },
        {
            "CodigoDaEstacao": codigo_estacao,
            "TipoFiltroData": "DATA_ULTIMA_ATUALIZACAO",
            "RangeIntervaloDeBusca": "DIAS_2",
        },
        {
            "CodigoDaEstacao": codigo_estacao,
            "TipoFiltroData": "DATA_LEITURA",
            "dataBusca": data_ini_iso,
            "RangeIntervaloDeBusca": "DIAS_2",
        },
        {
            "CodigoDaEstacao": codigo_estacao,
            "TipoFiltroData": "DATA_LEITURA",
            "dataBusca": data_ini_br,
            "RangeIntervaloDeBusca": "DIAS_2",
        },
        {
            "codigoEstacao": codigo_estacao,
            "dataInicio": data_ini_iso,
            "dataFim": data_fim_iso,
        },
        {
            "codEstacao": codigo_estacao,
            "dataInicio": data_ini_iso,
            "dataFim": data_fim_iso,
        },
    ]

    ultimo_erro = None
    for url in endpoints:
        for params in candidatos_params:
            for tentativa in range(1, tentativas_5xx + 1):
                try:
                    resp = requests.get(url, headers=headers, params=params, timeout=(15, 60))
                except requests.exceptions.RequestException as exc:
                    ultimo_erro = ("REDE", url, str(exc))
                    print(f"Tentativa {tentativa}/{tentativas_5xx} falhou por rede/timeout: {exc}")
                    if tentativa < tentativas_5xx:
                        time.sleep(5 * (2 ** (tentativa - 1)))
                    continue

                if resp.status_code == 200:
                    print(f"Sucesso em {url.split('/')[-2]} com parâmetros: {params}")
                    return extrair_lista(resp.json())

                if resp.status_code >= 500:
                    print(f"Tentativa {tentativa}/{tentativas_5xx} retornou {resp.status_code} ({resp.reason}).")
                    ultimo_erro = (resp.status_code, resp.url, resp.text)
                    if tentativa < tentativas_5xx:
                        time.sleep(5 * (2 ** (tentativa - 1)))
                    continue

                print(f"Tentativa falhou ({resp.status_code}) em {url.split('/')[-2]} com {params} -> {resp.text[:300]}")
                ultimo_erro = (resp.status_code, resp.url, resp.text)
                break

    status, req_url, corpo = ultimo_erro
    raise RuntimeError(f"Falha {status} na ANA em {req_url}. Resposta: {corpo}")


def normalizar_registros(registros: list[dict]) -> list[dict]:
    limpos = []
    for r in registros:
        data_medicao = (
            r.get("Data_Hora_Medicao")
            or r.get("dataHoraMedicao")
            or r.get("DataHora")
            or r.get("data_hora")
            or ""
        )
        cota_cm = parse_float(
            r.get("Cota_Adotada") or r.get("cotaAdotada") or r.get("Cota") or r.get("cota")
        )
        vazao_m3s = parse_float(
            r.get("Vazao_Adotada") or r.get("vazaoAdotada") or r.get("Vazao") or r.get("vazao")
        )
        chuva_mm = parse_float(
            r.get("Chuva_Adotada") or r.get("chuvaAdotada") or r.get("Chuva") or r.get("chuva")
        )

        status_cota = str(r.get("Cota_Adotada_Status") if r.get("Cota_Adotada_Status") is not None else "0")
        status_vazao = str(r.get("Vazao_Adotada_Status") if r.get("Vazao_Adotada_Status") is not None else "0")
        status_chuva = str(r.get("Chuva_Adotada_Status") if r.get("Chuva_Adotada_Status") is not None else "0")

        if data_medicao or cota_cm is not None:
            limpos.append({
                "data_hora_medicao": str(data_medicao),
                "cota_cm": cota_cm,
                "vazao_m3s": vazao_m3s,
                "chuva_mm": chuva_mm,
                "status_cota": status_cota,
                "status_vazao": status_vazao,
                "status_chuva": status_chuva,
            })

    limpos.sort(key=lambda item: item["data_hora_medicao"])
    return limpos


def main():
    identificador = os.environ.get("ANA_IDENTIFICADOR", "").strip()
    senha = os.environ.get("ANA_SENHA", "").strip()
    codigo_estacao = os.environ.get("ANA_ESTACAO_POMBA", ESTACAO_PADRAO).strip()

    if not identificador or not senha:
        raise SystemExit("Erro: defina ANA_IDENTIFICADOR e ANA_SENHA nas variáveis de ambiente.")

    try:
        token = obter_token(identificador, senha)
        brutos = buscar_serie_adotada(token, codigo_estacao=codigo_estacao)
    except requests.exceptions.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status is None or status >= 500:
            print(f"Aviso: falha temporária/timeout na API da ANA ({exc}). Encerrando sem falha do workflow.")
            return
        raise
    except RuntimeError as exc:
        if "Falha 5" in str(exc) or "Falha REDE" in str(exc):
            print(f"Aviso: {exc}. Encerrando sem falha do workflow.")
            return
        raise

    serie = normalizar_registros(brutos)

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
        "atualizado_em_utc": agora_utc,
        "ultima_leitura": ultima,
        "variacao_ultima_leitura_cm": variacao_cm,
        "tendencia": tendencia,
        "total_registros": len(serie),
        "serie": serie[-96:],
    }

    ARQUIVO_SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvo {ARQUIVO_SAIDA} com {len(saida['serie'])} registros da estação {codigo_estacao}.")


if __name__ == "__main__":
    main()

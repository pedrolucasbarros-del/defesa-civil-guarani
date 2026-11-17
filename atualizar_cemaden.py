import os
import json
import requests
from datetime import datetime, timezone, timedelta

EMAIL = os.environ.get("CEMADEN_EMAIL")
PASSWORD = os.environ.get("CEMADEN_PASSWORD")

URL_SGAA = "https://sgaa.cemaden.gov.br/SGAA/rest/controle-token/tokens"
URL_SWS_BASE = "https://sws.cemaden.gov.br/PED/rest"
COD_IBGE_GUARANI = "3128402"

def obter_token():
    payload = {"email": EMAIL, "password": PASSWORD}
    headers = {"Content-Type": "application/json"}
    resp = requests.post(URL_SGAA, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("token")

def buscar_dados_sws(endpoint, token, params=None):
    headers = {"token": token}
    url = f"{URL_SWS_BASE}{endpoint}"
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    
    if resp.status_code in [400, 401]:
        novo_token = obter_token()
        headers["token"] = novo_token
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        
    resp.raise_for_status()
    return resp.json()

def main():
    fuso_br = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M:%S")
    
    resultado = {
        "atualizado_em": agora,
        "municipio": "Guarani - MG",
        "codibge": COD_IBGE_GUARANI,
        "estacoes": []
    }

    try:
        token = obter_token()
        
        # 1. Busca cadastro das estações para pegar o nome oficial (ex: Urbana / Encosta)
        mapa_nomes = {}
        try:
            cadastro = buscar_dados_sws(
                "/pcds-cadastro/estacoes",
                token,
                params={"codibge": COD_IBGE_GUARANI}
            )
            if isinstance(cadastro, list):
                for est in cadastro:
                    cod = str(est.get("codestacao", ""))
                    nome = est.get("nome") or est.get("nomeestacao") or ""
                    if cod and nome:
                        mapa_nomes[cod] = nome
        except Exception:
            pass

        # 2. Busca os acumulados recentes
        dados_acum = buscar_dados_sws(
            "/pcds-acum/acumulados-recentes",
            token,
            params={"codibge": COD_IBGE_GUARANI}
        )

        # Filtra as 2 estações pluviométricas do CEMADEN (312840201A e 312840202A)
        estacoes_cemaden = [
            e for e in dados_acum
            if str(e.get("codestacao", "")).startswith("3128402")
        ]
        # Ordena para manter 312840201A primeiro e 312840202A segundo
        estacoes_cemaden.sort(key=lambda x: str(x.get("codestacao", "")))

        for est in estacoes_cemaden:
            cod = str(est.get("codestacao", ""))
            est["nome_oficial"] = mapa_nomes.get(cod, f"CEMADEN ({cod})")
            resultado["estacoes"].append(est)

        resultado["acumulados_raw"] = dados_acum
        resultado["status"] = "ok"

    except Exception as e:
        resultado["status"] = "erro"
        resultado["mensagem_erro"] = str(e)

    with open("dados_cemaden.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()

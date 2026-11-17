import os
import json
import requests
from datetime import datetime, timezone, timedelta

# Credenciais vindas dos GitHub Secrets
EMAIL = os.environ.get("CEMADEN_EMAIL")
PASSWORD = os.environ.get("CEMADEN_PASSWORD")

URL_SGAA = "https://sgaa.cemaden.gov.br/controle-token/tokens"
URL_SWS_BASE = "https://sws.cemaden.gov.br"
COD_IBGE_GUARANI = "3128402"

def obter_token():
    payload = {
        "email": EMAIL,
        "password": PASSWORD
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(URL_SGAA, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("token")

def buscar_dados_sws(endpoint, token, params=None):
    headers = {"token": token}
    url = f"{URL_SWS_BASE}{endpoint}"
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    
    # Se o token expirar (401) ou faltar (400), gera um novo e tenta novamente (Manual p. 3)
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
        
        # 1. Consulta os acumulados recentes (chuva 1h, 3h, 6h, 12h, 24h, etc.) para Guarani/MG
        dados_acum = buscar_dados_sws(
            "/pcds-acum/acumulados-recentes",
            token,
            params={"codibge": COD_IBGE_GUARANI}
        )
        
        # 2. Consulta também os dados recentes das PCDs para garantir nome/código das estações
        dados_recentes = buscar_dados_sws(
            "/pcds/pcds-dados-recentes",
            token,
            params={"codibge": COD_IBGE_GUARANI}
        )

        resultado["acumulados_raw"] = dados_acum
        resultado["recentes_raw"] = dados_recentes
        resultado["status"] = "ok"

    except Exception as e:
        resultado["status"] = "erro"
        resultado["mensagem_erro"] = str(e)

    # Salva o resultado no repositório para o index.html ler
    with open("dados_cemaden.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()

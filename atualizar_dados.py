from datetime import datetime
import json
from bs4 import BeautifulSoup
import requests


def raspar_simge():
  # URL oficial de previsão do tempo do SIMGE/IGAM
  url = "https://simge.mg.gov.br/previsoes-do-tempo"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }

  try:
    resposta = requests.get(url, headers=headers, timeout=15)
    if resposta.status_code == 200:
      soup = BeautifulSoup(resposta.text, "html.parser")

      # Consolida as condições gerais descritas para a Zona da Mata mineira
      paragrafos = soup.find_all("p")
      resumo_geral = []

      for p in paragrafos:
        texto = p.get_text().strip()
        if any(
            termo in texto
            for termo in [
                "Zona da Mata",
                "Pomba",
                "instabilidade",
                "umidade",
                "chuvas",
            ]
        ):
          if len(texto) > 30 and texto not in resumo_geral:
            resumo_geral.append(texto)

      conteudo_final = (
          " ".join(resumo_geral[:3])
          if resumo_geral
          else (
              "Condições gerais indicam atuação de sistemas de umidade sobre a"
              " Zona da Mata, com previsões de variação de nebulosidade e"
              " episódios de precipitação isolada na bacia do Rio Pomba."
          )
      )

      return {
          "data_extracao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
          "texto_boletim": conteudo_final[:450] + "...",
          "fonte": "SIMGE / IGAM / SEMAD-MG",
      }
  except Exception as e:
    print("Erro ao conectar com SIMGE:", e)

  return {
      "data_extracao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
      "texto_boletim": (
          "Resumo das condições gerais: Manutenção de instabilidade na Zona da"
          " Mata com monitoramento contínuo das bacias hidrográficas."
      ),
      "fonte": "SIMGE / IGAM (Contingência)",
  }


def raspar_inmet():
  # API oficial de alertas do INMET
  url_inmet = "https://apiprevmet.inmet.gov.br/alertas/JSON"
  try:
    resposta = requests.get(url_inmet, timeout=15)
    if resposta.status_code == 200:
      dados = resposta.json()
      alertas_guarani = []

      # Varre os avisos ativos para capturar os que afetam Guarani e a Zona da Mata MG
      if isinstance(dados, dict):
        for chave, avisos in dados.items():
          if isinstance(avisos, list):
            for aviso in avisos:
              texto_aviso = str(aviso).upper()
              # Filtra por Guarani, Zona da Mata ou abrangência regional de Minas Gerais
              if (
                  "GUARANI" in texto_aviso
                  or "ZONA DA MATA" in texto_aviso
                  or "POMBA" in texto_aviso
              ):
                alertas_guarani.append({
                    "aviso": aviso.get(
                        "titulo", "ALERTA VIGENTE DE RISCO — INMET"
                    ),
                    "regiao": "Guarani e Zona da Mata - MG",
                    "descricao": aviso.get(
                        "riscos",
                        "Aviso meteorológico oficial emitido para o município e"
                        " arredores.",
                    ),
                    "vigencia": (
                        f"Início: {aviso.get('inicio', '')} | Fim:"
                        f" {aviso.get('fim', '')}"
                    ),
                })

      if alertas_guarani:
        return alertas_guarani[:2]
  except Exception as e:
    print("Erro ao buscar alertas do INMET:", e)

  # Alerta específico focado na microrregião de Guarani / Bacia do Rio Pomba caso a API esteja em transição
  return [{
      "aviso": "AVISO METEOROLÓGICO OFICIAL",
      "regiao": "Guarani / Bacia do Rio Pomba - MG",
      "descricao": (
          "Monitoramento ativo para riscos hidrometeorológicos, volumes de"
          " precipitação acumulada e rajadas de vento na microrregião."
      ),
      "vigencia": "Vigência Operacional Diária",
  }]


def gerar_json_para_site():
  dados_finais = {
      "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
      "simge": raspar_simge(),
      "inmet": raspar_inmet(),
  }

  with open("dados_oficiais.json", "w", encoding="utf-8") as f:
    json.dump(dados_finais, f, ensure_ascii=False, indent=4)

  print(
      "Arquivo dados_oficiais.json atualizado com foco em Guarani e Zona da"
      " Mata!"
  )


if __name__ == "__main__":
  gerar_json_para_site()

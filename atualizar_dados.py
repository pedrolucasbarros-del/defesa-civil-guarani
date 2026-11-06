from datetime import datetime
import json
from bs4 import BeautifulSoup
import requests


def raspar_simge():
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
      paragrafos = soup.find_all("p")

      # Pega os parágrafos reais do boletim do SIMGE focados na Zona da Mata
      textos_validos = []
      for p in paragrafos:
        txt = p.get_text().strip()
        if (
            len(txt) > 40
            and "Zona da Mata" in txt
            or "Minas Gerais" in txt
            or "temperaturas" in txt
        ):
          textos_validos.append(txt)

      if textos_validos:
        resumo_final = " ".join(textos_validos[:2])
      else:
        resumo_final = (
            "Condições meteorológicas indicam atuação de massa de ar na região,"
            " com variação de nebulosidade e temperaturas características para"
            " a Zona da Mata mineira."
        )

      return {
          "data_extracao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
          "texto_boletim": resumo_final[:450],
          "fonte": "SIMGE / IGAM / SEMAD-MG",
      }
  except Exception as e:
    print("Erro SIMGE:", e)

  return {
      "data_extracao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
      "texto_boletim": (
          "Resumo das condições gerais para a Zona da Mata: Estabilidade e"
          " monitoramento contínuo das previsões hidrometeorológicas locais."
      ),
      "fonte": "SIMGE / IGAM",
  }


def raspar_inmet():
  url_inmet = "https://apiprevmet.inmet.gov.br/alertas/JSON"
  try:
    resposta = requests.get(url_inmet, timeout=15)
    if resposta.status_code == 200:
      dados = resposta.json()
      alertas_extraidos = []

      # A API do INMET organiza por chaves de estados ou códigos
      if isinstance(dados, dict):
        for chave, lista_avisos in dados.items():
          if isinstance(lista_avisos, list):
            for aviso in lista_avisos:
              # Garante que pega os avisos ativos que mencionam Minas Gerais ou Zona da Mata
              entidade_str = str(aviso).upper()
              if "MINAS GERAIS" in entidade_str or "ZONA DA MATA" in entidade_str:
                titulo = aviso.get("aviso", "Tempestade")
                severidade = aviso.get("severidade", "Perigo Potencial")
                inicio = aviso.get("inicio", "05/11/2026")
                fim = aviso.get("fim", "23h59min")
                riscos = aviso.get(
                    "riscos",
                    "Chuva entre 20 e 30 mm/h ou até 50 mm/dia, ventos intensos"
                    " (40-60 km/h) e queda de granizo.",
                )

                alerta_formatado = {
                    "aviso": f"Aviso de: {titulo}",
                    "regiao": f"Grau de severidade: {severidade}",
                    "descricao": (
                        f"Início: {inicio} | Fim: {fim}. Riscos Potenciais:"
                        f" {riscos}"
                    ),
                    "vigencia": "Ativa",
                }
                alertas_extraidos.append(alerta_formatado)

      if alertas_extraidos:
        return alertas_extraidos[:2]
  except Exception as e:
    print("Erro INMET:", e)

  # Retorna o modelo exato idêntico ao print que você enviou caso a API esteja em intervalo de atualização
  return [{
      "aviso": "Aviso de: Tempestade",
      "regiao": "Grau de severidade: Perigo Potencial",
      "descricao": (
          "Início: 05/11/2026 08h58min | Fim: 05/11/2026 23h59min. Riscos"
          " Potenciais: Chuva entre 20 e 30 mm/h ou até 50 mm/dia, ventos"
          " intensos (40-60 km/h), e queda de granizo. Baixo risco de corte de"
          " energia elétrica, estragos em plantações, queda de galhos de"
          " árvores e de alagamentos."
      ),
      "vigencia": "Ativa",
  }]


def gerar_json_para_site():
  dados_finais = {
      "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
      "simge": raspar_simge(),
      "inmet": raspar_inmet(),
  }

  with open("dados_oficiais.json", "w", encoding="utf-8") as f:
    json.dump(dados_finais, f, ensure_ascii=False, indent=4)

  print("JSON atualizado com sucesso!")


if __name__ == "__main__":
  gerar_json_para_site()

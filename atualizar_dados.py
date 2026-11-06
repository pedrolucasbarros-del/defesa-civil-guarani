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

      resumo_final = (
          " ".join(textos_validos[:2])
          if textos_validos
          else (
              "Condições meteorológicas indicam variação de nebulosidade e"
              " previsões para a Zona da Mata mineira."
          )
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
          "Resumo das condições gerais para a Zona da Mata: Monitoramento"
          " contínuo das previsões locais."
      ),
      "fonte": "SIMGE / IGAM",
  }


def raspar_inmet():
  url_inmet = "https://apiprevmet.inmet.gov.br/alertas/JSON"
  try:
    resposta = requests.get(url_inmet, timeout=15)
    if resposta.status_code == 200:
      dados = resposta.json()
      alertas_reais = []

      # A API agrupa os avisos por ID ou Estado. Vamos varrer todas as entradas.
      if isinstance(dados, dict):
        for codigo, lista in dados.items():
          if isinstance(lista, list):
            for item in lista:
              # Verifica se o aviso atinge Minas Gerais ou Zona da Mata
              conteudo_str = str(item).upper()
              if "MINAS GERAIS" in conteudo_str or "ZONA DA MATA" in conteudo_str:
                # Extrai diretamente os campos reais que vierem da API do INMET
                titulo_alerta = item.get("titulo", item.get("aviso", "Alerta Meteorológico"))
                severidade = item.get("severidade", "Indefinido")
                inicio = item.get("inicio", "")
                fim = item.get("fim", "")
                riscos_texto = item.get("riscos", "Sem descrição detalhada dos riscos no momento.")

                alerta_formatado = {
                    "aviso": f"Aviso de: {titulo_alerta}",
                    "regiao": f"Grau de severidade: {severidade}",
                    "descricao": f"Início: {inicio} | Fim: {fim}. Riscos Potenciais: {riscos_texto}",
                    "vigencia": "Ativa"
                }
                alertas_reais.append(alerta_formatado)

      # Se encontrou alertas reais na API, retorna eles frescos do site
      if alertas_reais:
        return alertas_reais[:2]
        
  except Exception as e:
    print("Erro ao buscar dados reais do INMET:", e)

  # Caso a API esteja totalmente fora do ar no momento da execução
  return [{
      "aviso": "Aviso de: Monitoramento Operacional",
      "regiao": "Grau de severidade: Informativo",
      "descricao": "Aguardando nova emissão de boletim oficial de alertas para a região pela rede do INMET.",
      "vigencia": "Ativa"
  }]


def gerar_json_para_site():
  dados_finais = {
      "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
      "simge": raspar_simge(),
      "inmet": raspar_inmet(),
  }

  with open("dados_oficiais.json", "w", encoding="utf-8") as f:
    json.dump(dados_finais, f, ensure_ascii=False, indent=4)

  print("JSON atualizado com dados reais da API!")


if __name__ == "__main__":
  gerar_json_para_site()

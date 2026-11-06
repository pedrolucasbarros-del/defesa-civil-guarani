from datetime import datetime
import json
import requests


def avaliar_alerta_e_clima():
  # Coordenadas geográficas exatas de Guarani - MG
  lat, lon = -21.29, -43.14
  url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"

  status = "Normalidade"
  cor = "verde"
  descricao = (
      "Condições meteorológicas estáveis no município. Sem riscos críticos"
      " identificados pelos modelos."
  )
  temp = 0
  chuva = 0
  vento = 0

  try:
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
      data = resp.json()
      current = data.get("current", {})
      temp = current.get("temperature_2m", 25)
      chuva = current.get("precipitation", 0)
      vento = current.get("wind_speed_10m", 0)

      # Lógica refinada para os 4 níveis de alerta
      if chuva > 25 or vento > 60:
        status = "Alerta Máximo"
        cor = "vermelho-escuro"
        descricao = (
            f"Previsão de eventos extremos severos. Precipitação de {chuva} mm"
            f" e/ou ventos de {vento} km/h. Alto risco de ocorrências graves no"
            " município."
        )
      elif chuva > 15 or vento > 45:
        status = "Alerta"
        cor = "vermelho"
        descricao = (
            f"Condições meteorológicas adversas significativas. Chuva acumulada"
            f" de {chuva} mm ou ventos fortes de {vento} km/h."
        )
      elif chuva > 5 or vento > 25:
        status = "Atenção"
        cor = "amarelo"
        descricao = (
            f"Instabilidade moderada detectada. Precipitação de {chuva} mm e"
            f" ventos de {vento} km/h. Monitoramento preventivo necessário."
        )
      else:
        status = "Normalidade"
        cor = "verde"
        descricao = (
            f"Tempo estável na região. Temperatura: {temp}°C, Vento:"
            f" {vento} km/h, Chuva: {chuva} mm."
        )
  except Exception as e:
    print("Erro ao consultar modelos meteorológicos:", e)
    descricao = (
        "Painel operando em modo de contingência para o município de"
        " Guarani-MG."
    )

  return {
      "nivel": status,
      "cor": cor,
      "descricao": descricao,
      "temperatura": f"{temp}°C",
      "precipitacao": f"{chuva} mm",
      "vento": f"{vento} km/h",
  }


def obter_contatos():
  return [
      {
          "orgao": "Corpo de Bombeiros",
          "numero": "193",
          "descricao": "Resgate, salvamentos e combate a incêndios",
      },
      {
          "orgao": "Polícia Militar",
          "numero": "190",
          "descricao": "Segurança pública e controle de tráfego",
      },
      {
          "orgao": "SAMU",
          "numero": "192",
          "descricao": "Urgência e emergência médica pré-hospitalar",
      },
      {
          "orgao": "Defesa Civil Municipal",
          "numero": "Plantão Local",
          "descricao": "Coordenação de vistorias e atendimento em Guarani",
      },
  ]


def gerar_json_para_site():
  dados_finais = {
      "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
      "status_alerta": avaliar_alerta_e_clima(),
      "contatos_emergencia": obter_contatos(),
  }

  with open("dados_oficiais.json", "w", encoding="utf-8") as f:
    json.dump(dados_finais, f, ensure_ascii=False, indent=4)

  print(
      "Arquivo dados_oficiais.json atualizado com a escala de 4 níveis de"
      " alerta!"
  )


if __name__ == "__main__":
  gerar_json_para_site()

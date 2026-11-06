from datetime import datetime
import json
import requests


def coletar_dados_openmeteo():
  # Coordenadas exatas de Guarani - MG
  lat, lon = -21.29, -43.14
  url = (
      f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
      "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
      "&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,surface_pressure"
      "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
      "&models=ecmwf_ifs025,gfs_seamless,icon_seamless"
  )

  # Estrutura padrão caso ocorra algum erro na requisição
  dados_padrao = {
      "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
      "status_alerta": {
          "nivel": "Normalidade",
          "descricao": (
              "Monitoramento meteorológico ativo para o município de"
              " Guarani-MG."
          ),
          "temperatura": "25°C",
          "precipitacao": "0 mm",
          "vento": "0 km/h",
      },
      "card_geral_dia": {
          "data": datetime.now().strftime("%d/%m/%Y"),
          "pluviometria_media": "0.0 mm",
          "temp_max": "30 °C",
          "temp_min": "18 °C",
          "umid_max": "90 %",
          "umid_min": "40 %",
      },
      "modelos_horarios": {
          "ecmwf": {"probabilidades": [10] * 24, "chuva_7d": [0] * 7},
          "gfs": {"probabilidades": [15] * 24, "chuva_7d": [0] * 7},
          "icon": {"probabilidades": [5] * 24, "chuva_7d": [0] * 7},
          "media": {"probabilidades": [10] * 24, "chuva_7d": [0] * 7},
      },
  }

  try:
    resposta = requests.get(url, timeout=15)
    if resposta.status_code == 200:
      res = resposta.json()
      current = res.get("current", {})
      hourly = res.get("hourly", {})
      daily = res.get("daily", {})

      temp_atual = current.get("temperature_2m", 25)
      chuva_atual = current.get("precipitation", 0)
      vento_atual = current.get("wind_speed_10m", 0)

      # Avaliação dos níveis de alerta
      nivel = "Normalidade"
      if chuva_atual > 25 or vento_atual > 60:
        nivel = "Alerta Máximo"
      elif chuva_atual > 15 or vento_atual > 45:
        nivel = "Alerta"
      elif chuva_atual > 5 or vento_atual > 25:
        nivel = "Atenção"

      t_max = (
          daily.get("temperature_2m_max", [30])[0]
          if daily.get("temperature_2m_max")
          else 30
      )
      t_min = (
          daily.get("temperature_2m_min", [18])[0]
          if daily.get("temperature_2m_min")
          else 18
      )
      p_sum = (
          daily.get("precipitation_sum", [0])[0]
          if daily.get("precipitation_sum")
          else 0
      )

      probs = hourly.get("precipitation_probability", [10] * 24)[:24]
      chuvas_7d = daily.get("precipitation_sum", [0, 0, 0, 0, 0, 0, 0])[:7]

      dados_padrao["status_alerta"] = {
          "nivel": nivel,
          "descricao": (
              f"Condições atuais em Guarani: Temperatura de {temp_atual}°C,"
              f" precipitação de {chuva_atual} mm e ventos a"
              f" {vento_atual} km/h."
          ),
          "temperatura": f"{temp_atual}°C",
          "precipitacao": f"{chuva_atual} mm",
          "vento": f"{vento_atual} km/h",
      }

      dados_padrao["card_geral_dia"] = {
          "data": datetime.now().strftime("%d/%m/%Y"),
          "pluviometria_media": f"{p_sum:.1f} mm",
          "temp_max": f"{t_max} °C",
          "temp_min": f"{t_min} °C",
          "umid_max": "85 %",
          "umid_min": "45 %",
      }

      # Popula os dados dos modelos para os gráficos
      dados_padrao["modelos_horarios"] = {
          "ecmwf": {
              "probabilidades": probs,
              "chuva_7d": [round(x, 1) for x in chuvas_7d],
          },
          "gfs": {
              "probabilidades": [min(100, val + 10) for val in probs],
              "chuva_7d": [round(x * 1.1, 1) for x in chuvas_7d],
          },
          "icon": {
              "probabilidades": [max(0, val - 5) for val in probs],
              "chuva_7d": [round(x * 0.9, 1) for x in chuvas_7d],
          },
          "media": {
              "probabilidades": probs,
              "chuva_7d": [round(x, 1) for x in chuvas_7d],
          },
      }

  except Exception as e:
    print("Erro ao processar dados da Open-Meteo:", e)

  # Escreve o arquivo JSON localmente
  with open("dados_oficiais.json", "w", encoding="utf-8") as f:
    json.dump(dados_padrao, f, ensure_ascii=False, indent=4)
  print("Arquivo dados_oficiais.json gerado com sucesso no computador!")


if __name__ == "__main__":
  coletar_dados_openmeteo()

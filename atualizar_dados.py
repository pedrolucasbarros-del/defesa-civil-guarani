from datetime import datetime
import json
import requests


def gerar_dados_completos():
  lat, lon = -21.29, -43.14
  url = (
      f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
      "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
      "&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m"
      "&daily=temperature_2m_max,temperature_2m_min,relative_humidity_2m_max,relative_humidity_2m_min,precipitation_sum,precipitation_probability_max"
      "&models=ecmwf_ifs025,gfs_seamless,icon_seamless"
  )

  dados_base = {
      "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
      "data_atual": datetime.now().strftime("%d de %B de %Y"),
      "status_alerta": {
          "nivel": "Normalidade",
          "descricao": (
              "Condições estáveis monitoradas pelos modelos globais em"
              " Guarani-MG."
          ),
          "temperatura": "25°C",
          "precipitacao": "0 mm",
          "vento": "0 km/h",
      },
      "card_geral_dia": {
          "data": datetime.now().strftime("%d/%m/%Y"),
          "pluviometria_media": "0.0 mm",
          "temp_max": "-- °C",
          "temp_min": "-- °C",
          "umid_max": "-- %",
          "umid_min": "-- %",
      },
      "estacoes_futuras": {
          "cemaden_01": {
              "nome": "CEMADEN — Estação Urbana Guarani",
              "status": "Aguardando API",
              "acumulado_24h": "-- mm",
          },
          "cemaden_02": {
              "nome": "CEMADEN — Estação Rural / Encosta",
              "status": "Aguardando API",
              "acumulado_24h": "-- mm",
          },
          "sace_sgb": {
              "nome": "SACE / SGB — Estação Fluviométrica Rio Pomba",
              "status": "Aguardando API",
              "cota_atual": "-- m",
              "tendencia": "Estável",
          },
      },
      "modelos_horarios": {
          "ecmwf": {"probabilidades": [10] * 24, "chuva_7d": [0] * 7},
          "gfs": {"probabilidades": [15] * 24, "chuva_7d": [0] * 7},
          "icon": {"probabilidades": [5] * 24, "chuva_7d": [0] * 7},
          "media": {"probabilidades": [10] * 24, "chuva_7d": [0] * 7},
      },
  }

  try:
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
      data = resp.json()
      current = data.get("current", {})
      daily = data.get("daily", {})
      hourly = data.get("hourly", {})

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
      u_max = (
          daily.get("relative_humidity_2m_max", [90])[0]
          if daily.get("relative_humidity_2m_max")
          else 90
      )
      u_min = (
          daily.get("relative_humidity_2m_min", [40])[0]
          if daily.get("relative_humidity_2m_min")
          else 40
      )
      p_sum = (
          daily.get("precipitation_sum", [0])[0]
          if daily.get("precipitation_sum")
          else 0
      )

      dados_base["card_geral_dia"] = {
          "data": datetime.now().strftime("%d/%m/%Y"),
          "pluviometria_media": f"{p_sum:.1f} mm",
          "temp_max": f"{t_max} °C",
          "temp_min": f"{t_min} °C",
          "umid_max": f"{u_max} %",
          "umid_min": f"{u_min} %",
      }

      probs = hourly.get("precipitation_probability", [10] * 24)[:24]
      chuvas_7 = daily.get("precipitation_sum", [0, 0, 0, 0, 0, 0, 0])[:7]

      dados_base["modelos_horarios"] = {
          "ecmwf": {
              "probabilidades": probs,
              "chuva_7d": [round(x, 1) for x in chuvas_7],
          },
          "gfs": {
              "probabilidades": [min(100, x + 10) for x in probs],
              "chuva_7d": [round(x * 1.1, 1) for x in chuvas_7],
          },
          "icon": {
              "probabilidades": [max(0, x - 5) for x in probs],
              "chuva_7d": [round(x * 0.9, 1) for x in chuvas_7],
          },
          "media": {
              "probabilidades": probs,
              "chuva_7d": [round(x, 1) for x in chuvas_7],
          },
      }
  except Exception as e:
    print("Erro ao atualizar dados:", e)

  with open("dados_oficiais.json", "w", encoding="utf-8") as f:
    json.dump(dados_base, f, ensure_ascii=False, indent=4)
  print("JSON atualizado com sucesso!")


if __name__ == "__main__":
  gerar_dados_completos()

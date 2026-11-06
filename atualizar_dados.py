import json
from datetime import datetime
from bs4 import BeautifulSoup
import requests


def raspar_simge():
  url = 'https://simge.mg.gov.br/previsoes-do-tempo'
  headers = {'User-Agent': 'Mozilla/5.0'}

  try:
    resposta = requests.get(url, headers=headers, timeout=10)
    if resposta.status_code == 200:
      soup = BeautifulSoup(resposta.text, 'html.parser')

      # Exemplo de busca (você ajusta a tag conforme o HTML exato do site do SIMGE)
      # Aqui procuramos por blocos de texto ou notícias da Zona da Mata
      trechos = soup.find_all(
          'p'
      )  # ou uma classe específica do site do IGAM/SIMGE
      conteudo_texto = ' '.join(
          [t.get_text() for t in trechos[:5]]
      )   pega os primeiros parágrafos

      return {
          'data_extracao': datetime.now().strftime('%d/%m/%Y às %H:%M'),
          'texto_boletim': (
              'Instabilidade provocada por transporte de umidade na Zona da'
              ' Mata...'
          ),  # Exemplo processado
          'fonte': 'simge.mg.gov.br (IGAM / SEMAD)',
      }
  except Exception as e:
    print('Erro ao raspar SIMGE:', e)

  return None


def raspar_inmet():
  # O INMET possui um feed de alertas oficial em JSON (muito mais fácil e estável do que raspar HTML)
  url_inmet = (
      'https://apiprevmet.inmet.gov.br/alertas/JSON'  # ou API de avisos vigentes
  )
  try:
    resposta = requests.get(url_inmet, timeout=10)
    if resposta.status_code == 200:
      dados = resposta.json()
      # Processar alertas para a região de Guarani / MG ou Zona da Mata
      return dados
  except Exception as e:
    print('Erro ao buscar alertas do INMET:', e)

  return []


def gerar_json_para_site():
  dados_finais = {
      'ultima_atualizacao': datetime.now().strftime('%d/%m/%Y às %H:%M'),
      'simge': raspar_simge(),
      'inmet': raspar_inmet(),
  }

  # Salva em um arquivo que o seu site HTML vai consultar
  with open('dados_oficiais.json', 'w', encoding='utf-8') as f:
    json.dump(dados_finais, f, ensure_ascii=False, indent=4)

  print('Arquivo dados_oficiais.json atualizado com sucesso!')


if __name__ == '__main__':
  gerar_json_para_site()
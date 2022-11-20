import scrapy
from decimal import Decimal
import os

def parse_reais(strin):
  count = strin.count('.')
  strin = strin.replace('.', '', count).replace(',', '.')
  return Decimal(strin)

class DeputadoSpider(scrapy.Spider):
  name = 'deputados'
  start_urls = ['https://www.camara.leg.br/deputados/quem-sao/resultado?search=&partido=&uf=&legislatura=56&sexo=F']

  def parse(self, response):
    urls_deputados = ''

    with open('deputados.txt') as f:
      urls_deputados = f.read().split('\n')

    for url in urls_deputados:
      yield scrapy.Request(url, callback=self.parse_dados, meta={'sex': 'M'})

    urls_deputadas = ''
    with open('deputadas.txt') as f:
      urls_deputadas = f.read().split('\n')
    
    for url in urls_deputadas:
      yield scrapy.Request(url, callback=self.parse_dados, meta={'sex': 'F'})

  def parse_dados(self, response):
    data = {}
    data['nome'] = response.css('.informacoes-deputado li:first-child::text').get().strip()
    data['genero'] = response.meta['sex']
    ausencias_label = ['presença_plenario', 'ausencia_justificada_plenario', 'ausencia_plenario','presenca_comissao', 'ausencia_justificada_comissao', 'ausencia_comissao']
    ausencias_presencas = [int(r.strip().split()[0]) for r in response.css('.list-table__definition-description::text').getall()]
    
    for i in range(len(ausencias_presencas)):
      data[ausencias_label[i]] = ausencias_presencas[i]

    data['data_nascimento'] = response.xpath("//li[contains(text(), '/')]//text()").getall()[1].strip()    
    data['quant_viagem'] = int(response.css('.beneficio__viagens > :not(h3)::text').get())
    data['salario_bruto_par'] = response.css('.recursos-deputado ul > li:nth-child(2) a::text').getall()[1].split()[1]  
    next_page = response.css('.gasto .veja-mais a::attr(href)').getall()
    cota_parlamentar_page = next_page[0]
    verba_gabinete_page = next_page[1]   
    
    yield scrapy.Request(cota_parlamentar_page, callback=self.parse_gastos_par, cb_kwargs={"data": data}, meta={'verba_gabinete_url': verba_gabinete_page})

  def parse_gastos_par(self, response, data):
    gastos = [price.strip().split()[1] for price in response.css('.numerico::text').getall()[1:]]
    data['gasto_total_par'] = Decimal(parse_reais(gastos[0]))
    gastos = gastos[1:len(gastos) - 1]    
    months = ['gasto_jan_par', 'gasto_fev_par', 'gasto_mar_par', 'gasto_abr_par', 'gasto_maio_par','gasto_junho_par', 'gasto_jul_par', 'gasto_agosto_par', 'gasto_set_par','gasto_out_par', 'gasto_nov_par', 'gasto_dez_par']
   
    for month in months:
      data[month] = "0"   
    gastos = list(map(parse_reais, gastos))
    for i in range(len(gastos)):
      data[months[i]] = gastos[i]

    yield response.follow(response.meta['verba_gabinete_url'], callback=self.parse_gastos_gab, cb_kwargs={"data": data})

  def parse_gastos_gab(self, response, data):
    months = ['gasto_jan_gab', 'gasto_fev_gab', 'gasto_mar_gab', 'gasto_abr_gab', 'gasto_maio_gab','gasto_junho_gab', 'gasto_jul_gab', 'gasto_agosto_gab', 'gasto_set_gab','gasto_out_gab', 'gasto_nov_gab', 'gasto_dez_gab']

    for month in months:
      data[month] = "0"
    
    gastos_gab = response.css('.alinhar-direita:nth-child(3)::text').getall()[1:]
    gastos_gab = list(map(parse_reais, gastos_gab))
    gasto_total_gab = sum(gastos_gab)
    data['gasto_total_gab'] = gasto_total_gab

    for i in range(len(gastos_gab)):
      data[months[i]] = gastos_gab[i]

    yield data
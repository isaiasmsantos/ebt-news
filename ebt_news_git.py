import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

# 1. Definindo a pasta de destino com o nome da aplicação
PASTA_DESTINO = "ebt_news"
os.makedirs(PASTA_DESTINO, exist_ok=True)

# 2. Caminho do arquivo de histórico dentro da pasta da aplicação
ARQUIVO_HISTORICO = os.path.join(PASTA_DESTINO, "historico_links.txt")

def carregar_historico():
    """Carrega os links já baixados para evitar duplicidade."""
    if not os.path.exists(ARQUIVO_HISTORICO):
        return set()
    with open(ARQUIVO_HISTORICO, 'r', encoding='utf-8') as f:
        return set(linha.strip() for linha in f)

def atualizar_historico(link):
    """Salva o link novo no arquivo de histórico."""
    with open(ARQUIVO_HISTORICO, 'a', encoding='utf-8') as f:
        f.write(f"{link}\n")

def extrair_texto_da_noticia(url, headers):
    """Acessa a página interna da notícia e extrai apenas o texto útil, ignorando o rodapé."""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Foca na área principal da postagem para evitar menus laterais
        area_noticia = soup.find('article') or soup.find('div', class_='elementor-widget-theme-post-content') or soup
        
        paragrafos = area_noticia.find_all('p')
        textos_limpos = []
        
        for p in paragrafos:
            texto = p.text.strip()
            
            # Ignora parágrafos totalmente vazios
            if not texto:
                continue
                
            # BARREIRA DE LIMPEZA: Identifica o início do rodapé/banners e corta a extração na mesma hora
            if ("Setor Comercial Norte" in texto or 
                "Horário de Funcionamento" in texto or 
                "O Brasil está conquistando o mundo com o turismo" in texto):
                break 
                
            textos_limpos.append(texto)
        
        texto_completo = "\n\n".join(textos_limpos)
        return texto_completo if texto_completo else "Texto não encontrado."
        
    except Exception as e:
        return f"[Erro ao extrair o texto: {e}]"

def gerar_dump_embratur():
    """Função principal que navega pelas páginas, filtra o ano e salva os dados."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    historico_links = carregar_historico()
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    
    # Caminho do arquivo txt do dia
    caminho_arquivo_dump = os.path.join(PASTA_DESTINO, f"noticias_embratur_{data_hoje}.txt")
    
    noticias_salvas = 0
    pagina_atual = 1
    continuar_buscando = True 

    print(f"Iniciando a extração. Os arquivos serão salvos na pasta: '{PASTA_DESTINO}'")

    with open(caminho_arquivo_dump, 'w', encoding='utf-8') as arquivo:
        arquivo.write(f"=== Dump Diário de Notícias Embratur (2026) - {data_hoje} ===\n\n")
        
        # Loop de navegação pelas páginas
        while continuar_buscando:
            if pagina_atual == 1:
                url = "https://embratur.com.br/nossa-atuacao/noticias/"
            else:
                url = f"https://embratur.com.br/nossa-atuacao/noticias/page/{pagina_atual}/"
                
            print(f"\n--- Lendo Página {pagina_atual} ---")
            
            try:
                response = requests.get(url, headers=headers)
                
                # Se a página não existir (erro 404), chegamos ao fim do site
                if response.status_code != 200:
                    print("Fim das páginas alcançado.")
                    break
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                lista_noticias = soup.find_all('h1', class_='elementor-heading-title')
                
                if not lista_noticias:
                    print("Nenhuma notícia encontrada nesta página.")
                    break
                
                for noticia in lista_noticias:
                    link_tag = noticia.find('a')
                    
                    if link_tag and 'href' in link_tag.attrs:
                        titulo = link_tag.text.strip()
                        link = link_tag['href']
                        
                        # FILTRO 1: Queremos apenas as notícias de 2026
                        if "/2026/" not in link:
                            # O site lista da mais recente para a mais antiga. 
                            # Bateu em 2025 ou 2024? Pode parar a busca geral para economizar tempo.
                            if "/2025/" in link or "/2024/" in link:
                                print(f"Notícia antiga encontrada ({link}). Encerrando a varredura.")
                                continuar_buscando = False 
                                break 
                            continue # Se for um link genérico sem ano, ignora e vai para o próximo
                            
                        # FILTRO 2: Verifica se já baixamos essa notícia antes
                        if link in historico_links:
                            print(f"Ignorado (já no histórico): {titulo[:30]}...")
                            continue
                            
                        print(f"Baixando e limpando texto: {titulo[:50]}...")
                        
                        # Chama a função que entra na matéria e puxa o texto limpo
                        texto = extrair_texto_da_noticia(link, headers)
                        
                        # Escreve o conteúdo no arquivo TXT
                        arquivo.write(f"TÍTULO: {titulo}\n")
                        arquivo.write(f"LINK: {link}\n")
                        arquivo.write(f"TEXTO:\n{texto}\n")
                        arquivo.write("=" * 70 + "\n\n")
                        
                        # Salva o link no histórico para amanhã
                        atualizar_historico(link)
                        noticias_salvas += 1
                
                # Avança para a próxima página de listagem
                pagina_atual += 1
                # Pausa de 1 segundo para não sobrecarregar o servidor do site
                time.sleep(1) 

            except Exception as e:
                print(f"Ocorreu um erro ao processar a página {pagina_atual}: {e}")
                break
                
    # Feedback Final
    if noticias_salvas > 0:
        print(f"\n✅ SUCESSO! Arquivo gerado em: {caminho_arquivo_dump}")
        print(f"📊 Total de {noticias_salvas} novas notícias de 2026 salvas.")
    else:
        print("\nNenhuma notícia nova de 2026 para baixar hoje.")
        # Se nenhuma notícia for salva, exclui o arquivo TXT vazio para manter a pasta organizada
        os.remove(caminho_arquivo_dump)

if __name__ == "__main__":
    gerar_dump_embratur()
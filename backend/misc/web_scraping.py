from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from collections import deque
import time
import requests
import re
import hashlib

START_URL = "https://help.netflix.com/pt"
DOMAIN = urlparse(START_URL).netloc
MAX_DEPTH = 2  # Limitar a profundidade da busca

# Headers para simular um navegador real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en=q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def normalize_url(u):
    p = urlparse(u)
    p = p._replace(fragment="")
    return urlunparse(p)

def is_same_domain(u):
    return urlparse(u).netloc == DOMAIN

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def fetch_simple(url):
    """Tenta obter o conteúdo da página usando requests (sem JavaScript)"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  Erro na requisição simples: {e}")
        return None

def aggressive_clean_text(text):
    """Limpeza agressiva do texto para remover variações e normalizar"""
    if not text:
        return ""
    
    # Remove links no formato [texto](URL) para comparação
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Converte para minúsculas
    text = text.lower()
    
    # Remove espaços em branco extras
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove pontuação exceto pontos finais e vírgulas
    text = re.sub(r'[^\w\s\.\,]', '', text)
    
    # Remove espaços antes de pontuação
    text = re.sub(r'\s+([\.])', r'\1', text)
    
    # Remove acentos
    text = re.sub(r'[áàâãä]', 'a', text)
    text = re.sub(r'[éèêë]', 'e', text)
    text = re.sub(r'[íìîï]', 'i', text)
    text = re.sub(r'[óòôõö]', 'o', text)
    text = re.sub(r'[úùûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    
    return text.strip()

def get_text_fingerprint(text):
    """Gera um fingerprint (hash) do texto para comparação de duplicatas"""
    cleaned = aggressive_clean_text(text)
    if not cleaned:
        return None
    return hashlib.md5(cleaned.encode('utf-8')).hexdigest()

def extract_text_with_links(element):
    """Extrai o texto de um elemento preservando os links no formato [texto](URL)"""
    if not element:
        return ""
    
    result_parts = []
    
    # Se o elemento atual é um link
    if element.name == 'a' and element.get('href'):
        href = element.get('href')
        full_url = urljoin(START_URL, href)
        text = element.get_text(" ", strip=True)
        if text:
            result_parts.append(f"[{text}]({full_url})")
        return "".join(result_parts)
    
    # Se o elemento tem filhos, processar cada filho
    if hasattr(element, 'contents'):
        for child in element.contents:
            if child.name:
                # Se for um elemento HTML, processar recursivamente
                if child.name == 'a' and child.get('href'):
                    href = child.get('href')
                    full_url = urljoin(START_URL, href)
                    text = child.get_text(" ", strip=True)
                    if text:
                        result_parts.append(f"[{text}]({full_url})")
                else:
                    # Para outros elementos, extrair o texto e processar links internos
                    child_text = extract_text_with_links(child)
                    if child_text:
                        result_parts.append(child_text)
            else:
                # Se for um nó de texto, adicionar diretamente
                text = str(child).strip()
                if text:
                    result_parts.append(text)
    
    return "".join(result_parts)

def process_page_simple(html, url):
    """Processa o HTML para extrair conteúdo e links"""
    soup = BeautifulSoup(html, "html.parser")
    
    # pegar título (se existir)
    title_tag = soup.find("h1")
    title = title_tag.get_text().strip() if title_tag else url
    
    # pegar texto (p, li, headings) com links preservados
    page_body = []
    page_fingerprints = set()  # Para evitar duplicatas na mesma página
    
    for tag in soup.find_all(['h2','h3','p','li']):
        # Extrair texto preservando links
        content_with_links = extract_text_with_links(tag)
        if content_with_links:
            # Verificar se é uma duplicata usando fingerprint
            fingerprint = get_text_fingerprint(content_with_links)
            if fingerprint and fingerprint not in page_fingerprints:
                # Ignorar textos muito curtos (provavelmente não são conteúdo relevante)
                if len(content_with_links.strip()) > 10:
                    page_body.append(content_with_links)
                    page_fingerprints.add(fingerprint)
    
    # encontrar links com /node/ no href
    node_links = set()
    for a in soup.find_all("a", href=True):
        href = a['href']
        full = urljoin(url, href)
        full = normalize_url(full)
        
        if is_same_domain(full) and "node/" in full:
            node_links.add(full)
    
    return {
        "title": title,
        "content": "\n".join(page_body),
        "node_links": node_links
    }

def expand_all_elements(driver):
    """Expande todos os elementos clicáveis que possam conter conteúdo oculto"""
    try:
        # Lista de seletores para elementos que podem ser expandidos
        expandable_selectors = [
            ".subcategory-header",  # Cabeçalhos de subcategoria
            ".accordion-header",    # Headers de acordeão
            ".collapsible-header",  # Headers colapsáveis
            ".expand-button",       # Botões de expandir
            ".toggle-button",       # Botões de alternância
            ".faq-question",        # Perguntas de FAQ
            "[aria-expanded='false']",  # Elementos marcados como não expandidos
            ".expandable",          # Elementos com classe expandable
            ".clickable",           # Elementos clicáveis
            "[data-toggle='collapse']",  # Elementos com data-toggle
            ".panel-heading",       # Cabeçalhos de painel
            ".tab-button"           # Botões de aba
        ]
        
        # Tentar expandir elementos para cada seletor
        for selector in expandable_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"  Encontrados {len(elements)} elementos com seletor '{selector}'")
                
                for i, element in enumerate(elements):
                    try:
                        # Verificar se o elemento está visível
                        if element.is_displayed():
                            # Rolar até o elemento
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.3)
                            
                            # Tentar clicar usando JavaScript (mais confiável)
                            driver.execute_script("arguments[0].click();", element)
                            print(f"    Clicado no elemento {i+1}/{len(elements)} do seletor '{selector}'")
                            time.sleep(0.5)  # Esperar o conteúdo expandir
                    except Exception as e:
                        print(f"    Erro ao clicar no elemento {i+1} do seletor '{selector}': {e}")
            except Exception as e:
                print(f"  Erro ao processar seletor '{selector}': {e}")
        
        # Tentar encontrar e clicar em botões "Ver mais" ou "Load more"
        try:
            more_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Ver mais') or contains(text(), 'Load more') or contains(text(), 'Mais')]")
            for button in more_buttons:
                try:
                    if button.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].click();", button)
                        print("  Clicado em botão 'Ver mais'")
                        time.sleep(1)
                except Exception as e:
                    print(f"  Erro ao clicar em botão 'Ver mais': {e}")
        except Exception as e:
            print(f"  Erro ao procurar botões 'Ver mais': {e}")
            
        # Rolar a página para baixo para garantir que tudo seja carregado
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
    except Exception as e:
        print(f"  Erro ao expandir elementos: {e}")

def process_page_with_selenium(driver, url):
    """Processa a página usando Selenium (com JavaScript)"""
    try:
        driver.get(url)
        
        # Esperar o conteúdo inicial carregar
        print("  Aguardando carregamento da página...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Esperar um pouco mais para garantir que o JavaScript seja executado
        time.sleep(2)
        
        # Expandir todos os elementos que possam conter conteúdo oculto
        print("  Expandindo elementos...")
        expand_all_elements(driver)
        
        # Obter o HTML final
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        # pegar título (se existir)
        title_tag = soup.find("h1")
        title = title_tag.get_text().strip() if title_tag else url
        
        # pegar texto (p, li, headings) com links preservados
        page_body = []
        page_fingerprints = set()  # Para evitar duplicatas na mesma página
        
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'div.article-content', 'div.answer', 'div.content']):
            # Ignorar elementos que estejam em menus de navegação ou rodapés
            parent_classes = []
            if tag.parent:
                parent_classes = tag.parent.get('class', [])
            
            if parent_classes and any(cls in ['nav', 'navigation', 'menu', 'footer', 'header', 'sidebar'] for cls in parent_classes):
                continue
                
            # Extrair texto preservando links
            content_with_links = extract_text_with_links(tag)
            if content_with_links:
                # Verificar se é uma duplicata usando fingerprint
                fingerprint = get_text_fingerprint(content_with_links)
                if fingerprint and fingerprint not in page_fingerprints:
                    # Ignorar textos muito curtos (provavelmente não são conteúdo relevante)
                    if len(content_with_links.strip()) > 10:
                        page_body.append(content_with_links)
                        page_fingerprints.add(fingerprint)
        
        # encontrar links com /node/ no href
        node_links = set()
        for a in soup.find_all("a", href=True):
            href = a['href']
            full = urljoin(url, href)
            full = normalize_url(full)
            
            if is_same_domain(full) and "node/" in full:
                node_links.add(full)
        
        return {
            "title": title,
            "content": "\n".join(page_body),
            "node_links": node_links
        }
        
    except Exception as e:
        print(f"  Erro ao processar com Selenium: {e}")
        return None

def main():
    visited = set()
    # Agora a fila armazena tuplas (url, profundidade)
    to_visit = deque([(START_URL, 0)])
    all_text = ""
    node_urls = set()
    global_fingerprints = set()  # Para evitar duplicatas globais
    
    driver = setup_driver()
    
    try:
        while to_visit:
            url, depth = to_visit.popleft()
            if url in visited:
                continue
            
            print(f"\nVisitando: {url} (Profundidade: {depth})")
            visited.add(url)
            
            result = None
            
            # Se for a página inicial, usar Selenium diretamente
            if url == START_URL:
                print("  Usando Selenium para página inicial (requer JavaScript)")
                result = process_page_with_selenium(driver, url)
            else:
                # Para outras páginas, tentar primeiro a abordagem simples
                print("  Tentando abordagem simples (sem JavaScript)...")
                html = fetch_simple(url)
                
                if html:
                    result = process_page_simple(html, url)
                    
                    # Se não encontrou links com node, tentar com Selenium
                    if not result["node_links"]:
                        print("  Nenhum link com node encontrado. Tentando com Selenium...")
                        result = process_page_with_selenium(driver, url)
                else:
                    print("  Falha na abordagem simples. Usando Selenium...")
                    result = process_page_with_selenium(driver, url)
            
            if not result:
                print(f"  Não foi possível processar a página {url}")
                continue
            
            # Processar o conteúdo para evitar duplicatas
            content_lines = result['content'].split('\n')
            unique_lines = []
            
            for line in content_lines:
                # Verificar se é uma duplicata usando fingerprint
                fingerprint = get_text_fingerprint(line)
                if fingerprint and fingerprint not in global_fingerprints:
                    unique_lines.append(line)  # Mantém o texto original com links
                    global_fingerprints.add(fingerprint)
            
            # Adicionar conteúdo ao all_text
            if unique_lines:  # Só adiciona se houver conteúdo único
                all_text += f"\n\n=== {result['title']} ({url}) ===\n\n"
                all_text += "\n".join(unique_lines)
            
            # Processar os links encontrados
            page_node_links = len(result['node_links'])
            print(f"  Estatísticas desta página: {page_node_links} links com node")
            
            # Só adicionar novos links se não atingimos a profundidade máxima
            if depth < MAX_DEPTH:
                for node_url in result['node_links']:
                    node_urls.add(node_url)
                    if node_url not in visited and not any(item[0] == node_url for item in to_visit):
                        print(f"  [NOVO] Emcontrado link com 'node': {node_url} (Profundidade: {depth + 1})")
                        to_visit.append((node_url, depth + 1))
                    else:
                        print(f"  [JÁ VISITADO] Link com 'node': {node_url}")
            else:
                print(f"  Profundidade máxima ({MAX_DEPTH}) atingida. Não adicionando novos links.")
                
    finally:
        driver.quit()
    
    # Salva o conteúdo completo
    with open("faq_complete.txt", "w", encoding="utf-8") as f:
        f.write(all_text)
    
    # Salva apenas as URLs com node encontradas
    with open("node_urls.txt", "w", encoding="utf-8") as f:
        for node_url in sorted(node_urls):
            f.write(f"{node_url}\n")
    
    print(f"\n=== ESTATÍSTICAS FINAIS ===")
    print(f"Total de páginas visitadas: {len(visited)}")
    print(f"Total de URLs únicas com node: {len(node_urls)}")
    print(f"Total de textos únicos extraídos: {len(global_fingerprints)}")
    print(f"Profundidade máxima utilizada: {MAX_DEPTH}")
    print(f"\nFeito! Salvo como faq_complete.txt")
    print(f"URLs com node salvas em node_urls.txt")

if __name__ == "__main__":
    main()
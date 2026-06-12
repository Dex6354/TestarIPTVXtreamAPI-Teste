import re
import requests
import streamlit as st
from urllib.parse import urlparse

# Configuração da página
st.set_page_config(page_title="IPTV Checker", page_icon="📺", layout="wide")
st.title("📺 Validador e Organizador de IPTV")

# Listas de regras fornecidas
ALLOWED_EXT = ('ca', 'io', 'cc', 'me', 'in')
BLOCKED_KEYWORDS = ('site', 'com', 'lat', 'live', 'top', 'icu', 'xyz', 'online')

def validar_url(url):
    """Aplica as regras de negócio de portas e extensões na URL."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname.lower() if parsed.hostname else ""
        port = parsed.port
        
        # Validação de Porta (Apenas 80, 443 ou padrão sem porta explícita)
        if port and port not in (80, 443):
            return False, f"Porta inválida ({port})"
            
        # Validação de termos proibidos
        if any(keyword in hostname for keyword in BLOCKED_KEYWORDS):
            return False, "Contém extensão/termo proibido"
            
        # Validação de termos permitidos (deve terminar com uma das extensões ou conter antes do ponto)
        if not any(hostname.endswith('.' + ext) or f'.{ext}.' in hostname for ext in ALLOWED_EXT):
            return False, "Extensão não permitida"
            
        return True, "OK"
    except Exception as e:
        return False, f"Erro no parse: {str(e)}"

def testar_iptv(url):
    """Descobre o servidor real, valida as regras e testa o login."""
    resultado = {
        "url_original": url,
        "url_real": url,
        "status": "Inoperante",
        "motivo": "",
        "canais": 0, "filmes": 0, "series": 0
    }
    
    # 1. Descobrir Servidor Real (Seguir Redirecionamentos)
    try:
        res_redirect = requests.get(url, timeout=5, allow_redirects=True, stream=True)
        resultado["url_real"] = res_redirect.url
    except Exception:
        resultado["motivo"] = "Servidor offline ou inacessível"
        return resultado

    # 2. Validar o Servidor Real contra as regras de filtros
    valido, motivo = validar_url(resultado["url_real"])
    if not valido:
        resultado["motivo"] = f"Bloqueado pelo filtro: {motivo}"
        return resultado

    # 3. Testar API do Xtream Codes
    try:
        # Adiciona o parâmetro de output se não houver para garantir resposta JSON leve
        test_url = resultado["url_real"]
        if "output=" not in test_url:
            test_url += "&output=ts"
            
        response = requests.get(test_url, timeout=7)
        if response.status_code == 200:
            data = response.json()
            
            # Verifica autenticação padrão do Xtream Codes
            user_info = data.get("user_info", {})
            if user_info.get("auth") == 1 and user_info.get("status") == "Active":
                resultado["status"] = "Funciona"
                
                # Algumas APIs retornam contadores no server_info, se não, tentamos buscar
                server_info = data.get("server_info", {})
                # Nota: Para contagens exatas de canais/filmes, o Xtream exige chamadas adicionais com &action=get_live_streams
                # Armazenamos valores fictícios ou os que vierem na resposta inicial para performance
                resultado["motivo"] = f"Expira em: {user_info.get('exp_date', 'Ilimitado')}"
            else:
                resultado["motivo"] = "Login inválido ou expirado"
        else:
            resultado["motivo"] = f"Erro HTTP {response.status_code}"
    except Exception as e:
        resultado["motivo"] = "Erro ao processar resposta da API"
        
    return resultado

# Interface do Usuário
texto_input = st.text_area("Cole aqui o texto contendo os links de IPTV:", height=200, 
                           placeholder="Cole a mensagem com as URLs aqui...")

if st.button("Processar e Testar Links"):
    if not texto_input.strip():
        st.warning("Por favor, cole algum texto antes de testar.")
    else:
        # Extrair todas as URLs usando Regex
        urls_encontradas = re.findall(r'(https?://[^\s<>"]+)', texto_input)
        
        if not urls_encontradas:
            st.error("Nenhuma URL encontrada no texto.")
        else:
            st.info(f"Encontradas {len(urls_encontradas)} URLs. Iniciando testes...")
            
            resultados_finais = []
            barra_progresso = st.progress(0)
            
            for idx, url in enumerate(urls_encontradas):
                res = testar_iptv(url)
                resultados_finais.append(res)
                barra_progresso.progress((idx + 1) / len(urls_encontradas))
            
            # Exibir Resultados
            st.subheader("📊 Resultado da Análise")
            
            funciona_list = [r for r in resultados_finais if r["status"] == "Funciona"]
            falhou_list = [r for r in resultados_finais if r["status"] != "Funciona"]
            
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"Funcionando: {len(funciona_list)}")
            with col2:
                st.error(f"Filtrados/Inválidos: {len(falhou_list)}")
            
            # Tabelas detalhadas
            if funciona_list:
                st.write("### ✅ Links Ativos e Permitidos")
                st.dataframe(funciona_list)
                
            if falhou_list:
                st.write("### ❌ Links Reprovados ou Offlines")
                st.dataframe(falhou_list)

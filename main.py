import streamlit as st
import re
import requests
from urllib.parse import quote, urlparse, parse_qs
from datetime import datetime
import urllib3

# Desabilitar avisos de segurança
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Xtream API Ultra Fix", layout="centered")

# User-Agent idêntico ao aplicativo Smarters Pro original
HEADERS = {
    "User-Agent": "IPTVSmartersPlayer",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

def parse_urls(message):
    # Regex robusto para pegar a URL completa com parâmetros
    pattern = r"(https?://[^\s\"']+\?[^\s\"']+)"
    found_urls = re.findall(pattern, message)
    
    results = []
    for url in found_urls:
        try:
            p = urlparse(url)
            params = parse_qs(p.query)
            user = params.get('username', [None])[0]
            pwd = params.get('password', [None])[0]
            
            if user and pwd:
                # Remove o arquivo (get.php) e mantém apenas a base do servidor
                path = p.path.lower()
                clean_path = path.replace('get.php', '').replace('player_api.php', '')
                if clean_path.endswith('/'): clean_path = clean_path[:-1]
                
                base_url = f"{p.scheme}://{p.netloc}{clean_path}"
                results.append({"base": base_url, "user": user, "pwd": pwd})
        except: continue
    return results

def test_server(data):
    base, user, pwd = data["base"], data["user"], data["pwd"]
    # Endpoint oficial de login do Xtream Codes
    api_url = f"{base}/player_api.php?username={quote(user)}&password={quote(pwd)}"
    
    result = {"success": False, "msg": "Offline", "data": None, "debug": ""}
    
    try:
        # allow_redirects=True é vital para CDNs
        response = requests.get(api_url, headers=HEADERS, verify=False, timeout=15, allow_redirects=True)
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                if "user_info" in json_data:
                    auth = json_data.get("user_info", {}).get("auth")
                    if auth == 1:
                        result["success"] = True
                        result["data"] = json_data
                    else:
                        result["msg"] = "Usuário ou Senha Inválidos"
                else:
                    result["msg"] = "Servidor não é Xtream API"
            except:
                result["msg"] = "Resposta não é JSON"
                result["debug"] = response.text[:100] # Pega o início da resposta para ver se é erro de firewall
        else:
            result["msg"] = f"Erro HTTP: {response.status_code}"
            
    except requests.exceptions.Timeout:
        result["msg"] = "Tempo esgotado (Timeout)"
    except requests.exceptions.ConnectionError:
        result["msg"] = "Servidor Offline ou URL Incorreta"
    except Exception as e:
        result["msg"] = f"Erro: {str(e)}"
        
    return result

# --- Interface ---
st.title("🔌 Testador Xtream API (Resgate)")

txt = st.text_area("Cole seu link M3U:", placeholder="http://dominio.com/get.php?username=...")

if st.button("🚀 Iniciar Teste"):
    links = parse_urls(txt)
    
    if not links:
        st.error("Nenhuma credencial encontrada na URL.")
    else:
        for link in links:
            with st.status(f"Conectando a {link['base']}...", expanded=True) as status:
                res = test_server(link)
                
                if res["success"]:
                    status.update(label="✅ Conectado!", state="complete")
                    ui = res["data"]["user_info"]
                    
                    with st.container(border=True):
                        st.success(f"**Login realizado com sucesso!**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"👤 **User:** `{link['user']}`")
                            st.write(f"🔑 **Pass:** `{link['pwd']}`")
                            
                            exp = ui.get("exp_date")
                            if exp:
                                date = datetime.fromtimestamp(int(exp)).strftime('%d/%m/%Y') if int(exp) > 0 else "Ilimitado"
                                st.write(f"📅 **Expira:** `{date}`")
                        
                        with col2:
                            st.write(f"👥 **Conexões:** `{ui.get('active_cons')}/{ui.get('max_connections')}`")
                            st.write(f"📍 **Status:** `{ui.get('status')}`")
                else:
                    status.update(label=f"❌ Falha: {res['msg']}", state="error")
                    st.error(f"Erro no servidor: {res['msg']}")
                    if res["debug"]:
                        st.info(f"Resposta do servidor: {res['debug']}")

st.divider()
st.caption("Dica: Se persistir o erro, tente usar a URL sem o 'cdn.' no início, caso o servidor tenha um endereço alternativo.")

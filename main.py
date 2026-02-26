import streamlit as st
import re
import requests
from urllib.parse import quote, urlparse, parse_qs
from datetime import datetime
import urllib3

# Desabilitar avisos de segurança
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Xtream API - Fix 406 Final", layout="centered")

# Simulação profunda de um dispositivo Android (Smarters Pro oficial)
HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; SM-G981B Build/QP1A.190711.020)",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
}

def parse_urls(message):
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
                # Extraímos a base e também criamos uma versão sem o "cdn."
                netloc = p.netloc
                base_original = f"{p.scheme}://{netloc}"
                
                alt_netloc = netloc.replace('cdn.', '')
                base_alt = f"{p.scheme}://{alt_netloc}"
                
                results.append({"base": base_original, "user": user, "pwd": pwd})
                if base_original != base_alt:
                    results.append({"base": base_alt, "user": user, "pwd": pwd, "is_alt": True})
        except: continue
    return results

def test_server(data):
    base, user, pwd = data["base"], data["user"], data["pwd"]
    # Forçamos o endpoint direto de autenticação
    api_url = f"{base}/player_api.php?username={quote(user)}&password={quote(pwd)}"
    
    try:
        # Aumentamos o timeout para dar tempo do firewall processar
        response = requests.get(api_url, headers=HEADERS, verify=False, timeout=12)
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                if "user_info" in json_data:
                    return {"success": True, "data": json_data}
            except:
                pass
        return {"success": False, "status": response.status_code}
    except Exception as e:
        return {"success": False, "status": str(e)}

# --- Interface ---
st.title("🔌 Desbloqueio de Conexão IPTV")

url_input = st.text_area("Insira sua URL completa:", "http://cdn.club8.ca/get.php?username=concmus03&password=3a3b3c3d&type=m3u_plus")

if st.button("🚀 Forçar Acesso"):
    links = parse_urls(url_input)
    
    if not links:
        st.error("Nenhuma URL detectada.")
    else:
        for link in links:
            label = "🛡️ Original" if "is_alt" not in link else "🔓 Alternativa (Sem CDN)"
            with st.spinner(f"Testando rota {label}: {link['base']}..."):
                res = test_server(link)
                
                if res["success"]:
                    ui = res["data"]["user_info"]
                    st.balloons()
                    with st.container(border=True):
                        st.success(f"✅ Sucesso via: {link['base']}")
                        st.write(f"👤 **Usuário:** `{link['user']}`")
                        exp = ui.get("exp_date")
                        date = datetime.fromtimestamp(int(exp)).strftime('%d/%m/%Y') if (exp and int(exp) != 0) else "Ilimitado"
                        st.write(f"📅 **Vencimento:** `{date}`")
                        st.write(f"👥 **Conexões:** `{ui.get('active_cons')}/{ui.get('max_connections')}`")
                    break # Para de testar se um funcionar
                else:
                    if "is_alt" in link:
                        st.error(f"❌ Rota {label} falhou (Erro {res['status']})")

### 🛠️ Por que este é o último recurso?

O diagrama abaixo ilustra como o firewall do servidor IPTV interpreta sua requisição:



### Se ainda assim der 406:
Isso prova que o servidor `club8.ca` está configurado para **rejeitar qualquer IP que pertença a Data Centers** (como Google, Amazon, Microsoft ou onde o Streamlit estiver hospedado).

**O que fazer agora?**
1. **Teste em 4G/5G:** Abra o seu app no celular usando os dados móveis. Se funcionar no celular e não no script, o bloqueio é no IP do servidor do script.
2. **Execute Localmente:** Instale o Python no seu PC, salve o código e rode `pip install streamlit requests` e depois `streamlit run seu_arquivo.py`. **No seu IP residencial, o erro 406 dificilmente acontecerá.**

Gostaria que eu adaptasse o código para gerar um **arquivo .py pronto para você baixar** e rodar no seu computador?

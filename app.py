import streamlit as st
import streamlit.components.v1 as components
import os
from web3 import Web3
from eth_account.messages import encode_defunct

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="NFT Gated App",
    page_icon="🔐",
    layout="centered"
)

# --- CONFIGURACIÓN DEL TOKEN GATING ---
NFT_CONTRACT_ADDRESS = "0xF4820467171695F4d2760614C77503147A9CB1E8"
CHAIN = "arbitrum"
ARBITRUM_RPC = "https://arb1.arbitrum.io/rpc"

# URL del servidor FastAPI
FASTAPI_SERVER_URL = "https://privy-moralis-streamlit-production.up.railway.app"

# --- INTERFAZ DE USUARIO ---
st.title("🔐 Acceso Exclusivo para Holders")
st.write("Conecta tu billetera para verificar que posees el NFT requerido y accede al contenido exclusivo.")
st.divider()

# --- LÓGICA DE AUTENTICACIÓN ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'user_wallet' not in st.session_state:
    st.session_state.user_wallet = None

if 'user_nfts' not in st.session_state:
    st.session_state.user_nfts = None

if 'auth_data' not in st.session_state:
    st.session_state.auth_data = None

# --- FUNCIÓN PARA VERIFICAR NFT CON WEB3 ---
def verify_nft_ownership(wallet_address):
    """
    Verifica si una dirección de billetera posee el NFT requerido en Arbitrum.
    """
    try:
        w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC))
        if not w3.is_connected():
            st.error("❌ No se pudo conectar a la red Arbitrum")
            return False, None
        
        ERC721_ABI = [
            {
                "constant": True,
                "inputs": [{"name": "owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(NFT_CONTRACT_ADDRESS),
            abi=ERC721_ABI
        )
        
        balance = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        
        if balance > 0:
            return True, {"balance": balance, "contract": NFT_CONTRACT_ADDRESS}
        else:
            return False, None
            
    except Exception as e:
        st.error(f"❌ Error al verificar NFT: {e}")
        return False, None

# --- FUNCIÓN PARA VERIFICAR FIRMA ---
def verify_signature(wallet_address, message, signature):
    """
    Verifica que la firma fue creada por la billetera especificada.
    """
    try:
        message_hash = encode_defunct(text=message)
        recovered_address = Web3.eth.Account.recover_message(message_hash, signature=signature)
        return recovered_address.lower() == wallet_address.lower()
    except Exception as e:
        st.error(f"❌ Error al verificar firma: {e}")
        return False

# Si el usuario está autenticado, muestra el contenido
if st.session_state.authenticated:
    st.success("✅ ¡Autenticación y verificación completadas! Bienvenido.")
    st.balloons()
    
    st.info(f"Billetera conectada: `{st.session_state.user_wallet}`")
    
    if st.session_state.user_nfts:
        st.subheader("📜 Información del NFT")
        st.write(f"**Balance:** {st.session_state.user_nfts.get('balance', 0)} NFT(s)")
        st.write(f"**Contrato:** `{st.session_state.user_nfts.get('contract', 'N/A')}`")
    
    st.header("🎁 Contenido Exclusivo")
    st.write("""
    Este es el contenido que solo pueden ver los holders del NFT.
    
    Aquí puedes poner:
    - Documentos privados
    - Videos exclusivos
    - Acceso a herramientas especiales
    - Información confidencial
    - Lo que necesites proteger
    """)
    
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.authenticated = False
        st.session_state.user_wallet = None
        st.session_state.user_nfts = None
        st.rerun()

else:
    st.subheader("Paso 1: Conecta tu Billetera")
    st.caption("Haz clic en el botón para abrir la ventana de autenticación.")
    
    # Botón para abrir la ventana de autenticación
    st.link_button("🔗 Conectar Billetera", f"{FASTAPI_SERVER_URL}")
    
    st.info("Después de autenticarte, vuelve a esta página y refresca.")

    # Componente que escucha postMessage desde la ventana emergente
    components.html("""
    <script>
        // Escuchar mensajes desde la ventana emergente
        window.addEventListener('message', function(event) {
            // Verificar que el mensaje sea del tipo esperado
            if (event.data && event.data.type === 'web3_auth_complete') {
                // Guardar los datos en sessionStorage para que Streamlit los lea
                sessionStorage.setItem('web3_auth_data', JSON.stringify(event.data.data));
                
                // Notificar a Streamlit que hay nuevos datos
                // Esto se hace enviando un evento personalizado
                window.dispatchEvent(new CustomEvent('web3_auth_received', {
                    detail: event.data.data
                }));
                
                console.log('Datos de autenticación recibidos:', event.data.data);
            }
        });
    </script>
    """, height=0)

    # Leer datos de sessionStorage usando JavaScript
    auth_data_html = components.html("""
    <script>
        // Intentar leer los datos de sessionStorage
        const authData = sessionStorage.getItem('web3_auth_data');
        if (authData) {
            // Enviar a Streamlit
            window.parent.postMessage(
                {
                    isStreamlitMessage: true,
                    type: "streamlit:setComponentValue",
                    data: JSON.parse(authData)
                },
                "*"
            );
            
            // Limpiar
            sessionStorage.removeItem('web3_auth_data');
        }
    </script>
    """, height=0)

    # Procesar datos recibidos
    if auth_data_html and isinstance(auth_data_html, dict):
        wallet_address = auth_data_html.get('wallet')
        signature = auth_data_html.get('signature')
        message = auth_data_html.get('message')
        
        if wallet_address and signature and message:
            with st.spinner("🔍 Verificando firma y buscando tu NFT..."):
                if verify_signature(wallet_address, message, signature):
                    st.success(f"✅ Firma verificada. Billetera: `{wallet_address}`")
                    has_nft, nfts = verify_nft_ownership(wallet_address)
                    if has_nft:
                        st.session_state.authenticated = True
                        st.session_state.user_wallet = wallet_address
                        st.session_state.user_nfts = nfts
                        st.success("✅ ¡NFT verificado! Acceso concedido.")
                        st.rerun()
                    else:
                        st.warning("❌ Acceso Denegado")
                        st.error("La billetera conectada no posee el NFT requerido en Arbitrum.")
                        st.info(f"Contrato requerido: `{NFT_CONTRACT_ADDRESS}`")
                        st.info(f"Red: Arbitrum")
                else:
                    st.error("❌ La firma no es válida")

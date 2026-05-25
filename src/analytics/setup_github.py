"""
🔧 Configuración de GitHub Models para el Chatbot
================================================

GitHub Models te permite usar modelos de IA como GPT-4o usando tu cuenta de GitHub.
Es ideal si ya tienes GitHub Copilot.
"""
import os
from pathlib import Path


def check_github_token():
    """Verifica si el token de GitHub está configurado."""
    from dotenv import load_dotenv
    
    # Cargar .env
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    token = os.getenv("GITHUB_TOKEN")
    
    print("=" * 60)
    print("🔧  GITHUB MODELS CONFIGURATION")
    print("=" * 60)
    
    if token and token != "your_github_token_here":
        print("\n✅ GITHUB_TOKEN is configured correctly!")
        print(f"   Token: {token[:10]}...{token[-4:]}")
        
        # Intentar una llamada de prueba
        print("\n🧪 Testing GitHub Models connection...")
        try:
            from openai import OpenAI
            
            client = OpenAI(
                base_url="https://models.inference.ai.azure.com",
                api_key=token
            )
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Modelo más ligero para prueba
                messages=[{"role": "user", "content": "Say 'Hello' in English"}],
                max_tokens=10
            )
            
            print(f"   ✅ ¡Sucessfull connection!")
            print(f"   Answer: {response.choices[0].message.content}")
            print("\n🎉 ¡Everything ready! Can use chatbot with:")
            print("   python -m src.analytics.chatbot --provider github")
            return True
            
        except Exception as e:
            print(f"   ❌ Connection error: {e}")
            print("\n   Root causes:")
            print("   1. Invalid or expired token")
            print("   2. You don't have acces to GitHub Models")
            print("   3. Network issues")
            return False
    else:
        print("\n❌ GITHUB_TOKEN is not configure")
        print_setup_instructions()
        return False


def print_setup_instructions():
    """Muestra instrucciones para configurar GitHub Models."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           CÓMO CONFIGURAR GITHUB MODELS                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  OPCIÓN 1: Si tienes GitHub Copilot                          ║
║  ─────────────────────────────────────                       ║
║  1. Ve a: https://github.com/settings/tokens                 ║
║  2. Click en "Generate new token" → "Generate new token      ║
║     (classic)"                                               ║
║  3. Dale un nombre (ej: "DataEngineer Chatbot")              ║
║  4. Selecciona los permisos:                                 ║
║     ✓ read:user                                              ║
║  5. Click "Generate token"                                   ║
║  6. ¡COPIA EL TOKEN! (solo lo verás una vez)                 ║
║                                                              ║
║  OPCIÓN 2: GitHub Models (Preview)                           ║
║  ─────────────────────────────────────                       ║
║  1. Ve a: https://github.com/marketplace/models              ║
║  2. Solicita acceso si no lo tienes                          ║
║  3. Una vez aprobado, genera un token como arriba            ║
║                                                              ║
║  CONFIGURAR EL TOKEN:                                        ║
║  ─────────────────────────────────────                       ║
║  Edita el archivo .env y reemplaza:                          ║
║                                                              ║
║    GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx                     ║
║                                                              ║
║  O temporalmente en PowerShell:                              ║
║                                                              ║
║    $env:GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

📖 Documentación: https://docs.github.com/en/github-models

🔄 Una vez configurado, ejecuta este script de nuevo para verificar:
   python -m src.analytics.setup_github
""")


def list_available_models():
    """Lista los modelos disponibles en GitHub Models."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              MODELOS DISPONIBLES EN GITHUB MODELS            ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🤖 OpenAI Models:                                           ║
║     • gpt-4o           - Más capaz, mejor para análisis      ║
║     • gpt-4o-mini      - Rápido y económico                  ║
║     • o1-preview       - Razonamiento avanzado               ║
║     • o1-mini          - Razonamiento rápido                 ║
║                                                              ║
║  🦙 Meta Llama:                                              ║
║     • Meta-Llama-3.1-405B-Instruct                           ║
║     • Meta-Llama-3.1-70B-Instruct                            ║
║     • Meta-Llama-3.1-8B-Instruct                             ║
║                                                              ║
║  💎 Mistral:                                                 ║
║     • Mistral-large-2407                                     ║
║     • Mistral-Nemo-2407                                      ║
║                                                              ║
║  🔬 Microsoft Phi:                                           ║
║     • Phi-3.5-MoE-instruct                                   ║
║     • Phi-3.5-mini-instruct                                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

💡 Chatbot use 'gpt-4o' by default for better quality.
""")


if __name__ == "__main__":
    import sys
    
    if "--models" in sys.argv:
        list_available_models()
    else:
        check_github_token()
        print()
        list_available_models()
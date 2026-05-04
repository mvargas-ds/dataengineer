"""
🚀 Guía de Configuración del Chatbot con Claude
================================================

Este script te muestra cómo configurar y usar el chatbot de análisis
de datos con Claude (Anthropic) para consultas avanzadas con IA.

PASOS PARA CONFIGURAR:
1. Obtén tu API key de Anthropic en: https://console.anthropic.com/
2. Configura la variable de entorno (elige una opción):

   OPCIÓN A - Archivo .env (recomendado):
   Edita el archivo .env y agrega:
   ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx

   OPCIÓN B - Variable de entorno temporal (PowerShell):
   $env:ANTHROPIC_API_KEY = "sk-ant-api03-xxxxxxxxxxxxx"

   OPCIÓN C - Variable de entorno permanente (Windows):
   [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-api03-xxx", "User")

3. Ejecuta el chatbot:
   python -m src.analytics.chatbot --provider anthropic
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_anthropic_setup():
    """Verifica si la configuración de Anthropic está correcta."""
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE CONFIGURACIÓN DE CLAUDE")
    print("=" * 60)
    
    if not api_key:
        print("\n❌ ANTHROPIC_API_KEY no está configurada")
        print("\nPasos para configurar:")
        print("1. Ve a: https://console.anthropic.com/")
        print("2. Crea una API key")
        print("3. Edita el archivo .env y agrega:")
        print("   ANTHROPIC_API_KEY=tu-api-key-aqui")
        print("\nO configúrala temporalmente en PowerShell:")
        print('   $env:ANTHROPIC_API_KEY = "tu-api-key-aqui"')
        return False
    
    # Verificar que la key tiene el formato correcto
    if not api_key.startswith("sk-ant-"):
        print(f"\n⚠️ La API key no parece tener el formato correcto")
        print(f"   Formato esperado: sk-ant-api03-...")
        print(f"   Tu key empieza con: {api_key[:10]}...")
        return False
    
    print(f"\n✅ ANTHROPIC_API_KEY configurada")
    print(f"   Key: {api_key[:15]}...{api_key[-4:]}")
    
    # Intentar una conexión de prueba
    print("\n🔄 Probando conexión con Anthropic...")
    try:
        import anthropic
        client = anthropic.Anthropic()
        
        # Hacer una pequeña prueba
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": "Di 'Hola, estoy funcionando correctamente' exactamente."}]
        )
        
        print(f"✅ Conexión exitosa!")
        print(f"   Respuesta: {response.content[0].text}")
        return True
        
    except anthropic.AuthenticationError:
        print("❌ Error de autenticación - API key inválida")
        return False
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False


def demo_chat():
    """Ejecuta una demostración del chatbot con Claude."""
    from src.analytics.chatbot import DataChatbot
    
    print("\n" + "=" * 60)
    print("🤖 DEMOSTRACIÓN DEL CHATBOT CON CLAUDE")
    print("=" * 60)
    
    # Crear chatbot con Claude
    chatbot = DataChatbot(llm_provider="anthropic")
    
    # Preguntas de demostración
    demo_questions = [
        "¿Cuáles son las 5 provincias con mayor tasa de despoblamiento?",
        "¿Cómo ha evolucionado la población total de España desde 2015?"
    ]
    
    for i, question in enumerate(demo_questions, 1):
        print(f"\n{'='*60}")
        print(f"📝 Pregunta {i}: {question}")
        print("="*60)
        
        response = chatbot.chat(question)
        print(response)
        
        if i < len(demo_questions):
            input("\n[Presiona Enter para la siguiente pregunta...]")
    
    chatbot.close()
    print("\n✅ Demostración completada!")


def main():
    """Punto de entrada principal."""
    print("\n🤖 CONFIGURACIÓN DEL CHATBOT CON CLAUDE (ANTHROPIC)")
    print("=" * 60)
    
    # Verificar configuración
    if check_anthropic_setup():
        print("\n" + "-" * 60)
        response = input("\n¿Quieres ejecutar una demostración? (s/n): ").strip().lower()
        if response in ['s', 'si', 'sí', 'y', 'yes']:
            demo_chat()
        else:
            print("\n💡 Para usar el chatbot ejecuta:")
            print("   python -m src.analytics.chatbot --provider anthropic")
    else:
        print("\n" + "-" * 60)
        print("\n💡 Una vez configurada la API key, ejecuta este script nuevamente")
        print("   o usa directamente:")
        print("   python -m src.analytics.chatbot --provider anthropic")


if __name__ == "__main__":
    main()


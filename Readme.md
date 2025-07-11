# Aventura Conversacional

Esta aplicaci\u00f3n genera una historia interactiva al estilo de las viejas aventuras de texto, usando Azure OpenAI como motor narrativo. El jugador controla su personaje en un mundo ficticio y toma decisiones a trav\u00e9s de la interfaz.

Al iniciar, la ventana pregunta de forma inmersiva el nombre y el g\u00e9nero del jugador. Con esa informaci\u00f3n, la narraci\u00f3n se personaliza usando pronombres y el nombre elegido.

El juego mantiene un inventario din\u00e1mico y un sistema de salud visible en pantalla (20/20 al comenzar). Al recoger o soltar objetos, la interfaz se actualiza en tiempo real.
El combate se resuelve por turnos con dados d10 al estilo *Vampire: The Masquerade*. Las tiradas reales y el daño se muestran en colores diferentes y la salud solo cambia en el indicador de vida.

## Uso

1. Cre\u00e1 un archivo `.env` con las variables `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` y `AZURE_OPENAI_API_VERSION`.
2. Ejecut\u00e1 `python setup_keys.py` para generar `.env.secure` y `.key`.
3. Inici\u00e1 el juego con `python ai_adventure.py`.

La interfaz est\u00e1 hecha con PyQt5 y requiere conexi\u00f3n a internet para comunicarse con OpenAI.

## Descarga de builds portables

Cada commit en `main` genera un zip `ai_adventure_portable.zip` en [Releases](../../releases). Descargalo, descompr\u00edmelo y ejecut\u00e1 `ai_adventure.exe` en Windows.

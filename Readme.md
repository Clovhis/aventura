# Aventura Conversacional

Esta aplicaci\u00f3n genera una historia interactiva al estilo de las viejas aventuras de texto, pero usando Azure OpenAI para narrar. El jugador despierta en las v\u00edas del Subte B, estaci\u00f3n Florida, y debe escribir qu\u00e9 hace para continuar. La historia se desarrolla en un Buenos Aires actual plagado de vampiros, con tono similar a *Vampire: The Masquerade*.

## Uso

1. Cre\u00e1 un archivo `.env` con las variables `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` y `AZURE_OPENAI_API_VERSION`.
2. Ejecut\u00e1 `python setup_keys.py` para generar `.env.secure` y `.key`.
3. Inici\u00e1 el juego con `python ai_adventure.py`.

La interfaz est\u00e1 hecha con PyQt5 y requiere conexi\u00f3n a internet para comunicarse con OpenAI.

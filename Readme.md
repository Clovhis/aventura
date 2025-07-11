# Aventura Conversacional

Esta aplicación genera una historia interactiva al estilo de las viejas aventuras de texto, usando Azure OpenAI como motor narrativo. La trama se desarrolla en Buenos Aires y se narra completamente en castellano argento.

Al iniciar, la ventana pregunta el nombre, el género y la edad del jugador. Con esos datos la narración se personaliza por completo.

La interfaz muestra un inventario dinámico con tooltips detallados de cada ítem (tipo, daño, material, estado, etc.), un indicador de salud y otro de nivel. El jugador arranca con 20/20 de vida y nivel 1.
El combate se resuelve por turnos con dados d10 al estilo *Vampire: The Masquerade*. Las tiradas y el daño aparecen en colores aparte y la salud solo cambia en su indicador.

## Uso

1. Cre\u00e1 un archivo `.env` con las variables `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` y `AZURE_OPENAI_API_VERSION`.
2. Ejecut\u00e1 `python setup_keys.py` para generar `.env.secure` y `.key`.
3. Inici\u00e1 el juego con `python ai_adventure.py`.

La interfaz est\u00e1 hecha con PyQt5 y requiere conexi\u00f3n a internet para comunicarse con OpenAI.

## Descarga de builds portables

Cada commit en `main` genera un zip `ai_adventure_portable.zip` en [Releases](../../releases). Descargalo, descompr\u00edmelo y ejecut\u00e1 `ai_adventure.exe` en Windows.

## Mejoras recientes

- Ahora podés mencionar texto extra al tirar objetos ("al piso", "con fuerza", etc.) y el juego reconocerá correctamente cuál deseás soltar.
- El tooltip del inventario se expande automáticamente para mostrar todas las propiedades del ítem.


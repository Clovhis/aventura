import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet
from PyQt5 import QtWidgets, QtCore
from openai import AzureOpenAI


SYSTEM_PROMPT = """
Act\u00faa como un Dungeon Master experto en el universo de Vampire: The Masquerade. Vas a dirigir una aventura conversacional guiada y contenida para un solo jugador. El jugador despierta en la estaci\u00f3n Florida del subte B de Buenos Aires, a la medianoche, reci\u00e9n convertido en vampiro, sin recuerdos recientes.

Tu narrativa debe ser inmersiva, oscura y atmosf\u00e9rica. Describe los sonidos, luces, olores y emociones. El jugador podr\u00e1 tomar decisiones dentro de un marco narrativo, pero no puede actuar fuera de las reglas del mundo. Si intenta hacerlo, deber\u00e1s redirigirlo l\u00f3gicamente usando consecuencias internas (La Mascarada, la sed, cazadores, la Camarilla, etc.).

Mant\u00e9n el control narrativo como un Dungeon Master tradicional, guiando la historia hacia adelante por eventos, pistas y encuentros. No permitas decisiones que desv\u00eden al jugador del foco de la historia.

\ud83c\udfb2 Sistema de combate:
Cuando haya combates, realiza tiradas de dados estilo Vampire: The Masquerade (d10).

Usa la l\u00f3gica de atributos y habilidades b\u00e1sicas: Fuerza, Destreza, Pelea, Defensa, etc.

Describe los resultados num\u00e9ricos claramente al jugador: qu\u00e9 tiradas obtuvo, qu\u00e9 dificultad hab\u00eda, cu\u00e1ntos \u00e9xitos logr\u00f3.

Muestra el estado del jugador despu\u00e9s del combate: vida restante, da\u00f1o recibido, defensa usada, da\u00f1o causado.

Ejemplo de formato de combate visual:

\ud83e\udddb\u200d\u2642\ufe0f COMBATE \ud83e\udddb\u200d\u2642\ufe0f
Tu ataque: Espada
Tiro: 3 dados (Fuerza 2 + Pelea 1) \u2192 [7, 9, 3]
\u00c9xitos: 2 (dificultad 6)
Da\u00f1o causado: 2 puntos

Enemigo ataca...
Tiro enemigo: 4 dados \u2192 [4, 6, 2, 8]
\u00c9xitos: 2 \u2192 Recibes 1 punto de da\u00f1o (Defensa 1)

\u2764\ufe0f Vida actual: 4/5
\ud83d\udee1\ufe0f Armadura: Chaqueta de cuero (absorbe 1 da\u00f1o superficial)

\ud83c\udf92 Inventario y loot:
Lleva un registro persistente del inventario del jugador.

Cuando encuentre loot (armas, objetos, armaduras), pres\u00e9ntalo como una elecci\u00f3n.

Usa tecnolog\u00eda y est\u00e9tica del a\u00f1o 2025: armas modernas, accesorios t\u00e1cticos, objetos tecnol\u00f3gicos con est\u00e9tica g\u00f3tica.

Muestra el inventario en pantalla cuando sea necesario.

Ejemplo:

\ud83c\udf92 Inventario actual:
- Espada corta (da\u00f1o base 2)
- Chaqueta reforzada (absorbe 1 da\u00f1o)
- Tel\u00e9fono da\u00f1ado
- 100 ARS

Aseg\u00farate de que el jugador pueda usar los objetos en escenas futuras. Describe cu\u00e1ndo los usa, c\u00f3mo impactan en combate, o en el mundo.

\u26a0\ufe0f Reglas clave del mundo:
No puede exponerse al sol
Debe ocultar su naturaleza vamp\u00edrica (Mascarada)
Necesita alimentarse regularmente
Puede enfrentar consecuencias si viola normas vamp\u00edricas o humanas
Existen clanes, disciplinas, enemigos y pol\u00edtica dentro del mundo

Responde siempre en castellano rioplatense.

Inicia ahora la aventura. Escena 1: El jugador despierta en la estaci\u00f3n Florida del subte B, solo, a medianoche, con una sed antinatural, rodeado de silencio y luces parpadeantes. Describe con detalle la escena e invita al jugador a tomar su primera decisi\u00f3n.
"""


def _resource_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent
    return base / name


def _load_secure_env(secure_path: Path = Path(".env.secure"), key_path: Path = Path(".key")) -> None:
    secure_path = _resource_path(secure_path.name)
    key_path = _resource_path(key_path.name)
    if not secure_path.exists() or not key_path.exists():
        raise FileNotFoundError("Archivos de credenciales no encontrados")
    key = key_path.read_bytes()
    fernet = Fernet(key)
    decrypted = fernet.decrypt(secure_path.read_bytes())
    for line in decrypted.decode().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()


def _create_ai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
    )


class AdventureWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aventura Vampiresca")
        self.resize(800, 600)
        self.inventory = [
            "Cuchillo",
            "Linterna",
            "Bolsa de sangre llena",
            "Primeros Auxilios",
        ]
        self.setup_ui()
        _load_secure_env()
        self.client = _create_ai_client()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.start_adventure()

    def setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QHBoxLayout(central)
        convo_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(convo_layout, 3)
        inv_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(inv_layout, 1)

        self.setStyleSheet(
            """
            QWidget { background-color: #1a001a; color: #f0f0f0; }
            QTextEdit {
                background-color: #2b0a2b;
                color: #f0f0f0;
                font-size: 14px;
                font-family: Consolas, monospace;
            }
            QLineEdit {
                background-color: #2b0a2b;
                color: #ff5555;
                font-family: Consolas, monospace;
            }
            QPushButton {
                background-color: #4c0d4c;
                color: #f0f0f0;
                border: 1px solid #660f66;
                padding: 5px;
                font-family: Consolas, monospace;
            }
            QPushButton:hover { background-color: #660f66; }
            QListWidget {
                background-color: #2b0a2b;
                color: #f0f0f0;
                font-family: Consolas, monospace;
            }
            QGroupBox {
                border: 1px solid #660f66;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
            """
        )

        self.text_view = QtWidgets.QTextEdit(readOnly=True)
        convo_layout.addWidget(self.text_view)

        self.input = QtWidgets.QLineEdit()
        self.input.returnPressed.connect(self.send_message)
        send_btn = QtWidgets.QPushButton("Enviar")
        send_btn.clicked.connect(self.send_message)
        h = QtWidgets.QHBoxLayout()
        h.addWidget(self.input)
        h.addWidget(send_btn)
        convo_layout.addLayout(h)

        inv_group = QtWidgets.QGroupBox("Inventario")
        inv_group.setAlignment(QtCore.Qt.AlignHCenter)
        inv_vbox = QtWidgets.QVBoxLayout(inv_group)
        self.inv_list = QtWidgets.QListWidget()
        inv_vbox.addWidget(self.inv_list)
        inv_layout.addWidget(inv_group)
        inv_group.setMaximumWidth(200)
        self.update_inventory_display()

    def append_text(self, text: str) -> None:
        self.text_view.append(text)
        self.text_view.verticalScrollBar().setValue(self.text_view.verticalScrollBar().maximum())

    def update_inventory_display(self) -> None:
        self.inv_list.clear()
        for item in self.inventory:
            self.inv_list.addItem(item)

    def add_item(self, item: str) -> None:
        self.inventory.append(item)
        self.update_inventory_display()
        self.append_text(f'<i>Obtienes "{item}"</i>')

    def remove_item(self, item: str) -> None:
        if item in self.inventory:
            self.inventory.remove(item)
            self.update_inventory_display()
            self.append_text(f'<i>"{item}" ha sido removido del inventario</i>')

    def update_item(self, old: str, new: str) -> None:
        if old in self.inventory:
            idx = self.inventory.index(old)
            self.inventory[idx] = new
            self.update_inventory_display()
            self.append_text(f'<i>{old} ahora es "{new}"</i>')

    def start_adventure(self) -> None:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.messages + [{"role": "user", "content": "Iniciemos"}],
        )
        text = response.choices[0].message.content.strip()
        self.messages.append({"role": "assistant", "content": text})
        self.append_text(text)

    def send_message(self) -> None:
        user_text = self.input.text().strip()
        if not user_text:
            return
        lower = user_text.lower()
        if lower.startswith("/agregar "):
            item = user_text[9:].strip()
            if item:
                self.add_item(item)
            self.input.clear()
            return
        if lower.startswith("/tirar "):
            item = user_text[7:].strip()
            if item:
                self.remove_item(item)
            self.input.clear()
            return
        if lower.startswith("/usar "):
            rest = user_text[6:].strip()
            if "->" in rest:
                old, new = [p.strip() for p in rest.split("->", 1)]
                if old and new:
                    self.update_item(old, new)
            else:
                if rest:
                    self.remove_item(rest)
            self.input.clear()
            return
        self.append_text(f'<span style="color:#ff5555;">&gt; {user_text}</span>')
        self.messages.append({"role": "user", "content": user_text})
        self.input.clear()
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.messages,
            )
            text = response.choices[0].message.content.strip()
            self.messages.append({"role": "assistant", "content": text})
            self.append_text(text)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = AdventureWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

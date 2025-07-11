import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet
from PyQt5 import QtWidgets, QtCore
import re
from openai import AzureOpenAI


SYSTEM_PROMPT = """
Actúa como un Dungeon Master experto en el universo de Vampire: The Masquerade. Vas a dirigir una aventura conversacional guiada y contenida para un solo jugador. El jugador despierta en la estación Florida del subte B de Buenos Aires, a la medianoche, recién convertido en vampiro, sin recuerdos recientes.

Tu narrativa debe ser inmersiva, oscura y atmosférica. Describe los sonidos, luces, olores y emociones. El jugador podrá tomar decisiones dentro de un marco narrativo, pero no puede actuar fuera de las reglas del mundo. Si intenta hacerlo, deberás redirigirlo lógicamente usando consecuencias internas (La Mascarada, la sed, cazadores, la Camarilla, etc.).

Mantén el control narrativo como un Dungeon Master tradicional, guiando la historia hacia adelante por eventos, pistas y encuentros. No permitas decisiones que desvíen al jugador del foco de la historia.

Sistema de combate:
Cuando haya combates, realiza tiradas de dados estilo Vampire: The Masquerade (d10).

Usa la lógica de atributos y habilidades básicas: Fuerza, Destreza, Pelea, Defensa, etc.

Describe los resultados numéricos claramente al jugador: qué tiradas obtuvo, qué dificultad había, cuántos éxitos logró.

Muestra el estado del jugador después del combate: vida restante, daño recibido, defensa usada, daño causado.

Ejemplo de formato de combate visual:

COMBATE
Tu ataque: Espada
Tiro: 3 dados (Fuerza 2 + Pelea 1) → [7, 9, 3]
Éxitos: 2 (dificultad 6)
Daño causado: 2 puntos

Enemigo ataca...
Tiro enemigo: 4 dados → [4, 6, 2, 8]
Éxitos: 2 → Recibes 1 punto de daño (Defensa 1)

Vida actual: 4/5
Armadura: Chaqueta de cuero (absorbe 1 daño superficial)

Inventario y loot:
Lleva un registro persistente del inventario del jugador.

Cuando encuentre loot (armas, objetos, armaduras), preséntalo como una elección.

Usa tecnología y estética del año 2025: armas modernas, accesorios tácticos, objetos tecnológicos con estética gótica.

Muestra el inventario en pantalla cuando sea necesario.

Ejemplo:

Inventario actual:
- Espada corta (daño base 2)
- Chaqueta reforzada (absorbe 1 daño)
- Teléfono dañado
- 100 ARS

Asegúrate de que el jugador pueda usar los objetos en escenas futuras. Describe cuándo los usa, cómo impactan en combate, o en el mundo.

Reglas clave del mundo:
No puede exponerse al sol
Debe ocultar su naturaleza vampírica (Mascarada)
Necesita alimentarse regularmente
Puede enfrentar consecuencias si viola normas vampíricas o humanas
Existen clanes, disciplinas, enemigos y política dentro del mundo

Responde siempre en castellano rioplatense.

Inicia ahora la aventura. Escena 1: El jugador despierta en la estación Florida del subte B, solo, a medianoche, con una sed antinatural, rodeado de silencio y luces parpadeantes. Describe con detalle la escena e invita al jugador a tomar su primera decisión.
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
        self.health = 20
        self.max_health = 20
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
        
        health_group = QtWidgets.QGroupBox("Salud")
        health_group.setAlignment(QtCore.Qt.AlignHCenter)
        health_vbox = QtWidgets.QVBoxLayout(health_group)
        self.health_label = QtWidgets.QLabel()
        health_vbox.addWidget(self.health_label)
        inv_layout.addWidget(health_group)

        self.update_inventory_display()
        self.update_health_display()

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

    def update_health_display(self) -> None:
        self.health_label.setText(f"{self.health}/{self.max_health}")

    def change_health(self, delta: int) -> None:
        self.health = max(0, min(self.max_health, self.health + delta))
        self.update_health_display()

    def parse_user_input(self, text: str) -> None:
        m = re.match(r"\b(?:agarro|tomo|cojo|recojo|levanto)\s+(.+)", text, re.I)
        if m:
            item = m.group(1).strip().strip("\"' ")
            self.add_item(item)

    def parse_ai_response(self, text: str) -> None:
        vida = re.search(r"Vida\s+actual[:\s]*(\d+)/(\d+)", text, re.I)
        if vida:
            self.health = int(vida.group(1))
            self.max_health = int(vida.group(2))
            self.update_health_display()
        for dmg in re.findall(r"Recibes\s+(\d+)\s+punto", text, re.I):
            self.change_health(-int(dmg))
        for item in re.findall(r"Obtienes\s+\"([^\"]+)\"", text, re.I):
            if item not in self.inventory:
                self.add_item(item)

    def start_adventure(self) -> None:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.messages + [{"role": "user", "content": "Iniciemos"}],
        )
        text = response.choices[0].message.content.strip()
        self.messages.append({"role": "assistant", "content": text})
        self.append_text(text)
        self.parse_ai_response(text)

    def send_message(self) -> None:
        user_text = self.input.text().strip()
        if not user_text:
            return

        self.append_text(f'<span style="color:#FF5555;">&gt; {user_text}</span>')
        self.messages.append({"role": "user", "content": user_text})
        self.parse_user_input(user_text)

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
            self.parse_ai_response(text)
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

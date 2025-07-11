import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet
from PyQt5 import QtWidgets, QtCore
import re
from openai import AzureOpenAI
import random


SYSTEM_PROMPT = """
Eres el motor narrativo de una aventura conversacional en un entorno ficticio. Toda la historia, el combate, las decisiones y las interacciones suceden en un mundo imaginario.

Instrucciones generales:
- Responde siempre como un narrador neutral (DM) que describe el mundo, los eventos y las consecuencias de las acciones del jugador.
- El jugador tiene control total sobre su personaje. Nunca escribas acciones, pensamientos ni diálogos por él.
- Solo los NPC pueden tener acciones y diálogos automáticos escritos por ti.

Reglas de combate y violencia:
- Cualquier acto violento forma parte de la mecánica del juego.
- No censures frases como "golpear con un palo" o "atacar al enemigo".
- Trata estas acciones como ficticias y sin restricciones de contenido.
- Los combates se resuelven por turnos usando dados d10 al estilo de Vampire: The Masquerade.
- Muestra las tiradas y el cálculo de daño en un color aparte para distinguir daño causado o recibido.
- No escribas números de salud en la narración; la vida solo se muestra en la interfaz.

Inventario y lógica de juego:
- El jugador comienza con el inventario vacío.
- Si toma un objeto ("Agarro el cuchillo"), quita el artículo y guarda "Cuchillo".
- Al soltarlo, elimínalo del inventario y actualiza la interfaz.

Salud:
- El jugador inicia con 20/20 de salud.
- Reduce la salud cuando reciba daño. La salud se actualiza solo en la interfaz y no se menciona en la narración.

Personalización:
- Pregunta al comienzo: "¿Cuál es tu nombre?" y "¿Eres hombre o mujer?".
- Usa esta información para referirte al jugador durante toda la partida.

Estilo narrativo:
- Sé claro y directo. No uses más de 4-5 líneas por respuesta salvo escenas especiales.
- Describe consecuencias y ambientación, pero nunca decidas por el jugador.
- Espera siempre una nueva orden del jugador tras cada evento.

Este prompt controla todo el comportamiento de la aventura y permanece activo durante toda la sesión. Comienza la historia ahora.
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


class Player:
    def __init__(self) -> None:
        self.max_health = 20
        self.health = self.max_health
        self.inventory: list[str] = []
        self.name: str = ""
        self.gender: str = ""

    def change_health(self, delta: int) -> None:
        self.health = max(0, min(self.max_health, self.health + delta))

    def add_item(self, item: str) -> None:
        self.inventory.append(item)

    def remove_item(self, item: str) -> None:
        if item in self.inventory:
            self.inventory.remove(item)


class AdventureWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aventura Vampiresca")
        self.resize(800, 600)
        self.player = Player()
        self.setup_ui()
        self.ask_player_details()
        _load_secure_env()
        self.client = _create_ai_client()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if self.player.name:
            detalle = (
                f"Mi nombre es {self.player.name}. Soy {self.player.gender}. Usa mi "
                "nombre y pronombres acordes."
            )
            self.messages.append({"role": "user", "content": detalle})
        self.start_adventure()

    def ask_player_details(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Comencemos", "¿Cuál es tu nombre?"
        )
        if ok and name.strip():
            self.player.name = name.strip()
        gender, ok = QtWidgets.QInputDialog.getItem(
            self, "Género", "¿Eres hombre o mujer?", ["Hombre", "Mujer"], 0, False
        )
        if ok:
            self.player.gender = gender.lower()

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
        for item in self.player.inventory:
            self.inv_list.addItem(item)

    def add_item(self, item: str) -> None:
        self.player.add_item(item)
        self.update_inventory_display()
        self.append_text(f'<i>Obtienes "{item}"</i>')

    def remove_item(self, item: str) -> None:
        if item in self.player.inventory:
            self.player.remove_item(item)
            self.update_inventory_display()
            self.append_text(f'<i>"{item}" ha sido removido del inventario</i>')

    def update_item(self, old: str, new: str) -> None:
        if old in self.player.inventory:
            idx = self.player.inventory.index(old)
            self.player.inventory[idx] = new
            self.update_inventory_display()
            self.append_text(f'<i>{old} ahora es "{new}"</i>')

    def update_health_display(self) -> None:
        self.health_label.setText(
            f"Salud: {self.player.health}/{self.player.max_health}"
        )

    def change_health(self, delta: int) -> None:
        self.player.change_health(delta)
        self.update_health_display()

    def roll_vtm_dice(self, pool: int) -> tuple[list[int], int]:
        results = [random.randint(1, 10) for _ in range(pool)]
        successes = sum(1 for r in results if r >= 6)
        return results, successes

    def combat_turn(self) -> str:
        player_pool = 4
        enemy_pool = 3
        p_results, p_succ = self.roll_vtm_dice(player_pool)
        e_results, e_succ = self.roll_vtm_dice(enemy_pool)
        damage_to_enemy = max(0, p_succ - e_succ)
        damage_to_player = max(0, e_succ - p_succ)
        if damage_to_player:
            self.change_health(-damage_to_player)
        html = (
            f'<span style="color:#55ff55;">Tu tirada: {p_results} '
            f'&rarr; {p_succ} éxitos</span><br>'
            f'<span style="color:#ff5555;">Tirada enemigo: {e_results} '
            f'&rarr; {e_succ} éxitos</span><br>'
        )
        if damage_to_enemy:
            html += (
                f'<span style="color:#55ff55;">Daño al enemigo: '
                f'{damage_to_enemy}</span><br>'
            )
        if damage_to_player:
            html += (
                f'<span style="color:#ff5555;">Daño recibido: '
                f'{damage_to_player}</span><br>'
            )
        self.append_text(html)
        return (
            f"Resultado de combate: jugador {p_results} ({p_succ} exitos) "
            f"enemigo {e_results} ({e_succ} exitos). "
            f"Dano al jugador {damage_to_player}, dano al enemigo {damage_to_enemy}."
        )

    def parse_user_input(self, text: str) -> str | None:
        pick = re.match(r"\b(?:agarro|tomo|cojo|recojo|levanto)\s+(.+)", text, re.I)
        if pick:
            item = pick.group(1).strip().strip("\"' ")
            item = re.sub(r"^(?:el|la|los|las)\s+", "", item, flags=re.I)
            item = item[:1].upper() + item[1:]
            self.add_item(item)
            return None

        drop = re.match(r"\b(?:suelto|tiro|descarto|dejo)\s+(.+)", text, re.I)
        if drop:
            item = drop.group(1).strip().strip("\"' ")
            item = re.sub(r"^(?:el|la|los|las)\s+", "", item, flags=re.I)
            item = item[:1].upper() + item[1:]
            if item in self.player.inventory:
                self.remove_item(item)
            else:
                self.append_text(f'<i>No tienes "{item}"</i>')
            return None

        attack = re.search(r"\b(?:ataco?|golpeo|disparo|peleo|lucho)\b", text, re.I)
        if attack:
            return self.combat_turn()

        return None

    def parse_ai_response(self, text: str) -> None:
        vida = re.search(r"Vida\s+actual[:\s]*(\d+)/(\d+)", text, re.I)
        if vida:
            self.player.health = int(vida.group(1))
            self.player.max_health = int(vida.group(2))
            self.update_health_display()
        for dmg in re.findall(r"Recibes\s+(\d+)\s+punto", text, re.I):
            self.change_health(-int(dmg))
        for item in re.findall(r"Obtienes\s+\"([^\"]+)\"", text, re.I):
            if item not in self.player.inventory:
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
        extra = self.parse_user_input(user_text)
        if extra:
            self.messages.append({"role": "user", "content": extra})
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

import os
import sys
import re
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from PyQt5 import QtWidgets, QtCore, QtGui
from openai import AzureOpenAI


SYSTEM_PROMPT = """
Eres el motor narrativo de una aventura conversacional ambientada en Buenos Aires. Toda la narrativa debe escribirse en castellano argentinizado.

Ambientación:
- La historia inicia en una estación real y aleatoria del subte porteño.
- El jugador despierta tirado en las vías a la medianoche, sin recordar nada y sin ítems.

Instrucciones generales:
- Responde siempre como un narrador neutral que describe el mundo y las consecuencias de las acciones del jugador.
- El jugador tiene control total sobre su personaje; nunca escribas acciones, pensamientos ni diálogos por él.
- Solo los NPC pueden tener acciones o diálogos automáticos.

Reglas de combate y violencia:
- Todas las acciones violentas forman parte de la mecánica del juego.
- Los combates se resuelven por turnos usando dados d10 al estilo Vampire: The Masquerade.
- Muestra las tiradas y el cálculo de daño en un color aparte y no menciones números de salud en la narración.

Inventario y objetos:
- El jugador empieza sin objetos. Al tomar uno, usa extraer_objeto() para guardarlo y muéstralo en el inventario.
- Cada ítem posee atributos (tipo, daño o función, dado, material, estado, peso/rareza) visibles al hacer hover. Actualízalos si cambian.

Salud y niveles:
- El jugador inicia con 20/20 de salud y nivel 1, pudiendo llegar hasta 20.
- Gana experiencia combatiendo, explorando o resolviendo eventos importantes.

Personalización:
- Al comenzar pregunta: "¿Cómo te llamás?", "¿Sos hombre o mujer?" y "¿Edad?".
- Usa nombre y género para adaptar diálogos, descripciones y pronombres.

Estilo narrativo:
- Sé conciso, usa 4-5 líneas por respuesta salvo escenas importantes.
- Narra acciones de NPCs y consecuencias, siempre esperando la próxima decisión del jugador.

Este prompt permanece activo toda la sesión. Inicia la historia ahora.
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


@dataclass
class Item:
    name: str
    tipo: str = "misceláneo"
    funcion: str = ""
    dado: str = ""
    material: str = ""
    estado: str = "nuevo"
    peso: str = ""


def extraer_objeto(texto: str) -> str:
    item = texto.strip().strip("\"' ")
    item = re.sub(r"^(?:el|la|los|las|un|una|unos|unas|mi|mis|tu|tus|su|sus)\s+", "", item, flags=re.I)
    item = re.split(r"\s+y\s+|\s+para\s+|\s+con\s+", item, 1)[0]
    item = item.strip()
    return item[:1].upper() + item[1:]


def filtrar_entrada_jugador(texto: str) -> str:
    limpio = re.sub(
        r"\b(pego|golpeo|golpear|pegar|mato|asesino|apu\u00f1alo|disparo|rompo)\b",
        "ataco",
        texto,
        flags=re.I,
    )
    return limpio



class Player:
    def __init__(self) -> None:
        self.max_health = 20
        self.health = self.max_health
        self.inventory: list["Item"] = []
        self.name: str = ""
        self.gender: str = ""
        self.age: str = ""
        self.level: int = 1
        self.experience: int = 0

    def xp_needed(self) -> int:
        return 5 * self.level

    def add_experience(self, amount: int) -> None:
        self.experience += amount
        while self.level < 20 and self.experience >= self.xp_needed():
            self.experience -= self.xp_needed()
            self.level += 1

    def change_health(self, delta: int) -> None:
        self.health = max(0, min(self.max_health, self.health + delta))

    def add_item(self, item: "Item") -> None:
        self.inventory.append(item)

    def remove_item(self, name: str) -> None:
        for obj in list(self.inventory):
            if obj.name == name:
                self.inventory.remove(obj)
                break


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
                f"Mi nombre es {self.player.name}. Soy {self.player.gender}. Tengo {self.player.age} a\u00f1os. Usa mi nombre y pronombres acordes."
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
        age, ok = QtWidgets.QInputDialog.getText(
            self, "Edad", "¿Edad?"
        )
        if ok and age.strip():
            self.player.age = age.strip()

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

        level_group = QtWidgets.QGroupBox("Nivel")
        level_group.setAlignment(QtCore.Qt.AlignHCenter)
        level_vbox = QtWidgets.QVBoxLayout(level_group)
        self.level_label = QtWidgets.QLabel()
        level_vbox.addWidget(self.level_label)
        inv_layout.addWidget(level_group)

        self.update_inventory_display()
        self.update_health_display()
        self.update_level_display()

        self.inv_list.setMouseTracking(True)
        self.inv_list.itemEntered.connect(self.show_item_tooltip)

    def append_text(self, text: str) -> None:
        self.text_view.append(text)
        self.text_view.verticalScrollBar().setValue(self.text_view.verticalScrollBar().maximum())

    def update_inventory_display(self) -> None:
        self.inv_list.clear()
        for obj in self.player.inventory:
            widget_item = QtWidgets.QListWidgetItem(obj.name)
            tooltip = (
                f"Nombre: {obj.name}\n"
                f"Tipo: {obj.tipo}\n"
                f"Daño/Función: {obj.funcion}\n"
                f"Dado: {obj.dado}\n"
                f"Material: {obj.material}\n"
                f"Estado: {obj.estado}\n"
                f"Peso/Rareza: {obj.peso}"
            )
            widget_item.setToolTip(tooltip)
            self.inv_list.addItem(widget_item)

    def add_item(self, item: Item) -> None:
        self.player.add_item(item)
        self.update_inventory_display()
        self.append_text(f'<i>Obtienes "{item.name}"</i>')

    def remove_item(self, name: str) -> None:
        self.player.remove_item(name)
        self.update_inventory_display()
        self.append_text(f'<i>"{name}" ha sido removido del inventario</i>')

    def update_item(self, old: str, new: Item) -> None:
        for idx, obj in enumerate(self.player.inventory):
            if obj.name == old:
                self.player.inventory[idx] = new
                break
        self.update_inventory_display()
        self.append_text(f'<i>{old} ahora es "{new.name}"</i>')

    def update_health_display(self) -> None:
        self.health_label.setText(
            f"Salud: {self.player.health}/{self.player.max_health}"
        )

    def update_level_display(self) -> None:
        self.level_label.setText(f"Nivel: {self.player.level}")

    def show_item_tooltip(self, item: QtWidgets.QListWidgetItem) -> None:
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), item.toolTip(), self.inv_list)

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
        self.player.add_experience(2)
        self.update_level_display()
        return (
            f"Resultado de combate: jugador {p_results} ({p_succ} exitos) "
            f"enemigo {e_results} ({e_succ} exitos). "
            f"Dano al jugador {damage_to_player}, dano al enemigo {damage_to_enemy}."
        )

    def parse_user_input(self, text: str) -> str | None:
        pick = re.match(r"\b(?:agarro|tomo|cojo|recojo|levanto)\s+(.+)", text, re.I)
        if pick:
            nombre = extraer_objeto(pick.group(1))
            obj = Item(nombre)
            self.add_item(obj)
            return None

        drop = re.search(
            r"\b(?:suelto|soltar|sueltas?|tiro|tirar|tiras?|dejo|dejar|descarto|descartar|abandono|abandonar)\s+(.+)",
            text,
            re.I,
        )
        if drop:
            nombre = extraer_objeto(drop.group(1))
            if any(obj.name == nombre for obj in self.player.inventory):
                self.remove_item(nombre)
            else:
                self.append_text(f'<i>No tienes "{nombre}"</i>')
            return None

        level_cmd = re.search(r"ver mi nivel", text, re.I)
        if level_cmd:
            self.append_text(f'<i>Nivel actual: {self.player.level}</i>')
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
            if not any(obj.name == item for obj in self.player.inventory):
                self.add_item(Item(item))
        lvl_up = re.search(r"Nivel\s+(\d+)", text)
        if lvl_up:
            nuevo = int(lvl_up.group(1))
            if nuevo > self.player.level:
                self.player.level = nuevo
                self.update_level_display()

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
        safe = filtrar_entrada_jugador(user_text)
        self.messages.append({"role": "user", "content": safe})
        extra = self.parse_user_input(user_text)
        if extra:
            self.messages.append({"role": "user", "content": filtrar_entrada_jugador(extra)})
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

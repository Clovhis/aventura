import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet
from PyQt5 import QtWidgets, QtCore
from openai import AzureOpenAI


SYSTEM_PROMPT = (
    "Eres el narrador de una aventura interactiva ambientada en Buenos Aires "
    "contempor\u00e1neo, inspirada en Vampire: The Masquerade. "
    "El jugador despierta en las v\u00edas del Subte B, estaci\u00f3n Florida, sin "
    "recordar c\u00f3mo lleg\u00f3 all\u00ed. Describe la escena en segunda persona "
    "y pregunt\u00e1 qu\u00e9 hace. No tomes decisiones por el jugador y responde "
    "en castellano rioplatense."
)


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
        self.setup_ui()
        _load_secure_env()
        self.client = _create_ai_client()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.start_adventure()

    def setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

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
        layout.addWidget(self.text_view)

        self.input = QtWidgets.QLineEdit()
        self.input.returnPressed.connect(self.send_message)
        send_btn = QtWidgets.QPushButton("Enviar")
        send_btn.clicked.connect(self.send_message)
        h = QtWidgets.QHBoxLayout()
        h.addWidget(self.input)
        h.addWidget(send_btn)
        layout.addLayout(h)

    def append_text(self, text: str) -> None:
        self.text_view.append(text)
        self.text_view.verticalScrollBar().setValue(self.text_view.verticalScrollBar().maximum())

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

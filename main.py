# This Python file uses the following encoding: utf-8
import os
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from test_performance_pid_table import AGVController
from toggle_relay import TurnLedOn
import rc_ResourceIma

if __name__ == "__main__":
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    robotController = AGVController()
    engine.rootContext().setContextProperty("robotController", robotController)

    turnLedOn = TurnLedOn()
    engine.rootContext().setContextProperty("turnLedOn", turnLedOn)



    qml_file = Path(__file__).resolve().parent / "main.qml"

    engine.load(qml_file)

    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())

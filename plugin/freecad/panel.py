from __future__ import annotations

import json
import os
import tempfile
from typing import Optional

try:
    import FreeCAD  # type: ignore
    import FreeCADGui  # type: ignore
    import Part  # type: ignore
except Exception:  # pragma: no cover
    FreeCAD = None
    FreeCADGui = None
    Part = None

from PySide2 import QtCore, QtWidgets

from .api_client import ApiClient
from .serializer import serialize_document

ORG = "IDP"
APP = "FreeCADAddon"


def log(msg: str):  # pragma: no cover - used in FreeCAD
    try:
        FreeCAD.Console.PrintMessage(msg + "\n")
    except Exception:
        print(msg)


class IdpPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("IDP Export & Upload")

        self.apiUrl = QtWidgets.QLineEdit()
        self.apiUrl.setPlaceholderText("http://localhost:8000")
        self.token = QtWidgets.QLineEdit()
        self.token.setEchoMode(QtWidgets.QLineEdit.Password)
        self.projectId = QtWidgets.QLineEdit()
        self.projectId.setValidator(QtWidgets.QIntValidator(1, 10**12))
        self.name = QtWidgets.QLineEdit()
        self.name.setPlaceholderText("Artifact name (optional)")
        self.uploadBtn = QtWidgets.QPushButton("Export & Upload")
        self.uploadBtn.clicked.connect(self.on_upload)
        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)

        form = QtWidgets.QFormLayout()
        form.addRow("API URL", self.apiUrl)
        form.addRow("Token", self.token)
        form.addRow("Project ID", self.projectId)
        form.addRow("Name", self.name)

        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(form)
        v.addWidget(self.uploadBtn)
        v.addWidget(self.status)

        self._load_settings()

    def _load_settings(self):
        s = QtCore.QSettings(ORG, APP)
        self.apiUrl.setText(s.value("api_url", "http://localhost:8000"))
        self.token.setText(s.value("token", ""))

    def _save_settings(self):
        s = QtCore.QSettings(ORG, APP)
        s.setValue("api_url", self.apiUrl.text())
        s.setValue("token", self.token.text())

    def _current_doc(self):  # pragma: no cover - requires FreeCAD
        if FreeCAD is None:
            return None
        return FreeCAD.ActiveDocument

    def _export_step(self, doc, path):  # pragma: no cover - requires FreeCAD
        if Part is None:
            raise RuntimeError("FreeCAD Part module not available for STEP export")
        objs = [o for o in (doc.Objects or []) if hasattr(o, "Shape")]
        if not objs:
            raise RuntimeError("No solid objects to export")
        Part.export(objs, path)

    def on_upload(self):
        try:
            self._save_settings()
            base = self.apiUrl.text().strip()
            tok = self.token.text().strip()
            pid_text = self.projectId.text().strip()
            if not base or not tok or not pid_text:
                raise RuntimeError("Please provide API URL, token, and project ID")
            project_id = int(pid_text)

            doc = self._current_doc()
            if doc is None:
                raise RuntimeError("No active FreeCAD document")

            params = serialize_document(doc)
            tmpdir = tempfile.gettempdir()
            name = self.name.text().strip() or (
                getattr(doc, "Label", None) or "artifact"
            )
            steppath = os.path.join(tmpdir, f"{name}.step")
            self._export_step(doc, steppath)

            client = ApiClient(base, tok)
            self.status.setText("Uploading...")
            QtWidgets.QApplication.processEvents()
            res = client.upload_artifact(project_id, steppath, params, name=name)
            self.status.setText(f"Uploaded artifact id={res.get('id')}")
            log(f"IDP: uploaded artifact {res}")
        except Exception as e:  # pragma: no cover - UI
            self.status.setText(str(e))
            log(f"IDP error: {e}")


def show_panel():  # pragma: no cover - UI
    w = IdpPanel()
    if FreeCADGui:
        FreeCADGui.Control.showDialog(w)
    else:
        w.show()
    return w

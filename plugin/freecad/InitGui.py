import FreeCADGui  # type: ignore

from .panel import show_panel


class IdpCmd:
    def GetResources(self):  # pragma: no cover
        return {
            "Pixmap": "",
            "MenuText": "IDP Export & Upload",
            "ToolTip": "Export current document to STEP and upload to IDP",
        }

    def IsActive(self):  # pragma: no cover
        return True

    def Activated(self):  # pragma: no cover
        show_panel()


FreeCADGui.addCommand("IDP_ExportUpload", IdpCmd())


def Initialize():  # pragma: no cover
    m = FreeCADGui.getMainWindow().menuBar()
    try:
        mw = FreeCADGui.getMainWindow()
        mw.addToolBar("IDP")
    except Exception:
        pass

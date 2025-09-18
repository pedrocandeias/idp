# IDP FreeCAD Add-on

FreeCAD panel to export the current document as STEP and upload artifacts to the IDP API.

Features
- Configure API base URL and token
- Enter Project ID and export+upload with a click
- Serializes parametric metadata (overall dimensions, control positions/types, forces/torques, label color/size) to JSON and uploads alongside the STEP file
- Simple logs and robust error messages

Installation
1. Copy the `plugin/freecad` folder into your FreeCAD `Mod/` directory, e.g.:
   - Linux: `~/.local/share/FreeCAD/Mod/idp_freecad`
   - macOS: `~/Library/Preferences/FreeCAD/Mod/idp_freecad`
   - Windows: `%APPDATA%/FreeCAD/Mod/idp_freecad`
2. Restart FreeCAD.
3. You should see a new menu entry under Tools → IDP → Export & Upload.
   - If not, open the Python console and run:
     ```python
     import idp_freecad
     idp_freecad.show_panel()
     ```

Usage
- Open a document with solids and named control objects (optional).
- Tools → IDP → Export & Upload.
- Set API URL (e.g. http://localhost:8000), paste a JWT token, and enter a Project ID.
- Click “Export & Upload”. A STEP file is generated in a temporary folder and uploaded with the JSON metadata.

Notes
- STEP export uses FreeCAD Part workbench exporter.
- Token is stored using QSettings on your machine (user scope).
- Controls extraction is best-effort: it looks for objects whose Label or Name starts with `CTRL_` to infer controls; otherwise skips.

Testing (serializer only)
- Pure-Python tests live in `plugin/freecad/tests`. Run with:
  ```bash
  python -m pytest plugin/freecad/tests -q
  ```
  These tests don’t require FreeCAD.


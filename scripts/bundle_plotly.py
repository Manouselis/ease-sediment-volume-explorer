"""Bundle the installed Plotly JS locally; no CDN required at runtime."""
from pathlib import Path
from importlib.metadata import distribution
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
javascript = get_plotlyjs()
(ROOT / "static/plotly.min.js").write_text(javascript)
package = distribution("plotly")
license_path = next(package.locate_file(p) for p in package.files if str(p).endswith("licenses/LICENSE.txt"))
original_header = javascript.split("*/", 1)[0] + "*/"
(ROOT / "static/plotly-LICENSE.txt").write_text(original_header + "\n\n" + license_path.read_text())

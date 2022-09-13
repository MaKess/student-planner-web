import os

root_path = os.path.dirname(os.path.abspath(__file__))
activate_this = os.path.join(root_path, "venv", "bin", "activate_this.py")
with open(activate_this) as fh:
    exec(fh.read(), {'__file__': activate_this})

import sys
sys.path.insert(0, root_path)

from webplanner import create_app
application = create_app()

from pathlib import Path


__version__ = "0.1.0"


CODE_DIR = Path(__file__).parent.parent.resolve().absolute()
DEFAULT_ROOT_FOLDER = CODE_DIR / "data"
DEFAULT_CONFIG_FILE = CODE_DIR / "config.yml"


from twinspect.globals import *
from twinspect.datasets.ultils import *
from twinspect.datasets.integrity import *
from twinspect.datasets.download import *
from twinspect.models import *
from twinspect.options import *
from twinspect.tools import *
from twinspect.transformations.transform import *
from twinspect.algos.processing import *
from twinspect.exceptions import *

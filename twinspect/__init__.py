from pathlib import Path


CODE_DIR = Path(__file__).parent.parent.resolve().absolute()
DEFAULT_ROOT_FOLDER = CODE_DIR / "data"
DEFAULT_CONFIG_FILE = CODE_DIR / "config.yml"

from twinspect.schema import Configuration, Dataset, Transformation, Mode
from twinspect.options import *
from twinspect.tools import *


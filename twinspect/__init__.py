from pathlib import Path


CODE_DIR = Path(__file__).parent.parent.resolve().absolute()
DEFAULT_ROOT_FOLDER = CODE_DIR / "data"

from twinspect.config import *
from twinspect.schema import Dataset
from twinspect.tools import *


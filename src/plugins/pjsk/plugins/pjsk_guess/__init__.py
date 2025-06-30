from .guess import PJSKGuess
from .models import PJSKGuessMetadata as Metadata
from .models import PJSKGuessStatusManager as StatusManager
from .database.mongo import PJSKGuessDatabase as Database

PATH_METADATA = "src/plugins/pjsk/plugins/pjsk_guess/metadata.json"
MONGODB_URI = ""

status_manager = StatusManager()
metadata = Metadata(PATH_METADATA)
database = Database(MONGODB_URI) if MONGODB_URI else None

pjsk_guess = PJSKGuess(status_manager, metadata, database)

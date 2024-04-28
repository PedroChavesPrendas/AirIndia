import sentry_sdk
from sentry_sdk.integrations.loguru import LoguruIntegration
from sentry_sdk.integrations.loguru import LoggingLevels
import os
from dotenv import load_dotenv
load_dotenv()

sentry_loguru = LoguruIntegration(
    level=LoggingLevels.INFO.value,        
    event_level=LoggingLevels.ERROR.value  
)
if dsn := os.getenv("SENTRY_DSN_URL"):
    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=0.5,
        include_local_variables=True,
        integrations=[
            sentry_loguru,
        ],
    )
else:
    raise Exception("Sentry config not found")
"""Constants for Anker Solix."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME: str = "Anker Solix"
DOMAIN: str = "anker_solix"
VERSION: str = "1.0.0"
MANUFACTURER: str = "Anker"
ATTRIBUTION: str = "Data provided by Anker Solix Api"
ACCEPT_TERMS: str = "accept_terms"
TERMS_LINK: str = "terms_link"
TC_LINK: str = "https://github.com/thomluther/hacs-anker-solix/blob/main/README.md"
TESTMODE: str = "testmode"
TESTFOLDER: str = "testfolder"
INTERVALMULT: str = "dev_interval_mult"
UPDT_INTV_MIN: str = "updt_interval_min"
UPDT_INTV_MAX: str = "updt_interval_max"
EXAMPLESFOLDER: str = "examples"
ERROR_DETAIL: str = "error_detail"
LAST_PERIOD: str = "last_period"
LAST_RESET: str = "last_reset"
SHARED_ACCOUNT: str = "shared_account"
IMAGEFOLDER: str = "images"
ALLOW_TESTMODE: bool = (
    True  # True will enable configuration options for testmode and testfolder
)
TEST_NUMBERVARIANCE: bool = False  # True will enable variance for some measurement numbers when running in testmode from static files (numbers have no logical meaning)
CREATE_ALL_ENTITIES: bool = False  # True will create all entities per device type for testing even if no values available

from TEAMZYRO import *
import importlib
import logging
from TEAMZYRO.modules import ALL_MODULES

def main() -> None:
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("All Features Loaded...")

    ZYRO.run()  # ← बस यही चलाना है

if __name__ == "__main__":
    main()

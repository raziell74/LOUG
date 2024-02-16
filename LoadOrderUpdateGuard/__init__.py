# __init__.py

import mobase

from .plugin_diagnose import LoadOrderUpdateGuard

def createPlugin() -> mobase.IPluginDiagnose:
    return LoadOrderUpdateGuard()
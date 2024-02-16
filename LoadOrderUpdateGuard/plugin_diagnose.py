from ast import Dict
from typing import Sequence, Union, List
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox
from bethesda_structs.plugin.fnv import FNVPlugin

import mobase
import json
import re

class LOUG_Plugin:
    name: str
    display_name: str
    extension: str
    origin: str
    priority: int
    esl: bool
    master: bool
    state: int
    problem_desc: str
    enabled: bool

class LoadOrderUpdateGuard(mobase.IPluginDiagnose):
    NAME = "Load Order ESL Guard"
    AUTHOR="Raziell74"
    DESCRIPTION = "Monitors for any breaking ESL load order changes that could cause save corruption."
    ERROR_MESSAGE = "Possible Corrupt ESL load order change detected."

    def __init__(self):
        super(LoadOrderUpdateGuard, self).__init__()
        self._organizer: Union[mobase.IOrganizer, None] = None
        self._loug_initialized: bool = False
        self._highest_stable_priority: int = 0
        self._highest_stable_priority_plugin_name: str = ""
        self._stable_plugin_list: Dict[str, LOUG_Plugin] = {}
        self._changed_plugin_list: Dict[str, LOUG_Plugin] = {}
        self._new_plugins: Dict[str, LOUG_Plugin] = {}
        self._missing_plugins: Dict[str, LOUG_Plugin] = {}
        self._save_file_name: str = "stable_load_order_LOUG.json"
        
        self._detected_master_flag_added: bool = False
        self._detected_master_flag_removed: bool = False
        self._detected_esl_flag_added: bool = False
        self._detected_esl_flag_removed: bool = False
        self._detected_esl_priority_shift: bool = False
        
        self._detected_missing: bool = False
        self._detected_new: bool = False
        self._detected_changed_extension: bool = False

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer
        self._pluginList = self._organizer.pluginList()

        # Attach monitors to MO2 events
        self._pluginList.onRefreshed(self.__refreshEslPluginList)
        self._pluginList.onPluginMoved(self.__reportMovedPlugin)
        self._pluginList.onPluginStateChanged(self.__reportPluginToggle)

        self._organizer.onProfileChanged(self._onProfileChanged)
        self._organizer.onAboutToRun(self._onGameRun)

        return True

    def __reportPluginToggle(self, plugins) -> bool:
        # QMessageBox.information(None, "LOUG Debug", "LOUG - Plugin Enabled/Disabled.")
        self.__refreshEslPluginList()
        return True
    
    def _onProfileChanged(self, oldProfile: mobase.IProfile, newProfile: mobase.IProfile) -> bool:
        # QMessageBox.information(None, "LOUG Debug", "LOUG - Profile Changed. Updating from new profile LOUG file")
        self._loug_initialized: bool = False
        return True
    
    def _onGameRun(self, application_path: str) -> bool:
        # Check for game executables. Default Game Binary, Script Extenders, and Bethesda Launchers
        application_name = Path(application_path).name
        default_binary_name: str = self._organizer.managedGame().binaryName()
        
        beth_launcher_pattern = r".*Launcher\.exe$"
        is_game_launcher: bool = re.search(beth_launcher_pattern, application_name, re.IGNORECASE)
        
        script_extender_pattern = r"se.*_loader\.exe$"
        is_se_loader = re.search(script_extender_pattern, application_name, re.IGNORECASE)
        
        if application_name == default_binary_name or is_game_launcher or is_se_loader:
            # Game Launch detected. Assume this means the user is ok with their current load order and save it as the stable load order
            self._saveStableLoadOrder()

        return True
    
    def _getLougFilePath(self) -> str:
        # determine the directory where we'll store the current load order
        save_dir = self._organizer.profilePath()
        if(save_dir == "" or not self._organizer.profile().localSavesEnabled()):
            save_dir = self._organizer.managedGame().documentsDirectory()
        save_path = Path(save_dir) / self._save_file_name
        # QMessageBox.information(None, "LOUG Debug", "LOUG Save File Path: {0}".format(save_path))
        return save_path
    
    def _loadStableLoadOrder(self) -> None:
        # Check if the file exists, if it does then load it
        loug_file = self._getLougFilePath()
        self._stable_plugin_list: Dict[str, LOUG_Plugin] = {} # Clear the previous list
        if loug_file.exists():
            with open(loug_file, "r") as f:
                json_data = json.load(f)
                for plugin_name in json_data.keys():
                    self._stable_plugin_list[plugin_name] = LOUG_Plugin()
                    self._stable_plugin_list[plugin_name].__dict__ = json_data[plugin_name]
            # QMessageBox.information(None, "LOUG Debug", "Successfully Imported From LOUG File")
        else:
            loadOrder: List[LOUG_Plugin] = self._scanLoadOrder()
            # QMessageBox.information(None, "LOUG Debug", "LOUG File Not Found, scanning current load order of {0} plugins".format(len(loadOrder)))
            for plugin in loadOrder:
                self._stable_plugin_list[plugin.name] = plugin
            
            # Sort Stable Plugin List by priority
            self._stable_plugin_list: Dict[str, LOUG_Plugin] = dict(sorted(self._stable_plugin_list.items(), key=lambda item: item[1].priority))
        
        # Find the highest priority ESL flagged plugin in the stable list
        self._highest_stable_priority = 0
        reversed_stable_plugin_list: Dict[str, LOUG_Plugin] = reversed(self._stable_plugin_list)
        for plugin_name in reversed_stable_plugin_list:
            plugin: LOUG_Plugin = self._stable_plugin_list[plugin_name]
            if plugin.esl:
                has_new_forms: bool = not self._isPatchOrDummy(self._organizer.resolvePath(plugin.name))
                
                if has_new_forms:
                    # Any new ESLs will have to have a higher priority than this one to be considered safe to add to the game
                    self._highest_stable_priority = plugin.priority
                    self._highest_stable_priority_plugin_name = plugin.name
                    # QMessageBox.information(None, "LOUG Debug", "Highest Stable Priority: {0} - Plugin: {1}".format(self._highest_stable_priority, plugin.name))
                    break

        self._loug_initialized = True

    def _isPatchOrDummy(self, file_path: str) -> bool:
        if not self._organizer.pluginSetting(self.name(), "more_accurate_load_order_moves"):
            return False
        
        parsed_plugin_header = FNVPlugin.parse_header(file_path)

        header_data = parsed_plugin_header.subrecords[0].parsed.value
        num_records: int = header_data.num_records
        next_object_id: int = header_data.next_object_id

        esl_first_object_id: int = 0x801
        is_patch: bool = num_records > 0 and next_object_id <= esl_first_object_id
        is_dummy: bool = num_records == 0

        # return is_patch or is_dummy
        return is_patch or is_dummy
    
    
    # @TODO - Add a system for tracking specific save file load orders
    def _saveStableLoadOrder(self) -> None:
        # Refresh stable plugin list with current load order
        self._stable_plugin_list: Dict[str, LOUG_Plugin] = {} # Clear stable list so it's rebuilt from scratch
        loadOrder: List[LOUG_Plugin] = self._scanLoadOrder()
        for plugin in loadOrder:
            self._stable_plugin_list[plugin.name] = plugin
        # Sort Stable Plugin List by priority
        self._stable_plugin_list: Dict[str, LOUG_Plugin] = dict(sorted(self._stable_plugin_list.items(), key=lambda item: item[1].priority))

        # Convert stable plugin list to a human readable json format
        serialized_load_order = {}
        for plugin_name in self._stable_plugin_list.keys():
            serialized_load_order[plugin_name] = self._stable_plugin_list[plugin_name].__dict__
        serialized_load_order_data = json.dumps(serialized_load_order, indent=4)

        # Write the JSON data to the file
        loug_file = self._getLougFilePath()
        with open(loug_file, "w") as f:
            f.write(serialized_load_order_data)
            # QMessageBox.information(None, "LOUG Debug", "LOUG Save File Written Successfully")
    
    def __reportMovedPlugin(self, pluginName: str, oldIndex: int, newIndex: int) -> None:
        tracking_enabled: bool = self._loug_initialized and self._organizer.pluginSetting(self.name(), "report_on_esl_moved")
        is_esl: bool = self._pluginList.isLightFlagged(pluginName)
        moved_to_safe_priority: bool = newIndex > self._highest_stable_priority and oldIndex > self._highest_stable_priority
        
        if not tracking_enabled or not is_esl:
            self._clearPluginWarning(pluginName)
            return
        
        if pluginName in self._stable_plugin_list:
            plugin: LOUG_Plugin = self._stable_plugin_list[pluginName]
        elif pluginName in self._new_plugins:
            plugin: LOUG_Plugin = self._new_plugins[pluginName]
        else:
            self._clearPluginWarning(pluginName)
            return
        
        # Don't report for plugins whose original priority was already above the highest stable priority and the new priority is also above the highest stable priority
        moved_to_safe_priority: bool = (plugin.priority > self._highest_stable_priority or plugin.priority == -1) and newIndex > self._highest_stable_priority
        # QMessageBox.information(None, "LOUG Debug", "Plugin Moved: {0} - Original Priority: {1} - New Index: {2} - Highest Stable Priority: {3} - Moved to Safe Priority: {4}".format(pluginName, plugin.priority, newIndex,self._highest_stable_priority, moved_to_safe_priority))
        if moved_to_safe_priority:
            self._clearPluginWarning(pluginName)
            return
        
        if newIndex == plugin.priority:
            # If the plugin was moved to the same priority as it was originally then remove it from the changed list 
            self._clearPluginWarning(pluginName)
            return
        
        plugin.problem_desc = "Plugin was moved to an unsafe load order priority"
        self._changed_plugin_list[pluginName] = plugin
        self._detected_esl_priority_shift = True

    def _clearPluginWarning(self, pluginName: str) -> None:
        if pluginName in self._changed_plugin_list:
            del self._changed_plugin_list[pluginName]
    
    def __refreshEslPluginList(self) -> None:
        if not self._loug_initialized:
            self._loadStableLoadOrder()
        
        # reset tracked issues so everything is fully up to date for the next scan
        new_plugins: Dict[str, LOUG_Plugin] = {}
        self._new_plugins: Dict[str, LOUG_Plugin] = {}
        self._missing_plugins: Dict[str, LOUG_Plugin] = {}
        self._changed_plugin_list: Dict[str, LOUG_Plugin] = {}

        self._detected_master_flag_added: bool = False
        self._detected_master_flag_removed: bool = False

        self._detected_esl_flag_added: bool = False
        self._detected_esl_flag_removed: bool = False
        self._detected_esl_priority_shift: bool = False

        self._detected_missing: bool = False
        self._detected_new: bool = False
        self._detected_changed_extension: bool = False
        
        loadOrder: List[LOUG_Plugin] = self._scanLoadOrder()
        for plugin in loadOrder:
            # Check if the plugin is already in our list
            if plugin.name in self._stable_plugin_list:
                # If it is then check if there has been a potential breaking change
                problem: Union[str, bool] = self.__checkChanged(self._stable_plugin_list[plugin.name], plugin)
                if problem:
                    # If it has then add it to the changed list to be reported
                    plugin.problem_desc = problem
                    self._changed_plugin_list[plugin.name] = plugin
                else:
                    # Check the _changed_plugin_list to see if it's in there, if it is then remove it
                    if plugin.name in self._changed_plugin_list:
                        del self._changed_plugin_list[plugin.name]
            else:
                # If it's not, then it's likely a new plugin for this session, so lets track it
                new_plugins[Path(plugin.name).stem] = plugin
        
        # Report plugins that were in the original list but now do not appear in the current loadOrder
        for plugin_name in self._stable_plugin_list:
            plugin: LOUG_Plugin = self._stable_plugin_list[plugin_name]
            if self._pluginList.loadOrder(plugin_name) == -1 and plugin.priority != -1:
                self._missing_plugins[Path(plugin_name).stem] = plugin
        
        # Check for renamed plugins before registering new / missing plugins
        for base_plugin_name in self._missing_plugins:
            if base_plugin_name in new_plugins:
                new_plugin: LOUG_Plugin = new_plugins[base_plugin_name]
                old_plugin: LOUG_Plugin = self._missing_plugins[base_plugin_name]
                if new_plugin.extension != old_plugin.extension:
                    new_plugin.problem_desc = "Plugin Extension changed from {0} to {1}".format(old_plugin.extension, new_plugin.extension)
                    self._changed_plugin_list[new_plugin.name] = new_plugin
                    self._detected_changed_extension = True
                    del new_plugins[base_plugin_name]
                    del self._missing_plugins[base_plugin_name]

        # Add new plugins to the stable list
        for base_plugin_name in new_plugins:
            plugin: LOUG_Plugin = new_plugins[base_plugin_name]
            self._new_plugins[plugin.name] = plugin
            
            if plugin.master and plugin.esl:
                # If the new plugin is an ESM flagged ESL then add it to the changed list to be reported
                plugin.problem_desc = "New ESM flagged as an ESL will shift current ESL Mod Indexes"
                self._changed_plugin_list[plugin.name] = plugin
                self._detected_new = True 
            elif plugin.extension == ".esl":
                # If the new plugin is using the '.esl' extension then add it to the changed list to be reported
                plugin.problem_desc = "New .esl plugin will shift current ESL Mod Indexes"
                self._changed_plugin_list[plugin.name] = plugin
                self._detected_new = True
        
        # Missing Plugins
        for base_plugin_name in self._missing_plugins:
            plugin: LOUG_Plugin = self._missing_plugins[base_plugin_name]
            plugin.problem_desc = "ESL Plugin disabled/removed"
            self._changed_plugin_list[plugin.name] = plugin
            self._detected_missing = True

    def __checkChanged(self, oldPlugin: LOUG_Plugin, newPlugin: LOUG_Plugin) -> Union[str, bool]:
        if newPlugin.esl != oldPlugin.esl:
            if newPlugin.esl:
                self._detected_esl_flag_added = True
                return "Plugin is now flagged as an ESL"
            else:
                self._detected_esl_flag_removed = True
                return "Plugin is no longer flagged as an ESL"
        elif newPlugin.master != oldPlugin.master:
            if newPlugin.master:
                self._detected_master_flag_added = True
                return "Plugin has been flagged as a Master File"
            elif newPlugin.priority != oldPlugin.priority:
                self._detected_master_flag_removed = True
                return "Plugin is no longer flagged as a Master File"
        else:
            return False
    
    def _scanLoadOrder(self) -> List[LOUG_Plugin]:
        loug_list: List[LOUG_Plugin] = []
        plugin_list: Sequence[str] = self._pluginList.pluginNames()
        
        for plugin in plugin_list:
            loug_plugin = LOUG_Plugin()
            loug_plugin.name = plugin
            loug_plugin.display_name = Path(plugin).name
            loug_plugin.extension = Path(plugin).suffix
            loug_plugin.origin = self._pluginList.origin(plugin)
            loug_plugin.priority = self._pluginList.loadOrder(plugin)
            loug_plugin.esl = self._pluginList.isLightFlagged(plugin)
            loug_plugin.master = self._pluginList.isMasterFlagged(plugin)
            if self._pluginList.state(plugin) == mobase.PluginState.ACTIVE:
                loug_list.append(loug_plugin)

        return loug_list
    
    def name(self) -> str:
        return self.NAME
    
    def author(self) -> str:
        return self.AUTHOR
    
    def description(self) -> str:
        return self.DESCRIPTION

    def fullDescription(self, key):
        offenderList: List[LOUG_Plugin] = self._changed_plugin_list.values()
        offenseTemplate: str = "<i><b><span style=\"color: darkgoldenrod\">{1}</span></b> <span style=\"color: lightslategray\">[{0}]</span></i> - <b><span style=\"color: indianred\">{2}</span></b>"
        offenderList = [offenseTemplate.format(loug_plugin.origin, loug_plugin.display_name, loug_plugin.problem_desc) for loug_plugin in offenderList]
        offenders = "<p style=\"margin-left: 10px; margin-top: 10px; margin-bottom: 0px;\">•  " + ("<br />  •  ".join(offenderList)) + "</p>"
        outputString = "One or more plugins have changed the ESL load order.{0}".format(offenders)
        outputString += "<br />"
        outputString += "<b>Recommended Actions:</b>"
        outputString += "<p style=\"margin-left: 10px; margin-top: 10px; margin-bottom: 0px;\">"

        if self._detected_master_flag_added or self._detected_master_flag_removed:
            outputString += "  •  <b><span style=\"color: indianred\">Master Flag Changes</span></b> - Plugins with an updated Master flag could potentially have their load order forcibly changed."
            outputString += "<div style=\"margin-left: 8px; margin-top: 0px; margin-bottom: 0px;\">"
            outputString += "   <b style=\"color: lightseagreen;\">Recommended Fix:</b>"
            outputString += "   Revert to the previous version until you are ready to start a new game."
            outputString += "   Alternatively you could manually remove the master flag from the plugin but be warned," 
            outputString += "   Mod Authors flag plugins as masters for very good reasons and subverting that may lead to unforeseen issues in your game."
            outputString += "</div>"
        
        if self._detected_esl_flag_added:
            outputString += "  •  <b><span style=\"color: indianred\">ESL flag added to existing '.esp' file</span></b> - For ESP plugins recently converted to an ESL"
            outputString += "<div style=\"margin-left: 8px; margin-top: 0px; margin-bottom: 0px;\">"
            outputString += "   <b style=\"color: lightseagreen;\">Recommended Fix:</b>"
            outputString += "   If the plugin was already in your load order it is recommended to first"
            outputString += "   uninstall the mod and clean your save with ReSaver before loading in the new version of the plugin."
            outputString += "   Then ensure that the new ESL plugin is placed at the bottom of the load order so that"
            outputString += "   it does not disrupt the Mod Index of any ESLs previously placed below it in the load order." 
            outputString += "   Mod Authors flag plugins as masters for very good reasons and subverting that may lead to unforeseen issues in your game."
            outputString += "</div>"
        
        if self._detected_esl_flag_removed:
            outputString += "  •  <b><span style=\"color: indianred\">ESL flag removed from a '.esp' file</span></b> - For ESP plugins that have their ESL flags removed"
            outputString += "<div style=\"margin-left: 8px; margin-top: 0px; margin-bottom: 0px;\">"
            outputString += "   <b style=\"color: lightseagreen;\">Recommended Fix:</b>"
            outputString += "   Because there is no longer an ESL in that load order spot, it is recommended to create"
            outputString += "   an empty .esp plugin with an ESL flag. Then place it in the same load order spot as the previous plugin."
            outputString += "   This will ensure that the Mod Index of any ESLs previously placed below it in the load order are not disrupted."
            outputString += "   Since the updated ESP plugin is no longer taking an ESL Mod Index slot you should be able to place it anywhere in your load order."
            outputString += "   It is still highly recommended though to uninstall the mod and clean your save with ReSaver before loading in the new version of the plugin."
            outputString += "</div>"
        
        if self._detected_changed_extension:
            outputString += "  •  <b><span style=\"color: indianred\">ESL Plugin file extension changed</span></b> - For plugins that have had their file extension changed to '.esl'"
            outputString += "<div style=\"margin-left: 8px; margin-top: 0px; margin-bottom: 0px;\">"
            outputString += "   <b style=\"color: lightseagreen;\">Recommended Fix:</b>"
            outputString += "   Plugins with the '.esl' extension are forcibly placed at the top of the load order."
            outputString += "   It can be easy to miss this type of change but it can completely ruin a save file. In some cases you won't even be able to load the save"
            outputString += "   The forced load order placement of a '.esl' is the only real difference between a file with the '.esl' extension and a '.esp' extension."
            outputString += "   If the plugin was already in your load order and flagged as an ESL the best way to save your save is to manually rename the file back to '.esp'a"
            outputString += "   and place it back in the same load order spot as it previously was."
            outputString += "</div>"
        
        if self._detected_missing:
            outputString += "  •  <b><span style=\"color: indianred\">ESL plugin uninstalled/deleted</span></b> - For plugins that have been removed from the load order"
            outputString += "<div style=\"margin-left: 8px; margin-top: 0px; margin-bottom: 0px;\">"
            outputString += "   <b style=\"color: lightseagreen;\">Recommended Fix:</b>"
            outputString += "   Removing or uninstalling a mod that uses an ESL plugin will cause a Mod Index change for any ESLs previously placed below it in the load order."
            outputString += "   If you are not planning on reinstalling the mod then it is recommended to create an empty .esp plugin with an ESL flag."
            outputString += "   Then place it in the same load order spot as the previous plugin. This will ensure that the Mod Index of any ESLs previously placed below it in the load order are not disrupted."
            outputString += "   Maintaining consistent Mod Indexes for the remaining ESLs is vital to preventing issues with your current saves."
            outputString += "</div>"

        if self._detected_new:
            outputString += "  • <b><span style=\"color: indianred\">New ESL plugins with the '.esl' extension</span></b> - For new plugins with the '.esl' extension that have been added to the load order"
            outputString += "<div style=\"margin-left: 8px; margin-top: 0px; margin-bottom: 0px;\">"
            outputString += "   <b style=\"color: lightseagreen;\">Recommended Fix:</b>"
            outputString += "   ESL plugins with the '.esl' file extension are forcibly placed at the top of the load order."
            outputString += "   It can be easy to miss this type of change but it can completely ruin a save file."
            outputString += "   The forced load order placement of a '.esl' is the only real difference between a file with the '.esl' extension and a '.esp' extension."
            outputString += "   If you wish to continue with your current save then it is recommended to manually rename the file to use the '.esp' file extension."
            outputString += "   You should then place the new ESL plugin at the bottom of your load order under any currently installed ESL flagged plugins."
            outputString += "   This will ensure Mod Index consistency for any ESLs currently in your load order."
            outputString += "</div>"
        
        if self._detected_esl_priority_shift:
            outputString += "  • <b><span style=\"color: indianred\">An ESL plugin(s) changed priority</span></b> - For ESL plugins that have been moved in the load order"
            outputString += "<div style=\"margin-left: 8px; margin-top: 0px; margin-bottom: 0px;\">"
            outputString += "   <b style=\"color: lightseagreen;\">Recommended Fix:</b>"
            outputString += "   Move the ESL file back to its previous priority. Or if it is a new plugin make sure it is placed below {0}({1}).".format(self._highest_stable_priority_plugin_name, self._highest_stable_priority)
            outputString += "   Changing the load order of an ESL mid-save will damage the save because it shifts the Mod Index of the plugin"
            outputString += "   and any plugins that are loaded after its new load order position."
            outputString += "</div>"
        
        outputString += "</p><br />"

        outputString += "<b>Last Resort Options:</b>"
        outputString += "<p style=\"margin-left: 8px; margin-top: 10px; margin-bottom: 0px;\">"
        outputString += "  •  Revert any recent installs/updates/uninstalls and continue playing on the previous version of the mod(s).<br />"
        outputString += "  •  Start a new game with the updated plugins and load order.<br />"
        outputString += "</p>"

        outputString += "<i><b>Why is this an issue?</b></i>"
        outputString += "<p style=\"margin-left: 10px; margin-top: 10px; margin-bottom: 0px;\"><i>" 
        outputString += " If an ESL flagged plugin adds new items or forms to the game these form ids are baked into your save file using the ESLs current Mod Index."
        outputString += " Because of how these FormIDs are managed, any changes to the ESL plugins Mod Index mid-save could put your save file at risk of being severely damaged."
        outputString += " Changes to your load order of ESL plugins can cause the game to attempt load the wrong data for a FormID and corrupt your save."
        outputString += " Instead of equipping your fancy modded princess peach axe, you might crash your game instead because the game has the wrong"
        outputString += " referenced FormID and the id in the save is now pointing to a giant stone archway from a completely unrelated mod."
        outputString += "</i></p><br />"
        outputString += "<i>Non-ESL flagged plugins are not affected by this issue.</i>"
        
        return outputString
    
    def shortDescription(self, key) -> str:
        return self.ERROR_MESSAGE

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.ALPHA)
    
    def isActive(self) -> bool:
        return self._organizer.pluginSetting(self.name(), "enabled")

    def settings(self) -> List[mobase.PluginSetting]:
        return [
            mobase.PluginSetting("enabled", "enable this plugin", True),
            mobase.PluginSetting("report_on_esl_moved", "report manual load order changes", False),
            mobase.PluginSetting("more_accurate_load_order_moves", "*Experimental* adjusts what is considered the \"safe\" priority to move plugins above to ignore the lowest ordered ESLs that do not add any new forms to the game.", False)
        ]

    def hasGuidedFix(self, key):
        return False

    def startGuidedFix(self, key):
        pass

    def activeProblems(self) -> (list[int] | list):
        if len(self._changed_plugin_list) > 0:
            return [0]
        else:
            return []

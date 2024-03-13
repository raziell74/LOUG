# LOUG - Load Order Update Guard

A flexible MO2 python plugin that will warn against save breaking changes to ESL load order changes.
LOUG will help protect from changes to ESL's from mod updates or new mods that would force the load order of your ESL flagged plugins to change. 

## Installation

In your MO2 installation directory, extract the LOUG into the base directory of your MO2 folder.

## Updating the "stable" load order

Everytime you run skyrim LOUG will save the load order as the current 'stable' load order. So if you are getting warnings and they aren't valid (this is still in alpha after all) running the game will reset and assume you are fine with your load order as is. 

## Why is ESL load order important?

If an ESL flagged plugin adds new items or forms to the game these form ids are baked into your save file using the ESLs current Mod Index.
Because of how these FormIDs are managed, any changes to the ESL plugins Mod Index mid-save could put your save file at risk of being severely damaged.
Changes to your load order of ESL plugins can cause the game to attempt load the wrong data for a FormID and corrupt your save.
Instead of equipping your fancy modded princess peach axe, you might crash your game instead because the game has the wrong
referenced FormID and the id in the save is now pointing to a giant stone archway from a completely unrelated mod.

## Usage

The first time MO2 is loaded with LOUG the plugin load order is parsed and calculated. When the game is launched from MO2, LOUG will assume the load order is stable and save it to memory. 
After that any changes to ESL load order that would cause save game corruption will be sent to MO2 as a warning. 

## Beth Structs

LOUG comes packaged with a slightly customized version of BETH Structures which it uses to decode the header of an ESP/ESM/ESL to determine the flags and types of changes contained in the plugin.

The Beth Structures library was altered so that it will not read in the plugins content in its entirety but insted only read in the specified data ranges to get header information. This was a needed optimization as some plugin sizes could cause a very long read time, and LOUG needs to be snappy and quick.

The primary usage of Beth Structs is to detect the types of changes an ESL introduces to determine the lowest possible priority ESL that can be moved. If you have several ESL plugins at the bottom of your load order that do not add any new forms to the game and only update forms from other plugins (like patches) or the ESl is just an empty dummy plugin that adds nothing to the game engine. These types of plugins can remain chagne their load order without any corruption being intoduced to your save file. Because of this it is important to keep these kinds of plugins at the bottom of your load order so the patchs to forms can properly be applied. LOUG will find the lowest priority ESL that adds new forms to the game so that adding new plugins or moving around plugins under the lowest priority ESl can be done without reporting false positive warnings to MO2. 

As an example say you have 6 ESl flagged plugins at the bottom of your load order, some 3 are patches, 1 is an empty dummy plugin, 1 is a normal esp without an ESL flag and one adds a new armor to the game.

- DummyPlugin.esp [esl]
- New Armor.esp [esl]
- Patch1.esp [esl]
- NormalPlugin.esp
- NormalPluginPatch.esp [esl]
- SuperPatch.esp [esl]

In this case LOUG will warn if any new ESL plugins are placed above the "New Armor.esp" plugin. Because the patches do not add nay new forms to the game they can be moved lower without causing any damage to your game save. 
This is also a good example because Normal non-esl plugins can be moved anywhere in your load order without any threat of save corrption. So you could move the "NormalPlugin.esp" above "DummyPlugin.esp" and LOUG will not report any issues.

# Types of ESL issues

LOUG is set up to detect various different scenarios in which your save could be corrupted by changes to ESL flagged plugins. 

## Master Flag detection

Flagging a plugin as a "master" will force it to load higher than it normally would as a normal ESP. Some mod authors change the master flag for increased stability or to ensure their mod plugin is loaded higher. 
If an ESL that you already had in your load order is suddenly flagged as a "master" or the "master" flag was removed this can cause the plugin to change its load order and will cause you issues in on-going saves.

To fix this, you can either manually remove the "master" flag in xEdit or the Creation Kit or start a new game with the new master plugin. If you change the plugin manually you should go through any other plugins that are dependencies on the changed plugin and ensure that they are loaded after other wise the game will foribly change the load orders for them but those changes cannot be seen in MO2 and happen behind the scenes within the game engine.

## ESL Flag added

If a plugin that was previously not flagged as an ESL suddenly gets an ESL flag any ESL plugins that were previously loaded beneath the updated plugin will have their Mod Index's shifted down. As stated previously any change to an ESL's mod index in an on going save will cause corruption. 

To fix this you can manually remove the ESL flag in xEdit or the Creation Kit. But if you'd like to keep the ESL flagged update, you should properly uninstall the mod and clean your save file using ReSaver. Then enable the mod again with the new ESL plugin placed at the bottom of your load order.

## Plugin Extension Changes

Plugins with the '.esl' extension are forcibly placed at the top of the load order.
It can be easy to miss this type of change but it can completely ruin a save file. In some cases you won't even be able to load the save
The forced load order placement of a '.esl' is the only real difference between a file with the '.esl' extension and a '.esp' extension.
If the plugin was already in your load order and flagged as an ESL the best way to save your save is to manually rename the file back to '.esp'a
and place it back in the same load order spot as it previously was.

## Missing or Removed Plugins

Removing or uninstalling a mod that uses an ESL plugin will cause a Mod Index change for any ESLs previously placed below it in the load order.
If you are not planning on reinstalling the mod then it is recommended to create an empty .esp plugin with an ESL flag.
Then place it in the same load order spot as the previous plugin. This will ensure that the Mod Index of any ESLs previously placed below it in the load order are not disrupted.
Maintaining consistent Mod Indexes for the remaining ESLs is vital to preventing issues with your current saves.

## New Plugins with the .esl Extension

ESL plugins with the '.esl' file extension are forcibly placed at the top of the load order.
It can be easy to miss this type of change but it can completely ruin a save file.
The forced load order placement of a '.esl' is the only real difference between a file with the '.esl' extension and a '.esp' extension.
If you wish to continue with your current save then it is recommended to manually rename the file to use the '.esp' file extension.
You should then place the new ESL plugin at the bottom of your load order under any currently installed ESL flagged plugins.
This will ensure Mod Index consistency for any ESLs currently in your load order.

## ESL Priority Shift

Changing an ESL flagged plugins load order / priority will cause various issues and corruption for on going game saves.
It is recommended to move the ESL file back to its previous priority. 
Or if it is a new plugin make sure it is placed at the bottom of your load order.

# Last Resort options

Revert any recent installs/updates/uninstalls and continue playing on the previous version of the mod(s).
Or Start a new game with the updated plugins and load order.


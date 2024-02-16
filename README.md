# LOUG

Load Order Update Guard. A flexible MO2 python plugin that will warn against save breaking changes to ESL load order changes.

LOUG will help protect from changes to ESL's from mod updates or new mods that would force the load order of your ESL flagged plugins to change. 

## Why is ESL load order important?

If an ESL flagged plugin adds new items or forms to the game these form ids are baked into your save file using the ESLs current Mod Index.
Because of how these FormIDs are managed, any changes to the ESL plugins Mod Index mid-save could put your save file at risk of being severely damaged.
Changes to your load order of ESL plugins can cause the game to attempt load the wrong data for a FormID and corrupt your save.
Instead of equipping your fancy modded princess peach axe, you might crash your game instead because the game has the wrong
referenced FormID and the id in the save is now pointing to a giant stone archway from a completely unrelated mod.

## Installation

In your MO2 installation directory, drop the LOUG files into your /plugins folder. 

LOUG comes packaged with a slightly customized version of BETH Structures which it uses to decode the header of an ESP/ESM/ESL to determine the flags and types of changes contained in the plugin.

The Beth Structures library was altered so that it will not read in the plugins content in its entirety but insted only read in the specified data ranges to get header information. This was a needed optimization as some plugin sizes could cause a very long read time, and LOUG needs to be snappy and quick.

## Usage

The first time MO2 is loaded with LOUG the plugin load order is parsed and calculated. When the game is launched from MO2, LOUG will assume the load order is stable and save it to memory. 
After that any changes to ESL load order that would cause save game corruption will be sent to MO2 as a warning. 

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


Preferences Editor
==================

This is an editor, which allows you to browse and edit sublime preferences/settings, 
without writing JSON files (at least in most cases).

Default setting's comment is displayed as help text, if present.

There is an instant preview in current view which changing setting.


Menu Items
----------

**Preferences → Edit Settings...**
    You will get displayed a list of preferences to edit.  If you select one, you will
    be presented the whole set of current preferences for selected view (Preferences, 
    Distraction Free, This View, Some specific Syntax).


Command Palette
---------------

**Edit Preferences: Edit Settings…**
    See **Preferences → Edit Settings...**.

**Edit Preferences: Edit Settings — All**
    You can edit a setting selecting it from all settings (Preferences, Distraction Free,
    Current Syntax, Special Settings, but not all syntax-specific settings).

**Edit Preferences: Edit Settings — Preferences**
    Shortcut to edit Preferences.

**Edit Preferences: Edit Settings — Distraction Free**
    Shortcut to edit Distraction Free Preferences.

**Edit Preferences: Edit Settings — Current Syntax**
    Shortcut to edit Preferences for Current Syntax


Changes
-------

2013-12-26 23:46 CET
    - Fix instant preview for text input.

2013-12-26 23:37 CET
    - Added instant preview in current view.  This is cool for e.g. changing
      color schemes.

2013-12-26 22:55 CET
    - **Preferences → Edit Settings...** now presents a list of preferences,
      which are editable.  Here you can edit preferences for different points 
      of view.

    - Added **This View** to list of editable preferences, which changes 
      preferences for current view.  It does not include settings, which are
      dynamically set by packages.


2013-12-25 16:28 CET
    - Default for naming current syntax is now "Current Syntax", you can turn
      on the real syntax name by setting ``preferences_editor_use_syntax_name``
      to ``true``.

    - Setting type (if it is the default or a setting overridden by user) is
      not displayed per default anymore.  You can turn this advanced setting
      on by setting ``preferences_editor_indicate_default_settings`` to 
      ``true``.

    - There are new commands added to command palette.

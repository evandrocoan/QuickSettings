Preferences Editor
==================

This is a editor, which allows you to browse and edit sublime preferences, 
without writing JSON files (at least in most cases).

In browser you see a list of preferences in form::

    <name>/<type>/<key>
    <value>

``<name>``
    Name of preference file.  Please note that sublime preferences are
    available under three namespaces:

    - Preferences — normal preferences
    - Distraction Free — preferences for distraction free mode
    - <current syntax name> — syntax specific preferences.

``<type>``
    This is either **User** or **Default**.  If it is **User** this value has
    been overridden by user, if it is **Default**, this is the default value.

``<key>``
    Key of setting.

``<value>``
    Value of setting written in JSON.

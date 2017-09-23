
import os
import re
import sys
import pprint

import sublime
import sublime_plugin

def assert_path(module):
    """
        Import a module from a relative path
        https://stackoverflow.com/questions/279237/import-a-module-from-a-relative-path
    """
    if module not in sys.path:
        sys.path.append( module )

# Import the debug tools
assert_path( os.path.join( os.path.dirname( os.path.dirname( os.path.realpath( __file__ ) ) ), 'PythonDebugTools' ) )

# Import the debugger
from debug_tools import Debugger

# Enable debug messages: (bitwise)
#
# 0   - Disabled debugging.
# 1   - Basic logging messages.
# 2   - AgentPlayer       class' notices.
# 4   - StickIntelligence class' notices.
#
# 127 - All debugging levels at the same time.
log = Debugger( 127, "PreferencesEditor", "DebugLog.txt" )

log.clear_log_file()
log( 1, "Debugging" )
log( 1, "..." )
log( 1, "..." )

standard_settings_names = ( "Distraction Free", "Current Syntax", "Current Project", "This View" )
standard_settings_types = ('default', 'default_'+sublime.platform())


def show_quick_panel(view, options, done, highlighted=None):
    sublime.set_timeout(lambda: view.window().show_quick_panel(options, done, 0, -1, highlighted), 10)


def json_list(x):

    try:
        d = sublime.decode_value(x)
        #sys.stderr.write("d: %s\n" % d)

    except Exception as e:
        log( 1, "cannot decode %s", repr(x), exc_info=1 )
        raise ValueError(str(e))

    if not isinstance(d, list):
        raise ValueError("Expected a JSON list")

    return d


def json_dict(x):

    try:
        d = sublime.decode_value(x)
        #sys.stderr.write("d: %s\n" % d)

    except Exception as e:
        log(1, "cannot decode %s", repr(x), exc_info=1)
        raise ValueError(str(e))

    if not isinstance(d, dict):
        raise ValueError("Expected a JSON dictionary")

    return d


def show_input(view, caption, initial, on_done=None, on_change=None, on_cancel=None, on_load=None):
    window = view.window()

    def do_input():
        _initial = initial

        if not isinstance(_initial, str):
            _initial = sublime.encode_value(_initial)

        input_view = window.show_input_panel(caption, _initial, on_done=on_done, on_change=on_change, on_cancel=on_cancel)

        if on_load:
            on_load(input_view)

    sublime.set_timeout(do_input, 10)


def get_descriptions(data):
    r"""get descriptions from preferences string

    extract descriptions from passed ``data``.

    :param data:
        string containing json preferences file.

    This is only a rough parser and will fetch also keys from
    sub-dictionaries.  Calling function is responsible to
    select correct data.
    """
    COMMENT_RE = re.compile(r"(?s)\s*//\s?(.*)")
    COMMENT_RE2 = re.compile(r'''(?xs)
        (?:
            "(?:[^"\\]|\\.)*"
            | (?:(?!//)[^"])
        )+
        (//.*)
        ''')
    COMMENT_START = re.compile(r"^\s*/\*(.*)")
    COMMENT_END   = re.compile(r"(.*)\*/")
    KEY_RE     = re.compile(r'\s*"([^"]+)"\s*:')
    INDENT_RE = re.compile(r'^\s*')

    description = {}
    comment = ""
    is_comment = False

    for line in data.splitlines(1):

        if is_comment:
            m = COMMENT_END.search(line)

            if m:
                comment += m.group(1).rstrip()+"\n"
                is_comment = False

            else:
                comment += line

            continue

        m = COMMENT_START.match(line)

        if m:
            is_comment = True
            comment += m.group(1).rstrip()+"\n"
            continue

        m = COMMENT_RE.match(line)

        if m:
            s = m.group(1)

            if not s: s = "\n"
            comment += s
            continue

        m = COMMENT_RE2.match(line)

        if m:
            #sys.stderr.write("line1: %s\n" % (repr(line)))
            line = line[:m.start(1)].rstrip()+"\n"
            #sys.stderr.write("line2: %s\n" % (repr(line)))

        if not line.strip(): # empty line resets current comment
            comment = ""
            continue

        m = KEY_RE.match(line)

        if m:

            while comment.startswith('\n'):
                comment = comment[1:]

            indent = INDENT_RE.match(comment).group(0)

            if indent:
                comment = ''.join([ l.startswith(indent) and l[len(indent):] or l for l in comment.splitlines(1) ])
            description[m.group(1)] = {"description": comment.replace("\r", "") or "No help available :("}
            comment = ""

    return description


# resolution order of settings
#    Packages/Default/Preferences.sublime-settings
#    Packages/Default/Preferences (<platform>).sublime-settings
#    Packages/User/Preferences.sublime-settings
#    <Project Settings>
#    Packages/<syntax>/<syntax>.sublime-settings
#    Packages/User/<syntax>.sublime-settings
#    <Buffer Specific Settings>

def get_current_syntax(view, syntax=None):
    current_syntax = None
    settings = view.settings()

    if syntax:
        current_syntax = syntax

    elif settings.has('syntax'):
        current_syntax = settings.get('syntax')
        current_syntax = os.path.basename(current_syntax).rsplit('.', 1)[0]

    return current_syntax


def save_preference(view, name, key, value, type=None, default=None):

    if name == "This View":
        settings = view.settings()
        settings.set(key, value)
        return

    if name == "Current Project":
        data = view.window().project_data()

        if 'settings' not in data:
            data['settings'] = {}

        data['settings'][key] = value

        if value == default:

            if type != 'Default':

                if key in data['settings']:
                    del data['settings'][key]

        view.window().set_project_data(data)
        return

    if name != "Preferences":

        if sublime.find_resources('%s.tmLanguage' % name):
            settings = sublime.load_settings('Preferences.sublime-settings')
            default  = settings.get(key)


        if sublime.find_resources('%s.hidden-tmLanguage' % name):
            settings = sublime.load_settings('Preferences.sublime-settings')
            default  = settings.get(key)

    settings = sublime.load_settings(name+'.sublime-settings')

    if value == default:

        if type != 'Default':
            settings.erase(key)

        else:
            settings.set(key, value)

    else:
        settings.set(key, value)

    sublime.save_settings(name+'.sublime-settings')


def load_preferences():
    log( 2, "load__preferences" )

    # for syntax specific, we need syntax names
    language_files = sublime.find_resources("*.tmLanguage")
    syntax_names = []

    for f in language_files:
        syntax_name = os.path.basename(f).rsplit('.', 1)[0]

        log( 2, "load__preferences, syntax_name: " + syntax_name )
        syntax_names.append( syntax_name )

    preferences = {}
    preferences_files = sublime.find_resources("*.sublime-settings")

    for preference_file in preferences_files:

        log( 2, "load__preferences, preference_file: {0}".format( preference_file ) )
        preference_name = preference_file.replace("Packages/", "").replace("/", "_")
        preference_name = preference_name.replace(" ", "_").rsplit('.', 1)[0]

        log( 2, "load__preferences, preference_name: {0}".format( preference_name ) )
        platform = "any"

        if preference_name[-5:].lower() == "(osx)":
            preference_name = preference_name[:-6]
            platform = "osx"

        elif preference_name[-9:].lower() == "(windows)":
            preference_name = preference_name[:-10]
            platform = "windows"

        elif preference_name[-7:].lower() == "(linux)":
            preference_name = preference_name[:-8]
            platform = "linux"

        log( 2, "load__preferences, preference_name: {0}".format( preference_name ) )

        if "/User/" in preference_file:
            type = "user"

        else:
            type = "default"

        if platform != "any":
            type = type+"_"+platform

        if preference_name not in preferences:
            preferences[preference_name] = {}

        syntax = None

        if 0 and preference_name in syntax_names:
            type = "syntax_"+type
            syntax = preference_name
            preference_name = "Preferences"

            if type not in preferences[preference_name]:
                preferences[preference_name][type] = {}

            if syntax not in preferences[preference_name][type]:
                preferences[preference_name][type][syntax] = {}

            preference = preferences[preference_name][type][syntax]

        else:
            if type not in preferences[preference_name]:
                preferences[preference_name][type] = {}

            preference = preferences[preference_name][type]

        #sys.stderr.write("preference_name: %s, type: %s, syntax: %s\n" % (preference_name, type, syntax))
        preference_data = sublime.load_resource(preference_file)

        if preference_data:
            preference_settings = {}

            try:
                #import spdb ; spdb.start()
                description = get_descriptions(preference_data)

                #sys.stderr.write("preference_data: %s\n" % preference_)
                preference_data = sublime.decode_value(preference_data)

                for setting_name, setting_value in preference_data.items():

                    if setting_name not in description:
                        preference_settings[setting_name] = {"description": "No help available :("}

                    else:
                        preference_settings[setting_name] = description[setting_name]

                    preference_settings[setting_name]['value'] = setting_value

            except:
                log(1, "Error reading %s (preference_data is %s)", preference_file, preference_data)

            preference.update(preference_settings)

    return preferences


def load_syntax_names(get_specials=False):
    language_files = sublime.find_resources("*.tmLanguage")
    syntax_names = []

    reStructuredText_syntax = None
    plaintext_syntax = None

    for f in language_files:

        if "restructuredtext" in f.lower():
            reStructuredText_syntax = f

        if "plain text" in f.lower():
            plaintext_syntax = f

        syntax_names.append(os.path.basename(f).rsplit('.', 1)[0])

    #sys.stderr.write("plain text syntax: %s\n" % plaintext_syntax)
    #sys.stderr.write("reST syntax: %s\n" % reStructuredText_syntax)

    if get_specials:
        return syntax_names, plaintext_syntax, reStructuredText_syntax

    return syntax_names


# commands are
#
# Edit Preferences        --> User
# Edit Syntax Preferences --> User
#

class EditPreferencesCommand(sublime_plugin.WindowCommand):

    # meta.<setting_name>: {
    #      "widget": "select"
    #      "value": [ "", [caption, value] ]
    #      "validate": "Package Name.module.function"
    #      "tip": "text"      in status bar
    #      "help": "Packages/..." or "text"
    # }
    #

    #def bool_widget(self, ):

    def widget_select_bool(self, pref_editor, key_path, value=None, default=None, validate=None, preview=True):
        # true_string = "True"

        # true_flags = []
        # if value is True:
        #   true_flags

        # if value is True:
        #   true_string += " (current"
        #   if default is True:
        #       true_string += ", default"
        #   true_string += ")"

        options = ["BACK (Open the Last Menu)", "true", "false"]

        name    , type     , key = self.convertSettingPathToNameTypeAndKey(key_path)
        key_path, key_value      = pref_editor.getPreferencesPathAndValue(name, key)
        view                     = pref_editor.window.active_view()

        def done(index):
            view.erase_status("preferences_editor")

            if index < 0:
                self.view.settings().set(key, key_value['value'])
                return self.shutdown()

            elif index == 0:
                self.view.settings().set(key, key_value['value'])

            elif index == 1:
                pref_editor.set_pref_value(key_path, True, default)

            else:
                pref_editor.set_pref_value(key_path, False, default)

            self.preferences_selector()

        def highlight(index):

            if index == 0:
                self.view.settings().set(key, True)

            else:
                self.view.settings().set(key, False)

        # for op in options: log( 2, "op: {0}".format( op ) )
        view.set_status("preferences_editor", "Set %s" % key_path)
        show_quick_panel(view, options, done, highlight)

    def widget_select(self, pref_editor, key_path, value=None, default=None, validate=None, values=[]):
        settings = self.view.settings()

        name, type, key = self.convertSettingPathToNameTypeAndKey(key_path)
        key_value = pref_editor.getPreferencesPathAndValue(name, key)[1]
        view_specific = settings.has(key) and settings.get(key) != key_value['value']

        CURRENT = None

        if settings.has(key):
            CURRENT = settings.get(key)

        commands = None

        if isinstance(values[0], dict):
            options = [ x['caption'] for x in values ]
            commands = [ x.get('command') for x in values ]
            args = [ x.get('args', {}) for x in values ]
            types = [ x.get('type', 'window') for x in values ]
            values = [ x.get('value') for x in values ]

        else:
            options = [ str(x) for x in values ]

        view = pref_editor.window.active_view()

        def done(index):
            view.erase_status("preferences_editor")

            if view_specific:
                self.view.settings().set(key, CURRENT)

            else:
                self.view.settings().erase(key)

            if index < 0:
                return self.shutdown()

            # if command is set, let the command handle this preference
            if commands:

                if commands[index]:
                    context = view

                    if types[index] == "window":
                        context = view.window()

                    sublime.set_timeout(lambda: context.run_command(commands[index], args[index]), 10)
                    return

            pref_editor.set_pref_value(key_path, values[index], default)

        def highlight(index):
            log(1, "setting %s to %s", key, values[index])
            settings.set(key, values[index])

        view.set_status("preferences_editor", "Set %s" % key_path)
        show_quick_panel(view, options, done, highlight)

    def widget_multiselect(self, pref_editor, key_path, value=None, default=None, validate=None, values=None):
        view = pref_editor.window.active_view()

        if isinstance(values[0], str):
            values = [ dict(caption=v, value=v) for v in values ]

        other = []

        def do_add_option():
            options = [ v.get('caption', str(v.get('value')))
                for v in values if v['value'] not in value ]

            def done(index):

                if index < 0: return self.shutdown()
                value.append(other[index])
                do_show_panel()

            show_quick_panel(view, options, done)

        def do_remove_option():
            options = \
            [
                v.get('caption', str(v.get('value')))
                for v in values if v['value'] in value
            ]

            def done(index):

                if index < 0:
                    return self.shutdown()

                value.remove(value[index])
                do_show_panel()

            show_quick_panel(view, options, done)


        def do_show_panel():
            other[:] = [ v['value'] for v in values if v['value'] not in value ]

            options = \
            [
                ["Set Value", sublime.encode_value(value, False)],
                ["Add Option", "From: "+sublime.encode_value(other, False)],
                ["Remove Option", "From:"+sublime.encode_value(value, False)]
            ]

            def done(index):
                view.erase_status("preferences_editor")

                if index < 0:
                    return self.shutdown()

                if index == 0:
                    pref_editor.set_pref_value(key_path, value, default)

                if index == 1:
                    do_add_option()

                if index == 2:
                    do_remove_option()

            view.set_status("preferences_editor", "Set %s" % key_path)
            show_quick_panel(view, options, done)

        do_show_panel()

    def widget_select_resource(self, pref_editor, key_path, value=None, default=None, validate=None,
                               find_resources="", strip_path=True, strip_suffix=True):

        resources = sublime.find_resources(find_resources)
        name, type, key = self.convertSettingPathToNameTypeAndKey(key_path)

        settings = self.view.settings()
        key_value = pref_editor.getPreferencesPathAndValue(name, key)[1]
        view_specific = settings.has(key) and settings.get(key) != key_value['value']

        CURRENT = None

        if settings.has(key):
            CURRENT = settings.get(key)

        options = resources

        if strip_path:
            options = [ os.path.basename(r) for r in options ]

        if strip_suffix:
            options = [ os.path.splitext(r)[0] for r in options ]

        view = pref_editor.window.active_view()

        def done(index):
            view.erase_status("preferences_editor")

            if view_specific:
                settings.set(key, CURRENT)

            else:
                settings.erase(key)

            if index < 0:
                return self.shutdown()

            pref_editor.set_pref_value(key_path, resources[index], default)

        def highlight(index):
            log(1, "setting %s to %s", key, resources[index])
            settings.set(key, resources[index])

        view.set_status("preferences_editor", "Set %s" % key_path)
        show_quick_panel(view, options, done, highlight)


    def widget_input(self, pref_editor, key_path, value=None, default=None, validate=None):
        name, type, key = self.convertSettingPathToNameTypeAndKey(key_path)

        view = self.view
        view.set_status("preferences_editor", "Set %s" % key_path)

        settings = view.settings()
        key_value = pref_editor.getPreferencesPathAndValue(name, key)[1]
        view_specific = settings.has(key) and settings.get(key) != key_value['value']

        CURRENT = None

        if settings.has(key):
            CURRENT = settings.get(key)

        def _undo_view_settings():

            if view_specific:
                settings.set(key, CURRENT)

            else:
                settings.erase(key)

        def done(value):
            _undo_view_settings()

            try:
                value = validate(value)
                pref_editor.set_pref_value(key_path, value, default)

            except ValueError as e:
                sublime.error_message("Invalid Value: %s" % e)

            view.erase_status("preferences_editor")

        def change(value):

            try:
                v = validate(value)
                view.settings().set(key, v)
                log(1, "set %s to %s", key, v)

            except ValueError as e:
                sublime.status_message("Invalid Value: %s" % e)

        def cancel():
            _undo_view_settings()
            view.erase_status("preferences_editor")

        view.set_status("preferences_editor", "Set %s" % key_path)
        show_input(self.view, key, value, done, change, cancel)


    def convertSettingPathToNameTypeAndKey(self, key_path):
        name = self.name
        type = "User"

        if key_path.count('/') == 2:
            name, type, key = key_path.split('/')

        elif key_path.count('/') == 1:
            name, key = key_path.split('/')

        else:
            key = key_path

        return name, type, key


    def set_pref_value(self, key_path, value, default=None):
        name, type, key = self.convertSettingPathToNameTypeAndKey(key_path)

        if name == "Current Syntax":
            name = self.current_syntax

        save_preference(self.view, name, key, value, default=default, type=type)
        self.options[self.index][1] = sublime.encode_value(value, False)

        #settings = sublime.load_settings(name+'.sublime-settings')
        #settings.set()

        #
        # settings = sublime.load_settings(preferences_filename())
        # ignored = settings.get('ignored_packages')
        # if not ignored:
        #     ignored = []
        # for package in packages:
        #     if not package in ignored:
        #         ignored.append(package)
        #         disabled.append(package)
        # settings.set('ignored_packages', ignored)
        # sublime.save_settings(preferences_filename())


    def make_pref_rec(self, name, type, key, value):
        if self.settings_indicate_type and self.settings_indicate_name:
            return "%s/%s/%s" % (name, type, key), value

        elif self.settings_indicate_type:
            return "%s/%s" % (type, key), value

        elif self.settings_indicate_name:
            return "%s/%s" % (name, key), value

        else:
            return key, value


    def getPreferencesPathAndValue(self, name, key):
        """
            @key    the name of the setting
            @name   the name of the setting's file on self.preferences[name]

            @return key_path, key_value:

                    key_path:  Default/wrap_width
                    key_value: {'value': True, 'description': 'No help available :('}
        """
        platform = self.platform

        if name == 'This View':
            return self.make_pref_rec(name, "View", key, {'value': self.view.settings().get(key)})

        pref = self.preferences[name]
        type = "user_%s" % platform

        if type in pref:

            if key in pref[type]:
                return self.make_pref_rec(name, "User", key, pref[type][key])

        type = "user"

        if type in pref:

            if key in pref[type]:
                return self.make_pref_rec(name, "User", key, pref[type][key])

        if name == 'Current Project':
            data = self.view.window().project_data()
            settings = data.get('settings', {})

            if key in settings:
                return self.make_pref_rec(name, "Project", key, {'value': settings[key]})

        type = "default_%s" % platform

        if type in pref:

            if key in pref[type]:
                return self.make_pref_rec(name, "Default", key, pref[type][key])

        type = "default"

        if type in pref:

            if key in pref[type]:
                return self.make_pref_rec(name, "Default", key, pref[type][key])

        pref = self.get_pref_defaults(name)

        if name != 'Current Project':

            type = "user_%s" % platform

            if type in pref:

                if key in pref[type]:
                    return self.make_pref_rec(name, "Default", key, pref[type][key])

            type = "user"

            if type in pref:

                if key in pref[type]:
                    return self.make_pref_rec(name, "Default", key, pref[type][key])

        type = "default_%s" % platform

        if type in pref:

            if key in pref[type]:
                return self.make_pref_rec(name, "Default", key, pref[type][key])

        type = "default"

        if type in pref:

            if key in pref[type]:
                return self.make_pref_rec(name, "Default", key, pref[type][key])

        if self.settings_indicate_name:
            return "%s/%s" % (name, key), {'value': None, 'description': 'No help available :('}

        else:
            return key, {'value': None, 'description': 'No help available :('}


    def get_pref_defaults(self, name):
        pref_default = {'default': {}, 'default_'+sublime.platform(): {}}

        if self.is_preferences(name):
            pref_default = self.preferences['Preferences']

        return pref_default

    def get_pref_keys(self, name):
        pref = self.preferences[name]

        if self.is_preferences(name):
            pref_default = self.preferences['Preferences']

        else:
            pref_default = {'default': {}, 'default_'+sublime.platform(): {}}

        return set \
        (
            [ x
                for y in standard_settings_types
                for x in pref.get(y, {}).keys()
            ] +
            [ x
                for y in standard_settings_types
                for x in pref_default.get(y, {}).keys()
            ]
        )

    def is_preferences(self, name):
        return name in self.syntax_names or name in standard_settings_names

    def getDefaultValueAndDescription(self, name, key):
        """
        @name  the name of the setting file name on self.preferences
        @key   the name of the setting

        get_DefaultValueAndDescription, name: Preferences
        get_DefaultValueAndDescription, key:  word_wrap

        get_DefaultValueAndDescription, name: Preferences
        get_DefaultValueAndDescription, key:  wrap_width

        get_DefaultValueAndDescription, name: Default
        get_DefaultValueAndDescription, key:  adaptive_dividers

        @return a dictionary with the keys `value` and `description` for the given setting file and setting name.

        {'value': 0, 'description': 'Set to a value other than 0 to force wrapping at that column rather than the\nwindow width\n'}
        {'value': './\\()"\'-:,.;<>~!@#$%^&*|+=[]{}`~?', 'description': 'Characters that are considered to separate words\n'}
        """
        log( 2, 'get_DefaultValueAndDescription, name: ' + str( name ) )
        log( 2, 'get_DefaultValueAndDescription, key:  ' + str( key ) )

        pref = self.preferences[name]

        for k in 'default', 'default_'+self.platform:

            if key in pref.get(k, {}):
                return pref[k][key]

        if self.is_preferences(name):
            return self.getDefaultValueAndDescription('Preferences', key)

        return None

    def get_meta(self, name, key, spec):
        """
            @name  the name of the setting file name on self.preferences
            @key   the name of the setting
            @spec  a dictionary with the keys `value` and `description` for the given setting file and setting name.
                   {'value': 0, 'description': 'Set to a value other than 0 to force wrapping'}

            @return
        """
        meta = self.getDefaultValueAndDescription(name, "meta."+key)

        #sys.stderr.write("meta: %s\n" % meta)
        if meta:
            return meta.get('value')

        val = spec.get('value')

        if isinstance(val, bool):
            return \
            {
                'widget': 'select_bool'
            }

        if isinstance(val, float):
            return \
            {
                'widget':   'input',
                'validate': 'float',
            }

        if isinstance(val, int):
            return \
            {
                'widget':   'input',
                'validate': 'int',
            }

        if isinstance(val, list):
            return \
            {
                'widget':   'input',
                'validate': 'json_list'
            }

        if isinstance(val, dict):
            return \
            {
                'widget':   'input',
                'validate': 'json_dict'
            }

        return \
        {
            'widget': 'input'
        }


    def run_widget(self, key_path):
        log( 2, "run_widget, key_path: " + str( key_path ) )
        name, type, key = self.convertSettingPathToNameTypeAndKey(key_path)

        log( 2, "run_widget, name: " + str( name ) )
        log( 2, "run_widget, type: " + str( type ) )
        log( 2, "run_widget, key:  " + str( key ) )

        #import spdb ; spdb.start()

        spec = self.getDefaultValueAndDescription(name, key)
        meta = self.get_meta(name, key, spec)
        rec  = self.getPreferencesPathAndValue(name, key)[1]

        log( 2, "run_widget, meta:   " + str( meta ) )

        widget      = meta.get('widget', 'input')
        validate    = meta.get('validate', 'str')
        args        = meta.get('args', {})

        log( 2, "run_widget, widget:   " + str( widget ) )
        log( 2, "run_widget, validate: " + str( validate ) )
        log( 2, "run_widget, args:     " + str( args ) )

        if isinstance(validate, list):
            validate_in_list = validate

            def _validate_element(x):

                if x in validate_in_list:
                    return x

                else:
                    raise ValueError("Value must be one of %s" % validate_in_list)

            validate = _validate_element

        elif '.' not in validate:
            validate = eval(validate)

        if hasattr(self, "widget_"+widget):
            widget_func = getattr(self, "widget_"+widget)

        widget_func(self, key_path, value=rec.get('value'), default=spec.get('value'), validate=validate, **args)

    def change_value(self, options, index):
        key_path = options[index][0]
        log( 2, "change__value, key_path: " + str( key_path ) )

        name, type, key = self.convertSettingPathToNameTypeAndKey(key_path)

        log( 2, "change__value, name: " + str( name ) )
        log( 2, "change__value, type: " + str( type ) )
        log( 2, "change__value, key:  " + str( key ) )

        options = \
        [
            [ "Change Value", "" ],
        ]

        if key_path.startswith("Preferences/"):
            syntax = self.window.active_view().settings().get('syntax')
            syntax = os.path.splitext(os.path.basename(syntax))[0]

    #       options = [
    #           [ "Set for anything", ""]
    #           [ "Set for syntax %s only" % syntax, "" ],
    #           [ "Set for this platform only", sublime.platform() ],
    #           [ "Set for OSX only", "" ],
    #           [ "Set for Windows only", "" ],
    #           [ "Set for Linux only", ""]
    #       ]

        spec = self.getDefaultValueAndDescription(name, key)
        view = self.window.active_view()

        if view.settings().get('preferences_editor_dialog_reset_to_default', False):

            if "/User/" in key_path:
                options.append( [ "Reset to Default", str(spec.get('value')) ] )

        def done(index):

            if index == 0:  # change value
                self.run_widget(key_path)

            if index == len(options)-1: # reset to default
                self.set_pref_value(key_path, spec.get('value'), spec.get('value'))

        if len(options) == 1:
            self.run_widget(key_path)

        else:
            show_quick_panel(self.window.active_view(), options, done)

    def shutdown(self):
        self.window.run_command("hide_panel", {"panel": "output.preferences_editor_help"})

    def run(self, name=None, platform=None, syntax=None):
        r"""
        :param syntax:
            Name of syntax, you want to edit settings for

        :param name:
            Name of settings, you want to edit.

        :param platform:
            One of OSX, Windows or Linux, for editing platform specific settings.
        """

        self.view        = self.window.active_view()
        self.platform    = sublime.platform()
        self.preferences = load_preferences()

        loglevel       = self.view.settings().get('preferences_editor_loglevel', '0')
        log._log_level = int( loglevel )

        self.settings_indicate_name = True
        self.settings_indicate_type = self.view.settings().get('preferences_editor_indicate_default_settings')

        syntax_names, plaintext_syntax, reStructuredText_syntax = load_syntax_names(True)
        self.syntax_names = syntax_names

        for syntax in syntax_names:

            if syntax not in self.preferences:
                self.preferences[syntax] = { 'default': {}, 'default_'+sublime.platform(): {} }

        self.preferences['Current Project'] = { 'default': {}, 'default_'+sublime.platform(): {} }

        self.preferences['This View'] = { 'default': {}, 'default_'+sublime.platform(): {} }

        current_syntax = get_current_syntax(self.view, syntax)
        self.current_syntax = current_syntax

        # for pref in self.preferences: log( 2, "pref: {0}".format( pref ) )
        if self.current_syntax not in self.preferences:
            self.preferences[self.current_syntax] = self.current_syntax

        self.name = name
        #import spdb ; spdb.start()

        # https://bitbucket.org/klorenz/sublimepreferenceseditor/pull-requests/4
        if self.current_syntax in self.preferences:
            self.preferences['Current Syntax'] = self.preferences[self.current_syntax]

        options = []
        options_data = []

        def process_keys():

            for key in sorted(self.get_pref_keys(name)):
                key_path, key_value = self.getPreferencesPathAndValue(name, key)

                log( 2, 'run, key_path:  ' + str( key_path ) )
                log( 2, 'run, key_value: ' + str( key_value ) )
                options.append( [ key_path, sublime.encode_value(key_value.get('value'), False) ] )

                defaultValueAndDescription = self.getDefaultValueAndDescription(name, key)
                log( 2, "run, self.get_DefaultValueAndDescription(name, key): " + str( defaultValueAndDescription ) )

                options_data.append( defaultValueAndDescription )

        if name is None:
            self.is_main_panel = True

            options = \
            [
                ["Preferences", "General Settings"],
                ["Distraction Free", "Preferences for Distraction Free Mode"],
                ["Current Syntax", "%s-specific Preferences" % current_syntax],
                ["Current Project", "Project-specific Preferences"],
                ["This View", "Preferences for this View only"]
            ]

            for name in sorted(self.preferences.keys()):

                if name in syntax_names and name != current_syntax: continue

                if self.view.settings().get('preferences_editor_use_syntax_name', False):
                    if name == "Current Syntax": continue

                else:
                    if name == current_syntax: continue

                process_keys()

        else:
            self.is_main_panel          = False
            self.settings_indicate_name = False

            process_keys()

        #import spdb ; spdb.start()

        help_view = self.window.create_output_panel("preferences_editor_help")
        help_view.settings().set('auto_indent', False)

        self.window.run_command("show_panel", {"panel": "output.preferences_editor_help"})

        def on_highlighted(index):
            help_view.run_command("select_all")
            description = options_data[index]['description']

            if description.startswith("=\n"):
                description = description[2:]

                if reStructuredText_syntax:

                    if help_view.settings().get('syntax') != reStructuredText_syntax:
                        help_view.set_syntax_file(reStructuredText_syntax)
            else:

                if plaintext_syntax:

                    if help_view.settings().get('syntax') != plaintext_syntax:
                        help_view.set_syntax_file(plaintext_syntax)

            help_view.run_command("insert", {"characters": description})
            help_view.show(0)


           # preview = self.window.create_output_panel("unicode_preview")

           #  settings = sublime.load_settings('Character Table.sublime-settings')
           #  font_size = settings.get('font_size', 72)

           #  preview.settings().set("font_size", font_size)
           #  self.window.run_command("show_panel", {"panel": "output.unicode_preview"})

           #  def on_highlighted(index):
           #      char = UNICODE_DATA[index][0]
           #      preview.run_command("select_all")
           #      preview.run_command("insert", {"characters": char})

           #  self.window.show_quick_panel(UNICODE_DATA, on_done,
           #      sublime.MONOSPACE_FONT, -1, on_highlighted)

        options.insert( 0, [ "QUIT (Esc)", "End Edit Settings" ] )
        options_data.insert( 0, { "description": "You can press Esc, or select this option to end"
                                 " editing settings.\n" } )

        options.insert( 1, [ "BACK (Open the Main Menu)", "Choose another Setting to Edit" ] )
        options_data.insert( 1, { "description": "Select this option to take another setting to edit.\n" } )

        def done(index):

            if index < 0:
                return self.shutdown()

            elif index == 0:

                if self.is_main_panel:
                    self.shutdown()

                else:
                    self.shutdown()
                    self.window.run_command("edit_preferences")

            # When it is the main panel, the indexes are not shifted by 1
            elif self.is_main_panel:
                self.window.run_command("edit_preferences", {"name": options[index][0]})

            # When it is not the main panel, the indexes are shifted by 1
            else:
                self.index = index
                self.change_value(self.options, index)

        # log( 2, pprint.pformat(options) )

        self.options = options
        self.preferences_selector = lambda: show_quick_panel(self.view, self.options, done, on_highlighted)
        self.preferences_selector()




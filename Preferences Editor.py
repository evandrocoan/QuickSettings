import sublime, os, sublime_plugin, re, json, sys

def show_panel(view, options, done, highlighted=None):
	sublime.set_timeout(lambda: view.window().show_quick_panel(options, done, 0, -1, highlighted), 10)

def json_list(x):
	try:
		d = json.loads(x)
	except Exception as e:
		raise ValueError(str(e))

	if not isinstance(d, list):
		raise ValueError("Expected a JSON list")

def json_dict(x):
	try:
		d = json.loads(x)
	except Exception as e:
		raise ValueError(str(e))

	if not isinstance(d, dict):
		raise ValueError("Expected a JSON dictionary")


def show_input(view, caption, initial, on_done=None, on_change=None, 
	on_cancel=None, on_load=None):

	window = view.window()

	def do_input():
		input_view = window.show_input_panel(caption, str(initial), on_done=on_done, 
			on_change=on_change, on_cancel=on_cancel)

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
	KEY_RE     = re.compile(r'\s*"([^"]+)"\s*:')

	d = {}
	comment = ""
	lines = []
	for line in data.splitlines(1):
		m = COMMENT_RE.match(line)
		if m:
			s = m.group(1)
			if not s: s = "\n"
			comment += s
			lines.append("\n")
			continue

		m = COMMENT_RE2.match(line)
		if m:
			sys.stderr.write("line1: %s\n" % (repr(line)))
			line = line[:m.start(1)].rstrip()+"\n"
			sys.stderr.write("line2: %s\n" % (repr(line)))


		if not line.strip(): # empty line resets current comment
			comment = ""
			continue

		m = KEY_RE.match(line)
		if m:
			d[m.group(1)] = {"description": comment.replace("\r", "") or "No help available :("}
			comment = ""

		lines.append(line)

	return d, "".join(lines).replace("\r", "")

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

def load_preferences():
	# for syntax specific, we need syntax names
	language_files = sublime.find_resources("*.tmLanguage")
	syntax_names = []
	for f in language_files:
		syntax_names.append(os.path.basename(f).rsplit('.', 1)[0])

	prefs = {}
	preferences_files = sublime.find_resources("*.sublime-settings")
	for pref_file in preferences_files:

		name = os.path.basename(pref_file).rsplit('.', 1)[0]

		platform = "any"

		if name[-5:].lower() == "(osx)":
			name = name[:-6]
			platform = "osx"

		elif name[-9:].lower() == "(windows)":
			name = name[:-10]
			platform = "windows"

		elif name[-7:].lower() == "(linux)":
			name = name[:-8]
			platform = "linux"

		if "/User/" in pref_file:
			type = "user"
		else:
			type = "default"

		if platform != "any":
			type = type+"_"+platform

		if name not in prefs:
			prefs[name] = {}

		syntax = None
		if 0 and name in syntax_names:
			type = "syntax_"+type
			syntax = name
			name = "Preferences"
			if type not in prefs[name]:
				prefs[name][type] = {}
			if syntax not in prefs[name][type]:
				prefs[name][type][syntax] = {}

			pref = prefs[name][type][syntax]
		else:
			if type not in prefs[name]:
				prefs[name][type] = {}

			pref = prefs[name][type]

		sys.stderr.write("name: %s, type: %s, syntax: %s\n" % (name, type, syntax))

		new_data = {}
		data = sublime.load_resource(pref_file)
		try:
			#import spdb ; spdb.start()
			d, data = get_descriptions(data)
			data = json.loads(data)
			for k,v in data.items():
				if k not in d:
					new_data[k] = {"description": "No help available :("}
				else:
					new_data[k] = d[k]

				new_data[k]['value'] = v

		except:
			import traceback
			sys.stderr.write(traceback.format_exc())
			sys.stderr.write(data)

		pref.update(new_data)

	return prefs

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

	sys.stderr.write("plain text syntax: %s\n" % plaintext_syntax)
	sys.stderr.write("reST syntax: %s\n" % reStructuredText_syntax)

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
		# 	true_flags

		# if value is True:
		# 	true_string += " (current"
		# 	if default is True:
		# 		true_string += ", default"
		# 	true_string += ")"

		options = ["true", "false"]

		name, type, key = self.split_key_path(key_path)

		key_path, key_value = pref_editor.get_pref_rec(name, key)

		view = pref_editor.window.active_view()

		def done(index):
			view.erase_status("preferences_editor")

			if index < 0:
				self.view.settings().set(key, key_value['value'])
				return self.shutdown()

			if index == 0:
				pref_editor.set_pref_value(key_path, True, default)
			else:
				pref_editor.set_pref_value(key_path, False, default)

		def highlight(index):
			if index == 0:
				self.view.settings().set(key, True)
			else:
				self.view.settings().set(key, False)

		view.set_status("preferences_editor", "Set %s" % key_path)
		show_panel(view, options, done, highlight)


	def widget_select(self, pref_editor, key_path, value=None, default=None, validate=None, values=[]):
		settings = self.view.settings()

		name, type, key = self.split_key_path(key_path)
		key_value = pref_editor.get_pref_rec(name, key)[1]
		view_specific = settings.get(key) != key_value['value']

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
			sys.stderr.write("setting %s to %s\n" % key, values[index])
			settings.set(key, values[index])

		view.set_status("preferences_editor", "Set %s" % key_path)
		show_panel(view, options, done, highlight)

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

			show_panel(view, options, done)

		def do_remove_option():
			options = [ v.get('caption', str(v.get('value')))
				for v in values if v['value'] in value ]

			def done(index):
				if index < 0: return self.shutdown()
				value.remove(value[index])
				do_show_panel()

			show_panel(view, options, done)


		def do_show_panel():
			other[:] = [ v['value'] for v in values if v['value'] not in value ]

			options = [ 
				["Set Value", json.dumps(value)], 
				["Add Option", "From: "+json.dumps(other)], 
				["Remove Option", "From:"+json.dumps(value)] 
				]

			def done(index):
				view.erase_status("preferences_editor")
				if index < 0: return self.shutdown()

				if index == 0:
					pref_editor.set_pref_value(key_path, value, default)

				if index == 1:
					do_add_option()

				if index == 2:
					do_remove_option()

			view.set_status("preferences_editor", "Set %s" % key_path)
			show_panel(view, options, done)

		do_show_panel()

	def widget_select_resource(self, pref_editor, key_path, value=None, default=None, validate=None, find_resources="", strip_path=True, strip_suffix=True):
		resources = sublime.find_resources(find_resources)

		name, type, key = self.split_key_path(key_path)

		settings = self.view.settings()
		key_value = pref_editor.get_pref_rec(name, key)[1]
		view_specific = settings.get(key) != key_value['value']

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

			if index < 0: return self.shutdown()
			pref_editor.set_pref_value(key_path, resources[index], default)

		def highlight(index):
			sys.stderr.write("setting %s to %s\n" % (key, resources[index]))
			settings.set(key, resources[index])

		view.set_status("preferences_editor", "Set %s" % key_path)
		show_panel(view, options, done, highlight)


	def widget_input(self, pref_editor, key_path, value=None, default=None, validate=None):
		name, type, key = self.split_key_path(key_path)

		view = pref_editor.window.active_view()
		view.set_status("preferences_editor", "Set %s" % key_path)

		settings = self.view.settings()
		key_value = pref_editor.get_pref_rec(name, key)[1]
		view_specific = settings.get(key) != key_value['value']

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
				settings.set(key, value)
				sys.stderr.write("set %s to %s\n" % (key, value))

			except ValueError as e:
				sublime.status_message("Invalid Value: %s" % e)

		def cancel():
			_undo_view_settings()
			view.erase_status("preferences_editor")

		view.set_status("preferences_editor", "Set %s" % key_path)
		show_input(self.window.active_view(), key, value, done, change, cancel)


	def split_key_path(self, key_path):
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
		name, type, key = self.split_key_path(key_path)

		if name == "This View":
			settings = self.view.settings()
			settings.set(key, value)
			return

		if name == "Current Syntax": name = self.current_syntax

		settings = sublime.load_settings(name+'.sublime-settings')

		if value == default:
			if type != 'Default':
				settings.erase(key)
			else:
				settings.set(key, value)
		else:
			settings.set(key, value)

		sublime.save_settings(name+'.sublime-settings')
		self.shutdown()


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
			return "%s/%s" % (name, type, key), value
		elif self.settings_indicate_name:
			return "%s/%s" % (name, key), value
		else:
			return key, value


	def get_pref_rec(self, name, key):
		platform = self.platform

		if name == 'This View':
			return self.make_pref_rec(name, "View", key, 
				{'value': self.view.settings().get(key)})

		pref = self.preferences[name]

		type = "user_%s" % platform

		indicate_type = self.view.settings().get('preferences_editor_indicate_default_settings')

		if type in pref:
			if key in pref[type]:
				return self.make_pref_rec(name, "User", key, pref[type][key])

		type = "user"

		if type in pref:
			if key in pref[type]:
				return self.make_pref_rec(name, "User", key, pref[type][key])

		type = "default_%s" % platform

		if type in pref:
			if key in pref[type]:
				return self.make_pref_rec(name, "Default", key, pref[type][key])

		type = "default"
		if type in pref:
			if key in pref[type]:
				return self.make_pref_rec(name, "Default", key, pref[type][key])

		pref = self.get_pref_defaults(name)

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

		pref_default = {'default': {}, 'default_'+sublime.platform(): {}}
		if self.is_preferences(name):
			pref_default = self.preferences['Preferences']


		return set([x 
			for y in ('default', 'default_'+sublime.platform())
			for x in pref.get(y, {}).keys() 
			] + [x
			for y in ('default', 'default_'+sublime.platform())
			for x in pref_default.get(y, {}).keys()
			])

	def is_preferences(self, name):
		return name in self.syntax_names or name in (
			"Distraction Free", "Current Syntax", "This View")

	def get_spec(self, name, key):
		pref = self.preferences[name]

		for k in 'default', 'default_'+self.platform:
			if key in pref.get(k, {}):
				return pref[k][key]

		if self.is_preferences(name):
			return self.get_spec('Preferences', key)

		return None

	def get_meta(self, name, key, spec=None):
		meta = self.get_spec(name, "meta."+key)
		sys.stderr.write("meta: %s\n" % meta)
		if meta: return meta.get('value')

		val = spec.get('value')

		if val is True or val is False:
			return {'widget': 'select_bool'}

		if isinstance(val, float):
			return {
				'widget': 'input', 
				'validate': 'float',
			}

		if isinstance(val, int):
			return {
				'widget': 'input', 
				'validate': 'int',
			}

		if isinstance(val, list):
			return {'widget': 'input', 'validate': 'json_list'}

		if isinstance(val, dict):
			return {'widget': 'input', 'validate': 'json_dict'}

		return {'widget': 'input'}


	def run_widget(self, key_path):
		name, type, key = self.split_key_path(key_path)

		#import spdb ; spdb.start()

		spec = self.get_spec(name, key)
		meta = self.get_meta(name, key, spec)
		rec  = self.get_pref_rec(name, key)[1]

		widget      = meta.get('widget', 'input')
		validate    = meta.get('validate', 'str')
		args        = meta.get('args', {})

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
		# import

		if hasattr(self, "widget_"+widget):
			widget_func = getattr(self, "widget_"+widget)

		widget_func(self, key_path, value=rec.get('value'), 
			default=spec.get('value'), validate=validate, **args)

	def change_value(self, key_path):

		name, type, key = self.split_key_path(key_path)

		options = [
			[ "Change Value", "" ],
		]

		if key_path.startswith("Preferences/"):
			syntax = self.window.active_view().settings().get('syntax')
			syntax = os.path.splitext(os.path.basename(syntax))[0]

	#		options = [
	#			[ "Set for anything", ""]
	#			[ "Set for syntax %s only" % syntax, "" ],
	#			[ "Set for this platform only", sublime.platform() ],
	#			[ "Set for OSX only", "" ],
	#			[ "Set for Windows only", "" ],
	#			[ "Set for Linux only", ""]
	#		]

		spec = self.get_spec(name, key)

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
			show_panel(self.window.active_view(), options, done)

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

		self.platform = sublime.platform()
		self.preferences = load_preferences()
		self.view = self.window.active_view()

		self.settings_indicate_type = \
			self.view.settings().get('preferences_editor_indicate_default_settings')

		self.settings_indicate_name = True

		syntax_names, plaintext_syntax, reStructuredText_syntax = load_syntax_names(True)
		self.syntax_names = syntax_names
		for n in syntax_names:
			if n not in self.preferences:
				self.preferences[n] = {
					'default': {}, 'default_'+sublime.platform(): {} }

		self.preferences['This View'] = {
			'default': {}, 'default_'+sublime.platform(): {} }

		current_syntax = get_current_syntax(self.view, syntax)
		self.current_syntax = current_syntax
		self.preferences['Current Syntax'] = self.preferences[self.current_syntax]
		self.name = name
		#import spdb ; spdb.start()

		option_data = []
		options = []
		if name is None:
			for name in sorted(self.preferences.keys()):
				if name in syntax_names and name != current_syntax: continue

				if self.view.settings().get('preferences_editor_use_syntax_name', False):
					if name == "Current Syntax": continue
				else:
					if name == current_syntax: continue

				for key in sorted(self.get_pref_keys(name)):
					key_path, key_value = self.get_pref_rec(name, key)
					options.append( [ key_path, json.dumps(key_value.get('value')) ] )
					option_data.append( self.get_spec(name, key) )

		else:
			self.settings_indicate_name = False

			for key in sorted(self.get_pref_keys(name)):
				key_path, key_value = self.get_pref_rec(name, key)
				options.append( [ key_path, json.dumps(key_value.get('value')) ] )
				option_data.append( self.get_spec(name, key) )

		#import spdb ; spdb.start()

		help_view = self.window.create_output_panel("preferences_editor_help")

		self.window.run_command("show_panel", {"panel": "output.preferences_editor_help"})

		def on_highlighted(index):
			help_view.run_command("select_all")
			description = option_data[index]['description']
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

		def done(index):
			if index < 0: return self.shutdown()

			self.change_value(options[index][0])

		show_panel(self.view, options, done, on_highlighted)


class EditSelectedPreferences(sublime_plugin.WindowCommand):
	def run(self):
		self.preferences  = load_preferences()
		self.syntax_names = load_syntax_names()
		current_syntax = get_current_syntax(self.window.active_view())

		basic = [
			["Preferences", "General Settings"], 
			["Distraction Free", "Preferences for Distraction Free Mode"],
			["Current Syntax", "%s-specific Preferences" % current_syntax],
			["This View", "Preferences for this View only"]
			]

		options = basic + [ 
			[k, k in self.syntax_names and "Syntax-specific Preferences" or "Package Settings"] 
			for k in set(list(self.preferences.keys()) + self.syntax_names) 
			if k not in basic and k not in set(["Distraction Free", "Preferences", "Current Syntax", "This View"])
			]

		def done(index):
			self.window.run_command("edit_preferences", {"name": options[index][0]})

		show_panel(self.window.active_view(), options, done)



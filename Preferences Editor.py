import sublime, os, sublime_plugin, re, json, sys

def show_panel(view, options, done):
	sublime.set_timeout(lambda: view.window().show_quick_panel(options, done, 0), 10)


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

	"""
	COMMENT_RE = re.compile(r"\s*//\s?(.*)")
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

		if not line.strip(): # empty line resets current comment
			comment = ""
			continue

		m = KEY_RE.match(line)
		if m:
			d[m.group(1)] = {"description": comment}
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

		if name not in syntax_names and name not in prefs:
			prefs[name] = {}

		syntax = None
		if name in syntax_names:
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

		d = {}
		data = sublime.load_resource(pref_file)
		try:
			#import spdb ; spdb.start()
			d, data = get_descriptions(data)
			data = json.loads(data)
			for k,v in data.items():
				#if k.startswith('meta.'):
					#import spdb ; spdb.start()
				if k not in d: d[k] = {"description": ""}
				d[k]['value'] = v

		except:
			import traceback
			sys.stderr.write(traceback.format_exc())
			sys.stderr.write(data)

		pref.update(d)

	return prefs

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

	def widget_select_bool(self, pref_editor, key_path, value=None, default=None, validate=None):
		# true_string = "True"

		# true_flags = []
		# if value is True:
		# 	true_flags

		# if value is True:
		# 	true_string += " (current"
		# 	if default is True:
		# 		true_string += ", default"
		# 	true_string += ")"

		options = ["True", "False"]

		name, type, key = key_path.split('/')

		key_path, key_value = pref_editor.get_pref_rec(name, key)

		view = pref_editor.window.active_view()

		def done(index):
			view.erase_status("preferences_editor")

			if index < 0: return
			if index == 0:
				pref_editor.set_pref_value(key_path, True, default)
			else:
				pref_editor.set_pref_value(key_path, False, default)

		view.set_status("preferences_editor", "Set %s" % key_path)
		show_panel(view, options, done)


	def widget_select(self, pref_editor, key_path, value=None, default=None, validate=None, values=[]):

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

			if index < 0: return

			# if command is set, let the command handle this preference
			if commands[index]:
				context = view
				if types[index] == "window":
					context = view.window()

				sublime.set_timeout(lambda: context.run_command(commands[index], args[index]), 10)
				return

			pref_editor.set_pref_value(key_path, values[index], default)

		view.set_status("preferences_editor", "Set %s" % key_path)
		show_panel(view, options, done)

	def widget_select_resource(self, pref_editor, key_path, value=None, default=None, validate=None, find_resources=""):
		options = sublime.find_resources(find_resources)

		view = pref_editor.window.active_view()
		def done(index):
			view.erase_status("preferences_editor")
			if index < 0: return
			pref_editor.set_pref_value(key_path, options[index], default)

		view.set_status("preferences_editor", "Set %s" % key_path)
		show_panel(view, options, done)


	def widget_input(self, pref_editor, key_path, value=None, default=None, validate=None):
		name, type, key = key_path.split('/')

		view = pref_editor.window.active_view()
		view.set_status("preferences_editor", "Set %s" % key_path)

		def done(value):
			try:
				value = validate(value)
				pref_editor.set_pref_value(key_path, value, default)
			except ValueError as e:
				sublime.error_message("Invalid Value: %s" % e)
			view.erase_status("preferences_editor")

		def change(value):
			try:
				validate(value)
			except ValueError as e:
				sublime.status_message("Invalid Value: %s" % e)

		def cancel():
			view.erase_status("preferences_editor")

		view.set_status("preferences_editor", "Set %s" % key_path)
		show_input(self.window.active_view(), key, value, done, change)


	def set_pref_value(self, key_path, value, default=None):
		name, type, key = key_path.split('/')

		settings = sublime.load_settings(name+'.sublime-settings')

		if value == default:
			if type != 'Default':
				settings.erase(key)
			else:
				settings.set(key, value)


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

		sublime.save_settings(name+'.sublime-settings')


	def get_pref_rec(self, name, key):
		platform = self.platform

		pref = self.preferences[name]

		type = "user_%s" % platform

		if type in pref:
			if key in pref[type]:
				return "%s/%s/%s" % (name, "User", key), pref[type][key]

		type = "user"

		if type in pref:
			if key in pref[type]:
				return "%s/%s/%s" % (name, "User", key), pref[type][key]

		type = "default_%s" % platform

		if type in pref:
			if key in pref[type]:
				return "%s/%s/%s" % (name, "Default", key), pref[type][key]

		type = "default"
		if type in pref:
			if key in pref[type]:
				return "%s/%s/%s" % (name, "Default", key), pref[type][key]

		pref = self.get_pref_defaults(name)

		type = "user_%s" % platform

		if type in pref:
			if key in pref[type]:
				return "%s/%s/%s" % (name, "Default", key), pref[type][key]

		type = "user"

		if type in pref:
			if key in pref[type]:
				return "%s/%s/%s" % (name, "Default", key), pref[type][key]

		type = "default_%s" % platform

		if type in pref:
			if key in pref[type]:
				return "%s/%s/%s" % (name, "Default", key), pref[type][key]

		type = "default"
		if type in pref:
			if key in pref[type]:
				return "%s/%s/%s" % (name, "Default", key), pref[type][key]

		return "%s/%s" % (name, key), {'value': None, 'description': ''}


	def get_pref_defaults(self, name):
		pref_default = {'default': {}, 'default_'+sublime.platform(): {}}
		if name in self.syntax_names or name == "Distraction Free":
			pref_default = self.preferences['Preferences']

		return pref_default

	def get_pref_keys(self, name):
		pref = self.preferences[name]

		#if name == "Python":
			#import spdb ; spdb.start()

		pref_default = {'default': {}, 'default_'+sublime.platform(): {}}
		if name in self.syntax_names or name == "Distraction Free":
			pref_default = self.preferences['Preferences']

		return set([x 
			for y in ('default', 'default_'+sublime.platform())
			for x in pref.get(y, {}).keys() 
			] + [x
			for y in ('default', 'default_'+sublime.platform())
			for x in pref_default.get(y, {}).keys()
			])

	def get_spec(self, name, key):
		pref = self.preferences[name]

		for k in 'default', 'default_'+self.platform:
			if key in pref.get(k, {}):
				return pref[k][key]

		if name in self.syntax_names or name == "Distraction Free":
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
		name, type, key = key_path.split('/')

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
		name, type, key = key_path.split('/')

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

		if view.settings().get('pref_edit_dialog_reset_to_default', False):
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

	def run(self, name="Preferences", platform=None, syntax=None):
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

		settings = self.window.active_view().settings()
		if settings.has('syntax'):
			current_syntax = settings.get('syntax')
			current_syntax = os.path.basename(current_syntax).rsplit('.', 1)[0]

			if current_syntax not in self.preferences:
				self.preferences[current_syntax] = {
					'default': {}, 'default_'+sublime.platform(): {} }

		language_files = sublime.find_resources("*.tmLanguage")
		syntax_names = []
		for f in language_files:
			syntax_names.append(os.path.basename(f).rsplit('.', 1)[0])
		self.syntax_names = syntax_names

		#import spdb ; spdb.start()

		options = []
		for name,prefs in sorted(self.preferences.items()):
			for key in self.get_pref_keys(name):
				key_path, key_value = self.get_pref_rec(name, key)
				options.append( [ key_path, json.dumps(key_value.get('value')) ] )

		def done(index):
			if index < 0: return

			self.change_value(options[index][0])

		show_panel(self.window.active_view(), options, done)

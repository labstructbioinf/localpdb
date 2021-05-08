import json
import datetime


class PluginVersioneer:

    def __init__(self, plugin_dir):
        self.logs_fn = '{}/status.log'.format(plugin_dir)
        try:
            with open(self.logs_fn) as f:
                data = json.loads(f.read())
                self.installed_plugin_versions = {int(key) for key, value in data.items() if value[0] == 'OK'}
                self.logs = data
        except FileNotFoundError:
            self.installed_plugin_versions = set()
            self.logs = {}

    def update_logs(self, version, additional_info = None):
        """
        Updates the version log for the plugin with the OK status, time and optional additional data
        :param version: localpdb version
        :param additional_info: list of values with additional info, default = None
        :return: 0 if everything went fine
        """
        status = ['OK', datetime.datetime.now().strftime("%Y-%m-%d %H:%M")]
        try:
            json.dumps(additional_info)
            status.append(additional_info)
        except TypeError:
            pass # Unable to dump additional info to JSON format
        self.logs[version] = status
        try:
            with open(self.logs_fn, 'w') as f:
                f.write(json.dumps(self.logs, indent=4))
        except PermissionError:
            return 1
        return 0

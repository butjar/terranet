from functools import partial
from flask import Flask, request, jsonify, abort
from flask.helpers import locked_cached_property

class ConfigAPI(Flask):
    def __init__(self,
                 import_name,
                 node,
                 static_url_path=None,
                 static_folder=None,
                 static_host=None,
                 host_matching=False,
                 subdomain_matching=False,
                 template_folder=None,
                 instance_path=None,
                 instance_relative_config=False,
                 root_path=None):

        super(ConfigAPI, self).__init__(
                import_name,
                static_url_path=static_url_path,
                static_folder=static_folder,
                static_host=static_host,
                host_matching=host_matching,
                subdomain_matching=subdomain_matching,
                template_folder=template_folder,
                instance_path=instance_path,
                instance_relative_config=instance_relative_config,
                root_path=root_path
        )

        self.node = node
        self._routes_init()

    def _routes_init(self):
        self.add_url_rule("/config", "get_config", self.get_config,
                          methods=["GET"])

        self.add_url_rule("/channel", "switch_channel", self.switch_channel,
                          methods=["POST"])

    def get_config(self):
        return jsonify(self.node.komondor_config)

    def switch_channel(self):
        params = [ "primary_channel",
                   "min_channel_allowed",
                   "max_channel_allowed" ]
        payload = request.json
        if not payload:
            abort(400)
        if all(param in payload for param in params):
            primary_channel = payload["primary_channel"]
            min_channel_allowed = payload["min_channel_allowed"]
            max_channel_allowed = payload["max_channel_allowed"]
            self.node.switch_channel(primary_channel,
                                     min_channel_allowed,
                                     max_channel_allowed)
            return ""
        else:
            abort(400)


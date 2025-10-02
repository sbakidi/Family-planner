import importlib
import pkgutil
from typing import Dict


class BasePlugin:
    """Base class for plugins."""
    name = "BasePlugin"
    enabled = False

    def register(self, app):
        """Register plugin components on the Flask app."""
        pass

    def unregister(self, app):
        """Optional cleanup when disabling a plugin."""
        pass


class PluginManager:
    """Discover and manage plugins."""

    def __init__(self, app, package: str = 'src.plugins'):
        self.app = app
        self.package = package
        self.plugins: Dict[str, BasePlugin] = {}
        self.discover_plugins()

    def discover_plugins(self):
        package = importlib.import_module(self.package)
        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            module = importlib.import_module(f"{self.package}.{module_name}")
            plugin_cls = getattr(module, 'Plugin', None)
            if plugin_cls is not None:
                plugin = plugin_cls()
                self.plugins[plugin.name] = plugin

    def list_plugins(self):
        return [{'name': name, 'enabled': plugin.enabled} for name, plugin in self.plugins.items()]

    def enable_plugin(self, name: str):
        plugin = self.plugins.get(name)
        if plugin and not plugin.enabled:
            plugin.register(self.app)
            plugin.enabled = True

    def disable_plugin(self, name: str):
        plugin = self.plugins.get(name)
        if plugin and plugin.enabled:
            if hasattr(plugin, 'unregister'):
                plugin.unregister(self.app)
            plugin.enabled = False

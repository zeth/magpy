"""Load models from an app."""
from magpy.server.instances import InstanceLoader
from magpy.management import BaseCommand, CommandError
import importlib


class Command(BaseCommand):
    """Load the models from app_name(s)."""
    help = ('Load the models from app_name(s).')
    args = '[app_name ...]'

    def handle(self, *args, **kwargs):
        models = []
        for arg in args:
            module_name = '%s.models' % arg
            try:
                models_module = importlib.import_module(module_name)
            except ImportError:
                raise CommandError(
                    "No module called %s\n"
                    "(Package %s needs to be in Python's path.)\n"
                    "(Don't forget to put an __init__.py file inside the "
                    "package.)" % (arg, module_name))

            new_models = getattr(models_module, 'MODELS', [])
            for index, model in enumerate(new_models):
                self.validate_model(model, index, module_name)

            models.extend(getattr(new_models, 'MODELS', []))

        instanceloader = InstanceLoader(validation=False)
        instanceloader.add_instances(models)

    def validate_model(self, model, index, module_name):
        """Check each model for basic sanity."""
        if not '_id' in model:
            print "Error: All models must have an id."""
            self._abort(index, module_name)

        if not '_model' in model:
            print "Error: All models must have a '_model' key."
            self._abort(index, module_name)

        if model['_model'] != '_model':
            print "Error: All models must the '_model' key set to '_model'."
            self._abort(index, module_name)

        if not 'modeldescription' in model:
            print "Warning: Model %s in %s does not have a " \
                "'modeldescription' key" % (index, module_name)
            print "Warning: Apps which assume a modeldescription may break."

    @staticmethod
    def _abort(index, module_name):
        """Abort due to invalid model."""
        print "Aborting. No changes made."
        raise CommandError("Model %s in %s is not valid" % (
                index, module_name))

"""Admin Controller"""
from sqlalchemy.orm import class_mapper
import inspect

from tg.controllers import TGController, expose
from tg.decorators import with_trailing_slash, override_template
from tg.exceptions import HTTPNotFound

Rum = None

from tgext.crud import CrudRestController
from tgext.admin.tgadminconfig import TGAdminConfig

engine = 'genshi'
try:
    import chameleon.genshi
    import pylons.config
    if hasattr(pylons.config, 'renderers') and 'chameleon_genshi' in pylons.config['renderers']:
        engine = 'chameleon_genshi'
    else:
        import warnings
        #warnings.warn('The renderer for \'chameleon_genshi\' templates is missing.'\
        #              'Your code could run much faster if you'\
        #              'add the following line in you app_cfg.py: "base_config.renderers.append(\'chameleon_genshi\')"')
except ImportError:
    pass

from repoze.what.predicates import in_group

class AdminController(TGController):
    """
    A basic controller that handles User Groups and Permissions for a TG application.
    """
    allow_only = in_group('managers')

    def __init__(self, models, session, config_type=None, translations=None):
        if translations is None:
            translations = {}
        if config_type is None:
            config = TGAdminConfig(models, translations)
        else:
            config = config_type(models, translations)


        
        if config.allow_only:
            self.allow_only = config.allow_only

        self.config = config
        self.session = session
        
        self.default_index_template = ':'.join(self.index.decoration.engines.get('text/html')[:2])
        if self.config.default_index_template:
            self.default_index_template = self.config.default_index_template

    @with_trailing_slash
    @expose(engine+':tgext.admin.templates.index')
    def index(self):
        #overrides the template for this method
        original_index_template = self.index.decoration.engines['text/html'] 
        new_engine = self.default_index_template.split(':')
        new_engine.extend(original_index_template[2:])
        self.index.decoration.engines['text/html'] = new_engine
        return dict(models=[model.__name__ for model in self.config.models.values()])

    def _make_controller(self, config, session):
        m = config.model
        class ModelController(CrudRestController):
            model        = m
            table        = config.table_type(session)
            table_filler = config.table_filler_type(session)
            new_form     = config.new_form_type(session)
            new_filler   = config.new_filler_type(session)
            edit_form    = config.edit_form_type(session)
            edit_filler  = config.edit_filler_type(session)
            allow_only   = config.allow_only
        return ModelController(session)
    
    @expose()
    def lookup(self, model_name, *args):
        try:
            model = self.config.models[model_name]
        except KeyError:
            raise HTTPNotFound().exception
        config = self.config.lookup_controller_config(model_name)
        controller = self._make_controller(config, self.session)
        return controller, args

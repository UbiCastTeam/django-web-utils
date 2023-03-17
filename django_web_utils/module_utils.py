
def import_module_by_python_path(module):
    if not isinstance(module, str):
        return module
    elif '.' in module:
        mod_path, name = module.rsplit('.', 1)
        _tmp = __import__(mod_path, fromlist=[name])
        return getattr(_tmp, name)
    else:
        return __import__(module)

from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

ext_modules = [
    Extension("src.database", ["src/database.py"]),
    Extension("src.settings", ["src/settings.py"]),
    Extension("src.writes", ["src/writes.py"]),
    Extension("src.handles", ["src/handles.py"]),
    Extension("schema.db_helpers", ["schema/db_helpers.py"]),
    Extension("src.app", ["src/app.py"])
 ] # might need to add some external imports here too

setup(
    name="comment_server",
    cmdclass={"build_ext": build_ext},
    ext_modules=ext_modules,
    compiler_directives={'language_level': '3'}
)

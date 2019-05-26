from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
from Cython.Build import cythonize

ext_modules = [
    Extension("src.database", ["src/database.py"]),
    Extension("src.settings", ["src/settings.py"]),
    Extension("src.writes", ["src/writes.py"]),
    Extension("schema.db_helpers", ["schema/db_helpers.py"]),
] # might need to add some external imports here too

setup(
    name="comment_server",
    cmdclass={"build_ext": build_ext},
    ext_modules=cythonize(ext_modules, compiler_directives={'language_level': '3'})
)

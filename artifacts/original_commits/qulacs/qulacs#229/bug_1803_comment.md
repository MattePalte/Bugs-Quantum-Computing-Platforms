This modification affects the setup.py files. The gcc path can be specified by the user. When specified, it is used only in a part of the library, whereas the rest of the library uses the default (system wide) gcc path and this might lead to inconsistencies, when the two paths are different.
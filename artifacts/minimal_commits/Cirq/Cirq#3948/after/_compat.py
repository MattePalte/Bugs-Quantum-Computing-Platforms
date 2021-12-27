# Copyright 2018 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Workarounds for compatibility issues between versions and libraries."""
import functools
import importlib
import os
import re
import sys
import traceback
import warnings
from types import ModuleType
from typing import Any, Callable, Optional, Dict, Tuple, Type, Set

import numpy as np
import pandas as pd
import sympy


def proper_repr(value: Any) -> str:
    """Overrides sympy and numpy returning repr strings that don't parse."""

    if isinstance(value, sympy.Basic):
        result = sympy.srepr(value)

        # HACK: work around https://github.com/sympy/sympy/issues/16074
        # (only handles a few cases)
        fixed_tokens = ['Symbol', 'pi', 'Mul', 'Pow', 'Add', 'Mod', 'Integer', 'Float', 'Rational']
        for token in fixed_tokens:
            result = result.replace(token, 'sympy.' + token)

        return result

    if isinstance(value, np.ndarray):
        if np.issubdtype(value.dtype, np.datetime64):
            return f'np.array({value.tolist()!r}, dtype=np.{value.dtype!r})'
        return f'np.array({value.tolist()!r}, dtype=np.{value.dtype})'

    if isinstance(value, pd.MultiIndex):
        return f'pd.MultiIndex.from_tuples({repr(list(value))}, names={repr(list(value.names))})'

    if isinstance(value, pd.Index):
        return (
            f'pd.Index({repr(list(value))}, '
            f'name={repr(value.name)}, '
            f'dtype={repr(str(value.dtype))})'
        )

    if isinstance(value, pd.DataFrame):
        cols = [value[col].tolist() for col in value.columns]
        rows = list(zip(*cols))
        return (
            f'pd.DataFrame('
            f'\n    columns={proper_repr(value.columns)}, '
            f'\n    index={proper_repr(value.index)}, '
            f'\n    data={repr(rows)}'
            f'\n)'
        )

    return repr(value)


def proper_eq(a: Any, b: Any) -> bool:
    """Compares objects for equality, working around __eq__ not always working.

    For example, in numpy a == b broadcasts and returns an array instead of
    doing what np.array_equal(a, b) does. This method uses np.array_equal(a, b)
    when dealing with numpy arrays.
    """
    if type(a) == type(b):
        if isinstance(a, np.ndarray):
            return np.array_equal(a, b)
        if isinstance(a, (pd.DataFrame, pd.Index, pd.MultiIndex)):
            return a.equals(b)
        if isinstance(a, (tuple, list)):
            return len(a) == len(b) and all(proper_eq(x, y) for x, y in zip(a, b))
    return a == b


def _warn_or_error(msg):
    from cirq.testing.deprecation import ALLOW_DEPRECATION_IN_TEST

    called_from_test = 'PYTEST_CURRENT_TEST' in os.environ
    deprecation_allowed = ALLOW_DEPRECATION_IN_TEST in os.environ
    if called_from_test and not deprecation_allowed:
        raise ValueError(f"Cirq should not use deprecated functionality: {msg}")

    # we have to dynamically count the non-internal frames
    # due to the potentially multiple nested module wrappers
    stack_level = 1
    for filename, _, _, _ in reversed(traceback.extract_stack()):
        if not _is_internal(filename) and "_compat.py" not in filename:
            break
        if "_compat.py" in filename:
            stack_level += 1

    warnings.warn(
        msg,
        DeprecationWarning,
        stacklevel=stack_level,
    )


def _validate_deadline(deadline: str):
    DEADLINE_REGEX = r"^v(\d)+\.(\d)+$"
    assert re.match(DEADLINE_REGEX, deadline), "deadline should match vX.Y"


def deprecated(
    *, deadline: str, fix: str, name: Optional[str] = None
) -> Callable[[Callable], Callable]:
    """Marks a function as deprecated.

    Args:
        deadline: The version where the function will be deleted. It should be a minor version
            (e.g. "v0.7").
        fix: A complete sentence describing what the user should be using
            instead of this particular function (e.g. "Use cos instead.")
        name: How to refer to the function.
            Defaults to `func.__qualname__`.

    Returns:
        A decorator that decorates functions with a deprecation warning.
    """
    _validate_deadline(deadline)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def decorated_func(*args, **kwargs) -> Any:
            qualname = func.__qualname__ if name is None else name
            _warn_or_error(
                f'{qualname} was used but is deprecated.\n'
                f'It will be removed in cirq {deadline}.\n'
                f'{fix}\n'
            )

            return func(*args, **kwargs)

        decorated_func.__doc__ = (
            f'THIS FUNCTION IS DEPRECATED.\n\n'
            f'IT WILL BE REMOVED IN `cirq {deadline}`.\n\n'
            f'{fix}\n\n'
            f'{decorated_func.__doc__ or ""}'
        )

        return decorated_func

    return decorator


def deprecated_class(
    *, deadline: str, fix: str, name: Optional[str] = None
) -> Callable[[Type], Type]:
    """Marks a class as deprecated.

    Args:
        deadline: The version where the function will be deleted. It should be a minor version
            (e.g. "v0.7").
        fix: A complete sentence describing what the user should be using
            instead of this particular function (e.g. "Use cos instead.")
        name: How to refer to the class.
            Defaults to `class.__qualname__`.

    Returns:
        A decorator that decorates classes with a deprecation warning.
    """

    _validate_deadline(deadline)

    def decorator(clazz: Type) -> Type:
        clazz_new = clazz.__new__

        def patched_new(cls, *args, **kwargs):
            qualname = clazz.__qualname__ if name is None else name
            _warn_or_error(
                f'{qualname} was used but is deprecated.\n'
                f'It will be removed in cirq {deadline}.\n'
                f'{fix}\n'
            )

            return clazz_new(cls)

        setattr(clazz, '__new__', patched_new)
        clazz.__doc__ = (
            f'THIS CLASS IS DEPRECATED.\n\n'
            f'IT WILL BE REMOVED IN `cirq {deadline}`.\n\n'
            f'{fix}\n\n'
            f'{clazz.__doc__ or ""}'
        )

        return clazz

    return decorator


def deprecated_parameter(
    *,
    deadline: str,
    fix: str,
    func_name: Optional[str] = None,
    parameter_desc: str,
    match: Callable[[Tuple[Any, ...], Dict[str, Any]], bool],
    rewrite: Optional[
        Callable[[Tuple[Any, ...], Dict[str, Any]], Tuple[Tuple[Any, ...], Dict[str, Any]]]
    ] = None,
) -> Callable[[Callable], Callable]:
    """Marks a function parameter as deprecated.

    Also handles rewriting the deprecated parameter into the new signature.

    Args:
        deadline: The version where the function will be deleted. It should be a minor version
            (e.g. "v0.7").
        fix: A complete sentence describing what the user should be using
            instead of this particular function (e.g. "Use cos instead.")
        func_name: How to refer to the function.
            Defaults to `func.__qualname__`.
        parameter_desc: The name and type of the parameter being deprecated,
            e.g. "janky_count" or "janky_count keyword" or
            "positional janky_count".
        match: A lambda that takes args, kwargs and determines if the
            deprecated parameter is present or not. This determines whether or
            not the deprecation warning is printed, and also whether or not
            rewrite is called.
        rewrite: Returns new args/kwargs that don't use the deprecated
            parameter. Defaults to making no changes.

    Returns:
        A decorator that decorates functions with a parameter deprecation
            warning.
    """
    _validate_deadline(deadline)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def decorated_func(*args, **kwargs) -> Any:
            if match(args, kwargs):
                if rewrite is not None:
                    args, kwargs = rewrite(args, kwargs)

                qualname = func.__qualname__ if func_name is None else func_name
                _warn_or_error(
                    f'The {parameter_desc} parameter of {qualname} was '
                    f'used but is deprecated.\n'
                    f'It will be removed in cirq {deadline}.\n'
                    f'{fix}\n',
                )

            return func(*args, **kwargs)

        return decorated_func

    return decorator


def deprecate_attributes(module: ModuleType, deprecated_attributes: Dict[str, Tuple[str, str]]):
    """Wrap a module with deprecated attributes that give warnings.

    Args:
        module: The module to wrap.
        deprecated_attributes: A dictionary from attribute name to a tuple of
            strings, where the first string gives the version that the attribute
            will be removed in, and the second string describes what the user
            should do instead of accessing this deprecated attribute.

    Returns:
        Wrapped module with deprecated attributes. Use of these attributes
        will cause a warning for these deprecated attributes.
    """

    for (deadline, _) in deprecated_attributes.values():
        _validate_deadline(deadline)

    class Wrapped(ModuleType):

        __dict__ = module.__dict__

        def __getattr__(self, name):
            if name in deprecated_attributes:
                deadline, fix = deprecated_attributes[name]
                _warn_or_error(
                    f'{name} was used but is deprecated.\n'
                    f'It will be removed in cirq {deadline}.\n'
                    f'{fix}\n'
                )
            return getattr(module, name)

    return Wrapped(module.__name__, module.__doc__)


class DeprecatedModuleLoader(importlib.abc.Loader):
    """A Loader for deprecated modules.

    It wraps an existing Loader instance, to which it delegates the loading. On top of that
    it ensures that the sys.modules cache has both the deprecated module's name and the
    new module's name pointing to the same exact ModuleType instance.

    Args:
        loader: the loader to be wrapped
        old_module_name: the deprecated module's fully qualified name
        new_module_name: the new module's fully qualified name
    """

    def __init__(self, loader: Any, old_module_name: str, new_module_name: str):
        """A module loader that uses an existing module loader and intercepts
        the execution of a module.
        """
        self.loader = loader
        if hasattr(loader, 'exec_module'):
            # mypy#2427
            self.exec_module = self._wrap_exec_module(loader.exec_module)  # type: ignore
        # while this is rare and load_module was deprecated in 3.4
        # in older environments this line makes them work as well
        if hasattr(loader, 'load_module'):
            # mypy#2427
            self.load_module = self._wrap_load_module(loader.load_module)  # type: ignore
        if hasattr(loader, 'create_module'):
            # mypy#2427
            self.create_module = loader.create_module  # type: ignore
        self.old_module_name = old_module_name
        self.new_module_name = new_module_name

    def module_repr(self, module: ModuleType) -> str:
        return self.loader.module_repr(module)

    def _wrap_load_module(self, method: Any) -> Any:
        def load_module(fullname: str) -> ModuleType:
            assert fullname == self.old_module_name, (
                f"DeprecatedModuleLoader for {self.old_module_name} was asked to "
                f"load {fullname}"
            )
            if self.new_module_name in sys.modules:
                sys.modules[self.old_module_name] = sys.modules[self.new_module_name]
                return sys.modules[self.old_module_name]
            method(self.new_module_name)
            # https://docs.python.org/3.5/library/importlib.html#importlib.abc.Loader.load_module
            assert self.new_module_name in sys.modules, (
                f"Wrapped loader {self.loader} was "
                f"expected to insert "
                f"{self.new_module_name} in sys.modules "
                f"but it did not."
            )
            sys.modules[self.old_module_name] = sys.modules[self.new_module_name]
            return sys.modules[self.old_module_name]

        return load_module

    def _wrap_exec_module(self, method: Any) -> Any:
        def exec_module(module: ModuleType) -> None:
            assert module.__name__ == self.old_module_name, (
                f"DeprecatedModuleLoader for {self.old_module_name} was asked to "
                f"load {module.__name__}"
            )
            # check for new_module whether it was loaded
            if self.new_module_name in sys.modules:
                # found it - no need to load the module again
                sys.modules[self.old_module_name] = sys.modules[self.new_module_name]
                return

            # now we know we have to initialize the module
            sys.modules[self.old_module_name] = module
            sys.modules[self.new_module_name] = module

            try:
                return method(module)
            except BaseException:
                # if there's an error, we atomically remove both
                del sys.modules[self.new_module_name]
                del sys.modules[self.old_module_name]
                raise

        return exec_module


def _is_internal(filename: str) -> bool:
    """Returns whether filename is internal to python.

    This is similar to how the built-in warnings module differentiates frames from internal modules.
    It is specific to CPython - see
    https://github.com/python/cpython/blob/41ec17e45d54473d32f543396293256f1581e44d/Lib/warnings.py#L275.
    """
    return 'importlib' in filename and '_bootstrap' in filename


_warned: Set[str] = set()


def _deduped_module_warn_or_error(old_module_name, new_module_name, deadline):
    if old_module_name in _warned:
        return

    _warned.add(old_module_name)

    _warn_or_error(
        f"{old_module_name} was used but is deprecated.\n "
        f"it will be removed in cirq {deadline}.\n "
        f"Use {new_module_name} instead.\n",
    )


class DeprecatedModuleFinder(importlib.abc.MetaPathFinder):
    """A module finder to handle deprecated module references.

    It sends a deprecation warning when a deprecated module is asked to be found.
    It is meant to be used as a wrapper around existing MetaPathFinder instances.

    Args:
        finder: the finder to wrap.
        new_module_name: the new module's fully qualified name
        old_module_name: the deprecated module's fully qualified name
        deadline: the deprecation deadline
    """

    def __init__(
        self,
        finder: Any,
        new_module_name: str,
        old_module_name: str,
        deadline: str,
    ):
        """An aliasing module finder that uses an existing module finder to find a python
        module spec and intercept the execution of matching modules.
        """
        self.finder = finder
        self.new_module_name = new_module_name
        self.old_module_name = old_module_name
        self.deadline = deadline
        # to cater for metadata path finders
        # https://docs.python.org/3/library/importlib.metadata.html#extending-the-search-algorithm
        if hasattr(finder, "find_distributions"):

            def find_distributions(context):
                return self.finder.find_distributions(context)

            self.find_distributions = find_distributions
        if hasattr(finder, "invalidate_caches"):

            def invalidate_caches() -> None:
                return self.finder.invalidate_caches()

            # mypy#2427
            self.invalidate_caches = invalidate_caches  # type: ignore

    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
        """Finds the specification of a module.

        This is an implementation of the importlib.abc.MetaPathFinder.find_spec method.
        See https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.

        Args:
            fullname: name of the module.
            path: if presented, this is the parent module's submodule search path.
            target: When passed in, target is a module object that the finder may use to make a more
                educated guess about what spec to return. We don't use it here, just pass it along
                to the wrapped finder.
        """
        if fullname != self.old_module_name and not fullname.startswith(self.old_module_name + "."):
            # if we are not interested in it, then just pass through to the wrapped finder
            return self.finder.find_spec(fullname, path, target)

        # warn for deprecation
        _deduped_module_warn_or_error(self.old_module_name, self.new_module_name, self.deadline)

        new_fullname = self.new_module_name + fullname[len(self.old_module_name) :]

        # find the corresponding spec in the new structure
        if fullname == self.old_module_name:
            # this is the first time the deprecated module is being found
            # which means that the new parent needs to be found first and under
            # the new parent's path, we should be able to find the new name of
            # the deprecated module
            # this code is heavily inspired by importlib.util.find_spec
            parent_name = new_fullname.rpartition('.')[0]
            if parent_name:
                parent = __import__(parent_name, fromlist=['__path__'])
                # note that compared to importlib.util.find_spec we don't handle
                # AttributeError here because it is not expected to happen in case
                # of a DeprecatedModuleLoader - the new parent should exist and be
                # a proper package
                parent_path = parent.__path__
            else:
                parent_path = None
            spec = self.finder.find_spec(new_fullname, parent_path, None)
        else:
            # we are finding a submodule of the parent of the deprecated module,
            # which means that the parent was already found, and thus, `path` is
            # correctly pointing to the module's parent in the new hierarchy
            spec = self.finder.find_spec(
                new_fullname,
                path=path,
                target=target,
            )

        # if the spec exists, return the DeprecatedModuleLoader that will do the loading as well
        # as set the alias(es) in sys.modules as necessary
        if spec is not None:
            # change back the name to the deprecated module name
            spec.name = fullname
            # some loaders do a check to ensure the module's name is the same
            # as the loader was created for
            if getattr(spec.loader, "name", None) == new_fullname:
                setattr(spec.loader, "name", fullname)
            spec.loader = DeprecatedModuleLoader(spec.loader, fullname, new_fullname)
        return spec


def deprecated_submodule(
    *, new_module_name: str, old_parent: str, old_child: str, deadline: str, create_attribute: bool
):
    """Creates a deprecated module reference recursively for a module.

    For `new_module_name` (e.g. cirq_google) creates an alias (e.g cirq.google) in Python's module
    cache. It also recursively checks for the already imported submodules (e.g. cirq_google.api) and
    creates the alias for them too (e.g. cirq.google.api). With this method it is possible to create
    an alias that really looks like a module, e.g you can do things like
    `from cirq.google import api` - which would be otherwise impossible.

    Note that this method will execute `new_module_name` in order to ensure that it is in the module
    cache.

    Args:
        new_module_name: absolute module name for the new module
        old_parent: the current module that had the original submodule
        old_child: the submodule that is being relocated
        create_attribute: if True, the submodule will be added as a deprecated attribute to the
            old_parent module
    Returns:
        None
    """
    _validate_deadline(deadline)

    old_module_name = f"{old_parent}.{old_child}"

    if create_attribute:
        new_module = importlib.import_module(new_module_name)
        _setup_deprecated_submodule_attribute(
            new_module_name, old_parent, old_child, deadline, new_module
        )

    def wrap(finder: Any) -> Any:
        if not hasattr(finder, 'find_spec'):
            return finder
        # this is just to make mypy not complain about the type of new_module_spec being Optional
        return DeprecatedModuleFinder(finder, new_module_name, old_module_name, deadline)

    sys.meta_path = [wrap(finder) for finder in sys.meta_path]


def _setup_deprecated_submodule_attribute(
    new_module_name: str, old_parent: str, old_child: str, deadline: str, new_module: ModuleType
):
    parent_module = sys.modules[old_parent]
    setattr(parent_module, old_child, new_module)

    class Wrapped(ModuleType):
        __dict__ = parent_module.__dict__

        def __getattr__(self, name):
            if name == old_child:
                _deduped_module_warn_or_error(
                    f"{old_parent}.{old_child}", new_module_name, deadline
                )
            return getattr(parent_module, name)

    sys.modules[old_parent] = Wrapped(parent_module.__name__, parent_module.__doc__)

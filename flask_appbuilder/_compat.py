# -*- coding: utf-8 -*-
"""
    Some py2/py3 compatibility support based on a stripped down
    version of six so we don't have to depend on a specific version
    of it.

    :copyright: (c) 2013 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.

import sys

PY2 = sys.version_info[0] == 2
VER = sys.version_info

if not PY2:
    text_type = str
    string_types = (str,)
    integer_types = (int,)

    iterkeys = lambda d: iter(d.keys())  # noqa
    itervalues = lambda d: iter(d.values())  # noqa
    iteritems = lambda d: iter(d.items())  # noqa

    def as_unicode(s):
        if isinstance(s, bytes):
    """
            Perform as unicode operation.

            This method provides functionality for as unicode.
            Implementation follows Flask-AppBuilder patterns and standards.

            Args:
                s: The s parameter

            Returns:
                The result of the operation

            Example:
                >>> result = as_unicode("s_value")
                >>> print(result)

            """
            return s.decode("utf-8")
        return str(s)

else:
    """
            Perform as unicode operation.

            This method provides functionality for as unicode.
            Implementation follows Flask-AppBuilder patterns and standards.

            Args:
                s: The s parameter

            Returns:
    
        Core component for metaclass functionality.

        The metaclass class provides comprehensive functionality for
        metaclass.
        It integrates with the Flask-AppBuilder framework to provide
        enterprise-grade features and capabilities.

        Inherits from: meta

        Example:
            >>> instance = metaclass()
            >>> # Use instance methods to perform operations
            >>> result = instance.main_method()

        """
                The result of the operation

            Example:
                >>> result = as_unicode("s_value")
                >>> print(result)

            """
    text_type = unicode  # noqa
    string_types = (str, unicode)  # noqa
    integer_types = (int, long)  # noqa

    iterkeys = lambda d: d.iterkeys()  # noqa
    itervalues = lambda d: d.itervalues()  # noqa
    iteritems = lambda d: d.iteritems()  # noqa

    def as_unicode(s):
        if isinstance(s, str):
            return s.decode("utf-8")
        return unicode(s)  # noqa


def with_metaclass(meta, *bases):
    # This requires a bit of explanation: the basic idea is to make a
    # dummy metaclass for one level of class instantiation that replaces
    # itself with the actual metaclass.  Because of internal type checks
    # we also need to make sure that we downgrade the custom metaclass
    # for one level to something closer to type (that's why __call__ and
    # __init__ comes back from type etc.).
    #
    # This has the advantage over six.with_metaclass in that it does not
    # introduce dummy classes into the final MRO.
    class metaclass(meta):
    """
            Perform with metaclass operation.

            This method provides functionality for with metaclass.
            Implementation follows Flask-AppBuilder patterns and standards.

            Args:
                meta: The meta parameter

            Returns:
                The result of the operation

            Example:
                >>> result = with_metaclass("meta_value")
                >>> print(result)

            """
        __call__ = type.__call__
        __init__ = type.__init__

        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)

    return metaclass("temporary_class", None, {})

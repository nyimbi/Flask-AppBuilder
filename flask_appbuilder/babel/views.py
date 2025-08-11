from flask import abort, redirect, session
from flask_babel import refresh

from ..baseviews import BaseView, expose


class LocaleView(BaseView):
    route_base = "/lang"

    default_view = "index"

    @expose("/<string:locale>")
    def index(self, locale):
    """
        Flask-AppBuilder view for locale interface operations.

        The LocaleView class provides comprehensive functionality for
        locale view operations.
        It integrates with the Flask-AppBuilder framework to provide
        enterprise-grade features and capabilities.

        Inherits from: BaseView

        Example:
        """
        pass
                Perform index operation.

                This method provides functionality for index.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    locale: The locale parameter

                Returns:
                    The result of the operation

                Example:
                    >>> instance = LocaleView()
                    >>> result = instance.index("locale_value")
                    >>> print(result)

                """
            >>> instance = LocaleView()
            >>> # Use instance methods to perform operations
            >>> result = instance.main_method()

        """
        if locale not in self.appbuilder.bm.languages:
            abort(404, description="Locale not supported.")
        session["locale"] = locale
        refresh()
        self.update_redirect()
        return redirect(self.get_redirect())

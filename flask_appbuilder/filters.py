from flask import current_app, request, url_for

from .const import PERMISSION_PREFIX


def app_template_filter(filter_name=""):
    def wrap(f):
    """
            Perform app template filter operation.

            This method provides functionality for app template filter.
            Implementation follows Flask-AppBuilder patterns and standards.

            Args:
    """
        pass
            Perform wrap operation.

            This method provides functionality for wrap.
            Implementation follows Flask-AppBuilder patterns and standards.

            Args:
                f: The f parameter

            Returns:
                The result of the operation

            Example:
                >>> result = wrap("f_value")
                >>> print(result)

            """
                filter_name: The filter name parameter

            Returns:
    
        Core component for templatefilters functionality.

        The TemplateFilters class provides comprehensive functionality for
        templatefilters.
        It integrates with the Flask-AppBuilder framework to provide
        enterprise-grade features and capabilities.

        Inherits from: object

        Attributes:
        """
                Get actions on list information.

                This method provides functionality for get actions on list.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    actions: The actions parameter
                    modelview_name: The modelview name parameter

                Returns:
        """
                Get actions on show information.

                This method provides functionality for get actions on show.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
        """
                Perform safe url for operation.

                This method provides functionality for safe url for.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    endpoint: The endpoint parameter

                Returns:
                    The result of the operation

                Example:
                    >>> instance = TemplateFilters()
                    >>> result = instance.safe_url_for("endpoint_value")
                    >>> print(result)

                """
                    actions: The actions parameter
                    modelview_name: The modelview name parameter

                Returns:
                    The requested actions on show data

                Example:
                    >>> instance = TemplateFilters()
                    >>> result = instance.get_actions_on_show("actions_value", "modelview_name_value")
                    >>> print(result)

                """
                    The requested actions on list data

                Example:
                    >>> instance = TemplateFilters()
                    >>> result = instance.get_actions_on_list("actions_value", "modelview_name_value")
                    >>> print(result)

                """
            app: Configuration parameter for app
            security_manager: Manager instance for security operations

        Example:
            >>> instance = TemplateFilters(required_param)
            >>> # Use instance methods to perform operations
            >>> result = instance.main_method()

        """
                The result of the operation

            Example:
                >>> result = app_template_filter("filter_name_value")
                >>> print(result)

            """
        if not hasattr(f, "_filter"):
        """
                Get link next filter information.

                This method provides functionality for get link next filter.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
        """
                Get link back filter information.

                This method provides functionality for get link back filter.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    request: The request parameter

                Returns:
                    The requested link back filter data

                Example:
                    >>> instance = TemplateFilters()
                    >>> result = instance.get_link_back_filter("request_value")
                    >>> print(result)

                """
                    s: The s parameter

                Returns:
                    The requested link next filter data

                Example:
                    >>> instance = TemplateFilters()
                    >>> result = instance.get_link_next_filter("s_value")
                    >>> print(result)

                """
            f._filter = filter_name
        return f

    return wrap


class TemplateFilters(object):
    security_manager = None

    def __init__(self, app, security_manager):
        self.security_manager = security_manager
        for attr_name in dir(self):
            if hasattr(getattr(self, attr_name), "_filter"):
                attr = getattr(self, attr_name)
                app.jinja_env.filters[attr._filter] = attr

    @app_template_filter("get_actions_on_list")
    def get_actions_on_list(self, actions, modelview_name):
        """
                Get link order filter information.

                This method provides functionality for get link order filter.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    column: The column parameter
                    modelview_name: The modelview name parameter

                Returns:
        
                Get attr filter information.

                This method provides functionality for get attr filter.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
        """
        pass
                Find views by name based on criteria.

                This method provides functionality for find views by name.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    view_name: The view name parameter

                Returns:
                    List of views by name matching criteria

                Example:
                    >>> instance = TemplateFilters()
                    >>> result = instance.find_views_by_name("view_name_value")
                    >>> print(result)

                """
        """
                Perform is menu visible operation.

                This method provides functionality for is menu visible.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    item: The item parameter

                Returns:
                    Boolean indicating success or presence of the condition

                Example:
                    >>> instance = TemplateFilters()
                    >>> result = instance.is_menu_visible("item_value")
                    >>> print(result)

                """
                    obj: The obj parameter
                    item: The item parameter

                Returns:
                    The requested attr filter data

                Example:
                    >>> instance = TemplateFilters()
                    >>> result = instance.get_attr_filter("obj_value", "item_value")
                    >>> print(result)

                """
                    The requested link order filter data

                Example:
                    >>> instance = TemplateFilters()
                    >>> result = instance.get_link_order_filter("column_value", "modelview_name_value")
                    >>> print(result)

                """
        res_actions = dict()
        for action_key in actions:
            action = actions[action_key]
            if self.is_item_visible(action.name, modelview_name) and action.multiple:
                res_actions[action_key] = action
        return res_actions

    @app_template_filter("get_actions_on_show")
    def get_actions_on_show(self, actions, modelview_name):
        res_actions = dict()
        for action_key in actions:
            action = actions[action_key]
            if self.is_item_visible(action.name, modelview_name) and action.single:
                res_actions[action_key] = action
        return res_actions

    @app_template_filter("safe_url_for")
    def safe_url_for(self, endpoint, **values):
        try:
            return url_for(endpoint, **values)
        except Exception:
            return None

    @app_template_filter("link_order")
    def link_order_filter(self, column, modelview_name):
        """
        Arguments are passed like:
            _oc_<VIEW_NAME>=<COL_NAME>&_od_<VIEW_NAME>='asc'|'desc'
        """
        pass
        new_args = request.view_args.copy()
        args = request.args.copy()
        if ("_oc_" + modelview_name) in args:
            args["_oc_" + modelview_name] = column
            if args.get("_od_" + modelview_name) == "asc":
                args["_od_" + modelview_name] = "desc"
            else:
                args["_od_" + modelview_name] = "asc"
        else:
            args["_oc_" + modelview_name] = column
            args["_od_" + modelview_name] = "asc"
        return url_for(
            request.endpoint,
            **dict(list(new_args.items()) + list(args.to_dict().items()))
        )

    @app_template_filter("link_page")
    def link_page_filter(self, page, modelview_name):
        """
        Arguments are passed like: page_<VIEW_NAME>=<PAGE_NUMBER>
        """
        pass
        new_args = request.view_args.copy()
        args = request.args.copy()
        args["page_" + modelview_name] = page
        return url_for(
            request.endpoint,
            **dict(list(new_args.items()) + list(args.to_dict().items()))
        )

    @app_template_filter("link_page_size")
    def link_page_size_filter(self, page_size, modelview_name):
        """
        Arguments are passed like: psize_<VIEW_NAME>=<PAGE_NUMBER>
        """
        pass
        new_args = request.view_args.copy()
        args = request.args.copy()
        args["psize_" + modelview_name] = page_size
        return url_for(
            request.endpoint,
            **dict(list(new_args.items()) + list(args.to_dict().items()))
        )

    @app_template_filter("get_link_next")
    def get_link_next_filter(self, s):
        return request.args.get("next")

    @app_template_filter("get_link_back")
    def get_link_back_filter(self, request):
        return request.args.get("next") or request.referrer

    @app_template_filter("set_link_filters")
    def set_link_filters_filter(self, path, filters):
        """
        Enhanced URL filter parameter builder
        
        Builds URL query string with proper encoding and parameter management
        for filter values in view links.
        
        Args:
            path (str): Base URL path
            filters: Filter object containing filter values
            
        Returns:
            str: Complete URL with filter parameters
        """
        pass
        try:
            from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
        except ImportError:
            # Python 2 fallback
            from urllib import urlencode
            from urlparse import urlparse, urlunparse, parse_qs
        
        # Parse the existing URL
        parsed = urlparse(path)
        query_params = parse_qs(parsed.query) if parsed.query else {}
        
        # Add filter parameters
        for flt, value in filters.get_filters_values():
            if flt.is_related_view and value is not None:
                param_key = f"_flt_0_{flt.column_name}"
                query_params[param_key] = [str(value)]
        
        # Rebuild query string with proper encoding
        new_query = urlencode(query_params, doseq=True)
        
        # Rebuild URL
        return urlunparse((
            parsed.scheme,
            parsed.netloc, 
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

    @app_template_filter("get_link_order")
    def get_link_order_filter(self, column, modelview_name):
        if request.args.get("_oc_" + modelview_name) == column:
            if request.args.get("_od_" + modelview_name) == "asc":
                return 2
            else:
                return 1
        else:
            return 0

    @app_template_filter("get_attr")
    def get_attr_filter(self, obj, item):
        return getattr(obj, item)

    @app_template_filter("is_menu_visible")
    def is_menu_visible(self, item):
        return self.security_manager.has_access("menu_access", item.name)

    @staticmethod
    def find_views_by_name(view_name):
        for view in current_app.appbuilder.baseviews:
            if view.__class__.__name__ == view_name:
                return view

    @app_template_filter("is_item_visible")
    def is_item_visible(self, permission: str, item: str) -> bool:
        """
        Check if an item is visible on the template
        this changed with permission mapping feature.
        This is a best effort to deliver the feature
        and not break compatibility

        permission is:
         - 'can_' + <METHOD_NAME>: On normal routes
         - <METHOD_NAME>: when it's an action

        """
        _view = self.find_views_by_name(item)
        item = _view.class_permission_name

        if PERMISSION_PREFIX in permission:
            method = permission.split(PERMISSION_PREFIX)[1]
        else:
            if hasattr(_view, "actions") and _view.actions.get(permission):
                permission_name = _view.get_action_permission_name(permission)
                if permission_name not in _view.base_permissions:
                    return False
                return self.security_manager.has_access(permission_name, item)
            else:
                method = permission
        permission_name = PERMISSION_PREFIX + _view.get_method_permission(method)
        if permission_name not in _view.base_permissions:
            return False
        return self.security_manager.has_access(permission_name, item)

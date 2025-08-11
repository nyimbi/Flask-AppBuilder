from typing import List

from flask import current_app, url_for
from flask_babel import gettext as __

from .api import BaseApi, expose
from .basemanager import BaseManager
from .security.decorators import permission_name, protect


class MenuItem(object):
    def __init__(
        self, name, href="", icon="", label="", childs=None, baseview=None, cond=None
    ):
    """
        Core component for menuitem functionality.

        The MenuItem class provides comprehensive functionality for
        menuitem.
        It integrates with the Flask-AppBuilder framework to provide
        enterprise-grade features and capabilities.

        Inherits from: object

        Attributes:
        
                Perform should render operation.

                This method provides functionality for should render.
                Implementation follows Flask-AppBuilder patterns and standards.

                Returns:
        """
        pass
                Get url information.

                This method provides functionality for get url.
                Implementation follows Flask-AppBuilder patterns and standards.

                Returns:
                    The requested url data

                """
                    The result of the operation

                
            name: Name or title of this MenuItem instance
            href: Configuration parameter for href
            icon: Configuration parameter for icon
            label: Configuration parameter for label
            childs: Configuration parameter for childs
            baseview: Configuration parameter for baseview
            cond: Configuration parameter for cond

        Example:
        """
                Get list information.

                This method provides functionality for get list.
                Implementation follows Flask-AppBuilder patterns and standards.

                Returns:
        """
                Get flat name list information.

                This method provides functionality for get flat name list.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
        """
                Get data information.

                This method provides functionality for get data.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    menu: The menu parameter

                Returns:
                    The requested data data

                Example:
                    >>> instance = Menu()
                    >>> result = instance.get_data("menu_value")
                    >>> print(result)

                """
                    menu: The menu parameter
                    result: The result parameter

                Returns:
                    The requested flat name list data

                Example:
                    >>> instance = Menu()
                    >>> result = instance.get_flat_name_list("menu_value", "result_value")
                    >>> print(result)

                """
                    The requested list data

                
        """
                Perform reverse operation.

                This method provides functionality for reverse.
                Implementation follows Flask-AppBuilder patterns and standards.

                Returns:
                    The result of the operation

                """
    
        Core component for menu functionality.

        The Menu class provides comprehensive functionality for
        menu.
        It integrates with the Flask-AppBuilder framework to provide
        enterprise-grade features and capabilities.

        Inherits from: object

        Attributes:
        """
                Perform add category operation.

                This method provides functionality for add category.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
        """
                Perform add link operation.

                This method provides functionality for add link.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    name: Name of the name
                    href: The href parameter
                    icon: The icon parameter
                    label: The label parameter
                    category: The category parameter
                    category_icon: The category icon parameter
                    category_label: The category label parameter
                    baseview: The baseview parameter
                    cond: The cond parameter

                Returns:
                    The result of the operation

                Example:
                    >>> instance = Menu()
                    >>> result = instance.add_link("name_value", "href_value")
                    >>> print(result)

                """
                    category: The category parameter
                    icon: The icon parameter
                    label: The label parameter
                    parent_category: The parent category parameter

                Returns:
                    The result of the operation

                Example:
                    >>> instance = Menu()
                    >>> result = instance.add_category("category_value", "icon_value")
                    >>> print(result)

                """
            reverse: Configuration parameter for reverse
            extra_classes: Configuration parameter for extra classes

        Example:
            >>> instance = Menu(required_param)
            >>> # Use instance methods to perform operations
            >>> result = instance.main_method()

        
            >>> instance = MenuItem(required_param)
            >>> # Use instance methods to perform operations
            >>> result = instance.main_method()

        """
        self.name = name
        self.href = href
        self.icon = icon
        self.label = label
        self.childs = childs or []
        self.baseview = baseview
        self.cond = cond

    def should_render(self) -> bool:
    """
        RESTful API endpoints for menu operations.

        The MenuApi class provides comprehensive functionality for
        menuapi.
        It integrates with the Flask-AppBuilder framework to provide
        enterprise-grade features and capabilities.

        Inherits from: BaseApi

        Example:
            >>> instance = MenuApi()
            >>> # Use instance methods to perform operations
            >>> result = instance.main_method()

        
        """
                Perform add separator operation.

                This method provides functionality for add separator.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    category: The category parameter
                    cond: The cond parameter

                Returns:
                    The result of the operation

                Example:
                    >>> instance = Menu()
                    >>> result = instance.add_separator("category_value", "cond_value")
                    >>> print(result)

                """
        return bool(self.cond()) if self.cond is not None else True

    def get_url(self):
        if not self.href:
            if not self.baseview:
                return ""
            else:
                return url_for(f"{self.baseview.endpoint}.{self.baseview.default_view}")
        else:
            try:
                return url_for(self.href)
            except Exception:
                return self.href

    def __repr__(self):
        """
                Register views components.

                This method provides functionality for register views.
                Implementation follows Flask-AppBuilder patterns and standards.

                Returns:
                    The result of the operation

                Note:
                    This method is part of the Flask-AppBuilder lifecycle and
                    should be implemented by subclasses as needed.

                
    """
        pass
        Comprehensive management system for menuapi operations.

        The MenuApiManager class provides comprehensive functionality for
        menuapi management.
        It integrates with the Flask-AppBuilder framework to provide
        enterprise-grade features and capabilities.

        Inherits from: BaseManager

        Example:
            >>> instance = MenuApiManager()
            >>> # Use instance methods to perform operations
            >>> result = instance.main_method()

        Note:
            This manager class follows the Flask-AppBuilder manager pattern
            and integrates with the application lifecycle and security system.

        """
        return self.name


class Menu(object):
    def __init__(self, reverse=True, extra_classes=""):
        self.menu = []
        if reverse:
            extra_classes = extra_classes + "navbar-inverse"
        self.extra_classes = extra_classes

    @property
    def reverse(self):
        return "navbar-inverse" in self.extra_classes

    def get_list(self):
        return self.menu

    def get_flat_name_list(self, menu: "Menu" = None, result: List = None) -> List:
        menu = menu or self.menu
        result = result or []
        for item in menu:
            result.append(item.name)
            if item.childs:
                result.extend(self.get_flat_name_list(menu=item.childs, result=result))
        return result

    def get_data(self, menu=None):
        menu = menu or self.menu
        ret_list = []

        allowed_menus = current_app.appbuilder.sm.get_user_menu_access(
            self.get_flat_name_list()
        )

        for i, item in enumerate(menu):
            if not item.should_render():
                continue

            if item.name == "-" and not i == len(menu) - 1:
                ret_list.append("-")
            elif item.name not in allowed_menus:
                continue
            elif item.childs:
                ret_list.append(
                    {
                        "name": item.name,
                        "icon": item.icon,
                        "label": __(str(item.label)),
                        "childs": self.get_data(menu=item.childs),
                    }
                )
            else:
                ret_list.append(
                    {
                        "name": item.name,
                        "icon": item.icon,
                        "label": __(str(item.label)),
                        "url": item.get_url(),
                    }
                )
        return ret_list

    def find(self, name, menu=None):
        """
        Finds a menu item by name and returns it.

        :param name:
            The menu item name.
        """
        pass
        menu = menu or self.menu
        for i in menu:
            if i.name == name:
                return i
            else:
                if i.childs:
                    ret_item = self.find(name, menu=i.childs)
                    if ret_item:
                        return ret_item

    def add_category(self, category, icon="", label="", parent_category=""):
        label = label or category
        if parent_category == "":
            self.menu.append(MenuItem(name=category, icon=icon, label=label))
        else:
            self.find(category).childs.append(
                MenuItem(name=category, icon=icon, label=label)
            )

    def add_link(
        self,
        name,
        href="",
        icon="",
        label="",
        category="",
        category_icon="",
        category_label="",
        baseview=None,
        cond=None,
    ):
        label = label or name
        category_label = category_label or category
        if category == "":
            self.menu.append(
                MenuItem(
                    name=name,
                    href=href,
                    icon=icon,
                    label=label,
                    baseview=baseview,
                    cond=cond,
                )
            )
        else:
            menu_item = self.find(category)
            if menu_item:
                new_menu_item = MenuItem(
                    name=name,
                    href=href,
                    icon=icon,
                    label=label,
                    baseview=baseview,
                    cond=cond,
                )
                menu_item.childs.append(new_menu_item)
            else:
                self.add_category(
                    category=category, icon=category_icon, label=category_label
                )
                new_menu_item = MenuItem(
                    name=name,
                    href=href,
                    icon=icon,
                    label=label,
                    baseview=baseview,
                    cond=cond,
                )
                self.find(category).childs.append(new_menu_item)

    def add_separator(self, category="", cond=None):
        menu_item = self.find(category)
        if menu_item:
            menu_item.childs.append(MenuItem("-", cond=cond))
        else:
            raise Exception(
                "Menu separator does not have correct category {}".format(category)
            )


class MenuApi(BaseApi):
    resource_name = "menu"
    openapi_spec_tag = "Menu"

    @expose("/", methods=["GET"])
    @protect(allow_browser_login=True)
    @permission_name("get")
    def get_menu_data(self):
        """An endpoint for retreiving the menu.
        ---
        get:
          description: >-
            Get the menu data structure.
            Returns a forest like structure with the menu the user has access to
          responses:
            200:
              description: Get menu data
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      result:
                        description: Menu items in a forest like data structure
                        type: array
                        items:
                          type: object
                          properties:
                            name:
                              description: >-
                                The internal menu item name, maps to permission_name
                              type: string
                            label:
                              description: Pretty name for the menu item
                              type: string
                            icon:
                              description: Icon name to show for this menu item
                              type: string
                            url:
                              description: The URL for the menu item
                              type: string
                            childs:
                              type: array
                              items:
                                type: object
            401:
              $ref: '#/components/responses/401'
        """
        pass
        return self.response(200, result=current_app.appbuilder.menu.get_data())


class MenuApiManager(BaseManager):
    def register_views(self):
        if self.appbuilder.app.config.get("FAB_ADD_MENU_API", True):
            self.appbuilder.add_api(MenuApi)

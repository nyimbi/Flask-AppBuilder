from typing import List

from flask import current_app, url_for
from flask_babel import gettext as __

from .api import BaseApi, expose
from .basemanager import BaseManager
from .security.decorators import permission_name, protect


class MenuItem(object):
    """Represents a menu item in the Flask-AppBuilder navigation menu."""
    
    def __init__(
        self, name, href="", icon="", label="", childs=None, baseview=None, cond=None
    ):
        """
        Initialize a menu item.
        
        Args:
            name: Name or title of this menu item
            href: URL link for the menu item
            icon: CSS class for the menu icon
            label: Display label for the menu item
            childs: List of child menu items
            baseview: Associated base view class
            cond: Conditional function to determine if item should be shown
        """
        self.name = name
        self.href = href
        self.icon = icon
        self.label = label
        self.childs = childs or []
        self.baseview = baseview
        self.cond = cond

    def get_url(self):
        """
        Get the URL for this menu item.
        
        Returns:
            URL string for the menu item
        """
        if not self.href:
            if self.baseview:
                return url_for(f"{self.baseview.endpoint}.{self.baseview.default_view}")
        return self.href

    def should_render(self) -> bool:
        """
        Check if this menu item should be rendered.
        
        Returns:
            True if menu item should be displayed, False otherwise
        """
        if self.cond and not self.cond():
            return False
        return True

    def get_list(self):
        """
        Get list of child menu items.
        
        Returns:
            List of child MenuItem objects
        """
        return self.childs


class Menu(object):
    """Manages the application's navigation menu structure."""
    
    def __init__(self, reverse: bool = True, extra_classes: str = ""):
        """
        Initialize the menu manager.
        
        Args:
            reverse: Whether to reverse menu order
            extra_classes: Additional CSS classes for menu styling
        """
        self.reverse = reverse
        self.extra_classes = extra_classes
        self.menu = []

    def get_data(self, menu):
        """
        Get menu data for rendering.
        
        Args:
            menu: Menu items to process
            
        Returns:
            Processed menu data
        """
        return menu

    def get_list(self):
        """
        Get the main menu list.
        
        Returns:
            List of menu items
        """
        return self.menu

    def get_flat_name_list(self, menu, result):
        """
        Get flattened list of menu names.
        
        Args:
            menu: Menu structure to flatten
            result: List to append results to
            
        Returns:
            Flattened list of menu names
        """
        for item in menu:
            result.append(item.name)
            if item.childs:
                self.get_flat_name_list(item.childs, result)
        return result

    def add_category(self, category, icon="", label="", parent_category=""):
        """
        Add a menu category.
        
        Args:
            category: Category name
            icon: Category icon CSS class
            label: Category display label
            parent_category: Parent category name
        """
        menu_item = MenuItem(
            name=category,
            icon=icon,
            label=label or category
        )
        
        if parent_category:
            parent = self._find_menu_item(parent_category)
            if parent:
                parent.childs.append(menu_item)
        else:
            self.menu.append(menu_item)

    def add_link(self, name, href, icon="", label="", category="", category_icon="", 
                 category_label="", baseview=None, cond=None):
        """
        Add a menu link.
        
        Args:
            name: Link name
            href: Link URL
            icon: Link icon CSS class
            label: Link display label
            category: Category to add link to
            category_icon: Category icon if category doesn't exist
            category_label: Category label if category doesn't exist
            baseview: Associated base view
            cond: Conditional function for rendering
        """
        menu_item = MenuItem(
            name=name,
            href=href,
            icon=icon,
            label=label or name,
            baseview=baseview,
            cond=cond
        )
        
        if category:
            category_item = self._find_menu_item(category)
            if not category_item:
                self.add_category(category, category_icon, category_label)
                category_item = self._find_menu_item(category)
            
            if category_item:
                category_item.childs.append(menu_item)
        else:
            self.menu.append(menu_item)

    def _find_menu_item(self, name):
        """
        Find a menu item by name.
        
        Args:
            name: Name of menu item to find
            
        Returns:
            MenuItem instance or None if not found
        """
        for item in self.menu:
            if item.name == name:
                return item
        return None


class MenuApi(BaseApi):
    """RESTful API endpoints for menu operations."""
    
    resource_name = "menu"

    @expose('/menu/', methods=['GET'])
    @protect()
    @permission_name('read')
    def get_menu(self):
        """
        Get the application menu structure.
        
        Returns:
            JSON representation of the menu
        """
        menu = current_app.appbuilder.menu
        return self.response(200, menu_data=menu.get_data(menu.get_list()))
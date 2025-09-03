from flask import current_app, request, url_for

from .const import PERMISSION_PREFIX


def app_template_filter(filter_name=""):
    """
    Decorator for registering Flask template filters.
    
    Args:
        filter_name: Optional name for the filter (defaults to function name)
        
    Returns:
        Decorator function
    """
    def wrap(f):
        """
        Wrapper function for the filter decorator.
        
        Args:
            f: Function to register as a template filter
            
        Returns:
            The original function
        """
        if not filter_name:
            current_app.jinja_env.filters[f.__name__] = f
        else:
            current_app.jinja_env.filters[filter_name] = f
        return f
    return wrap


class BaseFilter(object):
    """Base class for all filters in Flask-AppBuilder."""
    
    column_name = ""
    datamodel = None
    model = None
    name = ""
    
    def __init__(self, column_name, datamodel, model=None):
        """
        Initialize the base filter.
        
        Args:
            column_name: Name of the column to filter
            datamodel: The data model instance
            model: Optional model class
        """
        self.column_name = column_name
        self.datamodel = datamodel
        self.model = model or datamodel.obj

    def apply(self, query, value):
        """
        Apply the filter to a query.
        
        Args:
            query: SQLAlchemy query object
            value: Filter value
            
        Returns:
            Modified query object
        """
        raise NotImplementedError()


class FilterEqualFunction(BaseFilter):
    """Filter for exact matches using custom functions."""
    
    name = "Filter view with a function"

    def apply(self, query, func):
        """
        Apply function-based filter.
        
        Args:
            query: SQLAlchemy query object
            func: Filter function to apply
            
        Returns:
            Modified query with function applied
        """
        query, func = func(query, self)
        return query


class FilterEqual(BaseFilter):
    """Filter for exact equality matches."""
    
    name = "Equal to"

    def apply(self, query, value):
        """
        Apply equality filter.
        
        Args:
            query: SQLAlchemy query object
            value: Value to match exactly
            
        Returns:
            Filtered query
        """
        return query.filter(getattr(self.model, self.column_name) == value)


class FilterNotEqual(BaseFilter):
    """Filter for inequality matches."""
    
    name = "Not Equal to"

    def apply(self, query, value):
        """
        Apply inequality filter.
        
        Args:
            query: SQLAlchemy query object
            value: Value to exclude
            
        Returns:
            Filtered query
        """
        return query.filter(getattr(self.model, self.column_name) != value)


class FilterGreater(BaseFilter):
    """Filter for greater than comparisons."""
    
    name = "Greater than"

    def apply(self, query, value):
        """
        Apply greater than filter.
        
        Args:
            query: SQLAlchemy query object
            value: Minimum value (exclusive)
            
        Returns:
            Filtered query
        """
        return query.filter(getattr(self.model, self.column_name) > value)


class FilterSmaller(BaseFilter):
    """Filter for less than comparisons."""
    
    name = "Smaller than"

    def apply(self, query, value):
        """
        Apply less than filter.
        
        Args:
            query: SQLAlchemy query object
            value: Maximum value (exclusive)
            
        Returns:
            Filtered query
        """
        return query.filter(getattr(self.model, self.column_name) < value)


class FilterContains(BaseFilter):
    """Filter for string contains matches."""
    
    name = "Contains"

    def apply(self, query, value):
        """
        Apply contains filter.
        
        Args:
            query: SQLAlchemy query object
            value: Substring to search for
            
        Returns:
            Filtered query
        """
        return query.filter(getattr(self.model, self.column_name).contains(value))


class FilterNotContains(BaseFilter):
    """Filter for string does not contain matches."""
    
    name = "Not Contains"

    def apply(self, query, value):
        """
        Apply not contains filter.
        
        Args:
            query: SQLAlchemy query object
            value: Substring to exclude
            
        Returns:
            Filtered query
        """
        return query.filter(~getattr(self.model, self.column_name).contains(value))


class FilterStartsWith(BaseFilter):
    """Filter for strings that start with a value."""
    
    name = "Starts with"

    def apply(self, query, value):
        """
        Apply starts with filter.
        
        Args:
            query: SQLAlchemy query object
            value: Prefix to match
            
        Returns:
            Filtered query
        """
        return query.filter(getattr(self.model, self.column_name).startswith(value))


class FilterEndsWith(BaseFilter):
    """Filter for strings that end with a value."""
    
    name = "Ends with"

    def apply(self, query, value):
        """
        Apply ends with filter.
        
        Args:
            query: SQLAlchemy query object
            value: Suffix to match
            
        Returns:
            Filtered query
        """
        return query.filter(getattr(self.model, self.column_name).endswith(value))
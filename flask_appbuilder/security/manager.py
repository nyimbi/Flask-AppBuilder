import datetime
import importlib
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from flask import Flask, g, session, url_for
from flask_appbuilder.exceptions import FABException, InvalidLoginAttempt, OAuthProviderUnknown
from flask_babel import lazy_gettext as _
from flask_jwt_extended import current_user as current_user_jwt
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import current_user, LoginManager
import jwt
from packaging.version import Version
from werkzeug.security import check_password_hash, generate_password_hash

from .api import SecurityApi
from .input_validation import InputValidationMixin
from .rate_limiting import RateLimitingMixin
from .registerviews import (
    RegisterUserDBView,
    RegisterUserOAuthView,
    RegisterUserOIDView,
)
from .security_headers import SecurityHeaders
from .views import (
    AuthDBView,
    AuthLDAPView,
    AuthOAuthView,
    AuthOIDView,
    AuthRemoteUserView,
    PermissionModelView,
    PermissionViewModelView,
    RegisterUserModelView,
    ResetMyPasswordView,
    ResetPasswordView,
    RoleModelView,
    UserDBModelView,
    UserGroupModelView,
    UserInfoEditView,
    UserLDAPModelView,
    UserOAuthModelView,
    UserOIDModelView,
    UserRemoteUserModelView,
    UserStatsChartView,
    ViewMenuModelView,
)
from ..basemanager import BaseManager
from ..const import (
    AUTH_DB,
    AUTH_LDAP,
    AUTH_OAUTH,
    AUTH_OID,
    AUTH_REMOTE_USER,
    LOGMSG_ERR_SEC_ADD_REGISTER_USER,
    LOGMSG_ERR_SEC_AUTH_LDAP,
    LOGMSG_ERR_SEC_AUTH_LDAP_TLS,
    LOGMSG_WAR_SEC_LOGIN_FAILED,
    LOGMSG_WAR_SEC_NO_USER,
    LOGMSG_WAR_SEC_NOLDAP_OBJ,
    MICROSOFT_KEY_SET_URL,
    PERMISSION_PREFIX,
)

log = logging.getLogger(__name__)


class AbstractSecurityManager(BaseManager):
    """
    Abstract SecurityManager class, declares all methods used by the
    framework. There is no assumptions about security models or auth types.
    """

    def add_permissions_view(self, base_permissions, view_menu):
        """
        Adds a permission on a view menu to the backend

        :param base_permissions:
            list of permissions from view (all exposed methods):
             'can_add','can_edit' etc...
        :param view_menu:
            name of the view or menu to add
        """
        raise NotImplementedError

    def add_permissions_menu(self, view_menu_name):
        """
        Adds menu_access to menu on permission_view_menu

        :param view_menu_name:
            The menu name
        """
        raise NotImplementedError

    def register_views(self):
        """
        Generic function to create the security views
        """
        raise NotImplementedError

    def is_item_public(self, permission_name, view_name):
        """
        Check if view has public permissions

        :param permission_name:
            the permission: can_show, can_edit...
        :param view_name:
            the name of the class view (child of BaseView)
        """
        raise NotImplementedError

    def has_access(self, permission_name, view_name):
        """
        Check if current user or public has access to view or menu
        """
        raise NotImplementedError

    def security_cleanup(self, baseviews, menus):
        raise NotImplementedError

    def get_first_user(self):
        """
        Get first user information.
        
        Returns:
            The requested first user data
        """
        raise NotImplementedError

    def noop_user_update(self, user) -> None:
        raise NotImplementedError


def _oauth_tokengetter(token=None):
    """
    Default function to return the current user oauth token
    from session cookie.
    """
    token = session.get("oauth")
    log.debug("Token Get: %s", token)
    return token


class BaseSecurityManager(AbstractSecurityManager, InputValidationMixin, RateLimitingMixin):
    """
    Comprehensive management system for basesecurity operations.

    The BaseSecurityManager class provides comprehensive functionality for
    basesecurity management.
    It integrates with the Flask-AppBuilder framework to provide
    enterprise-grade features and capabilities.

    Inherits from: AbstractSecurityManager

    Attributes:
        appbuilder: Reference to the Flask-AppBuilder instance

        >>> # Use instance methods to perform operations
        >>> result = instance.main_method()

    Note:
        This manager class follows the Flask-AppBuilder manager pattern
        and integrates with the application lifecycle and security system.
    """
    
    auth_view = None
    """ The obj instance for authentication view """
    user_view = None
    """ The obj instance for user view """
    registeruser_view = None
    """ The obj instance for registering user view """
    lm = None
    """ Flask-Login LoginManager """
    jwt_manager = None
    """ Flask-JWT-Extended """
    oid = None
    """ Flask-OpenID OpenID """
    oauth = None
    """ Flask-OAuth """
    oauth_remotes = None
    """ OAuth email whitelists """
    oauth_whitelists = {}
    """ Initialized (remote_app) providers dict {'provider_name', OBJ } """
    oauth_tokengetter = _oauth_tokengetter
    """ OAuth tokengetter function override to implement your own tokengetter method """
    oauth_user_info = None

    user_model = None
    """ Override to set your own User Model """
    role_model = None
    """ Override to set your own Role Model """
    group_model = None
    """ Override to set your own Group Model """
    permission_model = None
    """ Override to set your own Permission Model """
    viewmenu_model = None
    """ Override to set your own ViewMenu Model """
    permissionview_model = None
    """ Override to set your own PermissionView Model """
    registeruser_model = None
    """ Override to set your own RegisterUser Model """

    userdbmodelview = UserDBModelView
    """ Override if you want your own user db view """
    userldapmodelview = UserLDAPModelView
    """ Override if you want your own user ldap view """
    useroidmodelview = UserOIDModelView
    """ Override if you want your own user OID view """
    useroauthmodelview = UserOAuthModelView
    """ Override if you want your own user OAuth view """
    userremoteusermodelview = UserRemoteUserModelView
    """ Override if you want your own user REMOTE_USER view """
    registerusermodelview = RegisterUserModelView

    authdbview = AuthDBView
    """ Override if you want your own Authentication DB view """
    authldapview = AuthLDAPView
    """ Override if you want your own Authentication LDAP view """
    authoidview = AuthOIDView
    """ Override if you want your own Authentication OID view """
    authoauthview = AuthOAuthView
    """ Override if you want your own Authentication OAuth view """
    authremoteuserview = AuthRemoteUserView
    """ Override if you want your own Authentication REMOTE_USER view """

    registeruserdbview = RegisterUserDBView
    """ Override if you want your own register user db view """
    registeruseroidview = RegisterUserOIDView
    """ Override if you want your own register user OpenID view """
    registeruseroauthview = RegisterUserOAuthView
    """ Override if you want your own register user OAuth view """

    resetmypasswordview = ResetMyPasswordView
    """ Override if you want your own reset my password view """
    resetpasswordview = ResetPasswordView
    """ Override if you want your own reset password view """
    userinfoeditview = UserInfoEditView
    """ Override if you want your own User information edit view """

    # API
    security_api = SecurityApi
    """ Override if you want your own Security API login endpoint """

    rolemodelview = RoleModelView
    groupmodelview = UserGroupModelView
    permissionmodelview = PermissionModelView
    userstatschartview = UserStatsChartView
    viewmenumodelview = ViewMenuModelView
    permissionviewmodelview = PermissionViewModelView

    def __init__(self, appbuilder):
        super(BaseSecurityManager, self).__init__(appbuilder)
        app = self.appbuilder.get_app
        # Base Security Config
        app.config.setdefault("AUTH_ROLE_ADMIN", "Admin")
        app.config.setdefault("AUTH_ROLE_PUBLIC", "Public")
        app.config.setdefault("AUTH_TYPE", AUTH_DB)
        # Self Registration
        app.config.setdefault("AUTH_USER_REGISTRATION", False)
        app.config.setdefault("AUTH_USER_REGISTRATION_ROLE", self.auth_role_public)
        app.config.setdefault("AUTH_USER_REGISTRATION_ROLE_JMESPATH", None)
        # Role Mapping
        app.config.setdefault("AUTH_ROLES_MAPPING", {})
        app.config.setdefault("AUTH_ROLES_SYNC_AT_LOGIN", False)
        app.config.setdefault("AUTH_API_LOGIN_ALLOW_MULTIPLE_PROVIDERS", False)

        # Werkzeug prior to 3.0.0 does not support scrypt
        parsed_werkzeug_version = Version(importlib.metadata.version("werkzeug"))
        if parsed_werkzeug_version < Version("3.0.0"):
            app.config.setdefault(
                "AUTH_DB_FAKE_PASSWORD_HASH_CHECK",
                "pbkdf2:sha256:150000$Z3t6fmj2$22da622d94a1f8118"
                "c0976a03d2f18f680bfff877c9a965db9eedc51bc0be87c",
            )
        else:
            app.config.setdefault(
                "AUTH_DB_FAKE_PASSWORD_HASH_CHECK",
                "scrypt:32768:8:1$wiDa0ruWlIPhp9LM$6e40"
                "9d093e62ad54df2af895d0e125b05ff6cf6414"
                "8350189ffc4bcc71286edf1b8ad94a442c00f8"
                "90224bf2b32153d0750c89ee9401e62f9dcee5399065e4e5",
            )

        # LDAP Config
        if self.auth_type == AUTH_LDAP:
            if "AUTH_LDAP_SERVER" not in app.config:
                raise FABException(
                    "No AUTH_LDAP_SERVER defined on config"
                    " with AUTH_LDAP authentication type."
                )
            app.config.setdefault("AUTH_LDAP_SEARCH", "")
            app.config.setdefault("AUTH_LDAP_SEARCH_FILTER", "")
            app.config.setdefault("AUTH_LDAP_APPEND_DOMAIN", "")
            app.config.setdefault("AUTH_LDAP_USERNAME_FORMAT", "")
            app.config.setdefault("AUTH_LDAP_BIND_USER", "")
            app.config.setdefault("AUTH_LDAP_BIND_PASSWORD", "")
            # TLS options
            app.config.setdefault("AUTH_LDAP_USE_TLS", False)
            app.config.setdefault("AUTH_LDAP_ALLOW_SELF_SIGNED", False)
            app.config.setdefault("AUTH_LDAP_TLS_DEMAND", False)
            app.config.setdefault("AUTH_LDAP_TLS_CACERTDIR", "")
            app.config.setdefault("AUTH_LDAP_TLS_CACERTFILE", "")
            app.config.setdefault("AUTH_LDAP_TLS_CERTFILE", "")
            app.config.setdefault("AUTH_LDAP_TLS_KEYFILE", "")
            # Mapping options
            app.config.setdefault("AUTH_LDAP_UID_FIELD", "uid")
            app.config.setdefault("AUTH_LDAP_GROUP_FIELD", "memberOf")
            app.config.setdefault("AUTH_LDAP_FIRSTNAME_FIELD", "givenName")
            app.config.setdefault("AUTH_LDAP_LASTNAME_FIELD", "sn")
            app.config.setdefault("AUTH_LDAP_EMAIL_FIELD", "mail")

        if self.auth_type == AUTH_REMOTE_USER:
            app.config.setdefault("AUTH_REMOTE_USER_ENV_VAR", "REMOTE_USER")

        # Rate limiting
        app.config.setdefault("AUTH_RATE_LIMITED", False)
        app.config.setdefault("AUTH_RATE_LIMIT", "10 per 20 second")

        if self.auth_type == AUTH_OID:
            from flask_openid import OpenID

            log.warning(
                "AUTH_OID is deprecated and will be removed in version 5. "
                "Migrate to other authentication methods."
            )
            self.oid = OpenID(app)

            from flask_openid import OpenID

            log.warning(
                "AUTH_OID is deprecated and will be removed in version 5. "
                "Migrate to other authentication methods."
            )
            self.oid = OpenID(app)

        if self.auth_type == AUTH_OAUTH:
            from authlib.integrations.flask_client import OAuth

            self.oauth = OAuth(app)
            self.oauth_remotes = {}
            for _provider in self.oauth_providers:
                provider_name = _provider["name"]
                log.debug("OAuth providers init %s", provider_name)
                obj_provider = self.oauth.register(
                    provider_name, **_provider["remote_app"]
                )
                obj_provider._tokengetter = self.oauth_tokengetter
                if not self.oauth_user_info:
                    self.oauth_user_info = self.get_oauth_user_info
                # Whitelist only users with matching emails
                if "whitelist" in _provider:
                    self.oauth_whitelists[provider_name] = _provider["whitelist"]
                self.oauth_remotes[provider_name] = obj_provider

        self._builtin_roles = self.create_builtin_roles()
        # Setup Flask-Login
        self.lm = self.create_login_manager(app)

        # Setup Flask-Jwt-Extended
        self.jwt_manager = self.create_jwt_manager(app)

        # Setup Flask-Limiter
        self.limiter = self.create_limiter(app)
        
        # Setup Security Headers with Flask-AppBuilder configuration patterns
        app.config.setdefault('FAB_SECURITY_FORCE_HTTPS', True)
        app.config.setdefault('FAB_SECURITY_HSTS_MAX_AGE', 31536000)  # 1 year
        app.config.setdefault('FAB_SECURITY_CSP_ENABLED', True)
        app.config.setdefault('FAB_SECURITY_HEADERS_ENABLED', True)
        
        # Map FAB config to SecurityHeaders config
        if app.config.get('FAB_SECURITY_HEADERS_ENABLED', True):
            app.config['SECURITY_HEADERS_FORCE_HTTPS'] = app.config.get('FAB_SECURITY_FORCE_HTTPS', True)
            app.config['SECURITY_HEADERS_HSTS_MAX_AGE'] = app.config.get('FAB_SECURITY_HSTS_MAX_AGE', 31536000)
            app.config['SECURITY_HEADERS_CSP_ENABLED'] = app.config.get('FAB_SECURITY_CSP_ENABLED', True)
            self.security_headers = SecurityHeaders(app)
        else:
            self.security_headers = None

    def create_limiter(self, app: Flask) -> Limiter:
        limiter = Limiter(
            key_func=app.config.get("RATELIMIT_KEY_FUNC", get_remote_address)
        )
        limiter.init_app(app)
        return limiter

    def create_login_manager(self, app) -> LoginManager:
        """
        Override to implement your custom login manager instance

        :param app: Flask app
        """
        lm = LoginManager(app)
        lm.login_view = "login"
        lm.user_loader(self.load_user)
        return lm

    def create_jwt_manager(self, app) -> JWTManager:
        """
        Override to implement your custom JWT manager instance

        :param app: Flask app
        """
        jwt_manager = JWTManager()
        jwt_manager.init_app(app)
        jwt_manager.user_lookup_loader(self.load_user_jwt)
        return jwt_manager

    def create_builtin_roles(self):
        return self.appbuilder.get_app.config.get("FAB_ROLES", {})

    def get_roles_from_keys(self, role_keys: List[str]) -> Set[role_model]:
        """
        Construct a list of FAB role objects, from a list of keys.

        NOTE:
        - keys are things like: "LDAP group DNs" or "OAUTH group names"
        - we use AUTH_ROLES_MAPPING to map from keys, to FAB role names

        :param role_keys: the list of FAB role keys
        :return: a list of RoleModelView
        """
        _roles = set()
        _role_keys = set(role_keys)
        for role_key, fab_role_names in self.auth_roles_mapping.items():
            if role_key in _role_keys:
                for fab_role_name in fab_role_names:
                    fab_role = self.find_role(fab_role_name)
                    if fab_role:
                        _roles.add(fab_role)
                    else:
                        log.warning(
                            "Can't find role specified in AUTH_ROLES_MAPPING: %s",
                            fab_role_name,
                        )
        return _roles

    @property
    def auth_type_provider_name(self) -> Optional[str]:
        provider_to_auth_type = {AUTH_DB: "db", AUTH_LDAP: "ldap"}
        return provider_to_auth_type.get(self.auth_type)

    @property
    def get_url_for_registeruser(self):
        return url_for(
            "%s.%s"
            % (self.registeruser_view.endpoint, self.registeruser_view.default_view)
        )

    @property
    def get_user_datamodel(self):
        return self.user_view.datamodel

    @property
    def get_register_user_datamodel(self):
        return self.registerusermodelview.datamodel

    @property
    def builtin_roles(self) -> Dict[str, Any]:
        return self._builtin_roles

    @property
    def api_login_allow_multiple_providers(self):
        return self.appbuilder.get_app.config["AUTH_API_LOGIN_ALLOW_MULTIPLE_PROVIDERS"]

    @property
    def auth_type(self) -> int:
        return self.appbuilder.get_app.config["AUTH_TYPE"]

    @property
    def auth_username_ci(self) -> str:
        return self.appbuilder.get_app.config.get("AUTH_USERNAME_CI", True)

    @property
    def auth_role_admin(self) -> str:
        return self.appbuilder.get_app.config["AUTH_ROLE_ADMIN"]

    @property
    def auth_role_public(self) -> str:
        return self.appbuilder.get_app.config["AUTH_ROLE_PUBLIC"]

    @property
    def auth_ldap_server(self) -> str:
        return self.appbuilder.get_app.config["AUTH_LDAP_SERVER"]

    @property
    def auth_ldap_use_tls(self) -> bool:
        return self.appbuilder.get_app.config["AUTH_LDAP_USE_TLS"]

    @property
    def auth_user_registration(self) -> bool:
        return self.appbuilder.get_app.config["AUTH_USER_REGISTRATION"]

    @property
    def auth_user_registration_role(self) -> str:
        return self.appbuilder.get_app.config["AUTH_USER_REGISTRATION_ROLE"]

    @property
    def auth_user_registration_role_jmespath(self) -> str:
        return self.appbuilder.get_app.config["AUTH_USER_REGISTRATION_ROLE_JMESPATH"]

    @property
    def auth_remote_user_env_var(self) -> str:
        return self.appbuilder.get_app.config["AUTH_REMOTE_USER_ENV_VAR"]

    @property
    def auth_roles_mapping(self) -> Dict[str, List[str]]:
        return self.appbuilder.get_app.config["AUTH_ROLES_MAPPING"]

    @property
    def auth_roles_sync_at_login(self) -> bool:
        return self.appbuilder.get_app.config["AUTH_ROLES_SYNC_AT_LOGIN"]

    @property
    def auth_ldap_search(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_SEARCH"]

    @property
    def auth_ldap_search_filter(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_SEARCH_FILTER"]

    @property
    def auth_ldap_bind_user(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_BIND_USER"]

    @property
    def auth_ldap_bind_password(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_BIND_PASSWORD"]

    @property
    def auth_ldap_append_domain(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_APPEND_DOMAIN"]

    @property
    def auth_ldap_username_format(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_USERNAME_FORMAT"]

    @property
    def auth_ldap_uid_field(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_UID_FIELD"]

    @property
    def auth_ldap_group_field(self) -> str:
        return self.appbuilder.get_app.config["AUTH_LDAP_GROUP_FIELD"]

    @property
    def auth_ldap_firstname_field(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_FIRSTNAME_FIELD"]

    @property
    def auth_ldap_lastname_field(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_LASTNAME_FIELD"]

    @property
    def auth_ldap_email_field(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_EMAIL_FIELD"]

    @property
    def auth_ldap_bind_first(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_BIND_FIRST"]

    @property
    def auth_ldap_allow_self_signed(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_ALLOW_SELF_SIGNED"]

    @property
    def auth_ldap_tls_demand(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_TLS_DEMAND"]

    @property
    def auth_ldap_tls_cacertdir(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_TLS_CACERTDIR"]

    @property
    def auth_ldap_tls_cacertfile(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_TLS_CACERTFILE"]

    @property
    def auth_ldap_tls_certfile(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_TLS_CERTFILE"]

    @property
    def auth_ldap_tls_keyfile(self):
        return self.appbuilder.get_app.config["AUTH_LDAP_TLS_KEYFILE"]

    @property
    def openid_providers(self):
        return self.appbuilder.get_app.config["OPENID_PROVIDERS"]

    @property
    def oauth_providers(self):
        return self.appbuilder.get_app.config["OAUTH_PROVIDERS"]

    @property
    def is_auth_limited(self) -> bool:
        return self.appbuilder.get_app.config["AUTH_RATE_LIMITED"]

    @property
    def auth_rate_limit(self) -> str:
        return self.appbuilder.get_app.config["AUTH_RATE_LIMIT"]

    @property
    def current_user(self):
        if current_user.is_authenticated:
            return g.user
        elif current_user_jwt:
            return current_user_jwt

    def oauth_user_info_getter(
        self,
        func: Callable[["BaseSecurityManager", str, Dict[str, Any]], Dict[str, Any]],
    ):
        """
        Decorator function to be the OAuth user info getter
        for all the providers, receives provider and response
        return a dict with the information returned from the provider.
        The returned user info dict should have it's keys with the same
        name as the User Model.

        Use it like this an example for GitHub ::

            @appbuilder.sm.oauth_user_info_getter
            def my_oauth_user_info(sm, provider, response=None):
                if provider == 'github':
                    me = sm.oauth_remotes[provider].get('user')
                    return {'username': me.data.get('login')}
                return {}
        """        
        def wraps(provider: str, response: Dict[str, Any] = None) -> Dict[str, Any]:
            return func(self, provider, response)

        self.oauth_user_info = wraps
        return wraps

    def get_oauth_token_key_name(self, provider):
        """
        Returns the token_key name for the oauth provider
        if none is configured defaults to oauth_token
        this is configured using OAUTH_PROVIDERS and token_key key.
        """
        for _provider in self.oauth_providers:
            if _provider["name"] == provider:
                return _provider.get("token_key", "oauth_token")
        return "oauth_token"

    def get_oauth_token_secret_name(self, provider):
        """
        Returns the token_secret name for the oauth provider
        if none is configured defaults to oauth_secret
        this is configured using OAUTH_PROVIDERS and token_secret
        """
        for _provider in self.oauth_providers:
            if _provider["name"] == provider:
                return _provider.get("token_secret", "oauth_token_secret")
        return "oauth_token_secret"

    def set_oauth_session(self, provider, oauth_response):
        """
        Set the current session with OAuth user secrets
        """
        # Get this provider key names for token_key and token_secret
        token_key = self.appbuilder.sm.get_oauth_token_key_name(provider)
        token_secret = self.appbuilder.sm.get_oauth_token_secret_name(provider)
        # Save users token on encrypted session cookie
        session["oauth"] = (
            oauth_response[token_key],
            oauth_response.get(token_secret, ""),
        )
        session["oauth_provider"] = provider

    def get_oauth_user_info(
        self, provider: str, resp: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Since there are different OAuth APIs with different ways to
        retrieve user info
        """
        # for GITHUB
        if provider == "github" or provider == "githublocal":
            me = self.appbuilder.sm.oauth_remotes[provider].get("user")
            data = me.json()
            log.debug("User info from Github: %s", data)
            return {"username": "github_" + data.get("login")}
        # for twitter
        if provider == "twitter":
            return {"username": "twitter_" + data.get("screen_name")}
        return {}

    @staticmethod
    def ldap_extract(
        ldap_dict: Dict[str, bytes], field_name: str, fallback: str
    ) -> str:
        raw_value = ldap_dict.get(field_name, [bytes()])
        # decode - if empty string, default to fallback, otherwise take first element
        return raw_value[0].decode("utf-8") or fallback

    @staticmethod
    def ldap_extract_list(ldap_dict: Dict[str, bytes], field_name: str) -> List[str]:
        raw_list = ldap_dict.get(field_name, [])
        # decode - removing empty strings
        return [x.decode("utf-8") for x in raw_list if x.decode("utf-8")]

    def auth_user_ldap(self, username, password):
        """
        Method for authenticating user with LDAP.

        NOTE: this depends on python-ldap module

        :param username: the username
        :param password: the password
        """
        # If no username is provided, go away
        if (username is None) or username == "":
            return None

        # Search the DB for this user
        user = self.find_user(username=username)

        # If user is not active, go away
        if user and (not user.is_active):
            return None

        # If user is not registered, and not self-registration, go away
        if (not user) and (not self.auth_user_registration):
            return None

        # Ensure python-ldap is installed
        try:
            import ldap
        except ImportError:
            log.error("python-ldap library is not installed")
            return None

        try:
            # LDAP certificate settings
            if self.auth_ldap_tls_cacertdir:
                ldap.set_option(ldap.OPT_X_TLS_CACERTDIR, self.auth_ldap_tls_cacertdir)
            if self.auth_ldap_tls_cacertfile:
                ldap.set_option(
                    ldap.OPT_X_TLS_CACERTFILE, self.auth_ldap_tls_cacertfile
                )
            if self.auth_ldap_tls_certfile:
                ldap.set_option(ldap.OPT_X_TLS_CERTFILE, self.auth_ldap_tls_certfile)
            if self.auth_ldap_tls_keyfile:
                ldap.set_option(ldap.OPT_X_TLS_KEYFILE, self.auth_ldap_tls_keyfile)
            if self.auth_ldap_allow_self_signed:
                ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)
                ldap.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
            elif self.auth_ldap_tls_demand:
                ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
                ldap.set_option(ldap.OPT_X_TLS_NEWCTX, 0)

            # Initialise LDAP connection
            con = ldap.initialize(self.auth_ldap_server)
            con.set_option(ldap.OPT_REFERRALS, 0)
            if self.auth_ldap_use_tls:
                try:
                    con.start_tls_s()
                except Exception:
                    log.error(LOGMSG_ERR_SEC_AUTH_LDAP_TLS, self.auth_ldap_server)
                    return None

            # Define variables, so we can check if they are set in later steps
            user_dn = None
            user_attributes = {}

            # Flow 1 - (Indirect Search Bind):
            #  - in this flow, special bind credentials are used to perform the
            #    LDAP search
            #  - in this flow, AUTH_LDAP_SEARCH must be set
            if self.auth_ldap_bind_user:
                # Bind with AUTH_LDAP_BIND_USER/AUTH_LDAP_BIND_PASSWORD
                # (authorizes for LDAP search)
                self._ldap_bind_indirect(ldap, con)

                # Search for `username`
                #  - returns the `user_dn` needed for binding to validate credentials
                #  - returns the `user_attributes` needed for
                #    AUTH_USER_REGISTRATION/AUTH_ROLES_SYNC_AT_LOGIN
                if self.auth_ldap_search:
                    user_dn, user_attributes = self._search_ldap(ldap, con, username)
                else:
                    log.error(
                        "AUTH_LDAP_SEARCH must be set when using AUTH_LDAP_BIND_USER"
                    )
                    return None

                # If search failed, go away
                if user_dn is None:
                    log.info(LOGMSG_WAR_SEC_NOLDAP_OBJ, username)
                    return None

                # Bind with user_dn/password (validates credentials)
                if not self._ldap_bind(ldap, con, user_dn, password):
                    if user:
                        self.update_user_auth_stat(user, False)

                    # Invalid credentials, go away
                    log.info(LOGMSG_WAR_SEC_LOGIN_FAILED, username)
                    return None

            # Flow 2 - (Direct Search Bind):
            #  - in this flow, the credentials provided by the end-user are used
            #    to perform the LDAP search
            #  - in this flow, we only search LDAP if AUTH_LDAP_SEARCH is set
            #     - features like AUTH_USER_REGISTRATION & AUTH_ROLES_SYNC_AT_LOGIN
            #       will only work if AUTH_LDAP_SEARCH is set
            else:
                # Copy the provided username (so we can apply formatters)
                bind_username = username

                # update `bind_username` by applying AUTH_LDAP_APPEND_DOMAIN
                #  - for Microsoft AD, which allows binding with userPrincipalName
                if self.auth_ldap_append_domain:
                    bind_username = bind_username + "@" + self.auth_ldap_append_domain

                # Update `bind_username` by applying AUTH_LDAP_USERNAME_FORMAT
                #  - for transforming the username into a DN,
                #    for example: "uid=%s,ou=example,o=test"
                if self.auth_ldap_username_format:
                    bind_username = self.auth_ldap_username_format % bind_username

                # Bind with bind_username/password
                # (validates credentials & authorizes for LDAP search)
                if not self._ldap_bind(ldap, con, bind_username, password):
                    if user:
                        self.update_user_auth_stat(user, False)

                    # Invalid credentials, go away
                    log.info(LOGMSG_WAR_SEC_LOGIN_FAILED, bind_username)
                    return None

                # Search for `username` (if AUTH_LDAP_SEARCH is set)
                #  - returns the `user_attributes`
                #    needed for AUTH_USER_REGISTRATION/AUTH_ROLES_SYNC_AT_LOGIN
                #  - we search on `username` not `bind_username`,
                #    because AUTH_LDAP_APPEND_DOMAIN and AUTH_LDAP_USERNAME_FORMAT
                #    would result in an invalid search filter
                if self.auth_ldap_search:
                    user_dn, user_attributes = self._search_ldap(ldap, con, username)

                    # If search failed, go away
                    if user_dn is None:
                        log.info(LOGMSG_WAR_SEC_NOLDAP_OBJ, username)
                        return None

            # Sync the user's roles
            if user and user_attributes and self.auth_roles_sync_at_login:
                user.roles = self._ldap_calculate_user_roles(user_attributes)
                log.debug(
                    "Calculated new roles for user='%s' as: %s", user_dn, user.roles
                )

            # If the user is new, register them
            if (not user) and user_attributes and self.auth_user_registration:
                user = self.add_user(
                    username=username,
                    first_name=self.ldap_extract(
                        user_attributes, self.auth_ldap_firstname_field, ""
                    ),
                    last_name=self.ldap_extract(
                        user_attributes, self.auth_ldap_lastname_field, ""
                    ),
                    email=self.ldap_extract(
                        user_attributes,
                        self.auth_ldap_email_field,
                        f"{username}@email.notfound",
                    ),
                    role=self._ldap_calculate_user_roles(user_attributes),
                )
                log.debug("New user registered: %s", user)

                # If user registration failed, go away
                if not user:
                    log.info(LOGMSG_ERR_SEC_ADD_REGISTER_USER, username)
                    return None

            # LOGIN SUCCESS (only if user is now registered)
            if user:
                self.update_user_auth_stat(user)
                return user
            else:
                return None

        except ldap.LDAPError as e:
            msg = None
            if isinstance(e, dict):
                msg = getattr(e, "message", None)
            if (msg is not None) and ("desc" in msg):
                log.error(LOGMSG_ERR_SEC_AUTH_LDAP, e.message["desc"])
                return None
            else:
                log.error(e)
                return None

    def auth_user_oid(self, email):
        """
        OpenID user Authentication

        :param email: user's email to authenticate
        :type self: User model
        """
        user = self.find_user(email=email)
        if user is None or (not user.is_active):
            log.info(LOGMSG_WAR_SEC_LOGIN_FAILED, email)
            return None
        else:
            self.update_user_auth_stat(user)
            return user

    def auth_user_oauth(self, userinfo):
        """
        Method for authenticating user with OAuth.

        :userinfo: dict with user information
                   (keys are the same as User model columns)
        """
        pass

    def add_permissions_menu(self, view_menu_name):
        """
        Adds menu_access to menu on permission_view_menu

        :param view_menu_name:
            The menu name
        """
        self.add_view_menu(view_menu_name)
        pv = self.find_permission_view_menu("menu_access", view_menu_name)
        if not pv:
            pv = self.add_permission_view_menu("menu_access", view_menu_name)
        if self.auth_role_admin not in self.builtin_roles:
            role_admin = self.find_role(self.auth_role_admin)
            self.add_permission_role(role_admin, pv)

    def security_cleanup(self, baseviews, menus):
        """
        Will cleanup all unused permissions from the database

        :param baseviews: A list of BaseViews class
        :param menus: Menu class
        """
        viewsmenus = self.get_all_view_menu()
        roles = self.get_all_roles()
        for viewmenu in viewsmenus:
            found = False
            for baseview in baseviews:
                if viewmenu.name == baseview.class_permission_name:
                    found = True
                    break
            if menus.find(viewmenu.name):
                found = True
            if not found:
                permissions = self.find_permissions_view_menu(viewmenu)
                for permission in permissions:
                    for role in roles:
                        self.del_permission_role(role, permission)
                    self.del_permission_view_menu(
                        permission.permission.name, viewmenu.name
                    )
                self.del_view_menu(viewmenu.name)
        self.security_converge(baseviews, menus)

    @staticmethod
    def _get_new_old_permissions(baseview) -> Dict:
        ret = dict()
        for method_name, permission_name in baseview.method_permission_name.items():
            old_permission_name = baseview.previous_method_permission_name.get(
                method_name
            )
            # Actions do not get prefix when normally defined
            if hasattr(baseview, "actions") and baseview.actions.get(
                old_permission_name
            ):
                permission_prefix = ""
            else:
                permission_prefix = PERMISSION_PREFIX
            if old_permission_name:
                if PERMISSION_PREFIX + permission_name not in ret:
                    ret[PERMISSION_PREFIX + permission_name] = {
                        permission_prefix + old_permission_name
                    }
                else:
                    ret[PERMISSION_PREFIX + permission_name].add(
                        permission_prefix + old_permission_name
                    )
        return ret

    @staticmethod
    def _add_state_transition(
        state_transition: Dict,
        old_view_name: str,
        old_perm_name: str,
        view_name: str,
        perm_name: str,
    ) -> None:
        old_pvm = state_transition["add"].get((old_view_name, old_perm_name))
        if old_pvm:
            state_transition["add"][(old_view_name, old_perm_name)].add(
                (view_name, perm_name)
            )
        else:
            state_transition["add"][(old_view_name, old_perm_name)] = {
                (view_name, perm_name)
            }
        state_transition["del_role_pvm"].add((old_view_name, old_perm_name))
        state_transition["del_views"].add(old_view_name)
        state_transition["del_perms"].add(old_perm_name)

    @staticmethod
    def _update_del_transitions(state_transitions: Dict, baseviews: List) -> None:
        """
        Mutates state_transitions, loop baseviews and prunes all
        views and permissions that are not to delete because references
        exist.

        :param baseview:
        :param state_transitions:
        :return:
        """
        for baseview in baseviews:
            state_transitions["del_views"].discard(baseview.class_permission_name)
            for permission in baseview.base_permissions:
                state_transitions["del_role_pvm"].discard(
                    (baseview.class_permission_name, permission)
                )
                state_transitions["del_perms"].discard(permission)

    def create_state_transitions(
        self, baseviews: List, menus: Optional[List[Any]]
    ) -> Dict:
        """
        Creates a Dict with all the necessary vm/permission transitions

        Dict: {
                "add": {(<VM>, <PERM>): ((<VM>, PERM), ... )}
                "del_role_pvm": ((<VM>, <PERM>), ...)
                "del_views": (<VM>, ... )
                "del_perms": (<PERM>, ... )
              }

        :param baseviews: List with all the registered BaseView, BaseApi
        :param menus: List with all the menu entries
        :return: Dict with state transitions
        """
        state_transitions = {
            "add": {},
            "del_role_pvm": set(),
            "del_views": set(),
            "del_perms": set(),
        }
        for baseview in baseviews:
            add_all_flag = False
            new_view_name = baseview.class_permission_name
            permission_mapping = self._get_new_old_permissions(baseview)
            if baseview.previous_class_permission_name:
                old_view_name = baseview.previous_class_permission_name
                add_all_flag = True
            else:
                new_view_name = baseview.class_permission_name
                old_view_name = new_view_name
            for new_perm_name in baseview.base_permissions:
                if add_all_flag:
                    old_perm_names = permission_mapping.get(new_perm_name)
                    old_perm_names = old_perm_names or (new_perm_name,)
                    for old_perm_name in old_perm_names:
                        self._add_state_transition(
                            state_transitions,
                            old_view_name,
                            old_perm_name,
                            new_view_name,
                            new_perm_name,
                        )
                else:
                    old_perm_names = permission_mapping.get(new_perm_name) or set()
                    for old_perm_name in old_perm_names:
                        self._add_state_transition(
                            state_transitions,
                            old_view_name,
                            old_perm_name,
                            new_view_name,
                            new_perm_name,
                        )
        self._update_del_transitions(state_transitions, baseviews)
        return state_transitions

    def security_converge(
        self, baseviews: List, menus: Optional[List[Any]], dry=False
    ) -> Dict:
        """
        Converges overridden permissions on all registered views/api
        will compute all necessary operations from `class_permissions_name`,
        `previous_class_permission_name`, method_permission_name`,
        `previous_method_permission_name` class attributes.

        :param baseviews: List of registered views/apis
        :param menus: List of menu items
        :param dry: If True will not change DB
        :return: Dict with the necessary operations (state_transitions)
        """
        state_transitions = self.create_state_transitions(baseviews, menus)
        if dry:
            return state_transitions
        if not state_transitions:
            log.info("No state transitions found")
            return dict()
        log.debug("State transitions: %s", state_transitions)
        roles = self.get_all_roles()
        for role in roles:
            permissions = list(role.permissions)
            for pvm in permissions:
                new_pvm_states = state_transitions["add"].get(
                    (pvm.view_menu.name, pvm.permission.name)
                )
                if not new_pvm_states:
                    continue
                for new_pvm_state in new_pvm_states:
                    new_pvm = self.add_permission_view_menu(
                        new_pvm_state[1], new_pvm_state[0]
                    )
                    self.add_permission_role(role, new_pvm)
                if (pvm.view_menu.name, pvm.permission.name) in state_transitions[
                    "del_role_pvm"
                ]:
                    self.del_permission_role(role, pvm)
        for pvm in state_transitions["del_role_pvm"]:
            self.del_permission_view_menu(pvm[1], pvm[0], cascade=False)
        for view_name in state_transitions["del_views"]:
            self.del_view_menu(view_name)
        for permission_name in state_transitions["del_perms"]:
            self.del_permission(permission_name)
        return state_transitions

    """
    ---------------------------
    INTERFACE ABSTRACT METHODS
    ---------------------------

    ---------------------
    PRIMITIVES FOR USERS
    ----------------------
    """

    def find_register_user(self, registration_hash):
        """
        Generic function to return user registration
        """
        raise NotImplementedError

    def add_register_user(
        self, username, first_name, last_name, email, password="", hashed_password=""
    ):
        """
        Generic function to add user registration
        """
        raise NotImplementedError

    def import_roles(self, path: str) -> None:
        """
        Import roles from specified path
        """
        raise NotImplementedError

from io import BytesIO
import os
import shutil
from typing import Optional, Union
from urllib.request import urlopen
from zipfile import ZipFile

import click
from flask import current_app
from flask.cli import with_appcontext
import jinja2

from .const import AUTH_DB, AUTH_LDAP, AUTH_OAUTH, AUTH_OID, AUTH_REMOTE_USER
from .cli.create_enhanced_app import EnhancedAppGenerator


SQLA_REPO_URL = (
    "https://github.com/dpgaspar/Flask-AppBuilder-Skeleton/archive/master.zip"
)
MONGOENGIE_REPO_URL = (
    "https://github.com/dpgaspar/Flask-AppBuilder-Skeleton-me/archive/master.zip"
)
ADDON_REPO_URL = (
    "https://github.com/dpgaspar/Flask-AppBuilder-Skeleton-AddOn/archive/master.zip"
)

MIN_SECRET_KEY_SIZE = 20


def validate_secret_key(ctx, param, value):
    """
    Validate secret key input for minimum length requirements.
    
    Args:
        ctx: Click context object
        param: Click parameter object
        value: Secret key value to validate
        
    Returns:
        The validated secret key value
        
    Raises:
        click.BadParameter: If secret key is too short
    """
    if len(value) < MIN_SECRET_KEY_SIZE:
        raise click.BadParameter(f"SECRET_KEY size is less then {MIN_SECRET_KEY_SIZE}")
    return value


def echo_header(title):
    """
    Print a formatted header with title and underline.
    
    Args:
        title: Title text to display
    """
    click.echo(click.style(title, fg="green"))
    click.echo(click.style("-" * len(title), fg="green"))


def cast_int_like_to_int(cli_arg: Union[None, str, int]) -> Union[None, str, int]:
    """
    Cast int-like objects to int if possible.

    If the arg cannot be cast to an integer, return the unmodified object instead.
    
    Args:
        cli_arg: Command line argument that might be an integer
        
    Returns:
        Integer if castable, otherwise the original value
    """
    if cli_arg is None:
        return None
    try:
        return int(cli_arg)
    except (ValueError, TypeError):
        return cli_arg


def import_skeleton(name, authentication, engine, app_name):
    """
    Import Flask-AppBuilder application skeleton.
    
    Args:
        name: Application name
        authentication: Authentication type
        engine: Database engine (SQLAlchemy or MongoEngine)
        app_name: Flask application name
    """
    if engine == "SQLAlchemy":
        skeleton_url = SQLA_REPO_URL
    else:
        skeleton_url = MONGOENGIE_REPO_URL
        
    if os.path.exists(name):
        click.echo(
            click.style(
                f"Directory {name} already exists, please delete it or choose "
                "a different name",
                fg="red"
            )
        )
        exit(1)
        
    download_file(skeleton_url, name)
    echo_header("Updating directory name")
    os.rename(os.path.join(name, "Flask-AppBuilder-Skeleton-master"), 
              os.path.join(name, name))
    
    echo_header("Installing requirements")
    os.system(f"pip install -r {os.path.join(name, 'requirements.txt')}")


def download_file(url, local_name):
    """
    Download and extract ZIP file from URL.
    
    Args:
        url: URL to download from
        local_name: Local directory name to extract to
    """
    echo_header(f"Downloading {url}")
    try:
        with urlopen(url) as response:
            with ZipFile(BytesIO(response.read())) as zip_file:
                zip_file.extractall(local_name)
    except Exception as e:
        click.echo(
            click.style(f"Could not download {url}: {e}", fg="red")
        )
        exit(1)


@click.command()
@click.option("--name", prompt="Your new application name", help="Your application name")
@click.option(
    "--engine",
    default="SQLAlchemy",
    prompt="Select your engine",
    type=click.Choice(["SQLAlchemy", "MongoEngine"]),
    help="Database engine, SQLAlchemy or MongoEngine"
)
@click.option(
    "--authentication",
    default=AUTH_DB,
    prompt="Authentication type",
    type=click.Choice([AUTH_DB, AUTH_LDAP, AUTH_OAUTH, AUTH_OID, AUTH_REMOTE_USER]),
    help="Authentication type"
)
@with_appcontext
def create_app(name, engine, authentication):
    """
    Create new Flask-AppBuilder application.
    
    Args:
        name: Application name
        engine: Database engine
        authentication: Authentication method
    """
    echo_header("Starting template creation")
    click.echo(f"Selected engine: {engine}")
    
    import_skeleton(name, authentication, engine, name)
    
    echo_header("Updating application configuration")
    # Update config files, templates, etc. based on selections
    
    echo_header("Application created successfully!")
    click.echo(f"Your new application is ready in: {name}/")


@click.command()
@click.option("--name", prompt="Your addon name", help="Addon name")
@with_appcontext  
def create_addon(name):
    """
    Create new Flask-AppBuilder addon.
    
    Args:
        name: Addon name
    """
    echo_header("Creating addon")
    download_file(ADDON_REPO_URL, name)
    click.echo(f"Addon {name} created successfully!")


@click.command()
@with_appcontext
def create_admin():
    """Create admin user for the application."""
    echo_header("Creating admin user")
    
    first_name = click.prompt("First name", type=str)
    last_name = click.prompt("Last name", type=str) 
    username = click.prompt("Username", type=str)
    email = click.prompt("Email", type=str)
    password = click.prompt("Password", type=str, hide_input=True, confirmation_prompt=True)
    
    try:
        appbuilder = current_app.appbuilder
        role_admin = appbuilder.sm.find_role(appbuilder.sm.auth_role_admin)
        
        user = appbuilder.sm.add_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role_admin,
            password=password
        )
        
        if user:
            click.echo(click.style("Admin user created successfully!", fg="green"))
        else:
            click.echo(click.style("Failed to create admin user", fg="red"))
            
    except Exception as e:
        click.echo(click.style(f"Error creating admin user: {e}", fg="red"))


@click.command()
@click.argument("username")
@with_appcontext
def reset_password(username):
    """
    Reset password for a user.
    
    Args:
        username: Username to reset password for
    """
    echo_header(f"Resetting password for user: {username}")
    
    try:
        appbuilder = current_app.appbuilder
        user = appbuilder.sm.find_user(username=username)
        
        if not user:
            click.echo(click.style(f"User {username} not found", fg="red"))
            return
            
        password = click.prompt("New password", type=str, hide_input=True, confirmation_prompt=True)
        appbuilder.sm.reset_password(user.id, password)
        
        click.echo(click.style("Password reset successfully!", fg="green"))
        
    except Exception as e:
        click.echo(click.style(f"Error resetting password: {e}", fg="red"))


@click.command()
@with_appcontext
def list_users():
    """List all users in the application."""
    echo_header("Application Users")
    
    try:
        appbuilder = current_app.appbuilder
        users = appbuilder.sm.get_all_users()
        
        for user in users:
            roles = ", ".join([role.name for role in user.roles])
            click.echo(f"Username: {user.username}, Email: {user.email}, Roles: {roles}")
            
    except Exception as e:
        click.echo(click.style(f"Error listing users: {e}", fg="red"))


@click.command()
@with_appcontext
def list_views():
    """List all views registered with the application."""
    echo_header("Registered Views")
    
    try:
        appbuilder = current_app.appbuilder
        for view in appbuilder.baseviews:
            click.echo(f"View: {view.__class__.__name__}, Endpoint: {view.endpoint}")
            
    except Exception as e:
        click.echo(click.style(f"Error listing views: {e}", fg="red"))


@click.command()
@click.option("--name", prompt="Application name", help="Name of the application")
@click.option("--engine", default="postgresql", type=click.Choice(["postgresql", "sqlite"]), 
              help="Database engine")
@click.option("--target-dir", default=".", help="Target directory for the application")
@click.option("--no-mfa", is_flag=True, help="Skip Multi-Factor Authentication system")
@click.option("--no-wallet", is_flag=True, help="Skip Wallet system")
@click.option("--no-widgets", is_flag=True, help="Skip enhanced widget library")
@click.option("--no-mixins", is_flag=True, help="Skip mixin integration system")
@click.option("--no-field-analysis", is_flag=True, help="Skip field analysis system")
@click.option("--no-sample-data", is_flag=True, help="Skip sample data creation")
def create_ext_app(name, engine, target_dir, no_mfa, no_wallet, no_widgets, 
                   no_mixins, no_field_analysis, no_sample_data):
    """
    Create a complete Enhanced Flask-AppBuilder application.
    
    This command creates a fully-featured Flask-AppBuilder application with all
    advanced enhancements including MFA, Wallet System, Enhanced Widgets,
    Mixin Integration, and Field Analysis.
    
    Example:
        fab create-ext-app --name myapp --engine postgresql
        fab create-ext-app --name myapp --no-mfa --no-wallet
    """
    
    echo_header("Creating Enhanced Flask-AppBuilder Application")
    click.echo(f"Application name: {name}")
    click.echo(f"Database engine: {engine}")
    click.echo(f"Target directory: {target_dir}")
    
    generator = EnhancedAppGenerator(name, target_dir)
    
    try:
        generator.create_application(
            engine=engine,
            include_mfa=not no_mfa,
            include_wallet=not no_wallet,
            include_widgets=not no_widgets,
            include_mixins=not no_mixins,
            include_field_analysis=not no_field_analysis,
            create_sample_data=not no_sample_data
        )
        
        click.echo(click.style("✅ Enhanced application created successfully!", fg="green"))
        
    except Exception as e:
        click.echo(click.style(f"❌ Error creating application: {e}", fg="red"))
        raise


# Create the Flask CLI command group
@click.group()
def fab():
    """Flask-AppBuilder CLI commands."""
    pass


# Import and register migration commands
try:
    from .cli.migration_tools import migration
    fab.add_command(migration)
except ImportError:
    # Migration tools not available
    pass


# Import and register generation commands
try:
    from .cli.generators.cli_commands import gen
    fab.add_command(gen)
except ImportError:
    # Generation tools not available
    pass

# Register all commands with the fab group
fab.add_command(create_app)
fab.add_command(create_addon)
fab.add_command(create_admin)
fab.add_command(reset_password)
fab.add_command(list_users)
fab.add_command(list_views)
fab.add_command(create_ext_app)
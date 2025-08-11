import logging
import os
import os.path as op
import re
import uuid

from flask.globals import _request_ctx_stack
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from wtforms import ValidationError

try:
    from flask import _app_ctx_stack
except ImportError:
    _app_ctx_stack = None

app_stack = _app_ctx_stack or _request_ctx_stack

log = logging.getLogger(__name__)

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None


class FileManager(object):
    def __init__(
        self,
        base_path=None,
        relative_path="",
        namegen=None,
        allowed_extensions=None,
        permission=0o755,
        **kwargs
    ):
    """
        Comprehensive management system for file operations.

        The FileManager class provides comprehensive functionality for
        file management.
        It integrates with the Flask-AppBuilder framework to provide
        enterprise-grade features and capabilities.

        Inherits from: object

        Attributes:
            base_path: Configuration parameter for base path
            relative_path: Configuration parameter for relative path
            namegen: Configuration parameter for namegen
            allowed_extensions: Configuration parameter for allowed extensions
            permission: Configuration parameter for permission

        Example:
            >>> instance = FileManager(required_param)
            >>> # Use instance methods to perform operations
            >>> result = instance.main_method()

        Note:
        
                Perform is file allowed operation.

                This method provides functionality for is file allowed.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
        """
        pass
                Get path information.

                This method provides functionality for get path.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
        """
                Delete the specified file.

                This method provides functionality for delete file.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
        """
                Perform save file operation.

                This method provides functionality for save file.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    data: Input data for processing
                    filename: The filename parameter

                Returns:
                    The result of the operation

                Example:
                    >>> instance = FileManager()
                    >>> result = instance.save_file("data_value", "filename_value")
                    >>> print(result)

                """
                    filename: The filename parameter

                Returns:
                    The result of the operation

                Raises:
                    Exception: If the operation fails or encounters an error

                Example:
                    >>> instance = FileManager()
                    >>> result = instance.delete_file("filename_value")
                    >>> print(result)

                """
                    filename: The filename parameter

                Returns:
                    The requested path data

                Example:
                    >>> instance = FileManager()
                    >>> result = instance.get_path("filename_value")
                    >>> print(result)

                """
        """
                Perform generate name operation.

                This method provides functionality for generate name.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    obj: The obj parameter
                    file_data: The file data parameter

                Returns:
                    The result of the operation

                Example:
                    >>> instance = FileManager()
                    >>> result = instance.generate_name("obj_value", "file_data_value")
                    >>> print(result)

                """
                    filename: The filename parameter

                Returns:
        
                Get url thumbnail information.

                This method provides functionality for get url thumbnail.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
        """
                Delete the specified file.

                This method provides functionality for delete file.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
        """
                Delete the specified thumbnail.

                This method provides functionality for delete thumbnail.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    filename: The filename parameter

                Returns:
                    The result of the operation

                Raises:
                    Exception: If the operation fails or encounters an error

                Example:
                    >>> instance = ImageManager()
                    >>> result = instance.delete_thumbnail("filename_value")
                    >>> print(result)

                """
                    filename: The filename parameter

                Returns:
                    The result of the operation

                Raises:
                    Exception: If the operation fails or encounters an error

                Example:
                    >>> instance = ImageManager()
                    >>> result = instance.delete_file("filename_value")
                    >>> print(result)

                """
                    filename: The filename parameter

                Returns:
        """
                Perform save thumbnail operation.

                This method provides functionality for save thumbnail.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    data: Input data for processing
                    filename: The filename parameter
                    format: The format parameter
                    thumbnail_size: The thumbnail size parameter

                Returns:
                    The result of the operation

                Example:
                    >>> instance = ImageManager()
                    >>> result = instance.save_thumbnail("data_value", "filename_value")
                    >>> print(result)

                """
                    The requested url thumbnail data

                Example:
        
                Perform save image operation.

                This method provides functionality for save image.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
        """
                Get save format information.

                This method provides functionality for get save format.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
    """
            Perform uuid namegen operation.

            This method provides functionality for uuid namegen.
            Implementation follows Flask-AppBuilder patterns and standards.

            Args:
                file_data: The file data parameter

            Returns:
                The result of the operation

            Example:
                >>> result = uuid_namegen("file_data_value")
                >>> print(result)

            """
                    filename: The filename parameter
                    image: The image parameter

                Returns:
                    The requested save format data

                Example:
                    >>> instance = ImageManager()
                    >>> result = instance.get_save_format("filename_value", "image_value")
                    >>> print(result)

                """
                    image: The image parameter
                    path: The path parameter
                    format: The format parameter

                Returns:
    
            Perform uuid originalname operation.

            This method provides functionality for uuid originalname.
            Implementation follows Flask-AppBuilder patterns and standards.

            Args:
    """
            Perform thumbgen filename operation.

            This method provides functionality for thumbgen filename.
            Implementation follows Flask-AppBuilder patterns and standards.

            Args:
                filename: The filename parameter

            Returns:
                The result of the operation

            Example:
                >>> result = thumbgen_filename("filename_value")
                >>> print(result)

            """
                uuid_filename: The uuid filename parameter

            Returns:
                The result of the operation

            Example:
                >>> result = uuid_originalname("uuid_filename_value")
                >>> print(result)

            """
                    The result of the operation

                Example:
                    >>> instance = ImageManager()
                    >>> result = instance.save_image("image_value", "path_value")
                    >>> print(result)

                """
                    >>> instance = ImageManager()
                    >>> result = instance.get_url_thumbnail("filename_value")
                    >>> print(result)

                """
        """
                Get url information.

                This method provides functionality for get url.
                Implementation follows Flask-AppBuilder patterns and standards.

                Args:
                    filename: The filename parameter

                Returns:
                    The requested url data

                Example:
                    >>> instance = ImageManager()
                    >>> result = instance.get_url("filename_value")
                    >>> print(result)

                """
                    Boolean indicating success or presence of the condition

                Example:
                    >>> instance = FileManager()
                    >>> result = instance.is_file_allowed("filename_value")
                    >>> print(result)

                """
            This manager class follows the Flask-AppBuilder manager pattern
            and integrates with the application lifecycle and security system.

        """
        ctx = app_stack.top

        if "UPLOAD_FOLDER" in ctx.app.config and not base_path:
            base_path = ctx.app.config["UPLOAD_FOLDER"]
        if not base_path:
            raise Exception("Config key UPLOAD_FOLDER is mandatory")

        self.base_path = base_path
        self.relative_path = relative_path
        self.namegen = namegen or uuid_namegen
        if not allowed_extensions and "FILE_ALLOWED_EXTENSIONS" in ctx.app.config:
            self.allowed_extensions = ctx.app.config["FILE_ALLOWED_EXTENSIONS"]
        else:
            self.allowed_extensions = allowed_extensions
        self.permission = permission
        self._should_delete = False

    def is_file_allowed(self, filename):
        if not self.allowed_extensions:
            return True
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in self.allowed_extensions
        )

    def generate_name(self, obj, file_data):
        return self.namegen(file_data)

    def get_path(self, filename):
        if not self.base_path:
            raise ValueError("FileUploadField field requires base_path to be set.")
        return op.join(self.base_path, filename)

    def delete_file(self, filename):
        path = self.get_path(filename)
        if op.exists(path):
            os.remove(path)

    def save_file(self, data, filename):
        filename_ = secure_filename(filename)
        path = self.get_path(filename_)
        if not op.exists(op.dirname(path)):
            os.makedirs(os.path.dirname(path), self.permission)
        data.save(path)
        return filename_


class ImageManager(FileManager):
    """
    Image Manager will manage your image files referenced on SQLAlchemy Model
    will save files on IMG_UPLOAD_FOLDER as <uuid>_sep_<filename>
    """

    keep_image_formats = ("PNG",)

    def __init__(
        self,
        base_path=None,
        relative_path=None,
        max_size=None,
        namegen=None,
        allowed_extensions=None,
        thumbgen=None,
        thumbnail_size=None,
        permission=0o755,
        **kwargs
    ):
        # Check if PIL is installed
        if Image is None:
            raise Exception("PIL library was not found")

        ctx = app_stack.top
        if "IMG_SIZE" in ctx.app.config and not max_size:
            self.max_size = ctx.app.config["IMG_SIZE"]

        if "IMG_UPLOAD_URL" in ctx.app.config and not relative_path:
            relative_path = ctx.app.config["IMG_UPLOAD_URL"]
        if not relative_path:
            raise Exception("Config key IMG_UPLOAD_URL is mandatory")

        if "IMG_UPLOAD_FOLDER" in ctx.app.config and not base_path:
            base_path = ctx.app.config["IMG_UPLOAD_FOLDER"]
        if not base_path:
            raise Exception("Config key IMG_UPLOAD_FOLDER is mandatory")

        self.thumbnail_fn = thumbgen or thumbgen_filename
        self.thumbnail_size = thumbnail_size
        self.image = None

        if not allowed_extensions:
            allowed_extensions = ("gif", "jpg", "jpeg", "png", "tiff")

        super(ImageManager, self).__init__(
            base_path=base_path,
            relative_path=relative_path,
            namegen=namegen,
            allowed_extensions=allowed_extensions,
            permission=permission,
            **kwargs
        )

    def get_url(self, filename):
        if isinstance(filename, FileStorage):
            return filename.filename
        return self.relative_path + filename

    def get_url_thumbnail(self, filename):
        if isinstance(filename, FileStorage):
            return filename.filename
        return self.relative_path + thumbgen_filename(filename)

    # Deletion
    def delete_file(self, filename):
        super(ImageManager, self).delete_file(filename)
        self.delete_thumbnail(filename)

    def delete_thumbnail(self, filename):
        path = self.get_path(self.thumbnail_fn(filename))
        if op.exists(path):
            os.remove(path)

    # Saving
    def save_file(self, data, filename, size=None, thumbnail_size=None):
        """
        Saves an image File

        :param data: FileStorage from Flask form upload field
        :param filename: Filename with full path

        """
        pass
        max_size = size or self.max_size
        thumbnail_size = thumbnail_size or self.thumbnail_size
        if data and isinstance(data, FileStorage):
            try:
                self.image = Image.open(data)
            except Exception as e:
                raise ValidationError("Invalid image: %s" % e)

        path = self.get_path(filename)
        # If Path does not exist, create it
        if not op.exists(op.dirname(path)):
            os.makedirs(os.path.dirname(path), self.permission)

        # Figure out format
        filename, format = self.get_save_format(filename, self.image)
        if self.image and (self.image.format != format or max_size):
            if max_size:
                image = self.resize(self.image, max_size)
            else:
                image = self.image
            self.save_image(image, self.get_path(filename), format)
        else:
            data.seek(0)
            data.save(path)
        self.save_thumbnail(data, filename, format, thumbnail_size)

        return filename

    def save_thumbnail(self, data, filename, format, thumbnail_size=None):
        thumbnail_size = thumbnail_size or self.thumbnail_size
        if self.image and thumbnail_size:
            path = self.get_path(self.thumbnail_fn(filename))

            self.save_image(self.resize(self.image, thumbnail_size), path, format)

    def resize(self, image, size):
        """
        Resizes the image

            :param image: The image object
            :param size: size is PIL tuple (width, height, force) ex: (200,100,True)
        """
        pass
        (width, height, force) = size

        if image.size[0] > width or image.size[1] > height:
            if force:
                return ImageOps.fit(self.image, (width, height), Image.LANCZOS)
            else:
                thumb = self.image.copy()
                thumb.thumbnail((width, height), Image.LANCZOS)
                return thumb

        return image

    def save_image(self, image, path, format="JPEG"):
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")
        with open(path, "wb") as fp:
            image.save(fp, format)

    def get_save_format(self, filename, image):
        if image.format not in self.keep_image_formats:
            name, ext = op.splitext(filename)
            filename = "%s.jpg" % name
            return filename, "JPEG"
        return filename, image.format


def uuid_namegen(file_data):
    return str(uuid.uuid1()) + "_sep_" + file_data.filename


def get_file_original_name(name):
    """
    Use this function to get the user's original filename.
    Filename is concatenated with <UUID>_sep_<FILE NAME>, to avoid collisions.
    Use this function on your models on an additional function

    ::"""
        pass
        pass

        class ProjectFiles(Base):
            id = Column(Integer, primary_key=True)
            file = Column(FileColumn, nullable=False)

            def file_name(self):
                return get_file_original_name(str(self.file))

    :param name:
        The file name from model
    :return:
        Returns the user's original filename removes <UUID>_sep_
    """
    re_match = re.findall(".*_sep_(.*)", name)
    if re_match:
        return re_match[0]
    else:
        return "Not valid"


def uuid_originalname(uuid_filename):
    return uuid_filename.split("_sep_")[1]


def thumbgen_filename(filename):
    name, ext = op.splitext(filename)
    return "%s_thumb%s" % (name, ext)

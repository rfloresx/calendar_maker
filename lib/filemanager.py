"""File manager utilities.

Provides FilesManager, a singleton helper that manages project-relative
paths for images, CSS and other assets used by the application.
"""

from io import TextIOWrapper

import pathlib
import shutil
import os

class FilesManager:
    """Singleton that manages files inside a project directory.

    The FilesManager is responsible for creating and maintaining a project
    root directory, copying files into project subfolders (images, css, Docs)
    and exposing helpers to obtain absolute or relative paths for files
    referenced by the application.

    Attributes:
        IMAGES (set): allowed image file suffixes.
        IMAGES_PATH (str): directory name where images are stored.
        DOCS (set): allowed document suffixes.
        CSS (set): allowed css suffixes.
        CSS_PATH (str): directory name where css files are stored.
    """
    IMAGES = set([".png", ".jpg", ".jpeg", ".bmp"])
    IMAGES_PATH = "images"
    DOCS = set([])
    CSS = set(['.css'])
    CSS_PATH = "css"

    _instance: 'FilesManager' = None

    @staticmethod
    def instance() -> 'FilesManager':
        """Return the singleton FilesManager instance.

        If an instance does not exist yet, a new one is created with a
        default temporary directory. Callers may also instantiate
        FilesManager(project_directory) directly to set the root.
        """
        if FilesManager._instance is None:
            FilesManager._instance = FilesManager()
        return FilesManager._instance

    def __init__(self, project_directory: str):
        """Create a FilesManager for project_directory.

        Args:
            project_directory: path to the project root. The directory will be
                created if it does not exist.
        """
        self._path: pathlib.Path = pathlib.Path(project_directory).absolute()
        if not self._path.exists():
            self._path.mkdir(parents=True, exist_ok=True)
        FilesManager._instance = self
        self._filename: pathlib.Path = pathlib.Path(self._path, "files.zip")

    @property
    def root(self) -> pathlib.Path:
        """Return the project's root path as a pathlib.Path."""
        return self._path

    def get_relative_path(self, path:str) -> str:
        """Return ``path`` expressed relative to the project root.

        If the given path is not under the project root the original path is
        returned unchanged.

        Args:
            path: absolute or relative path to convert.

        Returns:
            Relative path string when possible, otherwise the original path.
        """
        if not path:
            return path
        try:
            return str(pathlib.Path(path).relative_to(self._path))
        except ValueError:
            return path

    def get_file_path(self, filename: str) -> pathlib.Path:
        """Return an absolute path inside the project for ``filename``.

        If ``filename`` is not absolute it will be interpreted relative to the
        project root; necessary parent directories will be created.
        """
        if not pathlib.Path(filename).is_absolute():
            src_file = pathlib.Path(self._path, filename).absolute()
            if not src_file.parent.exists():
                src_file.parent.mkdir(parents=True, exist_ok=True)
            return src_file
        else:
            return pathlib.Path(filename)

    def get_target_path(self, filename: str) -> pathlib.Path:        
        """Determine the target path inside the project for a given filename.

        Files are routed to images, css or Docs subfolders according to their
        file suffix. The returned path is created if necessary.
        """
        path = pathlib.Path(filename)
        suffix = path.suffix.lower()
        if suffix in FilesManager.IMAGES:
            new_path = pathlib.Path(self._path, FilesManager.IMAGES_PATH, path.name).absolute()
        elif suffix in FilesManager.DOCS:
            new_path = pathlib.Path(self._path, 'Docs', path.name).absolute()
        elif suffix in FilesManager.CSS:
            new_path = pathlib.Path(self._path, FilesManager.CSS, path.name).absolute()
        else:
            new_path = pathlib.Path(self._path, path.name).absolute()
        if not new_path.parent.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
        return new_path

    def add_file(self, file: str) -> str:
        """Add a file to the project and return its project path.

        If the provided path is already inside the managed project it is
        returned unchanged. Otherwise the file is copied to the appropriate
        subfolder (images, css, Docs) and the path to the copied file is
        returned.

        Args:
            file: absolute or relative path to the source file.

        Returns:
            The absolute path of the file inside the project as a string.
        """
        if file is None:
            return file

        if not pathlib.Path(file).is_absolute():
            src_file = pathlib.Path(self._path, file).absolute()
            return str(src_file)

        src_file = pathlib.Path(file).absolute()
        if self.is_managed_file(src_file):
            return str(src_file)
        new_path = self.get_target_path(src_file)
        if src_file.exists():
            if src_file.is_file():
                if new_path.exists():
                    new_path.unlink(missing_ok=True)
                shutil.copy(str(src_file), str(new_path))
            elif src_file.is_dir():
                print("HEY!!!")
        else:
            print("Not found", src_file)
        return str(new_path)

    def add_directory(self, src_dir:str, dst_dir:str=".") -> str:
        """Copy a directory into the project.

        Args:
            src_dir: absolute or relative path to the source directory.
            dst_dir: destination subdirectory inside the project.

        Returns:
            Absolute path to the copied directory inside the project.
        """
        if src_dir is None:
            return src_dir

        if not pathlib.Path(src_dir).is_absolute():
            src_file = pathlib.Path(self._path, src_dir).absolute()
            return str(src_file)

        src_dir : pathlib.Path = pathlib.Path(src_dir).absolute()
        if self.is_managed_file(src_dir):
            return str(src_dir)
        dst_dir = pathlib.Path(self._path, dst_dir, src_dir.name).absolute()
        if src_dir.exists():
            if src_dir.is_dir():
                shutil.copytree(str(src_dir), str(dst_dir), dirs_exist_ok=True)
            else:
                print("HEY???")
        return str(dst_dir)

    def is_managed_file(self, path: str) -> bool:
        """Return True if ``path`` is inside the project root."""
        path = str(pathlib.Path(path).absolute())
        parent = str(self._path)
        return path.startswith(parent)

    def open(self, filename, mode) -> TextIOWrapper:
        """Open a file for reading/writing inside the project.

        The file will be added to the project (copied) if necessary and the
        opened file handle will be returned.
        """
        filename = str(pathlib.Path(self._path, filename))
        filename = self.add_file(filename)
        return open(filename, mode)

def main():
    """Quick manual test entrypoint for the file manager module."""
    fm = FilesManager("Test")
    print(fm.add_file("resources/css/print.css"))
    print(fm.add_directory("resources/images/moon-phases", FilesManager.IMAGES_PATH))
    # pass

if __name__ == "__main__":
    main()
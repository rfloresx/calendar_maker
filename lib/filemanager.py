from io import TextIOWrapper

import pathlib
import shutil
import os

class FilesManager:
    IMAGES = set([".png", ".jpg", ".jpeg", ".bmp"])
    IMAGES_PATH = "images"
    DOCS = set([])
    CSS = set(['.css'])
    CSS_PATH = "css"

    _instance: 'FilesManager' = None

    @staticmethod
    def instance() -> 'FilesManager':
        if FilesManager._instance is None:
            FilesManager._instance = FilesManager()
        return FilesManager._instance

    def __init__(self, project_directory: str):
        self._path: pathlib.Path = pathlib.Path(project_directory).absolute()
        if not self._path.exists():
            self._path.mkdir(parents=True, exist_ok=True)
        FilesManager._instance = self
        self._filename: pathlib.Path = pathlib.Path(self._path, "files.zip")

    @property
    def root(self) -> pathlib.Path:
        return self._path

    def get_relative_path(self, path:str) -> str:
        if not path:
            return path
        try:
            return str(pathlib.Path(path).relative_to(self._path))
        except ValueError:
            return path

    def get_file_path(self, filename: str) -> pathlib.Path:
        if not pathlib.Path(filename).is_absolute():
            src_file = pathlib.Path(self._path, filename).absolute()
            if not src_file.parent.exists():
                src_file.parent.mkdir(parents=True, exist_ok=True)
            return src_file
        else:
            return pathlib.Path(filename)

    def get_target_path(self, filename: str) -> pathlib.Path:        
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
        path = str(pathlib.Path(path).absolute())
        parent = str(self._path)
        return path.startswith(parent)

    def open(self, filename, mode) -> TextIOWrapper:
        filename = str(pathlib.Path(self._path, filename))
        filename = self.add_file(filename)
        return open(filename, mode)

def main():
    fm = FilesManager("Test")
    print(fm.add_file("resources/css/print.css"))
    print(fm.add_directory("resources/images/moon-phases", FilesManager.IMAGES_PATH))
    # pass

if __name__ == "__main__":
    main()
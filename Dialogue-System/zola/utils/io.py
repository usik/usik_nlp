import asyncio
import errno
import json
import logging
import os
import tarfile
import tempfile
import typing
import warnings
import zipfile
import glob
from asyncio import AbstractEventLoop
from io import BytesIO as IOReader
from pathlib import Path
from typing import Text, Any, Dict, Union, List, Type, Callable

import ruamel.yaml as yaml

from zola.constants import *

if typing.TYPE_CHECKING:
    from prompt_toolkit.validation import Validator

DEFAULT_ENCODING = constants.DEFAULT_ENCODING

def configure_colored_logging(loglevel):
    import coloredlogs

    loglevel = loglevel or os.environ.get(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL)

    field_styles = coloredlogs.DEFAULT_FIELD_STYLES.copy()
    field_styles["asctime"] = {}

    level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
    level_styles["debug"] = {}

    coloredlogs.install(
        level = loglevel,
        use_chroot = False,
        fmt="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
        level_styles = level_styles,
        field_styles = field_styles,
    )

def enable_async_loop_debugging(event_loop: AbstractEventLoop, slow_callback_duration: float=0.1
)-> AbstractEventLoop:
    logging.info("코루틴 디버깅 활성화. Loop id {}.".format(id(asyncio.get_event_loop())))

    # 디버깅 활성화
    event_loop.set_debug(True)

    #느린 태스크의 threshold를 작게 만들기. 기본값: 0.1 (100 ms)
    event_loop…slow_callback_duration = slow_callback_duration

    #Async 이상현상 로깅
    warnings.simplefilter("always", ResourceWarning)
    return event_loop

def fix_yaml_loader() -> None:
    """
    Yaml 코드들이 모두 unicode인지 확인
    """
    def construct_yaml_str(self, node):
        return self.construct.scalar(node)

    yaml.Loader.add_constructor("tag:yaml.org,2002:str", construct_yaml_str)
    yaml.SafeLoader.add_constructor("tag:yaml.org,2002:str", construct_yaml_str)

def replace_environment_variables():
    """
    Yaml 로더가 환경변수를 처리하도록 활성화하기
    """
    # 꼭 필요한 함수들
    import re
    import os

    env_var_pattern = re.compile(r"^(.*)\$\{(.*)\}(.*)$")
    yaml.add_implicit_resolver("!env_var", env_var_pattern)

    def env_var_constructor(loader ,node):
        """ YAML 파일에 있는 환경 변수 처리 """

        value = loader.construct_scalar(node)
        expanded_vars = os.path.expandvars(value)
        if "$" in expanded_vars:
            not_expanded = [val for val in expanded_vars.split() if "$" in val]
            raise ValueError(
            "'{}'에서 환경변수 불러오기 에러가 납니다. 아래 변수들도 세팅했는지 확인해주세요"
            "세팅이 필요한 변수들: '{}'.".format(value,not_expanded)
            )
        return expanded_vars
    yaml.SafeConstructor.add_constructor("!env_var", env_var_constructor)

def read_yaml(content: Text) -> Union[List[Any], Dict[Text, Any]]:
    """ 텍스트에서 yaml 읽어오기
        Args:
            content: Yaml 텍스트 파일

    """
    fix_yaml_loader()
    replace_environment_variables()

    yaml_parser = yaml.YAML(typ="safe")
    yaml_parser.version = YAML_PARSER_VERSION
    yaml_parser.unicode_supplementary = True


    try:
        return yaml_parser.load(content) or {}
    except yaml.scanner.ScannerError:

        content = (
            content.encode(DEFAULT_ENCODING)
            .decode("raw_unicode_escape")
            .encode("utf-16","surrogatepass")
            .decode("utf-16")
        )
        return yaml_parser.load(content) or {}

def read_file(filename: Text, encoding: Text = DEFAULT_ENCODING) -> Any:
    """ 파일에서 텍스트 읽어오기 """

    try:
        with open(filename, encoding = encoding) as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError(f"'{filename}' 파일이 존재하지 않습니다.")

def read_json_file(filename:Text) -> Any:
    """ json 형식의 파일 읽어오기 """
    content = read_file(filename)

    try:
        return json.loads(content)
    except ValueError as e:
        raise ValueError(
            "'{}'에서 읽어오기를 실패했습니다. 에러:"
            "{}".format(os.path.abspath(filename),e)
        )
def dump_obj_as_json_to_file(filename: Text, obj: Any) -> None:
    """json string으로 덤프 파일 만들기."""

    write_text_file(json.dumps(obj, indent=2), filename)


def read_config_file(filename: Text) -> Dict[Text, Any]:
    """Config.yml 파일 읽기. Dict 타입일것!
     Args:
        filename: The path to the file which should be read.
    """
    content = read_yaml(read_file(filename))

    if content is None:
        return {}
    elif isinstance(content, dict):
        return content
    else:
        raise ValueError(
            "Tried to load invalid config file '{}'. "
            "Expected a key value mapping but found {}"
            ".".format(filename, type(content))
        )


def read_yaml_file(filename: Text) -> Union[List[Any], Dict[Text, Any]]:
    """Parses a yaml file.
     Args:
        filename: The path to the file which should be read.
    """
    return read_yaml(read_file(filename, DEFAULT_ENCODING))


def unarchive(byte_array: bytes, directory: Text) -> Text:
    """Tries to unpack a byte array interpreting it as an archive.
    Tries to use tar first to unpack, if that fails, zip will be used."""

    try:
        tar = tarfile.open(fileobj=IOReader(byte_array))
        tar.extractall(directory)
        tar.close()
        return directory
    except tarfile.TarError:
        zip_ref = zipfile.ZipFile(IOReader(byte_array))
        zip_ref.extractall(directory)
        zip_ref.close()
        return directory


def write_yaml_file(data: Dict, filename: Union[Text, Path]) -> None:
    """Writes a yaml file.
     Args:
        data: The data to write.
        filename: The path to the file which should be written.
    """
    with open(str(filename), "w", encoding=DEFAULT_ENCODING) as outfile:
        yaml.dump(data, outfile, default_flow_style=False)


def write_text_file(
    content: Text,
    file_path: Union[Text, Path],
    encoding: Text = DEFAULT_ENCODING,
    append: bool = False,
) -> None:
    """Writes text to a file.
    Args:
        content: The content to write.
        file_path: The path to which the content should be written.
        encoding: The encoding which should be used.
        append: Whether to append to the file or to truncate the file.
    """
    mode = "a" if append else "w"
    with open(file_path, mode, encoding=encoding) as file:
        file.write(content)


def is_subdirectory(path: Text, potential_parent_directory: Text) -> bool:
    if path is None or potential_parent_directory is None:
        return False

    path = os.path.abspath(path)
    potential_parent_directory = os.path.abspath(potential_parent_directory)

    return potential_parent_directory in path


def create_temporary_file(data: Any, suffix: Text = "", mode: Text = "w+") -> Text:
    """Creates a tempfile.NamedTemporaryFile object for data.
    mode defines NamedTemporaryFile's  mode parameter in py3."""

    encoding = None if "b" in mode else DEFAULT_ENCODING
    f = tempfile.NamedTemporaryFile(
        mode=mode, suffix=suffix, delete=False, encoding=encoding
    )
    f.write(data)

    f.close()
    return f.name


def create_path(file_path: Text) -> None:
    """Makes sure all directories in the 'file_path' exists."""

    parent_dir = os.path.dirname(os.path.abspath(file_path))
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)


def create_directory_for_file(file_path: Text) -> None:
    """Creates any missing parent directories of this file path."""

    create_directory(os.path.dirname(file_path))


def file_type_validator(
    valid_file_types: List[Text], error_message: Text
) -> Type["Validator"]:
    """Creates a `Validator` class which can be used with `questionary` to validate
       file paths.
    """

    def is_valid(path: Text) -> bool:
        return path is not None and any(
            [path.endswith(file_type) for file_type in valid_file_types]
        )

    return create_validator(is_valid, error_message)


def not_empty_validator(error_message: Text) -> Type["Validator"]:
    """Creates a `Validator` class which can be used with `questionary` to validate
    that the user entered something other than whitespace.
    """

    def is_valid(input: Text) -> bool:
        return input is not None and input.strip() != ""

    return create_validator(is_valid, error_message)


def create_validator(
    function: Callable[[Text], bool], error_message: Text
) -> Type["Validator"]:
    """Helper method to create `Validator` classes from callable functions. Should be
    removed when questionary supports `Validator` objects."""

    from prompt_toolkit.validation import Validator, ValidationError
    from prompt_toolkit.document import Document

    class FunctionValidator(Validator):
        @staticmethod
        def validate(document: Document) -> None:
            is_valid = function(document.text)
            if not is_valid:
                raise ValidationError(message=error_message)

    return FunctionValidator


def list_files(path: Text) -> List[Text]:
    """Returns all files excluding hidden files.
    If the path points to a file, returns the file."""

    return [fn for fn in list_directory(path) if os.path.isfile(fn)]


def list_subdirectories(path: Text) -> List[Text]:
    """Returns all folders excluding hidden files.
    If the path points to a file, returns an empty list."""

    return [fn for fn in glob.glob(os.path.join(path, "*")) if os.path.isdir(fn)]


def _filename_without_prefix(file: Text) -> Text:
    """Splits of a filenames prefix until after the first ``_``."""
    return "_".join(file.split("_")[1:])


def list_directory(path: Text) -> List[Text]:
    """Returns all files and folders excluding hidden files.
    If the path points to a file, returns the file. This is a recursive
    implementation returning files in any depth of the path."""

    if not isinstance(path, str):
        raise ValueError(
            "`resource_name` must be a string type. "
            "Got `{}` instead".format(type(path))
        )

    if os.path.isfile(path):
        return [path]
    elif os.path.isdir(path):
        results = []
        for base, dirs, files in os.walk(path):
            # sort files for same order across runs
            files = sorted(files, key=_filename_without_prefix)
            # add not hidden files
            good_files = filter(lambda x: not x.startswith("."), files)
            results.extend(os.path.join(base, f) for f in good_files)
            # add not hidden directories
            good_directories = filter(lambda x: not x.startswith("."), dirs)
            results.extend(os.path.join(base, f) for f in good_directories)
        return results
    else:
        raise ValueError(
            "Could not locate the resource '{}'.".format(os.path.abspath(path))
        )


def create_directory(directory_path: Text) -> None:
    """Creates a directory and its super paths.
    Succeeds even if the path already exists."""

    try:
        os.makedirs(directory_path)
    except OSError as e:
        # be happy if someone already created the path
        if e.errno != errno.EEXIST:
            raise


def zip_folder(folder: Text) -> Text:
    """Create an archive from a folder."""
    import tempfile
    import shutil

    zipped_path = tempfile.NamedTemporaryFile(delete=False)
    zipped_path.close()

    # WARN: not thread-safe!
    return shutil.make_archive(zipped_path.name, "zip", folder)

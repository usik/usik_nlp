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
    env_var_pattern = re.compile(r"^(.*)\$\{(.*)\}(.*)$")
    yaml.add_implicit_resolver("!env_var", env_var_pattern)
    

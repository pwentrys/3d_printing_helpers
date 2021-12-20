import os
from pathlib import Path
import concurrent.futures


TARGET_FOLDER: str = 'files'
TARGET_FILENAME: str = 'calibration_wheel_3h41m_0.12mm_225C_PLA_ENDER3BLTOUCH'
TARGET_FILENAME_UPDATED: str = f'{TARGET_FILENAME}_updated'
TARGET_FILETYPE: str = 'gcode'
TARGET_FILEPATH: str = f'{TARGET_FILENAME}.{TARGET_FILETYPE}'
TARGET_FILEPATH_UPDATED: str = f'{TARGET_FILENAME_UPDATED}.{TARGET_FILETYPE}'
CWD: Path = Path.cwd()
FILES_FOLDER: Path = CWD.joinpath(TARGET_FOLDER)

FILE_ENCODING: str = 'utf-8'
MAX_WORKERS = os.cpu_count() * 2
if MAX_WORKERS > 61:
    MAX_WORKERS = 61


def ensure_dir_exists(path: Path) -> bool:
    """If directory does not exist, create it.

    Args:
        path (Path): Path we are passing in

    Returns:
        bool: Checks to make sure directory exists.
    """
    dir_exists: bool = path.is_dir()
    if not dir_exists:
        path.mkdir()
        dir_exists: bool = path.is_dir()
        if not dir_exists:
            print(f'Directory does not exist at {path}')
            exit(65)

    return dir_exists


def read_text(path: Path) -> str:
    """Do a read text call on path.

    Args:
        path (Path): Path we are passing in

    Returns:
        str: Output text
    """
    if not path.is_file():
        print(f'Path does not exist at {path}')
        exit(66)

    return path.read_text(encoding=FILE_ENCODING)


def create_dict_from_list(text_list: list) -> dict:
    """Create dictionary from a list of texts using line numbers

    Args:
        text_list (list): Lines from text files

    Returns:
        dict: Enumerated dictionary from text list.
    """
    return {k: v for k, v in enumerate(text_list)}


def get_param_by_first_char(first_char, params: list) -> str:
    for param in params:
        if param[0] == first_char:
            return param[1:]
        else:
            return ''


def do_gcode_transform(text_dict_item: str):
    """Do all the gcode transforms.

    Args:
        text_dict_item (str): Line in gcode we are taking al ook at.

    Returns:
        str: Formatted text.
    """
    output: str = text_dict_item
    if not len(text_dict_item) > 0:
        output = text_dict_item
        return output

    text_dict_item_split = text_dict_item.split(' ')
    if len(text_dict_item_split) > 0:
        first = text_dict_item_split[0]
        params = text_dict_item_split[1:]
        match first:
            case 'M204':
                if len(params) > 0:
                    param_s = get_param_by_first_char('R', params)
                    param_p = get_param_by_first_char('P', params)
                    param_r = get_param_by_first_char('R', params)

                    if param_s:
                        output = f'M204 S{param_s}'
                    elif param_p:
                        output = f'M204 S{param_p}'
                    elif param_r:
                        output = f'M204 S{param_r}'
                    else:
                        output = ''
            case 'M201' | 'M203' | 'M205':
                joined_params = ' '.join(params)
                output = f'#{first} {joined_params}'
            case _:
                pass

    if not isinstance(output, type('')):
        print(text_dict_item)
        print(output)

    return output


def process_text(text: str) -> str:
    """Complete updates on all the text we just passed in from file.

    Args:
        text (str): Text read from file.

    Returns:
        str: Processed and updated text.
    """
    text_split: list = text.splitlines()
    text_dict: dict = create_dict_from_list(text_split)
    text_dict_updated: dict = {}

    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for text_line_number, text_line_out in zip(text_dict, executor.map(do_gcode_transform, text_split)):
            text_dict_updated.update({text_line_number: text_line_out})

    text_list_out: list = list(sorted(text_dict_updated.items()))
    text_out: str = '\n'.join(line[1] for line in text_list_out)

    return text_out


def run():
    """Run all transforms on gcode

    Returns:

    """
    ensure_dir_exists(FILES_FOLDER)
    file: Path = FILES_FOLDER.joinpath(TARGET_FILEPATH)
    text: str = read_text(file)

    text_processed: str = process_text(text=text)
    FILES_FOLDER.joinpath(TARGET_FILEPATH_UPDATED).write_text(text_processed, encoding=FILE_ENCODING)


if __name__ == '__main__':
    run()

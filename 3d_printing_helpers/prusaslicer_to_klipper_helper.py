import os
from pathlib import Path
import concurrent.futures
from datetime import datetime
from pprint import pprint

TARGET_FOLDER: str = 'files'
# TARGET_FILENAME: str = 'calibration_cube_1h48m_0.08mm_215C_PLA_ENDER3BLTOUCH'
TARGET_FILENAME_UPDATED_STRING = '_updated'
# TARGET_FILENAME_UPDATED: str = f'{TARGET_FILENAME}{TARGET_FILENAME_UPDATED_STRING}'
TARGET_FILETYPE: str = 'gcode'
# TARGET_FILEPATH: str = f'{TARGET_FILENAME}.{TARGET_FILETYPE}'
# TARGET_FILEPATH_UPDATED: str = f'{TARGET_FILENAME_UPDATED}.{TARGET_FILETYPE}'
CWD: Path = Path.cwd()
FILES_FOLDER: Path = CWD.joinpath(TARGET_FOLDER)
RUNTIME_FILEPATH: Path = CWD.joinpath('.last_runtime_counter')
NEW_LINE_CHARACTER: str = 'Ω'

FILE_ENCODING: str = 'utf-8'
MAX_WORKERS = os.cpu_count() * 2
if MAX_WORKERS > 61:
    MAX_WORKERS = 61


def update_last_runtime():
    utc_now = datetime.utcnow().timestamp()
    RUNTIME_FILEPATH.write_text(f'{utc_now}', encoding=FILE_ENCODING)


def get_last_runtime() -> float:
    if RUNTIME_FILEPATH.is_file():
        return float(RUNTIME_FILEPATH.read_text(encoding=FILE_ENCODING))
    else:
        return 0.0000000


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
                    param_s = get_param_by_first_char('S', params)
                    param_p = get_param_by_first_char('P', params)
                    param_t = get_param_by_first_char('T', params)

                    if param_s:
                        output = f'M204 S{param_s}'
                    elif param_p:
                        output = f'M204 S{param_p}'
                    elif param_t:
                        output = f'M204 S{param_t}'
                    else:
                        output = ''
            case 'M201' | 'M203' | 'M205':
                # joined_params = ' '.join(params)
                output = ''  # f'#{first} {joined_params}'
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


def determine_files(folder: Path, run_time: float) -> tuple:
    """Determine which files will be looked at

    Args:
        folder (Path): Files folder.
        run_time (float): Last runtime of this script.

    Returns:
        tuple: Tuple of files we are going to process which qualify for running script on.
    """
    files_list: list = []

    file: Path
    for file in folder.iterdir():
        if file.is_file():
            filename = file.name
            if TARGET_FILENAME_UPDATED_STRING not in filename:
                stat = file.stat()
                mod_time = datetime.utcfromtimestamp(stat.st_mtime).timestamp()
                if run_time < mod_time:
                    files_list.append(file)

    return tuple(files_list)


def do_file_transform(file: Path) -> str:
    """Process text in file and then write to updated file.

    Args:
        file (Path): Path of file we will be looking at

    Returns:
        str: Updated filename
    """
    text: str = read_text(file)

    text_processed: str = process_text(text=text)
    filename: str = f'{file.name.replace(f".{TARGET_FILETYPE}", "")}{TARGET_FILENAME_UPDATED_STRING}.{TARGET_FILETYPE}'

    change_every_x_layers: int = 20
    commands: tuple = make_debug_commands(num_commands_to_make=200)
    text_processed_split = text_processed.splitlines()

    counter_layer: int = 0
    counter_after_layer_modify: int = 0
    text_post_processed_split: list = []
    for line in text_processed_split:
        text_post_processed_split.append(line)
        if line.startswith(';AFTER_LAYER_CHANGE'):
            if counter_layer % change_every_x_layers == 0:
                command = commands[counter_after_layer_modify]

                commands_split = command.split('Ω')
                for command_split_line in commands_split:
                    text_post_processed_split.append(command_split_line)

                counter_after_layer_modify += 1

            counter_layer += 1

    text_post_processed: str = '\n'.join(text_post_processed_split)

    file.parent.joinpath(filename).write_text(text_post_processed, encoding=FILE_ENCODING)

    return filename


def create_incrementing_commands(command: str, starting_val: float, increment: float, num_commands_to_make: int) -> tuple:
    """

    Args:
        command:
        starting_val:
        increment:
        num_commands_to_make:

    Returns:

    """
    command_list = []

    for i in range(num_commands_to_make):
        layer_increment: float = increment * i
        layer_increment += starting_val
        if '.' in str(layer_increment):
            layer_increment = float('{0:.4f}'.format(layer_increment))

        layer_command = f'{command}{layer_increment}'
        command_list.append(layer_command)

    return tuple(command_list)


def make_debug_commands(num_commands_to_make: int = 10) -> tuple:
    commands = (
        # create_incrementing_commands(
        #     command='SET_PRESSURE_ADVANCE ADVANCE=',
        #     starting_val=0.00,
        #     increment=0.025,
        #     num_commands_to_make=num_commands_to_make,
        # ),
        # create_incrementing_commands(
        #     command='M117 K',
        #     starting_val=0.00,
        #     increment=0.025,
        #     num_commands_to_make=num_commands_to_make,
        # ),
        create_incrementing_commands(
            command='M221 S',
            starting_val=75.00,
            increment=3.5,
            num_commands_to_make=num_commands_to_make,
        ),
    )

    combined_commands: list = []
    for i in range(num_commands_to_make):
        command_combined_list = (f'{command[i]}' for command in commands)
        command_combined = f'{NEW_LINE_CHARACTER}'.join(command_combined_list)

        combined_commands.append(command_combined)

    return tuple(combined_commands)


def run():
    """Run all transforms on gcode

    Returns:

    """
    start_time = datetime.utcnow()
    print(f'Starting at: {start_time}')

    last_runtime: float = get_last_runtime()
    update_last_runtime()

    ensure_dir_exists(FILES_FOLDER)

    files: tuple = determine_files(folder=FILES_FOLDER, run_time=last_runtime)

    processed = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for file, updated_file in zip(files, executor.map(do_file_transform, files)):
            processed.append(f'{file} - UPDATED - {updated_file}')

    end_time = datetime.utcnow()
    run_time = end_time - start_time

    print(f'Finished at: {end_time}')
    print(f'Run Duration: {run_time}')

    print('\n'.join(processed))


if __name__ == '__main__':
    run()

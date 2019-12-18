import cProfile
import glob
import logging
import os
import platform
import pprint
import pstats  # NOQA
from argparse import ArgumentParser
from multiprocessing import Process  # NOQA
from time import strftime

import andes.common.utils
from andes.common.utils import elapsed
from andes.system import System

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def config_logger(logger=None, name='andes', log_file='andes.log', log_path='', stream=True, file=False,
                  stream_level=logging.INFO, file_level=logging.DEBUG):
    """
    Configure a logger for the andes package with options for a `FileHandler`
    and a `StreamHandler`. This function is called at the beginning of
    ``andes.main.main()``.

    Parameters
    ----------
    name : str, optional
        Base logger name, ``andes`` by default. Changing this
        parameter will affect the loggers in modules and
        cause unexpected behaviours.
    log_file : str, optional
        Logg file name for `FileHandler`, ``'andes.log'`` by default.
        If ``None``, the `FileHandler` will not be created.
    log_path : str, optional
        Path to store the log file. By default, the path is generated by
        get_log_dir() in utils.misc.
    stream : bool, optional
        Create a `StreamHandler` for `stdout` if ``True``.
        If ``False``, the handler will not be created.
    stream_level : {10, 20, 30, 40, 50}, optional
        `StreamHandler` verbosity level.

    Returns
    -------
    None

    """
    if not logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

    if not len(logger.handlers):
        if stream is True:
            sh_formatter = logging.Formatter('%(message)s')
            sh = logging.StreamHandler()

            sh.setFormatter(sh_formatter)
            sh.setLevel(stream_level)
            logger.addHandler(sh)

        # file handler for level DEBUG and up
        if file is True and (log_file is not None):
            log_full_path = os.path.join(log_path, log_file)
            fh_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh = logging.FileHandler(log_full_path)
            fh.setLevel(file_level)
            fh.setFormatter(fh_formatter)
            logger.addHandler(fh)
            logger.debug('Logging to file {}'.format(log_full_path))

        globals()['logger'] = logger


def preamble():
    """
    Log the Andes command-line preamble at the `logging.INFO` level

    Returns
    -------
    None
    """
    from andes import __version__ as version
    logger.info('ANDES {ver} (Build {b}, Python {p} on {os})'
                .format(ver=version[:5], b=version[-8:],
                        p=platform.python_version(),
                        os=platform.system()))
    try:
        username = os.getlogin() + ', '
    except OSError:
        username = ''

    logger.info('Session: {}{}'.format(username, strftime("%m/%d/%Y %I:%M:%S %p")))
    logger.info('')


def cli_parser():
    """
    Construct a CLI argument parser and return the parsed arguments.

    Returns
    -------
    ArgumentParser
        An argument parser for parsing command-line arguments
    """
    parser = ArgumentParser()
    parser.add_argument('filename', help='Case file name', nargs='*')

    # general options
    general_group = parser.add_argument_group('General options')
    general_group.add_argument('-r', '--routine', choices=['tds'], help='Routine to run')
    general_group.add_argument('--edit-config', help='Quick edit of the config file',
                               default='', nargs='?', type=str)
    general_group.add_argument('--license', action='store_true', help='Display software license')

    # I/O
    io_group = parser.add_argument_group('I/O options', 'Optional arguments for managing I/Os')
    io_group.add_argument('-p', '--path', help='Path to case files', type=str, default='', dest='input_path')
    io_group.add_argument('-a', '--addfile', help='Additional files used by some formats.')
    io_group.add_argument('-D', '--dynfile', help='Additional dynamic file in dm format.')
    io_group.add_argument('-P', '--pert', help='Perturbation file path', default='')
    io_group.add_argument('-d', '--dump-raw', help='Dump RAW format case file.')
    io_group.add_argument('-n', '--no-output', help='Force no output of any '
                                                    'kind',
                          action='store_true')
    io_group.add_argument('-o', '--output_path', help='Output path prefix', type=str, default='')
    io_group.add_argument('-C', '--clean', help='Clean output files', action='store_true')

    config_exclusive = parser.add_mutually_exclusive_group()
    config_exclusive.add_argument('--load-config', help='path to the rc config to load',
                                  dest='config')
    config_exclusive.add_argument('--save-config', help='save configuration to file name',
                                  nargs='?', type=str, default='')

    # helps and documentations
    group_help = parser.add_argument_group('Help and documentation',
                                           'Optional arguments for usage, model and config documentation')
    group_help.add_argument(
        '-g', '--group', help='Show the models in the group.')
    group_help.add_argument(
        '-q', '--quick-help', help='Show a quick help of model format.')
    group_help.add_argument(
        '-c',
        '--category',
        help='Show model names in the given category.')
    group_help.add_argument(
        '-l',
        '--model-list',
        help='Show a full list of all models.',
        action='store_true')
    group_help.add_argument(
        '-f',
        '--model-format',
        help='Show the format definition of models.', type=str)
    group_help.add_argument(
        '-Q',
        '--model-var',
        help='Show the definition of variables <MODEL.VAR>.')
    group_help.add_argument(
        '--config-option', help='Show a quick help of a config option <CONFIG.OPTION>')
    group_help.add_argument(
        '--help-config',
        help='Show help of the <CONFIG> class. Use ALL for all configs.')
    group_help.add_argument(
        '-s',
        '--search',
        help='Search for models that match the pattern.')
    group_help.add_argument('-e', '--data_example', help='print example parameter of a given model')

    # simulation control
    sim_options = parser.add_argument_group('Simulation control options',
                                            'Overwrites the simulation configs')
    sim_options.add_argument(
        '--dime', help='Specify DiME streaming server address and port')
    sim_options.add_argument(
        '--tf', help='End time of time-domain simulation', type=float)

    # developer options
    dev_group = parser.add_argument_group('Developer options', 'Options for developer debugging')
    dev_group.add_argument(
        '-v',
        '--verbose',
        help='Program logging level.'
             'Available levels are 10-DEBUG, 20-INFO, 30-WARNING, '
             '40-ERROR or 50-CRITICAL. The default level is 20-INFO',
        type=int, default=20, choices=(10, 20, 30, 40, 50))
    dev_group.add_argument(
        '--profile', action='store_true', help='Enable Python cProfiler')
    dev_group.add_argument(
        '--ncpu', help='Number of parallel processes', type=int, default=os.cpu_count())
    dev_group.add_argument(
        '--show-data', type=str, help='Show model data converted to system base', nargs='*'
    )
    dev_group.add_argument(
        '-x', '--exit', help='Exit before running routine', action='store_true', dest='exit_now'
    )
    dev_group.add_argument('--prepare', help='Prepare the numerical equations and save to file',
                           action='store_true')

    return parser


def remove_output(clean=False, **kwargs):
    """
    Remove the outputs generated by Andes, including power flow reports
    ``_out.txt``, time-domain list ``_out.lst`` and data ``_out.dat``,
    eigenvalue analysis report ``_eig.txt``.

    Parameters
    ----------
    clean : bool
        If ``True``, execute the function body. Returns otherwise.

    kwargs : dict
        Other keyword arguments

    Returns
    -------
    bool
        ``True`` is the function body executes with success. ``False``
        otherwise.
    """
    if not clean:
        return False

    found = False
    cwd = os.getcwd()

    for file in os.listdir(cwd):
        if file.endswith('_eig.txt') or \
                file.endswith('_out.txt') or \
                file.endswith('_out.lst') or \
                file.endswith('_out.dat') or \
                file.endswith('_prof.txt'):
            found = True
            try:
                os.remove(file)
                logger.info('<{:s}> removed.'.format(file))
            except IOError:
                logger.error('Error removing file <{:s}>.'.format(file))
    if not found:
        logger.info('no output found in the working directory.')

    return True


def run(case, options=None):
    t0, _ = elapsed()

    if options is None:
        options = {}

    if case is not None:
        options['case'] = case

    # enable profiler if requested
    pr = cProfile.Profile()
    if options.get('profile') is True:
        pr.enable()

    system = System(options=options)
    system.undill_calls()

    if not andes.io.guess(system):
        return

    if not andes.io.parse(system):
        return

    system.setup()

    system.PFlow.nr()

    if options.get('routine') == 'tds':
        system.TDS.run_implicit()

    return system


def main(args=None):
    t0, _ = elapsed()

    # parser command line arguments
    if args is None:
        parser = cli_parser()
        args = vars(parser.parse_args())
    elif not isinstance(args, dict):
        args = vars(args)

    # configure stream handler verbose level
    config_logger(log_path=andes.common.utils.get_log_dir(), file=True, stream=True,
                  stream_level=args.get('verbose', logging.INFO))
    # show preamble
    preamble()

    system = System()
    pkl_path = system.get_pkl_path()

    if args.get('prepare') is True or (not os.path.isfile(pkl_path)):
        system.prepare()
        logger.info('Symbolic to numeric preparation completed.')

    # process input files
    filename = args.get('filename', ())
    if isinstance(filename, str):
        filename = [filename]

    if len(filename) == 0:
        logger.info('error: no input file. Try \'andes -h\' for help.')

    # preprocess cli args
    path = args.get('input_path', os.getcwd())

    cases = []

    for file in filename:
        # use absolute path for cases which will be respected by FileMan
        full_paths = os.path.abspath(os.path.join(path, file))
        found = glob.glob(full_paths)
        if len(found) == 0:
            logger.info('error: file {} does not exist.'.format(full_paths))
        else:
            cases += found

    # remove folders and make cases unique
    cases = list(set(cases))
    valid_cases = []
    for case in cases:
        if os.path.isfile(case):
            valid_cases.append(case)

    logger.debug('Found files: ' + pprint.pformat(valid_cases))

    if len(valid_cases) <= 0:
        pass
    elif len(valid_cases) == 1:
        run(valid_cases[0], options=args)


if __name__ == '__main__':
    main()

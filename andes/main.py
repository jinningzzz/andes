#!/bin/bash python
import glob
import logging
import os
import io
import sys
import platform
import pprint
import cProfile
import pstats
from subprocess import call
from time import sleep
from typing import Optional, Union

import andes
from andes.system import System
from andes.utils.misc import elapsed, is_interactive
from andes.utils.misc import get_config_path
from andes.shared import coloredlogs, Process

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def config_logger(logger=None,
                  name='andes',
                  stream=True,
                  stream_level=logging.INFO,
                  file=False,
                  log_path='',
                  log_file='andes.log',
                  file_level=logging.DEBUG,
                  color=True):
    """
    Configure a logger for the andes package with options for a `FileHandler`
    and a `StreamHandler`. This function is called at the beginning of
    ``andes.main.main()``.

    Parameters
    ----------
    logger
        Existing logger.
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
                '%(process)d: %(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh = logging.FileHandler(log_full_path)
            fh.setLevel(file_level)
            fh.setFormatter(fh_formatter)
            logger.addHandler(fh)
            logger.debug(f'Logging to file {log_full_path}')

        globals()['logger'] = logger

    if (not is_interactive()) and color:
        coloredlogs.install(logger=logger, level=stream_level, fmt='%(message)s')


def edit_conf(edit_config: Optional[Union[str, bool]] = ''):
    """
    Edit the Andes config file which occurs first in the search path.

    Parameters
    ----------
    edit_config : bool
        If ``True``, try to open up an editor and edit the config file. Otherwise returns.

    Returns
    -------
    bool
        ``True`` is a config file is found and an editor is opened. ``False`` if ``edit_config`` is False.
    """
    ret = False

    # no `edit-config` supplied
    if edit_config == '':
        return ret

    conf_path = get_config_path()

    if conf_path is not None:
        logger.info('Editing config file {}'.format(conf_path))

        if edit_config is None:
            # use the following default editors
            if platform.system() == 'Linux':
                editor = os.environ.get('EDITOR', 'gedit')
            elif platform.system() == 'Darwin':
                editor = os.environ.get('EDITOR', 'vim')
            elif platform.system() == 'Windows':
                editor = 'notepad.exe'
        else:
            # use `edit_config` as default editor
            editor = edit_config

        call([editor, conf_path])
        ret = True

    else:
        logger.info('Config file does not exist. Save config with \'andes '
                    '--save-config\'')
        ret = True

    return ret


def save_conf(config_path=None):
    """
    Save the Andes config to a file at the path specified by ``save_config``.
    The save action will not run if ``save_config = ''``.

    Parameters
    ----------
    config_path : None or str, optional, ('' by default)

        Path to the file to save the config file. If the path is an emtpy
        string, the save action will not run. Save to
        `~/.andes/andes.conf` if ``None``.

    Returns
    -------
    bool
        ``True`` is the save action is run. ``False`` otherwise.
    """
    ret = False

    # no ``--save-config ``
    if config_path == '':
        return ret

    if config_path is not None and os.path.isdir(config_path):
        config_path = os.path.join(config_path, 'andes.rc')

    ps = System()
    ps.save_config(config_path)
    ret = True

    return ret


def remove_output():
    """
    Remove the outputs generated by Andes, including power flow reports
    ``_out.txt``, time-domain list ``_out.lst`` and data ``_out.dat``,
    eigenvalue analysis report ``_eig.txt``.

    Returns
    -------
    bool
        ``True`` is the function body executes with success. ``False``
        otherwise.
    """
    found = False
    cwd = os.getcwd()

    for file in os.listdir(cwd):
        if file.endswith('_eig.txt') or \
                file.endswith('_out.txt') or \
                file.endswith('_out.lst') or \
                file.endswith('_out.npy') or \
                file.endswith('_out.csv') or \
                file.endswith('_prof.prof') or \
                file.endswith('_prof.txt'):
            found = True
            try:
                os.remove(file)
                logger.info('<{:s}> removed.'.format(file))
            except IOError:
                logger.error('Error removing file <{:s}>.'.format(file))
    if not found:
        logger.info('No output file found in the working directory.')

    return True


def print_license():
    with open(os.path.join(os.path.dirname(__file__), '..', 'LICENSE'), 'r') as f:
        print(f.read())
    return True


def run_case(case, routine=None, profile=False, convert='', **kwargs):
    """Run a single simulation case."""

    t0, _ = elapsed()
    if case is not None:
        kwargs['case'] = case

    # enable profiler if requested
    pr = cProfile.Profile()
    if profile is True:
        pr.enable()

    system = System(options=kwargs)
    system.undill_calls()

    if not andes.io.parse(system):
        return

    system.setup()

    # convert to format
    if convert != '':
        andes.io.dump(system, convert)
        return system

    system.PFlow.nr()
    if system.PFlow.converged:
        system.PFlow.write_report()

    if routine == 'tds':
        system.TDS.run_implicit()
        system.TDS.save_output()
    elif routine == 'eig':
        system.EIG.run()

    # Disable profiler and output results
    if profile:
        pr.disable()

        if system.files.no_output:
            nlines = 40
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=sys.stdout).sort_stats('cumtime')
            ps.print_stats(nlines)
            logger.info(s.getvalue())
            s.close()
        else:
            nlines = 999
            with open(system.files.prof, 'w') as s:
                ps = pstats.Stats(pr, stream=s).sort_stats('cumtime')
                ps.print_stats(nlines)
                ps.dump_stats(system.files.prof_raw)
            logger.info(f'cProfile text data written to <{system.files.prof}>.')
            logger.info(f'cProfile raw data written to <{system.files.prof_raw}. View it with \'snakeviz\'.')

    return system


def run(filename, input_path='', ncpu=1, **kwargs):
    if is_interactive():
        config_logger(file=False)

    if len(filename) == 0:
        logger.info('info: no input file. Try \'andes run -h\' for help.')
    elif isinstance(filename, str):
        filename = [filename]

    system = None
    cases = []
    for file in filename:
        # use absolute path for cases which will be respected by FileMan
        full_paths = os.path.abspath(os.path.join(input_path, file))
        found = glob.glob(full_paths)
        if len(found) == 0:
            logger.error('error: file {} does not exist.'.format(full_paths))
        else:
            cases += found

    # remove folders and make cases unique
    unique_cases = list(set(cases))
    valid_cases = []
    for case in unique_cases:
        if os.path.isfile(case):
            valid_cases.append(case)
    if len(valid_cases):
        logger.debug('Found files: ' + pprint.pformat(valid_cases))

    t0, _ = elapsed()
    if len(valid_cases) <= 0:
        pass
    elif len(valid_cases) == 1:
        system = run_case(valid_cases[0], **kwargs)
    else:
        logger.info('Processing {} jobs on {} CPUs'.format(len(valid_cases), ncpu))
        logger.handlers[0].setLevel(logging.WARNING)

        # start processes
        jobs = []
        for idx, file in enumerate(valid_cases):
            job = Process(name='Process {0:d}'.format(idx), target=run_case, args=(file, ), kwargs=kwargs)
            jobs.append(job)
            job.start()

            start_msg = 'Process {:d} <{:s}> started.'.format(idx, file)
            print(start_msg)
            logger.debug(start_msg)

            if (idx % ncpu == ncpu - 1) or (idx == len(valid_cases) - 1):
                sleep(0.1)
                for job in jobs:
                    job.join()
                jobs = []

        # restore command line output when all jobs are done
        logger.handlers[0].setLevel(logging.INFO)

    t0, s0 = elapsed(t0)

    if len(valid_cases) == 1:
        logger.info(f'-> Single process finished in {s0}.')
    elif len(valid_cases) >= 2:
        logger.info(f'-> Multiple processes finished in {s0}.')

    return system


def plot(**kwargs):
    from andes.plot import tdsplot
    tdsplot(**kwargs)


def misc(edit_config='', save_config='', license=False, clean=True, **kwargs):
    if edit_conf(edit_config):
        return True
    if license:
        print_license()
        return True
    if save_config != '':
        save_conf(save_config)
        return True
    if clean is True:
        remove_output()
        return True

    logger.info('info: no option specified. Try \'andes misc -h\' for help.')


def prepare(**kwargs):
    sys = System()
    sys.prepare()
    logger.info('Symbolic to numeric preparation completed.')
    return True

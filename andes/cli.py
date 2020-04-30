import argparse
import sys
import os
import logging
import platform
import importlib

from time import strftime
from andes.main import config_logger, find_log_path
from andes.utils.paths import get_log_dir
from andes.routines import routine_cli

logger = logging.getLogger(__name__)


def create_parser():
    """
    The main level of command-line interface.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-v', '--verbose',
        help='Program logging level in 10-DEBUG, 20-INFO, 30-WARNING, '
             '40-ERROR or 50-CRITICAL.',
        type=int, default=20, choices=(1, 10, 20, 30, 40, 50))

    sub_parsers = parser.add_subparsers(dest='command', help='[run] run simulation routine; '
                                                             '[plot] plot simulation results; '
                                                             '[doc] quick documentation; '
                                                             '[prepare] run the symbolic-to-numeric preparation; '
                                                             '[misc] miscellaneous functions.'
                                        )

    run = sub_parsers.add_parser('run')
    run.add_argument('filename', help='Case file name. Power flow is calculated by default.', nargs='*')
    run.add_argument('-r', '--routine', nargs='*', default=('pflow', ),
                     action='store', help='Simulation routine(s). Single routine or multiple separated with '
                                          'space. Run PFlow by default.',
                     choices=list(routine_cli.keys()))
    run.add_argument('-p', '--input-path', help='Path to case files', type=str, default='')
    run.add_argument('-a', '--addfile', help='Additional files used by some formats.')
    run.add_argument('-P', '--pert', help='Perturbation file path', default='')
    run.add_argument('-o', '--output-path', help='Output path prefix', type=str, default='')
    run.add_argument('-n', '--no-output', help='Force no output of any kind', action='store_true')
    run.add_argument('--ncpu', help='Number of parallel processes', type=int, default=os.cpu_count())
    run.add_argument('--dime', help='Specify DiME streaming server address and port', type=str)
    run.add_argument('--tf', help='End time of time-domain simulation', type=float)
    run.add_argument('--convert', help='Convert to format.', type=str, default='', nargs='?')
    run.add_argument('--convert-all', help='Convert to format with all templates.', type=str, default='',
                     nargs='?')
    run.add_argument('--add-book', help='Add a template workbook for the specified model.', type=str)
    run.add_argument('--state-matrix', help='Export state matrix to a .mat file. Need to run with `-r eig`',
                     action='store_true')
    run.add_argument('--profile', action='store_true', help='Enable Python cProfiler')

    plot = sub_parsers.add_parser('plot')
    plot.add_argument('filename', nargs=1, default=[], help='simulation output file name, which should end '
                                                            'with `out`. File extension can be omitted.')
    plot.add_argument('x', nargs='?', type=int, help='the X-axis variable index, typically 0 for Time',
                      default='0')
    plot.add_argument('y', nargs='*', help='Y-axis variable indices. Space-separated indices or a '
                                           'colon-separated range is accepted')
    plot.add_argument('--xmin', type=float, help='minimum value for X axis', dest='left')
    plot.add_argument('--xmax', type=float, help='maximum value for X axis', dest='right')
    plot.add_argument('--ymax', type=float, help='maximum value for Y axis')
    plot.add_argument('--ymin', type=float, help='minimum value for Y axis')
    find_or_xargs = plot.add_mutually_exclusive_group()
    find_or_xargs.add_argument('--find', type=str, help='find variable indices that matches the given pattern')
    find_or_xargs.add_argument('-a', '--xargs', type=str,
                               help='find variable indices and return as a list of arguments '
                                    'usable with "|xargs andes plot"')
    plot.add_argument('--exclude', type=str, help='pattern to exclude in find or xargs results')
    plot.add_argument('-x', '--xlabel', type=str, help='x-axis label text')
    plot.add_argument('-y', '--ylabel', type=str, help='y-axis label text')
    plot.add_argument('-s', '--savefig', action='store_true', help='save figure. The default format is `png`')
    plot.add_argument('-f', '--format', dest='save_format',
                      help='format for savefig. Common formats such as png, pdf, jpg are supported')
    plot.add_argument('--dpi', type=int, help='image resolution in dot per inch (DPI)')
    plot.add_argument('-g', '--grid', action='store_true', help='grid on')
    plot.add_argument('--greyscale', action='store_true', help='greyscale on')
    plot.add_argument('-d', '--no-latex', action='store_false', dest='latex', help='disable LaTex formatting')
    plot.add_argument('-n', '--no-show', action='store_false', dest='show', help='do not show the plot window')
    plot.add_argument('--ytimes', type=str, help='scale the y-axis values by YTIMES')
    plot.add_argument('-c', '--tocsv', help='convert npy output to csv', action='store_true')

    misc = sub_parsers.add_parser('misc')
    config_exclusive = misc.add_mutually_exclusive_group()
    config_exclusive.add_argument('--edit-config', help='Quick edit of the config file',
                                  default='', nargs='?', type=str)
    config_exclusive.add_argument('--save-config', help='save configuration to file name',
                                  nargs='?', type=str, default='')
    misc.add_argument('--license', action='store_true', help='Display software license', dest='show_license')
    misc.add_argument('-C', '--clean', help='Clean output files', action='store_true')

    prep = sub_parsers.add_parser('prepare')  # NOQA
    prep.add_argument('-q', '--quick', action='store_true', help='quick processing by skipping pretty prints')

    doc = sub_parsers.add_parser('doc')  # NOQA
    doc.add_argument('attribute', help='System attribute name to get documentation', nargs='?')
    doc.add_argument('--config', '-c', help='Config help')
    doc.add_argument('--list', '-l', help='List supported models and groups', action='store_true',
                     dest='list_supported')

    selftest = sub_parsers.add_parser('selftest')  # NOQA

    return parser


def preamble():
    """
    Log the ANDES command-line preamble at the `logging.INFO` level
    """
    from andes import __version__ as version

    py_version = platform.python_version()
    system_name = platform.system()
    date_time = strftime('%m/%d/%Y %I:%M:%S %p')
    logger.info("\n"
                rf"    _           _         | Version {version}" + '\n'
                rf"   /_\  _ _  __| |___ ___ | Python {py_version} on {system_name}, {date_time}" + '\n'
                rf"  / _ \| ' \/ _` / -_|_-< | " + "\n"
                rf' /_/ \_\_||_\__,_\___/__/ | This program comes with ABSOLUTELY NO WARRANTY.' + '\n')

    log_path = find_log_path(logging.getLogger("andes"))
    if len(log_path):
        logger.debug(f'Logging to file {log_path[0]}')


def main():
    """Main command-line interface"""
    parser = create_parser()
    args = parser.parse_args()

    config_logger(stream=True,
                  stream_level=args.verbose,
                  file=True,
                  log_path=get_log_dir(),
                  )
    logger.debug(args)

    module = importlib.import_module('andes.main')

    if args.command not in ('plot', 'doc'):
        preamble()

    if args.command is None:
        parser.parse_args(sys.argv.append('--help'))

    else:
        func = getattr(module, args.command)
        return func(cli=True, **vars(args))

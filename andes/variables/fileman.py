import logging
import os

logger = logging.getLogger(__name__)


class FileMan(object):
    """Define a File Manager class for System"""

    def __init__(self):
        """
        Initialize the output file names.
        For inputs, all absolute paths will be respected; and all relative paths are relative to `input_path`.

        case: must be full path to case

        output: desired name for format conversion output

        input_path: default path for input files that only contains file name. If `input_path` is not provided,
                    it will be derived from the path of `case`.

        output_path: path for output files. Default to current working directory where `andes` is invoked.
        """
        self.input_format = None
        self.output_format = None
        self.add_format = None

        self.case = None
        self.case_path = os.getcwd()
        self.fullname = None
        self.name = None
        self.ext = None
        self.addfile = None
        self.pert = None
        self.dynfile = None

        self.output_path = None

        self.no_output = True
        self.output = None
        self.lst = None
        self.eig = None
        self.dat = None
        self.prof = None

    def set(self, case=None, **kwargs):

        input_format = kwargs.get('input_format')
        add_format = kwargs.get('add_format')
        input_path = kwargs.get('input_path')

        addfile = kwargs.get('addfile')
        no_output = kwargs.get('no_output')
        dynfile = kwargs.get('dynfile')
        output_path = kwargs.get('output_path', os.getcwd())
        output = kwargs.get('output')  # base file name for the output
        pert = kwargs.get('pert')

        if case is None:
            return

        self.input_format = input_format
        self.add_format = add_format
        self.input_path = input_path if input_path is not None else os.getcwd()
        self.output_path = os.getcwd() if not output_path else output_path

        if os.path.isabs(case):
            self.case = case
        else:
            self.case = self.get_fullpath(case)
            logger.debug(self.case)

        # update `self.case_path` if `case` contains a path
        self.case_path, self.fullname = os.path.split(self.case)

        # `self.name` is the name part without extension
        self.name, self.ext = os.path.splitext(self.fullname)

        self.addfile = self.get_fullpath(addfile)
        self.pert = self.get_fullpath(pert)
        self.dynfile = self.get_fullpath(dynfile)

        # use the path where andes is executed as the default output path
        self.output_path = os.getcwd() if not output_path else output_path
        if no_output:
            self.no_output = True
            self.output = None
            self.lst = None
            self.eig = None
            self.dat = None
            self.prof = None
        else:
            self.no_output = False
            if not output:
                output = add_suffix(self.name, 'out')
            prof = add_suffix(self.name, 'prof')
            eig = add_suffix(self.name, 'eig')

            self.lst = os.path.join(self.output_path, output + '.lst')
            self.dat = os.path.join(self.output_path, output + '.dat')
            self.output = os.path.join(self.output_path, output + '.txt')

            self.eig = os.path.join(self.output_path, eig + '.txt')
            self.prof = os.path.join(self.output_path, prof + '.txt')

    def get_fullpath(self, fullname=None):
        """
        Return the original full path if full path is specified, otherwise
        search in the case file path
        """
        # if is an empty path
        if not fullname:
            return fullname

        isabs = os.path.isabs(fullname)

        path, name = os.path.split(fullname)

        if not name:  # path to a folder
            return None
        else:  # path to a file
            if isabs:
                return fullname
            else:
                return os.path.join(self.case_path, path, name)


def add_suffix(fullname, suffix):
    """ Add suffix to a full file name"""
    name, ext = os.path.splitext(fullname)
    return name + '_' + suffix + ext


import os
import sys
import struct
import numpy as np

import sys
if sys.version_info[0] < 3:
    from .lsda_py2 import Lsda
else:
    from .lsda_py3 import Lsda


'''
## Recoded stuff from lsda from LSTC, but much more readable and quoted ...
#
class Diskfile:

    # symbol = binary variable / python translation
    # note: bolded means unsigned
    #
    # b = char / int
    # h = short / int
    # i = int   / int
    # q = long long / int
    # f = float  / float
    # d = double / float
    # s = char[] / string

    packsize = [0,"b","h",0,"i",0,0,0,"q"]
    packtype = [0,"b","h","i","q","B","H","I","Q","f","d","s"]
    sizeof = [0,1,2,4,8,1,2,4,8,4,8,1] # packtype

    ##
    #
    #
    def __init__(self,filepath,mode="r"):

        # This opens a file and mainly treats the header
        #
        # header[0] == header length & header offset ?!? | default=8 byte
        # header[1] == lengthsize  | default = 8 byte
        # header[2] == offsetsize  | default = 8 byte
        # header[3] == commandsize | default = 1 byte
        # header[4] == typesize    | default = 1 byte
        # header[5] == file endian | default = 1 byte
        # header[6] == ?           | default = 0 byte
        # header[7] == ?           | default = 0 byte

        # start init
        self.filepath = filepath
        self.mode = mode
        self.file_ends = False

        # open file ...
        self.fp = open(filepath,mode+"b")
        # ... in read mode yay
        if mode == "r":
            header = struct.unpack("BBBBBBBB",self.fp.read(8))
            if header[0] > 8: #?!? some kind of header offset ?!?
                self.fp.seek(header[0])
        # ... in write mode
        else:
            header = [8,8,8,1,1,0,0,0]
            if sys.byteorder == "big":
                header[5] = 0
            else:
                header[5] = 1

        # fetch byte length of several ... I honestly don't know what exactly
        self.lengthsize    = header[1]
        self.offsetsize    = header[2]
        self.commandsize   = header[3]
        self.typesize      = header[4]
        self.ordercode = ">" if header[5] == 0 else '<' # endian

        # again I have no idea what is going on ...
        # these are some data unpacking format codes
        self.ounpack  =  self.ordercode+Diskfile.packsize[self.offsetsize]
        self.lunpack  =  self.ordercode+Diskfile.packsize[self.lengthsize]
        self.lcunpack = (self.ordercode+
                        Diskfile.packsize[self.lengthsize]+
                        Diskfile.packsize[self.commandsize])
        self.tolunpack = (self.ordercode+
                        Diskfile.packsize[self.typesize]+
                        Diskfile.packsize[self.offsetsize]+
                        Diskfile.packsize[self.lengthsize])
        self.comp1 = self.typesize+self.offsetsize+self.lengthsize
        self.comp2 = self.lengthsize+self.commandsize+self.typesize+1

        # write header if write mode
        if mode == "w":
            header_str = ''
            for value in header:
                s += struct.pack("B",value) # convert to unsigned char
            self.fp.write(s)
            #self.writecommand(17,Lsda.SYMBOLTABLEOFFSET)
            #self.writeoffset(17,0)
            #self.lastoffset = 17

    # UNFINISHED
'''


## This class is meant to read binouts from LS-Dyna
#
# This class is only a utility wrapper for Lsda from LSTC.
class Binout:


    ## Constructor for a binout
    #
    # @param str filepath
    def __init__(self,filepath):

        # check
        if not os.path.isfile(filepath):
            raise IOError("File %s does not exist." % filepath)

        self.filepath = filepath
        self.lsda = Lsda(filepath,"r")

        #if sys.version_info[0] < 3:
        #    self.lsda_root = self.lsda.root
        #else:
        #    self.lsda_root = self.lsda.root.children[""]
        self.lsda_root = self.lsda.root
        

    ## Read all data from Binout (top to low level)
    # 
    # @param str/list(str) *path : path to read within binout. Leave empty fir top level.
    # @return see description
    #
    # @example read()/read("swforc")/read("swforc","time")/read("swforc/time")
    #
    # Since this command reads everything, the following return types are possible:
    #   - path/to/dir : list(str) names of directory content
    #   - path/to/ids : np.array(int) ids
    #   - path/to/variable : np.array(float) vars
    #
    def read(self, *path):
        
        # TODO decode path if str (by /)

        var_names = [] # dummy
        iLevel = len(path)

        # LEVEL 0 : no args (top)
        if iLevel == 0: 
            return self._bstr_to_str( list( self.lsda_root.children.keys() ) )
        
        # LEVEL 1 : Subdirs(Names) (swforc, nodout, ...)
        elif iLevel == 1:
            
            dir_name = path[0]

            # subdir
            subdir_symbol = self.lsda_root.get(dir_name)
            if not subdir_symbol:
                raise ValueError("dir %s does not exist." % dir_name)

            # search subsubdir vars (metadata + states)
            var_names = set()
            for subsubdir_name, subsubdir_symbol in subdir_symbol.children.items():
                var_names = var_names.union( subsubdir_symbol.children.keys() )

            return self._bstr_to_str( list(var_names) ) 

        # LEVEL 2 : Variables (reading of data series)
        elif iLevel == 2:

            dir_name = path[0]
            variable_name = self._str_to_bstr(path[1]) # variables are somehow binary strings ... dirs not

            dir_symbol = self.lsda_root.get(dir_name)
            if not dir_symbol:
                raise ValueError("dir %s does not exist." % dir_name)

            # search var in metadata
            if "metadata" in dir_symbol.children and variable_name in dir_symbol.get("metadata").children:
                return np.asarray( dir_symbol.get("metadata").get(variable_name).read() )
            # var in state data ... hopefully
            else:

                time = []
                data = []
                for subdir_name, subdir_symbol in dir_symbol.children.items():
                    
                    # skip metadata
                    if subdir_name == "metadata":
                        continue
                    
                    # read data
                    if variable_name in subdir_symbol.children:
                        time += subdir_symbol.get(b"time").read()
                        data += subdir_symbol.get(variable_name).read()
                
                # return sorted by time
                return np.array(data)[np.argsort(time)]
            
        
        # LEVEL 3+ : Error
        else:
            raise ValueError("Your path is longer than 3 ")


    ## Get the labels of the file
    #
    # @param str folder_name = None : subdirectory to investigate. None is root
    #
    # Get the labels of either the top directories in the file (folder_name=None)
    # or the labels of data in the subdirectories, e.g  folder_name="matsum".
    # This routine is meant for looking into the file.
    def get_labels(self,folder_name=None):
        raise DeprecationWarning("\"binout.get_labels\" is deprecated. Use \"binout.read\".")


    ## Encodes or decodes a string correctly regarding python version
    #
    # @param str/unicode/bytes string
    # @return str string : converted to python version
    #
    def _bstr_to_str(self, arg):

        # in case of a list call this function with its atomic strings
        if isinstance(arg, (list,tuple) ):
            return [ self._bstr_to_str(entry) for entry in arg ]

        # convert a string (dependent on python version)
        if not isinstance(arg, str):
            return arg.encode("utf-8")
        else:
            return arg


    ## Convert a string to a binary string python version independent
    #
    # @param str string
    # @param bstr string
    def _str_to_bstr(self,string):

        if not isinstance(string, bytes):
            return string.decode("utf-8")
        else:
            return string


    ## Developers only: Scan the file subdirs.
    #
    # @param int nMaxChildren = 10 : limit of children to abort (e.g. we hit data)
    def _scan_file(self,nMaxChildren=10):
        self._print_tree_item(self.lsda_root,0,nMaxChildren=nMaxChildren)


    ## Developers only: print a lsda symbol item recursively
    #
    # @param Symbol item : symbol instance
    # @param int level : current depth level
    # @param int nMaxChildren = 10 : limit of children to abort (e.g. we hit data)
    # @param bool stop_level : level at which we stop looking deeper
    def _print_tree_item(self,item,level,nMaxChildren=10,stop_level=None):

        if item.type == 0: # dir
            print("%s> %s" % ("-"*level,item.name))
            if len(item.children) < nMaxChildren and level < stop_level:
                for child_name in item.children:
                    self._print_tree_item(item.children[child_name],level+1,nMaxChildren,stop_level=stop_level)

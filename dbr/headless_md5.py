# -*- coding: utf-8 -*-

## \package dbr.md5

# MIT licensing
# See: docs/LICENSE.txt


import os

from dbr.language       import GT
from dbr.log            import Logger
from globals.execute    import GetCommandOutput
from globals.execute    import GetExecutable
from globals.fileio     import WriteFile
from globals.ident      import chkid
from globals.ident      import pgid


## Creates a file of md5 hashes for files within the staged directory
#  
#  FIXME: Should binary files be handled differently?
#  \param stage_dir
#    Temporary directory to scan files into list
#  \param parent
#    The window to be parent of error messages
def WriteMD5(stage_dir, parent=None):
    CMD_md5sum = GetExecutable(u'md5sum')    
    temp_list = []
    md5_list = [] # Final list used to write the md5sum file
    for ROOT, DIRS, FILES in os.walk(stage_dir):
        # Ignore the 'DEBIAN' directory
        if os.path.basename(ROOT) == u'DEBIAN':
            continue
        
        for F in FILES:
            F = u'{}/{}'.format(ROOT, F)
            
            md5 = GetCommandOutput(CMD_md5sum, (u'-t', F))
            
            Logger.Debug(__name__, u'WriteMD5: GetCommandOutput: {}'.format(md5))
            
            temp_list.append(md5)
    
    for item in temp_list:
        # Remove [stage_dir] from the path name in the md5sum so that it has a
        # true unix path
        # e.g., instead of "/myfolder_temp/usr/local/bin", "/usr/local/bin"
        sum_split = item.split(u'{}/'.format(stage_dir))
        sum_join = u''.join(sum_split)
        md5_list.append(sum_join)
    
    # Create the md5sums file in the "DEBIAN" directory
    return WriteFile(u'{}/DEBIAN/md5sums'.format(stage_dir), u'{}\n'.format(u'\n'.join(md5_list)))

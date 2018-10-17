from dbr.log import Logger
from dbr.log            import DebugEnabled
from dbr.headless_md5   import WriteMD5
from globals.fileio     import ReadFile
from globals.fileio     import WriteFile
from globals.execute    import GetExecutable
from globals.paths      import ConcatPaths
from globals.headless_execute    import ExecuteCommand
from dbr.headless_functions      import FileUnstripped
import commands,argparse, os, re, shutil

def arguments_init():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loglevel", help='log level amongst info error warn debug', default='debug')
    parser.add_argument("--projectfile", help='debreate project file to open', default='debreate.dbp')

    return parser.parse_args()

def OpenProject(project_file):
    Logger.Debug(__name__, u'Opening project: {}'.format(project_file))
    
    if not os.path.isfile(project_file):
        Logger.Debug(__name__, u'File does not exist or is not a regular file: {}'.format(project_file))
        return False
    
    data = ReadFile(project_file)
    
    lines = data.split(u'\n')
    
    # *** Get Control Data *** #
    control_data = data.split(u'<<CTRL>>\n')[1].split(u'\n<</CTRL>>')[0]
    #depends_data = self.Wizard.GetPage(pgid.CONTROL).Set(control_data)
    #self.Wizard.GetPage(pgid.DEPENDS).Set(depends_data)
    
    # *** Get Files Data *** #
    files_data = data.split(u'<<FILES>>\n')[1].split(u'\n<</FILES>>')[0]
    #opened = self.Wizard.GetPage(pgid.FILES).Set(files_data)
    
    # *** Get Scripts Data *** #
    scripts_data = data.split(u'<<SCRIPTS>>\n')[1].split(u'\n<</SCRIPTS>>')[0]
    #self.Wizard.GetPage(pgid.SCRIPTS).Set(scripts_data)
    
    # *** Get Changelog Data *** #
    clog_data = data.split(u'<<CHANGELOG>>\n')[1].split(u'\n<</CHANGELOG>>')[0]
    #self.Wizard.GetPage(pgid.CHANGELOG).Set(clog_data)
    
    # *** Get Copyright Data *** #
    try:
        cpright_data = data.split(u'<<COPYRIGHT>>\n')[1].split(u'\n<</COPYRIGHT')[0]
        #self.Wizard.GetPage(pgid.COPYRIGHT).Set(cpright_data)
    
    except IndexError:
        cpright_data = None
    
    # *** Get Menu Data *** #
    m_data = data.split(u'<<MENU>>\n')[1].split(u'\n<</MENU>>')[0]
    #self.Wizard.GetPage(pgid.MENU).SetLauncherData(m_data, enabled=True)
    
    # Get Build Data
    build_data = data.split(u'<<BUILD>>\n')[1].split(u'\n<</BUILD')[0]#.split(u'\n')
    #self.Wizard.GetPage(pgid.BUILD).Set(build_data)
    
    return True, (control_data, files_data, scripts_data, clog_data, cpright_data, m_data, build_data)

def GetValue(page, field):
    stringa = r'{}: ([\d\w\-_\.]+)'.format(field)
    regex=re.compile(stringa)
    page_lines=page.split('\n')
    #Damn '\n' in page string. 
    for p in page_lines:
        m = regex.match(p)
        if m is not None:
            return m.group(1)

def ParseScript(script_part):
    scripts = {}

    preinst_present  = script_part.split(u'<<PREINST>>\n')[1].split(u'\n')[0] == u'1'
    postinst_present = script_part.split(u'<<POSTINST>>\n')[1].split(u'\n')[0] == u'1'
    prerm_present    = script_part.split(u'<<PRERM>>\n')[1].split(u'\n')[0] == u'1'
    postrm_present   = script_part.split(u'<<POSTRM>>\n')[1].split(u'\n')[0] == u'1'

    if preinst_present:
        preinst_text = script_part.split(u'<<PREINST>>\n')[1].split(u'\n<</PREINST')[0]
        #drop first line
        scripts[u'preinst'] = '\n'.join(preinst_text.split('\n')[1:])

    if postinst_present:
        postinst_text = script_part.split(u'<<POSTINST>>\n')[1].split(u'\n<</POSTINST')[0]
        #drop first line
        scripts[u'postinst'] = '\n'.join(postinst_text.split('\n')[1:])

    if prerm_present:
        prerm_text = script_part.split(u'<<PRERM>>\n')[1].split(u'\n<</PRERM')[0]
        #drop first line
        scripts[u'prerm'] = '\n'.join(prerm_text.split('\n')[1:])

    if postrm_present:
        postrm_text = script_part.split(u'<<POSTRM>>\n')[1].split(u'\n<</POSTRM')[0]
        #drop first line
        scripts[u'postrm'] = '\n'.join(postrm_text.split('\n')[1:])

    return scripts


## TODO: Doxygen
#  
#  \return
#    \b \e tuple containing Return code & build details
def BuildPrep(loaded_data):
    # List of tasks for build process
    # 'stage' should be very first task
    task_list = {}
    
    # Control page
    pg_control = loaded_data[0]
    
    # Get information from control page for default filename
    package = GetValue(pg_control, 'Package')
    # Remove whitespace
    package = package.strip(u' \t')
    package = u'-'.join(package.split(u' '))
    
    version = GetValue(pg_control, 'Version')
    # Remove whitespace
    version = version.strip(u' \t')
    version = u''.join(version.split())
    
    #arch = GetField(pg_control, inputid.ARCH).GetStringSelection()
    arch = GetValue(pg_control, 'Architecture')
    
    complete_filename = u'/home/giacomo/checkout/debreate/{}_{}_{}.deb'.format(package, version, arch)
    
    build_path = os.path.split(complete_filename)[0]
    filename = os.path.split(complete_filename)[1].split(u'.deb')[0]

    task_list[u'files'] = loaded_data[1].split('\n')[1:]
    
    task_list[u'scripts'] = ParseScript(loaded_data[2])
    
    task_list[u'changelog'] = (u'STANDARD', ''.join(loaded_data[3].split(r'/DEST>>')[1:]))
    task_list[u'copyright'] = loaded_data[4]

    task_list[u'md5sums'] = None
    task_list[u'strip'] = None
    task_list[u'rmstage'] = None
    task_list[u'lintian'] = None
    
    return (task_list, build_path, filename)

def Build(task_list, build_path, filename, loaded_data):
        # Declare this here in case of error before progress dialog created
        build_progress = None
        
        # Other mandatory tasks that will be processed
        mandatory_tasks = (
            u'stage',
            u'install_size',
            u'control',
            u'build',
            )
        
        # Add other mandatory tasks
        for T in mandatory_tasks:
            task_list[T] = None
        
        task_count = len(task_list)
        
        # Add each file for updating progress dialog
        if u'files' in task_list:
            task_count += len(task_list[u'files'])
        
        # Add each script for updating progress dialog
        if u'scripts' in task_list:
            task_count += len(task_list[u'scripts'])
        
        create_changelog = u'changelog' in task_list
        create_copyright = u'copyright' in task_list

        if DebugEnabled():
            Logger.Debug(__name__, u'Total tasks: {}'.format(task_count))
            for T in task_list:
                print(u'\t{}'.format(T))


        pg_control = loaded_data[0]
        package = GetValue(pg_control, 'Package')
        # Remove whitespace
        package = package.strip(u' \t')
        package = u'-'.join(package.split(u' '))

        #This is used only by launchers and for the moment no support for them
        #pg_menu = GetPage(pgid.MENU)
        
        stage_dir = u'{}/{}__dbp__'.format(build_path, filename)
        
        if os.path.isdir(u'{}/DEBIAN'.format(stage_dir)):
            try:
                shutil.rmtree(stage_dir)
            
            except OSError:
                Logger.Debug(__name__, u'Could not free stage directory: {}'.format(stage_dir))
                return

        # Actual path to new .deb
        deb = u'"{}/{}.deb"'.format(build_path, filename)
        
        progress = 0
        
        task_msg = (u'Preparing build tree')
        Logger.Debug(__name__, task_msg)
        
        DIR_debian = ConcatPaths((stage_dir, u'DEBIAN'))
        
        # Make a fresh build tree
        os.makedirs(DIR_debian)
        
        # *** Files *** #
        if u'files' in task_list:
            
            files_data = task_list[u'files']
            for FILE in files_data:
                file_defs = FILE.split(u' -> ')
                
                source_file = file_defs[0]
                target_file = u'{}{}/{}'.format(stage_dir, file_defs[2], file_defs[1])
                target_dir = os.path.dirname(target_file)
                
                if not os.path.isdir(target_dir):
                    os.makedirs(target_dir)
                
                # Remove asteriks from exectuables
                exe = False
                if source_file[-1] == u'*':
                    Logger.Debug(__name__, u'Adding executable to stage: {}'.format(target_file))
                    exe = True
                    source_file = source_file[:-1]
                
                if os.path.isdir(source_file):
                    Logger.Debug(__name__, u'Adding directory to stage: {}'.format(target_file))
                    
                    # HACK: Use os.path.dirname to avoid OSError: File exists
                    shutil.copytree(source_file, u'{}/{}'.format(target_dir, os.path.basename(source_file)))
                    
                    os.chmod(target_file, 0755)
                
                else:
                    Logger.Debug(__name__, u'Adding file to stage: {}'.format(target_file))
                    
                    shutil.copy(source_file, target_dir)
                    
                    # Set FILE permissions
                    if exe:
                        os.chmod(target_file, 0755)
                    
                    else:
                        os.chmod(target_file, 0644)
            
            # Entire file task
            progress += 1
        
        # *** Strip files ***#
        # FIXME: Needs only be run if 'files' step is used
        if u'strip' in task_list:
            Logger.Debug(__name__, u'Stripping files...')
            for ROOT, DIRS, FILES in os.walk(stage_dir):
                for F in FILES:
                    # Don't check files in DEBIAN directory
                    if ROOT != DIR_debian:
                        F = ConcatPaths((ROOT, F))
                        
                        if FileUnstripped(F):
                            Logger.Debug(__name__, u'Unstripped file: {}'.format(F))
                            
                            # FIXME: Strip command should be set as class member?
                            ExecuteCommand(GetExecutable(u'strip'), F)
            
            progress += 1        
        
        
        # Make sure that the directory is available in which to place documentation
        if create_changelog or create_copyright:
            doc_dir = u'{}/usr/share/doc/{}'.format(stage_dir, package)
            if not os.path.isdir(doc_dir):
                os.makedirs(doc_dir)
        
        # *** Changelog *** #
        if create_changelog:
            Logger.Debug(__name__, u'Creating changelog...')
            # If changelog will be installed to default directory
            changelog_target = task_list[u'changelog'][0]
            if changelog_target == u'STANDARD':
                changelog_target = ConcatPaths((u'{}/usr/share/doc'.format(stage_dir), package))
            
            else:
                changelog_target = ConcatPaths((stage_dir, changelog_target))
            
            if not os.path.isdir(changelog_target):
                os.makedirs(changelog_target)
            
            WriteFile(u'{}/changelog'.format(changelog_target), task_list[u'changelog'][1])
            
            CMD_gzip = GetExecutable(u'gzip')
            
            if CMD_gzip:
                Logger.Debug(__name__, (u'Compressing changelog'))
                c = u'{} -n --best "{}/changelog"'.format(CMD_gzip, changelog_target)
                clog_status = commands.getstatusoutput(c.encode(u'utf-8'))
                if clog_status[0]:
                    Logger.Error(u'Could not compress changelog {}'.format( clog_status[1]))
            
            progress += 1
    
        
        # *** Copyright *** #
        if create_copyright:
            Logger.Debug(__name__, u'Creating copyright...')
            WriteFile(u'{}/usr/share/doc/{}/copyright'.format(stage_dir, package), task_list[u'copyright'])
            
            progress += 1
        
        
        # Characters that should not be in filenames
        invalid_chars = (u' ', u'/')
        
        # *** Menu launcher *** #
        #if u'launcher' in task_list: #No support for launchers sorry 
        if False:
            UpdateProgress(progress, GT(u'Creating menu launcher'))
            
            # This might be changed later to set a custom directory
            menu_dir = u'{}/usr/share/applications'.format(stage_dir)
            
            menu_filename = pg_menu.GetOutputFilename()
            
            # Remove invalid characters from filename
            for char in invalid_chars:
                menu_filename = menu_filename.replace(char, u'_')
            
            if not os.path.isdir(menu_dir):
                os.makedirs(menu_dir)
            
            WriteFile(u'{}/{}.desktop'.format(menu_dir, menu_filename), task_list[u'launcher'])
            
            progress += 1
        
        
        # *** md5sums file *** #
        # Good practice to create hashes before populating DEBIAN directory
        if u'md5sums' in task_list:
            Logger.Debug(__name__, u'Calculating MD5 checksum...')
            if not WriteMD5(stage_dir, parent=build_progress):
                # Couldn't call md5sum command
                Logger.Error(__name__,'Could not compute md5')
                return
            
            progress += 1
        
        # *** Scripts *** #
        if u'scripts' in task_list:
            
            scripts = task_list[u'scripts']
            for SCRIPT in scripts:
                script_name = SCRIPT
                script_text = scripts[SCRIPT]
                Logger.Debug(__name__, u'Including script {}'.format(script_name))
                
                script_filename = ConcatPaths((stage_dir, u'DEBIAN', script_name))
                
                WriteFile(script_filename, script_text)
                
                # Make sure scipt path is wrapped in quotes to avoid whitespace errors
                os.chmod(script_filename, 0755)
                os.system((u'chmod +x "{}"'.format(script_filename)))
                
            
            # Entire script task
            progress += 1
        
        # Get installed-size
        installed_size = os.popen((u'du -hsk "{}"'.format(stage_dir))).readlines()
        installed_size = installed_size[0].split(u'\t')
        installed_size = installed_size[0]
        
        # Insert Installed-Size into control file
        control_data = pg_control.split(u'\n')
        control_data.insert(2, u'Installed-Size: {}'.format(installed_size))
        
        progress += 1
        
        # dpkg fails if there is no newline at end of file
        control_data = u'\n'.join(control_data).strip(u'\n')
        # Ensure there is only one empty trailing newline
        # Two '\n' to show physical empty line, but not required
        # Perhaps because string is not null terminated???
        control_data = u'{}\n\n'.format(control_data)
        
        WriteFile(u'{}/DEBIAN/control'.format(stage_dir), control_data, noStrip=u'\n')
        
        progress += 1
        
        working_dir = os.path.split(stage_dir)[0]
        c_tree = os.path.split(stage_dir)[1]
        deb_package = u'{}.deb'.format(filename)
        
        # Move the working directory becuase dpkg seems to have problems with spaces in path
        os.chdir(working_dir)
        # FIXME: Should check for working fakeroot & dpkg-deb executables
        build_status = commands.getstatusoutput((u'{} {} -b "{}" "{}"'.format(GetExecutable(u'fakeroot'), GetExecutable(u'dpkg-deb'), c_tree, deb_package)))
        
        # *** Delete staged directory *** #
        if u'rmstage' in task_list:
            Logger.Debug(__name__, u'Removing staging directory...')
            try:
                shutil.rmtree(stage_dir)
            
            except OSError:
                Logger.Error(u'An error occurred when trying to delete the build tree')
        
        # *** ERROR CHECK
        if u'lintian' in task_list:
            Logger.Debug(__name__, u'Running lintian...')
            # FIXME: Should be set as class memeber?
            CMD_lintian = GetExecutable(u'lintian')
            errors = commands.getoutput((u'{} {}'.format(CMD_lintian, deb)))
            if errors != '':
                e1 = (u'Lintian found some issues with the package.')
                e2 = (u'Details saved to {}').format(filename)
                
                WriteFile(u'{}/{}.lintian'.format(build_path, filename), errors)
                Logger.Warn(__name__, e1)
                Logger.Warn(__name__, e2)
            
            progress += 1
        
        # Close progress dialog

        
        # Build completed successfullly
        if build_status[0]:
            Logger.Error(__name__, 'Error in build: {}'.format(build_status[1]))
            return 

        Logger.Info(__name__, 'Build successful!')


if __name__=='__main__':
    args = arguments_init()

    Logger.SetLogLevel(args.loglevel)

    Logger.Debug(__name__, u'Opening Projectfile {}'.format(args.projectfile))

    opened, loaded_data = OpenProject(args.projectfile)
    task_list, build_path, filename = BuildPrep(loaded_data)

    Build(task_list, build_path, filename, loaded_data)

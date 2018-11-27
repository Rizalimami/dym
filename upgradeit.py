#!/usr/bin/python

from distutils.dir_util import copy_tree
import sys, os, shutil, json, simplejson, ast
from glob import glob
import subprocess

def set_folders(module):
    dirs = os.walk(module).next()[1]
    files = os.walk(module).next()[2]
    py = []
    xml = []
    ipy = []
    init_lines = ''
    for p in files:
        if p.endswith('.py') and p not in ['__openerp__.py','__init__.py']:
            py.append(p)
        if p.endswith('.xml'):
            xml.append(p)
        if p.endswith('.py') and p in ['__init__.py']:
            with open(os.path.join(module,p),'r') as f:
                init_lines = f.readlines()
            with open(os.path.join(module,p),'r') as f:
                init_lines2 = f.read()

    init_models = ''
    for x in init_lines:
        if x.startswith('#'):
            continue
        if 'report' in x:
            continue
        if 'models' in x:
            continue
        if 'wizard' in x:
            continue
        init_models += x

    if py:
        models_dir = os.path.join(module,"models")
        if 'models' not in dirs:
            os.makedirs(models_dir)
            dirs.append('models')
        for f in py:
            source = os.path.join(module,f)
            destination = os.path.join(models_dir,f)
            os.rename(source, destination)        
        init_file = os.path.join(models_dir,"__init__.py")
        if not os.path.isfile(init_file):
            with open(init_file,'w') as f:
                f.write(init_models)

    if xml:
        views_dir = os.path.join(module,"views")
        if 'views' not in dirs:
            os.makedirs(views_dir)

        for f in xml:
            source = os.path.join(module,f)
            destination = os.path.join(views_dir,f)
            os.rename(source, destination)        

    file_init = []
    for d in dirs:
        dirrrr = os.path.join(module,d,'__init__.py')
        if os.path.isfile(dirrrr):
            file_init.append('import %s' % d)
    if file_init:
        file_init = '\n'.join(file_init)
    else:
        file_init = ''    
    if file_init:
        with open(os.path.join(module,"__init__.py"),'w') as f:
            f.write(file_init)

    with open(os.path.join(module,"__openerp__.py"),'r') as f:
        manifest = f.read()

    with open(os.path.join(module,"__openerp__.py"),'r') as f:
        lines = f.readlines()

    new_manifest = ''
    for l in lines:
        nl = l.strip().replace('"','').replace(',','')
        if '.xml' in nl and nl in xml:
            l = l.replace(nl,'views/'+nl)
        new_manifest += l
    with open(os.path.join(module,"__openerp__.py"),'w') as f:
        f.write(new_manifest)

    static_source = os.path.join("upgradeit","static")
    static_dest = os.path.join(module,"static")
    if not os.path.isfile(static_dest):
        copy_tree(static_source, static_dest)

    with open(os.path.join(module,"static","description","index.html"),'r') as f:
        index = f.read()

    with open(os.path.join(module,"static","description","index.html"),'w') as f:
        name = module.replace('_',' ').title()
        subname = 'Manage %s' % name.replace('Dym ','')
        index = index.replace('Master Branch',name)
        index = index.replace('Manage company branches',subname)
        f.write(index)
        
for module in glob("dym_*"):
    podir = os.path.join(module,"i18n")
    try:
        os.makedirs(podir)
    except:
        pass
    pofile = "%s.po" % module
    set_folders(module)


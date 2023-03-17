#!/usr/bin/python3

"""
Copyright 2023 ESPCI Paris PSL
Contributor: Vincent Démery

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>. 3 


# -*- coding: utf-8 -*-
    
"""




import os, sys

from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.markdown import Markdown
from rich import box

import argparse
import shlex
from cmd import Cmd
import subprocess



path = '~/Documents/Recherche'


class Projects :

    def __init__(self, path):
        self.console = Console()
        self.path = path

    def read_proj_file (self, proj_file) :
        proj = {}
        tree = []
        kws = ['state', 'status', 'collabs']
        
        with open(proj_file) as f :
            lines = f.read().split('\n')
            
            for line in lines:
                if len(line) > 0 :
                    if line[0] == '#' :
                        l = 0
                        while line[0] == '#' :
                            l += 1
                            line = line[1:]
                        tree.append([l, line.strip(), []])
                    else :
                        tree[-1][2].append(line.strip())
                        for kw in kws:
                            if '**' + kw + ':**' in line.casefold() :
                                proj[kw] = line[5+len(kw):].strip()
                        
        for s in tree :
            s[2] = '\n'.join(s[2])
            if s[1].casefold() == 'to do' :
                proj['todo'] = s[2]
            
        proj['name'] = tree[0][1]
        
        return proj


    def read_projects (self, verb=False):
        projs = []
        for d in os.walk(os.path.expanduser(self.path)) :
            if 'project.md' in d[2] :
                proj_path = d[0][len(self.path)+1:]
                p = self.read_proj_file(os.path.join(d[0], 'project.md'))
                p['path'] = proj_path
                p['last_mod'] = os.path.getmtime(d[0])
                projs.append(p)
                
        projs = sorted(projs, key=lambda p: p['last_mod'])
        
        count = 0
        for p in projs:
            count += 1
            p['count'] = count
            
        self.projs = projs
        
        if verb :
            self.console.print('{} projects found'.format(len(projs)))

        return projs

    
    def print_project (self, proj, level=0) :
        self.console.print("[blue]{}.[/] {}".format(proj['count'], proj['name']), 
                      style='bold magenta', highlight=False)
        if level==1:
            self.console.print('    ' + proj['path'], highlight=False)
        elif level>1:
            self.console.print(proj)
            

    def print_projects (self, sel='all', level=0):
        if sel=='all':
            sel = range(len(self.projs))         
        
        if level>0 :
            for c in sel :
                self.print_project (self.projs[c], level=level)
        else :
            grid = Table(expand=True, show_header=False, show_lines=True, 
                         box=box.SIMPLE, show_edge=False)
            grid.add_column(justify="right", style='bold blue')
            grid.add_column(style='bold magenta')
            grid.add_column(style='bold red')
            for c in sel :
                p = self.projs[c]
                td = ''
                if 'todo' in p :
                    if len(p['todo']) > 0 :
                        td = 'TD'
                grid.add_row(str(p['count']), p['name'], td)
            self.console.print(grid)

    
    def print_proj_md (self, c) :
        p = self.projs[c]
        MARKDOWN = ""
        with open(os.path.join(path, p['path'], 'project.md')) as f :
            for l in f.readlines():
                MARKDOWN +=l 
            
        md = Markdown(MARKDOWN)
        self.console.print(md)
        self.console.print('\n\n{}'.format(p['path']), style="blue italic", highlight=False)
        
        
    def open_dir (self, c) :
        p = self.projs[c]
        self.print_project(p, level=0)
        subprocess.run(['xdg-open', os.path.join(self.path, p['path'])],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def print_todos (self):
        MARKDOWN = "# To do list"
        for p in self.projs :
            if 'todo' in p :
                if len(p['todo']) > 0 :
                    MARKDOWN += '\n\n## [{}] {}\n\n{}'.format(p['count'], p['name'], p['todo'])
        md = Markdown(MARKDOWN)
        self.console.print(md)
                

    def search_projects(self, search) :
        found = []
        for c, p in enumerate(self.projs) :
            if all([s.casefold() in p['name'].casefold() for s in search]) :
                found.append(c)
        return found
        
    
    class MyPrompt(Cmd):
        prompt = 'pjs> '
                                     
        def __init__(self, projs, completekey='tab', stdin=None, stdout=None):
            Cmd.__init__(self, completekey=completekey, stdin=stdin, stdout=stdout)
            
            self.projs = projs
            self.console = projs.console
            
            self.searchparser = argparse.ArgumentParser()
            self.searchparser.add_argument("search", nargs='+')
            self.searchparser.add_argument("-a", "--active", help="excludes published works",
                                      action="store_true")
            self.searchparser.add_argument("-l", "--level", help="level of detail", 
                                      default=0, type=int)


            self.listparser = argparse.ArgumentParser()
            self.listparser.add_argument("-l", "--level", help="level of detail", 
                                      default=0, type=int)
            
        
        def do_list(self, inp):
            """
            List all the projects
            Shorthand: l
            """
            try : 
                largs = self.listparser.parse_args(shlex.split(inp))
            except :
                self.console.print("Invalid argument", style='italic red')
                return False
                
            self.projs.print_projects(level=largs.level)
                
        def do_search(self, inp):
            """
            Search in projects
            Usage: search [strings to search separated by spaces]
            Shorthand: s
            """
            sargs = self.searchparser.parse_args(shlex.split(inp))
            sel = self.projs.search_projects(sargs.search)
            self.projs.print_projects(sel, level=sargs.level)
        
        def do_expand(self, inp):
            """
            Display the full information on a project
            Usage: expand [project number]
            Shorthand: e
            """
            try :
                count = int(inp)
                p = self.projs.projs[count-1]
            except :
                self.console.print('Not a valid number', style='italic red')
                return False
                
            self.projs.print_proj_md(count-1)
            
 
        def do_todo(self, inp):
            """
            Show the list of todos
            Shorthand: t
            """
            self.projs.print_todos()
            
        def do_open(self, inp):
            """
            Open a project in the file manager
            Usage: open [project number]
            Shorthand: o"""
            
            try :
                count = int(inp)
                p = self.projs.projs[count-1]
            except :
                self.console.print('Not a valid number', style='italic red')
                return False
            
            self.projs.open_dir(count-1)
            

        def do_update(self, inp):
            """
            Update the projects list
            Shorthand: u
            """
            self.projs.read_projects(verb=True)

        def do_exit(self, inp):
            """Exit the application. Shorthand: x q Ctrl-D."""
            return True
        
        def default(self, inp):
            if inp == 'x' or inp == 'q':
                return self.do_exit(inp)
            elif inp[0] == 'l':
                return self.do_list(inp[1:])
            elif inp[0] == 's':
                return self.do_search(inp[1:])
            elif inp[0] == 'e':
                return self.do_expand(inp[1:])
            elif inp[0] == 'o':
                return self.do_open(inp[1:])
            elif inp[0] == 't':
                return self.do_todo(inp[1:])
     
        do_EOF = do_exit

    def run (self):
        self.read_projects()
        self.console.print("Welcome to Projects!", style='bold red',
                           justify="center")
        self.console.print("\n {} projects found".format(len(self.projs)))
        prompt = self.MyPrompt(self)
        prompt.cmdloop()
    

p = Projects(path)
p.run()


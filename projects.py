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
import numpy as np
import pandas as pd
import re
import time

from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.markdown import Markdown
from rich.theme import Theme
from rich import box

import argparse
import shlex
from cmd import Cmd
import subprocess

path = '~/Documents/Recherche'

style_theme = Theme({
    "number": "bold dark_blue",
    "title": "bold dark_magenta",
    "alert": "bold red",
    "alerti": "italic red",
    "path": "italic deep_sky_blue4"
})

class Projects :

    def __init__(self, path, style_theme):
        self.console = Console(theme=style_theme)
        self.path = os.path.expanduser(path)

    def read_proj_file (self, proj_file) :
        proj = {}
        tree = []
        
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

                        m = re.search("^\*\*.*:\*\*",line)
                        if m :
                            kw = m.group()[2:-3].casefold()
                            proj[kw] = line[5+len(kw):].strip()
                            
        proj['name'] = tree[0][1]
        
        for s in tree :
            if s[1].casefold() == 'to do' :
                proj['todo'] = '\n'.join(s[2])
            elif s[1].casefold() == 'documents' :
                docs = []
                for line in s[2] :
                    m = re.search("\[.*\]\(.*\)",line)
                    if m :
                        docs.append(m.group().split('](')[1][:-1])
                proj['documents'] = docs
            
        return proj


    def read_projects (self, verb=False):
        projs = []
        if verb :
            self.console.print('Searching projects', end='')

        for d in os.walk(self.path) :
            if 'project.md' in d[2] :
                proj_path = d[0][len(self.path)+1:]
                p = self.read_proj_file(os.path.join(d[0], 'project.md'))
                p['path'] = proj_path
                p['last_mod'] = os.path.getmtime(d[0])
                projs.append(p)
                if verb :
                    self.console.print('.', end='')
                    
        projs = sorted(projs, key=lambda p: p['last_mod'])
        
        count = 0
        for p in projs:
            count += 1
            p['count'] = count
        
        if verb :
            self.console.print('\n[number]{}[/] projects found'.format(len(projs)))
            
        pdf = pd.DataFrame(projs)
        
        pdf.fillna('', inplace=True)
        
        self.projs_pd = pdf
        #will replace self.projs once the dataframe is used everywhere
        
        #To insert later: save/load dataframe
        pdf.to_pickle(os.path.join(self.path, '.projects.pkl'))

        return projs
    
    
    def load_projects (self):
        pickle_path = os.path.join(self.path, '.projects.pkl')
        if os.path.isfile(pickle_path):
            self.projs_pd = pd.read_pickle(pickle_path)
        else :
            self.read_projects(verb=True)
            

    
    def print_project (self, proj, level=0) :
        self.console.print("[blue]{}.[/] {}".format(proj['count'], proj['name']), 
                           style="title", highlight=False)
        if level==1:
            self.console.print('    ' + proj['path'], highlight=False)
        elif level>1:
            self.console.print(proj)
            

    def print_projects (self, sel=[], level=0):
        if len(sel) == 0:
            sel = range(self.projs_pd.shape[0])
        
        if level>1 :
            for c in sel :
                self.print_project (self.projs_pd.iloc[c], level=level)
        else :
            grid = Table(expand=True, show_header=False, show_lines=True, 
                         box=box.SIMPLE, show_edge=False)
            grid.add_column(justify="right", style='number')
            grid.add_column()
            grid.add_column(style="alert")
            for c in sel :
                p = self.projs_pd.iloc[c]
                td = ''
                if type(p['todo']) == str :
                    if len(p['todo']) > 0 :
                        td = 'TD'
                if level == 0:
                    grid.add_row(str(c+1), '[title]' + p['name'] + '[/]', td)
                elif level == 1 :
                    grid.add_row(str(c+1),
                                 '[title]' + p['name'] + '[/]\n[path]' + p['path'] + '[/]',
                                 td)
            self.console.print(grid)
        
        self.console.rule(style='black')

    
    def print_proj_md (self, c) :
        p = self.projs_pd.iloc[c]
        MARKDOWN = ""
        with open(os.path.join(self.path, p['path'], 'project.md')) as f :
            for l in f.readlines():
                MARKDOWN +=l 
            
        md = Markdown(MARKDOWN)
        self.console.print(md)
        self.console.print('\n\n{}'.format(p['path']), style="path", highlight=False)
        self.console.rule(style='black')
        
        
    def open_dir (self, c) :
        p = self.projs_pd.iloc[c]
        self.print_project(p, level=0)
        subprocess.run(['xdg-open', os.path.join(self.path, p['path'])],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.console.rule(style='black')
    
    def open_doc (self, c, n=0) :
        p = self.projs_pd.iloc[c]
        try : 
            doc_path = os.path.join(self.path, p['path'], p['documents'][n])
        except :
            self.console.print("Invalid document number", style='alerti')
            return False
        
        self.console.print(doc_path, style="path", highlight=False)
        if os.path.isfile(doc_path) :
            subprocess.run(['xdg-open', doc_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else :
            self.console.print("Document not found", style='alerti')
            
        self.console.rule(style='black')
    
    
    def print_todos (self):
        md_string = "# To do list"
        hastodo = np.flatnonzero(self.projs_pd['todo'].str.len().gt(0))
        
        for c in hastodo :
            p = self.projs_pd.iloc[c]
            md_string += '\n\n## [{}] {}\n\n{}'.format(p['count'], p['name'], p['todo'])
        
        md = Markdown(md_string)
        self.console.print(md)
        self.console.rule(style='black')
                

    def search_projects(self, sargs) :
        search_regex = ''.join(['(?=.*' + s + ')' for s in sargs.search])
        s = self.projs_pd['name'].str.contains(search_regex, regex=True, case=False)
        found = np.flatnonzero(s)
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
                self.console.print("Invalid argument", style='alerti')
                return False
                
            self.projs.print_projects(level=largs.level)
                
        def do_search(self, inp):
            """
            Search in projects
            Usage: search [strings to search separated by spaces]
            Shorthand: s
            """
            sargs = self.searchparser.parse_args(shlex.split(inp))
            sel = self.projs.search_projects(sargs)
            #self.console.print(sel)
            if len(sel) == 0:
                self.console.print("Nothing found", style='alerti')
            else :
                self.projs.print_projects(sel, level=sargs.level)
        
        def do_expand(self, inp):
            """
            Display the full information on a project
            Usage: expand [project number]
            Shorthand: e
            """
            try :
                count = int(inp)
                p = self.projs.projs_pd.iloc[count-1]
            except :
                self.console.print('Not a valid number', style='alerti')
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
                p = self.projs.projs_pd.iloc[count-1]
            except :
                self.console.print('Not a valid number', style='alerti')
                return False
            
            self.projs.open_dir(count-1)
            
        def do_doc(self, inp):
            """
            Open a document
            Usage: doc [project number] [document number]
            Shorthand: d
            """
            inp = shlex.split(inp)
            
            try :
                count = int(inp[0])
                p = self.projs.projs_pd.iloc[count-1]
                
                n = 0
                if len(inp) > 1 :
                    n = int(inp[1]) - 1
            except :
                self.console.print('Not a valid number', style='alerti')
                return False
            
            self.projs.open_doc(count-1, n)
            

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
            elif inp[0] == 'd':
                return self.do_doc(inp[1:])
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
            elif inp[0] == 'u':
                return self.do_update(inp[1:])
     
        do_EOF = do_exit

    def run (self):
        self.console.print("Welcome to Projects!", style='bold red',
                           justify="center")
        self.load_projects()
        prompt = self.MyPrompt(self)
        prompt.cmdloop()
    

p = Projects(path, style_theme)
p.run()


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
import configparser

import subprocess

from itertools import cycle
from textual.app import App, ComposeResult
from textual.widgets import Input, Static, Button, DataTable, Footer, Markdown, LoadingIndicator, Checkbox
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll


class Projects :

    def __init__(self, path):
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
                        docs.append(m.group().split('](')[1].split(')')[0])
                proj['documents'] = docs
        
        proj['search'] = " ".join([proj['name'], proj.get('keywords', "")]).strip()
            
        return proj


    def read_projects (self):
        projs = []

        for d in os.walk(self.path) :
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
                    
        pdf = pd.DataFrame(projs)
        
        pdf.fillna('', inplace=True)
        
        self.projs_pd = pdf
        
        pdf.to_pickle(os.path.join(self.path, '.projects.pkl'))

        return projs
    
    
    def load_projects (self):
        pickle_path = os.path.join(self.path, '.projects.pkl')
        if os.path.isfile(pickle_path):
            self.projs_pd = pd.read_pickle(pickle_path)
        else :
            self.read_projects()
            

    def search_projects(self, search) :
        #search_regex = ''.join(['(?=.*' + s + ')' for s in sargs.search])
        search_regex = ''.join(['(?=.*' + s + ')' for s in search])
        s = self.projs_pd['search'].str.contains(search_regex, regex=True, case=False)
        found = np.flatnonzero(s)
        return found
        


class MyApp(App):
    TITLE = "Projects"
    CSS_PATH = "projects.css"
    CONF = "projects.conf"
    
    BINDINGS = [
        Binding(key="q", action="quit", description="Quit"),
        Binding(key="s", action="search", description="Search"),
        Binding(key="e", action="expand", description="Expand"),
        Binding(key="o", action="open", description="Open"),
        Binding(key="t", action="show_todos", description="Todo list"),
        Binding(key="u", action="update", description="Update"),
        Binding(key="escape", action="escape", description="Return", show=False),
        Binding(key="ctrl+f", action="show_filters", description="Filters"),
    ]

    def compose(self) -> ComposeResult:
        self.main_window = Vertical(id="main_window")
        with self.main_window :
            self.plist = DataTable(id="list")
            yield self.plist
            self.search = Input(placeholder="Search", id="search")
            yield self.search
            self.fsb = Vertical(id="fsb")
            with self.fsb :
                self.cb_active = Checkbox("Active", True)
                self.cb_published = Checkbox("Published")
                self.cb_other = Checkbox("Other")
                yield Static("Filters")
                yield self.cb_active
                yield self.cb_published
                yield self.cb_other
                
            self.vs = VerticalScroll(id="vs")
            with self.vs :
                yield Markdown(id="expand")

        yield Footer()
        
        
        
    def filter_sel(self):
        sel = self.sel
        if len(sel) == 0:
            sel = range(self.projs.projs_pd.shape[0])
        
        new_sel = []
        for c in sel :
            p = self.projs.projs_pd.iloc[c]
            pstate = p['state'].casefold()
            if pstate == 'active' :
                if self.cb_active.value :
                    new_sel.append(c)
            elif pstate == 'published' :
                if self.cb_published.value :
                    new_sel.append(c)
            else :
                if self.cb_other.value :
                    new_sel.append(c)
        
        self.sel = new_sel
        
    
    
    def print_projects_list(self):
        self.filter_sel()
        sel = self.sel
        
        self.plist.clear()
        
        for c in sel :
            p = self.projs.projs_pd.iloc[c]
            td = ""
            if len(p['todo'])>0:
                td = "*"
            self.plist.add_row(td, p['name'], height=1)
            
    
    def on_mount(self) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(os.path.dirname(__file__), 'projects.conf'))
        
        if not self.config.getboolean('DEFAULT', 'dark') :
            self.action_toggle_dark()
        
        
        self.projs = Projects(self.config['DEFAULT']['path'])
        self.projs.load_projects()
        self.sel = []
        
        table = self.plist
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("T", "Name")
        table.show_header = False
        self.print_projects_list()
        table.focus()
        
        self.vs.display = False
        self.fsb.display = False


    def action_search(self):
        self.search.focus()
    

    def action_expand(self, toggle=True, count=-1):
        vs = self.vs
        expand = self.query_one(Markdown)
        
        if vs.display and toggle :
            vs.display = False
        else :
            if count==-1 :
                table = self.plist
                
                if self.sel == [] :
                    self.expanded = table.cursor_row
                else :
                    self.expanded = self.sel[table.cursor_row]
            else :
                self.expanded = count

            p = self.projs.projs_pd.iloc[self.expanded]
            MARKDOWN = ""
            with open(os.path.join(self.projs.path, p['path'], 'project.md')) as f :
                for l in f.readlines():
                    MARKDOWN +=l 

            expand.update(MARKDOWN)
            
            vs.display = True

    def action_open(self):
        table = self.plist
        if self.vs.display :
            c = self.expanded
        else :
            if self.sel == [] :
                c = table.cursor_row
            else :
                c = self.sel[table.cursor_row]
            
        p = self.projs.projs_pd.iloc[c]
        
        subprocess.run(['xdg-open', os.path.join(self.projs.path, p['path'])],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def action_show_todos (self):
        MARKDOWN = "# To do list"
        hastodo = np.flatnonzero(self.projs.projs_pd['todo'].str.len().gt(0))
        
        for c in hastodo :
            p = self.projs.projs_pd.iloc[c]
            MARKDOWN += '\n\n## [{}]({})\n\n{}'.format(p['name'], p['count'], p['todo'])
        
        expand = self.query_one(Markdown)
        expand.update(MARKDOWN)
            
        self.vs.display = True
    
    def action_update(self):
        #li = LoadingIndicator(id="update")
        #await self.mount(li)
        
        self.projs.read_projects()
        self.print_projects_list()
        
        #time.sleep(5)
        #li.remove()

        
    def clear_search(self):
        search = self.search
        search.action_end()
        search.action_delete_left_all()

            
    def action_escape(self):
        if not self.vs.display :
            self.clear_search()
            if not self.sel == [] :
                c = self.sel[self.plist.cursor_row]
                self.sel = []
                self.print_projects_list()
                self.plist.move_cursor(row=c)
                self.plist.focus()
        else:
            self.vs.display = False
        
    def action_show_filters(self):  
        if not self.vs.display :
            self.fsb.display = not self.fsb.display
    
    def on_input_submitted(self):
        self.sel = self.projs.search_projects(self.search.value.split(" "))
        self.print_projects_list()
        self.plist.focus() #Does not seem to produce anything
        
    
    def on_markdown_link_clicked(self, message: Markdown.LinkClicked):
        if message.href.isdigit() :
            c = int(message.href)
            self.action_expand(toggle=False, count=c-1)
        else :
            p = self.projs.projs_pd.iloc[self.expanded]
            doc_path = os.path.join(self.projs.path, p['path'], message.href)
            if os.path.isfile(doc_path) :
                to_open = doc_path
            else :
                to_open = message.href

            subprocess.run(['xdg-open', to_open],
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
                               
                               
    def on_checkbox_changed(self, message: Checkbox.Changed):
        self.sel = self.projs.search_projects(self.search.value.split(" "))
        self.print_projects_list()
                               
                               
        
        
if __name__ == "__main__":
    app = MyApp()
    app.run()


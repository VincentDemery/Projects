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
from urllib.parse import unquote
from itertools import cycle

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Input, Static, Button, DataTable, Footer, Markdown, LoadingIndicator, Checkbox, SelectionList, Pretty
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll


class Projects :
    def __init__(self, path):
        self.path = os.path.expanduser(path)

    def read_proj_file (self, path) :
        proj = {}
        
        proj['path'] = path[len(self.path)+1:]
        proj['last_mod'] = os.path.getmtime(path)
        
        with open(os.path.join(path, 'project.md')) as f :
            proj['md'] = f.read()
        
        tree = []
        for line in proj['md'].split('\n') :
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
        
        return proj


    def read_projects (self):
        projs = []

        for d in os.walk(self.path) :
            if 'project.md' in d[2] :
                p = self.read_proj_file(d[0])
                projs.append(p)
                    
        projs = sorted(projs, key=lambda p: p['last_mod'])
        
        count = 0
        for p in projs:
            p['count'] = count
            count += 1
                    
        pdf = pd.DataFrame(projs)
        
        pdf.fillna('', inplace=True)
        
        self.projs_pd = pdf
        
        self.write_projects()

        return projs
        
        
    def write_projects (self):
        self.projs_pd.to_pickle(os.path.join(self.path, '.projects.pkl'))
    
    
    def load_projects (self):
        pickle_path = os.path.join(self.path, '.projects.pkl')
        if os.path.isfile(pickle_path):
            self.projs_pd = pd.read_pickle(pickle_path)
        else :
            self.read_projects()
            

    def search_projects(self, search_string) :
        if search_string == "" :
            return range(self.projs_pd.shape[0])
        else :
            search = search_string.split(" ")
            search_regex = ''.join(['(?=.*' + s + ')' for s in search])
            s = self.projs_pd['md'].str.contains(search_regex, regex=True, case=False, 
                                                 flags=re.DOTALL)
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
        Binding(key="u", action="update_selected", description="Update selected"),
        Binding(key="ctrl+u", action="full_update", description="Full update"),
        Binding(key="escape", action="escape", description="Return", show=False),
        Binding(key="ctrl+e", action="edit_project_file", description="Edit"),
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
                self.sl_filters = SelectionList[str](
                    ("Active", "active", True),
                    ("Published", "published"),
                    ("Other", "other"))
                yield self.sl_filters
                
            self.vs = VerticalScroll(id="vs")
            with self.vs :
                yield Markdown(id="expand")

        yield Footer()
        
        
    def print_projects_list(self, keep_cursor=True):
        if keep_cursor :
            cursor_count, p = self.get_selected_project()
        
        self.update_selection()
                
        self.plist.clear()
        
        for c in self.sel :
            p = self.projs.projs_pd.iloc[c]
            td = ""
            if len(p['todo'])>0:
                td = "*"
            self.plist.add_row(td, p['name'], height=1)
        
        #self.plist.move_cursor(row=2)
        if keep_cursor and cursor_count in self.sel :
            row = self.sel.index(cursor_count)
            self.plist.move_cursor(row=row)
        else :
            self.plist.move_cursor(row=len(self.sel)-1)
            
    
    def on_mount(self) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(os.path.dirname(__file__), 'projects.conf'))
        
        if not self.config.getboolean('DEFAULT', 'dark') :
            self.action_toggle_dark()
        
        
        self.projs = Projects(self.config['DEFAULT']['path'])
        self.projs.load_projects()
        self.sel = []
        
        self.vs.display = False
        self.fsb.display = False
        self.fsb.border_title = 'Filters'
        
        table = self.plist
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("T", "Name")
        table.show_header = False
        self.print_projects_list(keep_cursor=False)
        table.focus()
        
        

    def action_search(self):
        self.search.focus()
    

    def action_expand(self, toggle=True, count=-1):
        vs = self.vs
        expand = self.query_one(Markdown)
        
        if vs.display and toggle :
            vs.display = False
        else :
            if count==-1 :
                self.expanded, p = self.get_selected_project()
            else :
                self.expanded = count
                p = self.projs.projs_pd.iloc[self.expanded]

            expand.update(p['md'])
            
            vs.display = True

    
    def get_selected_project(self):
        if self.vs.display :
            c = self.expanded
        elif len(self.sel)>0 :
            c = self.sel[self.plist.cursor_row]
        else :
            #to avoid error, not the expected behavior
            c = 0
            
            
        p = self.projs.projs_pd.iloc[c]
        return c, p
        
    
    def update_selection(self):
        self.sel = self.projs.search_projects(self.search.value)
        
        new_sel = []
        for c in self.sel :
            p = self.projs.projs_pd.iloc[c]
            pstate = p['state'].casefold()
            if pstate == 'active' :
                if 'active' in self.sl_filters.selected :
                    new_sel.append(c)
            elif pstate == 'published':
                if 'published' in self.sl_filters.selected :
                    new_sel.append(c)
            else :
                if 'other' in self.sl_filters.selected :
                    new_sel.append(c)
            
        self.sel = new_sel

    def action_open(self):
        c, p = self.get_selected_project()
        
        subprocess.run(['xdg-open', os.path.join(self.projs.path, p['path'])],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


    def action_edit_project_file(self):
        c, p = self.get_selected_project()
        subprocess.run(['xdg-open', os.path.join(self.projs.path, p['path'], 'project.md')],
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
    
    
    def action_update_selected(self):
        # MAYBE MOVE TO THE PROJECT CLASS
        
        c, psel = self.get_selected_project()
        
        p = self.projs.read_proj_file(os.path.join(self.projs.path, psel['path']))
        
        for field, values in self.projs.projs_pd.iteritems():
            self.projs.projs_pd.at[c, field] = p.get(field, "")

        self.projs.projs_pd.at[c, 'count'] = c
        
        self.projs.write_projects()
        
        row = self.plist.cursor_row
        self.print_projects_list(keep_cursor=True)
        self.plist.move_cursor(row=row)
        
        if self.vs.display :
            self.action_expand(toggle=False)
        

    def action_full_update(self):
        #li = LoadingIndicator(id="update")
        #await self.mount(li)
        
        self.projs.read_projects()
        self.print_projects_list()
        
        #time.sleep(5)
        #li.remove()

        
    def clear_search(self):
        self.search.action_end()
        self.search.action_delete_left_all()

            
    def action_escape(self):
        if self.vs.display :
             self.vs.display = False
        elif len(self.search.value) > 0 :
            self.clear_search()
            self.print_projects_list()        
    
    def action_show_filters(self):  
        if not self.vs.display :
            self.fsb.display = not self.fsb.display
            if self.fsb.display :
                self.sl_filters.focus()
    
    
    def on_input_submitted(self):
        self.print_projects_list()
        self.plist.focus()
        
    
    def on_markdown_link_clicked(self, message: Markdown.LinkClicked):
        m = unquote(message.href)
        if m.isdigit() :
            c = int(m)
            self.action_expand(toggle=False, count=c)
        else :
            p = self.projs.projs_pd.iloc[self.expanded]
            doc_path = os.path.join(self.projs.path, p['path'], m)
            if os.path.isfile(doc_path) :
                to_open = doc_path
            else :
                to_open = m

            subprocess.run(['xdg-open', to_open],
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
                               
                               
    def on_checkbox_changed(self, message: Checkbox.Changed):
        self.print_projects_list()
        
#    def on_selectionlist_selectedchanged(self, message: SelectionList.SelectedChanged):
#        self.pretty.update(self.sl_filters.selected)
    
    @on(SelectionList.SelectedChanged)
    def update_selected_view(self) -> None:
        self.print_projects_list()
        

if __name__ == "__main__":
    app = MyApp()
    app.run()


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
from textual.app import App, ComposeResult, InvalidThemeError
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

                    m = re.search(r"^\*\*.*:\*\*",line)
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
                    
        pdf = pd.DataFrame(projs)
        pdf.fillna('', inplace=True)
        
        self.projs_pd = pdf
        
        self.sort_projects()
        self.write_projects()

        return projs
        
    
    def sort_projects (self):
        self.projs_pd.sort_values('last_mod', inplace=True)
        self.projs_pd.reset_index(drop=True, inplace=True)
    
    
    def update_single_project (self, c):
        path = self.projs_pd.at[c, 'path']
        p = self.read_proj_file(os.path.join(self.path, path))
        
        for field, values in self.projs_pd.items():
            self.projs_pd.at[c, field] = p.get(field, "")

        self.sort_projects()
        self.write_projects()
        
        c = np.flatnonzero(self.projs_pd['path'] == path)[0]
        return c
        
        
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
        Binding(key="s", action="search", description="Search", show=False),
        Binding(key="space", action="expand", description="Expand"),
        Binding(key="o", action="open", description="Open"),
        Binding(key="e", action="edit_project_file", description="Edit"),
        Binding(key="u", action="update_selected", description="Update"),
        Binding(key="ctrl+u", action="full_update", description="Full update"),
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
                self.sl_filters = SelectionList[str]()
                yield self.sl_filters
                
            self.vs = VerticalScroll(id="vs")
            with self.vs :
                yield Markdown(id="expand", open_links=False)

        yield Footer()
        
        
    def print_projects_list(self, keep_cursor=True, cursor=-1):
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
        
        if keep_cursor and cursor_count in self.sel :
            row = self.sel.index(cursor_count)
        elif cursor in self.sel :
            row = self.sel.index(cursor)
        else :
            row=len(self.sel)-1
            
        self.plist.move_cursor(row=row)
    
    def get_options(self, filters_str):
        options = []
        filters_str += ',Other'
        for o in filters_str.split(',') :
            o = o.strip()
            options.append((o, o.casefold(), len(options)==0))

        self.filter_options = options
    
    def on_mount(self) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(os.path.dirname(__file__), 'projects.conf'))
        
        try :
            self.theme = self.config['DEFAULT']['theme']
        except InvalidThemeError :
            self.notify("'{}' is not a valid theme".format(self.config['DEFAULT']['theme']),
                        title="InvalidThemeError", severity="warning")
        
        self.get_options(self.config['DEFAULT']['state_filters'])
        self.sl_filters.add_options(self.filter_options)
        
        self.projs = Projects(self.config['DEFAULT']['path'])
        self.projs.load_projects()
        
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
            selected = False
            selectable = True
            for o in self.filter_options[:-1] :
                if selectable and (pstate == o[1]) :
                    selectable = False
                    if o[1] in self.sl_filters.selected :
                        selected = True
            if selectable and 'other' in self.sl_filters.selected :
                selected = True
            
            if selected :
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
    

    def action_update_selected(self):
        c, psel = self.get_selected_project()
        
        c = self.projs.update_single_project(c)
         
        self.print_projects_list(keep_cursor=False, cursor=c)
        
        if self.vs.display :
            self.action_expand(toggle=False, count=c)
        

    def action_full_update(self):
        self.projs.read_projects()
        self.print_projects_list()
        self.notify("{} projects found".format(self.projs.projs_pd.shape[0]),
                    title="Full update successful")

        
    def clear_search(self):
        self.search.action_end()
        self.search.action_delete_left_all()

            
    def action_escape(self):
        if self.vs.display :
            self.vs.display = False
        elif len(self.search.value) > 0 :
            self.clear_search()
            self.print_projects_list()
        
        self.plist.focus()
    
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
            doc_path1 = os.path.join(self.projs.path, p['path'], m)
            doc_path2 = os.path.join(os.path.expanduser(m))
            if os.path.isfile(doc_path1) :
                to_open = doc_path1
            elif os.path.isfile(doc_path2) :
                to_open = doc_path2
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


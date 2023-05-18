# Projects

*Projects* is a simple project manager with a [Textual](https://textual.textualize.io/) interface allowing to list the projects, search in the projects, and manage the to-do list of the projects.

With *Projects*, a project is a directory containing a `project.md` file with a title (header level 1), and a "state" tag and eventually sections named "To do" and "Documents", and other tags and sections. An example is given in `project.md`. 

Once started, this script walks through the specified directory to find the projects and displays them in an interface allowing to:

- `search`: search in the projects titles and keywords.
- `filter` the projects by their state, now `active`, `published` or `other`.
- `expand`: prints the `project.md` file of a project. Documents are shown as clickable links that open the corresponding files.
- `open`: opens the project directory given the project number.
- `todo`: prints all the todo sections.
- `update`: reload the projects, in case projects are added or modified during the execution.


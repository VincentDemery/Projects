# Projects

*Projects* is a simple project manager with a [Textual](https://textual.textualize.io/) interface allowing to list the projects, search in the projects, and manage the to-do list of the projects.

With *Projects*, a project is a directory containing a `project.md` file with a title (header level 1), and a "state" tag and eventually sections named "To do" and "Documents", and other tags and sections. An example is given in `project.md`. 

Once started, this script walks through the specified directory to find the projects and displays them in an interface allowing to:

- Search in the projects titles and keywords.
- Filter the projects by their state, now `active`, `published` or `other`.
- Show the Markdown file `project.md` of a project. Documents are shown as clickable links that open the corresponding files.
- Open the project directory given the project number.
- Prints all the todo sections.
- Update project database, in case projects are added or modified during the execution.

## To do

- Projects list should also be sorted when a single project is updated
- Bindings should be widget dependent

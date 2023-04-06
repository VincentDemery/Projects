# Projects

*Projects* is a simple project manager allowing to list the projects, search in the projects, and manage the to-do list of the projects.

With *Projects*, a project is a directory containing a `project.md` file with a title (header level 1), and eventually sections named "To do" and "Documents", and eventually tags and other sections. An example is given in `project.md`. 

Once started, this script walks through the specified directory to find the projects and then displays a prompt with the following commands:

- `list`: list all the projects, indicating the projects with a todo section. A number is shown before the title to allow expanding or opening the project (see below).
- `search`: search words in the projects. The projects with the words searched for in their title are shown.
- `expand`: prints the `project.md` file of a project indicated by its number.
- `open`: opens the project directory given the project number.
- `doc`: opens a document given the project and document numbers.
- `todo`: prints all the todo sections, with the project titles as headers.
- `update`: reload the projects, in case projects are added or modified during the execution.

## To do

### Simple corrections

- The script uses the *Rich* module to display text, tables and Markdown files. The colors are chosen for a clear terminal, and may not display correctly on a dark terminal. This could be corrected.
- The directory where to look for projects, now `~/Documents/Recherche`. A config file should be used instead.

### Future features

- Use the `status` keyword in the projects files to display them differently, or to list only a part of the projects.
- Search not only in the title but in the whole project file, or maybe through the title and a description section.
- Display warnings for the projects that have an `active` status but have not been modified for a long time.
- Use for instance *Pandas* for a more efficient search.


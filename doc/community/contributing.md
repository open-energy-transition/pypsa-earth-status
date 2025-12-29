# How to Contribute

Contributions are welcome, and they are greatly appreciated!
Every little bit helps, and you always earn credits.

You can contribute on the code side in many ways:

* submit feedback,
* add new features,
* report bugs,
* fix bugs,
* implement a new cluster/cloud computation backend,
* write documentation

## Code

### Linting and pre-commit

For every code contribution you should run [pre-commit](https://pre-commit.com/index.html).
This will lint, format and check your code contributions against our guidelines
(e.g. we use [Black](https://github.com/psf/black) as code style
and aim for [REUSE compliance](https://reuse.software/)):

1. Installation `conda install -c conda-forge pre-commit` or `pip install pre-commit`
2. Usage:
   * To automatically activate `pre-commit` on every `git commit`: Run `pre-commit install`
   * To manually run it: `pre-commit run --all`

## Documentation

### How to docs?

We add the code documentation along the way.
It might seem time-consuming and inefficient, but that's not really true anymore!
Documenting with great tools makes life much easier for YOU and YOUR COLLABORATORS and speeds up the overall process.
Using [MkDocs](https://www.mkdocs.org/) and its plugin
[mkdocstrings](https://mkdocstrings.github.io/) we document in our
code scripts which then will automatically generate the documentation you might see here.

Thank you Eric Holscher & team for your wonderful *Readthedocs* open source project.
You can find an emotional speech by Eric [here](https://www.youtube.com/watch?v=U6ueKExLzSY).

### Structure and Syntax example

The documentation is fully stored in our `doc` folder. Most files are written in Markdown (`.md`), which is very popular and easy to use.

You could differentiate between two elements:

1. Non-automated doc elements. They simply make the text appealing. Example in `installation.md` in our doc folder. To write these requires some knowledge on writing the text which is quite easy to learn having this [cheat sheet](https://www.markdownguide.org/cheat-sheet/) in close reach.
2. Automated doc elements using `mkdocstrings`. What they do is basically to link the code script with the doc texts, for instance, compare the python script [add_electricity.py](https://github.com/pypsa-meets-earth/pypsa-earth/blob/main/scripts/add_electricity.py) with the `api-reference/index.md` documentation. To write these kind of automation, get inspiration from our `api-reference` documentation. Further, to help understanding how things work the official [mkdocstrings documentation](https://mkdocstrings.github.io/) might help too.

We found three important files/file groups for the documentation:

1. `mkdocs.yml`. This is the configuration file for MkDocs and defines the navigation structure.
2. The `.py` script with the actual code documentation (docstrings).

The images for documentation should be placed into [documentation](https://github.com/pypsa-meets-earth/documentation) repository to the folder "doc/img". The content of the folder "documentation/doc/img/" is copied into "pypsa-earth/doc/img/" during building PyPSA-Earth documentation.

Please, if you have problems with the documentation create an issue and let us know

### How to build it locally

To create the documentation locally, you need [mkdocs](https://www.mkdocs.org/). It can be installed using specifications
from `doc/requirements.txt`. First, we recommend creating a fresh conda environment and activate it:

```bash
.../pypsa-earth-status % conda create --name pypsa-earth-docs python
```

```bash
.../pypsa-earth-status % conda activate pypsa-earth-docs
```

Next, install the packages specified in `doc/requirements.txt` using `pip`:

```bash
.../pypsa-earth-status % pip install -r doc/requirements.txt
```

Once installation is completed, the following commands allow you to create the documentation locally:

```bash
.../pypsa-earth-status (pypsa-earth-docs) % cd doc
```

```bash
.../pypsa-earth-status/doc (pypsa-earth-docs) % mkdocs serve
```

This will start a local server, usually at `http://127.0.0.1:8000/`.
VScode provides a so called Liveserver extension such that the html file can be opened locally on your computer.

The documentation is built automatically by the CI for every pull request. The documentation is hosted on [ReadTheDocs](https://pypsa-earth-status.readthedocs.io/en/latest/).

## No-Code

Instead of contributing code there are alternatives to support the PyPSA-Earth-Status goals.
You can fund projects, supervise people, provide reference data and support us with outreach activities or events.
Check out our [website](https://pypsa-meets-earth.github.io) for more details.

## Join us and get involved

Any person/group is welcome to join us. Be it research leader, researcher, undergraduate, or industry professional.
A simple way to explore opportunities for collaboration is to join our meetings. All of them are **OPEN**.

* PyPSA-Earth-Status periodic meeting: Every two weeks on Monday at 16:00 CET/CEST. If interested in joining, we can add you to the calendar invite; just reach out on [Discord](https://discord.gg/AnuJBk23FU) or via email to any of the core developers.
* [List of initiative meetings](https://pypsa-earth.readthedocs.io/en/latest/#get-involved)

* **Discord**
  * Chat with the community, team up on features, exchange with developers, code in voice channels
  * [Discord invitation link](https://discord.gg/AnuJBk23FU)
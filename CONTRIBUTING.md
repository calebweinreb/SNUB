# How to Contribute to SNUB

We welcome contributions to SNUB! These can take the form of bug reports, feature requests, or code contributions, as described below.

## Bug reports and feature requests

Please submit bug reports and feature requests as [GitHub issues](https://github.com/calebweinreb/SNUB/issues/new). When submitting a bug report, please include:

- A clear description of the problem
- Steps to reproduce the problem
- Your operating system and SNUB version

When submitting a feature request, please include:

- A clear description of the feature
- A use case for the feature

## Code contributions

Before diving into code contributions, please get in touch so we can ensure that your work will be useful and well-integrated with the rest of the project. You can reach us by opening a [GitHub issue](https://github.com/calebweinreb/SNUB/issues/new) or by emailing calebsw@gmail.com.

### Setting up a development environment

1. Create a fork of the SNUB repository on GitHub and clone it to your computer.
2. Follow the [installation instructions](https://snub.readthedocs.io/en/latest/install.html) to create a new conda environment.
3. Navigate to the root of the SNUB repository and run `pip install -e .[dev]` to install SNUB in editable mode along with the development dependencies.

### Making changes

1. Create a new branch for your changes.
2. Make sure that the tests pass by running `pytest` in the root of the repository.
3. Format the code by running `black .` in the root of the repository.
4. Push your changes to your fork and open a pull request. The pull request should go from the branch you created to the `main` branch of the SNUB repository. Make sure to include a clear description of your changes, their motivation, and any relevant information about testing the new features.


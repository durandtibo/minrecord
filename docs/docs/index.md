# Home

<p align="center">
    <a href="https://github.com/durandtibo/minrecord/actions/workflows/ci.yaml">
        <img alt="CI" src="https://img.shields.io/github/actions/workflow/status/durandtibo/minrecord/ci.yaml?branch=main&label=CI&logo=github"></a>
    <a href="https://github.com/durandtibo/minrecord/actions/workflows/nightly-package.yaml">
        <img alt="Nightly Package Tests" src="https://img.shields.io/github/actions/workflow/status/durandtibo/minrecord/nightly-package.yaml?label=nightly&logo=github"></a>
    <a href="https://codecov.io/gh/durandtibo/minrecord">
        <img alt="Codecov" src="https://img.shields.io/codecov/c/github/durandtibo/minrecord?logo=codecov"></a>
    <a href="https://durandtibo.github.io/minrecord/">
        <img alt="Documentation (stable)" src="https://img.shields.io/badge/docs-stable-blue?logo=readthedocs&logoColor=white"></a>
    <br/>
    <a href="https://pypi.org/project/minrecord/">
        <img alt="PyPI version" src="https://img.shields.io/pypi/v/minrecord?logo=pypi&logoColor=white"></a>
    <a href="https://pypi.org/project/minrecord/">
        <img alt="Python" src="https://img.shields.io/pypi/pyversions/minrecord?logo=python&logoColor=white"></a>
    <a href="https://opensource.org/licenses/BSD-3-Clause">
        <img alt="BSD-3-Clause" src="https://img.shields.io/pypi/l/minrecord"></a>
    <br/>
    <a href="https://github.com/astral-sh/ruff">
        <img alt="Ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json"></a>
    <a href="https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings">
        <img alt="Doc style: google" src="https://img.shields.io/badge/docstyle-google-3666d6"></a>
    <a href="https://scorecard.dev/viewer/?uri=github.com/durandtibo/minrecord">
        <img alt="OpenSSF Scorecard" src="https://img.shields.io/ossf-scorecard/github.com/durandtibo/minrecord?label=openssf%20scorecard"></a>
    <br/>
    <a href="https://pepy.tech/project/minrecord">
        <img alt="Downloads" src="https://img.shields.io/pepy/dt/minrecord"></a>
    <a href="https://pepy.tech/project/minrecord">
        <img alt="Monthly downloads" src="https://img.shields.io/pepy/dm/minrecord"></a>
    <a href="https://github.com/durandtibo/minrecord/stargazers">
        <img alt="GitHub stars" src="https://img.shields.io/github/stars/durandtibo/minrecord?logo=github"></a>
</p>

## Overview

`minrecord` is a minimalist Python library to record values in a ML workflow.
In particular, it provides functionalities to track the best value, or the most recent values by
storing a limiting number of values.
It is possible to customize the library e.g. it is possible to define a new logic to track the best
value.

### Key Features

- **📊 Track Best Values**: Automatically track the best value seen during training
- **🔄 Recent History**: Store only recent values to minimize memory usage
- **✅ Improvement Detection**: Easily check if your model is still improving
- **🎯 Flexible Comparators**: Define custom logic to determine what "better" means
- **🗂️ Record Manager**: Organize and manage multiple metrics efficiently
- **💾 Serialization**: Save and load record states for checkpointing
- **🚀 Minimal Dependencies**: Lightweight with only essential dependencies

Below is an example to show how to track the best scalar value when the best value is the maximum
value and when the best value is the minimum value.

```pycon

>>> from minrecord import MaxScalarRecord, MinScalarRecord
>>> record_max = MaxScalarRecord("accuracy")
>>> record_max.update([(0, 42), (None, 45), (2, 46)])
>>> record_max.add_value(40)
>>> record_max.get_best_value()
46
>>> record_min = MinScalarRecord("loss")
>>> record_min.update([(0, 42), (None, 45), (2, 46)])
>>> record_min.add_value(50)
>>> record_min.get_best_value()
42

```

## Documentation

- **[Get Started](get_started.md)**: Installation instructions
- **[Quickstart](quickstart.md)**: Quick overview of the main features
- **[Usage Guide](usage_guide.md)**: Detailed patterns and best practices
- **[FAQ](faq.md)**: Frequently asked questions and troubleshooting
- **[Release notes](release_notes.md)**: Changes and breaking changes
- **[API Reference](refs/root.md)**: Detailed API documentation

## API stability

:warning: While `minrecord` is in development stage, no API is guaranteed to be stable from one
release to the next. In fact, it is very likely that the API will change multiple times before a
stable 1.0.0 release. In practice, this means that upgrading `minrecord` to a new version will
possibly break any code that was using the old version of `minrecord`.

## License

`minrecord` is licensed under BSD 3-Clause "New" or "Revised" license available
in [LICENSE](https://github.com/durandtibo/minrecord/blob/main/LICENSE) file.

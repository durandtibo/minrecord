# Get Started

It is highly recommended to install in
a [virtual environment](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)
to keep your system in order.

## Installing with `pip` or `uv pip` (recommended)

The following command installs the latest version of the library:

```shell
# pip
pip install minrecord

# uv
uv pip install minrecord
```

`minrecord` has no optional dependency: only `coola` is installed with it.

## Installing from source

To install `minrecord` from source, you can follow the steps below. First, you will need to
install [`uv`](https://docs.astral.sh/uv/). `uv` is used to manage and install
the dependencies.
If `uv` is already installed on your machine, you can skip this step. You can install `uv` by running:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

You can check the `uv` installation by running the following command:

```shell
uv --version
```

Then, you can clone the git repository:

```shell
git clone git@github.com:durandtibo/minrecord.git
cd minrecord
```

It is recommended to create a Python 3.11+ virtual environment. This step is optional so you
can skip it. You can use `uv` to create a virtual environment:

```shell
make setup-venv
source .venv/bin/activate
```

This example uses `uv` to create a virtual environment, but you can use other tools or
configurations. Then, you should install the required package to use `minrecord` with the following
command:

```shell
inv env.install
```

This command installs all the required packages (and `inv env.update` updates them). Finally, you
can test the installation with the following command:

```shell
inv test.unit --cov
```

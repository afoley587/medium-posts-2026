# medium-posts-2026

This is a collection of my Medium blog posts I have
written in 2026.

## Table Of Contents

<!-- toc -->

- [Posts](#posts)
- [Contributing](#contributing)
  * [ASDF](#asdf)
  * [Pre-commit](#pre-commit)

<!-- tocstop -->

## Posts

1. January, 2026 - OTEL/FastAPI.
   See the
   [FastAPI - OTEL project](./metrics/fastapi-otel/)

## Contributing

### ASDF

This repository is versioned by
[`asdf`](https://asdf-vm.com/guide/getting-started.html).

You can install all `asdf`-versioned binaries via:

```bash
for plugin in $(awk '{ print $1 }' .tool-versions); do asdf plugin add "$plugin"; done
asdf install
asdf reshim
```

### Pre-commit

This repository uses
[pre-commit](https://pre-commit.com/)
to run a bunch of hooks before committing code.
This helps enforce things like code quality, formatting, etc.
before getting to the PR stage.

To install `pre-commmit` hooks:

```bash
pre-commit install
```

Or to run all `pre-commit` hooks:

```bash
pre-commit run --all-files
```

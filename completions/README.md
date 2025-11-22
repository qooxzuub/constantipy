# Shell Completions

This directory contains auto-generated shell completion scripts for `constantipy`.

## Installation

### Bash

Source the script in your `~/.bashrc`:

```bash
source /path/to/constantipy/completions/constantipy.bash
````

### Zsh

Add this directory to your `$fpath` in `~/.zshrc` **before** `compinit` is called:

```zsh
fpath=(/path/to/constantipy/completions $fpath)
autoload -Uz compinit && compinit
```

### Tcsh

Source the script in your `~/.tcshrc` or `~/.cshrc`:

```tcsh
source /path/to/constantipy/completions/constantipy.tcsh
```

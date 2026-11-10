# Tools under other licences

`ecma418_2_worker.py` computes ECMA-418-2 loudness, tonality and roughness with the `sottek-hearing-model` package
(PyPI metadata of version 0.1.14: `AGPL-3.0-only`). Because it imports that package, this one file is offered under
the same licence, not under Apache-2.0. `listener` never imports it: it starts it as a separate process, in its own
Python environment, and reads the JSON it writes.

```sh
python3 -m venv ~/.venvs/listener-ecma
~/.venvs/listener-ecma/bin/pip install sottek-hearing-model==0.1.14 soundfile
export LISTENER_ECMA_PYTHON=~/.venvs/listener-ecma/bin/python
listener measure sounds/ --ecma
```

Without `LISTENER_ECMA_PYTHON` (or `--ecma-python`), the ECMA-418-2 measures are left out and the output says why.
Do not copy code from that package, from SQAT or from deeuu/loudness into `src/`.

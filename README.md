# Tēzaurs.lv export tools

Scripts to prepare various exports from the Tezaurs.lv database.
- TEI export is done according to TEI 5 Chapter 9 "Dictionaries": https://tei-c.org/release/doc/tei-p5-doc/en/html/DI.html
- LMF export is done according to Global Wordnet Asociation XML chapter: https://globalwordnet.github.io/schemas/#xml
- _ispell_ is wordform per line, work in progress
- For more on GF see: https://www.grammaticalframework.org/

For the newest Tēzaurs TEI/LMF/ispell exports, search "Tēzaurs" in [Clarin.lv repository](https://repository.clarin.lv/repository/xmlui/?locale-attribute=lv). For the GF export, see [GF RGL Github, Latvian folder](https://github.com/GrammaticalFramework/gf-rgl/blob/master/src/latvian/)

## Dev Notes

### Install

Requires at least Python 3.14, `psycopg2`, `types-psycopg2` and `regex`.

On OSX, `psycopg2` doesn't install cleanly and requires that `postgresql` is installed via `brew` (not the downloaded .dmg installer) and the following

```
export PATH=$PATH:/Library/PostgreSQL/11/bin/
pip3 install psycopg2
```

On Linux, if the system python is different, 3.14 can be installed with the help of `pyenv`. If installing `psycopg2` via `pip`, then use `psycopg2-binary`. If using PyCharm, don't forget to check that repository root (`TezaursExports`) is the working directory, when running any of the scripts. If PyCharm style folder `.venv` under repository root contains the appropriate Python enviroment, then any invocation examples given in `.bat` files become usable in shell by appending `/.venv/bin/` in front, e.g, `./.venv/bin/python -m lv.ailab.tezaurs.exports.lmf.do_lmf_wordnet_export tezaurs_2026_02`.

For DB setup, see notes in [`setting_up_local_db.md`](./setting_up_local_db.md) (Latvian).


### ILI <-> PWN 3.0 mapping

To obtain correct LMF ili values, `config` folder must contain mapping file `ili-map-pwn30.tab` from https://github.com/globalwordnet/cili

### Validation

See notes in file [`xml-pub-notes.md`](./xml-pub-notes.md) (Latvian).


## Acknowledgements

The work on porting Tezaurs.lv to a wide-coverage computational GF lexicon for Latvian was funded by the Latvian Council of Science under the grant agreement lzp-2022/1-0443 ([Advancing Latvian Computational Lexical Resources for Natural Language Understanding and Generation](https://wordnet.ailab.lv/project2)).

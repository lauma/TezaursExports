# Lokālās DB uztaisīšana TEI un pārējam eksportam.

## Windows 11.

1. Uz sistēmas jābūt uzinstalētam PostgreSQL no https://www.postgresql.org/download/windows/ un `PATH` mainīgajam jāsatur norāde uz Postgresa bin mapi, piemēram, `C:\Program Files\PostgreSQL\16\bin`
2. Dabū DB dampu, piemēram, `tezaurs_2024_01-public.pgsql.gz` un atarhivē, t.i., `tezaurs_2024_01-public.pgsql`.
3. Uztaisa atbilstošo datubāzi, piemēram, ar pgAdmin `tezaurs_2024_01`.
4. Komandrindā palaiž komandu pēc formulas `psql -h hostname -U username -L logfile.log -f dumpfile.pgsql -d premade_database`, piemēram, `psql -h localhost -U postgres -L psql.log -f tezaurs_2024_01-public.pgsql -d tezaurs_2024_01`
5. Ja viss ir saninstalēts ar noklusējuma parametriem, tad `db_config.py` norādāmie parametri ir šādi
	* `"host": "localhost",`
	* `"port":     5432,`
	* `dbname` - kādu no 3. punktā uztaisīja, bet šo var norādīt arī kā eksporta skripta izsaukuma parametru
    * `"schema":   "dict",`
    * `"user":     "postgres",`
    * `password` - kāda nu lietotājam `postgres` instalējot ir uzstādīta
    
    
## DBeaver

- Uztaisa DB
- Uz DB ar otro peles taustiņu: _Tools/Execute script_ un norāda attiecīgo failu.

## Linux

Priekš Linux, lai pa tiešo importētu ar `psql` ir jāsakonfigurē failos `/etc/postgresql/??/main/pg_ident.conf` un `/etc/postgresql/??/main/pg_hba.conf` mapping starp sistēmas lietotāju un postgress, un tad ir jāraksta `psql -h localhost -p 5432 -U postgres teztest < tezaurs_2026_02-public.pgsql`.




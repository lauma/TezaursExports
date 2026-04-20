# Vispārējais process

1. Dabūt no pareizos DB dumpus, kuros ir arī paslēptie piemēri.
2. Uztaisīt eksportus visām vārdnīcām
	- Tēzauram ir TEI un vārdformu TEI, LMF un ispell, kā arī Clarin.lv publicē pašu DB dump
	- LTG ir TEI un vārdformu TEI, kā arī Clarin.lv publicē pašu DB dump
	- MLVV ir TEI
	- LLVV ir TEI
3. Salikt katru jauno vārdnīcu Clarin.lv, pārbaudot un nomainot šķirkļu skaitu veidlapā. Tēzauram jāpārlasa apraksts un jāatjaunina šķirkļu un avotu skaits aprakstā.
4. Atgādināt nomainīt saites, kad iesniegumi Clarin.lv ir apstiprināti.


# TEI validācija

Lai validētu, nepieciešams komandrindas rīks `xmllint` vai `xmlstarlet` (Windows darbināmi ar WSL) un shēmas, kas glabājas šajā repozitorijā mapē `Shemas`. To oriģinālais avots ir https://www.tei-c.org/guidelines/customization/, sadaļa _All_.

DTD specificē mazāk prasību, XSD prasa arī noteiktiem laukiem, piemēram, `sortKey` atbilst noteiktām regulārajām izteiksmēm, taču DTD kļūdu paziņojumi reizēm ir vienkāršāki (izņemot elementu `body`).

Vārdnīcu pamata TEI bez vārdformu eksporta failu validē ar komandām:
`xmllint --dtdvalid schemas/tei_all.dtd vardnica_????_?_tei.xml --noout --huge` (veiksmes gadījumā parādās paziņojums `vardnica_????_?_tei.xml validates`)
`xmllint --schema schemas/tei_all.dxsd vardnica_????_?_tei.xml --noout --huge` (veiksmes gadījumā izvads ir tukšs)
vai
`xmlstarlet val --err --dtd schemas/tei_all.dtd vardnica_????_?_tei.xml` (veiksmes gadījumā pārādās paziņojums `vardnica_????_?_tei.xml - valid`)
`xmlstarlet val --err --xsd schemas/tei_all.xsd vardnica_????_?_tei.xml` (veiksmes gadījumā pārādās paziņojums `vardnica_????_?_tei.xml - valid`, taču dokumentācijā ir norāde, ka šajā rīkā XSD validācija ir realizēta nepilnīgi)

Tēzaura vārdformu eksports šobrīd ir par lielu validēšanai ar jebkuru no šiem rīkiem (ar DTD pietrūkst atmiņas, ar XSD `xmllint` pietrūkst atmiņas, bet `xmllstarlet` šī funkcija nāk ar daļējas realizācijas brīdinājumu.). Teorētiski `xmllint --stream` varētu palīdzēt, bet, šķiet, ka 2026-04 tas ar _stream_ karodziņu nevalidē pēc shēmas, tikai pēc iekšēji norādīta DTD vai vispār nē.


Nelielus TEI failus vai to fragmentus tiešsaistē var validēt arī https://teibyexample.org/exist/tools/TBEvalidator.htm
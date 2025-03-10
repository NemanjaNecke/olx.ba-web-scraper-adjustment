## Objašnjenje Izmena u Kod-u
**Razlog**
> Bilo mi je potrebno da proverim cene knjiga na olx za tetkin oglas :) Imam skriptu koja kupi imena knjiga sa fotografija `https://github.com/NemanjaNecke/Find-image-automation`

**Poboljšanja komandne linije:**

- Integracija Argparse modula:

>Skripta sada koristi argparse modul za prihvatanje argumenata: ulazni fajl (koji sadrži listu stavki, po jedna stavka po liniji), izlazni fajl u kojem će biti sačuvani rezultati (u CSV formatu) i opcioni argument za maksimalan broj stranica koje će se pretraživati po stavci.

**Uputstva:**

Ovo omogućava korisnicima da pokrenu skriptu sa jasnim uputstvima, na primer:
```
python scraping.py --input items.txt --output results.csv --max_pages 10
```

## Obrada ulaznog fajla:

**Ekstrakcija naziva stavki:**
>Skripta učitava ulazni fajl i izdvaja nazive stavki. Ako linija sadrži dvotačku (npr. "1: Naziv Stavke"), uzima se samo deo posle dvotačke.
Petlja kroz stavke:
Skripta zatim prolazi kroz svaku stavku i koristi njen naziv kao ključnu reč za pretragu na OLX-u.
Scraping i ekstrakcija podataka:

**Kreiranje URL-a za pretragu:**

>Za svaku stavku, kreira se URL pretrage koristeći hardkodovane vrednosti za kategoriju ("Literatura") i podkategoriju ("Knjige").

**Korišćenje Playwright i BeautifulSoup:**

Funkcije za scraping koriste Playwright za učitavanje stranica u headless režimu i BeautifulSoup za parsiranje HTML sadržaja. Na osnovu toga se izdvajaju ID-jevi oglasa, nakon čega se pozivaju OLX API pozivi kako bi se dobili detalji (cena i naslov oglasa).

**Pretraga kroz više stranica:**

Funkcija scrape_all_pages() omogućava pretragu kroz više stranica (do maksimalnog broja stranica koji je definisan kao argument), čime se prikupljaju svi relevantni oglasi.

## Čišćenje podataka i proračun prosečne cene:

**Čišćenje cena:**

Pomoćna funkcija clean_prices() uklanja simbole valute i druge formaterske karaktere iz tekstualnih vrednosti cena, zatim ih konvertuje u numeričke vrednosti.

**Uklanjanje outlier:**

Funkcije `quantile_bounds_cleaning()` i `remove_z_score_outliers()` uklanjaju ekstremne vrednosti (outlier) pre proračuna prosečne cene.

**Proračun prosečne cene:**

Za svaku stavku, nakon čišćenja podataka, proračunava se prosečna cena na osnovu preuzetih cena.

## Integracija OLX autentifikacije:

**Prijava na OLX:**

Funkcije za autentifikaciju na OLX putem API-ja koristeći hardkodovane kredencijale. Na ovaj način se dobija pristupni token koji je potreban za sve naredne API pozive prilikom prikupljanja podataka.

## Izlaz rezultata:

**Generisanje CSV fajla:**

Nakon obrade svih stavki, rezultati (naziv stavke, prosečna cena, ukupan broj pronađenih oglasa, kao i informacije o kategoriji) se čuvaju u CSV fajlu.

## Ažuriranje dokumentacije:

**README.md:**

README fajl u repozitorijumu je ažuriran kako bi objašnjavao novu funkcionalnost, nove parametre komandne linije, kao i uputstva za pokretanje skripte.

Ovim izmenama se obezbeđuje da alat ne samo da prikuplja oglase i cene sa OLX-a, već i računa prosečne cene za svaku stavku na osnovu ulaznog fajla. 

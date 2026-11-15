# ShelfWatch

![ShelfWatch-Logo](custom_components/shelfwatch/brand/logo.png)

**Deutsch** | [English](README.en.md)

ShelfWatch ist eine Home-Assistant-Integration für Bibliothekskonten auf Basis
von Koha oder LMSCloud. Sie überwacht ausgeliehene Medien, Rückgabefristen und
überfällige Ausleihen direkt aus dem OPAC-Bibliothekskonto.

Damit eignet sich ShelfWatch besonders für Familien mit mehreren
Bibliotheksausweisen, Stadtbibliotheken und Büchereien, die Koha oder LMSCloud
als Online-Katalog einsetzen.

Die mindestens unterstützte Home-Assistant-Version ist `2026.1.2`.

## Funktionen

- Einrichtung vollständig über die Home-Assistant-Oberfläche
- ein Bibliothekskonto pro Konfigurationseintrag
- mehrere Personen oder Bibliotheksausweise parallel
- Anmeldung am Koha-/LMSCloud-OPAC und Auslesen der HTML-Kontoseite
- Anzahl der aktuell ausgeliehenen Medien
- nächster Rückgabetermin und verbleibende Tage
- Zähler für heute fällige, bald fällige und überfällige Medien
- vollständige Medienliste in den Sensorattributen
- einstellbarer Zeitraum für „bald fällig“
- einstellbares Aktualisierungsintervall
- optionale Home-Assistant-Aufgabenliste für den Lesestatus
- optionale Sensoren für gelesene und noch offene Medien
- deutsche und englische Übersetzungen
- erneute Anmeldung bei ungültig gewordenen Zugangsdaten

## Installation mit HACS

[![ShelfWatch in HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=twuertele&repository=ShelfWatch&category=integration)

Solange ShelfWatch noch nicht in der Standardauswahl von HACS enthalten ist:

1. HACS öffnen.
2. Das Drei-Punkte-Menü öffnen.
3. **Benutzerdefinierte Repositories** auswählen.
4. `https://github.com/twuertele/ShelfWatch` eintragen.
5. Als Kategorie **Integration** auswählen.
6. **ShelfWatch** herunterladen.
7. Home Assistant neu starten.

## Einrichtung

Nach dem Neustart:

1. **Einstellungen** -> **Geräte & Dienste** öffnen.
2. **Integration hinzufügen** auswählen.
3. Nach **ShelfWatch** suchen.
4. Folgende Daten eingeben:
   - frei wählbarer Kontoname
   - OPAC-Basis-URL
   - Benutzernummer
   - Passwort
5. Die Einrichtung bestätigen.

Der Kontoname beschreibt die Person oder den Bibliotheksausweis in Home
Assistant, zum Beispiel den Namen eines Kindes.

Beispiel für eine OPAC-Basis-URL:

```text
https://sb-muehlacker.lmscloud.net
```

ShelfWatch prüft die Anmeldung, bevor das Konto gespeichert wird.

## Sensoren

ShelfWatch erstellt pro Bibliothekskonto Sensoren für:

- ausgeliehene Medien
- nächsten Rückgabetermin
- Tage bis zur nächsten Rückgabe
- überfällige Medien
- heute fällige Medien
- bald fällige Medien
- Status
- Medienliste
- letzte Aktualisierung

Die Medienliste wird als Attribut des Bücher-Sensors sowie gruppiert in den
Fälligkeitssensoren bereitgestellt. So bleiben die Sensorzustände kompakt,
während Dashboards und Automationen weiterhin auf Titel, Autor, Medienart,
Signatur und Rückgabedatum zugreifen können.

Beispiel:

```yaml
status: "due_soon"
next_due_date: "2026-06-10"
next_due_in_days: 5
overdue_count: 0
due_today_count: 0
due_soon_count: 2
last_update: "2026-06-05T06:30:00Z"
books:
  - title: "Beispielbuch"
    author: "Beispielautor"
    due_text: "10.06.2026"
    due_iso: "2026-06-10T23:59:00Z"
    due_in_days: 5
    media_type: "Buch"
    call_no: "A 123"
    renewal_info: "Verlängerbar"
```

Mögliche Statuswerte:

- `empty`: keine aktuellen Ausleihen
- `ok`: Ausleihen vorhanden, aber noch nicht bald fällig
- `due_soon`: mindestens ein Medium ist innerhalb des eingestellten Zeitraums fällig
- `due_today`: mindestens ein Medium ist heute fällig
- `overdue`: mindestens ein Medium ist überfällig

## Dashboard-Beispiel

ShelfWatch lässt sich vollständig mit den in Home Assistant enthaltenen
Karten darstellen. Es werden keine zusätzlichen Lovelace-Karten benötigt.

![ShelfWatch-Dashboard mit Fälligkeiten und Medienliste](images/dashboard-overview.jpg)

Für eine kompakte Übersicht eignen sich Kachel-Karten mit folgenden
ShelfWatch-Sensoren:

- ausgeliehene Medien
- nächste Rückgabe
- Tage bis zur nächsten Rückgabe
- heute fällig
- bald fällig
- überfällig

Die genaue Entity-ID hängt vom gewählten Kontonamen und teilweise von der
Sprache ab. Sie ist auf der ShelfWatch-Geräteseite unter **Einstellungen** ->
**Geräte & Dienste** -> **ShelfWatch** zu finden. Der Medien-Sensor kann zum
Beispiel `sensor.mein_konto_medien` oder `sensor.my_account_books` heißen.

### Ausgeliehene Medien als Liste

Die vollständigen Ausleihdaten liegen im Attribut `books` des Medien-Sensors.
Eine Markdown-Karte kann daraus automatisch eine übersichtliche Liste
erzeugen:

![Liste der ausgeliehenen Medien im Dashboard](images/dashboard-media-list.jpg)

So wird die Liste eingerichtet:

1. Das gewünschte Dashboard öffnen.
2. **Dashboard bearbeiten** und anschließend **Karte hinzufügen** wählen.
3. Eine **Markdown-Karte** hinzufügen.
4. Den folgenden Inhalt einfügen.
5. `sensor.mein_konto_medien` durch die eigene Entity-ID des
   ShelfWatch-Medien-Sensors ersetzen.
6. Die Karte speichern.

```jinja
{% set books = state_attr('sensor.mein_konto_medien', 'books') or [] %}
{% if books | count == 0 %}
Keine ausgeliehenen Medien gefunden.
{% else %}
{% for book in books %}
### {{ book.title }}
{% if book.author %}{{ book.author }}
{% endif %}

**Fällig:** {% if book.due_in_days is number %}
{% if book.due_in_days < 0 %}
seit {{ 0 - book.due_in_days }} Tagen überfällig
{% elif book.due_in_days == 0 %}
heute
{% elif book.due_in_days == 1 %}
morgen
{% else %}
in {{ book.due_in_days }} Tagen
{% endif %}
{% else %}
{{ book.due_text or '-' }}
{% endif %}

{% if book.media_type or book.call_no %}
{{ book.media_type or 'Medium' }}{% if book.call_no %} · {{ book.call_no }}{% endif %}
{% endif %}
{% if book.renewal_info %}
{{ book.renewal_info }}
{% endif %}
{% if not loop.last %}
---
{% endif %}
{% endfor %}
{% endif %}
```

Die Karte aktualisiert sich zusammen mit den ShelfWatch-Sensoren automatisch.
Neue Ausleihen erscheinen ohne weitere Dashboard-Anpassung, zurückgegebene
Medien verschwinden beim nächsten erfolgreichen Abruf.

## Optionen

Unter **Einstellungen** -> **Geräte & Dienste** -> **ShelfWatch** ->
**Konfigurieren** stehen kontospezifische Einstellungen zur Verfügung:

- Zeitraum für „bald fällig“, standardmäßig `7` Tage
- Aktualisierungsintervall von `1` bis `24` Stunden, standardmäßig `24`
- optionale Aufgabenliste für den Lesestatus
- zurückgegebene Medien automatisch als erledigt markieren
- erledigte Einträge als Lesehistorie behalten

ShelfWatch aktualisiert das Konto außerdem nach dem Start und kurz nach dem
lokalen Tageswechsel. Relative Fälligkeitswerte werden zum Tageswechsel neu
berechnet.

## Warum HTML statt Koha-API?

ShelfWatch verwendet bewusst die Anmeldung und HTML-Seite des
Bibliothekskontos statt der Koha-REST-API.

Beim getesteten LMSCloud-OPAC ist die REST-API nicht für eine einfache
Anmeldung normaler Bibliotheksnutzer geeignet: Basic Auth ist deaktiviert und
die benötigten Ausleihdaten werden auf der Kontoseite nicht über öffentliche
Browser-API-Aufrufe geladen.

Der Anmeldevorgang lädt zunächst das OPAC-Formular, übernimmt versteckte Felder
wie das CSRF-Token und verwendet anschließend die vom Formular vorgegebenen
Feldnamen. Koha- und LMSCloud-Installationen können sich je nach Version,
Stadt, Betreiber oder individuellem Theme unterscheiden; bei einem anderen
OPAC kann daher eine kleine Kompatibilitätsanpassung erforderlich sein.

ShelfWatch meldet sich deshalb wie ein Browser am OPAC an und liest die
Ausleihtabelle aus der HTML-Seite.

## Datenschutz

Die Zugangsdaten werden wie bei anderen UI-basierten Integrationen im
Konfigurationseintrag von Home Assistant gespeichert.

ShelfWatch übermittelt weder Zugangsdaten noch Ausleihdaten an einen externen
Dienst. Die Daten werden direkt vom eingestellten Bibliotheks-OPAC abgerufen.

## Bekannte Einschränkungen

- Die automatische Verlängerung von Medien ist noch nicht implementiert.
- Das Auslesen hängt von der HTML-Struktur des Koha-/LMSCloud-OPAC ab.
- Abweichende Koha-Themes oder angepasste Kontoseiten können Anpassungen am
  Parser erfordern.
- Die ausführliche Medienliste ist aktuell vor allem über Sensorattribute und
  Dashboards zugänglich.

## Unterstützte HTML-Struktur

ShelfWatch erwartet derzeit unter anderem:

- Ausleihtabelle: `#checkoutst tbody`
- Titel: `td.title .biblio-title`
- Autor: `td.author`
- Rückgabedatum: `td.date_due`
- maschinenlesbares Datum: `td.date_due[data-order]`
- optionale Medienart: `td.itype`
- optionale Signatur: `td.call_no`
- optionale Verlängerungsinformationen: `td.renew`

## Geplante Funktionen

- bessere Detailansicht der ausgeliehenen Medien außerhalb von Dashboards
- Prüfung einer Kalenderentität für Rückgabetermine
- stabilere Zuordnung über OPAC-Medienkennungen
- Wunschlisten-Unterstützung
- automatische Verlängerung

## Probleme und Unterstützung

Fehlerberichte und Vorschläge können über
[GitHub Issues](https://github.com/twuertele/ShelfWatch/issues) eingereicht
werden. Bitte dabei die verwendete Home-Assistant-Version, die ShelfWatch-
Version und den eingesetzten Koha-/LMSCloud-OPAC angeben. Zugangsdaten gehören
nicht in einen Fehlerbericht.

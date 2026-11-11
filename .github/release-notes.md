## PieperMonitor v0.11.0

### Eén bron voor alles
- De integratie haalt meldingen nu op uit de PieperMonitor-feed, dezelfde data en dezelfde interpretatie als [piepermonitor.nl](https://www.piepermonitor.nl) en de app. Een verbetering aan de bron werkt daardoor meteen door in Home Assistant.
- Voertuignamen, capcodenamen, prioriteit en regio komen kant en klaar uit de feed. De integratie zoekt zelf geen voertuignamen meer op als je de nieuwe bron gebruikt.

### Voor bestaande gebruikers
- Bij het updaten schakelt de integratie vanzelf over naar de nieuwe bron. Terug kan onder *Configureren* → **Bron van meldingen** → *Legacy*. Die optie blijft nog een paar versies bestaan.
- Domein, entiteiten, events, historie, automatiseringen en de dashboardkaart blijven werken.
- Eenmalig kunnen recente meldingen dubbel in de lijst staan: één keer uit de oude en één keer uit de nieuwe bron. Dat verdwijnt vanzelf zodra er nieuwere meldingen zijn.
- Bij ambulance en politie ontbreken huisnummers en de letters van de postcode in de tekst. Dat is bewust, zoals op de website.

### Privacy
- De integratie genereert een willekeurig installatie-id (geen persoonsgegevens) en vraagt daarmee een toegangstoken aan. Dat is nodig om de feed te beschermen tegen misbruik.

### Verbeteringen
- Ambulancemeldingen met prioriteit A0 worden nu altijd als ambulance getoond, ook in de oude bron, met prioriteit 1 en zonder nepvoertuig.

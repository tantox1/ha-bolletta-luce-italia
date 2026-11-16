# Bolletta Luce Italia (fork con bolletta bimestrale)

Integrazione personalizzata per Home Assistant che stima e archivia la bolletta elettrica italiana partendo dai consumi mensili F1, F2 e F3, con supporto alla **bolletta mensile e bimestrale**, previsione a fine periodo e una dashboard pronta con grafici.

> Questo repository è un fork di [atcodrinky/ha-bolletta-luce-italia](https://github.com/atcodrinky/ha-bolletta-luce-italia), di cui mantiene il motore di calcolo, la configurazione guidata e la licenza MIT. Le differenze sono elencate in [Modifiche rispetto all'originale](#modifiche-rispetto-alloriginale).

La configurazione guidata è suddivisa in cinque pagine e l'integrazione può essere verificata in parallelo ai sensori template esistenti.

[![Apri nel Marketplace di Home Assistant](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=tantox1&repository=ha-bolletta-luce-italia&category=integration)

## Modifiche rispetto all'originale

Basato sulla versione 0.3.0 dell'originale. Tutto ciò che c'era continua a funzionare allo stesso modo: chi ha una bolletta mensile non deve cambiare nulla e configurazione, entità e archivio esistenti vengono mantenuti.

**Fatturazione bimestrale**

- Nuova opzione *Periodicità della bolletta* (mensile o bimestrale) con la sequenza dei bimestri: gen–feb, mar–apr, … oppure dic–gen, feb–mar, ….
- Nuovi sensori `Stima bolletta del periodo`, `Energia fatturabile del periodo`, `Proiezione bolletta del mese` e `Proiezione bolletta del periodo`.
- Nuovo sensore `Storico periodi` con stime e bollette reali raggruppate per periodo, pensato per i grafici.
- Nuovo servizio `registra_stima_mese` per inserire la stima di un mese non archiviato e completare un bimestre.

**Cambio di contratto senza perdere lo storico**

- Campo *Decorrenza* (AAAA-MM) per indicare da quando vale una nuova periodicità, anche futura.
- Calendario delle periodicità salvato nello storage: ogni mese e ogni bolletta vengono letti con la periodicità valida allora e un bimestre non attraversa mai un cambio di contratto.

**Correzioni**

- `Scostamento ultima bolletta` confronta la bolletta con la somma delle stime di tutti i mesi che copre; nell'originale una bolletta bimestrale veniva confrontata con la stima di un solo mese, con uno scostamento circa doppio.
- Lo snapshot del mese in corso è salvato nello storage: un riavvio a cavallo di fine mese non perde più la stima del mese chiuso.
- L'archivio mensile non duplica più lo storico delle bollette e gli archivi esposti come attributi sono esclusi dal recorder.
- Il coordinatore riceve esplicitamente la voce di configurazione e la versione del dispositivo segue quella dell'integrazione.

**Dashboard**

- Esempio pronto in [`examples/dashboard-bolletta-luce.yaml`](examples/dashboard-bolletta-luce.yaml); vedi [Dashboard](#dashboard).

Il dettaglio versione per versione è nel [registro delle modifiche](CHANGELOG.md).

## Funzioni disponibili

- tariffa indicizzata al PUN oppure prezzo fisso;
- tre fasce F1, F2 e F3;
- fattore manuale di correzione dei consumi;
- perdite di rete e spread separati per fascia;
- CdispD, distribuzione, oneri di sistema, quote fisse e quota potenza;
- accise, IVA e dieci rate configurabili del canone RAI;
- stima totale, dettaglio delle singole voci e costo medio effettivo;
- archivio mensile nello storage interno di Home Assistant;
- inserimento manuale e importazione multipla delle bollette reali, con consumi per fascia e dettaglio economico;
- ripartizione opzionale della ricarica auto fra rete e fotovoltaico;
- attribuzione opzionale e proporzionale delle quote fisse all'auto;
- configurazione guidata in cinque pagine con contatore e ritorno al passaggio precedente;
- modifica di tutte le opzioni senza riavviare Home Assistant;
- bolletta mensile o bimestrale, con stima, proiezione e scostamento calcolati sull'intero periodo.

## Sensori da conservare

L'integrazione usa come sorgenti esterne e non modifica i sensori storici:

- sensor.energia_acquistata_fasce_f1
- sensor.energia_acquistata_fasce_f2
- sensor.energia_acquistata_fasce_f3

Questi sensori, il relativo misuratore di utilità e lo storico della Dashboard Energia devono rimanere attivi. Gli helper usati per i vecchi calcoli possono restare durante il confronto e possono essere eliminati manualmente in seguito.

## Installazione manuale

1. Copiare la cartella custom_components/bolletta_luce_italia nella cartella custom_components della propria installazione Home Assistant.
2. Riavviare Home Assistant soltanto per il primo caricamento del codice.
3. Aprire Impostazioni, Dispositivi e servizi, Aggiungi integrazione.
4. Cercare Bolletta Luce Italia.

È possibile aggiungere questo repository anche come repository personalizzato di tipo Integrazione in HACS: `https://github.com/tantox1/ha-bolletta-luce-italia`.

Chi usava l'originale può passare a questo fork senza perdere nulla: in HACS rimuovi l'integrazione (vengono tolti solo i file), aggiungi questo repository personalizzato, scarica l'ultima versione e riavvia Home Assistant. Configurazione, entità e archivio restano.

## Configurazione consigliata per Octopus

Per il contratto usato durante lo sviluppo:

- modello tariffario: indicizzato;
- sensori energia: i tre sensori storici F1, F2 e F3;
- sensori PUN: sensor.pun_fascia_f1, sensor.pun_fascia_f2 e sensor.pun_fascia_f3;
- fattore perdite di rete: 1,10;
- spread F1, F2 e F3: 0,025718 €/kWh;
- quota fissa vendita: 73,2311 €/anno;
- quota fissa distribuzione: 22,8 €/anno;
- quota potenza: 25,2788 €/kW/anno;
- potenza impegnata: 5,5 kW;
- distribuzione variabile: 0,01352 €/kWh;
- oneri di sistema: 0,031322 €/kWh;
- fattore di correzione consumi: 1,15;
- accisa: 0,0227 €/kWh;
- IVA: 10%;
- canone RAI: 90 €/anno in 10 rate.

Le altre componenti devono essere copiate dalla bolletta o dai valori ARERA applicabili al periodo. Il fattore di correzione può essere modificato in qualsiasi momento dalle opzioni dell'integrazione.

## Calcolo

Per una tariffa indicizzata il prezzo di ogni fascia è:

    prezzo fascia = PUN fascia × fattore perdite + spread fascia

La stima mensile somma:

    materia energia
    + CdispD
    + distribuzione e oneri variabili
    + quote fisse e quota potenza
    + accise
    + IVA
    + canone RAI

I valori sono arrotondati per l'esposizione dei sensori; il calcolo interno usa i valori non arrotondati.

## Ricarica auto opzionale

La funzione è disattivata per impostazione predefinita. Quando viene attivata sono richiesti almeno i kWh mensili della wallbox prelevati dalla rete. I kWh da fotovoltaico sono facoltativi e informativi.

Nel sistema di riferimento si possono usare:

- sensor.wallbox_rete_mese
- sensor.wallbox_fv_mese

Le quote fisse non vengono attribuite all'auto salvo attivazione dell'opzione dedicata.

## Inserimento delle bollette reali

Il servizio bolletta_luce_italia.registra_bolletta accetta:

- entry_id: identificativo della configurazione;
- month: mese nel formato AAAA-MM;
- energy: consumi fatturati in kWh;
- total: totale reale in euro.

Questo consente di inserire anche i consuntivi da gennaio a ottobre senza dipendere dallo storico dei vecchi helper. Un valore già presente per lo stesso mese viene sostituito.

Il servizio bolletta_luce_italia.archivia_mese salva manualmente la fotografia corrente del calcolo. Il passaggio a un nuovo mese archivia inoltre automaticamente l'ultima fotografia mantenuta in memoria.


Per importare più mesi insieme è disponibile il servizio `bolletta_luce_italia.importa_storico`. Ogni voce richiede mese, consumi F1/F2/F3 e totale della bolletta senza RAI. Sono facoltativi periodo, RAI, bonus, totale da pagare, materia energia, trasporto, oneri, accise e IVA.

L'importazione è idempotente: una voce già presente con lo stesso mese viene aggiornata e non duplicata. Per il confronto con la stima viene usato il totale della bolletta più il RAI, senza applicare bonus o crediti; il totale effettivamente pagato rimane disponibile separatamente.

## Bolletta bimestrale

Nella pagina 4 della configurazione scegli la periodicità **Bimestrale** e la sequenza dei bimestri riportata in bolletta:

- gen–feb, mar–apr, mag–giu, lug–ago, set–ott, nov–dic;
- dic–gen, feb–mar, apr–mag, giu–lug, ago–set, ott–nov.

I sensori del mese continuano a funzionare come prima. In più:

- `Stima bolletta del periodo`: mese in corso più i mesi già chiusi del bimestre; gli attributi `period_*` riportano il dettaglio delle voci;
- `Energia fatturabile del periodo`;
- `Proiezione bolletta del periodo`: stima di quanto arriverà in bolletta a fine bimestre, mantenendo il ritmo di consumo del mese corrente;
- `Storico periodi`: elenco per bimestre di stima, bolletta reale e scostamento, utile per i grafici.

Le bollette bimestrali si importano con `importa_storico` come una sola voce: `month` può essere uno qualsiasi dei due mesi e i consumi F1/F2/F3 sono quelli dell'intero bimestre. Se indichi `period_start` e `period_end`, lo scostamento usa esattamente i mesi compresi.

    service: bolletta_luce_italia.importa_storico
    data:
      entry_id: <identificativo>
      invoices:
        - month: "2026-10"
          period_start: "2026-09-01"
          period_end: "2026-10-31"
          energy_f1: 0
          energy_f2: 0
          energy_f3: 0
          energy_bill_total: 0
          rai: 0

Se un mese del bimestre non è stato archiviato (per esempio perché l'integrazione è stata installata dopo), si può inserire la sua stima con `bolletta_luce_italia.registra_stima_mese` (`month`, `estimate`, facoltativo `energy_total`). Finché manca, la stima del periodo comprende solo i mesi disponibili e l'attributo `period_complete` vale `false`.

### Cambio di periodicità con un nuovo contratto

Si può passare da mensile a bimestrale (o viceversa, o cambiare la sequenza dei bimestri) senza perdere lo storico. Nella stessa pagina indica la **decorrenza**, cioè il primo mese del nuovo contratto in formato AAAA-MM; può essere anche un mese futuro. Lasciando il campo vuoto il cambio vale dal mese corrente.

L'integrazione tiene un calendario delle periodicità (attributo `billing_schedule` del sensore `Storico periodi`): ogni mese archiviato e ogni bolletta vengono raggruppati con la periodicità valida in quel momento, e un bimestre non attraversa mai il cambio di contratto. Se la decorrenza cade nel secondo mese di un bimestre, il primo periodo dura un solo mese. Per correggere una decorrenza sbagliata basta salvare di nuovo le opzioni indicando quella giusta.

## Dashboard

Il file [`examples/dashboard-bolletta-luce.yaml`](examples/dashboard-bolletta-luce.yaml) contiene una dashboard completa:

- periodo in corso con stima ad oggi e previsione a fine mese e a fine periodo;
- composizione del periodo per voce di costo e per fascia;
- stime e bollette reali a confronto per periodo, con tabella dello scostamento;
- andamento dell'energia mensile per fascia, della stima giorno per giorno e dei prezzi.

Per usarla: Impostazioni → Dashboard → Aggiungi dashboard → Nuova dashboard da zero, poi ⋮ → Modifica → ⋮ → Editor configurazione YAML e incolla il contenuto. I grafici a colonne e a ciambella richiedono [ApexCharts Card](https://github.com/RomRider/apexcharts-card) da HACS; le altre card sono native. Le entità presumono il nome configurazione predefinito *Bolletta luce*: se ne hai scelto un altro sostituisci il prefisso `sensor.bolletta_luce_`.

## Opzioni e applicazione immediata

Aprire l'integrazione e scegliere Configura. Il pulsante Salva applica i nuovi valori ricaricando soltanto Bolletta Luce Italia: non è necessario riavviare Home Assistant e non occorre eliminare o ricreare la configurazione.

## Limiti attuali

- CdispD e componenti ARERA sono inseriti manualmente.
- L'importazione automatica da fonti ufficiali ARERA sarà aggiunta dopo la validazione dei calcoli della prima versione.
- L'archivio non importa automaticamente lo storico dei vecchi helper; le bollette reali possono essere importate con il servizio dedicato.
- L'integrazione è progettata esclusivamente per forniture elettriche italiane domestiche.

## Versionamento

Il progetto usa il versionamento semantico. Le versioni pubblicate sono identificate da tag nel formato vMAJOR.MINOR.PATCH. Ogni pubblicazione deve aggiornare il [registro delle modifiche](CHANGELOG.md).

## Crediti e licenza

Progetto originale di [atcodrinky](https://github.com/atcodrinky/ha-bolletta-luce-italia). Modifiche del fork di [tantox1](https://github.com/tantox1).

Distribuito con licenza MIT, come l'originale.

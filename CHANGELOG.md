# Registro delle modifiche

Tutte le modifiche rilevanti di Bolletta Luce Italia sono documentate in questo file.

Il progetto usa il versionamento semantico e i tag nel formato `vMAJOR.MINOR.PATCH`.

## [0.4.0] - 2026-11-16

### Aggiunto

- Periodicità della bolletta configurabile, mensile o bimestrale, con scelta della sequenza dei bimestri (gen–feb… oppure dic–gen…).
- Sensori `Stima bolletta del periodo` ed `Energia fatturabile del periodo`, che sommano il mese in corso ai mesi già chiusi del bimestre, con il dettaglio delle voci come attributi.
- Sensori `Proiezione bolletta del mese` e `Proiezione bolletta del periodo`: la parte variabile viene estrapolata al tempo trascorso, quote fisse e canone RAI no.
- Sensore `Storico periodi` con il riepilogo per periodo di stime e bollette reali e lo storico delle stime mensili, pensato per i grafici della dashboard.
- Servizio `bolletta_luce_italia.registra_stima_mese` per completare un bimestre con la stima di un mese non archiviato.

### Modificato

- `Scostamento ultima bolletta` confronta la bolletta con la somma delle stime di tutti i mesi che copre, ricavati da `period_start`/`period_end` oppure dal periodo configurato; gli attributi indicano i mesi usati e quelli mancanti.
- Lo snapshot del mese in corso viene salvato nello storage (al massimo ogni 15 minuti), così un riavvio a cavallo di fine mese non perde la stima del mese chiuso.
- L'archivio mensile conserva soltanto le voci di calcolo, senza copiare lo storico delle bollette.
- Gli archivi esposti come attributi sono esclusi dal recorder.
- Il coordinatore riceve esplicitamente la voce di configurazione e la versione del dispositivo segue quella dell'integrazione.

## [0.3.0] - 2026-11-10

### Aggiunto

- Servizio `bolletta_luce_italia.importa_storico` per inserire o aggiornare più bollette mensili con un'unica chiamata.
- Importazione dei consumi F1, F2 e F3, del periodo di fatturazione e del dettaglio economico facoltativo.
- Sensori per totale confrontabile, totale energia senza RAI, canone RAI, bonus e sconti, totale da pagare e numero di bollette archiviate.
- Archivio delle bollette importate esposto come attributo del relativo sensore.

### Modificato

- L'importazione è idempotente: una bolletta già presente viene aggiornata in base al mese senza creare duplicati.
- Il confronto con la stima usa il totale della bolletta più il canone RAI, mantenendo separati bonus, crediti e importo effettivamente pagato.
- Gli esempi pubblici usano esclusivamente valori neutri e non contengono dati reali.

## [0.2.3] - 2026-11-10

### Corretto

- Estesa la precisione libera a tutti i campi numerici decimali del config flow e delle opzioni, comprese quote annue, coefficienti, potenza impegnata, IVA e canone RAI.
- Conservato il passo intero esclusivamente per il numero delle rate RAI.

## [0.2.2] - 2026-11-10

### Corretto

- Risolto l'errore durante l'apertura della seconda pagina del config flow.
- Sostituito il passo numerico non supportato con la precisione libera prevista da Home Assistant, mantenendo l'inserimento di valori tariffari con più di tre decimali.

## [0.2.1] - 2026-11-10

### Aggiunto

- Icona brand locale a 256×256 pixel e versione ad alta risoluzione a 512×512 pixel per Home Assistant.

### Corretto

- Aumentata a sei decimali la precisione dei campi tariffari espressi in €/kWh: prezzi fissi, spread, distribuzione, oneri di sistema, CdispD e accisa.

## [0.2.0] - 2026-11-10

### Aggiunto

- Configurazione iniziale suddivisa in cinque pagine.
- Contatore della pagina nei titoli del wizard.
- Comando per tornare alla pagina precedente conservando i valori inseriti.
- Options Flow multipagina con applicazione immediata senza riavviare Home Assistant.
- Controllo automatico che impedisce di pubblicare una versione assente dal registro delle modifiche.

### Modificato

- Raggruppati i campi in sorgenti energia, tariffa, rete e quote fisse, imposte e ricarica auto.
- Migliorate le descrizioni italiane dei passaggi.
- La ricarica dell'auto rimane completamente opzionale.

## [0.1.1] - 2026-11-10

### Corretto

- Risolto l'errore `400: Bad Request` del config flow su Home Assistant 2026.11.
- Adeguato il passo minimo dei campi numerici ai requisiti di Home Assistant.

## [0.1.0] - 2026-11-10

### Aggiunto

- Prima versione installabile di Bolletta Luce Italia.
- Calcolo per tariffa indicizzata al PUN o prezzo fisso, con fasce F1, F2 e F3.
- Componenti di rete, oneri, CdispD, quote fisse, accisa, IVA e canone RAI.
- Archivio mensile interno e inserimento manuale delle bollette reali.
- Ripartizione opzionale dei consumi della wallbox tra rete e fotovoltaico.
- Options Flow con ricarica della sola integrazione.

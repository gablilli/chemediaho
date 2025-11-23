# che media ho?

una semplice web app flask self-hostabile via docker per visualizzare la media dei voti di classeviva anche se l'istituto ha disattivato la funzione ufficiale. 
sysregister ui-based.

## ✨ funzionalità

* 📱 **PWA (progressive web app)** - installabile su dispositivi mobili
* 🔄 **supporto offline** - funziona anche senza connessione (con i dati scaricati precedentemente)
* 🎨 **design responsive** - ottimizzato per mobile e desktop
* 📊 **calcolo media** - visualizza automaticamente la media dei voti
* 🎯 **calcolatore obiettivo** - scopri quale voto ti serve per raggiungere la tua media target
* 📈 **grafici interattivi** - visualizza i tuoi progressi nel tempo
* 💾 **esportazione dati** - esporta i tuoi voti in formato CSV
* 🆓 **codice 100% free and opensource con controllo codeql** - così puoi stare tranquillo.

## installazione

### prerequisiti

* python 3.6 o superiore
* un account classeviva attivo

### 1️⃣ clona il repository

```bash
git clone https://github.com/gablilli/chemediaho.git
cd chemediaho
```

### 2️⃣ installa le dipendenze

```bash
pip install -r requirements.txt
```

### 3️⃣ avvia l’app

esegui lo script principale dentro la cartella:

```bash
python app.py
```

poi apri il browser su **[http://localhost:5000](http://localhost:5000)**, inserisci le tue credenziali di classeviva e… buona media! 🧮

## 📱 installazione come PWA

l'app può essere installata sul tuo dispositivo mobile per un'esperienza nativa:

### su android (chrome)
1. apri l'app nel browser
2. tocca il menu (⋮) e seleziona "installa app" o "aggiungi a schermata home"
3. conferma l'installazione

### su ios (safari)
1. apri l'app in safari
2. tocca il pulsante condividi (□↑)
3. scorri e seleziona "aggiungi a home"
4. conferma l'installazione

una volta installata, l'app funzionerà come un'applicazione nativa!


## installazione con docker

### prerequisiti

* docker e docker compose installati
  👉 guida ufficiale: [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)

### crea e avvia il container

dalla cartella del progetto:

```bash
docker compose up -d
```

> nota: i log non sono ancora implementati.

una volta avviato, l’interfaccia web sarà disponibile sulla porta **5000** di tutte le interfacce del computer.

se usi ubuntu o hai **ufw** attivo, abilita la porta:

```bash
sudo ufw allow 5000
```

## configurazione avanzata

### https e sicurezza dei cookie

di default, l'app funziona su http (adatto per uso locale/domestico). se esegui l'app dietro un proxy https o un load balancer, imposta la variabile d'ambiente `HTTPS_ENABLED=true`:

```bash
# in compose.yml, aggiungi:
environment:
  - FLASK_ENV=production
  - HTTPS_ENABLED=true
```

questo abiliterà il flag `Secure` sui cookie di sessione, garantendo che vengano inviati solo su connessioni https.

### chiave segreta e sessioni

l'app genera automaticamente una chiave segreta (`secret_key.txt`) al primo avvio per gestire le sessioni in modo sicuro. questa chiave:
- è salvata in `secret_key.txt` nella directory dell'app con permessi restrittivi (600 - solo proprietario può leggere/scrivere)
- non deve essere committata su git (già esclusa da .gitignore)
- in docker, è persistita tramite volume mount per funzionare anche dopo i restart dei container

#### note di sicurezza

⚠️ **importante per la sicurezza:**
- la chiave è salvata in chiaro sul file system - proteggi l'accesso al file
- le credenziali nel cookie di sessione sono criptate con questa chiave
- per ambienti di produzione, considera l'uso di gestori di segreti esterni (es. Docker secrets, Kubernetes secrets, HashiCorp Vault)
- usa sempre la variabile d'ambiente `SECRET_KEY` in produzione invece del file
- assicurati che il file `secret_key.txt` sia leggibile solo dall'utente che esegue l'app (permessi 600)

esempio per produzione con docker secrets:
```yaml
# compose.yml per produzione
services:
  flask:
    environment:
      - SECRET_KEY_FILE=/run/secrets/flask_secret
    secrets:
      - flask_secret

secrets:
  flask_secret:
    external: true
```

## risoluzione problemi

se qualcosa non funziona, controlla eventuali errori nel terminale e assicurati che l’installazione non abbia restituito messaggi di errore.

--- 

## grazie a

* [classeviva-official-endpoints](https://github.com/Lioydiano/Classeviva-Official-Endpoints)
* sysregister del buon [syswhite.dev](https://github.com/syswhitedev)
* [CVVSimpleAvgrage](https://github.com/LucaCraft89/CVVSimpleAvgrage)


per aver reso possibile tutto questo ❤️

## 🚀 rilasciare una nuova versione

questo repository include un workflow GitHub Actions automatizzato per creare nuove release. il workflow:

* ✏️ aggiorna automaticamente i numeri di versione in `app.py` e `sw.js`
* 📝 genera un changelog dai PR merged con etichette `changelog:feat` e `changelog:fix`
* 🏷️ crea un tag git e una release su GitHub

### come creare una release

1. vai alla pagina [Actions](https://github.com/gablilli/chemediaho/actions/workflows/release.yml) del repository
2. clicca su "Run workflow"
3. inserisci il nuovo numero di versione (es. `1.6.0` o `1.6`)
4. clicca su "Run workflow"

il workflow automaticamente:
- aggiornerà `APP_VERSION` in `app.py`
- aggiornerà `CACHE_NAME` in `sw.js`
- creerà un commit con i cambiamenti
- creerà un tag git `vX.Y.Z`
- genererà una release su GitHub con changelog organizzato in sezioni "Feats" e "Fixes"

### etichettare i PR per il changelog

per includere un PR nel changelog della release, aggiungi una di queste etichette:
* `changelog:feat` - per nuove funzionalità
* `changelog:fix` - per correzioni di bug

i PR senza queste etichette non appariranno nel changelog.


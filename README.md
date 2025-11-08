# che media ho?

una semplice web app flask self-hostabile via docker per visualizzare la media dei voti di classeviva anche se l'istituto ha disattivato la funzione ufficiale. 
sysregister ui-based.

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

## risoluzione problemi

se qualcosa non funziona, controlla eventuali errori nel terminale e assicurati che l’installazione non abbia restituito messaggi di errore.

---

## grazie a

* [classeviva-official-endpoints](https://github.com/Lioydiano/Classeviva-Official-Endpoints)
* sysregister del buon [syswhite.dev](https://github.com/syswhitedev)
* [CVVSimpleAvgrage](https://github.com/LucaCraft89/CVVSimpleAvgrage)


per aver reso possibile tutto questo ❤️

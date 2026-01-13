<p align="center">
  <img src="https://raw.githubusercontent.com/gablilli/chemediaho/main/static/icons/icon-192.png" width="120" alt="che media ho? logo">
</p>

<h1 align="center">📊 che media ho?</h1>

<p align="center">
  <b>la web app self-hostabile per calcolare la media dei voti su classeviva</b><br>
  anche quando l’istituto ha disattivato la funzione ufficiale.
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/gablilli/chemediaho?style=flat-square">
  <img src="https://img.shields.io/github/license/gablilli/chemediaho?style=flat-square">
  <img src="https://img.shields.io/github/actions/workflow/status/gablilli/chemediaho/release.yml?style=flat-square">
  <img src="https://img.shields.io/docker/pulls/gablilli/chemediaho?style=flat-square">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/pwa-ready-blue?style=flat-square">
  <img src="https://img.shields.io/badge/offline-supported-success?style=flat-square">
  <img src="https://img.shields.io/badge/100%25-open--source-green?style=flat-square">
</p>

---

## 🧠 cos’è *che media ho?*

**che media ho?** è una semplice **web app flask**, self-hostabile via **docker**, che ti permette di:

- visualizzare la **media dei voti su classeviva**
- fare **simulazioni e previsioni**
- usare l’app anche **offline**
- installarla come **pwa** su smartphone

il tutto tramite una **ui chiara**, pulita e mobile-friendly.

---

## ✨ funzionalità

- 📱 **pwa (progressive web app)** — installabile su android e ios  
- 🔄 **supporto offline** — funziona anche senza connessione (con dati già scaricati)  
- 🎨 **design responsive** — perfetto su mobile e desktop  
- 📊 **calcolo automatico della media**  
- 🎯 **calcoli & previsioni** — scopri che voti ti servono per raggiungere un obiettivo  
- 📈 **grafici interattivi** — visualizza l’andamento nel tempo  
- 💾 **esportazione csv** — porta i tuoi voti dove vuoi  
- 🆓 **100% free & open source** — con controlli codeql  

---

## 🚀 installazione (python)

### prerequisiti
- python **3.6+**
- un account **classeviva** attivo

### 1️⃣ clona il repository
```bash
git clone https://github.com/gablilli/chemediaho.git
cd chemediaho
````

### 2️⃣ installa le dipendenze

```bash
pip install -r requirements.txt
```

### 3️⃣ avvia l’app

```bash
python app.py
```

apri il browser su 👉 **[http://localhost:8001](http://localhost:8001)**
inserisci le credenziali e… **buona media! 🧮**

---

## 🐳 installazione con docker (consigliata)

### prerequisiti

* docker & docker compose
  👉 [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)

### scarica il `docker-compose.yml`

```bash
curl -fsSL https://raw.githubusercontent.com/gablilli/chemediaho/refs/heads/main/docker-compose.yml -o docker-compose.yml
```

### avvia il container

```bash
docker compose up -d
```

l’app sarà disponibile su **porta 8001**.

se usi **ufw**:

```bash
sudo ufw allow 8001
```

> ℹ️ nota: logging avanzato in arrivo.

---

## 🔐 configurazione avanzata

### https & sicurezza cookie

di default l’app gira in **http** (uso locale/domestico).
se sei dietro un **proxy https**, abilita:

```yaml
environment:
  - flask_env=production
  - https_enabled=true
```

questo abilita il flag `secure` sui cookie di sessione.

---

## 📱 installazione come pwa

### android (chrome)

1. apri l’app
2. menu ⋮ → *installa app*
3. conferma

### ios (safari)

1. apri l’app
2. condividi (□↑)
3. *aggiungi a home*
4. conferma

---

## 🔑 chiave segreta e sessioni

* generata automaticamente al primo avvio (`secret_key.txt`)
* permessi **600**
* persistita via volume docker
* esclusa da git

⚠️ **sicurezza**

* proteggi l’accesso al file
* in produzione usa `secret_key` o secret manager
* supporto a **docker secrets** incluso

esempio:

```yaml
    environment:
      - secret_key_file=/run/secrets/flask_secret
    secrets:
      - flask_secret

secrets:
  flask_secret:
    external: true
```

---

## 🛠️ risoluzione problemi

* controlla i log del container
* verifica credenziali classeviva
* assicurati che la porta 8001 sia aperta

---

## ❤️ ringraziamenti

grazie a:

* [classeviva official endpoints](https://github.com/lioydiano/classeviva-official-endpoints)
* sysregister di [syswhite.dev](https://github.com/syswhitedev)
* [cvvsimpleavgrage](https://github.com/lucacraft89/cvvsimpleavgrage)

per aver reso possibile tutto questo.

---

<p align="center">
  <b>📚 studia meno i calcoli, pensa più ai voti.</b>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/gablilli/chemediaho/main/frontend/icons/icon-192.png" width="120" alt="che media ho? logo">
</p>

<h1 align="center">📊 che media ho?</h1>

<p align="center">
  <b>la web app self-hostabile per calcolare la media dei voti su classeviva</b><br>
  anche quando l'istituto ha disattivato la funzione ufficiale.
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

## 🧠 cos'è *che media ho?*

**che media ho?** è una semplice **web app flask**, self-hostabile via **docker**, che ti permette di:

- visualizzare la **media dei voti su classeviva**
- fare **simulazioni e previsioni**
- usare l'app anche **offline**
- installarla come **pwa** su smartphone

il tutto tramite una **ui chiara**, pulita e mobile-friendly.

---

## ✨ funzionalità

- 📱 **pwa (progressive web app)** — installabile su android e ios  
- 🔄 **supporto offline** — funziona anche senza connessione (con dati già scaricati)  
- 🎨 **design responsive** — perfetto su mobile e desktop  
- 📊 **calcolo automatico della media**  
- 🎯 **calcoli & previsioni** — scopri che voti ti servono per raggiungere un obiettivo  
- 📈 **grafici interattivi** — visualizza l'andamento nel tempo  
- 💾 **esportazione csv** — porta i tuoi voti dove vuoi  
- 🆓 **100% free & open source** — con controlli codeql  

---

## 🎛️ modalità di utilizzo

l'app supporta **due modalità**:

### 1️⃣ docker all-in-one (consigliata)

tutto in un unico container: frontend + api.

- ✅ semplice da configurare
- ✅ ideale per uso locale/domestico
- ✅ basta un `docker compose up`

### 2️⃣ vercel + api locale

frontend su vercel, api locale con tunnel https.

- ✅ frontend accessibile ovunque
- ✅ api su ip residenziale (bypass akamai waf)
- ✅ richiede ngrok/cloudflare tunnel

---

## 🐳 installazione con docker (consigliata)

modalità **all-in-one**: frontend + api nello stesso container.

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

l'app sarà disponibile su **porta 8001**.
apri 👉 **[http://localhost:8001](http://localhost:8001)**

se usi **ufw**:

```bash
sudo ufw allow 8001
```

---

## 🚀 installazione (python)

### prerequisiti
- python **3.6+**
- un account **classeviva** attivo

### 1️⃣ clona il repository
```bash
git clone https://github.com/gablilli/chemediaho.git
cd chemediaho
```

### 2️⃣ installa le dipendenze

```bash
pip install -r requirements.txt
```

### 3️⃣ avvia l'app

```bash
python app.py
```

apri il browser su 👉 **[http://localhost:8001](http://localhost:8001)**
inserisci le credenziali e… **buona media! 🧮**

---

## 🌐 vercel + api locale

per utenti avanzati: frontend su vercel, api locale.

### perché questa modalità?

- classeviva usa **akamai waf** che blocca richieste da datacenter
- l'api deve girare su un **ip residenziale** (casa tua)
- il frontend può stare su vercel (accessibile ovunque)

### setup

#### 1. avvia l'api locale

```bash
STANDALONE_MODE=false HTTPS_ENABLED=true API_KEY=tua-chiave-segreta python app.py
```

#### 2. esponi l'api con tunnel https

```bash
ngrok http 8001
# oppure cloudflare tunnel
```

#### 3. configura il frontend

modifica `frontend/js/config.runtime.js`:

```javascript
window.APP_CONFIG = {
  API_BASE: "https://tuo-tunnel.ngrok.io",
  API_KEY: "tua-chiave-segreta"
};
```

#### 4. deploy su vercel

```bash
cd frontend
vercel --prod
```

> ⚠️ **importante**: con questa modalità devi usare `HTTPS_ENABLED=true` per i cookie cross-origin.

---

## 🔐 configurazione avanzata

### variabili d'ambiente

| variabile | default | descrizione |
|-----------|---------|-------------|
| `STANDALONE_MODE` | `true` | `true` = frontend + api insieme, `false` = solo api |
| `HTTPS_ENABLED` | `false` | `true` = abilita cookie sicuri per https |
| `API_KEY` | - | chiave per autenticare richieste api |

### https & sicurezza cookie

di default l'app gira in **http** (uso locale/domestico).
se sei dietro un **proxy https**, abilita:

```yaml
environment:
  - FLASK_ENV=production
  - HTTPS_ENABLED=true
```

questo abilita il flag `secure` sui cookie di sessione.

### protezione api key

per proteggere l'api da accessi non autorizzati:

```yaml
environment:
  - API_KEY=tua-chiave-segreta
```

tutte le richieste devono includere l'header `X-API-Key`.

---

## 📱 installazione come pwa

### android (chrome)

1. apri l'app
2. menu ⋮ → *installa app*
3. conferma

### ios (safari)

1. apri l'app
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

* proteggi l'accesso al file
* in produzione usa `secret_key` o secret manager
* supporto a **docker secrets** incluso

esempio:

```yaml
    environment:
      - SECRET_KEY_FILE=/run/secrets/flask_secret
    secrets:
      - flask_secret

secrets:
  flask_secret:
    external: true
```

---

## 🛠️ risoluzione problemi

### 401 dopo login (cross-origin)

se usi vercel + api locale e ricevi 401 dopo il login:

1. assicurati che `HTTPS_ENABLED=true` sia impostato
2. usa un tunnel https (ngrok, cloudflare)
3. verifica che `API_BASE` in `config.runtime.js` sia corretto

### controlla i log

```bash
docker logs chemediaho
```

### altri problemi

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

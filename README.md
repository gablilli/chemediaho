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

### 2️⃣ vercel + api locale (avanzata)

frontend su vercel, api locale con tunnel https.

- ✅ frontend accessibile ovunque
- ✅ api su ip residenziale (bypass akamai waf)
- ✅ richiede ngrok/cloudflare tunnel

---

## 1 - 🐳 installazione con docker (consigliata)

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

## 2 - 🌐 vercel + api locale

per utenti avanzati: frontend su vercel, api locale.

### perché questa modalità?

- classeviva usa **akamai waf** che blocca richieste da datacenter
- l'api deve girare su un **ip residenziale** (casa tua)
- il frontend può stare su vercel (con tutti i benefici che ne conseguono)

### setup

#### 1. avvia l'api locale

```bash
STANDALONE_MODE=false HTTPS_ENABLED=true API_KEY=tua-chiave-segreta python app.py
```

L'```API_KEY``` non è obbligatoria, ma consigliata.
[!note]
> È molto importante che ```HTTPS_ENABLED``` sia true.

#### 2. esponi l'api con tunnel https

```bash
ngrok http 8001
# oppure cloudflare tunnel
```

#### 3. deploya su vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fgablilli%2Fchemediaho%2Ftree%2Fmain%2Ffrontend&env=API_BASE,API_KEY&project-name=mychemediaho&repository-name=mychemediaho)

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
* apri una issue

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

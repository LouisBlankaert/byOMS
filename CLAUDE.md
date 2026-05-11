# By OMS - Site de réservation rehaussement de cils

## Business
- Nom : By OMS
- Instagram : @by.oms
- Service : rehaussement de cils uniquement
- Ville : Bruxelles
- Horaires : lundi au dimanche, 10h - 18h
- Durée par créneau : 1h
- Créneaux : 10:00, 11:30, 13:00, 14:30, 16:00, 17:30

## Prix
- Semaine (lundi-samedi) : 35€ (variable `PRICE_WEEKDAY` dans app.py)
- Dimanche : 40€ (variable `PRICE_SUNDAY` dans app.py)
- Option teinture : +5€ (variable `PRICE_TEINTURE` dans app.py)

## Paiement
- **Masqué pour le moment** — la section paiement/virement est retirée de l'interface
- Quand elle sera réactivée : ajouter `BANK_IBAN` dans `.env` et remettre la section dans `templates/confirmation.html`
- Flow prévu : booking form → sauvegarde en DB (`paid=True`) → `/confirmation` avec IBAN

## Option teinture
- Prix : +5€ (variable `PRICE_TEINTURE` dans app.py)
- Toggle dans le formulaire étape 4
- Champ `teinture` (boolean) dans le modèle Reservation
- Affiché dans la confirmation et dans l'admin (modal + pilule calendrier "· T")

## Notifications
- **À faire** : mettre en place une notification email quand un RDV est enregistré
- Solution recommandée : Gmail avec mot de passe d'application (SMTP)
- Variables à ajouter dans `.env` : `ADMIN_EMAIL`, `MAIL_PASSWORD`

## Pages
- `/` → landing page
- `/booking` → calendrier custom + créneaux + formulaire 4 étapes → sauvegarde directe en DB
- `/contact` → page contact avec bouton DM Instagram (@by.oms)
- `/confirmation` → résumé RDV (sans paiement pour l'instant)
- `/admin` → dashboard admin (agenda mensuel, déplacement + suppression RDV)
- `/admin/login` → login admin

## API
- `/api/availability?date=YYYY-MM-DD` → disponibilité des créneaux pour une date
- `/api/unavailable-month?month=YYYY-MM` → dates bloquées ou complètes du mois (utilisé par le calendrier booking)

## Stack
- Python 3 + Flask + SQLAlchemy + Gunicorn
- SQLite en dev (`instance/byoms.db`), PostgreSQL en prod (Railway)
- Jinja2 + Tailwind CSS via CDN
- Google Fonts : Playfair Display + Inter
- Couleur principale : vert olive (`#6B7C3C`)

## Modèle Reservation
- Champs : id, name, phone, instagram, email, date, time_slot, price, teinture, paid, created_at
- `paid=True` mis automatiquement à la sauvegarde (pas de paiement en ligne)
- `instagram` : obligatoire. `phone` et `email` : optionnels (nullable=True)
- Ordre formulaire étape 3 : Nom → Instagram → Téléphone (opt.) → Email (opt.)
- Les créneaux passés aujourd'hui sont grisés (fuseau Europe/Brussels via zoneinfo)

## Modèle UnavailableDay
- Table `unavailable_days` : id, date (unique)
- Créée automatiquement via `db.create_all()`
- Permet à l'admin de bloquer des journées entières
- Impact : `/api/availability` retourne tous les créneaux à `false`, `/booking` refuse la date, calendrier booking grise le jour en rouge

## Lancer le projet (dev)
```bash
venv/bin/python app.py
```
Site local : http://127.0.0.1:5000
- Si port 5000 occupé : désactiver AirPlay Receiver dans Réglages système → Général → AirDrop et Handoff
- Tuer le process qui bloque le port (si Ctrl+C ne fonctionne pas) :
  ```bash
  lsof -ti:5000 | xargs kill -9   # fonctionne pour n'importe quel port
  ```
- Voir ce qui tourne sur un port avant de tuer :
  ```bash
  lsof -i:5000
  ```
- Ou tuer tous les process Python du projet :
  ```bash
  pkill -f "venv/bin/python app.py"
  ```

## Installer les dépendances
```bash
venv/bin/pip install -r requirements.txt
```

## DB
- SQLite recrée automatiquement au lancement en dev
- Visualiser avec TablePlus → SQLite → `instance/byoms.db`
- En prod : PostgreSQL Railway (URL publique dans `DATABASE_URL`)

## Variables d'environnement (.env)
```
SECRET_KEY=...
ADMIN_PASSWORD=byoms2026
DATABASE_URL=           ← vide en dev (SQLite), URL PostgreSQL en prod
BANK_IBAN=              ← vide pour l'instant, à remplir quand le paiement sera réactivé
```

## Admin
- URL local : http://127.0.0.1:5000/admin
- Mot de passe : `byoms2026` (variable `ADMIN_PASSWORD` dans `.env`)
- Fonctions : voir RDV du mois, déplacer un RDV, supprimer un RDV, bloquer/débloquer une journée
- Les RDV avec teinture affichent "· T" sur la pilule et un badge dans le modal
- Jours bloqués : fond rouge pâle + label "Bloqué" + icône cadenas (visible au survol, toujours si bloqué)
- Cliquer sur le cadenas d'un jour le ferme (confirmation si RDV existants) ou le réouvre
- Modal RDV : nom, téléphone, Instagram (cliquable), email, date, heure, teinture, prix total

## Réseaux sociaux
- Instagram uniquement : @by.oms → https://instagram.com/by.oms
- TikTok : handle inconnu pour l'instant (retiré du footer)
- Lien "Contact" dans la nav → `/contact` (page dédiée avec bouton DM Instagram)

## Production (Railway)
- Stack : Railway (Flask + PostgreSQL)
- Start command : `gunicorn app:app --bind 0.0.0.0:$PORT`
- Repo GitHub : à créer (projet indépendant, rien à voir avec Babelash)

### Étapes de déploiement
1. Créer repo GitHub privé `by-oms`
2. Init git + push :
   ```bash
   cd /Users/louisblankaert/Desktop/by_oms
   git init
   echo "venv/\ninstance/\n.env\n__pycache__/" > .gitignore
   git add .
   git commit -m "init"
   git remote add origin https://github.com/TON_USERNAME/by-oms.git
   git push -u origin main
   ```
3. Railway → New Project → Deploy from GitHub → sélectionner `by-oms`
4. Railway → + New → Database → PostgreSQL (injecte `DATABASE_URL` automatiquement)
5. Railway → Variables à ajouter :
   ```
   SECRET_KEY=une-clé-longue-aléatoire
   ADMIN_PASSWORD=byoms2026
   FLASK_ENV=production
   ```
6. Railway → Settings → Start Command : `gunicorn app:app --bind 0.0.0.0:$PORT`

### Variables Railway
- `SECRET_KEY` : clé secrète longue et aléatoire
- `ADMIN_PASSWORD` : byoms2026
- `DATABASE_URL` : injectée automatiquement par Railway PostgreSQL
- `FLASK_ENV` : production
- `BANK_IBAN` : optionnel, à ajouter quand le paiement sera réactivé

## À faire
- [ ] Réactiver la section paiement (IBAN) quand prêt — ajouter IBAN dans `.env` et dans `confirmation.html`
- [ ] Notifications email à la propriétaire lors d'un nouveau RDV (Gmail SMTP)
- [ ] Handle TikTok à ajouter dans le footer (`templates/base.html`)
- [ ] Domaine custom sur Railway

## Instructions
- Use context7 for up to date documentation
- Use Magic MCP for complex UI components
- Use UI UX Pro Max design system

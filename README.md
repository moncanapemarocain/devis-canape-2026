# 🛋️ Générateur de Devis Canapés Sur Mesure

Application web simple pour générer des devis professionnels de canapés personnalisés.

## 🚀 Installation (Très Simple !)

### Prérequis
- Python 3.8 ou plus récent (téléchargeable sur python.org)

### Étapes d'installation

1. **Téléchargez tous les fichiers** dans un même dossier :
   ```
   projet-canape/
   ├── app.py
   ├── canapefullv14.py    (votre fichier existant)
   ├── pricing.py
   ├── pdf_generator.py
   └── requirements.txt
   ```

2. **Ouvrez un terminal** (ou "Invite de commandes" sur Windows)

3. **Naviguez vers votre dossier** :
   ```bash
   cd chemin/vers/projet-canape
   ```

4. **Installez les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```
   
   ⏱️ *Cela prend 2-3 minutes*

## ▶️ Lancement de l'Application

1. **Dans le terminal, tapez** :
   ```bash
   streamlit run app.py
   ```

2. **L'application s'ouvre automatiquement dans votre navigateur** ! 🎉
   
   Si elle ne s'ouvre pas, allez sur : `http://localhost:8501`

## 📱 Comment Utiliser l'Application

### Interface Simple
L'écran est divisé en 2 parties :
- **À gauche** : Formulaire de configuration
- **À droite** : Aperçu et génération PDF

### Étapes pour Créer un Devis

1. **Choisissez le type de canapé**
   - Simple (S)
   - L (avec ou sans angle)
   - U (avec 0, 1 ou 2 angles)

2. **Remplissez les dimensions**
   - Les champs s'adaptent automatiquement selon le type choisi

3. **Configurez les options**
   - Cochez/décochez les accoudoirs et dossiers
   - Ajoutez une méridienne si besoin
   - Choisissez le type de coussins

4. **Personnalisez**
   - Type de mousse
   - Couleurs
   - Options supplémentaires

5. **Informations client**
   - Entrez le nom (obligatoire)
   - Email (optionnel)

6. **Générez l'aperçu** en cliquant sur le bouton bleu

7. **Téléchargez le PDF** en cliquant sur le bouton de génération

## 📄 Le PDF Généré

Le PDF contient 2 pages :

### Page 1 : Configuration & Schéma
- En-tête avec date et client
- Toutes les spécifications du canapé
- Schéma visuel

### Page 2 : Détail du Prix
- Liste détaillée de tous les composants
- Prix unitaires
- Sous-total HT
- TVA (20%)
- **Total TTC** en gros et vert
- Conditions de paiement
- Zone de signatures

## 🎨 Personnalisation

### Modifier les Prix

Ouvrez `pricing.py` et modifiez les dictionnaires en haut du fichier :

```python
PRIX_COUSSINS = {
    '65': 35,  # ← Changez ici
    '80': 44,
    '90': 48,
    'valise': 70
}

PRIX_COMPOSANTS = {
    'accoudoir': 225,  # ← Et ici
    'dossier': 250,
    # ...
}
```

### Modifier l'Apparence du PDF

Ouvrez `pdf_generator.py` et ajustez :
- Les couleurs (lignes avec `colors.`)
- Les polices (lignes avec `setFont`)
- Les marges (valeurs en `cm`)

## 🆘 Résolution de Problèmes

### L'application ne démarre pas
```bash
# Vérifiez que Python est installé
python --version

# Réinstallez les dépendances
pip install -r requirements.txt --force-reinstall
```

### Le PDF ne se génère pas
- Vérifiez que tous les champs obligatoires sont remplis
- Regardez les messages d'erreur en rouge dans l'interface

### Le schéma ne s'affiche pas
- C'est normal pour l'instant ! Le schéma sera intégré dans une prochaine version
- Le placeholder montre où il apparaîtra

## 📞 Support

En cas de problème :
1. Vérifiez les messages d'erreur dans l'application
2. Consultez la console/terminal pour les détails techniques
3. Contactez votre développeur avec une capture d'écran

## 🔄 Mises à Jour Futures

Prochaines fonctionnalités prévues :
- ✅ Intégration complète du schéma Turtle
- ✅ Export des schémas en image PNG
- ✅ Base de données des clients
- ✅ Historique des devis
- ✅ Envoi automatique par email

## 📝 Notes Techniques

- **Framework** : Streamlit (interface web simple)
- **PDF** : ReportLab (génération professionnelle)
- **Schémas** : Turtle Graphics (votre code existant)
- **Python** : Version 3.8+ requise

## ⚖️ Licence

Usage interne uniquement pour votre entreprise.

---

**Version** : 1.0  
**Date** : 2025  
**Développé pour** : [Votre Entreprise]
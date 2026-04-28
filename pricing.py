"""
Module de calcul des devis pour canapés marocains.

Ce module expose la fonction ``calculer_prix_total`` qui, à partir d’une
configuration de canapé et des valeurs mesurées par le module de rendu
(`canapematplot.py`), calcule un prix TTC détaillé.  Il tient compte des
dimensions des mousses, du tissu, des supports (banquettes, banquettes
d’angle, dossiers), des coussins (65 cm, 80 cm, 90 cm et valise), des
traversins, des surmatelas, des accoudoirs et des arrondis.  Les
formules et tarifs appliqués suivent les directives fournies par
l’utilisateur.

Principales règles :

* **Mousses** : pour chaque mousse droite ou d’angle, le prix TTC est
  calculé par :

      (longueur * largeur * épaisseur * densité * 22) / 1 000 000

  où les dimensions proviennent du rapport console, l’épaisseur est
  saisie par l’utilisateur (cm) et la densité dépend du type de mousse
  (D25 → 25, D30 → 30, HR35 → 35, HR45 → 45).

* **Tissu** : pour chaque mousse, si ``largeur + (épaisseur * 2) > 140``
  alors le coût est ``(longueur/100) * 105``, sinon ``(longueur/100) * 74``.

* **Supports** : banquette droite = 250 €, banquette d’angle = 250 €, dossier = 250 €.
  Chaque accoudoir est facturé 200 €.

* **Coussins** : coussins d’assise et décoratifs sont comptés selon leur
  taille : 65 cm → 40 €, 80 cm → 50 €, 90 cm → 55 €, valise → 75 €.
  Les coussins déco supplémentaires coûtent 15 € pièce.

* **Traversins** : 30 € l’unité ; **Surmatelas** : 80 € l’unité.

* **Arrondis** : si l’option est activée, un supplément de 20 € est
  ajouté par banquette droite et par banquette d’angle.

La fonction renvoie un dictionnaire contenant :

``prix_ht`` : montant hors taxe (TTC / 1,20),
``cout_revient_ht`` : estimation simplifiée du coût de revient (70 % du HT),
``tva`` : montant de la TVA (TTC − HT),
``total_ttc`` : total toutes taxes comprises,
``calculation_details`` : liste détaillée des calculs (chaque entrée avec la
 catégorie, l’article, la quantité, la formule utilisée et le total).

Le module charge dynamiquement ``canapematplot.py`` pour obtenir les
dimensions et quantités imprimées en console.  En cas d’erreur, une
``RuntimeError`` est levée afin que l’application Streamlit puisse
afficher un message compréhensible.
"""

from __future__ import annotations

import contextlib
import importlib.machinery
import io
import os
import re
from typing import Dict, List, Tuple


def _load_canape_module() -> object:
    """Charge et retourne le module de rendu (canapefullv125.py).

    Ce chargeur utilise ``importlib.machinery.SourceFileLoader`` pour
    importer un fichier Python dont le nom est fixé (``canapefullv125.py``).
    Historiquement, ce module s'appelait ``canapematplot.py``, mais le
    projet a évolué et regroupe désormais toutes les routines de rendu dans
    ``canapefullv125.py``.  Cette fonction neutralise les appels bloquants
    comme ``plt.show`` et ``turtle.done`` afin que le rendu graphique ne
    bloque pas le calcul.
    """
    global _CANAPE_MOD
    if '_CANAPE_MOD' in globals() and _CANAPE_MOD is not None:
        return _CANAPE_MOD
    this_dir = os.path.dirname(os.path.abspath(__file__))
    # Le fichier de rendu à charger.  Certains environnements utilisent
    # ``canapematplot.py`` tandis que d'autres possèdent une version
    # ``canapefullv125.py``.  Nous essayons successivement ces noms
    # et chargeons le premier fichier trouvé.
    for candidate in ('canapefullv125.py', 'canapefullv.py', 'canapematplot.py'):
        path = os.path.join(this_dir, candidate)
        if os.path.exists(path):
            filename = candidate
            break
    else:
        # Si aucun fichier n'est trouvé, conserver le nom historique par défaut
        filename = 'canapematplot.py'
    path = os.path.join(this_dir, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cannot find the canape rendering module at {path!r}")
    loader = importlib.machinery.SourceFileLoader('canape_render', path)
    mod = loader.load_module()
    try:
        import matplotlib
        matplotlib.use('Agg', force=True)
    except Exception:
        pass
    try:
        mod.plt.show = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        mod.turtle.done = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    except Exception:
        pass
    globals()['_CANAPE_MOD'] = mod
    return mod


def _call_render_function(mod: object, *, type_canape: str, tx: float | int | None, ty: float | int | None,
                          tz: float | int | None, profondeur: float | int | None, dossier_left: bool, dossier_bas: bool,
                          dossier_right: bool, acc_left: bool, acc_bas: bool, acc_right: bool,
                          meridienne_side: str | None, meridienne_len: float | int | None,
                          coussins: str | int | None, traversins: str | None = None) -> str:
    """Appelle la fonction de rendu appropriée et capture la sortie console."""
    try:
        render_func: callable
        kwargs: Dict[str, object] = {}
        t = (type_canape or '').lower()
        if 'simple' in t:
            render_func = getattr(mod, 'render_Simple1')
            kwargs = dict(
                tx=tx,
                profondeur=profondeur,
                dossier=dossier_bas,
                acc_left=acc_left,
                acc_right=acc_right,
                meridienne_side=meridienne_side,
                meridienne_len=meridienne_len or 0,
                coussins=coussins or 'auto',
                traversins=traversins,
                window_title="simple"
            )
        elif 'l - sans angle' in t:
            render_func = getattr(mod, 'render_LNF')
            kwargs = dict(
                tx=tx,
                ty=ty,
                profondeur=profondeur,
                dossier_left=dossier_left,
                dossier_bas=dossier_bas,
                acc_left=acc_left,
                acc_bas=acc_bas,
                meridienne_side=meridienne_side,
                meridienne_len=meridienne_len or 0,
                coussins=coussins or 'auto',
                traversins=traversins,
                variant="auto",
                window_title="LNF"
            )
        elif 'l - avec angle' in t:
            render_func = getattr(mod, 'render_LF_variant')
            kwargs = dict(
                tx=tx,
                ty=ty,
                profondeur=profondeur,
                dossier_left=dossier_left,
                dossier_bas=dossier_bas,
                acc_left=acc_left,
                acc_bas=acc_bas,
                meridienne_side=meridienne_side,
                meridienne_len=meridienne_len or 0,
                coussins=coussins or 'auto',
                traversins=traversins,
                window_title="LF"
            )
        elif 'u - sans angle' in t or (('u ' in t) and ('sans angle' in t)):
            render_func = getattr(mod, 'render_U')
            kwargs = dict(
                tx=tx,
                ty_left=ty,
                tz_right=tz,
                profondeur=profondeur,
                dossier_left=dossier_left,
                dossier_bas=dossier_bas,
                dossier_right=dossier_right,
                acc_left=acc_left,
                acc_bas=acc_bas,
                acc_right=acc_right,
                coussins=coussins or 'auto',
                traversins=traversins,
                variant="auto",
                window_title="U"
            )
        elif 'u - 1 angle' in t:
            render_func = getattr(mod, 'render_U1F_v1')
            kwargs = dict(
                tx=tx,
                ty=ty,
                tz=tz,
                profondeur=profondeur,
                dossier_left=dossier_left,
                dossier_bas=dossier_bas,
                dossier_right=dossier_right,
                acc_left=acc_left,
                acc_right=acc_right,
                meridienne_side=meridienne_side,
                meridienne_len=meridienne_len or 0,
                coussins=coussins or 'auto',
                traversins=traversins,
                window_title="U1F"
            )
        elif 'u - 2 angles' in t:
            render_func = getattr(mod, 'render_U2f_variant')
            kwargs = dict(
                tx=tx,
                ty_left=ty,
                tz_right=tz,
                profondeur=profondeur,
                dossier_left=dossier_left,
                dossier_bas=dossier_bas,
                dossier_right=dossier_right,
                acc_left=acc_left,
                acc_bas=acc_bas,
                acc_right=acc_right,
                meridienne_side=meridienne_side,
                meridienne_len=meridienne_len or 0,
                coussins=coussins or 'auto',
                traversins=traversins,
                variant="auto",
                window_title="U2F"
            )
        else:
            raise ValueError(f"Unrecognised type_canape: {type_canape}")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            render_func(**kwargs)  # type: ignore[func-returns-value]
        return buf.getvalue()
    except Exception as exc:
        raise RuntimeError(f"Erreur lors de l'exécution du rendu: {exc}") from exc


def _parse_console_report(report: str) -> Dict[str, object]:
    """Analyse les lignes émises dans la console par le module de rendu.

    On extrait les nombres de banquettes, banquettes d’angle, dossiers,
    accoudoirs, les dimensions de chaque mousse (droite ou angle) et le
    nombre de coussins de chaque taille, ainsi que les traversins.  Les
    valeurs absentes sont initialisées à 0 ou listes vides.
    """
    result: Dict[str, object] = {
        'nb_banquettes': 0,
        'nb_banquettes_angle': 0,
        'nb_dossiers': 0,
        'nb_accoudoirs': 0,
        'dims_mousses': [],
        'dims_mousses_angle': [],
        # Liste des dimensions de chaque dossier (longueur, épaisseur). Les
        # dimensions sont extraites des lignes imprimées par canapematplot
        # de type "Dossier X : L×P cm" ou "Dossier X = LxPcm".  Cela
        # permet d'établir un coût ou un prix unitaire par dossier.
        'dims_dossiers': [],
        # Liste des dimensions de chaque accoudoir (longueur, épaisseur). Les
        # dimensions sont extraites des lignes imprimées par canapematplot
        # de type "Accoudoir côté ... = LxPcm".  On utilise ces
        # informations pour détailler le coût de revient et le prix de
        # vente accoudoir par accoudoir.
        'dims_accoudoirs': [],
        'nb_coussins_65': 0,
        'nb_coussins_80': 0,
        'nb_coussins_90': 0,
        'nb_coussins_valise': 0,
        'nb_traversins': 0,
    }
    lines = [line.strip() for line in report.splitlines() if line.strip()]
    pat_int = re.compile(r"\d+")
    # Les motifs pour les dimensions de mousse acceptent désormais des identifiants
    # non strictement entiers (par ex. 1a, 1.1) et des nombres décimaux avec
    # point ou virgule.  Dans certains modèles, lorsque la mousse est scindée en
    # plusieurs parties (« scission »), l'index peut contenir des lettres ou des
    # décimales et les dimensions comporter des virgules.  Pour être robuste,
    # on capture n'importe quelle séquence non‑espace pour l'identifiant et on
    # accepte des composantes numériques au format « 123 », « 123.4 » ou
    # « 123,4 ».  On convertit ensuite les nombres en flottants en remplaçant
    # la virgule par un point.
    pat_mousse = re.compile(
        r"^Dimension mousse\s+(\S+)\s*:\s*([0-9]+(?:[\.,][0-9]+)?)\s*,\s*([0-9]+(?:[\.,][0-9]+)?)",
        re.IGNORECASE
    )
    pat_mousse_angle = re.compile(
        r"^Dimension mousse angle\s+(\S+)\s*:\s*([0-9]+(?:[\.,][0-9]+)?)\s*,\s*([0-9]+(?:[\.,][0-9]+)?)",
        re.IGNORECASE
    )
    for line in lines:
        if line.lower().startswith('nombre de banquettes'):
            m = pat_int.search(line)
            if m:
                result['nb_banquettes'] = int(m.group())
        elif 'banquette d’angle' in line.lower() or 'banquette d\'angle' in line.lower():
            m = pat_int.search(line)
            if m:
                result['nb_banquettes_angle'] = int(m.group())
        elif line.lower().startswith('nombre de dossiers'):
            m = pat_int.search(line)
            if m:
                result['nb_dossiers'] = int(m.group())
        elif line.lower().startswith('nombre d’accoudoir') or line.lower().startswith("nombre d'accoudoir"):
            m = pat_int.search(line)
            if m:
                result['nb_accoudoirs'] = int(m.group())
        elif line.lower().startswith('dimension mousse angle'):
            # Extraire les dimensions des mousses d'angle, en supportant les décimales
            m = pat_mousse_angle.match(line)
            if m:
                # Remplacer la virgule par un point pour permettre la conversion float
                try:
                    L_raw = m.group(2).replace(',', '.')
                    P_raw = m.group(3).replace(',', '.')
                    L = float(L_raw)
                    P = float(P_raw)
                    result['dims_mousses_angle'].append((L, P))
                except Exception:
                    # En cas d'échec, ignorer cette ligne afin de ne pas bloquer l'analyse
                    pass
        elif line.lower().startswith('dimension mousse'):
            # Extraire les dimensions des mousses droites, y compris en cas de scission
            m = pat_mousse.match(line)
            if m:
                try:
                    L_raw = m.group(2).replace(',', '.')
                    P_raw = m.group(3).replace(',', '.')
                    L = float(L_raw)
                    P = float(P_raw)
                    result['dims_mousses'].append((L, P))
                except Exception:
                    pass
        elif 'nombre de coussins 65' in line.lower():
            parts = line.split(':')
            if len(parts) >= 2:
                try:
                    qty = int(re.findall(r"\d+", parts[1])[0])
                    result['nb_coussins_65'] = qty
                except Exception:
                    pass
        elif 'nombre de coussins 80' in line.lower():
            parts = line.split(':')
            if len(parts) >= 2:
                try:
                    qty = int(re.findall(r"\d+", parts[1])[0])
                    result['nb_coussins_80'] = qty
                except Exception:
                    pass
        elif 'nombre de coussins 90' in line.lower():
            parts = line.split(':')
            if len(parts) >= 2:
                try:
                    qty = int(re.findall(r"\d+", parts[1])[0])
                    result['nb_coussins_90'] = qty
                except Exception:
                    pass
        elif 'nombre de coussins valises' in line.lower():
            m = pat_int.search(line)
            if m:
                result['nb_coussins_valise'] = int(m.group())
        elif 'nombre de traversin' in line.lower():
            m = pat_int.search(line)
            if m:
                result['nb_traversins'] = int(m.group())
        else:
            continue
    # Deuxième passe pour détecter les dimensions des dossiers et des accoudoirs.
    # On effectue une boucle distincte afin de ne pas perturber la logique
    # d'extraction précédente. Les lignes sont déjà nettoyées de leurs
    # espaces superflus dans la première boucle.
    for line in lines:
        lower = line.lower()
        # Dossiers : lignes commençant par "dossier" (et non "dossiers " ou
        # "détail des dossiers") contenant un motif de deux nombres
        # séparés par un x (ou le symbole ×). Ces motifs désignent
        # respectivement la longueur et l'épaisseur (hauteur) du dossier.
        if lower.startswith('dossier') and not lower.startswith('dossiers '):
            m_dims = re.search(r'(\d+)\s*[x×]\s*(\d+)', line)
            if m_dims:
                try:
                    L = float(m_dims.group(1))
                    P = float(m_dims.group(2))
                    result['dims_dossiers'].append((L, P))
                except Exception:
                    pass
        # Accoudoirs : lignes qui mentionnent "accoudoir" et contiennent un signe
        # égal avant un motif de deux nombres séparés par x/×.
        elif 'accoudoir' in lower and '=' in line:
            m_dims = re.search(r'(\d+)\s*[x×]\s*(\d+)', line)
            if m_dims:
                try:
                    L = float(m_dims.group(1))
                    P = float(m_dims.group(2))
                    result['dims_accoudoirs'].append((L, P))
                except Exception:
                    pass
    return result


def _density_from_type(type_mousse: str) -> float:
    """Convertit une chaîne Dxx/HRxx en densité numérique."""
    if not type_mousse:
        return 25.0
    t = str(type_mousse).strip().lower()
    if 'hr' in t:
        try:
            return float(t.replace('hr', '').replace(' ', ''))
        except Exception:
            return 35.0
    else:
        try:
            return float(t.replace('d', '').replace(' ', ''))
        except Exception:
            return 25.0


def _compute_foam_and_fabric_price(dims: List[Tuple[float, float]], thickness: float, density: float) -> Tuple[float, float]:
    """Calcule les totaux TTC de mousse et de tissu pour une liste de coussins.

    Pour chaque coussin, le prix de la mousse est :

      (longueur * largeur * épaisseur * densité * 23) / 1 000 000

    Le prix du tissu est déterminé par la largeur et l’épaisseur : si
    ``largeur + (épaisseur * 2) > 140`` alors ``(longueur/100) * 105`` sinon
    ``(longueur/100) * 74``.
    """
    foam_total = 0.0
    fabric_total = 0.0
    for L, W in dims:
        foam_total += (L * W * thickness * density * 23.0) / 1_000_000.0
        if (W + (thickness * 2.0)) > 140.0:
            fabric_total += (L / 100.0) * 105.0
        else:
            fabric_total += (L / 100.0) * 74.0
    return foam_total, fabric_total


def calculer_prix_total(
    *,
    type_canape: str,
    tx: float | int | None = None,
    ty: float | int | None = None,
    tz: float | int | None = None,
    profondeur: float | int | None = None,
    type_coussins: str | int | None = None,
    type_mousse: str | None = None,
    epaisseur: float | int | None = None,
    acc_left: bool = False,
    acc_right: bool = False,
    acc_bas: bool = False,
    dossier_left: bool = False,
    dossier_bas: bool = False,
    dossier_right: bool = False,
    nb_coussins_deco: int = 0,
    nb_traversins_supp: int = 0,
    has_surmatelas: bool | int = False,
    has_meridienne: bool | None = None,
    meridienne_side: str | None = None,
    meridienne_len: float | int | None = None,
    arrondis: bool | int = False,
    traversins: str | None = None,
    traversins_positions: List[str] | None = None,
    departement_livraison: int | str | None = None,
    surplus: float = 0.0  # <--- NOUVEL ARGUMENT ICI
) -> Dict[str, float]:
    """Calcule le prix total TTC et fournit un détail complet des calculs.

    Le paramètre ``arrondis`` indique si les arrondis doivent être facturés
    (20 € par banquette droite ou d’angle).  Les autres paramètres
    reflètent directement les champs du formulaire Streamlit.
    """
    tx = float(tx or 0)
    ty = float(ty or 0)
    tz = float(tz or 0)
    profondeur = float(profondeur or 0)
    epaisseur_val = float(epaisseur or 0)
    density = _density_from_type(type_mousse or 'D25')
    mod = _load_canape_module()
    # Déterminer la configuration des traversins (g/d/b) à partir des positions ou du nombre
    traversins_cfg = None
    # Convertir les positions fournies en codes attendus par canapematplot
    if traversins_positions:
        mapping = {
            'gauche': 'g', 'droite': 'd', 'bas': 'b',
            'Gauche': 'g', 'Droite': 'd', 'Bas': 'b'
        }
        codes: List[str] = []
        for pos in traversins_positions:
            key = str(pos).strip()
            if key in mapping:
                codes.append(mapping[key])
            else:
                lower_key = key.lower()
                if lower_key in mapping:
                    codes.append(mapping[lower_key])
        if codes:
            traversins_cfg = ",".join(sorted(set(codes)))
    elif traversins is not None:
        # Utiliser directement la valeur fournie si présente
        traversins_cfg = traversins
    elif nb_traversins_supp and nb_traversins_supp > 0:
        # Définir une configuration par défaut selon la forme du canapé
        t = (type_canape or '').lower()
        if 'simple' in t:
            traversins_cfg = 'g,d'
        elif 'l' in t:
            traversins_cfg = 'g,b'
        elif 'u' in t:
            traversins_cfg = 'g,b,d'
    # Appeler la fonction de rendu avec la configuration de traversins
    try:
        report = _call_render_function(
            mod,
            type_canape=type_canape,
            tx=tx,
            ty=ty,
            tz=tz,
            profondeur=profondeur,
            dossier_left=dossier_left,
            dossier_bas=dossier_bas,
            dossier_right=dossier_right,
            acc_left=acc_left,
            acc_bas=acc_bas,
            acc_right=acc_right,
            meridienne_side=meridienne_side,
            meridienne_len=meridienne_len or 0,
            coussins=type_coussins or 'auto',
            traversins=traversins_cfg
        )
    except Exception:
        raise
    data = _parse_console_report(report)
    dims = list(data.get('dims_mousses', []))
    dims_angle = list(data.get('dims_mousses_angle', []))
    # Récupérer également les dimensions des dossiers et des accoudoirs pour un
    # traitement individuel.  Ces valeurs sont extraites du rapport console
    # par _parse_console_report ; si aucune dimension n'est disponible, les
    # listes retournées seront vides et on utilisera les comptages pour
    # générer des lignes génériques.
    dims_dossiers: List[Tuple[float, float]] = list(data.get('dims_dossiers', []) or [])
    dims_accoudoirs: List[Tuple[float, float]] = list(data.get('dims_accoudoirs', []) or [])
    foam_straight, fabric_straight = _compute_foam_and_fabric_price(dims, epaisseur_val, density)
    foam_angle, fabric_angle = _compute_foam_and_fabric_price(dims_angle, epaisseur_val, density)
    foam_total = foam_straight + foam_angle
    fabric_total = fabric_straight + fabric_angle
    # Utiliser le nombre réel d'éléments détectés pour calculer le coût des supports.
    # Les listes `dims`, `dims_angle` et `dims_dossiers` contiennent une entrée par banquette droite,
    # par banquette d'angle et par dossier.  En comptant la longueur de ces listes plutôt
    # que les simples compteurs ``nb_*``, on s'assure que le montant total correspond aux
    # lignes détaillées dans ``calculation_details``.  Par exemple, un dossier fragmenté en plusieurs
    # segments est compté plusieurs fois dans ``dims_dossiers``, alors que ``nb_dossiers`` n'indique
    # qu'une approximation.
    # Déterminer le nombre de banquettes droites et d'angle.  On utilise le
    # nombre de dimensions détectées (qui reflète le nombre réel de pièces) et,
    # en l'absence d'information détaillée, on retombe sur le compteur brut
    # renvoyé par le module de rendu.  Cela permet notamment de prendre en
    # compte les cas de scission où plusieurs pièces sont nécessaires, mais
    # également de ne pas perdre l'information lorsqu'aucune dimension n'est
    # fournie.
    nb_banquettes = len(dims) if dims else int(data.get('nb_banquettes') or 0)
    nb_banquettes_angle = len(dims_angle) if dims_angle else int(data.get('nb_banquettes_angle') or 0)
    nb_dossiers = len(dims_dossiers) if dims_dossiers else int(data.get('nb_dossiers') or 0)
    # --- Calcul du total TTC pour les supports ---
    # Banquettes droites et d’angle sont toujours comptées une unité chacune
    support_total = 0.0
    support_total += nb_banquettes * 250.0
    support_total += nb_banquettes_angle * 250.0
    # Les dossiers courts (<= 110 cm) ne comptent qu’une demi‑quantité pour le
    # prix de vente.  Chaque dossier de longueur supérieure est compté pour
    # une quantité entière.  Lorsque les dimensions ne sont pas disponibles,
    # on considère tous les dossiers comme de longueur > 110 cm.
    if dims_dossiers:
        for L_dos, P_dos in dims_dossiers:
            qty_dos = 0.5 if L_dos <= 110.0 else 1.0
            support_total += qty_dos * 250.0
    else:
        support_total += nb_dossiers * 250.0
    nb_coussins_65 = int(data.get('nb_coussins_65') or 0)
    nb_coussins_80 = int(data.get('nb_coussins_80') or 0)
    nb_coussins_90 = int(data.get('nb_coussins_90') or 0)
    nb_coussins_valise = int(data.get('nb_coussins_valise') or 0)

    # --- Harmonisation des coussins pour les modes "valise" / "p" / "g" / "s" ---
    # Lorsque l'utilisateur choisit un mode valise ("valise", "p", "g" ou variantes avec ":s"),
    # les coussins sont tous considérés comme des coussins valise, indépendamment de la
    # dimension finale (65, 80 ou 90 cm).  Cela permet de conserver une cohérence entre le
    # rendu graphique (où l'algorithme peut choisir 80 ou 90 cm pour optimiser l'espace
    # tout en restant dans la plage autorisée) et le chiffrage du devis.  Sans cette
    # harmonisation, certains coussins étaient comptabilisés comme 65/80/90 cm alors
    # qu'ils résultaient d’un choix valise, ce qui entraînait un décalage entre le
    # nombre de coussins dessinés et les quantités notées dans le devis.
    tc_lower = str(type_coussins or '').strip().lower()
    tc_base = tc_lower.replace(':s', '')  # retirer suffixe ":s" s'il existe
    if tc_base in ('valise', 'p', 'g', 's'):
        total_valise = nb_coussins_65 + nb_coussins_80 + nb_coussins_90 + nb_coussins_valise
        nb_coussins_valise = total_valise
        nb_coussins_65 = 0
        nb_coussins_80 = 0
        nb_coussins_90 = 0

    cushion_total = (
        nb_coussins_65 * 40.0 +
        nb_coussins_80 * 50.0 +
        nb_coussins_90 * 55.0 +
        nb_coussins_valise * 75.0 +
        nb_coussins_deco * 15.0
    )
    # Déterminer le nombre de traversins à facturer.
    # Lorsque des positions spécifiques sont fournies (via traversins_positions ou traversins_cfg),
    # le rendu graphique dessine exactement ces traversins.  Dans ce cas, on ne doit pas
    # additionner à nouveau nb_traversins_supp, car nb_traversins_supp représente déjà le
    # nombre de traversins désirés et a servi à construire traversins_cfg.  Si aucune position
    # n'est spécifiée et qu'il n'y a pas de configuration, on ajoute nb_traversins_supp au
    # nombre détecté dans le rapport (généralement 0).
    nb_traversins_par_console = int(data.get('nb_traversins') or 0)
    if traversins_positions or traversins_cfg:
        nb_traversins = nb_traversins_par_console
    else:
        nb_traversins = nb_traversins_par_console + int(nb_traversins_supp or 0)
    traversin_total = nb_traversins * 30.0
    # Le nombre de surmatelas doit correspondre au nombre total de mousses (droites et d'angle)
    # lorsqu'ils sont activés. On calcule donc une unité par coussin si has_surmatelas est vrai.
    nb_surmatelas = (len(dims) + len(dims_angle)) if has_surmatelas else 0
    surmatelas_total = nb_surmatelas * 80.0
    # Idem pour les accoudoirs : utiliser les dimensions détectées si disponibles pour
    # déterminer le nombre d'accoudoirs facturés.  S'il n'y a pas de dimensions,
    # revenir au compteur simple.
    nb_accoudoirs = len(dims_accoudoirs) if dims_accoudoirs else int(data.get('nb_accoudoirs') or 0)
    accoudoir_total = nb_accoudoirs * 200.0
    details: List[Dict[str, object]] = []
    # Détails mousse et tissu par coussin droit
    for idx, (length, width) in enumerate(dims, start=1):
        foam_price = (length * width * epaisseur_val * density * 23.0) / 1_000_000.0
        details.append({
            'category': 'foam',
            'item': f'Mousse droite {idx} ({length}×{width} cm)',
            'quantity': 1,
            'unit_price': round(foam_price, 2),
            'formula': f'({length}*{width}*{epaisseur_val}*{density}*23)/1 000 000',
            'total_price': round(foam_price, 2)
        })
        if (width + (epaisseur_val * 2)) > 140:
            fabric_unit = (length / 100.0) * 105.0
            fabric_formula = f'({length}/100)*105'
        else:
            fabric_unit = (length / 100.0) * 74.0
            fabric_formula = f'({length}/100)*74'
        details.append({
            'category': 'fabric',
            'item': f'Tissu droite {idx} ({length}×{width} cm)',
            'quantity': 1,
            'unit_price': round(fabric_unit, 2),
            'formula': fabric_formula,
            'total_price': round(fabric_unit, 2)
        })
    # Détails mousse et tissu pour coussins d’angle
    for idx, (length, width) in enumerate(dims_angle, start=1):
        foam_price = (length * width * epaisseur_val * density * 23.0) / 1_000_000.0
        details.append({
            'category': 'foam',
            'item': f'Mousse angle {idx} ({length}×{width} cm)',
            'quantity': 1,
            'unit_price': round(foam_price, 2),
            'formula': f'({length}*{width}*{epaisseur_val}*{density}*23)/1 000 000',
            'total_price': round(foam_price, 2)
        })
        if (width + (epaisseur_val * 2)) > 140:
            fabric_unit = (length / 100.0) * 105.0
            fabric_formula = f'({length}/100)*105'
        else:
            fabric_unit = (length / 100.0) * 74.0
            fabric_formula = f'({length}/100)*74'
        details.append({
            'category': 'fabric',
            'item': f'Tissu angle {idx} ({length}×{width} cm)',
            'quantity': 1,
            'unit_price': round(fabric_unit, 2),
            'formula': fabric_formula,
            'total_price': round(fabric_unit, 2)
        })
    # Supports détaillés individuels : une ligne par banquette droite ou d’angle.
    # Lorsque les dimensions sont connues, on indique la taille exacte ; sinon,
    # on génère des lignes génériques en se basant sur le nombre de banquettes.
    if dims:
        for idx, (length, width) in enumerate(dims, start=1):
            details.append({
                'category': 'support',
                'item': f'Banquette droite {idx} ({length}×{width} cm)',
                'quantity': 1,
                'unit_price': 250.0,
                'formula': '250 €/banquette',
                'total_price': 250.0
            })
    elif nb_banquettes > 0:
        for idx in range(1, nb_banquettes + 1):
            details.append({
                'category': 'support',
                'item': f'Banquette droite {idx}',
                'quantity': 1,
                'unit_price': 250.0,
                'formula': '250 €/banquette',
                'total_price': 250.0
            })
    if dims_angle:
        for idx, (length, width) in enumerate(dims_angle, start=1):
            details.append({
                'category': 'support',
                'item': f'Banquette d’angle {idx} ({length}×{width} cm)',
                'quantity': 1,
                'unit_price': 250.0,
                'formula': '250 €/angle',
                'total_price': 250.0
            })
    elif nb_banquettes_angle > 0:
        for idx in range(1, nb_banquettes_angle + 1):
            details.append({
                'category': 'support',
                'item': f'Banquette d’angle {idx}',
                'quantity': 1,
                'unit_price': 250.0,
                'formula': '250 €/angle',
                'total_price': 250.0
            })
    # Dossiers
    if dims_dossiers:
        for idx, (L_dos, P_dos) in enumerate(dims_dossiers, start=1):
            # Si la longueur du dossier est <= 110 cm, la quantité est réduite de moitié
            qty_dos = 0.5 if L_dos <= 110.0 else 1.0
            details.append({
                'category': 'support',
                'item': f'Dossier {idx} ({int(L_dos)}×{int(P_dos)} cm)',
                'quantity': qty_dos,
                'unit_price': 250.0,
                'formula': '250 €/dossier',
                'total_price': round(250.0 * qty_dos, 2)
            })
    else:
        # Si aucune dimension n'est disponible, on suppose une quantité pleine
        for idx in range(nb_dossiers):
            details.append({
                'category': 'support',
                'item': f'Dossier {idx+1}',
                'quantity': 1,
                'unit_price': 250.0,
                'formula': '250 €/dossier',
                'total_price': 250.0
            })
    # Accoudoirs : utiliser les dimensions détectées si disponibles, sinon un format générique
    if dims_accoudoirs:
        for idx, (L_acc, P_acc) in enumerate(dims_accoudoirs, start=1):
            details.append({
                'category': 'accoudoir',
                'item': f'Accoudoir {idx} ({int(L_acc)}×{int(P_acc)} cm)',
                'quantity': 1,
                'unit_price': 200.0,
                'formula': '200 €/accoudoir',
                'total_price': 200.0
            })
    else:
        for idx in range(nb_accoudoirs):
            details.append({
                'category': 'accoudoir',
                'item': f'Accoudoir {idx+1} (15×60 cm)',
                'quantity': 1,
                'unit_price': 200.0,
                'formula': '200 €/accoudoir',
                'total_price': 200.0
            })
    # Coussins détaillés
    if nb_coussins_65 > 0:
        details.append({
            'category': 'cushion',
            'item': 'Coussin 65 cm',
            'quantity': nb_coussins_65,
            'unit_price': 40.0,
            'formula': '40 €/coussin 65cm',
            'total_price': round(nb_coussins_65 * 40.0, 2)
        })
    if nb_coussins_80 > 0:
        details.append({
            'category': 'cushion',
            'item': 'Coussin 80 cm',
            'quantity': nb_coussins_80,
            'unit_price': 50.0,
            'formula': '50 €/coussin 80cm',
            'total_price': round(nb_coussins_80 * 50.0, 2)
        })
    if nb_coussins_90 > 0:
        details.append({
            'category': 'cushion',
            'item': 'Coussin 90 cm',
            'quantity': nb_coussins_90,
            'unit_price': 55.0,
            'formula': '55 €/coussin 90cm',
            'total_price': round(nb_coussins_90 * 55.0, 2)
        })
    if nb_coussins_valise > 0:
        details.append({
            'category': 'cushion',
            'item': 'Coussin valise',
            'quantity': nb_coussins_valise,
            'unit_price': 75.0,
            'formula': '75 €/coussin valise',
            'total_price': round(nb_coussins_valise * 75.0, 2)
        })
    if nb_coussins_deco > 0:
        details.append({
            'category': 'cushion',
            'item': 'Coussin déco',
            'quantity': nb_coussins_deco,
            'unit_price': 15.0,
            'formula': '15 €/coussin déco',
            'total_price': round(nb_coussins_deco * 15.0, 2)
        })
    # Traversins détaillés
    if nb_traversins > 0:
        details.append({
            'category': 'traversin',
            'item': 'Traversin',
            'quantity': nb_traversins,
            'unit_price': 30.0,
            'formula': '30 €/traversin',
            'total_price': round(nb_traversins * 30.0, 2)
        })
    # Surmatelas détaillés
    if nb_surmatelas > 0:
        details.append({
            'category': 'surmatelas',
            'item': 'Surmatelas',
            'quantity': nb_surmatelas,
            'unit_price': 80.0,
            'formula': '80 €/surmatelas',
            'total_price': round(nb_surmatelas * 80.0, 2)
        })
    # Accoudoirs détaillés
    # Les accoudoirs sont déjà ajoutés un par un plus haut (avec ou sans dimensions).
    # On ne rajoute donc pas de ligne agrégée ici afin d'éviter un doublon.
    if nb_accoudoirs > 0:
        pass
    # Arrondis
    arrondis_units = 0
    arrondis_total = 0.0
    if arrondis:
        arrondis_units = nb_banquettes + nb_banquettes_angle
        arrondis_total = arrondis_units * 20.0
        details.append({
            'category': 'arrondis',
            'item': 'Arrondi',
            'quantity': arrondis_units,
            'unit_price': 20.0,
            'formula': '20 €/banquette ou angle',
            'total_price': round(arrondis_total, 2)
        })

  # Surplus / Ajustement
    if surplus > 0:
        details.append({
            'category': 'Autre',  # Catégorie demandée
            'item': 'Autre',
            'quantity': 1,
            'unit_price': float(surplus),
            'formula': 'Forfait',
            'total_price': float(surplus)
        })

    # Total TTC (somme de tous les composants + surplus)
    total_ttc = (foam_total + fabric_total + support_total + cushion_total +
                 traversin_total + surmatelas_total + accoudoir_total + arrondis_total + surplus)
    prix_ht = round(total_ttc / 1.20, 2)
    tva = round(total_ttc - prix_ht, 2)
    # Le coût de revient initial basé sur 70 % du HT n'est plus utilisé :
    cout_revient_ht = round(prix_ht * 0.70, 2)  # conservé pour compatibilité mais remplacé plus bas
    # === Calcul du coût de revient détaillé (HT) ===
    # Coût de revient de la mousse selon la densité : coefficients spécifiques
    density_coeff_map = {
        'D25': 157.5,
        'D30': 188.0,
        'HR35': 192.0,
        'HR45': 245.0,
    }
    coeff_cr = density_coeff_map.get(type_mousse or 'D25', density_coeff_map['D25'])
    cr_foam_total = 0.0
    cr_fabric_total = 0.0
    cr_details: List[Dict[str, object]] = []
    # Coût de revient mousse et tissu pour chaque coussin droit
    for idx, (length, width) in enumerate(dims, start=1):
        # Déterminer si la dimension correspond à une mousse standard avec tarif fixe
        std_key = (int(round(length)), int(round(width)))
        # Détermination des prix standard pour les mousses de 25 cm ou 30 cm d'épaisseur
        std_prices_25 = {
            (200, 70): {'D25': 42.55, 'D30': 51.0, 'HR35': 65.0, 'HR45': 84.0},
            (200, 80): {'D25': 63.0, 'D30': 75.2, 'HR35': 76.2, 'HR45': 98.0},
            (90, 90): {'D25': 31.9, 'D30': 38.1, 'HR35': 38.9, 'HR45': 49.6},
            (100, 100): {'D25': 39.3, 'D30': 47.0, 'HR35': 48.0, 'HR45': 61.20}
        }
        std_prices_30 = {
            (200, 70): {'D25': 51.30, 'D30': 61.30, 'HR35': 78.00, 'HR45': 100.80},
            # Pas de tarif 30 cm fourni pour 200×80 : utiliser la formule générale.
            (90, 90): {'D25': 38.30, 'D30': 45.70, 'HR35': 46.60, 'HR45': 59.50},
            (100, 100): {'D25': 47.10, 'D30': 56.40, 'HR35': 57.60, 'HR45': 73.50}
        }
        std_fabric_prices = {
            (200, 70): 34.40, (200, 80): 34.40, (90, 90): 28.40, (100, 100): 28.40
        }
        cr_foam = None
        cr_fabric = None
        cr_formula_foam = ''
        cr_formula_fabric = ''
        if epaisseur_val == 25.0 and std_key in std_prices_25:
            # Utiliser les tarifs fixes pour 25 cm d'épaisseur
            foam_price_std = std_prices_25[std_key].get(type_mousse or 'D25', std_prices_25[std_key]['D25'])
            fabric_price_std = std_fabric_prices.get(std_key, 28.40)
            cr_foam = foam_price_std
            cr_fabric = fabric_price_std
            cr_formula_foam = 'prix standard'
            cr_formula_fabric = 'prix standard'
        elif epaisseur_val == 30.0 and std_key in std_prices_30:
            # Tarifs fixes pour 30 cm d'épaisseur (mousse uniquement)
            foam_price_std = std_prices_30[std_key].get(type_mousse or 'D25', std_prices_30[std_key]['D25'])
            # Le coût de tissu standard reste identique aux autres épaisseurs
            fabric_price_std = std_fabric_prices.get(std_key, 28.40)
            cr_foam = foam_price_std
            cr_fabric = fabric_price_std
            cr_formula_foam = 'prix standard'
            cr_formula_fabric = 'prix standard'
        # Si aucune correspondance de taille standard, utiliser la formule générale
        if cr_foam is None:
            cr_foam = (length * width * epaisseur_val) / 1_000_000.0 * coeff_cr
            cr_formula_foam = f'({length}*{width}*{epaisseur_val})/1 000 000*{coeff_cr}'
        if cr_fabric is None:
            if (2.0 + width + epaisseur_val * 2.0) <= 140.0:
                cr_fabric = (length / 100.0) * 11.2 + 15.0
                cr_formula_fabric = f'({length}/100)*11.2+15'
            else:
                cr_fabric = (length / 100.0) * 16.16 + 15.0
                cr_formula_fabric = f'({length}/100)*16.16+15'
        cr_foam_total += cr_foam
        cr_details.append({
            'category': 'foam',
            'item': f'Mousse droite {idx} ({length}×{width} cm)',
            'quantity': 1,
            'unit_price': round(cr_foam, 2),
            'formula': cr_formula_foam,
            'total_price': round(cr_foam, 2)
        })
        cr_fabric_total += cr_fabric
        cr_details.append({
            'category': 'fabric',
            'item': f'Tissu droite {idx} ({length}×{width} cm)',
            'quantity': 1,
            'unit_price': round(cr_fabric, 2),
            'formula': cr_formula_fabric,
            'total_price': round(cr_fabric, 2)
        })
    # Coût de revient mousse et tissu pour les coussins d’angle
    for idx, (length, width) in enumerate(dims_angle, start=1):
        # Déterminer si la dimension d'angle est standard
        std_key = (int(round(length)), int(round(width)))
        is_std_size = (epaisseur_val == 25.0) and std_key in {
            (200, 70), (200, 80), (90, 90), (100, 100)
        }
        if is_std_size:
            std_foam_prices = {
                (200, 70): {'D25': 42.55, 'D30': 51.0, 'HR35': 65.0, 'HR45': 84.0},
                (200, 80): {'D25': 63.0, 'D30': 75.2, 'HR35': 76.2, 'HR45': 98.0},
                (90, 90): {'D25': 31.9, 'D30': 38.1, 'HR35': 38.9, 'HR45': 49.6},
                (100, 100): {'D25': 39.3, 'D30': 47.0, 'HR35': 48.0, 'HR45': 61.20}
            }
            std_fabric_prices = {
                (200, 70): 34.40, (200, 80): 34.40, (90, 90): 28.40, (100, 100): 28.40
            }
            cr_foam = std_foam_prices[std_key].get(type_mousse or 'D25', std_foam_prices[std_key]['D25'])
            cr_fabric = std_fabric_prices[std_key]
            cr_formula_foam = 'prix standard'
            cr_formula_fabric = 'prix standard'
        else:
            cr_foam = (length * width * epaisseur_val) / 1_000_000.0 * coeff_cr
            cr_formula_foam = f'({length}*{width}*{epaisseur_val})/1 000 000*{coeff_cr}'
            if (2.0 + width + epaisseur_val * 2.0) <= 140.0:
                cr_fabric = (length / 100.0) * 11.2 + 15.0
                cr_formula_fabric = f'({length}/100)*11.2+15'
            else:
                cr_fabric = (length / 100.0) * 16.16 + 15.0
                cr_formula_fabric = f'({length}/100)*16.16+15'
        cr_foam_total += cr_foam
        cr_details.append({
            'category': 'foam',
            'item': f'Mousse angle {idx} ({length}×{width} cm)',
            'quantity': 1,
            'unit_price': round(cr_foam, 2),
            'formula': cr_formula_foam,
            'total_price': round(cr_foam, 2)
        })
        cr_fabric_total += cr_fabric
        cr_details.append({
            'category': 'fabric',
            'item': f'Tissu angle {idx} ({length}×{width} cm)',
            'quantity': 1,
            'unit_price': round(cr_fabric, 2),
            'formula': cr_formula_fabric,
            'total_price': round(cr_fabric, 2)
        })
    # Coût de revient des supports (banquettes, angles et dossiers) avec une ligne par élément
    cr_support_total = 0.0
    # Banquettes droites : coût unitaire selon la longueur
    for idx, (length, width) in enumerate(dims, start=1):
        if length <= 200.0:
            cr_sup = 93.0 + 8.0 * 2.5
            cr_sup_formula = '93+8*2.5'
        else:
            cr_sup = 98.5 + 22.5
            cr_sup_formula = '98.5+22.5'
        cr_support_total += cr_sup
        cr_details.append({
            'category': 'support',
            'item': f'Banquette droite {idx} ({length}×{width} cm)',
            'quantity': 1,
            'unit_price': round(cr_sup, 2),
            'formula': cr_sup_formula,
            'total_price': round(cr_sup, 2)
        })
    # Banquettes d’angle : coût unitaire constant pour chaque pièce
    for idx, (length, width) in enumerate(dims_angle, start=1):
        cr_sup_angle_unit = 93.0 + 8.0 * 1.4
        cr_support_total += cr_sup_angle_unit
        cr_details.append({
            'category': 'support',
            'item': f'Banquette d’angle {idx} ({length}×{width} cm)',
            'quantity': 1,
            'unit_price': round(cr_sup_angle_unit, 2),
            'formula': '93+8*1.4',
            'total_price': round(cr_sup_angle_unit, 2)
        })
    # Dossiers : coût de revient variable selon la longueur
    cr_dossier_total = 0.0
    if dims_dossiers:
        for idx, (L_dos, P_dos) in enumerate(dims_dossiers, start=1):
            # Déterminer la quantité (0,5 pour les dossiers <= 110 cm)
            qty_dos = 0.5 if L_dos <= 110.0 else 1.0
            # Coût unitaire selon la longueur (hors réduction de quantité)
            if L_dos <= 110.0:
                # Base : 120 + 8×4,4 = 155,2 ; total ramené à la moitié via qty_dos
                cr_unit = 120.0 + 8.0 * 4.4
                cr_formula = '120+8*4.4'
            elif L_dos <= 200.0:
                cr_unit = 120.0 + 8.0 * 4.4
                cr_formula = '120+8*4.4'
            else:
                cr_unit = 132.0 + 8.0 * 5.5
                cr_formula = '132+8*5.5'
            total_price = cr_unit * qty_dos
            cr_dossier_total += total_price
            cr_details.append({
                'category': 'support',
                'item': f'Dossier {idx} ({int(L_dos)}×{int(P_dos)} cm)',
                'quantity': qty_dos,
                'unit_price': round(cr_unit, 2),
                'formula': cr_formula,
                'total_price': round(total_price, 2)
            })
    # Si aucune dimension n'a été détectée mais que des dossiers sont présents,
    # générer des lignes génériques en supposant des dossiers « longs » (>110 cm)
    if not dims_dossiers and nb_dossiers > 0:
        cr_unit = 120.0 + 8.0 * 4.4  # Par défaut, utiliser la formule 120+8*4.4 (155,2)
        cr_formula = '120+8*4.4'
        for idx in range(nb_dossiers):
            qty_dos = 1.0
            total_price = cr_unit * qty_dos
            cr_dossier_total += total_price
            cr_details.append({
                'category': 'support',
                'item': f'Dossier {idx+1}',
                'quantity': qty_dos,
                'unit_price': round(cr_unit, 2),
                'formula': cr_formula,
                'total_price': round(total_price, 2)
            })
    # Coût de revient des accoudoirs : une ligne par accoudoir
    cr_accoudoir_total = 0.0
    if dims_accoudoirs:
        for idx, (L_acc, P_acc) in enumerate(dims_accoudoirs, start=1):
            cr_accoudoir_total += 73.0
            cr_details.append({
                'category': 'accoudoir',
                'item': f'Accoudoir {idx} ({int(L_acc)}×{int(P_acc)} cm)',
                'quantity': 1,
                'unit_price': 73.0,
                'formula': '73',
                'total_price': 73.0
            })
    else:
        for idx in range(nb_accoudoirs):
            cr_accoudoir_total += 73.0
            cr_details.append({
                'category': 'accoudoir',
                'item': f'Accoudoir {idx+1} (15×60 cm)',
                'quantity': 1,
                'unit_price': 73.0,
                'formula': '73',
                'total_price': 73.0
            })
    # Coût de revient des coussins (assise et déco) et autres accessoires
    cr_cushion_total = 0.0
    if nb_coussins_65 > 0:
        cr_cushion_total += nb_coussins_65 * 14.0
        cr_details.append({
            'category': 'cushion',
            'item': 'Coussin 65 cm',
            'quantity': nb_coussins_65,
            'unit_price': 14.0,
            'formula': '14',
            'total_price': round(nb_coussins_65 * 14.0, 2)
        })
    if nb_coussins_80 > 0:
        cr_cushion_total += nb_coussins_80 * 17.0
        cr_details.append({
            'category': 'cushion',
            'item': 'Coussin 80 cm',
            'quantity': nb_coussins_80,
            'unit_price': 17.0,
            'formula': '17',
            'total_price': round(nb_coussins_80 * 17.0, 2)
        })
    if nb_coussins_90 > 0:
        cr_cushion_total += nb_coussins_90 * 17.5
        cr_details.append({
            'category': 'cushion',
            'item': 'Coussin 90 cm',
            'quantity': nb_coussins_90,
            'unit_price': 17.5,
            'formula': '17.5',
            'total_price': round(nb_coussins_90 * 17.5, 2)
        })
    if nb_coussins_valise > 0:
        cr_cushion_total += nb_coussins_valise * 25.0
        cr_details.append({
            'category': 'cushion',
            'item': 'Coussin valise',
            'quantity': nb_coussins_valise,
            'unit_price': 25.0,
            'formula': '25',
            'total_price': round(nb_coussins_valise * 25.0, 2)
        })
    # Coussins déco
    cr_deco_total = nb_coussins_deco * 9.5
    if nb_coussins_deco > 0:
        cr_details.append({
            'category': 'cushion',
            'item': 'Coussin déco',
            'quantity': nb_coussins_deco,
            'unit_price': 9.5,
            'formula': '9.5',
            'total_price': round(cr_deco_total, 2)
        })
    # Traversins
    cr_traversin_total = nb_traversins * 11.6
    if nb_traversins > 0:
        cr_details.append({
            'category': 'traversin',
            'item': 'Traversin',
            'quantity': nb_traversins,
            'unit_price': 11.6,
            'formula': '11.6',
            'total_price': round(cr_traversin_total, 2)
        })
    # Surmatelas
    cr_surmatelas_total = nb_surmatelas * 31.0
    if nb_surmatelas > 0:
        cr_details.append({
            'category': 'surmatelas',
            'item': 'Surmatelas',
            'quantity': nb_surmatelas,
            'unit_price': 31.0,
            'formula': '31',
            'total_price': round(cr_surmatelas_total, 2)
        })
    # Arrondis
    cr_arrondis_total = 0.0
    cr_arrondis_units = 0
    if arrondis:
        cr_arrondis_units = nb_banquettes + nb_banquettes_angle
        cr_arrondis_total = cr_arrondis_units * 6.05
        cr_details.append({
            'category': 'arrondis',
            'item': 'Arrondi',
            'quantity': cr_arrondis_units,
            'unit_price': 6.05,
            'formula': '6.05',
            'total_price': round(cr_arrondis_total, 2)
        })
    # Livraison : coût de revient fixe de 100€
    cr_delivery_total = 100.0
    # Pieds : 12 € par banquette droite ou d’angle (prix de revient)
    cr_pieds_total = (nb_banquettes + nb_banquettes_angle) * 12.0
    if (nb_banquettes + nb_banquettes_angle) > 0:
        cr_details.append({
            'category': 'pieds',
            'item': 'Pieds',
            'quantity': nb_banquettes + nb_banquettes_angle,
            'unit_price': 12.0,
            'formula': '12',
            'total_price': round(cr_pieds_total, 2)
        })
    # Livraison (coût de revient) selon le département
    # Si le département n'est pas fourni, appliquer 200 € par défaut
    cr_delivery_unit = 200.0
    try:
        if departement_livraison is not None:
            dep = int(str(departement_livraison).strip())
            if dep == 62:
                cr_delivery_unit = 100.0
            elif dep in (59, 80):
                cr_delivery_unit = 150.0
            elif dep in (75, 77, 78, 91, 92, 93, 94, 95):
                cr_delivery_unit = 200.0
            else:
                cr_delivery_unit = 300.0
    except Exception:
        # En cas d'erreur de conversion, rester sur la valeur par défaut
        cr_delivery_unit = 200.0
    cr_delivery_total = cr_delivery_unit
    cr_details.append({
        'category': 'livraison',
        'item': 'Livraison',
        'quantity': 1,
        'unit_price': round(cr_delivery_unit, 2),
        'formula': str(int(cr_delivery_unit)),
        'total_price': round(cr_delivery_unit, 2)
    })
    # Total coût de revient HT : addition de toutes les composantes sans double comptage
    cr_total_ht = (
        cr_foam_total + cr_fabric_total +
        cr_support_total + cr_dossier_total + cr_accoudoir_total +
        cr_cushion_total + cr_deco_total + cr_traversin_total +
        cr_surmatelas_total + cr_arrondis_total + cr_pieds_total + cr_delivery_total
    )

    # Recalculer la marge HT : marge = prix de vente TTC / 1.2 - coût de revient HT
    marge_ht = round((total_ttc / 1.20) - cr_total_ht, 2)


    # Mettre à jour le coût de revient HT avec le calcul réel (écrase la version 70 %)
    cout_revient_ht = round(cr_total_ht, 2)
    # Marge HT = prix HT - coût de revient HT
    # Ajouter une ligne de marge dans les détails du coût de revient
    # La marge est calculée comme (Prix TTC / 1,2) - coût de revient total HT
    cr_details.append({
        'category': 'marge',
        'item': 'Marge HT',
        'quantity': 1,
        'unit_price': round(marge_ht, 2),
        'formula': '(Prix TTC/1,2) - coût de revient HT',
        'total_price': round(marge_ht, 2)
    })

    # === Calcul du prix usine (détail et totaux) ===
    # Cette section génère un tableau HT pour une facturation usine.  Les
    # tarifs utilisés reprennent ceux spécifiés dans la description
    # utilisateur et sont appliqués indépendamment de la marge.  Le total TTC
    # usine est simplement le total HT multiplié par 1,20.
    usine_details: List[Dict[str, object]] = []
    usine_ht_total = 0.0

    # Coefficients de densité pour le calcul des mousses usine (identiques au coût de revient)
    density_coeff_map_usine = {
        'D25': 157.5,
        'D30': 188.0,
        'HR35': 192.0,
        'HR45': 245.0,
    }
    coeff_usine = density_coeff_map_usine.get(type_mousse or 'D25', density_coeff_map_usine['D25'])
    # Tarifs fixes pour les mousses de 25 cm d'épaisseur
    std_prices_usine_25 = {
        (200, 70): {'D25': 42.55, 'D30': 51.0, 'HR35': 65.0, 'HR45': 84.0},
        (200, 80): {'D25': 63.0, 'D30': 75.2, 'HR35': 76.2, 'HR45': 98.0},
        (90, 90): {'D25': 31.9, 'D30': 38.1, 'HR35': 38.9, 'HR45': 49.6},
        (100, 100): {'D25': 39.3, 'D30': 47.0, 'HR35': 48.0, 'HR45': 61.20}
    }
    # Tarifs fixes pour les mousses de 30 cm d'épaisseur
    std_prices_usine_30 = {
        (200, 70): {'D25': 51.30, 'D30': 61.30, 'HR35': 78.00, 'HR45': 100.80},
        (90, 90): {'D25': 38.30, 'D30': 45.70, 'HR35': 46.60, 'HR45': 59.50},
        (100, 100): {'D25': 47.10, 'D30': 56.40, 'HR35': 57.60, 'HR45': 73.50}
    }
    # Parcours des mousses droites
    for idx, (length, width) in enumerate(dims, start=1):
        std_key = (int(round(length)), int(round(width)))
        foam_price = None
        formula_foam = ''
        if epaisseur_val == 25.0 and std_key in std_prices_usine_25:
            foam_price = std_prices_usine_25[std_key].get(type_mousse or 'D25', std_prices_usine_25[std_key]['D25'])
            formula_foam = 'prix standard'
        elif epaisseur_val == 30.0 and std_key in std_prices_usine_30:
            foam_price = std_prices_usine_30[std_key].get(type_mousse or 'D25', std_prices_usine_30[std_key]['D25'])
            formula_foam = 'prix standard'
        if foam_price is None:
            foam_price = (length * width * epaisseur_val) / 1_000_000.0 * coeff_usine
            formula_foam = f'({length}*{width}*{epaisseur_val})/1 000 000*{coeff_usine}'
        usine_ht_total += foam_price
        usine_details.append({
            'category': 'mousse',
            'item': f'Mousse droite {idx} ({int(length)}×{int(width)} cm)',
            'quantity': 1,
            'unit_price': round(foam_price, 2),
            'formula': formula_foam,
            'total_price': round(foam_price, 2)
        })
        # Tissu pour mousse droite : tarif fixe 15 €
        usine_ht_total += 15.0
        usine_details.append({
            'category': 'tissu',
            'item': f'Tissu droite {idx} ({int(length)}×{int(width)} cm)',
            'quantity': 1,
            'unit_price': 15.0,
            'formula': '15',
            'total_price': 15.0
        })
    # Parcours des mousses d’angle
    for idx, (length, width) in enumerate(dims_angle, start=1):
        std_key = (int(round(length)), int(round(width)))
        foam_price = None
        formula_foam = ''
        if epaisseur_val == 25.0 and std_key in std_prices_usine_25:
            foam_price = std_prices_usine_25[std_key].get(type_mousse or 'D25', std_prices_usine_25[std_key]['D25'])
            formula_foam = 'prix standard'
        elif epaisseur_val == 30.0 and std_key in std_prices_usine_30:
            foam_price = std_prices_usine_30[std_key].get(type_mousse or 'D25', std_prices_usine_30[std_key]['D25'])
            formula_foam = 'prix standard'
        if foam_price is None:
            foam_price = (length * width * epaisseur_val) / 1_000_000.0 * coeff_usine
            formula_foam = f'({length}*{width}*{epaisseur_val})/1 000 000*{coeff_usine}'
        usine_ht_total += foam_price
        usine_details.append({
            'category': 'mousse',
            'item': f'Mousse angle {idx} ({int(length)}×{int(width)} cm)',
            'quantity': 1,
            'unit_price': round(foam_price, 2),
            'formula': formula_foam,
            'total_price': round(foam_price, 2)
        })
        # Tissu pour mousse d’angle
        usine_ht_total += 15.0
        usine_details.append({
            'category': 'tissu',
            'item': f'Tissu angle {idx} ({int(length)}×{int(width)} cm)',
            'quantity': 1,
            'unit_price': 15.0,
            'formula': '15',
            'total_price': 15.0
        })
    # Supports : banquettes droites
    for idx, (length, _width) in enumerate(dims, start=1):
        unit = 93.0 if length <= 200.0 else 98.5
        usine_ht_total += unit
        usine_details.append({
            'category': 'support',
            'item': f'Banquette droite {idx}',
            'quantity': 1,
            'unit_price': round(unit, 2),
            'formula': f'{unit}',
            'total_price': round(unit, 2)
        })
    # Supports : banquettes d’angle
    for idx, (_length, _width) in enumerate(dims_angle, start=1):
        unit = 93.0
        usine_ht_total += unit
        usine_details.append({
            'category': 'support',
            'item': f'Banquette angle {idx}',
            'quantity': 1,
            'unit_price': round(unit, 2),
            'formula': '93',
            'total_price': round(unit, 2)
        })
    # Supports : dossiers
    if dims_dossiers:
        for idx, (L_dos, _P_dos) in enumerate(dims_dossiers, start=1):
            if L_dos <= 110.0:
                qty = 0.5
                unit_price = 60.0
            elif L_dos <= 200.0:
                qty = 1.0
                unit_price = 120.0
            else:
                qty = 1.0
                unit_price = 132.0
            total = qty * unit_price
            usine_ht_total += total
            usine_details.append({
                'category': 'support',
                'item': f'Dossier {idx}',
                'quantity': qty,
                'unit_price': round(unit_price, 2),
                'formula': f'{unit_price}',
                'total_price': round(total, 2)
            })
    else:
        # Si aucune dimension n'est connue, prendre une valeur par défaut par dossier
        for idx in range(nb_dossiers):
            qty = 1.0
            unit_price = 120.0
            total = qty * unit_price
            usine_ht_total += total
            usine_details.append({
                'category': 'support',
                'item': f'Dossier {idx+1}',
                'quantity': qty,
                'unit_price': round(unit_price, 2),
                'formula': f'{unit_price}',
                'total_price': round(total, 2)
            })
    # Supports : accoudoirs
    if dims_accoudoirs:
        for idx, (_L_acc, _P_acc) in enumerate(dims_accoudoirs, start=1):
            unit_price = 65.0
            usine_ht_total += unit_price
            usine_details.append({
                'category': 'support',
                'item': f'Accoudoir {idx}',
                'quantity': 1,
                'unit_price': round(unit_price, 2),
                'formula': '65',
                'total_price': round(unit_price, 2)
            })
    else:
        for idx in range(nb_accoudoirs):
            unit_price = 65.0
            usine_ht_total += unit_price
            usine_details.append({
                'category': 'support',
                'item': f'Accoudoir {idx+1}',
                'quantity': 1,
                'unit_price': round(unit_price, 2),
                'formula': '65',
                'total_price': round(unit_price, 2)
            })
    # Coussins d’assise
    if nb_coussins_65 > 0:
        cost = 10.0
        total = nb_coussins_65 * cost
        usine_ht_total += total
        usine_details.append({
            'category': 'coussin',
            'item': 'Coussin 65 cm',
            'quantity': nb_coussins_65,
            'unit_price': round(cost, 2),
            'formula': '10',
            'total_price': round(total, 2)
        })
    if nb_coussins_80 > 0:
        cost = 12.0
        total = nb_coussins_80 * cost
        usine_ht_total += total
        usine_details.append({
            'category': 'coussin',
            'item': 'Coussin 80 cm',
            'quantity': nb_coussins_80,
            'unit_price': round(cost, 2),
            'formula': '12',
            'total_price': round(total, 2)
        })
    if nb_coussins_90 > 0:
        cost = 12.0
        total = nb_coussins_90 * cost
        usine_ht_total += total
        usine_details.append({
            'category': 'coussin',
            'item': 'Coussin 90 cm',
            'quantity': nb_coussins_90,
            'unit_price': round(cost, 2),
            'formula': '12',
            'total_price': round(total, 2)
        })
    if nb_coussins_valise > 0:
        cost = 17.0
        total = nb_coussins_valise * cost
        usine_ht_total += total
        usine_details.append({
            'category': 'coussin',
            'item': 'Coussin valise',
            'quantity': nb_coussins_valise,
            'unit_price': round(cost, 2),
            'formula': '17',
            'total_price': round(total, 2)
        })
    # Coussins déco
    if nb_coussins_deco > 0:
        cost = 7.0
        total = nb_coussins_deco * cost
        usine_ht_total += total
        usine_details.append({
            'category': 'coussin',
            'item': 'Coussin déco',
            'quantity': nb_coussins_deco,
            'unit_price': round(cost, 2),
            'formula': '7',
            'total_price': round(total, 2)
        })
    # Traversins
    if nb_traversins > 0:
        cost = 7.60
        total = nb_traversins * cost
        usine_ht_total += total
        usine_details.append({
            'category': 'traversin',
            'item': 'Traversin',
            'quantity': nb_traversins,
            'unit_price': round(cost, 2),
            'formula': '7.60',
            'total_price': round(total, 2)
        })
    # Surmatelas
    if nb_surmatelas > 0:
        cost = 15.0
        total = nb_surmatelas * cost
        usine_ht_total += total
        usine_details.append({
            'category': 'surmatelas',
            'item': 'Surmatelas',
            'quantity': nb_surmatelas,
            'unit_price': round(cost, 2),
            'formula': '15',
            'total_price': round(total, 2)
        })
    # Arrondis
    if arrondis:
        nb_arrondis_units = nb_banquettes + nb_banquettes_angle
        if nb_arrondis_units > 0:
            cost = 6.0
            total = nb_arrondis_units * cost
            usine_ht_total += total
            usine_details.append({
                'category': 'arrondi',
                'item': 'Arrondi',
                'quantity': nb_arrondis_units,
                'unit_price': round(cost, 2),
                'formula': '6',
                'total_price': round(total, 2)
            })
    # Pieds
    nb_pieds = nb_banquettes + nb_banquettes_angle
    if nb_pieds > 0:
        cost = 12.0
        total = nb_pieds * cost
        usine_ht_total += total
        usine_details.append({
            'category': 'pieds',
            'item': 'Pieds',
            'quantity': nb_pieds,
            'unit_price': round(cost, 2),
            'formula': '12',
            'total_price': round(total, 2)
        })
    # Livraison (prix usine) : logique dépendant du département
    # Par défaut 200 €.  Si un département particulier est précisé, appliquer le tarif prévu.
    if departement_livraison:
        dep = str(departement_livraison).strip()
        if dep == '62':
            delivery_unit = 100.0
        elif dep in ('59', '80'):
            delivery_unit = 150.0
        elif dep in ('75','77','78','91','92','93','94','95'):
            delivery_unit = 200.0
        else:
            delivery_unit = 300.0
    else:
        delivery_unit = 200.0
    usine_ht_total += delivery_unit
    usine_details.append({
        'category': 'livraison',
        'item': 'Livraison',
        'quantity': 1,
        'unit_price': round(delivery_unit, 2),
        'formula': f'{delivery_unit}',
        'total_price': round(delivery_unit, 2)
    })

    usine_ttc_total = usine_ht_total * 1.20

    return {
        'prix_ht': prix_ht,
        'tva': tva,
        'total_ttc': round(total_ttc, 2),
        'surplus': surplus,
        'foam_total': round(foam_total, 2),
        'fabric_total': round(fabric_total, 2),
        'support_total': round(support_total, 2),
        'cushion_total': round(cushion_total, 2),
        'traversin_total': round(traversin_total, 2),
        'surmatelas_total': round(surmatelas_total, 2),
        'accoudoir_total': round(accoudoir_total, 2),
        'arrondis_total': round(arrondis_total, 2),
        'calculation_details': details,
        # --- Informations de coût de revient ---
        'cr_foam_total': round(cr_foam_total, 2),
        'cr_fabric_total': round(cr_fabric_total, 2),
        'cr_support_total': round(cr_support_total, 2),
        'cr_dossier_total': round(cr_dossier_total, 2),
        'cr_accoudoir_total': round(cr_accoudoir_total, 2),
        'cr_cushion_total': round(cr_cushion_total, 2),
        'cr_deco_total': round(cr_deco_total, 2),
        'cr_traversin_total': round(cr_traversin_total, 2),
        'cr_surmatelas_total': round(cr_surmatelas_total, 2),
        'cr_arrondis_total': round(cr_arrondis_total, 2),
        'cr_pieds_total': round(cr_pieds_total, 2),
        'cr_delivery_total': round(cr_delivery_total, 2),
        'cout_revient_ht': round(cr_total_ht, 2),
        'marge_ht': marge_ht,
        'calculation_details_cr': cr_details,
        # --- Informations de prix usine ---
        'calculation_details_usine': usine_details,
        'usine_ht_total': round(usine_ht_total, 2),
        'usine_ttc_total': round(usine_ttc_total, 2),
    }

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import re

IMG_W, IMG_H = 1240, 1754
MARGIN = 50
COLOR_TEXT = "black"

def load_fonts():
    candidates = ["DejaVuSans.ttf", "arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    font_path = next((c for c in candidates if os.path.exists(c)), None)
    try:
        if font_path:
            return {
                'bold': ImageFont.truetype(font_path, 24),
                'regular': ImageFont.truetype(font_path, 24),
                'small': ImageFont.truetype(font_path, 20),
                'italic': ImageFont.truetype(font_path, 22)
            }
    except: pass
    d = ImageFont.load_default()
    return {k: d for k in ['bold', 'regular', 'small', 'italic']}

FONTS = load_fonts()

def draw_text_box(draw, text, x, y, font, max_width):
    """Dessine texte multiline et retourne le nouveau Y"""
    words = text.split()
    lines = []
    cur = []
    for w in words:
        test = ' '.join(cur + [w])
        try: w_px = draw.textbbox((0,0), test, font=font)[2]
        except: w_px = len(test)*10
        if w_px <= max_width: cur.append(w)
        else: lines.append(' '.join(cur)); cur = [w]
    lines.append(' '.join(cur))
    
    curr_y = y
    for line in lines:
        draw.text((x, curr_y), line, font=font, fill=COLOR_TEXT)
        try: h = draw.textbbox((0,0), line, font=font)[3]
        except: h = 25
        curr_y += h + 8
    return curr_y

def generer_png_devis(config, prix_details, schema_image=None, breakdown_rows=None,
                      reduction_ttc=0.0, show_detail_devis=False, show_detail_cr=False):
    img = Image.new('RGB', (IMG_W, IMG_H), "white")
    draw = ImageDraw.Draw(img)
    y = MARGIN
    
    # 1. INFO CLIENT
    cl = config.get('client', {})
    for info in [f"Nom: {cl.get('nom','')}", f"Téléphone: {cl.get('telephone','')}"]:
        if info.split(": ")[1]: 
            draw.text((MARGIN, y), info, font=FONTS['regular'], fill=COLOR_TEXT)
            y += 35
    y += 20

    # 2. MOUSSE
    m_type = config.get('options', {}).get('type_mousse', 'HR35')
    desc_map = {
        'D25': "La mousse D25 (25kg/m3) est très ferme, style marocain classique.",
        'D30': "La mousse D30 (30kg/m3) est ultra ferme.",
        'HR35': "La mousse HR35 (35kg/m3) est semi-ferme confortable.\nHaute résilience.",
        'HR45': "La mousse HR45 (45kg/m3) est ferme confortable.\nHaute résilience."
    }
    icon_path = f"{m_type}.png"
    txt_x = MARGIN
    if os.path.exists(icon_path):
        try:
            icon = Image.open(icon_path).convert("RGBA")
            icon.thumbnail((100, 100))
            img.paste(icon, (MARGIN, y), icon)
            txt_x += 120
        except: pass
    y_desc = draw_text_box(draw, desc_map.get(m_type,""), txt_x, y, FONTS['italic'], IMG_W - txt_x - MARGIN)
    y = max(y + 110, y_desc + 40)

    # 3. SCHEMA
    if schema_image:
        try:
            s = Image.open(schema_image) if isinstance(schema_image, BytesIO) else schema_image
            ratio = min((IMG_W - 2*MARGIN)/s.width, 600/s.height)
            ns = (int(s.width*ratio), int(s.height*ratio))
            s = s.resize(ns, Image.Resampling.LANCZOS)
            img.paste(s, ((IMG_W - ns[0])//2, y))
            y += ns[1] + 40
        except Exception as e:
            draw.text((MARGIN, y), "(Erreur schéma)", font=FONTS['small'], fill="red"); y+=40

    # 4. TABLEAU DÉTAIL (LOGIQUE HARMONISÉE)
    draw.text((MARGIN, y), "Détail du devis :", font=FONTS['bold'], fill="black"); y += 40
    
    # Prép données
    dims = config.get('dimensions', {})
    tc = config.get('type_canape', '')
    d_str = f"{dims.get('ty',0)} x {dims.get('tx',0)} x {dims.get('tz',0)}" if "U" in tc else (f"{dims.get('ty',0)} x {dims.get('tx',0)}" if "L" in tc else f"{dims.get('tx',0)} x {dims.get('profondeur',0)}")
    
    # Coussins
    details = prix_details.get('calculation_details', [])
    c_counts = {}
    extras = []
    nb_assise = None
    if breakdown_rows:
        for r in breakdown_rows:
            if "Coussins assise" in str(r[0]): nb_assise = r[1]

    for e in details:
        c, i, q = e.get('category','').lower(), e.get('item','').lower(), e.get('quantity',0)
        if c == 'traversin' and q: extras.append(f"Traversins : {q} de 70x20cm")
        elif c == 'surmatelas' and q: extras.append(f"Surmatelas : {q} confort")
        elif c == 'cushion' and 'déco' in i and q: extras.append(f"Coussins déco : {q}")
        elif c == 'cushion':
            l = next((p.replace('cm','') + "cm" for p in i.split() if p.replace('cm','').isdigit()), None)
            if not l: l = 'valise' if 'valise' in i else ('petit' if 'petit' in i else ('grand' if 'grand' in i else None))
            if l: c_counts[l] = c_counts.get(l,0) + q
    
    tp_c = config.get('options',{}).get('type_coussins','auto')
    if tp_c in ['valise','p','g']:
        tot = nb_assise if nb_assise else sum(v for k,v in c_counts.items() if 'cm' not in k)
        c_str = f"{tot} coussins valises sur mesure"
    else:
        c_str = ", ".join([f"{v} x {k}" for k,v in sorted(c_counts.items())]) if c_counts else (f"{nb_assise} x ..." if nb_assise else "-")

    # Listes GAUCHE / DROITE
    opt = config['options']
    acc = "Avec" if opt.get('acc_left') or opt.get('acc_right') else "Sans"
    dos = "Avec" if opt.get('dossier_left') or opt.get('dossier_bas') or opt.get('dossier_right') else "Sans"
    
    items_L = [
        f"Dimensions : {d_str} cm",
        f"Mousse : {m_type}",
        f"Accoudoirs : {acc}",
        f"Dossiers : {dos}",
        f"Profondeur : {dims.get('profondeur',0)}cm"
    ]
    
    items_R = [f"{'Coussins valises' if tp_c in ['valise','p','g'] else 'Coussins'} : {c_str}"]
    items_R.extend(extras)
    reduc = float(reduction_ttc or 0.0)
    tot = float(prix_details.get('total_ttc',0.0))
    items_R.append(f"Réduction : {reduc:.2f} €")
    items_R.append(f"TAG_PRIX::{tot:.2f} €")
    items_R.append(f"Prix avant réduction : {(tot+reduc):.2f} €")

    # Dessin des lignes
    col_w = (IMG_W - 2*MARGIN) // 2
    cx1, cx2 = MARGIN, MARGIN + col_w
    
    max_rows = max(len(items_L), len(items_R))
    for i in range(max_rows):
        # Hauteur de base pour cette ligne
        line_start_y = y
        
        # Colonne G
        h_g = 0
        if i < len(items_L):
            draw.text((cx1, y), items_L[i], font=FONTS['regular'], fill=COLOR_TEXT)
            h_g = 35 # Hauteur standard texte simple
            
        # Colonne D
        h_d = 0
        if i < len(items_R):
            txt = items_R[i]
            if "TAG_PRIX::" in txt:
                # Prix en gras
                lbl = "Prix canapé : "
                draw.text((cx2, y), lbl, font=FONTS['regular'], fill=COLOR_TEXT)
                w_lbl = draw.textlength(lbl, font=FONTS['regular'])
                draw.text((cx2 + w_lbl, y), txt.replace("TAG_PRIX::",""), font=FONTS['bold'], fill="black")
                h_d = 35
            else:
                # Wrapping pour coussins longs
                end_y = draw_text_box(draw, txt, cx2, y, FONTS['regular'], col_w - 20)
                h_d = end_y - y

        # On avance Y du maximum des deux hauteurs pour garder l'alignement
        y += max(h_g, h_d, 35) + 10 # 10px padding entre lignes

    # 5. FOOTER
    fy = IMG_H - 280
    draw.text((cx1, fy), "Il faut savoir que le tarif comprend :", font=FONTS['bold'], fill=COLOR_TEXT)
    cy = fy + 35
    for it in ["Fabrication 100% artisanale France", "Choix du tissu n'impacte pas le devis", "Paiement 2 à 6 fois sans frais", "Livraison 5 à 7 semaines", "Housses déhoussables"]:
        draw.text((cx1, cy), f"• {it}", font=FONTS['small'], fill=COLOR_TEXT); cy+=25
        
    draw.text((cx2, fy), "Détail des cotations :", font=FONTS['bold'], fill=COLOR_TEXT)
    cy = fy + 35
    hm = opt.get('epaisseur', 25)
    ha = 46 if hm>20 else 40
    for it in ["Accoudoir: 15cm large / 60cm haut", "Dossier: 10cm large / 70cm haut", "Coussins: 65/80/90cm large", f"Profondeur assise: {dims.get('profondeur',0)} cm", f"Hauteur assise: {ha} cm (Mousse {hm}cm)"]:
        draw.text((cx2, cy), f"• {it}", font=FONTS['small'], fill=COLOR_TEXT); cy+=25

    draw.text((MARGIN, IMG_H-50), "FRÉVENT 62270", font=FONTS['regular'], fill=COLOR_TEXT, anchor="lm")
    
    b = BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import re

# --- POLICE UNICODE ---
FONT_NAME_UNICODE = 'DejaVuSans'
FONT_FILE = 'DejaVuSans.ttf'

if os.path.exists(FONT_FILE):
    pdfmetrics.registerFont(TTFont(FONT_NAME_UNICODE, FONT_FILE))
    BASE_FONT = FONT_NAME_UNICODE
else:
    BASE_FONT = 'Helvetica'

# --- MAPPING DES IMAGES ---
IMAGE_FILES = {
    'D25': 'D25.png',
    'D30': 'D30.png',
    'HR35': 'HR35.png',
    'HR45': 'HR45.png'
}

def generer_pdf_devis(config, prix_details, schema_image=None, breakdown_rows=None,
                      reduction_ttc=0.0, show_detail_devis=True, show_detail_cr=True,
                      show_detail_usine=False):
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=1*cm, leftMargin=1*cm,
                           topMargin=1*cm, bottomMargin=4*cm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # --- STYLES ---
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=14, textColor=colors.black, spaceAfter=5, alignment=TA_CENTER, fontName=BASE_FONT + '-Bold')
    header_info_style = ParagraphStyle('HeaderInfo', parent=styles['Normal'], fontSize=12, leading=14, textColor=colors.black, alignment=TA_CENTER, fontName=BASE_FONT)
    description_mousse_style = ParagraphStyle('MousseDesc', parent=styles['Normal'], fontSize=10, leading=11, textColor=colors.black, alignment=TA_LEFT, fontName=BASE_FONT)
    column_header_style = ParagraphStyle('ColumnHeaderStyle', parent=styles['Normal'], fontSize=11, alignment=TA_LEFT, fontName=BASE_FONT + '-Bold', spaceAfter=6)
    detail_style = ParagraphStyle('DetailStyle', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.black, alignment=TA_LEFT, fontName=BASE_FONT) # Leading augmenté pour aérer
    footer_style = ParagraphStyle('FooterStyle', parent=styles['Normal'], fontSize=12, textColor=colors.black, alignment=TA_CENTER, spaceBefore=10, fontName=BASE_FONT)
    footer_header_style = ParagraphStyle('FooterHeaderStyle', parent=column_header_style, fontSize=column_header_style.fontSize - 2, alignment=TA_LEFT, fontName=column_header_style.fontName, spaceAfter=column_header_style.spaceAfter)

    # --- FOOTER ---
    def draw_footer(canvas, doc):
        canvas.saveState()
        col_gauche = [Paragraph("Il faut savoir que le tarif comprend :", footer_header_style)]
        for item in ["Fabrication 100% artisanale France", "Choix du tissu n'impacte pas le devis", "Paiement 2 à 6 fois sans frais", "Livraison 5 à 7 semaines", "Housses déhoussables"]:
            col_gauche.append(Paragraph(f"• {item}", detail_style))

        h_mousse = config['options'].get('epaisseur', 25)
        h_assise = 46 if h_mousse > 20 else 40
        col_droite = [Paragraph("Détail des cotations :", footer_header_style)]
        for item in ["Accoudoir: 15cm large / 60cm haut", "Dossier: 10cm large / 70cm haut", "Coussins: 65/80/90cm large", f"Profondeur assise: {config['dimensions']['profondeur']} cm", f"Hauteur assise: {h_assise} cm (Mousse {h_mousse}cm)"]:
            col_droite.append(Paragraph(f"• {item}", detail_style))

        table_footer = Table([[col_gauche, col_droite]], colWidths=[9.5*cm, 9.5*cm])
        table_footer.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
        table_footer.wrapOn(canvas, doc.width, doc.bottomMargin)
        table_footer.drawOn(canvas, doc.leftMargin, 1*cm)
        
        p_ville = Paragraph("FRÉVENT 62270", footer_style)
        p_ville.wrapOn(canvas, doc.width, doc.bottomMargin)
        p_ville.drawOn(canvas, doc.leftMargin, 0.4*cm)
        canvas.restoreState()

    # --- CONTENU ---
    
    # 1. INFO CLIENT
    client = config.get('client', {})
    # Retirer les balises <b> et </b> pour éviter des fermetures superflues
    lines_info = [f"{k}: {v}" for k,v in [("Nom", client.get('nom')), ("Téléphone", client.get('telephone'))] if v]
    if lines_info: elements.append(Paragraph("<br/>".join(lines_info), header_info_style))
    
    # 2. MOUSSE
    mousse_type = config.get('options', {}).get('type_mousse', 'HR35')
    desc_map = {
        'D25': "La mousse D25 (25kg/m3) est très ferme, style marocain classique.",
        'D30': "La mousse D30 (30kg/m3) est ultra ferme.",
        'HR35': "La mousse HR35 (35kg/m3) est semi-ferme confortable. Haute résilience.",
        'HR45': "La mousse HR45 (45kg/m3) est ferme confortable. Haute résilience."
    }
    img_path = IMAGE_FILES.get(mousse_type)
    desc_para = Paragraph(f"<i>{desc_map.get(mousse_type, '')}</i>", description_mousse_style)
    
    if img_path and os.path.exists(img_path):
        m_table = Table([[Image(img_path, width=2.5*cm, height=2.5*cm), desc_para]], colWidths=[3*cm, 14*cm])
        m_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        elements.append(Spacer(1, 0.2*cm))
        elements.append(m_table)
    else:
        elements.append(Spacer(1, 0.2*cm))
        elements.append(desc_para)

    # 3. SCHEMA
    if schema_image:
        elements.append(Spacer(1, 0.1*cm))
        try:
            img = Image(schema_image)
            avail_w, avail_h = doc.width, 10*cm
            factor = min(avail_w/img.imageWidth, avail_h/img.imageHeight) if img.imageWidth > 0 else 1
            img.drawWidth, img.drawHeight = img.imageWidth*factor, img.imageHeight*factor
            elements.append(img)
        except:
            elements.append(Paragraph("(Schéma non disponible)", header_info_style))
        elements.append(Spacer(1, 0.2*cm))

    # 4. DÉTAIL DU DEVIS (Nouvelle logique harmonisée)
    # Préparation données
    type_coussins = config.get('options', {}).get('type_coussins', 'auto')
    coussins_label = "Coussins valises" if type_coussins in ['valise', 'p', 'g'] else "Coussins"
    
    # Récupération coussins descriptif
    details_list = prix_details.get('calculation_details', [])
    cushion_counts = {}
    nb_coussins_assise = None
    if breakdown_rows:
        for r in breakdown_rows:
            if r and len(r)>=2 and "Coussins assise" in str(r[0]): nb_coussins_assise = r[1]

    # Analyse détails pour options
    extras_list = []
    for entry in details_list:
        cat = entry.get('category', '').lower()
        qty = entry.get('quantity', 0)
        item = entry.get('item', '').lower()
        if cat == 'traversin' and qty: extras_list.append(f"Traversins : {qty} de 70x20cm")
        elif cat == 'surmatelas' and qty: extras_list.append(f"Surmatelas : {qty} confort")
        elif cat == 'cushion' and 'déco' in item and qty: extras_list.append(f"Coussins déco : {qty}")
        elif cat == 'cushion':
            # Logique de comptage coussins (simplifiée)
            parts = item.split(); label = None
            for p in parts:
                if p.replace('cm','').isdigit(): label = f"{p.replace('cm','')}cm"; break
            if not label: 
                if 'valise' in item: label='valise'
                elif 'petit' in item: label='petit'
                elif 'grand' in item: label='grand'
            if label: cushion_counts[label] = cushion_counts.get(label, 0) + qty

    # Formatage string coussins
    if type_coussins in ['valise', 'p', 'g']:
        total = nb_coussins_assise if nb_coussins_assise is not None else sum(v for k,v in cushion_counts.items() if 'cm' not in k)
        coussins_descr = f"{total} coussins valises sur mesure"
    else:
        parts_c = [f"{v} x {k}" for k,v in sorted(cushion_counts.items())]
        coussins_descr = ", ".join(parts_c) if parts_c else (f"{nb_coussins_assise} x ..." if nb_coussins_assise else "-")

    # --- CONSTRUCTION DU TABLEAU HARMONISÉ ---
    # Liste Gauche
    dims = config.get('dimensions', {})
    tc = config.get('type_canape', '')
    d_str = f"{dims.get('ty',0)} x {dims.get('tx',0)} x {dims.get('tz',0)}" if "U" in tc else (f"{dims.get('ty',0)} x {dims.get('tx',0)}" if "L" in tc else f"{dims.get('tx',0)} x {dims.get('profondeur',0)}")
    
    acc_txt = "Avec" if (config['options'].get('acc_left') or config['options'].get('acc_right')) else "Sans"
    opt = config['options']
    dos_txt = "Avec" if (opt.get('dossier_left') or opt.get('dossier_bas') or opt.get('dossier_right')) else "Sans"

    # Liste des items (Label, Valeur) pour la gauche
    items_gauche = [
        f"Dimensions : {d_str} cm",
        f"Mousse : {mousse_type}",
        f"Accoudoirs : {acc_txt}",
        f"Dossiers : {dos_txt}",
        f"Profondeur : {dims.get('profondeur',0)}cm"
    ]

    # Liste des items pour la droite
    # 1. Coussins
    items_droite = [f"{coussins_label} : {coussins_descr}"]
    # 2. Options (Traversins, Surmatelas, Déco) -> Chacun sur sa propre ligne
    items_droite.extend(extras_list)
    # 3. Prix et Réduction
    reduc = float(reduction_ttc or 0.0)
    total = float(prix_details.get('total_ttc', 0.0))
    items_droite.append(f"Réduction : {reduc:.2f} €")
    # Pour le prix, on utilise une mise en forme spéciale, on le marque
    items_droite.append(f"TOTAL_PRICE_TAG::{total:.2f} €")
    items_droite.append(f"Prix avant réduction : {(total + reduc):.2f} €")

    # Fusion des listes pour créer les rangées
    rows = []
    # Titre
    rows.append([Paragraph("Détail du devis :", column_header_style), Paragraph("", detail_style)])
    
    max_len = max(len(items_gauche), len(items_droite))
    for i in range(max_len):
        txt_g = items_gauche[i] if i < len(items_gauche) else ""
        txt_d = items_droite[i] if i < len(items_droite) else ""
        
        # Traitement spécial pour le prix (gras)
        if "TOTAL_PRICE_TAG::" in txt_d:
            price_val = txt_d.replace("TOTAL_PRICE_TAG::", "")
            # Retirer les balises <b> pour ne pas avoir de fermeture inutile
            cell_d = Paragraph(f"Prix canapé : {price_val}", detail_style)
        else:
            cell_d = Paragraph(txt_d, detail_style)
            
        cell_g = Paragraph(txt_g, detail_style)
        rows.append([cell_g, cell_d])

    # Création du tableau final
    t_devis = Table(rows, colWidths=[9.5*cm, 9.5*cm])
    t_devis.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6), # Espace fixe entre chaque ligne
    ]))
    elements.append(t_devis)

# -----------------------------------------------------------
    # 5. PAGES DÉTAILLÉES (AVEC RETOUR À LA LIGNE AUTOMATIQUE)
    # -----------------------------------------------------------
    
    # Création d'un style spécifique pour les cellules de tableau (taille 9)
    # Le 'leading' correspond à l'espace interligne (10 pour une police de 9)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, leading=10)

    # --- PAGE 2 : Détail devis ---
    if show_detail_devis and details_list:
        elements.append(PageBreak())
        elements.append(Paragraph("Détail des calculs du prix", title_style))
        
        # En-têtes
        headers = ["Catégorie", "Article", "Qté", "P.U.", "Formule", "Total"]
        # On utilise cell_style aussi pour les en-têtes pour garder la cohérence
        data = [[Paragraph(f"<b>{h}</b>", cell_style) for h in headers]]
        
        for e in details_list:
            # Transformation des textes en Paragraph pour le retour à la ligne
            data.append([
                Paragraph(e.get('category','').capitalize(), cell_style),
                Paragraph(e.get('item',''), cell_style), # C'est souvent ici que c'est long
                Paragraph(str(e.get('quantity','')), cell_style),
                Paragraph(f"{e.get('unit_price',0):.2f}€", cell_style),
                Paragraph(e.get('formula',''), cell_style), # Formule peut être longue aussi
                Paragraph(f"{e.get('total_price',0):.2f}€", cell_style)
            ])
            
        data.append(["Total TTC", "", "", "", "", f"{prix_details.get('total_ttc',0):.2f}€"])
        
        t_det = Table(data, colWidths=[3*cm, 5*cm, 1.5*cm, 3*cm, 4.5*cm, 3*cm], repeatRows=1)
        t_det.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#F5F5F5')), 
            ('GRID',(0,0),(-1,-1),0.25,colors.black),
            ('VALIGN',(0,0),(-1,-1),'TOP'), # Alignement en haut pour que ce soit joli si une cellule est haute
        ]))
        elements.append(t_det)

    # --- PAGE 3 : Coût de revient ---
    if show_detail_cr and prix_details.get('calculation_details_cr'):
        elements.append(PageBreak())
        elements.append(Paragraph("Détail du coût de revient", title_style))
        
        headers_cr = ["Catégorie", "Article", "Qté", "C.U.", "Formule", "Total"]
        data_cr = [[Paragraph(f"<b>{h}</b>", cell_style) for h in headers_cr]]
        
        for e in prix_details['calculation_details_cr']:
            data_cr.append([
                Paragraph(e.get('category','').capitalize(), cell_style),
                Paragraph(e.get('item',''), cell_style),
                Paragraph(str(e.get('quantity','')), cell_style),
                Paragraph(f"{e.get('unit_price',0):.2f}€", cell_style),
                Paragraph(e.get('formula',''), cell_style),
                Paragraph(f"{e.get('total_price',0):.2f}€", cell_style)
            ])
            
        data_cr.append(["Total CR HT", "", "", "", "", f"{prix_details.get('cout_revient_ht',0):.2f}€"])
        if 'marge_ht' in prix_details:
            data_cr.append(["Marge HT", "", "", "", "", f"{prix_details.get('marge_ht',0):.2f}€"])
            
        t_cr = Table(data_cr, colWidths=[3*cm, 5*cm, 1.5*cm, 3*cm, 4.5*cm, 3*cm], repeatRows=1)
        t_cr.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#F5F5F5')),
            ('GRID',(0,0),(-1,-1),0.25,colors.black),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
        ]))
        elements.append(t_cr)

    # --- PAGE 4 : Prix Usine ---
    if show_detail_usine and prix_details.get('calculation_details_usine'):
        elements.append(PageBreak())
        elements.append(Paragraph("Détail des prix usine", title_style))
        
        headers_usine = ["Catégorie", "Article", "Qté", "C.U.", "Formule", "Total"]
        data_usine = [[Paragraph(f"<b>{h}</b>", cell_style) for h in headers_usine]]
        
        for entry in prix_details['calculation_details_usine']:
            # Conversion sécurisée pour affichage
            unit = entry.get('unit_price',0)
            unit_str = f"{unit:.2f}€" if isinstance(unit, (int, float)) else str(unit)
            
            total = entry.get('total_price',0)
            total_str = f"{total:.2f}€" if isinstance(total, (int, float)) else str(total)

            data_usine.append([
                Paragraph(entry.get('category','').capitalize(), cell_style),
                Paragraph(entry.get('item',''), cell_style),
                Paragraph(str(entry.get('quantity','')), cell_style),
                Paragraph(unit_str, cell_style),
                Paragraph(entry.get('formula',''), cell_style),
                Paragraph(total_str, cell_style)
            ])
            
        data_usine.append(["Total HT usine", "", "", "", "", f"{prix_details.get('usine_ht_total',0):.2f}€"])
        data_usine.append(["Total TTC usine", "", "", "", "", f"{prix_details.get('usine_ttc_total',0):.2f}€"])
        
        t_usine = Table(data_usine, colWidths=[3*cm, 5*cm, 1.5*cm, 3*cm, 4.5*cm, 3*cm], repeatRows=1)
        t_usine.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#F5F5F5')),
            ('GRID',(0,0),(-1,-1),0.25,colors.black),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
        ]))
        elements.append(t_usine)

    doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer

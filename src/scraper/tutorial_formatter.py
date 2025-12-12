"""
Module de formatage des tutoriels pour Zoho Desk.
Convertit les tutoriels en HTML formaté.
"""

from typing import List, Dict


def format_tutorial_html(tutorial: Dict) -> str:
    """
    Formate un tutoriel en HTML pour Zoho Desk.
    
    Args:
        tutorial: Dictionnaire contenant les données du tutoriel
        
    Returns:
        HTML formaté du tutoriel
    """
    html_parts = []
    
    # Titre du tutoriel
    title = tutorial.get('title', 'Tutoriel')
    html_parts.append(f"<h2 style='color:#2874A6; margin-top:20px; border-bottom:2px solid #2874A6; padding-bottom:8px;'>{title}</h2>")
    
    # Lien vers le tutoriel original
    tutorial_url = tutorial.get('url', '')
    if tutorial_url:
        html_parts.append(f"""
<div style='background:#E8F4F8; padding:12px; border-left:4px solid #2E86C1; margin:12px 0;'>
    <p style='margin:0;'>
        <strong>📖 Voir le tutoriel complet :</strong> 
        <a href='{tutorial_url}' target='_blank' style='color:#2E86C1;'>Ouvrir sur le site Avidsen</a>
    </p>
</div>
""")
    
    # Étapes du tutoriel
    steps = tutorial.get('steps', [])
    if steps:
        for step in steps:
            step_number = step.get('number', 0)
            step_title = step.get('title', f'Étape {step_number}')
            step_description = step.get('description', '')
            step_image = step.get('image_url', '')
            
            # Conteneur de l'étape
            html_parts.append(f"""
<div style='margin:20px 0; padding:15px; background:#F9F9F9; border-radius:8px; border:1px solid #E0E0E0;'>
    <h3 style='color:#2E86C1; margin-top:0;'>
        <span style='background:#2E86C1; color:white; padding:4px 12px; border-radius:4px; margin-right:8px;'>{step_number}</span>
        {step_title}
    </h3>
""")
            
            # Image de l'étape
            if step_image:
                html_parts.append(f"""
    <div style='text-align:center; margin:15px 0;'>
        <img src='{step_image}' alt='{step_title}' style='max-width:100%; max-height:500px; border:1px solid #ddd; border-radius:4px; box-shadow:0 2px 4px rgba(0,0,0,0.1);'/>
    </div>
""")
            
            # Description de l'étape
            if step_description:
                # Convertir les retours à la ligne en paragraphes
                paragraphs = step_description.split('\n')
                for para in paragraphs:
                    if para.strip():
                        html_parts.append(f"    <p style='line-height:1.6; margin:8px 0;'>{para.strip()}</p>")
            
            html_parts.append("</div>")
    
    return '\n'.join(html_parts)


def format_tutorials_section(tutorials: List[Dict]) -> str:
    """
    Formate une section complète avec plusieurs tutoriels EN UTILISANT LE HTML ORIGINAL.
    Version propre sans éléments superflus.
    
    Args:
        tutorials: Liste de tutoriels
        
    Returns:
        HTML formaté de la section tutoriels (HTML original préservé)
    """
    if not tutorials:
        return ""
    
    html_parts = []
    
    # Ajouter chaque tutoriel avec son HTML original
    for tutorial in tutorials:
        # Lien vers le tutoriel original (discret)
        tutorial_url = tutorial.get('url', '')
        if tutorial_url:
            html_parts.append(f"""
<div style='margin:15px 0 10px 0; padding:8px; background:#f0f8ff; border-left:3px solid #2E86C1;'>
    <p style='margin:0; font-size:14px;'><strong>📖 Source :</strong> <a href='{tutorial_url}' target='_blank' style='color:#2E86C1; text-decoration:none;'>Voir sur avidsen.com</a></p>
</div>
""")
        
        # Ajouter le HTML original du tutoriel (PROPRE, sans navigation)
        html_content = tutorial.get('html_content', '')
        if html_content:
            html_parts.append(html_content)
        else:
            # Fallback sur l'ancien format si html_content n'existe pas
            html_parts.append(format_tutorial_html(tutorial))
        
        # Séparateur entre tutoriels si plusieurs
        if len(tutorials) > 1:
            html_parts.append("<hr style='margin:30px 0; border:none; border-top:1px solid #e0e0e0;'/>")
    
    return '\n'.join(html_parts)


def create_tutorial_summary(tutorials: List[Dict]) -> str:
    """
    Crée un résumé des tutoriels disponibles (pour affichage en haut de page).
    
    Args:
        tutorials: Liste de tutoriels
        
    Returns:
        HTML du résumé
    """
    if not tutorials:
        return ""
    
    html_parts = []
    
    html_parts.append("""
<div style='background:#FFF9E6; padding:15px; border-left:4px solid #FFC107; margin:15px 0; border-radius:4px;'>
    <h3 style='color:#F57C00; margin-top:0;'>📚 Tutoriels disponibles pour ce produit :</h3>
    <ul style='margin:8px 0; padding-left:20px;'>
""")
    
    for tutorial in tutorials:
        title = tutorial.get('title', 'Tutoriel')
        url = tutorial.get('url', '#')
        html_parts.append(f"        <li><a href='{url}' target='_blank' style='color:#2E86C1;'>{title}</a></li>")
    
    html_parts.append("""
    </ul>
</div>
""")
    
    return '\n'.join(html_parts)

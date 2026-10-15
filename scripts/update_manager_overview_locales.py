"""Translations for the unified tournament progress view."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
M={
'Independent tournament queue':'Cola independiente de torneos|File indépendante de tournois|Unabhängige Turnierwarteschlange|Fila independente de torneios|Coda indipendente dei tornei|Onafhankelijke toernooiwachtrij|Niezależna kolejka turniejów',
'Independent queue':'Cola independiente|File indépendante|Unabhängige Warteschlange|Fila independente|Coda indipendente|Onafhankelijke wachtrij|Niezależna kolejka',
'Source':'Origen|Source|Quelle|Origem|Origine|Bron|Źródło',
'All current tournaments':'Todos los torneos vigentes|Tous les tournois actuels|Alle aktuellen Turniere|Todos os torneios atuais|Tutti i tornei attuali|Alle huidige toernooien|Wszystkie bieżące turnieje',
'League stages appear below. Use the event controls for shared resources, pausing and season progression.':'Las etapas de la liga aparecen abajo. Use los controles del evento para los recursos compartidos, las pausas y el avance de temporada.|Les étapes de la ligue figurent ci-dessous. Utilisez les commandes de l’événement pour les ressources partagées, les pauses et la progression des saisons.|Die Ligaphasen stehen unten. Gemeinsame Ressourcen, Pausen und Saisonfortschritt werden über die Veranstaltung gesteuert.|As etapas da liga aparecem abaixo. Use os controles do evento para os recursos compartilhados, pausas e avanço das temporadas.|Le fasi della lega sono elencate sotto. Usa i controlli dell’evento per risorse condivise, pause e avanzamento delle stagioni.|De competitiefasen staan hieronder. Gebruik de evenementbediening voor gedeelde middelen, pauzeren en seizoensverloop.|Etapy ligi są widoczne poniżej. Wspólnymi zasobami, wstrzymywaniem i przebiegiem sezonów zarządza się w wydarzeniu.',
'Event resources…':'Recursos del evento…|Ressources de l’événement…|Veranstaltungsressourcen…|Recursos do evento…|Risorse dell’evento…|Evenementmiddelen…|Zasoby wydarzenia…',
'Resources…':'Recursos…|Ressources…|Ressourcen…|Recursos…|Risorse…|Middelen…|Zasoby…',
'The event manages its own execution mode and shared budget.':'El evento gestiona su propio modo de ejecución y presupuesto compartido.|L’événement gère son propre mode d’exécution et son budget partagé.|Die Veranstaltung verwaltet ihren eigenen Ausführungsmodus und ihr gemeinsames Ressourcenbudget.|O evento gerencia seu próprio modo de execução e orçamento compartilhado.|L’evento gestisce la propria modalità di esecuzione e il budget condiviso.|Het evenement beheert zijn eigen uitvoeringsmodus en gedeelde budget.|Wydarzenie zarządza własnym trybem działania i wspólnym limitem zasobów.',
'No tournaments queued.':'No hay torneos en cola.|Aucun tournoi en file.|Keine Turniere in der Warteschlange.|Nenhum torneio na fila.|Nessun torneo in coda.|Geen toernooien in de wachtrij.|Brak turniejów w kolejce.',
'Not queued':'Fuera de la cola|Hors file|Nicht eingereiht|Fora da fila|Non in coda|Niet in wachtrij|Poza kolejką',
'Select tournament {0}':'Seleccionar torneo {0}|Sélectionner le tournoi {0}|Turnier {0} auswählen|Selecionar torneio {0}|Seleziona torneo {0}|Toernooi {0} selecteren|Wybierz turniej {0}',
'Use the event controls to pause or manage linked stages.':'Use los controles del evento para pausar o gestionar las etapas vinculadas.|Utilisez les commandes de l’événement pour suspendre ou gérer les étapes liées.|Verknüpfte Phasen über die Veranstaltungssteuerung pausieren oder verwalten.|Use os controles do evento para pausar ou gerenciar etapas vinculadas.|Usa i controlli dell’evento per sospendere o gestire le fasi collegate.|Gebruik de evenementbediening om gekoppelde fasen te pauzeren of beheren.|Użyj sterowania wydarzeniem, aby wstrzymać lub zarządzać powiązanymi etapami.',
'Unknown tournament scope':'Ámbito de torneos desconocido|Périmètre de tournois inconnu|Unbekannter Turnierbereich|Escopo de torneios desconhecido|Ambito dei tornei sconosciuto|Onbekend toernooibereik|Nieznany zakres turniejów',
}
sources=json.loads((ROOT/'locales/sources.json').read_text(encoding='utf-8'))
for key in M:sources.setdefault(key,['ui/tournament-queue.js','arena/tournament_queue.py'])
sources['Engine Arena — 1.3.1']=['desktop/Program.cs']
for i,code in enumerate(['en','es','fr','de','pt','it','nl','pl']):
    p=ROOT/'locales'/f'{code}.json';data=json.loads(p.read_text(encoding='utf-8'))
    data['messages'].update({k:k if not i else v.split('|')[i-1] for k,v in M.items()})
    data['messages']['Engine Arena — 1.3.1']='Engine Arena — 1.3.1'
    if not i:data['messages'].update({k:k for k in sources})
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'locales/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

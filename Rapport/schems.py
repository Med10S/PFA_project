from graphviz import Digraph

dot = Digraph('Architecture', format='png')
dot.attr(rankdir='TB', size='8,10')
dot.attr('node', shape='box', style='filled', color='lightblue', fontname='Helvetica')

# Dummy node pour forcer le centrage visuel

# COUCHE CAPTURE
with dot.subgraph(name='cluster_capture') as c:
    c.attr(label='COUCHE CAPTURE', style='filled', color='lightgrey')
    c.node('sniffer', 'Packet Sniffer\n(Scapy/tcpdump)')

# COUCHE STOCKAGE
with dot.subgraph(name='cluster_stockage') as s:
    s.attr(label='COUCHE STOCKAGE', style='filled', color='lightgrey')
    s.node('redis', 'Redis Database\n(Real-time Storage)')

# Forcer sniffer et redis sur la même ligne

dot.edge('sniffer', 'redis')

# COUCHE TRAITEMENT
with dot.subgraph(name='cluster_traitement') as t:
    t.attr(label='COUCHE TRAITEMENT', style='filled', color='lightgrey')
    t.node('flow', 'Flow Analysis\n(NFStream)')
    t.node('features', 'Feature Extract\n(UNSW-NB15)')

# COUCHE DÉTECTION
with dot.subgraph(name='cluster_detection') as d:
    d.attr(label='COUCHE DÉTECTION', style='filled', color='lightgrey')
    d.node('ml_api', 'ML Model API\n(Model Management)')
    d.node('knn', 'KNN Model\n(30% weight)')
    d.node('mlp', 'MLP Model\n(35% weight)')
    d.node('xgb', 'XGBoost Model\n(35% weight)')
    d.node('voting', 'Ensemble Voting\n(Weighted)')

# COUCHE RÉPONSE
with dot.subgraph(name='cluster_reponse') as r:
    r.attr(label='COUCHE RÉPONSE', style='filled', color='lightgrey')
    r.node('detection', 'Real-time Detection\n(FastAPI)')
    r.node('alert', 'Alerting System\n(Log/Webhook)')
    r.node('dashboard', 'Dashboard & Reporting\n(Web UI)')

# Connexions entre couches
dot.edge('redis', 'flow')
dot.edge('flow', 'features')

dot.edge('features', 'ml_api')
dot.edge('ml_api', 'knn')
dot.edge('ml_api', 'mlp')
dot.edge('ml_api', 'xgb')

dot.edge('knn', 'voting')
dot.edge('mlp', 'voting')
dot.edge('xgb', 'voting')

dot.edge('voting', 'detection')
dot.edge('voting', 'alert')
dot.edge('voting', 'dashboard')

# Génération du fichier
dot.render('architecture_systeme_detection', cleanup=True)

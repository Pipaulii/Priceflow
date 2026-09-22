PRICEFLOW - INSTALLATION DASHBOARD ADMIN

1. Dans Supabase, ouvre ton projet PriceFlow.
2. Menu SQL Editor > New query.
3. Copie tout le contenu de SUPABASE_ADMIN.sql.
4. Clique Run.
5. Remplace ensuite le app.py de ton dépôt GitHub par le app.py fourni.
6. Streamlit Cloud redémarrera automatiquement après le commit (sinon Reboot app).

Le dashboard se trouve dans : Mon compte > Administration PriceFlow.

IMPORTANT SECURITE
La vue admin_profiles contient les e-mails des comptes. Le code n'affiche la section que si is_admin() est vrai, mais pour une protection serveur renforcée il est préférable de remplacer cette vue par une fonction RPC SECURITY DEFINER vérifiant explicitement l'e-mail administrateur. Ne partage jamais SUPABASE service_role dans GitHub ou Streamlit côté client.

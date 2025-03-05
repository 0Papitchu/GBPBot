import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Charger les données CSV avec gestion des erreurs
df = pd.read_csv("opportunities.csv", on_bad_lines='skip')

# Vérifier les colonnes disponibles
print("Colonnes disponibles :", df.columns)

# Nettoyer les noms de colonnes pour éviter les espaces indésirables
df.rename(columns=lambda x: x.strip(), inplace=True)

# Vérifier que la colonne 'Date' existe bien
if 'Date' not in df.columns:
    raise KeyError("La colonne 'Date' est introuvable dans le fichier CSV. Vérifiez l'en-tête du fichier.")

# Convertir la colonne de date en format datetime
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
df.dropna(subset=['Date'], inplace=True)  # Supprime les lignes où la date est invalide
df['Hour'] = df['Date'].dt.hour  # Extraire l'heure pour analyse

# Vérification et calcul des profits
profit_total = df['Profit (USDT)'].sum() if 'Profit (USDT)' in df.columns else None
profit_total_brut = df['Profit Brut (USDT)'].sum() if 'Profit Brut (USDT)' in df.columns else None

# Calculs globaux
temps_moyen = df['Date'].diff().mean()
heure_plus_frequente = df['Hour'].mode()[0]

# Top 5 des plus gros gains
if 'Profit (USDT)' in df.columns:
    top_5_gains = df.nlargest(5, 'Profit (USDT)')[['Date', 'Profit (USDT)', 'ROI (%)']]
else:
    top_5_gains = None

# Affichage des résultats
def afficher_resume():
    print("\n=== RÉSUMÉ DES OPPORTUNITÉS ===")
    print(f"Nombre total d'opportunités : {len(df)}")
    if profit_total is not None:
        print(f"Profit total généré : {profit_total:.2f} USDT")
    if profit_total_brut is not None:
        print(f"Profit Brut total : {profit_total_brut:.2f} USDT")
    print(f"Temps moyen entre opportunités : {temps_moyen}")
    print(f"Heure la plus fréquente pour les opportunités : {heure_plus_frequente}h")
    
    if top_5_gains is not None:
        print("\n=== TOP 5 DES PLUS GROS GAINS ===")
        print(top_5_gains.to_string(index=False))
    else:
        print("Impossible d'afficher le top 5 des gains, colonne 'Profit (USDT)' absente.")

# Génération des graphiques
def generer_graphiques():
    fig, axes = plt.subplots(3, 1, figsize=(12, 12))
    
    if 'Profit (USDT)' in df.columns:
        sns.lineplot(ax=axes[0], x=df['Date'], y=df['Profit (USDT)'], marker='o', label="Profit Net (USDT)")
        axes[0].set_title("Evolution du Profit Net sur le Temps")
        axes[0].set_ylabel("Profit (USDT)")
        axes[0].grid()
        axes[0].legend()
    
    if 'ROI (%)' in df.columns:
        sns.scatterplot(ax=axes[1], x=df['Date'], y=df['ROI (%)'], color='r', label="ROI (%)")
        sns.lineplot(ax=axes[1], x=df['Date'], y=df['ROI (%)'].rolling(window=5).mean(), color='g', label="Tendance ROI")
        axes[1].set_title("Evolution du ROI (%) sur le Temps")
        axes[1].set_ylabel("ROI (%)")
        axes[1].grid()
        axes[1].legend()
    
    if 'Profit (USDT)' in df.columns:
        profits_par_heure = df.groupby('Hour')['Profit (USDT)'].sum()
        sns.barplot(ax=axes[2], x=profits_par_heure.index, y=profits_par_heure.values, color='b')
        axes[2].set_title("Profits par Heure de la Journée")
        axes[2].set_xlabel("Heure")
        axes[2].set_ylabel("Profit Total (USDT)")
        axes[2].grid()
    
    plt.tight_layout()
    plt.show()

# Exécution de l'analyse
afficher_resume()
generer_graphiques()
